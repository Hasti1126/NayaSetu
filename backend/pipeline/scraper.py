import httpx
import asyncio
import fitz
from bs4 import BeautifulSoup
from datetime import datetime, date
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential
import os
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; NyaySetu/1.0)",
    "Accept": "text/html,application/xhtml+xml",
}

CORE_LAWS = [
    # --- PROPERTY & RENT ---
    {"name": "Transfer of Property Act 1882", "url": "https://indiankanoon.org/doc/187040/", "type": "statute"},
    {"name": "Registration Act 1908", "url": "https://indiankanoon.org/doc/1556021/", "type": "statute"},
    {"name": "Maharashtra Rent Control Act 1999", "url": "https://indiankanoon.org/doc/176526529/", "type": "statute"},
    {"name": "Delhi Rent Control Act 1958", "url": "https://indiankanoon.org/doc/493081/", "type": "statute"},
    {"name": "RERA Act 2016", "url": "https://indiankanoon.org/doc/120763531/", "type": "statute"},
    {"name": "Stamp Act 1899", "url": "https://indiankanoon.org/doc/1015881/", "type": "statute"},

    # --- CONTRACT & CIVIL ---
    {"name": "Indian Contract Act 1872", "url": "https://indiankanoon.org/doc/1623393/", "type": "statute"},
    {"name": "Specific Relief Act 1963", "url": "https://indiankanoon.org/doc/1840869/", "type": "statute"},
    {"name": "Limitation Act 1963", "url": "https://indiankanoon.org/doc/1317393/", "type": "statute"},
    {"name": "Civil Procedure Code 1908", "url": "https://indiankanoon.org/doc/1714097/", "type": "statute"},
    {"name": "Arbitration and Conciliation Act 1996", "url": "https://indiankanoon.org/doc/1052228/", "type": "statute"},

    # --- EMPLOYMENT & LABOUR ---
    {"name": "Industrial Disputes Act 1947", "url": "https://indiankanoon.org/doc/464922/", "type": "statute"},
    {"name": "Payment of Gratuity Act 1972", "url": "https://indiankanoon.org/doc/418955/", "type": "statute"},
    {"name": "Minimum Wages Act 1948", "url": "https://indiankanoon.org/doc/1955238/", "type": "statute"},
    {"name": "Payment of Wages Act 1936", "url": "https://indiankanoon.org/doc/1258138/", "type": "statute"},
    {"name": "Employees Provident Fund Act 1952", "url": "https://indiankanoon.org/doc/1362048/", "type": "statute"},
    {"name": "Maternity Benefit Act 1961", "url": "https://indiankanoon.org/doc/559557/", "type": "statute"},
    {"name": "Sexual Harassment of Women at Workplace Act 2013", "url": "https://indiankanoon.org/doc/160916812/", "type": "statute"},
    {"name": "Shops and Establishments Act", "url": "https://indiankanoon.org/doc/1596598/", "type": "statute"},
    {"name": "Contract Labour Act 1970", "url": "https://indiankanoon.org/doc/547524/", "type": "statute"},
    {"name": "Workmen Compensation Act 1923", "url": "https://indiankanoon.org/doc/1989045/", "type": "statute"},

    # --- CONSUMER & BANKING ---
    {"name": "Consumer Protection Act 2019", "url": "https://indiankanoon.org/doc/102837089/", "type": "statute"},
    {"name": "Negotiable Instruments Act 1881", "url": "https://indiankanoon.org/doc/1356482/", "type": "statute"},
    {"name": "SARFAESI Act 2002", "url": "https://indiankanoon.org/doc/1252270/", "type": "statute"},
    {"name": "Recovery of Debts Act 1993", "url": "https://indiankanoon.org/doc/882094/", "type": "statute"},
    {"name": "Insolvency and Bankruptcy Code 2016", "url": "https://indiankanoon.org/doc/109115936/", "type": "statute"},

    # --- FAMILY LAW ---
    {"name": "Hindu Marriage Act 1955", "url": "https://indiankanoon.org/doc/1312881/", "type": "statute"},
    {"name": "Hindu Succession Act 1956", "url": "https://indiankanoon.org/doc/1706624/", "type": "statute"},
    {"name": "Hindu Adoption and Maintenance Act 1956", "url": "https://indiankanoon.org/doc/381617/", "type": "statute"},
    {"name": "Guardians and Wards Act 1890", "url": "https://indiankanoon.org/doc/1359604/", "type": "statute"},
    {"name": "Muslim Personal Law", "url": "https://indiankanoon.org/doc/176122/", "type": "statute"},
    {"name": "Indian Divorce Act 1869", "url": "https://indiankanoon.org/doc/1090292/", "type": "statute"},
    {"name": "Domestic Violence Act 2005", "url": "https://indiankanoon.org/doc/542601/", "type": "statute"},
    {"name": "Dowry Prohibition Act 1961", "url": "https://indiankanoon.org/doc/1396781/", "type": "statute"},

    # --- CRIMINAL ---
    {"name": "Indian Penal Code 1860", "url": "https://indiankanoon.org/doc/1569253/", "type": "statute"},
    {"name": "Code of Criminal Procedure 1973", "url": "https://indiankanoon.org/doc/445276/", "type": "statute"},
    {"name": "Indian Evidence Act 1872", "url": "https://indiankanoon.org/doc/1306824/", "type": "statute"},
    {"name": "POCSO Act 2012", "url": "https://indiankanoon.org/doc/174607042/", "type": "statute"},
    {"name": "SC ST Prevention of Atrocities Act 1989", "url": "https://indiankanoon.org/doc/539423/", "type": "statute"},
    {"name": "NDPS Act 1985", "url": "https://indiankanoon.org/doc/1031396/", "type": "statute"},

    # --- TECHNOLOGY & DATA ---
    {"name": "Information Technology Act 2000", "url": "https://indiankanoon.org/doc/1965344/", "type": "statute"},
    {"name": "Digital Personal Data Protection Act 2023", "url": "https://indiankanoon.org/doc/184220615/", "type": "statute"},

    # --- TAXATION ---
    {"name": "Income Tax Act 1961", "url": "https://indiankanoon.org/doc/1307902/", "type": "statute"},
    {"name": "GST Act 2017", "url": "https://indiankanoon.org/doc/109205868/", "type": "statute"},

    # --- SOCIAL & RIGHTS ---
    {"name": "Right to Information Act 2005", "url": "https://indiankanoon.org/doc/1965344/", "type": "statute"},
    {"name": "Right to Education Act 2009", "url": "https://indiankanoon.org/doc/186199804/", "type": "statute"},
    {"name": "Persons with Disabilities Act 2016", "url": "https://indiankanoon.org/doc/185091908/", "type": "statute"},
    {"name": "Senior Citizens Act 2007", "url": "https://indiankanoon.org/doc/35535820/", "type": "statute"},

    # --- CONSTITUTION ---
    {"name": "Constitution of India Fundamental Rights", "url": "https://indiankanoon.org/doc/609139/", "type": "statute"},
]
# @retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=4))
# async def fetch(client, url):
#     r = await client.get(url, headers=HEADERS, timeout=10.0, follow_redirects=True)
#     r.raise_for_status()
#     return r.text


SCRAPER_API_KEY = os.getenv("SCRAPER_API_KEY")

@retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=4))
async def fetch(client, url):
    if SCRAPER_API_KEY:
        proxy_url = f"http://api.scraperapi.com/?api_key={SCRAPER_API_KEY}&url={url}"
    else:
        proxy_url = url  # fallback for local/dev

    logger.info(f"Fetching: {url}")

    r = await client.get(
        proxy_url,
        headers=HEADERS,
        timeout=20.0,
        follow_redirects=True
    )
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
