import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")


def get_llm(temperature=0.3):
    """Return the Gemini chat model."""
    return ChatGoogleGenerativeAI(model=MODEL_NAME, temperature=temperature)


def to_text(response) -> str:
    """Extract plain text from a model response (handles string or block-list content)."""
    content = response.content
    if isinstance(content, str):
        return content
    parts = []
    for block in content:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict) and block.get("type") == "text":
            parts.append(block.get("text", ""))
    return "".join(parts)


def ask_llm(prompt: str, temperature: float = 0.3) -> str:
    """Send a prompt and return the answer as plain text."""
    return to_text(get_llm(temperature).invoke(prompt))


if __name__ == "__main__":
    print(ask_llm("Explain Python set in 2 lines."))