# 📚 AI Study Buddy: Your Personal AI Tutor

> **Status: 🚧 In progress.** See the [Project Status](#project-status) checklist below.

AI Study Buddy is a RAG-based tutoring chatbot that answers questions from a student's own notes and PDFs, generates interactive quizzes, runs mock interview practice with feedback, and saves chat history, helping learners study faster with accurate, source-backed explanations.

**Live demo:** _coming soon_  
**Demo GIF:** _coming soon_

---

## Table of Contents

- [Problem Statement](#problem-statement)
- [Features](#features)
- [How It Works](#how-it-works)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Setup and Installation](#setup-and-installation)
- [Usage](#usage)
- [Evaluation Results](#evaluation-results)
- [Design Decisions](#design-decisions)
- [Limitations](#limitations)
- [Project Status](#project-status)
- [Future Improvements](#future-improvements)
- [Author](#author)

---

## Problem Statement

Students learning Python, SQL, Machine Learning and Generative AI face recurring problems:

- **Scattered material:** notes, PDFs and tutorials live in many places.
- **Generic AI answers:** general chatbots don't know the student's own notes and may hallucinate.
- **No active practice:** reading alone is not enough, and writing quizzes by hand takes time.
- **No continuity:** most tools forget past conversations.
- **Hard to understand:** documentation is often written for experts, not beginners.

AI Study Buddy grounds every answer in the student's uploaded documents using Retrieval-Augmented Generation (RAG), shows the sources, and adds quizzes, interview practice and saved history.

## Features

- 💬 **Study Chat:** answers from your own notes, with source file and page
- 🧠 **Conversation memory:** follow-ups like "give me an example" work
- 🗂️ **Chat history:** all chats saved in SQLite; reopen or delete them
- 📝 **Interactive quizzes:** LLM-generated multiple-choice questions with scoring and explanations
- 🎤 **Interview practice:** get a question, type an answer, receive a score and feedback
- 📊 **Quiz score history**
- 📄 **Supports PDF, TXT and MD files**

## How It Works

```
┌──────────────────────────────────────────────────────────┐
│            AI Study Buddy: Streamlit app                 │
│    Study Chat · History · Quizzes · Interview Practice   │
└──────────────────────────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
   Study chatbot     Quizzes / Interview   Chat history
   (RAG + Gemini)    (LLM-generated)        (SQLite)
        │
        ▼
 LangChain · Gemini · ChromaDB · SQLite
```

**Indexing** (when you click "Process documents"):

```
PDF/TXT/MD → load text → split into chunks → embeddings → store in ChromaDB
```

**Answering** (every question):

```
Question → embed → find similar chunks in ChromaDB
         → prompt = rules + recent chat + context + question
         → Gemini → answer + sources → shown in UI and saved in SQLite
```

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.10+ |
| Frontend | Streamlit |
| LLM | Google Gemini via `langchain-google-genai` |
| Orchestration | LangChain |
| Embeddings | HuggingFace `all-MiniLM-L6-v2` (runs locally) |
| Vector database | ChromaDB |
| Chat storage | SQLite |

## Project Structure

```
ai-study-buddy/
├── data/
│   └── sample/            # small public sample notes for demo/testing
├── eval/
│   └── questions.json     # evaluation questions with expected keywords
├── tests/                 # pytest tests
├── screenshots/           # images used in this README
├── llm.py                 # Gemini connection
├── ingest.py              # load, chunk, embed, store in ChromaDB
├── rag.py                 # retrieval + answer generation
├── db.py                  # SQLite chat history and quiz scores
├── quiz.py                # JSON quiz generation
├── interview.py           # interview questions + feedback
├── app.py                 # Streamlit UI
├── requirements.txt
├── .env.example           # template for your API key
├── .gitignore
└── README.md
```

Auto-created at runtime (not committed): `chroma_db/`, `study_buddy.db`.

## Setup and Installation

### Prerequisites

- Python 3.10 or higher (3.11 or 3.12 recommended)
- A free Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey)

### Steps

```bash
# 1. Clone
git clone https://github.com/<your-username>/ai-study-buddy.git
cd ai-study-buddy

# 2. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Mac / Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Add your API key
copy .env.example .env         # Windows
# cp .env.example .env         # Mac / Linux
# then open .env and set GOOGLE_API_KEY=your_key_here

# 5. Run
streamlit run app.py
```

The app opens at `http://localhost:8501`. The first run downloads the embedding model, which takes a minute.

## Usage

1. **Upload material:** in the sidebar, upload PDFs or notes and click **Process documents**.
2. **Study Chat:** ask a question from your notes, then a follow-up.
3. **History:** reopen or delete earlier chats and view quiz scores.
4. **Quizzes:** enter a topic, choose level and number of questions, then submit for your score.
5. **Interview Practice:** enter a topic, get a question, answer it, and read the feedback.

## Evaluation Results

_To be filled in after running `eval/eval.py`. Only measured numbers go here._

| Setup | Retrieval hit rate | Keyword coverage |
|---|---|---|
| No RAG (pure LLM) | n/a | TBD |
| RAG, chunk 500, k=3 | TBD | TBD |
| RAG, chunk 800, k=4 | TBD | TBD |
| RAG + MMR | TBD | TBD |

## Design Decisions 

_To be filled in as the project is built._

- **Chunk size and overlap:** TBD
- **Embedding model:** TBD
- **Why SQLite:** TBD
- **Why MMR retrieval:** TBD

## Limitations

- Scanned (image-only) PDFs are not supported; no OCR yet
- Single-user app, no login
- Depends on the Gemini API (rate limits apply on the free tier)
- Conversation memory keeps only the last few messages

## Project Status

- [ ] Project setup (folders, venv, dependencies)
- [ ] LLM connection (`llm.py`)
- [ ] Document ingestion + ChromaDB (`ingest.py`)
- [ ] RAG answering with memory (`rag.py`)
- [ ] SQLite chat history (`db.py`)
- [ ] Quiz generator (`quiz.py`)
- [ ] Interview practice (`interview.py`)
- [ ] Streamlit UI (`app.py`)
- [ ] Streaming, retries, MMR retrieval
- [ ] Evaluation set and results
- [ ] Tests
- [ ] Deployment on Streamlit Community Cloud
- [ ] Screenshots and demo GIF

## Future Improvements

- OCR support for scanned PDFs
- Reranking for better retrieval
- Switch LLM provider (Groq, Ollama) by editing `llm.py` only
- Progress dashboard with charts
- Multi-user login
- Voice input

## Author

**Your Name**  
[GitHub](https://github.com/your-username) · [LinkedIn](https://linkedin.com/in/your-profile)
