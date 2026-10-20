from pathlib import Path

import streamlit as st

import db
import ui
from ingest import DATA_DIR, build_vectorstore
from interview import evaluate_answer, get_interview_question
from llm import friendly_error
from quiz import generate_quiz
from rag import ask, get_retriever

st.set_page_config(page_title="AI Study Buddy", page_icon="🤖")
ui.load_css()
db.init_db()

PAGES = ["Study Chat", "History", "Quizzes", "Interview Practice"]

# ---------- Session state ----------
st.session_state.setdefault("session_id", None)
st.session_state.setdefault("page", "Study Chat")
st.session_state.setdefault("asked", [])
st.session_state.setdefault("quiz_id", 0)


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


def error_text(e):
    """Readable message for API errors; quiz generation raises its own ValueError."""
    return str(e) if isinstance(e, ValueError) else friendly_error(e)


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

# ---------- Quizzes ----------
elif page == "Quizzes":
    ui.page_header("Quizzes", "Test yourself on any topic.")

    topic = st.text_input("Topic", placeholder="e.g. SQL joins, Python decorators")
    c1, c2 = st.columns(2)
    n = c1.slider("Questions", 3, 10, 5)
    level = c2.selectbox("Level", ["beginner", "intermediate", "advanced"])

    if st.button("Generate quiz", type="primary"):
        if not topic.strip():
            st.warning("Enter a topic first.")
        else:
            with st.spinner("Creating quiz..."):
                try:
                    st.session_state.quiz = generate_quiz(topic.strip(), n, level)
                    st.session_state.quiz_topic = topic.strip()
                    st.session_state.quiz_id += 1
                    st.session_state.quiz_result = None
                except Exception as e:
                    st.error(error_text(e))

    quiz = st.session_state.get("quiz")
    if quiz:
        qid = st.session_state.quiz_id
        st.divider()
        st.subheader(f"Quiz: {st.session_state.quiz_topic}")

        with st.form(f"quiz_form_{qid}"):
            answers = [
                st.radio(f"{i + 1}. {q['question']}", q["options"], index=None, key=f"q{qid}_{i}")
                for i, q in enumerate(quiz)
            ]
            submitted = st.form_submit_button("Submit answers")

        if submitted:
            score = sum(
                1 for i, q in enumerate(quiz) if answers[i] == q["options"][q["answer"]]
            )
            already_saved = (st.session_state.get("quiz_result") or {}).get("qid") == qid
            if not already_saved:
                db.save_quiz_result(st.session_state.quiz_topic, score, len(quiz))
            st.session_state.quiz_result = {"qid": qid, "answers": answers, "score": score}

        result = st.session_state.get("quiz_result")
        if result and result["qid"] == qid:
            for i, q in enumerate(quiz):
                correct = q["options"][q["answer"]]
                chosen = result["answers"][i]
                if chosen == correct:
                    st.success(f"Q{i + 1}: Correct")
                elif chosen is None:
                    st.warning(f"Q{i + 1}: Not answered. Correct answer: {correct}")
                else:
                    st.error(f"Q{i + 1}: Wrong. Correct answer: {correct}")
                st.caption(q["explanation"])
            st.subheader(f"Score: {result['score']}/{len(quiz)}")

# ---------- Interview Practice ----------
else:
    ui.page_header("Interview Practice", "Practice questions and get instant feedback.")

    topic = st.text_input(
        "Topic", placeholder="e.g. Python, SQL, Machine Learning", key="iv_topic"
    )
    level = st.selectbox("Level", ["fresher", "junior", "intermediate"], key="iv_level")

    if st.button("Get a question", type="primary"):
        if not topic.strip():
            st.warning("Enter a topic first.")
        else:
            with st.spinner("Preparing a question..."):
                try:
                    q = get_interview_question(
                        topic.strip(), level, st.session_state.asked
                    )
                    st.session_state.current_q = q
                    st.session_state.current_topic = topic.strip()
                    st.session_state.asked.append(q)
                    st.session_state.feedback = None
                except Exception as e:
                    st.error(error_text(e))

    current_q = st.session_state.get("current_q")
    if current_q:
        st.divider()
        st.subheader(current_q)
        answer = st.text_area(
            "Your answer", height=150, key=f"iv_ans_{len(st.session_state.asked)}"
        )
        if st.button("Get feedback"):
            if not answer.strip():
                st.warning("Write your answer first.")
            else:
                with st.spinner("Evaluating..."):
                    try:
                        st.session_state.feedback = evaluate_answer(
                            st.session_state.current_topic, current_q, answer
                        )
                    except Exception as e:
                        st.error(error_text(e))
        if st.session_state.get("feedback"):
            st.markdown(st.session_state.feedback)