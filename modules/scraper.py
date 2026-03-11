"""
modules/scraper.py
7-layer Burundi Business Intelligence scraper.
Strategy: direct RSS/page fetch for trusted sources first,
then DuckDuckGo for supplementary coverage.
"""

import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from youtube_transcript_api import YouTubeTranscriptApi

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; BurundiIntelBot/2.0)"}

# ── DIRECT RSS FEEDS — pulled first, most reliable ──
RSS_FEEDS = [
    # Layer 1 — Domestic
    ("iwacu-burundi.org",       "https://www.iwacu-burundi.org/feed/"),
    ("burundi-eco.com",         "https://burundi-eco.com/feed/"),
    ("breakingburundi.com",     "https://breakingburundi.com/feed/"),
    ("abpinfo.bi",              "https://www.abpinfo.bi/feed/"),
    # Layer 2 — East Africa
    ("theeastafrican.co.ke",    "https://www.theeastafrican.co.ke/rss/"),
    ("theafricareport.com",     "https://www.theafricareport.com/feed/"),
    ("allafrica.com",           "https://allafrica.com/tools/headlines/rdf/burundi/headlines.rdf"),
    ("africanews.com",          "https://www.africanews.com/feed/"),
    # Layer 3 — Business & investment
    ("african.business",        "https://african.business/feed/"),
    ("miningweekly.com",        "https://www.miningweekly.com/rss/rss.xml"),
    ("techafricanews.com",      "https://techafricanews.com/feed/"),
    # Layer 5 — Development
    ("worldbank.org",           "https://feeds.worldbank.org/worldbank/bi/rss"),
    # Layer 7 — China
    ("focac.org",               "https://www.focac.org/rss.xml"),
]

# ── DDGS FALLBACK QUERIES (generic, no site: operator) ──
DDG_QUERIES = [
    "Burundi business economy news",
    "Burundi investissement economie actualites",
    "Burundi mining nickel investment",
    "Burundi government policy finance",
    "Burundi China infrastructure project",
    "Burundi East Africa trade corridor",
    "Burundi startup entrepreneur innovation",
    "Burundi appel offres marche public",
]

DEFAULT_CATEGORY_KEYWORDS = {
    "markets":   ["bourse","stock","taux","banque","brb","franc burundais","monetary",
                  "sovereign","commodity","nickel","mining","coffee","export","investment"],
    "contracts": ["appel d'offres","marché public","contrat","armp","tender","procurement",
                  "infrastructure","construction","road","bridge","sinohydro","crbc"],
    "ventures":  ["startup","entrepreneur","jeune","projet","université","venture",
                  "innovation","telecom","energie","renewable","fintech","levée"],
    "china":     ["china","chinese","chine","chinois","focac","belt road","bri",
                  "sinohydro","crbc","xi jinping"],
}

def score_source(url, trusted_sources):
    domain = urlparse(url).netloc.replace("www.", "")
    for t in trusted_sources:
        if t in domain:
            return 5
    if ".bi" in domain:
        return 4
    if any(k in domain for k in ["reuters","bbc","ft.com","economist","bloomberg",
                                  "eastafrican","afdb","worldbank","imf","focac"]):
        return 4
    return 3

def classify_category(title, snippet, cfg):
    text     = (title + " " + snippet).lower()
    keywords = cfg.get("category_keywords", DEFAULT_CATEGORY_KEYWORDS)
    for cat in ["china","markets","contracts","ventures"]:
        if any(k in text for k in keywords.get(cat, [])):
            return cat
    return "general"

def detect_language(text):
    fr_markers = ["le ","la ","les ","du ","de ","est ","une ","pour ","dans ","avec "]
    return "FR" if sum(1 for m in fr_markers if m in text.lower()) >= 3 else "EN"

def is_burundi_relevant(title, snippet):
    text = (title + " " + snippet).lower()
    return any(k in text for k in ["burundi","bujumbura","gitega","bif","kirundi","ntahangwa"])

def make_article(title, url, snippet, source_domain, cfg, trusted):
    lang = detect_language(title + " " + snippet)
    return {
        "id":               "",
        "title":            title,
        "url":              url,
        "source":           source_domain,
        "snippet":          snippet,
        "authority":        score_source(url, trusted),
        "lang_original":    lang,
        "lang_display":     lang,
        "is_video":         False,
        "category":         classify_category(title, snippet, cfg),
        "time":             datetime.now().strftime("%H:%M"),
        "content":          "",
        "transcript":       None,
        "summary_original": "",
        "summary_fr":       "",
        "translation_note": None,
        "key_figures":      [],
        "key_entities":     [],
        "relevance_local":          70,
        "relevance_regional":       25,
        "relevance_international":  10,
        "audio_path":       None,
        "has_audio":        False,
        "card_pdf_path":    None,
    }

# ── RSS FETCHER ──
def fetch_rss(source_domain, feed_url, cfg, trusted, seen_urls, max_items=5):
    results = []
    try:
        resp = requests.get(feed_url, headers=HEADERS, timeout=12)
        root = ET.fromstring(resp.content)
        ns   = {"atom": "http://www.w3.org/2005/Atom"}

        # Handle both RSS and Atom formats
        items = root.findall(".//item") or root.findall(".//atom:entry", ns)

        for item in items[:max_items]:
            # RSS
            title   = (item.findtext("title") or "").strip()
            url     = (item.findtext("link") or "").strip()
            snippet = (item.findtext("description") or item.findtext("summary") or "").strip()
            # Strip HTML from snippet
            snippet = BeautifulSoup(snippet, "html.parser").get_text()[:300]

            # Atom fallback
            if not url:
                link_el = item.find("atom:link", ns)
                url = link_el.get("href","") if link_el is not None else ""

            if not title or not url or url in seen_urls:
                continue
            if not url.startswith("http"):
                continue

            seen_urls.add(url)

            # For non-domestic sources, filter to Burundi-relevant only
            if source_domain not in ["iwacu-burundi.org","burundi-eco.com",
                                     "breakingburundi.com","abpinfo.bi"]:
                if not is_burundi_relevant(title, snippet):
                    continue

            a = make_article(title, url, snippet, source_domain, cfg, trusted)
            if a["authority"] >= cfg["search"].get("min_authority_score", 2):
                results.append(a)

    except Exception as e:
        print(f"    ⚠️  RSS error ({source_domain}): {e}")
    return results

# ── ARTICLE TEXT FETCHER ──
def fetch_article_text(url):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=12)
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script","style","nav","footer","aside","form","header","noscript"]):
            tag.decompose()
        for sel in ["article",".article-body",".post-content",".entry-content","main"]:
            el = soup.select_one(sel)
            if el:
                text = el.get_text(separator="\n", strip=True)
                if len(text) > 200:
                    return text[:4000]
        paras = soup.find_all("p")
        return "\n".join(p.get_text(strip=True) for p in paras if len(p.get_text(strip=True)) > 40)[:4000]
    except:
        return ""

# ── DDGS FALLBACK ──
def search_ddg(query, max_results=4):
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            return [
                {"title": r.get("title",""), "url": r.get("href",""), "snippet": r.get("body","")}
                for r in ddgs.text(query, max_results=max_results)
            ]
    except Exception as e:
        print(f"    ⚠️  DDG error: {e}")
        return []

# ── MAIN ──
def scrape_all(cfg):
    articles  = []
    seen_urls = set()
    trusted   = cfg.get("trusted_sources", [])

    # ── STEP 1: Direct RSS feeds ──
    print("    📡 Direct RSS feeds...")
    for source_domain, feed_url in RSS_FEEDS:
        print(f"       → {source_domain}")
        items = fetch_rss(source_domain, feed_url, cfg, trusted, seen_urls)
        articles.extend(items)
        time.sleep(0.5)

    print(f"    → {len(articles)} articles via RSS")

    # ── STEP 2: DuckDuckGo supplementary ──
    print("    🔍 DuckDuckGo supplementary search...")
    for query in DDG_QUERIES:
        results = search_ddg(query, max_results=3)
        time.sleep(0.8)
        for r in results:
            url = r["url"]
            if url in seen_urls or not url.startswith("http"):
                continue
            if not is_burundi_relevant(r["title"], r["snippet"]):
                continue
            seen_urls.add(url)
            a = make_article(r["title"], url, r["snippet"],
                             urlparse(url).netloc.replace("www.",""), cfg, trusted)
            if a["authority"] >= cfg["search"].get("min_authority_score", 2):
                articles.append(a)

    # ── STEP 3: Fetch full article text ──
    print(f"    → {len(articles)} articles total, fetching content...")
    for a in articles:
        if not a["content"]:
            a["content"] = fetch_article_text(a["url"])
        time.sleep(0.3)

    # ── Assign IDs and sort ──
    articles.sort(key=lambda a: a["authority"], reverse=True)
    for i, a in enumerate(articles):
        a["id"] = f"a{i+1}"

    return articles
