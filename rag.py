from functools import lru_cache
from pathlib import Path

from langchain_chroma import Chroma

from ingest import DB_DIR, get_embeddings
from llm import ask_llm

SYSTEM_PROMPT = """You are AI Study Buddy, a friendly tutor who explains in simple language.
Rules:
- Use the CONTEXT from the student's notes to answer.
- Explain step by step and include a short example when useful.
- If the context doesn't contain the answer, say so clearly, then give a brief
  general explanation labeled "From general knowledge".
"""


@lru_cache(maxsize=4)
def get_retriever(k=4):
    """Open the vector store and return a retriever for the top-k similar chunks."""
    db = Chroma(persist_directory=DB_DIR, embedding_function=get_embeddings())
    return db.as_retriever(search_kwargs={"k": k})


def format_history(history, last_n=6):
    """Turn the last few chat messages into plain text for the prompt."""
    lines = []
    for m in history[-last_n:]:
        role = "Student" if m["role"] == "user" else "Tutor"
        lines.append(f"{role}: {m['content']}")
    return "\n".join(lines)


def build_prompt(question, history, context):
    return f"""{SYSTEM_PROMPT}

CHAT HISTORY:
{format_history(history)}

CONTEXT:
{context}

QUESTION: {question}

ANSWER:"""


def format_source(doc):
    """Return 'file.pdf (page 3)' or just 'file.md' for text files."""
    name = Path(doc.metadata.get("source", "unknown")).name
    page = doc.metadata.get("page")
    return f"{name} (page {page + 1})" if page is not None else name


def ask(question, history):
    """Retrieve relevant chunks, ask Gemini, and return (answer, sources)."""
    docs = get_retriever().invoke(question)
    context = "\n\n".join(d.page_content for d in docs)
    answer = ask_llm(build_prompt(question, history, context))
    sources = sorted({format_source(d) for d in docs})
    return answer, sources


if __name__ == "__main__":
    history = []
    while True:
        q = input("You: ").strip()
        if q.lower() in ("exit", "quit"):
            break
        if not q:
            continue
        a, s = ask(q, history)
        print("\nTutor:", a, "\nSources:", s, "\n")
        history += [{"role": "user", "content": q}, {"role": "assistant", "content": a}]