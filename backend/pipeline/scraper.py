# pipeline/scraper.py — NyaySetu Comprehensive Legal Scraper
# Sources: India Code, eGazette, Supreme Court, Legislative.gov.in,
#          RBI, LiveLaw, BarAndBench, Labour Ministry

import httpx
import asyncio
import fitz
from bs4 import BeautifulSoup
from datetime import datetime, date
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

HEADERS = {
    "User-Agent": "NyaySetu-LegalBot/1.0 (Legal aid for Indian citizens; contact@nyaysetu.in)",
    "Accept": "text/html,application/xhtml+xml",
}

# Core laws — scraped on every daily run (backbone of NyaySetu)
CORE_LAWS = [
    # Rental
    {"name": "Transfer of Property Act 1882", "url": "https://www.indiacode.nic.in/handle/123456789/2338", "type": "statute"},
    {"name": "Model Tenancy Act 2021", "url": "https://mohua.gov.in/upload/uploadfiles/files/ModelTenancyAct2021English.pdf", "type": "statute", "is_pdf": True},
    {"name": "Maharashtra Rent Control Act 1999", "url": "https://indiankanoon.org/doc/176526529/", "type": "statute"},
    {"name": "Delhi Rent Control Act 1958", "url": "https://indiankanoon.org/doc/493081/", "type": "statute"},
    # Employment
    {"name": "Industrial Disputes Act 1947", "url": "https://www.indiacode.nic.in/handle/123456789/1530", "type": "statute"},
    {"name": "Payment of Gratuity Act 1972", "url": "https://www.indiacode.nic.in/handle/123456789/1591", "type": "statute"},
    {"name": "Employees Provident Fund Act 1952", "url": "https://www.indiacode.nic.in/handle/123456789/1523", "type": "statute"},
    {"name": "Minimum Wages Act 1948", "url": "https://www.indiacode.nic.in/handle/123456789/1542", "type": "statute"},
    {"name": "Sexual Harassment at Workplace Act 2013", "url": "https://www.indiacode.nic.in/handle/123456789/2328", "type": "statute"},
    # Contracts
    {"name": "Indian Contract Act 1872", "url": "https://www.indiacode.nic.in/handle/123456789/2187", "type": "statute"},
    # Property
    {"name": "Registration Act 1908", "url": "https://www.indiacode.nic.in/handle/123456789/2120", "type": "statute"},
    {"name": "RERA Act 2016", "url": "https://www.indiacode.nic.in/handle/123456789/2303", "type": "statute"},
    # Consumer
    {"name": "Consumer Protection Act 2019", "url": "https://www.indiacode.nic.in/handle/123456789/14672", "type": "statute"},
    # New criminal codes (2024)
    {"name": "Bharatiya Nyaya Sanhita 2023 (replaces IPC)", "url": "https://www.indiacode.nic.in/handle/123456789/20062", "type": "statute"},
    {"name": "Bharatiya Nagarik Suraksha Sanhita 2023 (replaces CrPC)", "url": "https://www.indiacode.nic.in/handle/123456789/20063", "type": "statute"},
    # Digital
    {"name": "Digital Personal Data Protection Act 2023", "url": "https://www.indiacode.nic.in/handle/123456789/20017", "type": "statute"},
    {"name": "Information Technology Act 2000", "url": "https://www.indiacode.nic.in/handle/123456789/1999", "type": "statute"},
]

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=8))
async def fetch(client, url):
    r = await client.get(url, headers=HEADERS, timeout=15.0, follow_redirects=True)
    r.raise_for_status()
    return r.text

async def fetch_pdf(client, url):
    r = await client.get(url, headers=HEADERS, timeout=30.0, follow_redirects=True)
    r.raise_for_status()
    doc = fitz.open(stream=r.content, filetype="pdf")
    return "\n".join(page.get_text() for page in doc).strip()

def clean(html):
    soup = BeautifulSoup(html, "lxml")
    for t in soup(["script","style","nav","footer","header","aside"]):
        t.decompose()
    main = soup.find("div", {"id":["main-content","content"]}) or soup.find("article") or soup.find("main") or soup.find("body")
    if not main: return ""
    lines = [l.strip() for l in main.get_text("\n").splitlines() if l.strip()]
    return "\n".join(lines)

def to_chunks(text, name, url, doc_type, extra=None):
    words = text.split()
    size, overlap, chunks = 600, 80, []
    i = 0
    while i < len(words):
        c = " ".join(words[i:i+size])
        if len(c.strip()) > 80:
            chunks.append(c)
        i += size - overlap
    meta_base = {"source": name, "title": name[:200], "url": url, "type": doc_type,
                 "scraped_at": datetime.now().isoformat(), "scrape_date": date.today().isoformat()}
    if extra:
        meta_base.update(extra)
    return [{"text": c, "metadata": {**meta_base, "chunk_index": i, "total_chunks": len(chunks)}}
            for i, c in enumerate(chunks)]

async def scrape_core_laws(client):
    docs = []
    for law in CORE_LAWS:
        try:
            text = await fetch_pdf(client, law["url"]) if law.get("is_pdf") else clean(await fetch(client, law["url"]))
            if len(text) < 100:
                continue
            docs.extend(to_chunks(text, law["name"], law["url"], law["type"], {"is_core": True}))
            logger.info(f"  ✅ {law['name']}")
            await asyncio.sleep(1.5)
        except Exception as e:
            logger.warning(f"  ❌ {law['name']}: {e}")
    return docs

async def scrape_india_code_recent(client):
    docs = []
    try:
        html = await fetch(client, "https://www.indiacode.nic.in/handle/123456789/1362/recent-item")
        soup = BeautifulSoup(html, "lxml")
        for link in soup.select("a[href*='/handle/']")[:12]:
            href = link["href"]
            if not href.startswith("http"):
                href = "https://www.indiacode.nic.in" + href
            try:
                text = clean(await fetch(client, href))
                title = link.get_text(strip=True)
                if len(text) > 200:
                    docs.extend(to_chunks(text, f"India Code: {title}", href, "statute"))
                await asyncio.sleep(1)
            except Exception: pass
    except Exception as e:
        logger.error(f"India Code: {e}")
    logger.info(f"  ✅ India Code recent: {len(docs)} chunks")
    return docs

async def scrape_egazette(client):
    docs = []
    try:
        url = f"https://egazette.gov.in/WriteReadData/{date.today().year}/"
        html = await fetch(client, url)
        soup = BeautifulSoup(html, "lxml")
        pdfs = [a["href"] for a in soup.find_all("a", href=True) if a["href"].endswith(".pdf")][:4]
        for pdf in pdfs:
            if not pdf.startswith("http"):
                pdf = "https://egazette.gov.in" + pdf
            try:
                text = await fetch_pdf(client, pdf)
                if len(text) > 200:
                    docs.extend(to_chunks(text, f"eGazette {date.today()}", pdf, "notification"))
                await asyncio.sleep(1)
            except Exception: pass
    except Exception as e:
        logger.error(f"eGazette: {e}")
    logger.info(f"  ✅ eGazette: {len(docs)} chunks")
    return docs

async def scrape_rbi(client):
    docs = []
    try:
        html = await fetch(client, "https://rbi.org.in/Scripts/NotificationUser.aspx")
        soup = BeautifulSoup(html, "lxml")
        for row in soup.select("table tr")[:8]:
            link = row.find("a")
            if not link: continue
            href = link.get("href","")
            if not href.startswith("http"): href = "https://rbi.org.in" + href
            try:
                text = clean(await fetch(client, href))
                if len(text) > 200:
                    docs.extend(to_chunks(text, f"RBI: {link.get_text(strip=True)}", href, "regulatory"))
                await asyncio.sleep(1)
            except Exception: pass
    except Exception as e:
        logger.error(f"RBI: {e}")
    logger.info(f"  ✅ RBI: {len(docs)} chunks")
    return docs

async def scrape_news(client, name, index_url, base_url, item_sel, link_sel):
    docs = []
    try:
        html = await fetch(client, index_url)
        soup = BeautifulSoup(html, "lxml")
        for item in soup.select(item_sel)[:8]:
            link = item.select_one(link_sel)
            if not link: continue
            href = link.get("href","")
            if not href.startswith("http"): href = base_url + href
            try:
                text = clean(await fetch(client, href))
                if len(text) > 300:
                    docs.extend(to_chunks(text, f"{name}: {link.get_text(strip=True)[:100]}", href, "news"))
                await asyncio.sleep(1)
            except Exception: pass
    except Exception as e:
        logger.error(f"{name}: {e}")
    logger.info(f"  ✅ {name}: {len(docs)} chunks")
    return docs

async def run_scraper() -> list[dict]:
    logger.info(f"🕷️  NyaySetu scraper starting — {date.today()}")
    all_docs = []
    async with httpx.AsyncClient(timeout=20.0) as client:
        logger.info("Phase 1: Core Indian Laws (India Code)")
        all_docs.extend(await scrape_core_laws(client))

        logger.info("Phase 2: India Code recent updates")
        all_docs.extend(await scrape_india_code_recent(client))

        logger.info("Phase 3: eGazette notifications")
        all_docs.extend(await scrape_egazette(client))

        logger.info("Phase 4: RBI circulars")
        all_docs.extend(await scrape_rbi(client))

        logger.info("Phase 5: Legal news")
        news = await asyncio.gather(
            scrape_news(client, "LiveLaw", "https://www.livelaw.in/top-stories",
                        "https://www.livelaw.in", "article", "a[href*='/top-stories/']"),
            scrape_news(client, "Bar & Bench", "https://www.barandbench.com/news",
                        "https://www.barandbench.com", "article", "a[href*='/news/']"),
            return_exceptions=True,
        )
        for r in news:
            if isinstance(r, list): all_docs.extend(r)

    # Coverage report
    by_src = {}
    for d in all_docs:
        s = d["metadata"].get("source","?").split(":")[0]
        by_src[s] = by_src.get(s, 0) + 1
    logger.info("\n📊 COVERAGE REPORT")
    for src, n in sorted(by_src.items(), key=lambda x: -x[1]):
        logger.info(f"  {src:<40} {n:>4} chunks")
    logger.info(f"  TOTAL: {len(all_docs)} chunks")
    return all_docs

if __name__ == "__main__":
    asyncio.run(run_scraper())
