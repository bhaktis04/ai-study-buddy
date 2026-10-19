from llm import get_llm

def get_interview_question(topic, level="fresher", asked=None):
    asked_text = "\n".join(asked or [])
    prompt = f"""Ask ONE interview question on "{topic}" for a {level} candidate.
Do not repeat any of these earlier questions:
{asked_text}

Return only the question text."""
    return get_llm(temperature=0.7).invoke(prompt).content.strip()

def evaluate_answer(topic, question, answer):
    prompt = f"""You are a friendly interviewer for {topic}.

Question: {question}
Candidate's answer: {answer}

Give feedback in this format:
**Score:** X/10
**What was good:** ...
**What to improve:** ...
**Model answer:** a short ideal answer
"""
    return get_llm(temperature=0.3).invoke(prompt).content