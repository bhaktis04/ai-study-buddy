from pathlib import Path

import streamlit as st

import db
import ui
from docs_page import render_documents_page
from ingest import DATA_DIR, add_files
from interview import evaluate_and_next, get_interview_question
from llm import friendly_error
from quiz import generate_quiz
from rag import ask, get_retriever, has_index
from report import build_markdown, build_pdf, report_filename

st.set_page_config(page_title="AI Study Buddy", page_icon="🤖")
ui.load_css()
db.init_db()

PAGES = ["Study Chat", "History", "Quizzes", "Interview Practice", "Documents"]

# ---------- Session state ----------
st.session_state.setdefault("session_id", None)
st.session_state.setdefault("page", "Study Chat")
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
            saved = []
            for f in uploaded:
                target = Path(DATA_DIR) / f.name
                target.write_bytes(f.getbuffer())
                saved.append(str(target))
            with st.spinner("Reading and indexing..."):
                results = add_files(saved)
            get_retriever.cache_clear()
            for r in results:
                if r.get("error"):
                    st.error(f"{r['name']}: could not be read ({r['error']})")
                elif r["chunks"] == 0:
                    st.warning(f"{r['name']}: no readable text found (a scanned PDF?).")
                else:
                    st.success(f"{r['name']}: {r['pages']} pages, {r['chunks']} chunks")

page = st.session_state.page

if page in ("Study Chat", "Quizzes") and not has_index():
    st.warning(
        "No study notes indexed yet. Upload a file in the sidebar and click "
        "'Process documents' to get answers from your own material. "
        "Until then, answers come from general knowledge."
    )

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

    st.subheader("Quiz and interview scores")
    results = db.get_quiz_results()
    if not results:
        st.caption("No attempts yet.")
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

# ---------- Documents ----------
elif page == "Documents":
    render_documents_page()

# ---------- Interview Practice ----------
else:
    ui.page_header(
        "Interview Practice",
        "A mock interview: answer in the chat and get feedback on every reply.",
    )
    ss = st.session_state
    ss.setdefault("iv_active", False)
    ss.setdefault("iv_done", False)
    ss.setdefault("iv_msgs", [])
    ss.setdefault("iv_asked", [])
    ss.setdefault("iv_scores", [])
    ss.setdefault("iv_log", [])
    ss.setdefault("iv_saved", False)

    # ----- 1. Setup -----
    if not ss.iv_active and not ss.iv_done:
        topic = st.text_input(
            "Topic", placeholder="e.g. Python, SQL, Machine Learning", key="iv_topic_input"
        )
        level = st.selectbox("Level", ["fresher", "junior", "intermediate"], key="iv_level_input")

        if st.button("Start interview", type="primary"):
            if not topic.strip():
                st.warning("Enter a topic first.")
            else:
                with st.spinner("Your interviewer is getting ready..."):
                    try:
                        q = get_interview_question(topic.strip(), level)
                    except Exception as e:
                        st.error(error_text(e))
                        st.stop()
                ss.iv_topic, ss.iv_level = topic.strip(), level
                ss.iv_question = q
                ss.iv_asked = [q]
                ss.iv_scores = []
                ss.iv_log = []
                ss.iv_saved = False
                ss.iv_msgs = [{
                    "role": "assistant",
                    "content": f"Hi! I'll be your interviewer for **{ss.iv_topic}**. "
                               f"Let's begin.\n\n**Question 1:** {q}",
                }]
                ss.iv_active = True
                st.rerun()

    # ----- 2. Live interview chat -----
    elif ss.iv_active:
        c1, c2, c3 = st.columns([3, 1.3, 1.3])
        c1.caption(f"{ss.iv_topic} · {ss.iv_level} · {len(ss.iv_scores)} answered")

        if c2.button("Skip question"):
            with st.spinner("Finding another question..."):
                try:
                    q = get_interview_question(ss.iv_topic, ss.iv_level, ss.iv_asked)
                except Exception as e:
                    st.error(error_text(e))
                    st.stop()
            ss.iv_question = q
            ss.iv_asked.append(q)
            ss.iv_msgs.append({
                "role": "assistant",
                "content": f"No problem, here's another one.\n\n"
                           f"**Question {len(ss.iv_asked)}:** {q}",
            })
            st.rerun()

        if c3.button("End interview"):
            ss.iv_active = False
            ss.iv_done = True
            st.rerun()

        for m in ss.iv_msgs:
            with st.chat_message(m["role"]):
                st.markdown(m["content"])

        if answer := st.chat_input("Type your answer..."):
            with st.chat_message("user"):
                st.markdown(answer)
            with st.chat_message("assistant"):
                with st.spinner("Evaluating..."):
                    try:
                        result = evaluate_and_next(
                            ss.iv_topic, ss.iv_level, ss.iv_question, answer, ss.iv_asked
                        )
                    except Exception as e:
                        st.error(error_text(e))
                        st.stop()
                number = len(ss.iv_asked) + 1
                reply = f"{result['feedback']}\n\n---\n**Question {number}:** {result['next_question']}"
                st.markdown(reply)

            ss.iv_msgs += [
                {"role": "user", "content": answer},
                {"role": "assistant", "content": reply},
            ]
            if result["score"] is not None:
                ss.iv_scores.append((ss.iv_question, result["score"]))
            ss.iv_log.append({
                "question": ss.iv_question,
                "answer": answer,
                "feedback": result["feedback"],
                "score": result["score"],
            })
            ss.iv_question = result["next_question"]
            ss.iv_asked.append(result["next_question"])

    # ----- 3. Summary -----
    else:
        scores = ss.iv_scores
        st.subheader("Interview summary")
        if not scores:
            st.info("You ended the interview before answering any question.")
        else:
            total = sum(s for _, s in scores)
            avg = total / len(scores)
            if not ss.iv_saved:
                db.save_quiz_result(f"Interview: {ss.iv_topic}", round(total), 10 * len(scores))
                ss.iv_saved = True

            m1, m2 = st.columns(2)
            m1.metric("Average score", f"{avg:.1f}/10")
            m2.metric("Questions answered", len(scores))
            for i, (q, s) in enumerate(scores, 1):
                st.write(f"{i}. {q} — **{s:g}/10**")

            if avg >= 8:
                st.success("Strong performance. Keep practising harder questions.")
            elif avg >= 5:
                st.info("Good start. Review the model answers and try again.")
            else:
                st.warning("Needs more practice. Revisit your notes on this topic.")

        if ss.iv_log:
            st.divider()
            st.subheader("Download your report")
            d1, d2 = st.columns(2)
            d1.download_button(
                "Download Markdown",
                data=build_markdown(ss.iv_topic, ss.iv_level, ss.iv_log).encode("utf-8"),
                file_name=report_filename(ss.iv_topic, "md"),
                mime="text/markdown",
                key="dl_md",
            )
            try:
                d2.download_button(
                    "Download PDF",
                    data=build_pdf(ss.iv_topic, ss.iv_level, ss.iv_log),
                    file_name=report_filename(ss.iv_topic, "pdf"),
                    mime="application/pdf",
                    key="dl_pdf",
                )
            except Exception as e:
                d2.error(f"PDF unavailable: {e}")

        if st.button("Start a new interview", type="primary"):
            ss.iv_active = False
            ss.iv_done = False
            ss.iv_msgs, ss.iv_asked, ss.iv_scores, ss.iv_log = [], [], [], []
            ss.iv_saved = False
            st.rerun()