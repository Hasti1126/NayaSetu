# ⚖️ NyaySetu — AI Legal Aid for Every Indian

> *"Bridge to Justice" — न्यायसेतु*

**Real AI. Real Indian Law. Updated Daily.**

Not rule-based. Not keyword matching. A genuine RAG pipeline that:
1. Crawls Indian legal sources every day
2. Retrieves the most relevant law for your document
3. Runs 3-pass LLM reasoning over retrieved law
4. Gives grounded, cited answers — not hallucination

---

## Architecture

```
DAILY PIPELINE (2 AM IST)
indiankanoon.org ──┐
legislative.gov.in ├──► Scraper ──► Chunker ──► sentence-transformers ──► ChromaDB
livelaw.in ────────┘

QUERY PIPELINE
User document/question
        ↓
   Embed query
        ↓
ChromaDB similarity search → Top 5 law chunks (with dates)
        ↓
Pass 1 → Extract clauses (Ollama LLM)
Pass 2 → Reason per clause against retrieved law (Ollama LLM)
Pass 3 → Synthesize final verdict (Ollama LLM)
        ↓
Cited, grounded answer with source URLs
```

---

## Quick Start

### Prerequisites
```bash
# Python 3.11+
python --version

# Node 18+
node --version

# Ollama
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2    # ~2GB, recommended
ollama serve            # keep running in background
```

### Backend
```bash
cd backend
pip install -r requirements.txt

# Seed the law database (first time only, ~5 minutes)
python -m pipeline.scheduler

# Start API server
uvicorn main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

---

## Project Structure

```
nyaysetu/
├── backend/
│   ├── main.py                   ← FastAPI server (REST + SSE streaming)
│   ├── pipeline/
│   │   ├── scraper.py            ← Crawls indiankanoon.org, livelaw.in daily
│   │   ├── embedder.py           ← ChromaDB vector store (sentence-transformers)
│   │   └── scheduler.py          ← APScheduler: runs pipeline at 2 AM IST
│   ├── rag/
│   │   └── reasoner.py           ← 3-pass Ollama reasoning engine
│   └── requirements.txt
└── frontend/
    └── src/
        └── App.jsx               ← React chat + document UI
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `GET /api/status` | GET | System health, DB stats, model availability |
| `POST /api/ask` | POST | Answer a legal question (SSE stream) |
| `POST /api/analyze/text` | POST | Analyze pasted document text (SSE stream) |
| `POST /api/analyze/pdf` | POST | Upload + analyze PDF (SSE stream) |
| `POST /api/pipeline/run` | POST | Manually trigger law scrape |

---

## What Makes This Real AI (Not Rule-Based)

| Approach | Rule Engine | NyaySetu |
|----------|------------|---------|
| How it works | `if "evict 24 hours" in text` | LLM reads clause, reasons against actual law |
| Unknown clauses | Can't detect | Handles any clause it hasn't seen |
| Law knowledge | Hardcoded | Retrieved fresh from DB daily |
| Citations | Hardcoded strings | Actual source URLs with dates |
| Reasoning | None | 3-pass chain-of-thought |
| Hallucination risk | None (but misses everything new) | Low (grounded in retrieved law) |

---

## For IIMA Ventures Residency Pitch

**Problem:** 80% of Indians can't afford a lawyer. They sign documents blind.

**Solution:** NyaySetu — daily-updated Indian law database + local LLM reasoning.

**Demo flow (2 minutes):**
1. Paste a rent agreement with an illegal eviction clause
2. Watch 3-pass reasoning live: "Pass 1: extracting clauses... Pass 2: cross-referencing Transfer of Property Act 1882... Pass 3: synthesizing verdict..."
3. Result: "DANGER — This violates Section 106, TPA 1882. Source: indiankanoon.org (retrieved today)"
4. Switch to Q&A: "Can my landlord increase rent without notice?" → cited answer from Model Tenancy Act 2021

**The panel will ask:** "How is the knowledge current?"
**Your answer:** "ChromaDB is re-embedded every morning at 2 AM IST from live Indian legal sources."

---

*Built for IIMA Ventures AI Summer Residency 2026 · Made with ❤️ for India*
