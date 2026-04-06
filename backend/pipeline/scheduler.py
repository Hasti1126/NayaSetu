# pipeline/scheduler.py
import asyncio
import chromadb
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger
from pipeline.scraper import run_scraper
from pipeline.embedder import upsert_documents, get_stats

# For selective chunk deletion when a law changes
_chroma = chromadb.PersistentClient(path="./chroma_db")
_collection = _chroma.get_or_create_collection(
    name="indian_laws",
    metadata={"hnsw:space": "cosine"},
)

def _delete_law_chunks(law_name: str):
    try:
        _collection.delete(where={"source": law_name})
        logger.info(f"🗑️  Cleared old chunks for: {law_name}")
    except Exception as e:
        logger.warning(f"Could not clear chunks for {law_name}: {e}")

async def run_pipeline():
    """Full pipeline: scrape → embed → store. Called by main.py."""
    logger.info("🚀 Starting NyaySetu smart pipeline...")
    try:
        result = await run_scraper()

        mode         = result["mode"]
        documents    = result["docs"]
        changed_laws = result["changed_laws"]

        logger.info(f"📋 Mode: {mode} | Changed: {len(changed_laws)} laws | Chunks: {len(documents)}")

        if mode == "no_change":
            logger.info("✅ All laws unchanged — ChromaDB is up to date")
            return

        if mode == "full":
            # First ever run — insert everything
            if documents:
                upsert_documents(documents)
                stats = get_stats()
                logger.info(f"✅ Full seed done. DB now has {stats['total_chunks']} chunks")
            else:
                logger.warning("⚠️ No documents scraped — check sources")

        elif mode == "incremental":
            # Delete stale chunks for changed laws, then insert fresh ones
            for law_name in changed_laws:
                _delete_law_chunks(law_name)
            if documents:
                upsert_documents(documents)
                stats = get_stats()
                logger.info(f"✅ Updated {len(changed_laws)} laws. DB now has {stats['total_chunks']} chunks")

    except Exception as e:
        logger.error(f"❌ Pipeline failed: {e}")
        raise

def start_scheduler():
    """Start APScheduler — called by main.py lifespan."""
    scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")
    # Weekly instead of daily — laws don't change every day
    scheduler.add_job(
        run_pipeline,
        CronTrigger(day_of_week="sun", hour=2, minute=0, timezone="Asia/Kolkata"),
        id="weekly_pipeline",
        name="Weekly Law Change Detection",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("⏰ Scheduler started — law change check every Sunday at 2 AM IST")
    return scheduler

async def run_now():
    await run_pipeline()

if __name__ == "__main__":
    asyncio.run(run_now())
