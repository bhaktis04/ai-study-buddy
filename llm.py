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


def friendly_error(e) -> str:
    """Turn an API exception into a short, readable message for the UI."""
    msg = str(e)
    if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
        return ("Gemini's free-tier limit is reached. Wait a while, or set a "
                "different GEMINI_MODEL in .env.")
    if "404" in msg or "NOT_FOUND" in msg:
        return "Model not found. Check GEMINI_MODEL in .env."
    if "API key" in msg or "401" in msg or "403" in msg or "PERMISSION_DENIED" in msg:
        return "There's a problem with your API key. Check GOOGLE_API_KEY in .env."
    return f"Something went wrong ({type(e).__name__}). Try again."


if __name__ == "__main__":
    try:
        print(ask_llm("Explain Python lists in 2 lines."))
    except Exception as e:
        print(friendly_error(e)) 
