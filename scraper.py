"""
modules/scraper.py
Recherche DuckDuckGo + extraction article / transcription YouTube.
Identique dans les versions gratuite et payante.
"""

import time
import requests
from datetime import datetime
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from youtube_transcript_api import YouTubeTranscriptApi

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; BurundiDailyBot/1.0)"}

CATEGORY_KEYWORDS = {
    "markets":   ["bourse","action","cotée","stock","marché financier","taux","banque","brb","franc burundais"],
    "contracts": ["appel d'offres","marché public","contrat gouvernement","armp","tender","procurement"],
    "ventures":  ["startup","entrepreneur","jeune","projet","école","université","venture","levée","innovation"],
}

def score_source(url, trusted_sources):
    domain = urlparse(url).netloc.replace("www.", "")
    for t in trusted_sources:
        if t in domain:
            return 5
    if ".bi" in domain:
        return 4
    if any(k in domain for k in ["reuters","bbc","eastafrican","monitor","rfi","africanews"]):
        return 4
    return 3

def classify_category(title, snippet):
    text = (title + " " + snippet).lower()
    for cat, keywords in CATEGORY_KEYWORDS.items():
        if any(k in text for k in keywords):
            return cat
    return "general"

def detect_language(text):
    fr_markers = ["le ","la ","les ","du ","de ","est ","une ","pour ","dans ","avec "]
    return "FR" if sum(1 for m in fr_markers if m in text.lower()) >= 3 else "EN"

def search_ddg(query, max_results=5):
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            return [{"title": r.get("title",""), "url": r.get("href",""), "snippet": r.get("body","")}
                    for r in ddgs.text(query, max_results=max_results)]
    except Exception as e:
        print(f"    ⚠️  Search error: {e}")
        return []

def fetch_article_text(url):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script","style","nav","footer","aside","form","header"]):
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

def fetch_youtube_transcript(url):
    try:
        video_id = None
        if "youtu.be/" in url:
            video_id = url.split("youtu.be/")[1].split("?")[0]
        elif "v=" in url:
            video_id = url.split("v=")[1].split("&")[0]
        if not video_id:
            return None
        for lang in [["fr"],["en"],["rn"],["sw"]]:
            try:
                tl   = YouTubeTranscriptApi.get_transcript(video_id, languages=lang)
                text = " ".join(t["text"] for t in tl)
                return {"transcript": text[:5000], "language": lang[0].upper()}
            except:
                continue
    except Exception as e:
        print(f"    ⚠️  YouTube error: {e}")
    return None

def scrape_all(cfg):
    articles  = []
    seen_urls = set()
    trusted   = cfg.get("trusted_sources", [])

    for query in cfg["search"]["queries"]:
        print(f"    🔍 {query}")
        results = search_ddg(query, cfg["search"].get("max_results_per_query", 5))
        time.sleep(0.6)

        for r in results:
            url = r["url"]
            if url in seen_urls or not url.startswith("http"):
                continue
            seen_urls.add(url)

            authority = score_source(url, trusted)
            if authority < cfg["search"].get("min_authority_score", 2):
                continue

            title   = r.get("title", "")
            snippet = r.get("snippet", "")
            is_yt   = "youtube.com" in url or "youtu.be" in url
            lang    = detect_language(title + " " + snippet)

            article = {
                "id": f"a{len(articles)+1}", "title": title, "url": url,
                "source": urlparse(url).netloc.replace("www.", ""),
                "snippet": snippet, "authority": authority,
                "lang_original": lang, "lang_display": lang,
                "is_video": is_yt, "category": classify_category(title, snippet),
                "time": datetime.now().strftime("%H:%M"),
                "content": "", "transcript": None,
                "summary_original": "", "summary_fr": "", "translation_note": None,
                "key_figures": [], "key_entities": [],
                "relevance_local": 70, "relevance_regional": 25, "relevance_international": 10,
                "audio_path": None, "has_audio": False, "card_pdf_path": None,
            }

            if is_yt:
                yt = fetch_youtube_transcript(url)
                if yt:
                    article["content"]       = yt["transcript"]
                    article["transcript"]    = yt["transcript"]
                    article["lang_original"] = yt["language"]
            else:
                article["content"] = fetch_article_text(url)

            if article["content"] or article["snippet"]:
                articles.append(article)

    articles.sort(key=lambda a: a["authority"], reverse=True)
    return articles
