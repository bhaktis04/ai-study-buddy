import json
import re

from llm import ask_llm
from rag import get_retriever

REQUIRED_KEYS = {"question", "options", "answer", "explanation"}


def _parse_json(raw):
    """Remove code fences and extract the JSON list from the model's reply."""
    raw = re.sub(r"```(?:json)?", "", raw).strip()
    start, end = raw.find("["), raw.rfind("]")
    if start != -1 and end != -1:
        raw = raw[start:end + 1]
    return json.loads(raw)


def _validate(quiz):
    """Keep only well-formed questions: 4 options and an answer index from 0 to 3."""
    clean = []
    for q in quiz:
        if not isinstance(q, dict) or not REQUIRED_KEYS <= q.keys():
            continue
        answer = q["answer"]
        if isinstance(answer, str) and answer.strip().isdigit():
            answer = int(answer)
        if (
            isinstance(q["options"], list)
            and len(q["options"]) == 4
            and isinstance(answer, int)
            and 0 <= answer <= 3
        ):
            clean.append({**q, "answer": answer})
    if not clean:
        raise ValueError("The response had no valid questions.")
    return clean


def generate_quiz(topic, num_questions=5, level="beginner", retries=3):
    """Return a list of dicts: question, options (4), answer (index), explanation."""
    docs = get_retriever(k=5).invoke(topic)
    context = "\n\n".join(d.page_content for d in docs)

    prompt = f"""Create {num_questions} multiple-choice questions on "{topic}"
for a {level} learner. Base them on this material from the student's notes.
If the material doesn't cover the topic, use your general knowledge instead.

MATERIAL:
{context}

Return ONLY a valid JSON list, with no extra text and no markdown fences.
Each item must have exactly these keys:
"question": string,
"options": list of exactly 4 strings,
"answer": integer index (0-3) of the correct option,
"explanation": short string
"""

    last_error = None
    for _ in range(retries):
        try:
            raw = ask_llm(prompt, temperature=0.5)
            return _validate(_parse_json(raw))
        except (json.JSONDecodeError, ValueError, KeyError) as e:
            last_error = e
    raise ValueError(f"Could not generate a valid quiz after {retries} tries: {last_error}")


if __name__ == "__main__":
    quiz = generate_quiz("Python decorators", 3)
    for i, q in enumerate(quiz, 1):
        print(f"\nQ{i}. {q['question']}")
        for j, opt in enumerate(q["options"]):
            print(f"  {'ABCD'[j]}) {opt}")
        print(f"Answer: {'ABCD'[q['answer']]}  |  {q['explanation']}")