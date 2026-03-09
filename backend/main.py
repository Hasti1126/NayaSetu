from dotenv import load_dotenv
load_dotenv()
# main.py — NyaySetu FastAPI Backend
# Serves RAG pipeline via REST API with SSE streaming

import asyncio
import json
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from loguru import logger
import fitz  # PyMuPDF

from pipeline.embedder import get_stats
from pipeline.scheduler import start_scheduler, run_pipeline
from rag.reasoner import analyze_document_rag, answer_legal_question


# ── Lifespan: startup + shutdown ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 NyaySetu starting up...")

    # Start daily scheduler
    scheduler = start_scheduler()

    # Seed DB if empty
    stats = get_stats()
    if stats.get("total_chunks", 0) == 0:
        logger.info("📭 DB is empty — running initial pipeline...")
        asyncio.create_task(run_pipeline())
    else:
        logger.info(f"📚 DB has {stats['total_chunks']} law chunks ready")

    yield

    scheduler.shutdown()
    logger.info("👋 NyaySetu shutting down")


app = FastAPI(
    title="NyaySetu API",
    description="AI Legal Aid for Every Indian — RAG + Ollama",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Models ───────────────────────────────────────────────────────────────────
class QuestionRequest(BaseModel):
    question: str
    lang: str = "en"


class TextAnalysisRequest(BaseModel):
    text: str
    doc_name: str = "Legal Document"
    lang: str = "en"


# ── Helpers ──────────────────────────────────────────────────────────────────
def extract_pdf_text(file_bytes: bytes) -> str:
    """Extract text from PDF using PyMuPDF (offline)."""
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text() + "\n"
    return text.strip()


async def sse_stream(generator):
    """Wrap async generator as Server-Sent Events stream."""
    async for event in generator:
        yield f"data: {json.dumps(event)}\n\n"
    yield "data: [DONE]\n\n"


# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {"message": "NyaySetu API — AI Legal Aid for Every Indian ⚖️"}


@app.get("/api/status")
def status():
    """System status — DB stats, model availability."""
    db_stats = get_stats()
    return {
        "status": "ok",
        "db": db_stats,
        "model": "llama-3.3-70b-versatile (Groq)",
        "ollama_available": True,
        "ready": db_stats.get("total_chunks", 0) > 0,
    }


@app.post("/api/analyze/text")
async def analyze_text(request: TextAnalysisRequest):
    """
    Analyze a legal document from pasted text.
    Returns full 3-pass RAG analysis as SSE stream.
    """
    if len(request.text.strip()) < 50:
        raise HTTPException(400, "Document text too short")

    async def generator():
        progress_events = []

        async def on_progress(message: str, percent: int):
            event = {"type": "progress", "message": message, "percent": percent}
            progress_events.append(event)
            # yield is handled by the outer generator

        # Run analysis
        task = asyncio.create_task(
            analyze_document_rag(request.text, request.doc_name, on_progress)
        )

        # Stream progress while analysis runs
        last_sent = 0
        while not task.done():
            while last_sent < len(progress_events):
                yield progress_events[last_sent]
                last_sent += 1
            await asyncio.sleep(0.1)

        # Flush remaining progress events
        while last_sent < len(progress_events):
            yield progress_events[last_sent]
            last_sent += 1

        # Send final result
        result = await task
        yield {"type": "result", "data": result}

    return StreamingResponse(
        sse_stream(generator()),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/analyze/pdf")
async def analyze_pdf(file: UploadFile = File(...)):
    """Upload PDF → extract text → analyze."""
    if not file.filename.endswith(".pdf"):
        raise HTTPException(400, "Only PDF files supported")

    file_bytes = await file.read()
    if len(file_bytes) > 10 * 1024 * 1024:  # 10MB limit
        raise HTTPException(400, "File too large (max 10MB)")

    try:
        text = extract_pdf_text(file_bytes)
    except Exception as e:
        raise HTTPException(400, f"Could not read PDF: {e}")

    if len(text.strip()) < 50:
        raise HTTPException(400, "Could not extract text from PDF")

    # Reuse text analysis endpoint
    request = TextAnalysisRequest(text=text, doc_name=file.filename)
    return await analyze_text(request)


@app.post("/api/ask")
async def ask_question(request: QuestionRequest):
    """
    Answer a direct legal question using RAG.
    SSE stream.
    """
    if len(request.question.strip()) < 5:
        raise HTTPException(400, "Question too short")

    async def generator():
        progress_events = []

        async def on_progress(message: str, percent: int):
            progress_events.append({"type": "progress", "message": message, "percent": percent})

        task = asyncio.create_task(
            answer_legal_question(request.question, on_progress)
        )

        last_sent = 0
        while not task.done():
            while last_sent < len(progress_events):
                yield progress_events[last_sent]
                last_sent += 1
            await asyncio.sleep(0.1)

        while last_sent < len(progress_events):
            yield progress_events[last_sent]
            last_sent += 1

        result = await task
        yield {"type": "result", "data": result}

    return StreamingResponse(
        sse_stream(generator()),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/pipeline/run")
async def trigger_pipeline():
    """Manually trigger the scrape + embed pipeline."""
    asyncio.create_task(run_pipeline())
    return {"message": "Pipeline started in background"}

@app.post("/api/ask/simple")
async def ask_simple(request: QuestionRequest):
    """Non-streaming version — works better in Codespaces."""
    result = await answer_legal_question(request.question)
    return result

@app.post("/api/analyze/simple")
async def analyze_simple(request: TextAnalysisRequest):
    """Non-streaming version — works better in Codespaces."""
    result = await analyze_document_rag(request.text, request.doc_name)
    return result
