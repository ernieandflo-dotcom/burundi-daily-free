"""
modules/pdf_builder.py
Builds the master daily PDF report (all articles, grouped by category).
"""

import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, HRFlowable, PageBreak, Table, TableStyle
)

GOLD    = colors.HexColor("#C8A84B")
DARK    = colors.HexColor("#0C0E0D")
MUTED   = colors.HexColor("#888880")
CHARCOAL= colors.HexColor("#2A2520")
DIVIDER = colors.HexColor("#E0D8CC")

CAT_LABELS = {
    "general":   "ACTUALITÉS GÉNÉRALES",
    "markets":   "MARCHÉS & ENTREPRISES",
    "contracts": "CONTRATS GOUVERNEMENTAUX",
    "ventures":  "NOUVELLES VENTURES & ENTREPRENEURS",
}
CATEGORY_ORDER = ["general","markets","contracts","ventures"]

def build_pdf(articles, cfg, date_str, date_fr):
    out_dir  = os.path.join(cfg["output"]["base_dir"], date_str)
    os.makedirs(out_dir, exist_ok=True)
    pdf_path = os.path.join(out_dir, "report.pdf")

    doc = SimpleDocTemplate(
        pdf_path, pagesize=A4,
        leftMargin=2.2*cm, rightMargin=2.2*cm,
        topMargin=2.5*cm,  bottomMargin=2.5*cm,
    )

    # ── STYLES ──
    def S(name, **kw):
        return ParagraphStyle(name, **kw)

    brand_s   = S("Brand",  fontName="Courier-Bold", fontSize=9, textColor=GOLD, letterSpacing=3)
    title_s   = S("Title",  fontName="Times-Bold",   fontSize=28, textColor=DARK, leading=32, spaceAfter=4)
    date_s    = S("Date",   fontName="Times-Roman",  fontSize=11, textColor=MUTED, spaceAfter=16)
    cat_s     = S("Cat",    fontName="Courier-Bold", fontSize=8,  textColor=GOLD, spaceBefore=20, spaceAfter=6, letterSpacing=2)
    art_tit_s = S("ArtTit", fontName="Times-Bold",   fontSize=13, textColor=DARK, leading=16, spaceBefore=14, spaceAfter=4)
    meta_s    = S("Meta",   fontName="Courier",      fontSize=8,  textColor=MUTED, spaceAfter=6)
    body_s    = S("Body",   fontName="Times-Roman",  fontSize=10.5, textColor=CHARCOAL, leading=16, spaceAfter=8)
    fig_s     = S("Fig",    fontName="Courier-Bold", fontSize=8,  textColor=CHARCOAL)
    ent_s     = S("Ent",    fontName="Courier",      fontSize=8,  textColor=CHARCOAL, spaceAfter=4)
    note_s    = S("Note",   fontName="Courier",      fontSize=7.5, textColor=MUTED, spaceAfter=4, leftIndent=8)
    trans_s   = S("Trans",  fontName="Times-Italic", fontSize=9,  textColor=colors.HexColor("#4A4540"),
                             leading=13, spaceAfter=6, leftIndent=12, rightIndent=12)

    story = []

    # ── COVER ──
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph("BURUNDI", brand_s))
    story.append(Paragraph("Veille Économique", title_s))
    story.append(Paragraph(date_fr, date_s))
    story.append(HRFlowable(width="100%", thickness=1.5, color=GOLD, spaceAfter=6))
    story.append(Paragraph(
        f"{len(articles)} articles · Résumés FR · Modèle : {cfg['translation']['model']}",
        S("Sub", fontName="Courier", fontSize=8, textColor=MUTED, spaceAfter=24)
    ))

    # ── ARTICLES BY CATEGORY ──
    grouped = {c: [] for c in CATEGORY_ORDER}
    for a in articles:
        grouped.setdefault(a.get("category","general"), []).append(a)

    for cat in CATEGORY_ORDER:
        arts = grouped.get(cat, [])
        if not arts:
            continue

        story.append(Paragraph(f"── {CAT_LABELS[cat]} ──", cat_s))
        story.append(HRFlowable(width="100%", thickness=0.5, color=DIVIDER, spaceAfter=4))

        for a in arts:
            story.append(Paragraph(a["title"], art_tit_s))

            stars = "★" * a["authority"] + "☆" * (5 - a["authority"])
            story.append(Paragraph(
                f"{a['source']}  ·  {a.get('lang_display','?')}  ·  {a['time']}  ·  {stars}",
                meta_s
            ))

            if a.get("summary_fr"):
                story.append(Paragraph(a["summary_fr"], body_s))

            # Key figures inline
            figs = a.get("key_figures", [])
            if figs:
                story.append(Paragraph("Chiffres clés : " + "  ·  ".join(figs), fig_s))

            # Key entities inline
            ents = a.get("key_entities", [])
            if ents:
                story.append(Paragraph("Acteurs : " + "  ·  ".join(ents), ent_s))

            # Relevance
            story.append(Paragraph(
                f"Pertinence → Local : {a.get('relevance_local',0)}%  "
                f"| Régional : {a.get('relevance_regional',0)}%  "
                f"| International : {a.get('relevance_international',0)}%",
                note_s
            ))

            if a.get("translation_note"):
                story.append(Paragraph(f"🌐 {a['translation_note']}", note_s))

            if a.get("transcript"):
                story.append(Paragraph("Transcription :", S("TH",
                    fontName="Courier-Bold", fontSize=7.5, textColor=MUTED, spaceBefore=4, spaceAfter=2)))
                story.append(Paragraph(a["transcript"][:1000] + "…", trans_s))

            story.append(HRFlowable(width="55%", thickness=0.3, color=DIVIDER,
                                    spaceAfter=2, spaceBefore=6))

    doc.build(story)
    return pdf_path
