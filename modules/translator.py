"""
modules/translator.py — FREE VERSION (fixed)
"""

import time
import requests

HF_API_URL = "https://router.huggingface.co/hf-inference/models"

LANG_NAMES = {
    "EN": "anglais", "SW": "swahili", "RN": "kirundi",
    "FR": "français", "PT": "portugais", "AR": "arabe",
}

HF_TRANSLATION_MODELS = {
    "EN": "Helsinki-NLP/opus-mt-en-fr",
    "SW": "Helsinki-NLP/opus-mt-swc-fr",
    "PT": "Helsinki-NLP/opus-mt-pt-fr",
    "AR": "Helsinki-NLP/opus-mt-ar-fr",
}

def hf_translate(text, hf_key, model, retries=2):
    if not text or not text.strip():
        return ""
    headers = {"Authorization": f"Bearer {hf_key}"}
    payload = {"inputs": text[:512]}
    url     = f"{HF_API_URL}/{model}"
    for attempt in range(retries):
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=45)
            if resp.status_code == 503:
                wait = 20
                try:
                    wait = int(resp.json().get("estimated_time", 20))
                except Exception:
                    pass
                print(f"      ⏳ Modèle traduction en chargement, attente {min(wait,30)}s...")
                time.sleep(min(wait, 30))
                continue
            if resp.status_code in (404, 410):
                print(f"      ⚠️  Modèle traduction indisponible ({resp.status_code}): {model}")
                return ""
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list) and data:
                return (data[0].get("translation_text") or data[0].get("generated_text") or "").strip()
            if isinstance(data, dict):
                return (data.get("translation_text") or data.get("generated_text") or "").strip()
        except requests.exceptions.Timeout:
            print(f"      ⚠️  Timeout traduction (tentative {attempt+1}/{retries})")
            time.sleep(5)
        except Exception as e:
            print(f"      ⚠️  HF translate error: {e}")
            break
    return ""

def translate_all(articles, cfg):
    hf_key = cfg.get("hf_api_key", "")
    for a in articles:
        lang = a.get("lang_original", "EN").upper()
        if lang == "FR":
            a["summary_fr"]       = a.get("summary_original", "")
            a["lang_display"]     = "FR"
            a["translation_note"] = None
            continue
        model = HF_TRANSLATION_MODELS.get(lang)
        if not model:
            a["summary_fr"]       = a.get("summary_original", "")
            a["lang_display"]     = lang
            a["translation_note"] = f"Traduction non disponible pour {LANG_NAMES.get(lang, lang)}"
            continue
        lang_name  = LANG_NAMES.get(lang, lang.lower())
        source_txt = a.get("summary_original", "")
        translated = hf_translate(source_txt, hf_key, model) if hf_key else ""
        if translated:
            a["summary_fr"]       = translated
            a["lang_display"]     = f"{lang}→FR"
            a["translation_note"] = f"Traduit de l'{lang_name} · Helsinki-NLP/opus-mt"
        else:
            a["summary_fr"]       = source_txt
            a["lang_display"]     = lang
            a["translation_note"] = f"Traduction échouée — texte original ({lang_name})"
    return articles
