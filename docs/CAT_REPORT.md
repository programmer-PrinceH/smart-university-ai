# Smart University AI: CAT Report

**Module:** Python and Fundamentals of AI (ITLPA701) · **Level:** RTQF VI · **Year 3** · **Total marks:** 30
**Student:** NIYONSHUTI Prince Heritier · **Date:** ____________

> Sections marked **[FILL IN]** need your real results or screenshots. Nothing in this report has been
> measured for you: run the evaluator on your own PDF and paste your numbers.

## 1. Problem and domain
University students struggle to revise from long lecture PDFs and to get quick, trustworthy help.
Domain: **question answering and document retrieval** (NLP). The app answers questions from the student's own
notes with page citations, summarises them, generates revision quizzes, and helps debug Python.

## 2. AI approach and justification
**RAG with a pretrained LLM.** Why: (a) the answers must come from the student's documents, which a general
LLM does not know; (b) retrieval lets us show exact sources, reducing hallucination; (c) no training data or
GPU is needed (training an LLM from scratch is not required by the CAT); (d) the same pipeline serves Q&A,
summaries and quizzes. AI Chat and the Python Assistant call the LLM directly because they do not need documents.

## 3. Architecture
```
User -> Streamlit UI -> application logic (features/)
   PDF -> text extraction (PyMuPDF, per page) -> cleaning -> chunking (keeps page numbers)
       -> embeddings (all-MiniLM-L6-v2) -> ChromaDB (text + document + page + chunk id)
   Question -> embedding -> top-k retrieval -> similarity threshold
       -> numbered passages + strict prompt -> LLM -> answer with [n] citations
       -> sources looked up from stored metadata (never written by the AI) -> user
```
[FILL IN: insert a diagram or screenshot.]

## 4. Data acquisition and preprocessing
- **Source:** lecturer-approved / own academic PDFs uploaded by the user. [FILL IN: names, pages.]
- **Validation:** empty file, not a PDF, damaged, password-protected, too large (20 MB), too many pages (300), no extractable text (scanned) are rejected with clear messages.
- **Extraction:** page by page, so every piece of text keeps its page number.
- **Cleaning:** remove null characters, join hyphenated line breaks, remove lone page numbers, collapse spaces and blank lines.
- **Deduplication:** a content hash identifies each file, so the same PDF is never processed twice.

## 5. Feature engineering
- **Data features:** text chunks (1000 characters, 200 overlap, sentence-aware, never crossing pages) converted into 384-dimensional normalised embeddings, stored with document name, page, chunk id.
- **Model features:** prompt templates per task (`ai/prompts.py`), numbered context passages, structured JSON output for quizzes, a fixed six-section format for summaries.

## 6. Parameters and why
| Parameter | Value | Justification |
|---|---|---|
| Chunk size | 1000 chars | about 250 tokens: fits the embedding model's input and holds one idea |
| Overlap | 200 chars (20%) | keeps definitions that cross chunk borders |
| Embedding model | all-MiniLM-L6-v2 | small, fast, local, good English quality |
| Similarity | cosine | standard for sentence embeddings (vectors are normalised) |
| Top-k | 4 | enough context without noise (tuned in section 8) |
| Min similarity | 0.25 | refuse instead of guessing when nothing relevant is found (tuned in section 8) |
| LLM | gemini-3.5-flash (`.env`) | fast (about 2 s in a test) and a normal flash model; chosen after gemini-3.7-flash and gemini-3.8-flash timed out during development |
| Temperature | chat 0.7, RAG 0.2, summary 0.3, quiz 0.5, Python 0.3 | creativity only where it helps |
| Max tokens | 2048 / 3000 / 4000 | enough for the answer type |
| Chat memory | last 20 messages | keeps context without unbounded cost |

## 7. Implementation and testing
Python 3.12, Streamlit, ChromaDB, sentence-transformers, PyMuPDF, SQLite, OpenAI-compatible LLM client.
136 automated tests (`python -m pytest -q`) cover validation, chunking, retrieval, citations, quiz parsing,
summaries, persistence, error messages and every UI page, using a fake LLM and fake embeddings.
Manual testing of the real models: [FILL IN: what you tried, screenshots].

## 8. Evaluation
Run: `python -m evaluation.evaluator --doc "<pdf name>" --label baseline`

**Metrics:** RAG: retrieval hit rate, MRR, answer correctness (keyword proxy), grounding, citation accuracy,
refusal/hallucination on out-of-document questions, response time. LLM: correctness, relevance, response time,
hallucination (false-premise questions). Quiz: validity, page grounding, answer-key accuracy (manual).

| Metric | Baseline | After adjustment |
|---|---|---|
| Retrieval hit rate | [FILL IN] | [FILL IN] |
| Answer correct rate | [FILL IN] | [FILL IN] |
| Grounding rate | [FILL IN] | [FILL IN] |
| Citation accuracy | [FILL IN] | [FILL IN] |
| Hallucination rate (out of document) | [FILL IN] | [FILL IN] |
| Average response time (s) | [FILL IN] | [FILL IN] |
| Quiz validity / answer-key accuracy | [FILL IN] | [FILL IN] |

**Interpretation:** [FILL IN: what the numbers mean, where it failed, examples of wrong answers.]
Note: keyword scoring is a proxy for correctness. Read the saved answers in the JSON to confirm.

## 9. Adjustment based on results
| Change | Reason (evidence) | Effect |
|---|---|---|
| [FILL IN, e.g. top-k 4 -> 6] | [FILL IN] | [FILL IN] |

## 10. Responsible AI
- **Hallucination:** RAG, mandatory numbered citations, sources taken from metadata, similarity threshold, explicit "not found" answer, low temperature. Remaining risk: the LLM can still misread a passage or write a wrong quiz answer key.
- **Privacy:** files, extracted text, embeddings and conversations stay local; only the question and retrieved passages (or document text for summaries/quizzes) go to the LLM provider; `.env`, `data/` and `vector_store/` are excluded from Git.
- **Academic misuse:** positioned as a learning tool; prompts explain methods; quizzes and summaries support understanding; users should follow university rules.
- **Other limits:** no OCR; English-centred embedding model; free API limits.

## 11. Reproducibility
`requirements.txt` (and your own `pip freeze` lock file), `.env.example`, all parameters in `config/settings.py`,
prompts in `ai/prompts.py`, vector store persisted in `vector_store/`, evaluation questions in `evaluation/test_questions.json`.

## 12. CAT marking alignment
| CAT criterion (marks) | Where | Status |
|---|---|---|
| Functionalities specified (1.5) | README, section 1-3 | Implemented |
| Environment configured (1.5) | venv + `requirements.txt` + `.env.example` | Implemented |
| Data acquired from given source (3) | PDF upload, validation | Implemented; **[FILL IN] your PDFs** |
| Data pre-processed (3) | extraction, cleaning, chunking | Implemented and unit-tested |
| Data features engineered (3) | embeddings + metadata | Implemented (real model needs first-run download) |
| Model features engineered (3) | prompts, retrieval, JSON schema | Implemented and unit-tested |
| Approach selected and justified (1.5) | section 2 | Written |
| Parameters selected and explained (1.5) | section 6 | Written |
| Application implemented and tested (6) | 5 features, 136 tests | Implemented; **run it with your real key and PDF** |
| Metrics selected (1) | section 8 | Written |
| Evaluation implemented, results interpreted (2) | `evaluation/evaluator.py` | Tool implemented; **you must run it and interpret [FILL IN]** |
| Parameters/prompts adjusted from results (1) | section 9 | **[FILL IN] after your evaluation runs** |
| Configuration/vector store/prompts saved (1) | `config/`, `ai/prompts.py`, `vector_store/` | Implemented |
| Deployed/demonstrated via web app (1) | Streamlit | Implemented |
| Responsible use discussed (task 8) | section 10 and in-app box | Written |
