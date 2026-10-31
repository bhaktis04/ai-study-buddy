import streamlit as st

import ui
from ingest import add_files, build_vectorstore, delete_document, list_documents
from rag import get_retriever

STATUS_ICON = {"Indexed": "✅", "Not indexed": "⏳", "File missing": "⚠️"}


def _flash(kind, message):
    """Remember a message across the rerun that follows an action."""
    st.session_state.doc_flash = (kind, message)


def _show_flash():
    flash = st.session_state.pop("doc_flash", None)
    if flash:
        getattr(st, flash[0])(flash[1])


def render_documents_page():
    ui.page_header("Documents", "Manage the notes your study buddy answers from.")
    _show_flash()

    # ----- Delete confirmation -----
    pending = st.session_state.get("confirm_delete")
    if pending:
        st.warning(f"Delete **{pending}**? This removes the file and its indexed chunks.")
        b1, b2, _ = st.columns([1.2, 1, 4])
        if b1.button("Yes, delete", type="primary"):
            try:
                removed = delete_document(pending)
                get_retriever.cache_clear()
                _flash("success", f"Deleted {pending} ({removed} chunks removed).")
            except Exception as e:
                _flash("error", f"Could not delete {pending}: {e}")
            st.session_state.confirm_delete = None
            st.rerun()
        if b2.button("Cancel"):
            st.session_state.confirm_delete = None
            st.rerun()
        st.divider()

    docs = list_documents()
    if not docs:
        st.info("No documents yet. Upload files in the sidebar and click 'Process documents'.")
        return

    # ----- Summary -----
    waiting = sum(1 for d in docs if d["status"] == "Not indexed")
    c1, c2, c3 = st.columns(3)
    c1.metric("Files", len(docs))
    c2.metric("Indexed chunks", sum(d["chunks"] for d in docs))
    c3.metric("Waiting to index", waiting)
    st.divider()

    # ----- One row per document -----
    for d in docs:
        name = d["name"]
        col_name, col_status, col_index, col_del = st.columns([4, 1.8, 1.4, 0.8])
        col_name.write(f"**{name}**  \n{d['size_kb']:.0f} KB · {d['chunks']} chunks")
        col_status.write(f"{STATUS_ICON[d['status']]} {d['status']}")

        label = "Re-index" if d["status"] == "Indexed" else "Index"
        if col_index.button(label, key=f"idx_{name}", disabled=d["path"] is None):
            with st.spinner(f"Indexing {name}..."):
                result = add_files([d["path"]])[0]
            get_retriever.cache_clear()
            if result.get("error"):
                _flash("error", f"{name}: could not be read ({result['error']})")
            elif result["chunks"] == 0:
                _flash("warning", f"{name}: no readable text found (a scanned PDF?).")
            else:
                _flash("success", f"{name}: {result['pages']} pages, {result['chunks']} chunks indexed.")
            st.rerun()

        if col_del.button("🗑", key=f"del_{name}"):
            st.session_state.confirm_delete = name
            st.rerun()

    # ----- Full rebuild -----
    st.divider()
    st.caption("Rebuild clears the whole index and re-reads every file in the data folder.")
    if st.button("Re-index everything"):
        with st.spinner("Rebuilding the index..."):
            try:
                pages, chunks = build_vectorstore()
                get_retriever.cache_clear()
                _flash("success", f"Rebuilt: {pages} pages, {chunks} chunks.")
            except Exception as e:
                _flash("error", f"Could not rebuild: {e}")
        st.rerun()