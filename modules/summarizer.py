"""
modules/summarizer.py — FREE VERSION (fixed)
"""

import re
import time
import requests

HF_API_URL = "https://router.huggingface.co/hf-inference/models"

MODEL_EN = "facebook/bart-large-cnn"
MODEL_FR = "plguillou/t5-base-fr-sum-cnndm"

def extract_figures(text):
    patterns = [
        r'\d+[\.,]?\d*\s*(?:million|milliard|billion|M|Md)\s*(?:USD|EUR|BIF|€|\$)?',
        r'\d+[\.,]?\d*\s*%',
        r'(?:USD|EUR|BIF|€|\$)\s*\d+[\.,]?\d*(?:\s*(?:million|M|milliard))?',
        r'\b20\d\d\b',
        r'\d+\s*km',
    ]
    seen, result = set(), []
    for pat in patterns:
        for m in re.findall(pat, text, re.IGNORECASE):
            m = m.strip()
            if m and m not in seen:
                seen.add(m)
                result.append(m)
            if len(result) >= 4:
                return result
    return result

def extract_entities(text):
    matches = re.findall(
        r'\b([A-ZÁÀÂÄÉÈÊËÍÏÎÓÔÖÚÙÛÜ][a-záàâäéèêëíïîóôöúùûü]+'
        r'(?:\s+[A-ZÁÀÂÄÉÈÊËÍÏÎÓÔÖÚÙÛÜ][a-záàâäéèêëíïîóôöúùûü]+){0,3})\b', text)
    stopwords = {"Le","La","Les","Du","De","Des","Un","Une","Et","En","Au","Aux","Dans","Pour","Sur","Par","Avec","Mais","Selon","Plus"}
    seen, result = set(), []
    for e in matches:
        if e not in stopwords and len(e) > 4 and e not in seen:
            seen.add(e)
            result.append(e)
        if len(result) >= 5:
            break
    return result

def estimate_relevance(title, content):
    text     = (title + " " + content).lower()
    local_kw = ["bujumbura","burundi","bif","kirundi","gitega","ngozi","rumonge","kayanza"]
    reg_kw   = ["afrique de l'est","east africa","eac","rwanda","tanzanie","kenya","ouganda","lac tanganyika"]
    intl_kw  = ["world bank","banque mondiale","imf","fmi","onu","union africaine","investissement étranger","export"]
    local    = min(100, 40 + sum(15 for k in local_kw if k in text))
    regional = min(100, 10 + sum(12 for k in reg_kw  if k in text))
    intl     = min(100,  5 + sum(10 for k in intl_kw if k in text))
    return local, regional, intl

def sentence_fallback(text, n=2):
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    return " ".join(sentences[:n]).strip()

def hf_summarize(text, hf_key, model, max_len=130, min_len=40, retries=2):
    headers = {"Authorization": f"Bearer {hf_key}"}
    payload = {"inputs": text[:1024], "parameters": {"max_length": max_len, "min_length": min_len, "do_sample": False}}
    url = f"{HF_API_URL}/{model}"
    for attempt in range(retries):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=45)
            if resp.status_code == 503:
                wait = 20
                try:
                    wait = int(resp.json().get("estimated_time", 20))
                except Exception:
                    pass
                print(f"      ⏳ Modèle en chargement, attente {min(wait,30)}s...")
                time.sleep(min(wait, 30))
                continue
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
            a.setdefault("summary_original",        a.get("snippet", ""))
            a.setdefault("key_figures",              [])
            a.setdefault("key_entities",             [])
            a.setdefault("relevance_local",          70)
            a.setdefault("relevance_regional",       25)
            a.setdefault("relevance_international",  10)
            continue
        lang  = a.get("lang_original", "EN").upper()
        model = model_fr if lang == "FR" else model_en
        print(f"      📝 [{i+1}/{len(articles)}] {a['title'][:48]}...")
        summary = hf_summarize(content, hf_key, model) if hf_key else ""
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
