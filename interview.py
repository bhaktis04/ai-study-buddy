from llm import ask_llm


def get_interview_question(topic, level="fresher", asked=None):
    """Ask ONE interview question, avoiding ones that were already asked."""
    asked_text = "\n".join(f"- {q}" for q in (asked or [])) or "(none yet)"
    prompt = f"""Ask ONE interview question on "{topic}" for a {level} candidate.
Do not repeat any of these earlier questions:
{asked_text}

Return only the question text, with no numbering and no extra words."""
    return ask_llm(prompt, temperature=0.7).strip()


def evaluate_answer(topic, question, answer):
    """Score the candidate's answer out of 10 and give feedback."""
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


def friendly_error(e):
    """Turn an API exception into a short message instead of a long traceback."""
    msg = str(e)
    if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
        return ("Gemini free-tier limit reached. Wait a while, or set a different "
                "GEMINI_MODEL in .env.")
    if "404" in msg or "NOT_FOUND" in msg:
        return "Model not found. Check GEMINI_MODEL in .env."
    return f"Something went wrong ({type(e).__name__}). Try again."


if __name__ == "__main__":
    topic = input("Topic (e.g. Python, SQL, Machine Learning): ").strip() or "Python"
    asked = []
    question = None

    while True:
        # Only ask Gemini for a new question when we don't have one pending
        if question is None:
            try:
                question = get_interview_question(topic, asked=asked)
            except Exception as e:
                print("\n" + friendly_error(e))
                break
            asked.append(question)
            print("\nQuestion:", question)

        answer = input("Your answer ('skip' for a new question, 'exit' to quit): ").strip()

        if answer.lower() in ("exit", "quit"):
            break
        if answer.lower() == "skip":
            question = None
            continue
        if not answer:          # empty Enter costs nothing and asks nothing
            continue

        try:
            print("\n" + evaluate_answer(topic, question, answer) + "\n")
        except Exception as e:
            print("\n" + friendly_error(e))
            continue            # keep the same question so you can retry the answer
        question = None 