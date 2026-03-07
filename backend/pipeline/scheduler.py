# pipeline/scheduler.py
# Runs the scrape → embed pipeline daily at 2 AM IST

import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger
from pipeline.scraper import run_scraper
from pipeline.embedder import upsert_documents, get_stats


async def run_pipeline():
    """Full pipeline: scrape → embed → store."""
    logger.info("🚀 Starting daily NyaySetu pipeline...")
    try:
        # Step 1: Scrape
        documents = await run_scraper()
        logger.info(f"📄 Scraped {len(documents)} chunks")

        # Step 2: Embed + store
        if documents:
            upsert_documents(documents)
            stats = get_stats()
            logger.info(f"✅ Pipeline complete. DB now has {stats['total_chunks']} chunks")
        else:
            logger.warning("⚠️ No documents scraped — check sources")

    except Exception as e:
        logger.error(f"❌ Pipeline failed: {e}")
        raise


def start_scheduler():
    """Start the APScheduler for daily runs."""
    scheduler = AsyncIOScheduler(timezone="Asia/Kolkata")

    # Run daily at 2:00 AM IST
    scheduler.add_job(
        run_pipeline,
        CronTrigger(hour=2, minute=0, timezone="Asia/Kolkata"),
        id="daily_pipeline",
        name="Daily Legal Data Pipeline",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("⏰ Scheduler started — pipeline runs daily at 2 AM IST")
    return scheduler


async def run_now():
    """Run the pipeline immediately (for first-time setup)."""
    await run_pipeline()


if __name__ == "__main__":
    asyncio.run(run_now())
