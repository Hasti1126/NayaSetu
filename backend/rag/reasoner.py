# rag/reasoner.py
# The core reasoning engine — takes user query + retrieved law chunks
# and uses Ollama LLM to reason step-by-step over them.
# This is REAL reasoning, not just prompt stuffing.

import ollama
import json
from loguru import logger
from pipeline.embedder import retrieve

# ── Model config ─────────────────────────────────────────────────────────────
PREFERRED_MODELS = ["llama3.2", "llama3", "mistral", "phi3", "gemma2"]


def get_available_model() -> str:
    """Pick best available Ollama model."""
    try:
        models = ollama.list()
        available = [m["name"].split(":")[0] for m in models.get("models", [])]
        for preferred in PREFERRED_MODELS:
            if any(preferred in a for a in available):
                return preferred
        return available[0] if available else None
    except Exception:
        return None


# ── Step 1: Extract clauses from document ────────────────────────────────────
def extract_clauses(document_text: str, model: str) -> list[str]:
    """
    Pass 1: Ask LLM to identify and list all distinct clauses.
    This isolates each clause before we analyze them.
    """
    prompt = f"""You are a legal document parser. Read this document and list every distinct clause or provision.

DOCUMENT:
{document_text[:3000]}

List each clause on a new line, numbered. Be specific — extract the actual clause text, not summaries.
Output ONLY the numbered list, nothing else."""

    response = ollama.generate(
        model=model,
        prompt=prompt,
        options={"temperature": 0.0, "num_predict": 800},
    )
    
    raw = response["response"]
    clauses = []
    for line in raw.strip().split("\n"):
        line = line.strip()
        if line and (line[0].isdigit() or line.startswith("-")):
            # Strip numbering
            clause = line.lstrip("0123456789.-) ").strip()
            if len(clause) > 20:
                clauses.append(clause)
    
    logger.info(f"📋 Extracted {len(clauses)} clauses from document")
    return clauses


# ── Step 2: Retrieve relevant law for each clause ────────────────────────────
def retrieve_law_for_clause(clause: str) -> list[dict]:
    """
    For each clause, retrieve the most relevant Indian law sections from ChromaDB.
    This grounds the LLM in actual law, not hallucination.
    """
    chunks = retrieve(clause, n_results=3)
    return chunks


# ── Step 3: Reason about each clause against retrieved law ───────────────────
def reason_about_clause(clause: str, law_chunks: list[dict], model: str) -> dict:
    """
    Pass 2 (per clause): Given a clause + actual law text, reason step by step.
    THIS is where real legal reasoning happens.
    """
    law_context = "\n\n---\n\n".join([
        f"SOURCE: {c['source']} (retrieved {c['scraped_at'][:10]})\nURL: {c['url']}\n\n{c['text']}"
        for c in law_chunks
    ])

    prompt = f"""You are an expert Indian lawyer analyzing a contract clause for someone who cannot afford legal help.

CLAUSE TO ANALYZE:
"{clause}"

RELEVANT INDIAN LAW (retrieved from live database):
{law_context}

Think step by step:
1. What does this clause actually mean in plain language?
2. Does this clause comply with the Indian law provided above?
3. If it violates any law, which specific section and why?
4. What is the risk level: SAFE / WARNING / DANGER?
5. What should the person signing this document do?

Respond in this exact JSON format:
{{
  "plain_meaning": "what this clause means in simple language",
  "plain_meaning_hindi": "same in Hindi",
  "complies_with_law": true or false,
  "violation": "specific law section violated, or null if compliant",
  "severity": "SAFE" or "WARNING" or "DANGER",
  "reasoning": "your step-by-step legal reasoning",
  "action": "what the person should do",
  "sources_used": ["source name 1", "source name 2"]
}}"""

    response = ollama.generate(
        model=model,
        prompt=prompt,
        options={"temperature": 0.1, "num_predict": 600},
    )

    try:
        raw = response["response"]
        json_match = raw[raw.find("{"):raw.rfind("}") + 1]
        result = json.loads(json_match)
        result["original_clause"] = clause
        result["law_chunks"] = law_chunks
        return result
    except Exception as e:
        logger.warning(f"Failed to parse clause analysis: {e}")
        return {
            "original_clause": clause,
            "plain_meaning": "Could not analyze this clause.",
            "plain_meaning_hindi": "इस खंड का विश्लेषण नहीं हो सका।",
            "severity": "WARNING",
            "reasoning": response["response"],
            "action": "Please consult a lawyer for this clause.",
            "law_chunks": law_chunks,
        }


# ── Step 4: Synthesize final verdict ─────────────────────────────────────────
def synthesize_verdict(
    document_text: str,
    clause_analyses: list[dict],
    model: str,
    doc_name: str = "document",
) -> dict:
    """
    Pass 3: Given all clause-level analyses, synthesize an overall verdict.
    The LLM sees the full picture and gives a holistic assessment.
    """
    # Summarize clause analyses for the final prompt
    clause_summary = "\n".join([
        f"- Clause: \"{c['original_clause'][:100]}...\" → {c.get('severity', 'UNKNOWN')}: {c.get('plain_meaning', '')[:100]}"
        for c in clause_analyses[:10]  # limit to avoid context overflow
    ])

    danger_count = sum(1 for c in clause_analyses if c.get("severity") == "DANGER")
    warning_count = sum(1 for c in clause_analyses if c.get("severity") == "WARNING")

    prompt = f"""You are a senior Indian lawyer giving a final verdict on a legal document.

DOCUMENT TYPE: {doc_name}
CLAUSE ANALYSIS SUMMARY:
{clause_summary}

STATISTICS:
- {danger_count} DANGER clauses found
- {warning_count} WARNING clauses found
- {len(clause_analyses)} total clauses analyzed

Give a final verdict with:
1. Should this person sign this document as-is?
2. What are the TOP 3 most urgent things to fix?
3. What rights does this person have under Indian law?
4. One sentence summary in Hindi for a non-lawyer

Respond in JSON:
{{
  "should_sign": true or false,
  "overall_risk": "Low" or "Moderate" or "High" or "Very High",
  "risk_score": number 0-100,
  "verdict_english": "2-3 sentence plain English verdict",
  "verdict_hindi": "2-3 sentence plain Hindi verdict",
  "top_3_urgent": ["urgent action 1", "urgent action 2", "urgent action 3"],
  "key_rights": ["right 1 under Indian law", "right 2", "right 3"]
}}"""

    response = ollama.generate(
        model=model,
        prompt=prompt,
        options={"temperature": 0.1, "num_predict": 500},
    )

    try:
        raw = response["response"]
        json_match = raw[raw.find("{"):raw.rfind("}") + 1]
        return json.loads(json_match)
    except Exception:
        return {
            "should_sign": False,
            "overall_risk": "Unknown",
            "risk_score": 50,
            "verdict_english": "Analysis complete. Please review individual clause findings above.",
            "verdict_hindi": "विश्लेषण पूर्ण। कृपया व्यक्तिगत खंड निष्कर्ष देखें।",
            "top_3_urgent": ["Review all DANGER clauses", "Consult a lawyer", "Negotiate before signing"],
            "key_rights": [],
        }


# ── Main pipeline entry point ─────────────────────────────────────────────────
async def analyze_document_rag(
    document_text: str,
    doc_name: str = "Legal Document",
    on_progress=None,
) -> dict:
    """
    Full 3-pass RAG reasoning pipeline:
    Pass 1 → Extract clauses
    Pass 2 → Retrieve law + reason per clause  
    Pass 3 → Synthesize final verdict
    """
    model = get_available_model()
    if not model:
        raise RuntimeError(
            "No Ollama model found. Run: ollama pull llama3.2 && ollama serve"
        )

    logger.info(f"🤖 Using model: {model}")

    # ── Pass 1: Extract clauses ──────────────────────────────────────────────
    if on_progress:
        await on_progress("🔍 Pass 1: Extracting clauses from document...", 0)

    clauses = extract_clauses(document_text, model)

    # ── Pass 2: Retrieve law + reason per clause ─────────────────────────────
    clause_analyses = []
    for i, clause in enumerate(clauses[:12]):  # analyze up to 12 clauses
        if on_progress:
            pct = int(((i + 1) / len(clauses)) * 70)
            await on_progress(
                f"⚖️  Pass 2: Analyzing clause {i+1}/{len(clauses)}: \"{clause[:60]}...\"",
                pct,
            )

        # Retrieve relevant law from ChromaDB
        law_chunks = retrieve_law_for_clause(clause)

        # Reason about this clause
        analysis = reason_about_clause(clause, law_chunks, model)
        clause_analyses.append(analysis)

    # ── Pass 3: Synthesize final verdict ────────────────────────────────────
    if on_progress:
        await on_progress("📋 Pass 3: Synthesizing final verdict...", 85)

    verdict = synthesize_verdict(document_text, clause_analyses, model, doc_name)

    if on_progress:
        await on_progress("✅ Analysis complete!", 100)

    # ── Format final response ────────────────────────────────────────────────
    dangers = [c for c in clause_analyses if c.get("severity") == "DANGER"]
    warnings = [c for c in clause_analyses if c.get("severity") == "WARNING"]
    safe = [c for c in clause_analyses if c.get("severity") == "SAFE"]

    return {
        "model_used": model,
        "passes": 3,
        "doc_name": doc_name,
        "verdict": verdict,
        "clause_analyses": clause_analyses,
        "summary": {
            "total_clauses": len(clause_analyses),
            "danger_count": len(dangers),
            "warning_count": len(warnings),
            "safe_count": len(safe),
            "risk_score": verdict.get("risk_score", 50),
        },
        "dangers": dangers,
        "warnings": warnings,
        "safe_clauses": safe,
    }


# ── Q&A mode: answer legal questions directly ────────────────────────────────
async def answer_legal_question(question: str, on_progress=None) -> dict:
    """
    For direct legal Q&A (not document upload).
    Retrieves relevant law → reasons over it → gives cited answer.
    """
    model = get_available_model()
    if not model:
        raise RuntimeError("No Ollama model found.")

    if on_progress:
        await on_progress("🔎 Searching Indian law database...", 20)

    # Retrieve relevant law chunks
    chunks = retrieve(question, n_results=5)

    if on_progress:
        await on_progress("🤔 Reasoning over retrieved law...", 50)

    law_context = "\n\n---\n\n".join([
        f"SOURCE: {c['source']} ({c['scraped_at'][:10]})\n{c['text']}"
        for c in chunks
    ])

    prompt = f"""You are NyaySetu, a helpful Indian legal assistant for common people.

USER QUESTION: {question}

RELEVANT INDIAN LAW (from live database, retrieved today):
{law_context}

Answer the question clearly and helpfully. Use the law provided above — cite specific sections.
If the law context doesn't cover the question, say so honestly.

Format your response as JSON:
{{
  "answer_english": "clear, plain English answer citing specific laws",
  "answer_hindi": "same answer in Hindi",
  "applicable_laws": ["law section 1", "law section 2"],
  "practical_advice": "what the person should actually do",
  "confidence": "High/Medium/Low based on how well the retrieved law covers this question",
  "sources": ["source name 1", "source name 2"]
}}"""

    response = ollama.generate(
        model=model,
        prompt=prompt,
        options={"temperature": 0.15, "num_predict": 700},
    )

    if on_progress:
        await on_progress("✅ Answer ready!", 100)

    try:
        raw = response["response"]
        json_match = raw[raw.find("{"):raw.rfind("}") + 1]
        result = json.loads(json_match)
        result["retrieved_chunks"] = chunks
        result["model_used"] = model
        return result
    except Exception:
        return {
            "answer_english": response["response"],
            "answer_hindi": "",
            "applicable_laws": [],
            "practical_advice": "Consult a local advocate for specific advice.",
            "confidence": "Low",
            "retrieved_chunks": chunks,
            "model_used": model,
        }
