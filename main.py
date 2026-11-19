from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

import db
from llm import PROVIDER, friendly_error, last_provider
from rag import ask, has_index


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()          # create the SQLite tables on startup
    yield


app = FastAPI(
    title="AI Study Buddy API",
    description="RAG-based tutoring API: chat with your notes, quizzes, mock interviews.",
    version="1.0.0",
    lifespan=lifespan,
)


# ---------- Schemas ----------
class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, examples=["What is a decorator in Python?"])
    session_id: str | None = Field(
        default=None, description="Send the id from an earlier reply to continue that chat."
    )


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    sources: list[str]
    provider: str | None = None


class SessionInfo(BaseModel):
    id: str
    title: str
    created_at: str


class MessageOut(BaseModel):
    role: str
    content: str
    sources: list[str]


def _session_exists(session_id: str) -> bool:
    return any(s[0] == session_id for s in db.list_sessions())


# ---------- Endpoints ----------
@app.get("/health", tags=["System"])
def health():
    """Check that the API is running and whether any notes are indexed."""
    return {"status": "ok", "llm_provider": PROVIDER, "notes_indexed": has_index()}


@app.post("/chat", response_model=ChatResponse, tags=["Chat"])
def chat(req: ChatRequest):
    """Ask a question. Answers come from your indexed notes, with sources."""
    question = req.question.strip()
    if not question:
        raise HTTPException(status_code=422, detail="Question must not be empty.")

    history = []
    if req.session_id:
        if not _session_exists(req.session_id):
            raise HTTPException(status_code=404, detail="Session not found.")
        history = db.get_messages(req.session_id)

    try:
        answer, sources = ask(question, history)
    except Exception as e:
        raise HTTPException(status_code=503, detail=friendly_error(e))

    sid = req.session_id or db.create_session(question[:40])
    db.add_message(sid, "user", question)
    db.add_message(sid, "assistant", answer, sources)
    return ChatResponse(session_id=sid, answer=answer, sources=sources, provider=last_provider())


@app.get("/sessions", response_model=list[SessionInfo], tags=["History"])
def list_sessions():
    """List saved chats, newest first."""
    return [SessionInfo(id=i, title=t, created_at=c) for i, t, c in db.list_sessions()]


@app.get("/sessions/{session_id}", response_model=list[MessageOut], tags=["History"])
def get_session(session_id: str):
    """Return every message in one saved chat."""
    if not _session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found.")
    return db.get_messages(session_id)


@app.delete("/sessions/{session_id}", tags=["History"])
def delete_session(session_id: str):
    """Delete one chat and its messages."""
    if not _session_exists(session_id):
        raise HTTPException(status_code=404, detail="Session not found.")
    db.delete_session(session_id)
    return {"deleted": session_id}