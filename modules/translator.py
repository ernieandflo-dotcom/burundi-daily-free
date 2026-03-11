"""
modules/translator.py — NO-OP VERSION
──────────────────────────────────────
Translation disabled. Summaries are kept in their original
language (EN, FR, SW, etc.) with a note indicating the source language.
No API calls. No external dependencies. Never fails.
"""

LANG_NAMES = {
    "EN": "English", "SW": "Swahili", "RN": "Kirundi",
    "FR": "Français", "PT": "Português", "AR": "Arabic",
}


def translate_all(articles, cfg):
    for a in articles:
        lang = a.get("lang_original", "EN").upper()

        # Pass summary through as-is, just set the display fields
        a["summary_fr"]       = a.get("summary_original", a.get("snippet", ""))
        a["lang_display"]     = lang
        a["translation_note"] = None if lang == "FR" else f"Original language: {LANG_NAMES.get(lang, lang)}"

    return articles
