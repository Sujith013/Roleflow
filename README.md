# Job Application Agent

An end-to-end agent that ingests your resume/GitHub/LinkedIn data, finds matching
jobs via free job-board APIs, ranks them, tailors your resume per job, and
(eventually) assists with filling out applications.

LLM backend: **Microsoft Foundry** (Azure AI Foundry) — model-agnostic via the
Azure AI Inference SDK, so you can point it at GPT-5.4, DeepSeek, Llama, Mistral,
or Claude on Foundry without changing application code.

## Build stages

- [x] Stage 0 — Project skeleton + Foundry LLM client
- [x] Stage 1 — Resume + GitHub ingestion -> structured candidate profile
- [ ] Stage 2 — Job aggregation (Adzuna / Greenhouse / USAJOBS)
- [ ] Stage 3 — Matching & ranking
- [ ] Stage 4 — Resume tailoring per job
- [ ] Stage 5 — Application assist (Playwright, human-approved submit)

## Setup

1. **Provision a model in Microsoft Foundry**
   - Go to https://ai.azure.com → create/open a Foundry project
   - Model catalog → pick a model (e.g. `gpt-5.5`, `DeepSeek-R1`, `Llama-3.3-70B`) → Deploy
   - Copy the **endpoint URL** and **API key** from the deployment's Overview page

2. **Configure environment**
   ```bash
   cp .env.example .env
   # then edit .env and fill in your values
   ```

3. **Install dependencies**
   ```bash
   python -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. **Run tests** (no API key needed — LLM calls are mocked)
   ```bash
   pytest tests/ -v
   ```

5. **Try it on your real resume** (needs a real Foundry endpoint/key in `.env`)
   ```bash
   python scripts/parse_resume.py /path/to/your_resume.pdf
   # .docx, .tex, and .txt also work
   ```

## Why this order

Each stage produces data the next stage consumes, and each one is independently
testable:
- Stage 1 you can test the moment you have a resume file, with no cloud cost
  for the text-extraction parts, and one cheap LLM call to verify structuring.
- Stage 2 you can test against live free APIs immediately (Adzuna/USAJOBS/Greenhouse
  need no scraping and no LinkedIn/Indeed automation — see project notes on why
  those are avoided).
- Stages 3-5 build on real outputs from 1-2, so you're testing with real data
  the whole way, not synthetic fixtures.
