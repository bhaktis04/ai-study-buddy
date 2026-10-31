import re

from llm import ask_llm, friendly_error

NEXT_MARKER = "===NEXT==="


def get_interview_question(topic, level="fresher", asked=None):
    """Ask ONE interview question, avoiding ones that were already asked."""
    asked_text = "\n".join(f"- {q}" for q in (asked or [])) or "(none yet)"
    prompt = f"""Ask ONE interview question on "{topic}" for a {level} candidate.
Do not repeat any of these earlier questions:
{asked_text}

Return only the question text, with no numbering and no extra words."""
    return ask_llm(prompt, temperature=0.7).strip()


def evaluate_answer(topic, question, answer):
    """Score a single answer out of 10 and give feedback."""
    prompt = f"""You are a friendly but honest interviewer for {topic}.

Question: {question}
Candidate's answer: {answer}

Give feedback in exactly this format, in under 150 words:
**Score:** X/10
**What was good:** ...
**What to improve:** ...
**Model answer:** a short ideal answer
"""
    return ask_llm(prompt, temperature=0.3)


def _parse_score(text):
    m = re.search(r"Score:\W*(\d+(?:\.\d+)?)\s*/\s*10", text, re.IGNORECASE)
    if not m:
        return None
    return max(0.0, min(10.0, float(m.group(1))))


def evaluate_and_next(topic, level, question, answer, asked):
    """Feedback on the answer AND the next question, in one Gemini request.

    Returns a dict: feedback (str), next_question (str), score (float or None).
    """
    asked_text = "\n".join(f"- {q}" for q in asked) or "(none)"
    prompt = f"""You are a friendly but honest interviewer for {topic} ({level} level).

Question: {question}
Candidate's answer: {answer}

Reply in exactly this format:
**Score:** X/10
**What was good:** ...
**What to improve:** ...
**Model answer:** a short ideal answer
{NEXT_MARKER}
One NEW interview question on {topic}. Do not repeat any of these:
{asked_text}
Write only the question text after the marker, with no label or numbering.
Keep the feedback part under 150 words.
"""
    raw = ask_llm(prompt, temperature=0.4)
    feedback, _, next_q = raw.partition(NEXT_MARKER)
    feedback = feedback.strip()
    next_q = re.sub(r"^(next question|question)\s*\d*\s*[:\-]\s*", "", next_q.strip(),
                    flags=re.IGNORECASE)

    if not next_q:  # the model skipped the marker, so ask for a question separately
        next_q = get_interview_question(topic, level, asked)

    return {"feedback": feedback, "next_question": next_q, "score": _parse_score(feedback)}


if __name__ == "__main__":
    topic = input("Topic (e.g. Python, SQL, Machine Learning): ").strip() or "Python"
    level = "fresher"
    try:
        question = get_interview_question(topic, level)
    except Exception as e:
        print(friendly_error(e))
        raise SystemExit
    asked = [question]

    while True:
        print("\nQuestion:", question)
        answer = input("Your answer ('skip' or 'exit'): ").strip()
        if answer.lower() in ("exit", "quit"):
            break
        if not answer:
            continue
        try:
            if answer.lower() == "skip":
                question = get_interview_question(topic, level, asked)
            else:
                result = evaluate_and_next(topic, level, question, answer, asked)
                print("\n" + result["feedback"])
                question = result["next_question"]
        except Exception as e:
            print("\n" + friendly_error(e))
            continue
        asked.append(question)