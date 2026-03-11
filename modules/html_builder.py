"""
modules/html_builder.py
Generates the daily index.html viewer.
Injects real article data as JSON. Supports:
  - inline PDF viewer (report.pdf via <embed>)
  - individual card PDF downloads
  - audio playback
  - category tabs, relevance meters
"""

import json
import os
import shutil
from datetime import datetime

def build_html(articles, cfg, date_str, date_fr):
    out_dir  = os.path.join(cfg["output"]["base_dir"], date_str)
    os.makedirs(out_dir, exist_ok=True)
    html_path = os.path.join(out_dir, "index.html")

    # Build serialisable records
    cat_order = ["general","markets","contracts","ventures","china"]
    grouped   = {c: [] for c in cat_order}

    for a in articles:
        cat = a.get("category", "general")
        audio_rel = f"audio/article_{a['id']}_fr.mp3" if a.get("has_audio") else ""
        card_rel  = a.get("card_pdf_rel") or ""
        grouped.setdefault(cat, []).append({
            "id":            a["id"],
            "title":         a["title"],
            "source":        a["source"],
            "url":           a["url"],
            "lang":          a.get("lang_display", "?"),
            "time":          a["time"],
            "authority":     a["authority"],
            "hasAudio":      bool(a.get("has_audio")),
            "audioSrc":      audio_rel,
            "hasCard":       bool(card_rel),
            "cardSrc":       card_rel,
            "summary":       a.get("summary_fr") or a.get("snippet",""),
            "translationNote": a.get("translation_note") or "",
            "keyFigures":    a.get("key_figures", []),
            "keyEntities":   a.get("key_entities", []),
            "relevanceLocal":         a.get("relevance_local", 70),
            "relevanceRegional":      a.get("relevance_regional", 30),
            "relevanceInternational": a.get("relevance_international", 10),
            "isVideo":       a.get("is_video", False),
        })

    data = {
        "date":           date_fr,
        "generatedAt":    datetime.now().strftime("%H:%M") + " UTC",
        "totalArticles":  len(articles),
        "audioCount":     sum(1 for a in articles if a.get("has_audio")),
        "hasPdf":         os.path.exists(os.path.join(out_dir, "report.pdf")),
        **grouped,
    }
    data_json = json.dumps(data, ensure_ascii=False, indent=2)

    html = HTML_TEMPLATE.replace("/*__DATA__*/", f"const DATA = {data_json};")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    # Root index always points to today
    root_index = os.path.join(cfg["output"]["base_dir"], "index.html")
    shutil.copy(html_path, root_index)

    return html_path


# ══════════════════════════════════════════════════════════════════
#  EMBEDDED HTML TEMPLATE
# ══════════════════════════════════════════════════════════════════
HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Burundi Veille Économique</title>
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;600;700&family=JetBrains+Mono:wght@300;400;500&display=swap" rel="stylesheet">
<style>
:root{
  --gold:#C8A84B;--gold-dim:rgba(200,168,75,.12);--gold-line:rgba(200,168,75,.2);
  --bg:#0C0E0D;--text:#E2D9C8;--text-dim:#B8AFA0;--text-muted:#5A5550;
  --surface:rgba(255,255,255,.022);--border:rgba(255,255,255,.06);
  --border-gold:rgba(200,168,75,.28);--green:#7EC87E;--blue:#8BAED4;
  --violet:#A78BFA;--amber:#D4823A;
}
*{margin:0;padding:0;box-sizing:border-box}
body{background:var(--bg);color:var(--text);font-family:'Playfair Display',Georgia,serif;min-height:100vh;overflow-x:hidden}
body::before{content:'';position:fixed;inset:0;background:radial-gradient(ellipse at 15% 5%,rgba(180,120,30,.08),transparent 50%),radial-gradient(ellipse at 85% 95%,rgba(30,90,60,.1),transparent 50%);pointer-events:none;z-index:0}
.wrapper{max-width:480px;margin:0 auto;position:relative;z-index:1;min-height:100vh}

/* HEADER */
.header{position:sticky;top:0;z-index:100;background:rgba(12,14,13,.96);backdrop-filter:blur(16px);border-bottom:1px solid var(--gold-line);padding:16px 16px 12px;animation:slideDown .4s ease}
@keyframes slideDown{from{transform:translateY(-16px);opacity:0}to{transform:translateY(0);opacity:1}}
.header-top{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px}
.brand-label{font-family:'JetBrains Mono',monospace;font-size:9px;letter-spacing:.28em;color:var(--gold);text-transform:uppercase;margin-bottom:3px}
.brand-title{font-size:21px;font-weight:700;letter-spacing:-.02em;line-height:1}
.date-badge{font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--gold);border:1px solid var(--gold-line);border-radius:4px;padding:3px 9px;background:var(--gold-dim);white-space:nowrap}
.counts{font-family:'JetBrains Mono',monospace;font-size:9px;color:var(--text-muted);margin-top:4px;text-align:right}
.live-dot{display:inline-block;width:5px;height:5px;border-radius:50%;background:var(--green);margin-right:4px;animation:pulse 2s ease-in-out infinite;vertical-align:middle}
@keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.4;transform:scale(.8)}}

/* TABS */
.tabs{display:flex;gap:5px;overflow-x:auto;scrollbar-width:none;padding-bottom:2px}
.tabs::-webkit-scrollbar{display:none}
.tab{flex-shrink:0;padding:5px 11px;border-radius:20px;border:1px solid var(--border);background:transparent;color:var(--text-muted);font-family:'JetBrains Mono',monospace;font-size:10px;cursor:pointer;transition:all .18s;white-space:nowrap}
.tab:hover{border-color:var(--gold-line);color:var(--gold)}
.tab.active{border-color:rgba(200,168,75,.5);background:var(--gold-dim);color:var(--gold)}

/* NAV PILLS (main sections) */
.section-nav{display:flex;gap:6px;padding:10px 16px 0;border-top:1px solid var(--border)}
.snav-btn{flex:1;padding:7px 4px;border:1px solid var(--border);border-radius:8px;background:transparent;color:var(--text-muted);font-family:'JetBrains Mono',monospace;font-size:9px;cursor:pointer;transition:all .18s;text-align:center}
.snav-btn.active{border-color:var(--gold-line);background:var(--gold-dim);color:var(--gold)}

/* SECTIONS */
.section{display:none;padding:12px 12px 90px}
.section.active{display:block}

/* ARTICLE CARD */
.card{margin-bottom:8px;border-radius:11px;border:1px solid var(--border);background:var(--surface);overflow:hidden;transition:border-color .2s,background .2s;animation:fadeUp .35s ease both}
@keyframes fadeUp{from{transform:translateY(10px);opacity:0}to{transform:translateY(0);opacity:1}}
.card.open{border-color:var(--border-gold);background:rgba(200,168,75,.03)}
.card-head{padding:12px 14px;cursor:pointer;user-select:none}
.card-meta{display:flex;justify-content:space-between;align-items:center;margin-bottom:7px}
.meta-left{display:flex;gap:5px;align-items:center}
.lang-badge{font-family:'JetBrains Mono',monospace;font-size:8px;letter-spacing:.1em;padding:2px 6px;border-radius:3px}
.lang-fr{color:var(--blue);background:rgba(139,174,212,.1)}
.lang-trans{color:var(--green);background:rgba(126,200,126,.1)}
.lang-video{color:var(--violet);background:rgba(167,139,250,.1)}
.time-tag{font-family:'JetBrains Mono',monospace;font-size:9px;color:#3A3A3A}
.stars{display:flex;gap:3px}
.star{width:5px;height:5px;border-radius:50%;background:rgba(200,168,75,.15)}
.star.on{background:var(--gold)}
.card-title{font-size:13px;font-weight:600;line-height:1.38;margin-bottom:7px}
.card-foot{display:flex;justify-content:space-between;align-items:center}
.src-tag{font-family:'JetBrains Mono',monospace;font-size:9px;color:var(--text-muted)}
.chevron{font-size:10px;color:#404040;transition:transform .2s;display:inline-block}
.card.open .chevron{transform:rotate(180deg)}

/* EXPANDED BODY */
.card-body{display:none;padding:0 14px 14px}
.card.open .card-body{display:block}
.divider{height:1px;background:rgba(200,168,75,.1);margin-bottom:11px}
.summary-text{font-size:12.5px;line-height:1.7;color:var(--text-dim);margin-bottom:11px}
.trans-note{font-family:'JetBrains Mono',monospace;font-size:8px;color:var(--text-muted);margin-bottom:9px;font-style:italic}

/* KEY FIGURES + ENTITIES */
.pills-row{display:flex;flex-wrap:wrap;gap:5px;margin-bottom:8px}
.pill{font-family:'JetBrains Mono',monospace;font-size:9px;padding:3px 8px;border-radius:12px;white-space:nowrap}
.pill-fig{background:rgba(200,168,75,.1);color:var(--gold);border:1px solid rgba(200,168,75,.2)}
.pill-ent{background:rgba(139,174,212,.08);color:var(--blue);border:1px solid rgba(139,174,212,.18)}
.pill-label{font-family:'JetBrains Mono',monospace;font-size:8px;color:var(--text-muted);margin-bottom:4px;text-transform:uppercase;letter-spacing:.08em}

/* RELEVANCE METER */
.relevance-section{margin:10px 0 12px}
.relevance-label{font-family:'JetBrains Mono',monospace;font-size:8px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.08em;margin-bottom:7px}
.rel-bars{display:flex;flex-direction:column;gap:5px}
.rel-row{display:flex;align-items:center;gap:8px}
.rel-name{font-family:'JetBrains Mono',monospace;font-size:8px;color:var(--text-muted);width:80px;flex-shrink:0}
.rel-track{flex:1;height:5px;background:rgba(255,255,255,.06);border-radius:3px;overflow:hidden}
.rel-fill{height:100%;border-radius:3px;transition:width .6s ease}
.rel-fill.local{background:var(--green)}
.rel-fill.regional{background:var(--amber)}
.rel-fill.intl{background:var(--blue)}
.rel-pct{font-family:'JetBrains Mono',monospace;font-size:8px;color:var(--text-muted);width:28px;text-align:right;flex-shrink:0}

/* ACTIONS */
.actions{display:flex;gap:6px;flex-wrap:wrap;margin-top:4px}
.btn{display:flex;align-items:center;gap:5px;padding:6px 11px;border-radius:7px;font-family:'JetBrains Mono',monospace;font-size:10px;cursor:pointer;transition:all .16s;border:none;outline:none;text-decoration:none}
.btn-audio{border:1px solid rgba(200,168,75,.3);background:rgba(200,168,75,.05);color:var(--gold)}
.btn-audio:hover,.btn-audio.playing{background:rgba(200,168,75,.18)}
.btn-card{border:1px solid rgba(139,174,212,.25);background:rgba(139,174,212,.05);color:var(--blue)}
.btn-card:hover{background:rgba(139,174,212,.15)}
.btn-src{border:1px solid var(--border);background:transparent;color:#666}
.btn-src:hover{color:var(--text-dim);border-color:rgba(255,255,255,.14)}

/* WAVE ANIMATION */
.wave{display:none;align-items:center;gap:2px;height:12px}
.btn-audio.playing .wave{display:flex}
.btn-audio.playing .wav-lbl{display:none}
.wave span{display:block;width:2px;background:var(--gold);border-radius:2px;animation:wav .8s ease-in-out infinite}
.wave span:nth-child(1){height:4px;animation-delay:0s}
.wave span:nth-child(2){height:8px;animation-delay:.1s}
.wave span:nth-child(3){height:12px;animation-delay:.2s}
.wave span:nth-child(4){height:8px;animation-delay:.3s}
.wave span:nth-child(5){height:4px;animation-delay:.4s}
@keyframes wav{0%,100%{transform:scaleY(.5)}50%{transform:scaleY(1)}}

/* PDF VIEWER */
.pdf-section{padding:12px 12px 90px}
.pdf-toolbar{display:flex;align-items:center;justify-content:space-between;margin-bottom:10px}
.pdf-title{font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--gold)}
.pdf-dl-btn{font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--text-muted);background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:5px 10px;cursor:pointer;text-decoration:none}
.pdf-dl-btn:hover{color:var(--gold);border-color:var(--gold-line)}
.pdf-embed{width:100%;height:70vh;border:1px solid var(--border);border-radius:8px;background:#1a1a18}
.pdf-fallback{text-align:center;padding:40px;font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--text-muted)}

/* AUDIO SECTION */
.audio-section{padding:12px 12px 90px}
.audio-card{margin-bottom:8px;border:1px solid var(--border);border-radius:10px;background:var(--surface);padding:12px 14px;display:flex;align-items:center;gap:12px}
.audio-play{width:36px;height:36px;border-radius:50%;background:var(--gold-dim);border:1px solid var(--gold-line);display:flex;align-items:center;justify-content:center;cursor:pointer;flex-shrink:0;font-size:13px;transition:background .18s}
.audio-play:hover{background:rgba(200,168,75,.25)}
.audio-info{flex:1;min-width:0}
.audio-title{font-size:12px;font-weight:600;line-height:1.3;margin-bottom:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.audio-meta{font-family:'JetBrains Mono',monospace;font-size:8.5px;color:var(--text-muted)}

/* BOTTOM NAV */
.bottom-nav{position:fixed;bottom:0;left:50%;transform:translateX(-50%);width:100%;max-width:480px;background:rgba(12,14,13,.97);backdrop-filter:blur(18px);border-top:1px solid rgba(255,255,255,.05);display:flex;justify-content:space-around;padding:10px 0 16px;z-index:100}
.nav-btn{display:flex;flex-direction:column;align-items:center;gap:4px;background:none;border:none;cursor:pointer;color:#3A3530;transition:color .15s;padding:0 10px}
.nav-btn:hover,.nav-btn.active{color:var(--gold)}
.nav-icon{font-size:18px}
.nav-label{font-family:'JetBrains Mono',monospace;font-size:8px;letter-spacing:.06em;text-transform:uppercase}

.section-hdr{font-family:'JetBrains Mono',monospace;font-size:8px;letter-spacing:.3em;color:var(--text-muted);text-transform:uppercase;padding:8px 2px 7px;display:flex;align-items:center;gap:6px}
.section-line{flex:1;height:1px;background:var(--border)}
.empty{text-align:center;padding:50px 20px;font-family:'JetBrains Mono',monospace;font-size:12px;color:var(--text-muted)}
::-webkit-scrollbar{width:3px}
::-webkit-scrollbar-thumb{background:rgba(200,168,75,.15);border-radius:3px}
</style>
</head>
<body>
<div class="wrapper">

<!-- HEADER -->
<div class="header">
  <div class="header-top">
    <div>
      <div class="brand-label">Burundi Intelligence</div>
      <div class="brand-title">Veille Économique</div>
    </div>
    <div>
      <div class="date-badge" id="hdr-date">—</div>
      <div class="counts"><span class="live-dot"></span><span id="hdr-counts">—</span></div>
    </div>
  </div>
  <div class="tabs" id="tabs">
    <button class="tab active" onclick="switchTab('general',this)">📰 Actualités</button>
    <button class="tab" onclick="switchTab('markets',this)">📈 Marchés</button>
    <button class="tab" onclick="switchTab('contracts',this)">🏛️ Contrats</button>
    <button class="tab" onclick="switchTab('ventures',this)">🌱 Entrepreneurs</button>
    <button class="tab" onclick="switchTab('china',this)">🇨🇳 Chine</button>
  </div>
</div>

<!-- NEWS SECTION -->
<div class="section active" id="sec-news">
  <div id="article-container"></div>
</div>

<!-- PDF SECTION -->
<div class="section" id="sec-pdf">
  <div class="pdf-section">
    <div class="pdf-toolbar">
      <span class="pdf-title">📄 Rapport du jour</span>
      <a class="pdf-dl-btn" id="pdf-dl" href="report.pdf" download>↓ Télécharger</a>
    </div>
    <embed class="pdf-embed" id="pdf-embed" src="report.pdf" type="application/pdf">
    <div class="pdf-fallback" id="pdf-fallback" style="display:none">
      PDF non disponible — lancez d'abord le script Python.<br><br>
      <a href="report.pdf" style="color:var(--gold)">Essayer quand même ↗</a>
    </div>
  </div>
</div>

<!-- AUDIO SECTION -->
<div class="section" id="sec-audio">
  <div class="audio-section" id="audio-container"></div>
</div>

<!-- BOTTOM NAV -->
<nav class="bottom-nav">
  <button class="nav-btn active" onclick="setNav('news',this)">
    <span class="nav-icon">🏠</span><span class="nav-label">Accueil</span>
  </button>
  <button class="nav-btn" onclick="setNav('pdf',this)">
    <span class="nav-icon">📄</span><span class="nav-label">PDF</span>
  </button>
  <button class="nav-btn" onclick="setNav('audio',this)">
    <span class="nav-icon">🎧</span><span class="nav-label">Audio</span>
  </button>
</nav>

</div><!-- /wrapper -->

<script>
/*__DATA__*/

// ── STATE ──
let currentTab   = 'general';
let openCard     = null;
let currentAudio = null;
let audioEl      = new Audio();

// ── INIT ──
document.getElementById('hdr-date').textContent   = DATA.date || '—';
document.getElementById('hdr-counts').textContent =
  `${DATA.totalArticles||0} articles · ${DATA.audioCount||0} audio`;

renderArticles('general');
renderAudio();

// ── ARTICLE RENDERING ──
function renderArticles(tab) {
  const container = document.getElementById('article-container');
  const arts      = DATA[tab] || [];
  container.innerHTML = '';

  if (!arts.length) {
    container.innerHTML = '<div class="empty">Aucun article aujourd\'hui.</div>';
    return;
  }

  const labels = {
    general:'Actualités du jour', markets:'Marchés & Entreprises',
    contracts:"Marchés publics & Appels d'offres", ventures:'Nouvelles Ventures',
    china:'Intelligence Chine–Burundi'
  };
  const hdr = document.createElement('div');
  hdr.className = 'section-hdr';
  hdr.innerHTML = `<span>${labels[tab]||tab}</span><div class="section-line"></div>`;
  container.appendChild(hdr);

  arts.forEach((a, idx) => {
    const card = document.createElement('div');
    card.className = 'card';
    card.id = 'card-' + a.id;
    card.style.animationDelay = (idx * 0.06) + 's';

    const langCls = a.isVideo ? 'lang-video' : a.lang.includes('→') ? 'lang-trans' : 'lang-fr';
    const langLabel = a.isVideo ? '🎬 VIDEO' : a.lang;
    const stars = [1,2,3,4,5].map(i =>
      `<div class="star ${i<=a.authority?'on':''}"></div>`).join('');

    // Key figures pills
    const figPills = (a.keyFigures||[]).map(f =>
      `<span class="pill pill-fig">${f}</span>`).join('');
    const entPills = (a.keyEntities||[]).map(e =>
      `<span class="pill pill-ent">${e}</span>`).join('');

    // Relevance bars
    const relevance = `
      <div class="relevance-section">
        <div class="relevance-label">Pertinence géographique</div>
        <div class="rel-bars">
          <div class="rel-row">
            <span class="rel-name">Local</span>
            <div class="rel-track"><div class="rel-fill local" style="width:${a.relevanceLocal}%"></div></div>
            <span class="rel-pct">${a.relevanceLocal}%</span>
          </div>
          <div class="rel-row">
            <span class="rel-name">Régional</span>
            <div class="rel-track"><div class="rel-fill regional" style="width:${a.relevanceRegional}%"></div></div>
            <span class="rel-pct">${a.relevanceRegional}%</span>
          </div>
          <div class="rel-row">
            <span class="rel-name">International</span>
            <div class="rel-track"><div class="rel-fill intl" style="width:${a.relevanceInternational}%"></div></div>
            <span class="rel-pct">${a.relevanceInternational}%</span>
          </div>
        </div>
      </div>`;

    const audioBtn = a.hasAudio ? `
      <button class="btn btn-audio" id="abtn-${a.id}" onclick="toggleAudio('${a.id}','${a.audioSrc}',event)">
        <span class="wav-lbl">▶ Audio FR</span>
        <span class="wave"><span></span><span></span><span></span><span></span><span></span></span>
      </button>` : '';

    const cardBtn = a.hasCard ? `
      <a class="btn btn-card" href="${a.cardSrc}" download>🃏 Carte PDF</a>` : '';

    const transNote = a.translationNote ?
      `<div class="trans-note">🌐 ${a.translationNote}</div>` : '';

    card.innerHTML = `
      <div class="card-head" onclick="toggleCard('${a.id}')">
        <div class="card-meta">
          <div class="meta-left">
            <span class="lang-badge ${langCls}">${langLabel}</span>
            <span class="time-tag">${a.time}</span>
          </div>
          <div class="stars">${stars}</div>
        </div>
        <div class="card-title">${a.title}</div>
        <div class="card-foot">
          <span class="src-tag">${a.source}</span>
          <span class="chevron">▼</span>
        </div>
      </div>
      <div class="card-body">
        <div class="divider"></div>
        <p class="summary-text">${a.summary}</p>
        ${transNote}
        ${figPills ? `<div class="pill-label">Chiffres clés</div><div class="pills-row">${figPills}</div>` : ''}
        ${entPills ? `<div class="pill-label">Acteurs</div><div class="pills-row">${entPills}</div>` : ''}
        ${relevance}
        <div class="actions">
          ${audioBtn}
          ${cardBtn}
          <a class="btn btn-src" href="${a.url}" target="_blank">↗ Source</a>
        </div>
      </div>`;

    container.appendChild(card);
  });
}

// ── AUDIO SECTION ──
function renderAudio() {
  const container = document.getElementById('audio-container');
  const all = ['general','markets','contracts','ventures','china'].flatMap(c => DATA[c]||[]).filter(a => a.hasAudio);

  if (!all.length) {
    container.innerHTML = '<div class="empty">Aucun audio disponible aujourd\'hui.</div>';
    return;
  }

  const hdr = document.createElement('div');
  hdr.className = 'section-hdr';
  hdr.innerHTML = `<span>Tous les audios FR</span><div class="section-line"></div>`;
  container.appendChild(hdr);

  all.forEach(a => {
    const card = document.createElement('div');
    card.className = 'audio-card';
    card.innerHTML = `
      <div class="audio-play" onclick="toggleAudio('${a.id}','${a.audioSrc}',event)" id="aplay-${a.id}">▶</div>
      <div class="audio-info">
        <div class="audio-title">${a.title}</div>
        <div class="audio-meta">${a.source} · ${a.time} · FR</div>
      </div>`;
    container.appendChild(card);
  });
}

// ── INTERACTIONS ──
function toggleCard(id) {
  const card = document.getElementById('card-' + id);
  const wasOpen = card.classList.contains('open');
  document.querySelectorAll('.card.open').forEach(c => c.classList.remove('open'));
  if (!wasOpen) {
    card.classList.add('open');
    setTimeout(() => card.scrollIntoView({behavior:'smooth', block:'nearest'}), 50);
  }
}

function toggleAudio(id, src, e) {
  e && e.stopPropagation();
  const btn   = document.getElementById('abtn-' + id);
  const play  = document.getElementById('aplay-' + id);
  const isPlaying = currentAudio === id && !audioEl.paused;

  // Stop all visual states
  document.querySelectorAll('.btn-audio.playing').forEach(b => b.classList.remove('playing'));
  document.querySelectorAll('.audio-play').forEach(p => p.textContent = '▶');

  if (isPlaying) {
    audioEl.pause();
    currentAudio = null;
  } else {
    if (currentAudio !== id) {
      audioEl.src = src;
      audioEl.load();
    }
    audioEl.play().catch(()=>{});
    currentAudio = id;
    if (btn) btn.classList.add('playing');
    if (play) play.textContent = '⏸';
  }
}

audioEl.onended = () => {
  document.querySelectorAll('.btn-audio.playing').forEach(b => b.classList.remove('playing'));
  document.querySelectorAll('.audio-play').forEach(p => p.textContent = '▶');
  currentAudio = null;
};

function switchTab(tab, el) {
  currentTab = tab;
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  el.classList.add('active');
  renderArticles(tab);
  document.getElementById('sec-news').scrollTop = 0;
}

function setNav(section, el) {
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  el.classList.add('active');
  document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));
  document.getElementById('sec-' + section).classList.add('active');
  // Show/hide tabs
  document.querySelector('.header .tabs').style.display = section === 'news' ? 'flex' : 'none';
}

// Check if PDF exists (graceful fallback)
fetch('report.pdf', {method:'HEAD'}).catch(() => {
  document.getElementById('pdf-embed').style.display   = 'none';
  document.getElementById('pdf-fallback').style.display = 'block';
});
</script>
</body>
</html>"""
