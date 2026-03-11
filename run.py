#!/usr/bin/env python3
"""
Burundi Daily Intelligence — FREE VERSION
------------------------------------------
  Search    → DuckDuckGo (free)
  Summaries → Hugging Face BART (free tier)
  TTS       → gTTS via Google Translate (free, no key)
  Hosting   → GitHub Pages (free)
"""

import os
import sys
import yaml
from datetime import datetime


def load_config(path="config.yaml"):
    with open(path, "r") as f:
        cfg = yaml.safe_load(f)
    cfg["hf_api_key"] = os.environ.get("HF_API_KEY", cfg.get("hf_api_key", ""))
    return cfg


def main():
    cfg      = load_config()
    date_str = datetime.now().strftime("%Y-%m-%d")
    date_fr  = datetime.now().strftime("%-d %B %Y")

    print(f"\n🌍 Burundi Daily Intelligence — VERSION GRATUITE")
    print(f"📅 {date_str}  |  ⏰ {datetime.now().strftime('%H:%M')} UTC")
    print("=" * 52)

    if not cfg.get("hf_api_key"):
        print("\n⚠️  HF_API_KEY manquant.")
        sys.exit(1)

    from modules.scraper      import scrape_all
    from modules.summarizer   import summarize_articles
    from modules.translator   import translate_all
    from modules.tts          import generate_audio
    from modules.html_builder import build_html

    print("\n📡 [1/5] Collecte des articles...")
    articles = scrape_all(cfg)
    print(f"    → {len(articles)} articles collectés")

    print("\n🧠 [2/5] Résumés (BART via Hugging Face)...")
    articles = summarize_articles(articles, cfg)

    print("\n🌐 [3/5] Langue originale conservée...")
    articles = translate_all(articles, cfg)

    print("\n🎧 [4/5] Génération audio TTS (gTTS — gratuit)...")
    articles = generate_audio(articles, cfg, date_str)

    print("\n🖥️  [5/5] Viewer HTML...")
    html_path = build_html(articles, cfg, date_str, date_fr)
    print(f"    → {html_path}")

    print(f"\n✅ Terminé ! {len(articles)} articles.")

    if cfg.get("auto_open") and os.environ.get("CI") != "true":
        import webbrowser
        webbrowser.open(f"file://{os.path.abspath(html_path)}")


if __name__ == "__main__":
    main()
