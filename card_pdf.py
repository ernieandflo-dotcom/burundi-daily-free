"""
modules/card_pdf.py
Generates individual downloadable "news cards" as PDFs.
Each card includes: summary, source, date, key figures,
key entities, and a local→regional→international relevance meter.
"""

import os
from datetime import datetime
from reportlab.lib.pagesizes import A5
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.pdfgen import canvas
from reportlab.platypus import Flowable

# ── COLOURS ──
GOLD     = colors.HexColor("#C8A84B")
DARK     = colors.HexColor("#0C0E0D")
CHARCOAL = colors.HexColor("#2A2520")
MUTED    = colors.HexColor("#888880")
LIGHT_BG = colors.HexColor("#F9F6F0")
DIVIDER  = colors.HexColor("#E0D8CC")
GREEN    = colors.HexColor("#4A9E6B")
AMBER    = colors.HexColor("#D4823A")
BLUE     = colors.HexColor("#3A72A8")

CAT_LABELS = {
    "general":   "Actualités",
    "markets":   "Marchés",
    "contracts": "Contrats Gov.",
    "ventures":  "Entrepreneurs",
}

CAT_COLORS = {
    "general":   colors.HexColor("#3A72A8"),
    "markets":   colors.HexColor("#4A9E6B"),
    "contracts": colors.HexColor("#C8A84B"),
    "ventures":  colors.HexColor("#8B5CF6"),
}

# ── RELEVANCE BAR FLOWABLE ──
class RelevanceBar(Flowable):
    """Draws a 3-segment local/regional/international relevance meter."""

    def __init__(self, local, regional, international, width=10*cm):
        super().__init__()
        self.local         = local
        self.regional      = regional
        self.international = international
        self.bar_width     = width
        self.height        = 2.2*cm
        self.width         = width

    def draw(self):
        c = self.canv
        labels   = ["Local", "Régional", "International"]
        scores   = [self.local, self.regional, self.international]
        bar_clrs = [GREEN, AMBER, BLUE]
        seg_w    = self.bar_width / 3
        bar_h    = 0.35*cm
        y_bar    = 1.3*cm
        y_label  = 0.7*cm
        y_score  = 0.1*cm

        for i, (label, score, clr) in enumerate(zip(labels, scores, bar_clrs)):
            x = i * seg_w

            # Background track
            c.setFillColor(colors.HexColor("#E8E4DC"))
            c.roundRect(x + 2, y_bar, seg_w - 6, bar_h, 2, fill=1, stroke=0)

            # Fill bar
            fill_w = max(4, (seg_w - 6) * score / 100)
            c.setFillColor(clr)
            c.roundRect(x + 2, y_bar, fill_w, bar_h, 2, fill=1, stroke=0)

            # Label
            c.setFillColor(MUTED)
            c.setFont("Courier", 6.5)
            c.drawCentredString(x + seg_w/2, y_label, label)

            # Score
            c.setFillColor(CHARCOAL)
            c.setFont("Courier-Bold", 7)
            c.drawCentredString(x + seg_w/2, y_score, f"{score}%")

# ── CARD BUILDER ──
def build_single_card(article, output_path, date_fr, model_used):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A5,
        leftMargin=1.6*cm, rightMargin=1.6*cm,
        topMargin=1.6*cm,  bottomMargin=1.6*cm,
    )

    cat   = article.get("category", "general")
    c_clr = CAT_COLORS.get(cat, GOLD)

    # ── STYLES ──
    tag_style = ParagraphStyle("Tag",
        fontName="Courier-Bold", fontSize=7, textColor=colors.white,
        spaceAfter=6, alignment=TA_LEFT,
    )
    title_style = ParagraphStyle("Title",
        fontName="Times-Bold", fontSize=14, textColor=DARK,
        leading=17, spaceAfter=8,
    )
    source_style = ParagraphStyle("Source",
        fontName="Courier", fontSize=7.5, textColor=MUTED, spaceAfter=2,
    )
    summary_style = ParagraphStyle("Summary",
        fontName="Times-Roman", fontSize=9.5, textColor=CHARCOAL,
        leading=14, spaceAfter=10,
    )
    section_style = ParagraphStyle("Section",
        fontName="Courier-Bold", fontSize=7, textColor=MUTED,
        spaceBefore=8, spaceAfter=4, letterSpacing=1,
    )
    pill_style = ParagraphStyle("Pill",
        fontName="Courier", fontSize=7.5, textColor=CHARCOAL, spaceAfter=2,
    )
    note_style = ParagraphStyle("Note",
        fontName="Courier", fontSize=6.5, textColor=MUTED,
        spaceAfter=0, alignment=TA_RIGHT,
    )

    story = []

    # ── CATEGORY TAG ──
    tag_text = f'<font color="white"><b> {CAT_LABELS.get(cat,"").upper()} </b></font>'
    # Use a table to simulate a coloured pill
    tag_table = Table(
        [[Paragraph(CAT_LABELS.get(cat,"").upper(), ParagraphStyle("T",
            fontName="Courier-Bold", fontSize=7, textColor=colors.white))]],
        colWidths=[2.2*cm], rowHeights=[0.38*cm]
    )
    tag_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), c_clr),
        ("ROUNDEDCORNERS", [3]),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 6),
        ("RIGHTPADDING", (0,0), (-1,-1), 6),
        ("TOPPADDING", (0,0), (-1,-1), 2),
        ("BOTTOMPADDING", (0,0), (-1,-1), 2),
    ]))
    story.append(tag_table)
    story.append(Spacer(1, 0.25*cm))

    # ── TITLE ──
    story.append(Paragraph(article["title"], title_style))

    # ── SOURCE LINE ──
    stars  = "★" * article["authority"] + "☆" * (5 - article["authority"])
    lang   = article.get("lang_display", "?")
    source_line = f"{article['source']}  ·  {lang}  ·  {article['time']}  ·  {stars}"
    story.append(Paragraph(source_line, source_style))
    story.append(HRFlowable(width="100%", thickness=0.5, color=DIVIDER, spaceAfter=8, spaceBefore=4))

    # ── SUMMARY ──
    story.append(Paragraph(article.get("summary_fr") or article.get("snippet", ""), summary_style))

    # ── KEY FIGURES ──
    figures = article.get("key_figures", [])
    if figures:
        story.append(Paragraph("CHIFFRES CLÉS", section_style))
        fig_data = [[Paragraph(f"▸ {fig}", pill_style) for fig in figures[:4]]]
        fig_table = Table(fig_data, colWidths=[3*cm]*min(len(figures[:4]),4))
        fig_table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,-1), colors.HexColor("#F3EFE7")),
            ("ROUNDEDCORNERS", [3]),
            ("LEFTPADDING", (0,0), (-1,-1), 5),
            ("TOPPADDING", (0,0), (-1,-1), 3),
            ("BOTTOMPADDING", (0,0), (-1,-1), 3),
        ]))
        story.append(fig_table)

    # ── KEY ENTITIES ──
    entities = article.get("key_entities", [])
    if entities:
        story.append(Paragraph("ACTEURS & INSTITUTIONS", section_style))
        ent_text = "  ·  ".join(entities[:5])
        story.append(Paragraph(ent_text, pill_style))

    # ── RELEVANCE METER ──
    story.append(Paragraph("PERTINENCE GÉOGRAPHIQUE", section_style))
    story.append(RelevanceBar(
        local=article.get("relevance_local", 70),
        regional=article.get("relevance_regional", 30),
        international=article.get("relevance_international", 10),
        width=doc.width,
    ))
    story.append(Spacer(1, 0.3*cm))

    # ── TRANSLATION NOTE ──
    if article.get("translation_note"):
        story.append(Paragraph(f"🌐 {article['translation_note']}", note_style))

    # ── SOURCE URL ──
    story.append(HRFlowable(width="100%", thickness=0.3, color=DIVIDER, spaceBefore=6, spaceAfter=4))
    footer = f"Source : {article['url'][:60]}{'…' if len(article['url'])>60 else ''}  ·  Carte générée le {date_fr}"
    story.append(Paragraph(footer, ParagraphStyle("Footer",
        fontName="Courier", fontSize=6, textColor=MUTED, alignment=TA_LEFT)))

    doc.build(story)

# ── BATCH BUILDER ──
def build_card_pdfs(articles, cfg, date_str, date_fr):
    cards_dir = os.path.join(cfg["output"]["base_dir"], date_str, "cards")
    os.makedirs(cards_dir, exist_ok=True)
    model_used = cfg["translation"]["model"]

    for a in articles:
        path = os.path.join(cards_dir, f"card_{a['id']}.pdf")
        try:
            build_single_card(a, path, date_fr, model_used)
            a["card_pdf_path"] = path
            a["card_pdf_rel"]  = f"cards/card_{a['id']}.pdf"
            print(f"      🃏 card_{a['id']}.pdf")
        except Exception as e:
            print(f"      ⚠️  Card PDF error ({a['id']}): {e}")
            a["card_pdf_path"] = None
            a["card_pdf_rel"]  = None

    return articles
