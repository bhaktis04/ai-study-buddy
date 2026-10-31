from functools import lru_cache
from pathlib import Path

from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

DATA_DIR = Path("data")
DB_DIR = "chroma_db"
CHUNK_SIZE = 800
CHUNK_OVERLAP = 150
SUPPORTED = {".pdf", ".txt", ".md"}


@lru_cache(maxsize=1)
def get_embeddings():
    """Load the embedding model once and reuse it."""
    return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")


def _store():
    return Chroma(persist_directory=DB_DIR, embedding_function=get_embeddings())


def _split(docs):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP
    )
    return splitter.split_documents(docs)


def _load_file(path):
    """Read one PDF / TXT / MD file into LangChain documents."""
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return PyPDFLoader(str(path)).load()
    if suffix in (".txt", ".md"):
        return TextLoader(str(path), encoding="utf-8").load()
    return []


def _data_files():
    return [
        f for f in sorted(Path(DATA_DIR).glob("**/*"))
        if f.is_file() and f.suffix.lower() in SUPPORTED
    ]


def load_documents():
    """Read every supported file in data/ (used for a full rebuild)."""
    docs = []
    for f in _data_files():
        docs.extend(_load_file(f))
    return docs


def _chunk_ids(store, filename):
    """IDs of all stored chunks that came from this file name."""
    data = store.get(include=["metadatas"])
    metas = data.get("metadatas") or []
    return [
        i for i, m in zip(data["ids"], metas)
        if Path((m or {}).get("source", "")).name == filename
    ]


def build_vectorstore():
    """Full rebuild from everything in data/. Returns (pages, chunks)."""
    docs = load_documents()
    if not docs:
        raise ValueError("No documents found in the data/ folder.")
    chunks = _split(docs)

    try:
        _store().delete_collection()   # clear the old index, so no duplicates
    except Exception:
        pass

    Chroma.from_documents(chunks, get_embeddings(), persist_directory=DB_DIR)
    return len(docs), len(chunks)


def add_files(paths):
    """Index only these files. Re-adding a file replaces its old chunks.

    Returns one dict per file: name, pages, chunks, and error (if any).
    """
    store = _store()
    results = []
    for p in paths:
        p = Path(p)
        try:
            ids = _chunk_ids(store, p.name)
            if ids:
                store.delete(ids=ids)
            docs = _load_file(p)
            chunks = _split(docs)
            if chunks:
                store.add_documents(chunks)
            results.append({"name": p.name, "pages": len(docs), "chunks": len(chunks)})
        except Exception as e:
            results.append({"name": p.name, "pages": 0, "chunks": 0, "error": str(e)})
    return results


def delete_document(filename):
    """Remove a file's chunks from the index and delete the file itself.

    Returns the number of chunks removed.
    """
    store = _store()
    ids = _chunk_ids(store, filename)
    if ids:
        store.delete(ids=ids)
    for f in _data_files():
        if f.name == filename:
            f.unlink()
    return len(ids)


def _indexed_counts():
    """{file name: number of stored chunks}."""
    if not Path(DB_DIR).exists():
        return {}
    try:
        data = _store().get(include=["metadatas"])
    except Exception:
        return {}
    counts = {}
    for m in data.get("metadatas") or []:
        name = Path((m or {}).get("source", "")).name
        if name:
            counts[name] = counts.get(name, 0) + 1
    return counts


def list_documents():
    """One row per document, with status Indexed, Not indexed or File missing."""
    indexed = _indexed_counts()
    files = {f.name: f for f in _data_files()}
    rows = []
    for name, f in files.items():
        n = indexed.get(name, 0)
        rows.append({
            "name": name,
            "path": str(f),
            "size_kb": f.stat().st_size / 1024,
            "chunks": n,
            "status": "Indexed" if n else "Not indexed",
        })
    for name, n in indexed.items():       # in the index but no longer on disk
        if name not in files:
            rows.append({"name": name, "path": None, "size_kb": 0.0,
                         "chunks": n, "status": "File missing"})
    return rows


if __name__ == "__main__":
    pages, chunks = build_vectorstore()
    print(f"Loaded {pages} pages -> {chunks} chunks stored in {DB_DIR}/")