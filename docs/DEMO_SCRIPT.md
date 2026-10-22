# Demo script (5-10 minutes)

Prepare beforehand: `.env` filled, one lecture PDF already uploaded once (so the embedding model is cached),
one real evaluation run saved in `evaluation/results/`, a Python snippet with a bug ready to paste.

1. **Open the app** (`streamlit run app.py`). Say: "Smart University AI, a RAG study assistant."
2. **Show the UI:** sidebar, five feature cards, dark mode switch, recent documents.
3. **AI Chat:** ask "What is Python?", then "What are its advantages?" (shows conversation memory). Point out the saved conversation in the sidebar.
4. **Upload a lecture PDF** in Documents -> Library. Show the **Ready** pill, page and chunk counts, and the extracted-text preview.
5. **Ask a question about the PDF** (Documents -> Ask).
6. **Show the real source:** document name and page number, then open "Show the passages used" and check the page in the PDF.
   Then ask something that is NOT in the PDF and show the "could not find" refusal.
7. **Summarize the PDF:** the six sections; mention chunk-based (map-reduce) processing for long files.
8. **Generate a quiz:** choose 5 questions, Medium; answer; show score, percentage, explanations and the source page.
9. **Python Assistant:** paste buggy code + the error; show the five sections and the highlighted corrected code.
10. **Evaluation:** open `evaluation/results/eval_*.md`; explain retrieval hit rate, grounding, hallucination rate, response time, and what you changed after the first run.
11. **Responsible AI:** open the "Using this assistant responsibly" box on Home; explain hallucination, privacy and academic misuse and how each is reduced.

Be ready to explain: chunk size/overlap, top-k, similarity threshold, temperatures, why RAG instead of fine-tuning, and where the page numbers come from.
