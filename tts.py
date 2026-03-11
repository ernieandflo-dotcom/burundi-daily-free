"""
modules/tts.py — FREE VERSION
Uses gTTS (Google Translate TTS) — completely free, no API key needed.
Quality is decent. Works for French natively.
"""

import os
import re

def clean_for_tts(text):
    text = re.sub(r'https?://\S+', '', text)
    text = re.sub(r'[*_`#→↗↓🌐📰🎬▸·]', '', text)
    return text.strip()

def generate_audio(articles, cfg, date_str):
    try:
        from gtts import gTTS
    except ImportError:
        print("    ⚠️  gTTS non installé. Lancez : pip install gtts")
        return articles

    tts_cfg   = cfg.get("tts", {})
    lang      = tts_cfg.get("language", "fr")
    slow      = tts_cfg.get("slow", False)
    out_dir   = os.path.join(cfg["output"]["base_dir"], date_str, "audio")
    os.makedirs(out_dir, exist_ok=True)

    for a in articles:
        summary = a.get("summary_fr", "")
        if not summary:
            continue

        spoken = f"{clean_for_tts(a['title'])}. {clean_for_tts(summary)}"
        if a.get("transcript"):
            spoken += f". Transcription : {clean_for_tts(a['transcript'][:400])}"

        try:
            tts  = gTTS(text=spoken[:3000], lang=lang, slow=slow)
            path = os.path.join(out_dir, f"article_{a['id']}_fr.mp3")
            tts.save(path)
            a["audio_path"] = path
            a["has_audio"]  = True
            print(f"      🎵 article_{a['id']}_fr.mp3")
        except Exception as e:
            print(f"      ⚠️  TTS error ({a['id']}): {e}")

    return articles
