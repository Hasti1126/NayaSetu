import httpx
import asyncio
import fitz
from bs4 import BeautifulSoup
from datetime import datetime, date
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; NyaySetu/1.0)",
    "Accept": "text/html,application/xhtml+xml",
}

CORE_LAWS = [
    {"name": "Transfer of Property Act 1882", "url": "https://indiankanoon.org/doc/187040/", "type": "statute"},
    {"name": "Indian Contract Act 1872", "url": "https://indiankanoon.org/doc/1623393/", "type": "statute"},
    {"name": "Industrial Disputes Act 1947", "url": "https://indiankanoon.org/doc/464922/", "type": "statute"},
    {"name": "Consumer Protection Act 2019", "url": "https://indiankanoon.org/doc/102837089/", "type": "statute"},
    {"name": "Maharashtra Rent Control Act 1999", "url": "https://indiankanoon.org/doc/176526529/", "type": "statute"},
    {"name": "Delhi Rent Control Act 1958", "url": "https://indiankanoon.org/doc/493081/", "type": "statute"},
    {"name": "Payment of Gratuity Act 1972", "url": "https://indiankanoon.org/doc/418955/", "type": "statute"},
    {"name": "Information Technology Act 2000", "url": "https://indiankanoon.org/doc/1965344/", "type": "statute"},
    {"name": "RERA Act 2016", "url": "https://indiankanoon.org/doc/120763531/", "type": "statute"},
]

@retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=4))
async def fetch(client, url):
    r = await client.get(url, headers=HEADERS, timeout=10.0, follow_redirects=True)
    r.raise_for_status()
    return r.text

def clean(html):
    soup = BeautifulSoup(html, "lxml")
    for t in soup(["script","style","nav","footer","header"]):
        t.decompose()
    main = soup.find("div", {"id": "judgments"}) or soup.find("div", class_="judgement") or soup.find("body")
    if not main: return ""
    lines = [l.strip() for l in main.get_text("\n").splitlines() if l.strip()]
    return "\n".join(lines)

def to_chunks(text, name, url, doc_type):
    words = text.split()
    size, overlap, chunks = 500, 50, []
    i = 0
    while i < len(words):
        c = " ".join(words[i:i+size])
        if len(c.strip()) > 80:
            chunks.append(c)
        i += size - overlap
    now = datetime.now().isoformat()
    return [{"text": c, "metadata": {
        "source": name, "title": name, "url": url, "type": doc_type,
        "scraped_at": now, "scrape_date": date.today().isoformat(),
        "chunk_index": i, "total_chunks": len(chunks)
    }} for i, c in enumerate(chunks)]

async def scrape_core_laws(client):
    docs = []
    for law in CORE_LAWS:
        try:
            text = clean(await fetch(client, law["url"]))
            if len(text) > 100:
                docs.extend(to_chunks(text, law["name"], law["url"], law["type"]))
                logger.info(f"  ✅ {law['name']}")
            await asyncio.sleep(1)
        except Exception as e:
            logger.warning(f"  ❌ {law['name']}: {e}")
    return docs

async def scrape_news(client, name, url, base, sel, lsel):
    docs = []
    try:
        html = await fetch(client, url)
        soup = BeautifulSoup(html, "lxml")
        for item in soup.select(sel)[:6]:
            link = item.select_one(lsel)
            if not link: continue
            href = link.get("href","")
            if not href.startswith("http"): href = base + href
            try:
                text = clean(await fetch(client, href))
                title = link.get_text(strip=True)[:100]
                if len(text) > 200:
                    docs.extend(to_chunks(text, f"{name}: {title}", href, "news"))
                await asyncio.sleep(1)
            except Exception: pass
    except Exception as e:
        logger.error(f"{name}: {e}")
    logger.info(f"  ✅ {name}: {len(docs)} chunks")
    return docs

async def run_scraper() -> list[dict]:
    logger.info(f"🕷️  Scraper starting — {date.today()}")
    all_docs = []
    async with httpx.AsyncClient(timeout=15.0) as client:
        logger.info("Phase 1: Core Laws (IndianKanoon)")
        all_docs.extend(await scrape_core_laws(client))
        logger.info("Phase 2: Legal News")
        news = await asyncio.gather(
            scrape_news(client, "LiveLaw", "https://www.livelaw.in/top-stories",
                        "https://www.livelaw.in", "article", "a[href*='/top-stories/']"),
            scrape_news(client, "Bar & Bench", "https://www.barandbench.com/news",
                        "https://www.barandbench.com", "article", "a[href*='/news/']"),
            return_exceptions=True,
        )
        for r in news:
            if isinstance(r, list): all_docs.extend(r)
    logger.info(f"📊 TOTAL: {len(all_docs)} chunks")
    return all_docs

if __name__ == "__main__":
    asyncio.run(run_scraper())
