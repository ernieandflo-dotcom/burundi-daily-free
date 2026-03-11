"""
modules/summarizer.py — FREE VERSION
Uses Hugging Face Inference API (free tier):
  - facebook/bart-large-cnn       for English content
  - moussaKam/barthez-orangesum-abstract  for French content

Also does basic keyword extraction for figures and entities
(no LLM needed — regex-based, free).
"""

import re
import requests

HF_API_URL = "https://api-inference.huggingface.co/models"

# ── KEYWORD EXTRACTORS (regex, no API cost) ──

def extract_figures(text):
    """Pull out numbers, percentages, currency amounts."""
    patterns = [
        r'\d+[\.,]?\d*\s*(?:million|milliard|billion|M|Md)\s*(?:USD|EUR|BIF|€|\$)?',
        r'\d+[\.,]?\d*\s*%',
        r'(?:USD|EUR|BIF|€|\$)\s*\d+[\.,]?\d*(?:\s*(?:million|M|milliard))?',
        r'\d{4}',      # Years
        r'\d+\s*km',
    ]
    figures = []
    for pat in patterns:
        matches = re.findall(pat, text, re.IGNORECASE)
        figures.extend(m.strip() for m in matches)
    # Deduplicate and cap
    seen = set()
    result = []
    for f in figures:
        if f not in seen:
            seen.add(f)
            result.append(f)
        if len(result) >= 4:
            break
    return result

def extract_entities(text):
    """Extract capitalised proper nouns likely to be orgs/institutions."""
    # Match sequences of capitalised words (2+ chars)
    matches = re.findall(r'\b([A-ZÁÀÂÄÉÈÊËÍÏÎÓÔÖÚÙÛÜ][a-záàâäéèêëíïîóôöúùûü]+(?:\s+[A-ZÁÀÂÄÉÈÊËÍÏÎÓÔÖÚÙÛÜ][a-záàâäéèêëíïîóôöúùûü]+){0,3})\b', text)
    # Filter out common words
    stopwords = {"Le","La","Les","Du","De","Des","Un","Une","Et","En","Au","Aux","Dans","Pour","Sur","Par","Avec"}
    entities  = [m for m in matches if m not in stopwords and len(m) > 4]
    # Deduplicate
    seen, result = set(), []
    for e in entities:
        if e not in seen:
            seen.add(e)
            result.append(e)
        if len(result) >= 5:
            break
    return result

def estimate_relevance(title, content):
    """Heuristic relevance scoring — no API needed."""
    text = (title + " " + content).lower()
    local_kw  = ["bujumbura","burundi","bif","kirundi","gitega","ngozi","rumonge"]
    reg_kw    = ["afrique de l'est","east africa","eac","rwanda","tanzanie","kenya","ouganda","lac tanganyika"]
    intl_kw   = ["world bank","banque mondiale","imf","fmi","onu","union africaine","investissement étranger","export"]
    local  = min(100, 40 + sum(15 for k in local_kw if k in text))
    regional  = min(100, 10 + sum(12 for k in reg_kw  if k in text))
    intl      = min(100, 5  + sum(10 for k in intl_kw if k in text))
    return local, regional, intl

# ── HF SUMMARIZER ──

def hf_summarize(text, hf_key, model, max_len=130, min_len=40):
    headers  = {"Authorization": f"Bearer {hf_key}"}
    payload  = {
        "inputs": text[:1024],
        "parameters": {"max_length": max_len, "min_length": min_len, "do_sample": False},
        "options": {"wait_for_model": True},
    }
    try:
        resp = requests.post(f"{HF_API_URL}/{model}", headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list) and data:
            return data[0].get("summary_text", "").strip()
    except Exception as e:
        print(f"      ⚠️  HF summarize error: {e}")
    return ""

def summarize_articles(articles, cfg):
    hf_key   = cfg.get("hf_api_key", "")
    models   = cfg.get("models", {})
    model_en = models.get("summarizer",    "facebook/bart-large-cnn")
    model_fr = models.get("summarizer_fr", "moussaKam/barthez-orangesum-abstract")

    for i, a in enumerate(articles):
        content = (a.get("content") or a.get("snippet", ""))[:1024]
        if not content:
            a["summary_original"] = a.get("snippet", "")
            continue

        lang  = a.get("lang_original", "EN").upper()
        model = model_fr if lang == "FR" else model_en

        print(f"      📝 [{i+1}/{len(articles)}] {a['title'][:48]}...")
        summary = hf_summarize(content, hf_key, model)

        if not summary:
            # Fallback: first 2 sentences of content
            sentences = re.split(r'(?<=[.!?])\s+', content)
            summary   = " ".join(sentences[:2])

        a["summary_original"]        = summary
        a["key_figures"]             = extract_figures(content)
        a["key_entities"]            = extract_entities(a["title"] + " " + content[:500])
        loc, reg, intl               = estimate_relevance(a["title"], content)
        a["relevance_local"]         = loc
        a["relevance_regional"]      = reg
        a["relevance_international"] = intl

    return articles
