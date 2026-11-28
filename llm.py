# import os
# import time

# from dotenv import load_dotenv
# from langchain_google_genai import ChatGoogleGenerativeAI

# load_dotenv()

# # LLM_PROVIDER: "gemini" (default), "ollama", or "auto" (Gemini first, Ollama if Gemini fails)
# PROVIDER = os.getenv("LLM_PROVIDER", "gemini").strip().lower()
# GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
# OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
# OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
# MODEL_NAME = GEMINI_MODEL

# GEMINI_TIMEOUT = 20          # seconds to wait for Gemini in auto mode
# GEMINI_COOLDOWN = 600        # after a failure, skip Gemini for this many seconds

# _last_provider = {"name": None}
# _gemini_down_until = {"t": 0.0}


# def _gemini(temperature, fast=False):
#     """Gemini model. fast=True fails quickly instead of retrying for a long time."""
#     if fast:
#         return ChatGoogleGenerativeAI(
#             model=GEMINI_MODEL, temperature=temperature,
#             max_retries=1, timeout=GEMINI_TIMEOUT,
#         )
#     return ChatGoogleGenerativeAI(model=GEMINI_MODEL, temperature=temperature)


# def _ollama(temperature):
#     from langchain_ollama import ChatOllama   # imported only when needed

#     # num_ctx is raised because RAG prompts (notes + history) are longer than the default
#     return ChatOllama(
#         model=OLLAMA_MODEL, temperature=temperature, base_url=OLLAMA_URL, num_ctx=4096
#     )


# def get_llm(temperature=0.3):
#     """Return the chat model for the configured provider."""
#     return _ollama(temperature) if PROVIDER == "ollama" else _gemini(temperature)


# def to_text(response) -> str:
#     """Extract plain text from a model response (handles string or block-list content)."""
#     content = response.content
#     if isinstance(content, str):
#         return content
#     parts = []
#     for block in content:
#         if isinstance(block, str):
#             parts.append(block)
#         elif isinstance(block, dict) and block.get("type") == "text":
#             parts.append(block.get("text", ""))
#     return "".join(parts)


# def ask_llm(prompt: str, temperature: float = 0.3) -> str:
#     """Send a prompt and return plain text, using the configured provider."""
#     if PROVIDER == "ollama":
#         text = to_text(_ollama(temperature).invoke(prompt))
#         _last_provider["name"] = "ollama"
#         return text

#     if PROVIDER == "auto":
#         if time.time() >= _gemini_down_until["t"]:
#             try:
#                 text = to_text(_gemini(temperature, fast=True).invoke(prompt))
#                 _last_provider["name"] = "gemini"
#                 return text
#             except Exception:
#                 # Gemini failed (quota, key, network): skip it for a while
#                 _gemini_down_until["t"] = time.time() + GEMINI_COOLDOWN
#         text = to_text(_ollama(temperature).invoke(prompt))
#         _last_provider["name"] = "ollama"
#         return text

#     text = to_text(_gemini(temperature).invoke(prompt))
#     _last_provider["name"] = "gemini"
#     return text


# def last_provider():
#     """Name of the provider that answered the most recent call."""
#     return _last_provider["name"]


# def friendly_error(e) -> str:
#     """Turn an API exception into a short, readable message for the UI."""
#     msg = str(e)
#     low = msg.lower()
#     if "connecterror" in low or "connection refused" in low or "actively refused" in low \
#             or "failed to connect" in low:
#         return "Can't reach Ollama. Start the Ollama app (or run 'ollama serve') and try again."
#     if "try pulling it first" in low or "ollama" in low:
#         return f"Ollama model problem. Run: ollama pull {OLLAMA_MODEL}"
#     if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
#         return ("Gemini's free-tier limit is reached. Wait a while, set LLM_PROVIDER=auto "
#                 "to fall back to Ollama, or set a different GEMINI_MODEL in .env.")
#     if "404" in msg or "NOT_FOUND" in msg:
#         return "Model not found. Check GEMINI_MODEL in .env."
#     if "API key" in msg or "401" in msg or "403" in msg or "PERMISSION_DENIED" in msg:
#         return "There's a problem with your API key. Check GOOGLE_API_KEY in .env."
#     return f"Something went wrong ({type(e).__name__}): {msg[:150]}"


# if __name__ == "__main__":
#     start = time.time()
#     try:
#         print(ask_llm("Explain Python lists in 2 lines."))
#         print(f"\n[{last_provider()} answered in {time.time() - start:.1f}s]")
#     except Exception as e:
#         print(friendly_error(e))




import os
import time

from dotenv import load_dotenv

load_dotenv()

# LLM_PROVIDER: "gemini", "groq", "ollama", or "auto" (try each configured provider in turn)
PROVIDER = os.getenv("LLM_PROVIDER", "gemini").strip().lower()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
MODEL_NAME = GEMINI_MODEL

CLOUD_TIMEOUT = 20        # seconds to wait for a cloud provider in auto mode
COOLDOWN = 600            # after a failure, skip that provider for this many seconds

_last_provider = {"name": None}
_down_until = {}


def _gemini(temperature, fast=False):
    from langchain_google_genai import ChatGoogleGenerativeAI

    kwargs = dict(model=GEMINI_MODEL, temperature=temperature)
    if fast:
        kwargs.update(max_retries=1, timeout=CLOUD_TIMEOUT)
    return ChatGoogleGenerativeAI(**kwargs)


def _groq(temperature, fast=False):
    from langchain_groq import ChatGroq   # reads GROQ_API_KEY from the environment

    kwargs = dict(model=GROQ_MODEL, temperature=temperature)
    if fast:
        kwargs.update(max_retries=1, timeout=CLOUD_TIMEOUT)
    return ChatGroq(**kwargs)


def _ollama(temperature, fast=False):
    from langchain_ollama import ChatOllama

    # num_ctx is raised because RAG prompts (notes + history) are longer than the default
    return ChatOllama(
        model=OLLAMA_MODEL, temperature=temperature, base_url=OLLAMA_URL, num_ctx=4096
    )


BUILDERS = {"gemini": _gemini, "groq": _groq, "ollama": _ollama}


def _has_key(name):
    if name == "groq":
        return bool(os.getenv("GROQ_API_KEY"))
    if name == "gemini":
        return bool(os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"))
    return True   # ollama needs no key


def _auto_order():
    return [p for p in ("groq", "gemini", "ollama") if _has_key(p)]


def get_llm(temperature=0.3):
    """Return the chat model for the configured provider."""
    name = PROVIDER if PROVIDER in BUILDERS else _auto_order()[0]
    return BUILDERS[name](temperature)


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


def _invoke(name, prompt, temperature, fast=False):
    text = to_text(BUILDERS[name](temperature, fast).invoke(prompt))
    _last_provider["name"] = name
    return text


def ask_llm(prompt: str, temperature: float = 0.3) -> str:
    """Send a prompt and return plain text, using the configured provider."""
    if PROVIDER in BUILDERS:
        return _invoke(PROVIDER, prompt, temperature)

    # auto mode: try each provider that has a key, skipping ones that failed recently
    order = _auto_order()
    candidates = [n for n in order if time.time() >= _down_until.get(n, 0)] or order
    last_error = None
    for name in candidates:
        try:
            return _invoke(name, prompt, temperature, fast=(name != "ollama"))
        except Exception as e:
            last_error = e
            _down_until[name] = time.time() + COOLDOWN
    raise last_error


def last_provider():
    """Name of the provider that answered the most recent call."""
    return _last_provider["name"]


def friendly_error(e) -> str:
    """Turn an API exception into a short, readable message for the UI."""
    msg = str(e)
    low = msg.lower()
    if "connecterror" in low or "connection refused" in low or "actively refused" in low \
            or "failed to connect" in low:
        return "Can't reach Ollama. Start the Ollama app (or run 'ollama serve') and try again."
    if "try pulling it first" in low:
        return f"Ollama model problem. Run: ollama pull {OLLAMA_MODEL}"
    if "invalid_api_key" in low or "invalid api key" in low:
        return "The API key was rejected. Check GROQ_API_KEY or GOOGLE_API_KEY in .env."
    if "429" in msg or "RESOURCE_EXHAUSTED" in msg or "rate limit" in low:
        return ("The provider's rate limit is reached. Wait a moment, or switch "
                "LLM_PROVIDER in .env (groq, gemini, ollama or auto).")
    if "404" in msg or "NOT_FOUND" in msg or "model_not_found" in low:
        return "Model not found. Check GROQ_MODEL, GEMINI_MODEL or OLLAMA_MODEL in .env."
    if "API key" in msg or "401" in msg or "403" in msg or "PERMISSION_DENIED" in msg:
        return "There's a problem with your API key. Check the key lines in .env."
    return f"Something went wrong ({type(e).__name__}): {msg[:150]}"


if __name__ == "__main__":
    start = time.time()
    try:
        print(ask_llm("Explain Python lists in 2 lines."))
        print(f"\n[{last_provider()} answered in {time.time() - start:.1f}s]")
    except Exception as e:
        print(friendly_error(e))