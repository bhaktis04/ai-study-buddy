from rag import get_retriever
from llm import get_llm

def generate_quiz(topic, num_questions=5, level="beginner"):
    docs = get_retriever(k=5).invoke(topic)
    context = "\n\n".join(d.page_content for d in docs)

    prompt = f"""Create {num_questions} multiple-choice questions on "{topic}"
for a {level} learner, based on this material:

{context}

Format each question exactly like this:
Q1. question text
A) ...  B) ...  C) ...  D) ...
Answer: <letter>
Explanation: <one or two lines>
"""
    return get_llm(temperature=0.5).invoke(prompt).content

def generate_interview_questions(topic, num_questions=5):
    prompt = f"""Give {num_questions} commonly asked interview questions on "{topic}"
for a fresher/junior role. For each question, include a short model answer."""
    return get_llm(temperature=0.5).invoke(prompt).content