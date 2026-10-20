from pathlib import Path

import streamlit as st

import db
import ui
from ingest import DATA_DIR, build_vectorstore
from llm import friendly_error
from rag import ask, get_retriever

st.set_page_config(page_title="AI Study Buddy", page_icon="🤖")
ui.load_css()
db.init_db()

PAGES = ["Study Chat", "History", "Quizzes", "Interview Practice"]

# ---------- Session state ----------
st.session_state.setdefault("session_id", None)
st.session_state.setdefault("page", "Study Chat")


def open_session(sid):
    st.session_state.session_id = sid
    st.session_state.page = "Study Chat"


def new_chat():
    st.session_state.session_id = None
    st.session_state.page = "Study Chat"


def show_sources(sources):
    if sources:
        with st.expander("Sources"):
            for s in sources:
                st.write("•", s)


# ---------- Sidebar ----------
with st.sidebar:
    st.title("🤖 AI Study Buddy")
    st.radio("Go to", PAGES, key="page")
    st.button("➕ New chat", on_click=new_chat)

    st.divider()
    st.subheader("Study material")
    uploaded = st.file_uploader(
        "Upload PDFs or notes", type=["pdf", "txt", "md"], accept_multiple_files=True
    )
    if st.button("Process documents", type="primary"):
        if not uploaded:
            st.warning("Choose at least one file first.")
        else:
            Path(DATA_DIR).mkdir(exist_ok=True)
            for f in uploaded:
                (Path(DATA_DIR) / f.name).write_bytes(f.getbuffer())
            with st.spinner("Reading and indexing..."):
                try:
                    pages, chunks = build_vectorstore()
                    get_retriever.cache_clear()
                    st.success(f"Indexed {pages} pages into {chunks} chunks")
                except Exception as e:
                    st.error(f"Could not index the documents: {e}")

page = st.session_state.page

# ---------- Study Chat ----------
if page == "Study Chat":
    ui.page_header("Study Chat", "Ask anything about your study material...")
    sid = st.session_state.session_id
    messages = db.get_messages(sid) if sid else []

    for m in messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
            show_sources(m["sources"])

    if question := st.chat_input("Ask anything about your study material..."):
        with st.chat_message("user"):
            st.markdown(question)
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    answer, sources = ask(question, messages)
                except Exception as e:
                    st.error(friendly_error(e))
                    st.stop()
            st.markdown(answer)
            show_sources(sources)

        if sid is None:
            sid = db.create_session(question[:40])
            st.session_state.session_id = sid
        db.add_message(sid, "user", question)
        db.add_message(sid, "assistant", answer, sources)

# ---------- History ----------
elif page == "History":
    ui.page_header("History", "Revisit your earlier chats and quiz scores.")
    sessions = db.list_sessions()
    if not sessions:
        st.info("No saved chats yet.")
    for sid, title, created in sessions:
        c1, c2, c3 = st.columns([5, 1.5, 1])
        c1.write(f"**{title}**  \n{created}")
        c2.button("Open", key=f"open_{sid}", on_click=open_session, args=(sid,))
        if c3.button("🗑", key=f"del_{sid}"):
            db.delete_session(sid)
            if st.session_state.session_id == sid:
                st.session_state.session_id = None
            st.rerun()

    st.subheader("Quiz scores")
    results = db.get_quiz_results()
    if not results:
        st.caption("No quiz attempts yet.")
    for topic, score, total, when in results:
        st.write(f"{when} — {topic}: **{score}/{total}**")

# ---------- Quizzes (coming in a later module) ----------
elif page == "Quizzes":
    ui.page_header("Quizzes", "Test yourself on any topic.")
    st.info("Quizzes arrive in a later step.")

# ---------- Interview Practice (coming in a later module) ----------
else:
    ui.page_header("Interview Practice", "Practice questions and get instant feedback.")
    st.info("Interview practice arrives in a later step.")