from langchain_chroma import Chroma
from ingest import get_embeddings, DB_DIR
from llm import get_llm

SYSTEM_PROMPT = """You are AI Study Buddy, a friendly tutor who explains in simple language.
Rules:
- Use the CONTEXT from the student's notes to answer.
- Explain step by step and include a short example when useful.
- If the context doesn't contain the answer, say so clearly, then give a brief
  general explanation labeled "From general knowledge".
"""

def get_retriever(k=4):
    db = Chroma(persist_directory=DB_DIR, embedding_function=get_embeddings())
    return db.as_retriever(search_kwargs={"k": k})

def format_history(history, last_n=6):
    lines = []
    for m in history[-last_n:]:
        role = "Student" if m["role"] == "user" else "Tutor"
        lines.append(f"{role}: {m['content']}")
    return "\n".join(lines)

def ask(question, history):
    retriever = get_retriever()
    docs = retriever.invoke(question)
    context = "\n\n".join(d.page_content for d in docs)

    prompt = f"""{SYSTEM_PROMPT}

CHAT HISTORY:
{format_history(history)}

CONTEXT:
{context}

QUESTION: {question}

ANSWER:"""

    answer = get_llm().invoke(prompt).content
    sources = sorted({
        f"{d.metadata.get('source', '?')} (page {d.metadata.get('page', 0) + 1})"
        for d in docs
    })
    return answer, sources

if __name__ == "__main__":
    history = []
    while True:
        q = input("You: ")
        if q.lower() in ("exit", "quit"):
            break
        a, s = ask(q, history)
        print("\nTutor:", a, "\nSources:", s, "\n")
        history += [{"role": "user", "content": q}, {"role": "assistant", "content": a}]