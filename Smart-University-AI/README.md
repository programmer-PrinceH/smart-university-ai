# Smart University AI

An AI study assistant for university students, built in Python with Streamlit.
It was built for the CAT of **ITLPA701 - Python and Fundamentals of AI** (RP Ngoma College).

**AI approach:** Retrieval-Augmented Generation (RAG) with a pretrained LLM
(no model is trained from scratch). Chat and the Python Assistant use the same LLM without retrieval.

## The five features

| # | Feature | What it does |
|---|---|---|
| 1 | **AI Chat** | Academic Q&A with conversation memory and streaming answers. Conversations are saved (SQLite). |
| 2 | **Ask My Documents** | Upload PDFs, ask questions, get answers grounded in the PDF with the **real document name and page number**. Says so when the answer is not in the documents. |
| 3 | **Summarize PDF** | Six-section study summary (overview, topics, key points, definitions, concepts, conclusion). Long PDFs are summarised section by section (map-reduce). |
| 4 | **Generate Quiz** | 5/10/15 multiple-choice questions (Easy/Medium/Hard) from a PDF, one at a time, then score, percentage, explanations and source page. |
| 5 | **Python Assistant** | Explains code, debugs errors (what it means, why, how to fix, corrected code, explanation) with syntax highlighting. |

## Quick start (Windows PowerShell)

```powershell
# 1. Python 3.11 or 3.12 is recommended (check: python --version)
cd Smart-University-AI
python -m venv venv
.\venv\Scripts\Activate.ps1

# 2. Install (the first install is large: it includes PyTorch)
python -m pip install --upgrade pip
pip install -r requirements.txt

# 3. Configure your API key
copy .env.example .env
notepad .env        # replace your_key_here with your key
```

`.env` needs three lines (these defaults are for Google Gemini):

```
LLM_API_KEY=your_key_here
LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
LLM_MODEL=gemini-3.7-flash
```

Any OpenAI-compatible provider works (for example Groq: change the base URL and model name).
Model names change often; copy a current one from your provider if you get "model not found".

```powershell
# 4. Run
streamlit run app.py
```

The first time you upload a PDF, the embedding model (about 90 MB) is downloaded once.
Do this at home before an exam. After that, indexing works offline.

## Using it

1. **Documents -> Library:** drag in a text-based PDF. Wait for the green **Ready** pill.
2. **Documents -> Ask:** ask a question. Sources appear under the answer.
3. **Documents -> Summarize:** click *Summarize document* (the result is saved).
4. **Quiz:** choose document, number of questions and difficulty.
5. **Python Assistant:** paste code and/or an error, or ask a question.
6. **Dark mode** is the switch at the bottom of the sidebar.

## Project structure

```
app.py                  entry point and page routing
config/settings.py      ALL parameters (models, RAG, chunking, temperatures) and UI text
ai/                     llm.py (LLM calls), prompts.py, embeddings.py, vector_store.py (ChromaDB), rag.py
documents/              loader.py, processor.py (extract + clean), chunker.py, summarizer.py
features/               chat.py, document_qa.py, quiz.py, python_assistant.py
database/database.py    SQLite: saved conversations
ui/                     sidebar, pages, reusable components, CSS (light/dark)
evaluation/             evaluator.py + test_questions.json (+ results/ after a run)
tests/                  110 automated tests (pytest)
docs/                   CAT_REPORT.md (report skeleton), DEMO_SCRIPT.md
```

Data is stored locally and ignored by Git: `data/` (PDFs, extracted text, summaries, `app.db`) and `vector_store/` (ChromaDB).

## Key parameters (all in `config/settings.py`)

| Parameter | Value | Why |
|---|---|---|
| Chunk size / overlap | 1000 / 200 characters | About 250 tokens fits the embedding model; 20% overlap keeps ideas that cross a boundary. Chunks never cross page borders, so citations are exact. |
| Embedding model | all-MiniLM-L6-v2 (384 dims) | Small, fast, local (documents are not sent anywhere for embedding). |
| Similarity | cosine (normalised vectors) | Standard for text embeddings. |
| Top-k / min similarity | 4 / 0.25 | Enough context without noise; below the threshold the AI is not even asked (reduces hallucination). **Tune with the evaluator.** |
| Temperature | chat 0.7, RAG 0.2, summary 0.3, quiz 0.5, Python 0.3 | Creative where useful, faithful where accuracy matters. |
| Max tokens | chat 2048, Python 3000, summary 3000, quiz 4000 | Room for the answer type. |
| LLM | `LLM_MODEL` in `.env` | Switching model is a one-line change. |

## Tests

```powershell
python -m pytest -q
```

The 110 tests check **our code**: PDF validation and cleaning, chunking, retrieval ranking, citation
extraction (invented page numbers are dropped), quiz JSON parsing and validation, map-reduce
summaries, SQLite persistence, friendly error messages, and the whole UI flow of every page.
They use a **fake LLM and fake embeddings**, so they run offline and fast.
They do **not** measure the real quality of the AI: that is what the evaluator is for.

## Evaluation (real measurements)

1. Upload your PDF in the app.
2. Edit `evaluation/test_questions.json`: replace the `TODO` RAG questions with questions whose answers are
   on known pages of your PDF (add keywords and page numbers). Items still saying `TODO` are skipped.
3. Run:

```powershell
python -m evaluation.evaluator --doc "part of your pdf name" --label baseline
```

It measures **retrieval hit rate and MRR, answer correctness (keyword proxy), grounding, citation accuracy,
refusal and hallucination rates, response time**, plus chat correctness/hallucination and quiz validity.
Results go to `evaluation/results/` (JSON with every answer, and a Markdown table).

To show the CAT's "adjust based on results", change one setting and run again with another label, for example:

```powershell
python -m evaluation.evaluator --doc "name" --label topk6 --top-k 6
python -m evaluation.evaluator --doc "name" --label sim15 --min-similarity 0.15
```

Quiz answer-key accuracy cannot be judged automatically: open the saved JSON, check each question against
the PDF, and set `manual_correct` to true/false.

## Troubleshooting

| Problem | Fix |
|---|---|
| "No API key found" | Put the key in `.env` (`LLM_API_KEY=...`, no spaces or quotes) and **restart** Streamlit. |
| "The AI took too long" / "Cannot reach the AI service" | Try again; check your internet; try another model in `.env` (some models are slow or overloaded at times). |
| "The model was not found" | Use a current model name from your provider. |
| "The embedding model could not be loaded" | Connect to the internet once so it can download. |
| Scanned PDF rejected | Only text-based PDFs work (no OCR). |
| Rate-limit message | Wait a minute; free tiers have limits. |

## Responsible AI

- **Hallucination:** document answers must cite numbered passages; the page shown comes from stored metadata, never from the AI; unsupported questions get "I could not find the answer".
- **Privacy:** PDFs, extracted text, embeddings and conversations stay on your computer. Only your question and the few passages needed to answer it are sent to the LLM provider. Summaries and quizzes send document text to the provider too. Do not upload confidential documents unless that is acceptable. Never commit `.env`.
- **Academic misuse:** the prompts steer toward explaining methods, and the quiz/summary tools support learning. Follow your university's rules on AI in graded work.

## Known limitations

- Each document question is searched on its own, so follow-ups like "explain that more" have no context.
- The quiz answer key and summaries are written by an LLM and can contain mistakes. Verify important facts.
- Long PDFs are sampled for quizzes and processed section by section for summaries; free API tiers can interrupt long jobs.
- Document-question conversations are not saved (AI Chat and Python Assistant conversations are).
- No OCR, no DOCX/TXT upload, no voice, no accounts (by design).
