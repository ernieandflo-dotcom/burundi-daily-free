#!/usr/bin/env python3
"""
Burundi Daily Intelligence — FREE VERSION
------------------------------------------
100% free stack:
  Search      → DuckDuckGo (free)
  Summaries   → Hugging Face BART (free tier)
  Translation → Hugging Face Helsinki-NLP (free tier)
  TTS         → gTTS via Google Translate (free, no key)
  PDF         → ReportLab (free)
  Hosting     → GitHub Pages (free)

Only secret needed: HF_API_KEY (Hugging Face — free account)
"""

import os
import sys
import yaml
from datetime import datetime


def load_config(path="config.yaml"):
    with open(path, "r") as f:
        cfg = yaml.safe_load(f)
    # Inject from GitHub Secrets / environment
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
        print("\n⚠️  HF_API_KEY manquant. Créez un compte gratuit sur huggingface.co")
        print("   → huggingface.co/settings/tokens → New token (role: Read)")
        print("   → Ajoutez-le dans GitHub Secrets sous le nom HF_API_KEY")
        sys.exit(1)

    from modules.scraper      import scrape_all
    from modules.summarizer   import summarize_articles
    from modules.translator   import translate_all
    from modules.tts          import generate_audio
    from modules.pdf_builder  import build_pdf
    from modules.card_pdf     import build_card_pdfs
    from modules.html_builder import build_html

    print("\n📡 [1/7] Collecte des articles...")
    articles = scrape_all(cfg)
    print(f"    → {len(articles)} articles collectés")

    print("\n🧠 [2/7] Résumés (BART via Hugging Face)...")
    articles = summarize_articles(articles, cfg)

    print("\n🌐 [3/7] Traduction française (Helsinki-NLP)...")
    articles = translate_all(articles, cfg)

    print("\n🎧 [4/7] Génération audio TTS (gTTS — gratuit)...")
    articles = generate_audio(articles, cfg, date_str)

    print("\n📄 [5/7] Rapport PDF principal...")
    pdf_path = build_pdf(articles, cfg, date_str, date_fr)
    print(f"    → {pdf_path}")

    print("\n🃏 [6/7] Cartes PDF individuelles...")
    articles = build_card_pdfs(articles, cfg, date_str, date_fr)

    print("\n🖥️  [7/7] Viewer HTML...")
    html_path = build_html(articles, cfg, date_str, date_fr)
    print(f"    → {html_path}")

    print(f"\n✅ Terminé ! {len(articles)} articles · 100% gratuit.")

    if cfg.get("auto_open") and os.environ.get("CI") != "true":
        import webbrowser
        webbrowser.open(f"file://{os.path.abspath(html_path)}")


if __name__ == "__main__":
    main()
