import shutil
from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

DATA_DIR = Path("data")
DB_DIR = "chroma_db"

def get_embeddings():
    return HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

def load_documents(folder=DATA_DIR):
    docs = []
    for f in Path(folder).glob("**/*"):
        suffix = f.suffix.lower()
        if suffix == ".pdf":
            docs.extend(PyPDFLoader(str(f)).load())
        elif suffix in (".txt", ".md"):
            docs.extend(TextLoader(str(f), encoding="utf-8").load())
    return docs

def build_vectorstore():
    docs = load_documents()
    if not docs:
        raise ValueError("No documents found in the data/ folder.")

    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=150)
    chunks = splitter.split_documents(docs)

    shutil.rmtree(DB_DIR, ignore_errors=True)   # avoid duplicates on rebuild
    Chroma.from_documents(chunks, get_embeddings(), persist_directory=DB_DIR)
    return len(docs), len(chunks)

if __name__ == "__main__":
    pages, chunks = build_vectorstore()
    print(f"Loaded {pages} pages → {chunks} chunks stored in {DB_DIR}/")