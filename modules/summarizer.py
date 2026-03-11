"""
modules/summarizer.py — FREE VERSION (fixed)
─────────────────────────────────────────────
Uses Hugging Face Inference API v2 (new endpoint format, 2024+).
Primary model  : facebook/bart-large-cnn       (EN summarisation)
French content : plguillou/t5-base-fr-sum-cnndm (still live)

If HF API fails for any reason the script never crashes —
falls back to extracting the first 2 sentences of the article.
"""

import re
import time
import requests

# ── New HF Inference API endpoint (v2, still free) ──
HF_API_URL = "https://router.huggingface.co/hf-inference/models"

# ── Working summarisation models (verified March 2026) ──
MODEL_EN = "facebook/bart-large-cnn"
MODEL_FR = "plguillou/t5-base-fr-sum-cnndm"

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

def sentence_fallback(text, n=2):
    """Return first n sentences — used when API fails."""
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return " ".join(sentences[:n]).strip()


# ── HF SUMMARIZER (with retry + graceful failure) ──

def hf_summarize(text, hf_key, model, max_len=130, min_len=40, retries=2):
    headers = {"Authorization": f"Bearer {hf_key}"}
    payload = {
        "inputs": text[:1024],
        "parameters": {"max_length": max_len, "min_length": min_len, "do_sample": False},
    }
    url = f"{HF_API_URL}/{model}"

    for attempt in range(retries):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=45)

            # Model loading — wait and retry
            if resp.status_code == 503:
                wait = 20
                try:
                    wait = int(resp.json().get("estimated_time", 20))
                except Exception:
                    pass
                print(f"      ⏳ Modèle en chargement, attente {min(wait,30)}s...")
                time.sleep(min(wait, 30))
                continue

            # Gone or Not Found — model no longer available
            if resp.status_code in (404, 410):
                print(f"      ⚠️  Modèle indisponible ({resp.status_code}): {model}")
                return ""

            resp.raise_for_status()
            data = resp.json()

            if isinstance(data, list) and data:
                return (data[0].get("summary_text") or data[0].get("generated_text") or "").strip()
            if isinstance(data, dict):
                return (data.get("summary_text") or data.get("generated_text") or "").strip()

        except requests.exceptions.Timeout:
            print(f"      ⚠️  Timeout (tentative {attempt+1}/{retries})")
            time.sleep(5)
        except Exception as e:
            print(f"      ⚠️  HF summarize error: {e}")
            break

    return ""


def summarize_articles(articles, cfg):
    hf_key   = cfg.get("hf_api_key", "")
    models   = cfg.get("models", {})
    model_en = models.get("summarizer",    MODEL_EN)
    model_fr = models.get("summarizer_fr", MODEL_FR)

    for i, a in enumerate(articles):
        content = (a.get("content") or a.get("snippet", ""))[:1024]

        if not content:
            a.setdefault("summary_original",       a.get("snippet", ""))
            a.setdefault("key_figures",             [])
            a.setdefault("key_entities",            [])
            a.setdefault("relevance_local",         70)
            a.setdefault("relevance_regional",      25)
            a.setdefault("relevance_international", 10)
            continue

        lang  = a.get("lang_original", "EN").upper()
        model = model_fr if lang == "FR" else model_en

        print(f"      📝 [{i+1}/{len(articles)}] {a['title'][:48]}...")

        summary = hf_summarize(content, hf_key, model) if hf_key else ""

        # Always fall back — script must never crash here
        if not summary:
            summary = sentence_fallback(content) or a.get("snippet", a.get("title", ""))

        a["summary_original"]        = summary
        a["key_figures"]             = extract_figures(content)
        a["key_entities"]            = extract_entities(a["title"] + " " + content[:500])
        loc, reg, intl               = estimate_relevance(a["title"], content)
        a["relevance_local"]         = loc
        a["relevance_regional"]      = reg
        a["relevance_international"] = intl

    return articles
