import streamlit as st
from pathlib import Path

import db
from ingest import build_vectorstore, DATA_DIR
from rag import ask
from quiz import generate_quiz
from interview import get_interview_question, evaluate_answer

st.set_page_config(page_title="AI Study Buddy", page_icon="📚")
db.init_db()

# ---------- State ----------
st.session_state.setdefault("session_id", None)
st.session_state.setdefault("page", "Study Chat")
st.session_state.setdefault("asked", [])

def open_session(sid):
    st.session_state.session_id = sid
    st.session_state.page = "Study Chat"

def new_chat():
    st.session_state.session_id = None
    st.session_state.page = "Study Chat"

# ---------- Sidebar ----------
with st.sidebar:
    st.title("📚 AI Study Buddy")
    st.radio("Go to", ["Study Chat", "History", "Quizzes", "Interview Practice"], key="page")
    st.button("➕ New chat", on_click=new_chat)

    st.divider()
    st.subheader("Study material")
    uploaded = st.file_uploader("Upload PDFs or notes", type=["pdf", "txt", "md"],
                                accept_multiple_files=True)
    if st.button("Process documents") and uploaded:
        Path(DATA_DIR).mkdir(exist_ok=True)
        for f in uploaded:
            (Path(DATA_DIR) / f.name).write_bytes(f.getbuffer())
        with st.spinner("Reading and indexing..."):
            pages, chunks = build_vectorstore()
        st.success(f"Indexed {pages} pages into {chunks} chunks")

page = st.session_state.page

# ---------- Study Chat ----------
if page == "Study Chat":
    st.header("Study Chat")
    sid = st.session_state.session_id
    messages = db.get_messages(sid) if sid else []

    for m in messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
            if m["sources"]:
                with st.expander("Sources"):
                    for s in m["sources"]:
                        st.write("•", s)

    if question := st.chat_input("Ask anything from your notes..."):
        if sid is None:
            sid = db.create_session(question[:40])
            st.session_state.session_id = sid
        with st.chat_message("user"):
            st.markdown(question)
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                answer, sources = ask(question, messages)
            st.markdown(answer)
            with st.expander("Sources"):
                for s in sources:
                    st.write("•", s)
        db.add_message(sid, "user", question)
        db.add_message(sid, "assistant", answer, sources)

# ---------- History ----------
elif page == "History":
    st.header("Chat History")
    sessions = db.list_sessions()
    if not sessions:
        st.info("No saved chats yet.")
    for sid, title, created in sessions:
        c1, c2, c3 = st.columns([5, 1.5, 1])
        c1.write(f"**{title}**  \n{created}")
        c2.button("Open", key=f"open_{sid}", on_click=open_session, args=(sid,))
        if c3.button("🗑", key=f"del_{sid}"):
            db.delete_session(sid)
            st.rerun()

    st.subheader("Quiz scores")
    for topic, score, total, when in db.get_quiz_results():
        st.write(f"{when} — {topic}: **{score}/{total}**")

# ---------- Quizzes ----------
elif page == "Quizzes":
    st.header("Quiz")
    topic = st.text_input("Topic (e.g. SQL joins, Python decorators)")
    c1, c2 = st.columns(2)
    n = c1.slider("Questions", 3, 10, 5)
    level = c2.selectbox("Level", ["beginner", "intermediate", "advanced"])

    if st.button("Generate quiz") and topic:
        with st.spinner("Creating quiz..."):
            try:
                st.session_state.quiz = generate_quiz(topic, n, level)
                st.session_state.quiz_topic = topic
            except Exception as e:
                st.error(f"Could not generate a valid quiz, please try again. ({e})")

    quiz = st.session_state.get("quiz")
    if quiz:
        with st.form("quiz_form"):
            answers = [
                st.radio(f"{i+1}. {q['question']}", q["options"], index=None, key=f"q{i}")
                for i, q in enumerate(quiz)
            ]
            submitted = st.form_submit_button("Submit answers")

        if submitted:
            score = 0
            for i, q in enumerate(quiz):
                correct = q["options"][q["answer"]]
                if answers[i] == correct:
                    score += 1
                    st.success(f"Q{i+1}: Correct")
                else:
                    st.error(f"Q{i+1}: Wrong. Correct answer: {correct}")
                st.caption(q["explanation"])
            st.subheader(f"Score: {score}/{len(quiz)}")
            db.save_quiz_result(st.session_state.quiz_topic, score, len(quiz))

# ---------- Interview Practice ----------
else:
    st.header("Interview Practice")
    topic = st.text_input("Topic (e.g. Machine Learning, LangChain, SQL)")

    if st.button("Get a question") and topic:
        with st.spinner("Preparing..."):
            q = get_interview_question(topic, asked=st.session_state.asked)
        st.session_state.current_q = q
        st.session_state.asked.append(q)
        st.session_state.feedback = None

    if st.session_state.get("current_q"):
        st.subheader(st.session_state.current_q)
        answer = st.text_area("Your answer", height=150)
        if st.button("Get feedback") and answer.strip():
            with st.spinner("Evaluating..."):
                st.session_state.feedback = evaluate_answer(
                    topic, st.session_state.current_q, answer)
        if st.session_state.get("feedback"):
            st.markdown(st.session_state.feedback)