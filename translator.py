"""
modules/translator.py — FREE VERSION
Uses Helsinki-NLP translation models via Hugging Face Inference API (free).
  EN → FR : Helsinki-NLP/opus-mt-en-fr
  SW → FR : Helsinki-NLP/opus-mt-swc-fr
  Others  : fallback — keep original + note
"""

import requests

HF_API_URL = "https://api-inference.huggingface.co/models"

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

def hf_translate(text, hf_key, model):
    headers = {"Authorization": f"Bearer {hf_key}"}
    payload = {
        "inputs": text[:512],
        "options": {"wait_for_model": True},
    }
    try:
        resp = requests.post(f"{HF_API_URL}/{model}", headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, list) and data:
            return data[0].get("translation_text", "").strip()
    except Exception as e:
        print(f"      ⚠️  HF translate error: {e}")
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
            # No model for this language — keep as-is with note
            a["summary_fr"]       = a.get("summary_original", "")
            a["lang_display"]     = lang
            a["translation_note"] = f"Traduction non disponible pour {LANG_NAMES.get(lang, lang)}"
            continue

        lang_name = LANG_NAMES.get(lang, lang.lower())
        translated = hf_translate(a.get("summary_original", ""), hf_key, model)

        if translated:
            a["summary_fr"]       = translated
            a["lang_display"]     = f"{lang}→FR"
            a["translation_note"] = f"Traduit de l'{lang_name} · Helsinki-NLP/opus-mt"
        else:
            # Fallback: keep original
            a["summary_fr"]       = a.get("summary_original", "")
            a["lang_display"]     = lang
            a["translation_note"] = f"Traduction échouée — texte original ({lang_name})"

    return articles
