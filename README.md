# ⚖️ NyaySetu — AI Legal Aid for Every Indian
### *न्यायसेतु — Bridge to Justice*

> **Real AI. Real Indian Law. Updated Daily.**  
> Not rule-based. Not keyword matching. A genuine RAG pipeline grounded in live Indian legal sources.

🌐 **Live Demo:** [nayasetu.vercel.app](https://nayasetu.vercel.app)

---

## What It Does

80% of Indians cannot afford a lawyer. They sign rent agreements, employment contracts, and loan documents without understanding what they're agreeing to.

NyaySetu changes that. Upload any legal document and get:
- Plain English (and Hindi) explanation of every clause
- Cross-referenced against live Indian law database
- DANGER / WARNING / SAFE classification per clause
- Risk score based on actual violations found
- Specific legal rights you hold under Indian law

---

## How It Works

```
DAILY PIPELINE (2 AM IST)
indiankanoon.org ──► Scraper ──► Chunker ──► ChromaDB Vector Store

QUERY PIPELINE
User document / question
        ↓
   Embed query
        ↓
ChromaDB similarity search → Top 5 relevant law chunks
        ↓
Pass 1 → Extract clauses        (Groq LLM)
Pass 2 → Reason per clause      (Groq LLM × N clauses)
Pass 3 → Synthesize verdict     (Groq LLM)
        ↓
Cited, grounded answer with source URLs
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React + Vite, deployed on Vercel |
| Backend | FastAPI (Python), deployed on Render |
| Vector DB | ChromaDB with built-in embeddings |
| LLM | Llama 3.3 70B via Groq API (free tier) |
| Scraping | BeautifulSoup + httpx from indiankanoon.org |
| Scheduling | APScheduler — runs pipeline daily at 2 AM IST |

---

## What Makes This Real AI

| Approach | Rule Engine | NyaySetu |
|---|---|---|
| Unknown clauses | Can't detect | Handles any clause |
| Law knowledge | Hardcoded | Retrieved fresh from DB daily |
| Citations | Hardcoded strings | Actual source URLs with dates |
| Reasoning | None | 3-pass chain-of-thought |
| Hindi support | Manual translation | LLM generates natively |
| Risk score | Fixed | Calculated from actual violations |

---

## Indian Laws in Database

- Transfer of Property Act 1882
- Indian Contract Act 1872
- Industrial Disputes Act 1947
- Consumer Protection Act 2019
- Maharashtra Rent Control Act 1999
- Delhi Rent Control Act 1958
- Payment of Gratuity Act 1972
- Information Technology Act 2000
- RERA Act 2016
- Constitution of India (Article 21)

---

## Local Setup

### Prerequisites
```bash
Python 3.11+
Node 18+
Groq API key (free at console.groq.com)
```

### Backend
```bash
cd backend
pip install -r requirements.txt

# Add your Groq key
echo "GROQ_API_KEY=your_key_here" > .env

# Seed the law database
python -m pipeline.scheduler

# Start API server
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend
```bash
cd frontend
npm install

# Set backend URL
echo "VITE_API_URL=http://localhost:8000" > .env.local

npm run dev
# → http://localhost:5173
```

---

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `GET /api/status` | GET | System health, DB stats, model info |
| `POST /api/ask/simple` | POST | Answer a legal question |
| `POST /api/analyze/simple` | POST | Analyze pasted document text |
| `POST /api/analyze/pdf/simple` | POST | Upload and analyze PDF |
| `POST /api/pipeline/run` | POST | Manually trigger law scrape |

---

## Project Structure

```
NyaySetu/
├── backend/
│   ├── main.py                   ← FastAPI server
│   ├── pipeline/
│   │   ├── scraper.py            ← Scrapes indiankanoon.org daily
│   │   ├── embedder.py           ← ChromaDB vector store
│   │   └── scheduler.py          ← Runs pipeline at 2 AM IST
│   ├── rag/
│   │   └── reasoner.py           ← 3-pass Groq reasoning engine
│   └── requirements.txt
└── frontend/
    └── src/
        └── App.jsx               ← React UI
```

---

## Demo Flow (2 minutes)

1. Go to [nayasetu.vercel.app](https://nayasetu.vercel.app)
2. Upload the sample rent agreement PDF
3. Watch 3-pass reasoning: *"Extracting clauses → Cross-referencing Transfer of Property Act 1882 → Synthesizing verdict"*
4. Result: **Risk Score 80 — DANGER: Eviction without notice violates Section 106, TPA 1882**
5. Switch to Q&A: *"Can my landlord increase rent without notice?"* → cited answer from Rent Control Act

---



**Problem:** 80% of Indians cannot afford legal counsel. They sign documents blind.

**Solution:** NyaySetu — daily-updated Indian law database + LLM reasoning, accessible to anyone with a phone.

**Why it's real AI:** The panel will ask *"How is the knowledge current?"*

Answer: *"ChromaDB is re-embedded every morning at 2 AM IST from live indiankanoon.org. The LLM never answers from training data alone — every response is grounded in retrieved law chunks with source URLs and scrape dates."*

---

## Built With ❤️ for India

*NyaySetu is not a law firm. For serious legal matters, consult a qualified advocate.*
