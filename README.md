# ⚖️ NyaySetu — AI Legal Aid for Every Indian
### *न्यायसेतु — Bridge to Justice*

> **Real AI. Real Indian Law. Updated Daily.**
> Not rule-based. Not keyword matching. A genuine RAG pipeline grounded in 49 live Indian legal sources.

🌐 **Live Demo:** [nayasetu.vercel.app](https://nayasetu.vercel.app)  
🔧 **Backend API:** [nayasetu.onrender.com](https://nayasetu.onrender.com/api/status)

---

## The Problem

80% of Indians cannot afford a lawyer. They sign rent agreements, employment contracts, and loan documents without understanding what they're agreeing to. A single dangerous clause can cost them their home, their job, or their savings.

---

## The Solution

NyaySetu — upload any legal document and get:

- Plain English and Hindi explanation of every clause
- Cross-referenced against 49 live Indian laws updated daily
- DANGER / WARNING / SAFE classification per clause
- Risk score calculated from actual violations found
- Specific legal rights you hold under Indian law
- Source URLs with retrieval dates — no hallucination

---

## How It Works

```
DAILY PIPELINE (2 AM IST)
indiankanoon.org ──► ScraperAPI ──► Scraper ──► Chunker ──► ChromaDB

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
Cited, grounded answer with source URLs and dates
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React + Vite, deployed on Vercel |
| Backend | FastAPI (Python), deployed on Render |
| Vector DB | ChromaDB with built-in embeddings |
| LLM | Llama 3.3 70B via Groq API |
| Scraping | BeautifulSoup + httpx + ScraperAPI |
| Scheduling | APScheduler — runs pipeline daily at 2 AM IST |

---

## Indian Laws Covered (49 Laws)

### Property & Rent
Transfer of Property Act 1882, Registration Act 1908, Maharashtra Rent Control Act 1999, Delhi Rent Control Act 1958, RERA Act 2016, Stamp Act 1899

### Contract & Civil
Indian Contract Act 1872, Specific Relief Act 1963, Limitation Act 1963, Civil Procedure Code 1908, Arbitration and Conciliation Act 1996

### Employment & Labour
Industrial Disputes Act 1947, Payment of Gratuity Act 1972, Minimum Wages Act 1948, Payment of Wages Act 1936, EPF Act 1952, Maternity Benefit Act 1961, POSH Act 2013, Contract Labour Act 1970, Workmen Compensation Act 1923

### Consumer & Banking
Consumer Protection Act 2019, Negotiable Instruments Act 1881, SARFAESI Act 2002, Recovery of Debts Act 1993, Insolvency and Bankruptcy Code 2016

### Family Law
Hindu Marriage Act 1955, Hindu Succession Act 1956, Hindu Adoption and Maintenance Act 1956, Guardians and Wards Act 1890, Muslim Personal Law, Indian Divorce Act 1869, Domestic Violence Act 2005, Dowry Prohibition Act 1961

### Criminal
Indian Penal Code 1860, Code of Criminal Procedure 1973, Indian Evidence Act 1872, POCSO Act 2012, SC/ST Prevention of Atrocities Act 1989, NDPS Act 1985

### Technology & Data
Information Technology Act 2000, Digital Personal Data Protection Act 2023

### Taxation
Income Tax Act 1961, GST Act 2017

### Social & Rights
RTI Act 2005, Right to Education Act 2009, Persons with Disabilities Act 2016, Senior Citizens Act 2007

### Constitution
Constitution of India — Fundamental Rights

---

## What Makes This Real AI

| | Rule Engine | NyaySetu |
|---|---|---|
| Unknown clauses | Can't detect | Handles any clause |
| Law knowledge | Hardcoded | Retrieved fresh daily |
| Citations | Hardcoded strings | Live source URLs + dates |
| Reasoning | None | 3-pass chain-of-thought |
| Hindi support | Manual | LLM generates natively |
| Risk score | Fixed | Calculated from violations |
| Laws covered | Fixed set | 49 laws, growing |

---

## Local Setup

### Prerequisites
```
Python 3.11+
Node 18+
Groq API key — free at console.groq.com
ScraperAPI key — free at scraperapi.com
```

### Backend
```bash
cd backend
pip install -r requirements.txt
echo "GROQ_API_KEY=your_key" > .env
echo "SCRAPER_API_KEY=your_key" >> .env
python -m pipeline.scheduler
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend
```bash
cd frontend
npm install
echo "VITE_API_URL=http://localhost:8000" > .env.local
npm run dev
```

---

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `GET /api/status` | GET | System health, DB stats |
| `POST /api/ask/simple` | POST | Answer a legal question |
| `POST /api/analyze/simple` | POST | Analyze document text |
| `POST /api/analyze/pdf/simple` | POST | Upload and analyze PDF |
| `POST /api/pipeline/run` | POST | Trigger law scrape manually |

---

*NyaySetu is not a law firm. For serious legal matters, consult a qualified advocate.*
*Built with ❤️ for India*
