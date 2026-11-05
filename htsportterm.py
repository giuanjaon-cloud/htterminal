import datetime
import json
import os
import re
import sys
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

import requests
from bs4 import BeautifulSoup

BASE_SITE = "https://www.htsport.org/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
    "Cache-Control": "no-cache",
}

# ---------------------------------------------------------------------------
# HTML TEMPLATE: STILE DAZN CON HISTORY API (RITORNO ALLE OPZIONI CORRETTO)
# ---------------------------------------------------------------------------
HTML_TEMPLATE = r'''<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#000000">
<meta name="referrer" content="no-referrer">
<title>PALINSESTO - __DATE_PLACEHOLDER__</title>
<link href="https://fonts.googleapis.com/css2?family=Roboto+Condensed:wght@400;700&family=Roboto:wght@400;500;700&display=swap" rel="stylesheet">
<style>
  :root {
    --bg-main: #000000;
    --bg-surface: #111111;
    --bg-surface-hover: #1c1c1c;
    --accent: #edff00; /* Giallo fluo stile DAZN */
    --text-primary: #ffffff;
    --text-secondary: #aaaaaa;
    --border-color: #222222;
    --font-head: 'Roboto Condensed', sans-serif;
    --font-body: 'Roboto', sans-serif;
  }
  
  * { box-sizing: border-box; -webkit-tap-highlight-color: transparent; margin: 0; padding: 0; }
  
  body {
    background: var(--bg-main);
    color: var(--text-primary);
    font-family: var(--font-body);
    padding: max(20px, env(safe-area-inset-top)) max(20px, env(safe-area-inset-right)) max(20px, env(safe-area-inset-bottom)) max(20px, env(safe-area-inset-left));
    min-height: 100vh;
    -webkit-font-smoothing: antialiased;
    overflow-x: hidden;
  }
  
  .container { max-width: 1400px; margin: 0 auto; transition: opacity 0.3s; }
  
  /* Header */
  .header-wrap { display: flex; flex-direction: column; gap: 15px; margin-bottom: 30px; }
  .logo-text {
    font-family: var(--font-head);
    font-size: clamp(32px, 5vw, 48px);
    font-weight: 700;
    color: var(--text-primary);
    letter-spacing: -1px;
    text-transform: uppercase;
  }
  .logo-text span { color: var(--accent); font-size: 0.6em; margin-left: 10px; vertical-align: middle; }
  
  /* Controls */
  .controls { 
    display: flex; flex-wrap: wrap; gap: 20px; align-items: center; justify-content: space-between; 
    padding-bottom: 20px; border-bottom: 2px solid var(--border-color); 
  }
  
  .select-wrapper { position: relative; min-width: 250px; max-width: 350px; flex-grow: 1; }
  .select-wrapper select {
    width: 100%; appearance: none; background: var(--bg-surface); color: var(--text-primary);
    border: 2px solid var(--border-color); padding: 14px 20px; border-radius: 4px;
    font-family: var(--font-head); font-size: 16px; font-weight: 700; text-transform: uppercase; 
    cursor: pointer; transition: all 0.2s ease; outline: none;
  }
  .select-wrapper select:focus, .select-wrapper select:hover { 
    border-color: var(--accent); background: var(--bg-surface-hover); 
  }
  .select-wrapper::after { 
    content: "▼"; position: absolute; right: 20px; top: 50%; transform: translateY(-50%); 
    color: var(--text-primary); font-size: 12px; pointer-events: none; 
  }
  
  .status-text { 
    font-family: var(--font-head); font-size: 16px; font-weight: 700; color: var(--text-secondary); 
    text-transform: uppercase; display: flex; align-items: center; gap: 8px;
  }
  .status-text .count { color: var(--text-primary); font-size: 20px; }

  /* Sections */
  .section-container { margin-top: 35px; }
  .section-title {
    font-family: var(--font-head);
    font-size: 24px;
    font-weight: 700;
    color: var(--text-primary);
    text-transform: uppercase;
    margin-bottom: 20px;
    border-left: 4px solid var(--accent);
    padding-left: 12px;
    line-height: 1.1;
  }

  /* Grid */
  .grid { 
    display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); 
    gap: 20px; 
  }
  
  /* Cards */
  .card {
    display: flex; flex-direction: column; background: var(--bg-surface);
    border: 2px solid transparent; border-radius: 8px; overflow: hidden;
    text-decoration: none; color: var(--text-primary); text-align: left;
    transition: all 0.2s ease; cursor: pointer; position: relative;
    min-height: 160px; outline: none; width: 100%;
  }
  .card:hover, .card:focus-visible {
    transform: translateY(-4px); border-color: var(--accent);
    background: var(--bg-surface-hover);
    box-shadow: 0 10px 20px rgba(0,0,0,0.5);
  }
  
  .card-header { 
    padding: 12px 16px; border-bottom: 1px solid var(--border-color); 
    display: flex; justify-content: space-between; align-items: center; 
  }
  .league { 
    font-family: var(--font-head); font-size: 13px; font-weight: 700; color: var(--text-secondary);
    text-transform: uppercase; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; padding-right: 10px;
  }
  
  .time-badge { 
    font-family: var(--font-head); font-size: 13px; font-weight: 700; color: var(--text-primary); 
    background: var(--border-color); padding: 4px 10px; border-radius: 4px; display: inline-block;
    letter-spacing: 1px;
  }
  .time-badge.live-active { background: #e50000; }
  .time-badge.badge-247 { background: transparent; border: 1px solid var(--border-color); color: var(--text-secondary); }
  
  .card-body { 
    padding: 20px 16px; flex-grow: 1; display: flex; flex-direction: column; 
    align-items: center; justify-content: center; text-align: center; gap: 12px;
  }
  .team-logos {
    display: flex; align-items: center; justify-content: center; gap: 15px; margin-bottom: 5px;
  }
  .team-logo {
    width: 45px; height: 45px; object-fit: contain;
    filter: drop-shadow(0 2px 4px rgba(0,0,0,0.5));
  }
  .match-title { 
    font-family: var(--font-head); font-size: 20px; font-weight: 700; line-height: 1.2; 
    display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; 
  }
  
  .card-footer { 
    padding: 12px 16px; background: rgba(0,0,0,0.4); 
    display: flex; justify-content: space-between; align-items: center; border-top: 1px solid var(--border-color);
  }
  .source-count { font-size: 13px; color: var(--text-secondary); font-weight: 500; }
  .play-btn { 
    font-family: var(--font-head); font-size: 14px; font-weight: 700; color: var(--bg-main); 
    background: var(--text-primary); padding: 6px 16px; border-radius: 4px; 
    transition: all 0.2s ease; text-transform: uppercase; display: inline-block;
  }
  .card:hover .play-btn, .card:focus-visible .play-btn { background: var(--accent); }

  /* MODAL SORGENTI */
  .modal-overlay {
    position: fixed; inset: 0; background: rgba(0, 0, 0, 0.9);
    display: none; align-items: center; justify-content: center; z-index: 1000; padding: 20px;
  }
  .modal-overlay.active { display: flex; }
  .modal-content {
    background: var(--bg-surface); border: 2px solid var(--border-color); border-radius: 8px;
    width: 100%; max-width: 500px; padding: 25px;
    display: flex; flex-direction: column; gap: 20px; max-height: 85vh;
  }
  .modal-title { font-family: var(--font-head); font-size: 24px; font-weight: 700; text-transform: uppercase; margin-bottom: 5px; color: var(--text-primary); text-align: center;}
  .sources-list { display: flex; flex-direction: column; gap: 10px; overflow-y: auto; padding-right: 5px; }
  
  .source-btn {
    background: var(--bg-main); border: 2px solid var(--border-color); border-radius: 6px;
    padding: 14px; color: var(--text-primary); font-family: var(--font-body); font-size: 15px; font-weight: 500;
    text-align: left; cursor: pointer; transition: all 0.2s; outline: none; text-decoration: none;
    display: flex; justify-content: space-between; align-items: center; width: 100%;
  }
  .source-btn:hover, .source-btn:focus-visible {
    border-color: var(--accent); background: #1a1a1a;
  }
  .source-btn::after {
      content: "►"; color: var(--accent); font-size: 12px; opacity: 0; transition: opacity 0.2s;
  }
  .source-btn:hover::after, .source-btn:focus-visible::after { opacity: 1; }

  .close-modal {
    margin-top: 10px; background: transparent; border: 2px solid var(--text-secondary);
    color: var(--text-secondary); padding: 12px; border-radius: 6px; cursor: pointer;
    font-family: var(--font-head); font-weight: 700; font-size: 16px; text-transform: uppercase; outline: none;
    transition: all 0.2s; width: 100%; text-align: center; text-decoration: none; display: block;
  }
  .close-modal:focus-visible, .close-modal:hover { border-color: var(--text-primary); color: var(--text-primary); }

  /* PLAYER PULITO A SCHERMO INTERO */
  #clean-player-container {
    position: fixed; inset: 0; background: #000; z-index: 9999; display: none;
  }
  #clean-player-iframe { width: 100%; height: 100%; border: none; }
  .close-player-btn {
    position: absolute; top: 20px; right: 20px; background: rgba(0,0,0,0.7); border: 2px solid var(--text-secondary);
    color: var(--text-primary); width: 44px; height: 44px; border-radius: 50%; font-size: 18px; font-weight: bold;
    cursor: pointer; z-index: 10000; display: flex; align-items: center; justify-content: center;
    transition: all 0.2s; outline: none;
  }
  .close-player-btn:hover, .close-player-btn:focus-visible {
    border-color: var(--accent); color: var(--accent); transform: scale(1.1);
  }

  @media (max-width: 600px) {
    body { padding: 15px; }
    .logo-text { font-size: 32px; }
    .grid { grid-template-columns: 1fr; gap: 15px; }
    .select-wrapper { min-width: 100%; }
    .controls { flex-direction: column; align-items: stretch; gap: 15px; }
    .status-text { justify-content: flex-end; }
  }
</style>
<script type="application/json" id="fallback-data">__DATA_PLACEHOLDER__</script>
</head>
<body>

<div class="container" id="main-ui">
  <div class="header-wrap">
    <h1 class="logo-text">PALINSESTO <span>__DATE_PLACEHOLDER__</span></h1>
    
    <div class="controls">
      <div class="select-wrapper">
        <select id="league" aria-label="Filtra per competizione">
          <option value="all">TUTTI GLI EVENTI</option>
        </select>
      </div>
      <div class="status-text">
        EVENTI LIVE: <span class="count" id="event-count">0</span>
      </div>
    </div>
  </div>

  <div id="channels-section" class="section-container" style="display: none;">
    <h2 class="section-title">CANALI 24/7</h2>
    <main class="grid" id="channels-grid"></main>
  </div>

  <div id="events-section" class="section-container" style="margin-top: 50px;">
    <h2 class="section-title">EVENTI LIVE</h2>
    <main class="grid" id="events-grid">
      <div style="color:var(--text-secondary); font-size:18px; text-align:center; grid-column:1/-1; padding:40px;">Caricamento in corso...</div>
    </main>
  </div>
</div>

<div class="modal-overlay" id="source-modal">
  <div class="modal-content">
    <div class="modal-title" id="modal-title">Scegli canale</div>
    <div class="sources-list" id="sources-list"></div>
    <button class="close-modal" id="close-modal">Annulla</button>
  </div>
</div>

<div id="clean-player-container">
  <!-- L'iframe viene generato dinamicamente per distruggerlo e riavviarlo pulito -->
</div>

<script>
(() => {
  "use strict";
  const $ = id => document.getElementById(id);
  const el = {
    mainUI: $("main-ui"),
    eventsGrid: $("events-grid"),
    channelsGrid: $("channels-grid"),
    channelsSection: $("channels-section"),
    league: $("league"),
    count: $("event-count"),
    modal: $("source-modal"),
    modalTitle: $("modal-title"),
    sourcesList: $("sources-list"),
    closeModal: $("close-modal"),
    playerContainer: $("clean-player-container")
  };

  let allEvents = [];
  let shownEvents = [];
  let lastFocusedElement = null;

  const escapeHTML = value => String(value ?? "").replace(/[&<>"']/g, ch =>
    ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[ch])
  );

  const getSources = ev => Array.isArray(ev.sources)
    ? ev.sources.filter(s => s && typeof s.url === "string" && /^https?:\/\//i.test(s.url))
    : [];

  window.saveFocus = function(element) {
      lastFocusedElement = element;
  };

  // ==========================================
  // DISTRUZIONE IFRAME E MULTI-HISTORY STATE
  // ==========================================

  // Inizializza lo stato Home
  history.replaceState({ view: 'home' }, "", "");

  window.launchPlayer = function(url) {
    // Aggiungi un nuovo step alla cronologia che dice "siamo nel player"
    history.pushState({ view: 'player' }, "", "");

    // Distrugge qualsiasi vecchio iframe
    el.playerContainer.innerHTML = '';

    // Ricrea il bottone di chiusura (chiama solo history.back() per uniformità)
    const closeBtn = document.createElement('button');
    closeBtn.className = 'close-player-btn';
    closeBtn.title = 'Chiudi Player';
    closeBtn.innerHTML = '✕';
    closeBtn.onclick = (e) => { e.preventDefault(); history.back(); };
    el.playerContainer.appendChild(closeBtn);

    // Ricrea l'iframe fisicamente
    const iframe = document.createElement('iframe');
    iframe.id = 'clean-player-iframe';
    iframe.allowFullscreen = true;
    iframe.allow = "autoplay; fullscreen; encrypted-media";
    
    if (!url.toLowerCase().includes("matchora")) {
      iframe.setAttribute("sandbox", "allow-scripts allow-same-origin allow-presentation allow-forms");
    }
    iframe.src = url;
    el.playerContainer.appendChild(iframe);

    // Nasconde modale e main, mostra player
    el.modal.classList.remove("active");
    el.mainUI.style.display = "none";
    el.playerContainer.style.display = "block";
    closeBtn.focus();
  };

  window.openModalGlobal = function(event, eventIndex) {
      event.preventDefault();
      lastFocusedElement = event.currentTarget;
      
      // Aggiunge uno step "modale" nella cronologia
      history.pushState({ view: 'modal' }, "", "");
      
      const ev = shownEvents[eventIndex];
      const sources = getSources(ev);
      
      el.modalTitle.textContent = ev.title || "Seleziona Canale";
      el.sourcesList.innerHTML = "";
      
      sources.forEach((src, idx) => {
        const btn = document.createElement("button");
        btn.className = "source-btn";
        btn.textContent = src.name || `Opzione ${idx + 1}`;
        btn.onclick = () => launchPlayer(src.url);
        el.sourcesList.appendChild(btn);
      });

      el.mainUI.style.display = "block"; // La UI deve restare visibile in background
      el.modal.classList.add("active");
      
      const firstBtn = el.sourcesList.querySelector("button");
      if(firstBtn) firstBtn.focus();
  };

  window.launchSingleStream = function(event, url) {
      event.preventDefault();
      lastFocusedElement = event.currentTarget;
      launchPlayer(url);
  };

  // GESTORE DEL TASTO INDIETRO E DEI CAMBI DI STATO
  window.addEventListener("popstate", (e) => {
      const state = e.state;
      
      // Abbatti SEMPRE l'iframe appena l'utente preme Indietro
      el.playerContainer.innerHTML = '';
      el.playerContainer.style.display = "none";
      
      if (!state || state.view === 'home') {
          // Tornati alla griglia principale
          el.modal.classList.remove("active");
          el.mainUI.style.display = "block";
          if (lastFocusedElement) { lastFocusedElement.focus(); }
      } 
      else if (state.view === 'modal') {
          // Tornati alle opzioni (perché si è chiuso il player)
          el.mainUI.style.display = "block"; // Il palinsesto è sotto la modale
          el.modal.classList.add("active");
          const firstBtn = el.sourcesList.querySelector("button");
          if(firstBtn) firstBtn.focus();
      }
  });

  // Tasto Annulla Modale (simula tasto back telecomando)
  el.closeModal.addEventListener("click", (e) => {
      e.preventDefault();
      history.back();
  });

  // Tasti TV o Tastiera (Esc, Backspace, Tizen Back)
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" || e.key === "Backspace" || e.keyCode === 10009) {
      if (el.playerContainer.style.display === "block" || el.modal.classList.contains("active")) {
          e.preventDefault();
          history.back();
      }
    }
  });


  // ==========================================
  // RENDERIZZAZIONE CARDS (BOTTONI NATIVI)
  // ==========================================
  function createCardHTML(ev, index, isChannel) {
    const sources = getSources(ev);
    const sourcesCount = sources.length;
    const title = ev.title || "Evento";
    const leagueName = ev.league || "Sport";
    
    let btnText = "GUARDA ORA";
    let countText = sourcesCount > 1 ? `${sourcesCount} opzioni disponibili` : "";
    
    const timeText = ev.time || "LIVE";
    let badgeHtml = "";
    if (isChannel) {
      badgeHtml = '<span class="time-badge badge-247">24/7</span>';
    } else {
      const isLive = timeText.toLowerCase().includes("live") || timeText.toLowerCase().includes("diretta");
      badgeHtml = `<span class="time-badge ${isLive ? 'live-active' : ''}">${escapeHTML(timeText.toUpperCase())}</span>`;
    }

    let logosHtml = "";
    if (ev.home_logo || ev.away_logo) {
      logosHtml = `<div class="team-logos">`;
      if (ev.home_logo) logosHtml += `<img src="${escapeHTML(ev.home_logo)}" alt="Home" class="team-logo" loading="lazy" referrerpolicy="no-referrer">`;
      if (ev.away_logo) logosHtml += `<img src="${escapeHTML(ev.away_logo)}" alt="Away" class="team-logo" loading="lazy" referrerpolicy="no-referrer">`;
      logosHtml += `</div>`;
    }

    const cardInnerHTML = `
      <div class="card-header">
        <span class="league">${escapeHTML(leagueName)}</span>
        ${badgeHtml}
      </div>
      <div class="card-body">
        ${logosHtml}
        <div class="match-title">${escapeHTML(title)}</div>
      </div>
      <div class="card-footer">
        <span class="source-count">${countText}</span>
        <span class="play-btn">${btnText}</span>
      </div>`;

    if (sourcesCount === 1) {
        const safeUrl = sources[0].url.replace(/'/g, "\\'");
        return `<button class="card" onclick="launchSingleStream(event, '${safeUrl}')">${cardInnerHTML}</button>`;
    } else {
        return `<button class="card" onclick="openModalGlobal(event, ${index})">${cardInnerHTML}</button>`;
    }
  }

  function render() {
    const league = el.league.value;
    let eventsHtml = "";
    let channelsHtml = "";
    let eventsCount = 0;
    let channelsCount = 0;
    
    shownEvents = [];

    allEvents.forEach((ev) => {
      if (getSources(ev).length === 0) return;

      const isChannel = ev.league && ev.league.toLowerCase().includes("canali");
      
      if (isChannel) {
        if (league === "all") {
          shownEvents.push(ev);
          channelsHtml += createCardHTML(ev, shownEvents.length - 1, true);
          channelsCount++;
        }
      } else {
        if (league === "all" || ev.league === league) {
          shownEvents.push(ev);
          eventsHtml += createCardHTML(ev, shownEvents.length - 1, false);
          eventsCount++;
        }
      }
    });

    if (eventsCount === 0) {
      el.eventsGrid.innerHTML = '<div style="color:var(--text-secondary); font-size:18px; font-weight:700; text-align:center; grid-column: 1/-1; padding: 40px;">NESSUN EVENTO DISPONIBILE</div>';
    } else {
      el.eventsGrid.innerHTML = eventsHtml;
    }
    el.count.textContent = eventsCount; 

    if (channelsCount === 0) {
      el.channelsSection.style.display = 'none';
    } else {
      el.channelsSection.style.display = 'block';
      el.channelsGrid.innerHTML = channelsHtml;
    }
  }

  try {
    const raw = JSON.parse($("fallback-data").textContent);
    allEvents = Array.isArray(raw.data) ? raw.data : [];
  } catch (_) {
    allEvents = [];
  }

  const leagues = [...new Set(allEvents.map(e => e.league).filter(Boolean))].sort((a,b) => a.localeCompare(b, "it"));
  leagues.forEach(l => {
      if(!l.toLowerCase().includes("canali")) {
          el.league.add(new Option(l, l))
      }
  });
  
  el.league.addEventListener("change", render);

  render();
})();
</script>
</body>
</html>
'''

# ---------------------------------------------------------------------------
# FETCH & RISOLUZIONE VERO PLAYER (ANTI-MATRIOSKA)
# ---------------------------------------------------------------------------
def get_html_directly():
    print(f"Connessione a {BASE_SITE}...")
    try:
        response = requests.get(BASE_SITE, headers=HEADERS, timeout=(10, 25))
        response.raise_for_status()
        if not response.encoding or response.encoding.lower() in ("iso-8859-1", "latin-1"):
            response.encoding = "utf-8"
        return response.text
    except requests.RequestException as exc:
        print(f"Download fallito: {exc}")
        return None

def resolve_direct_player_url(session, page_url):
    try:
        res = session.get(page_url, headers=HEADERS, timeout=7)
        if res.status_code == 200:
            soup = BeautifulSoup(res.text, "html.parser")
            for iframe in soup.find_all("iframe"):
                src = iframe.get("src", "").strip()
                if not src:
                    continue
                if any(x in src for x in ["googletag", "doubleclick", "adnxs", "banner", "ads"]):
                    continue
                if src.startswith("//"):
                    return "https:" + src
                if src.startswith("http"):
                    return src
                return urllib.parse.urljoin(page_url, src)
    except Exception:
        pass
    return page_url

# ---------------------------------------------------------------------------
# PARSING
# ---------------------------------------------------------------------------
def clean_text(element):
    if not element:
        return ""
    text = " ".join(element.get_text(" ", strip=True).split())
    return re.sub(r'[\s\-–/]+$', '', text).strip()

_TEAM_SPLIT_RE = re.compile(r"\s+(?:vs\.?|v\.?|–|-)\s+", re.IGNORECASE)

def split_teams(title):
    parts = _TEAM_SPLIT_RE.split(title, maxsplit=1)
    if len(parts) == 2:
        t1 = re.sub(r'[\s\-–/]+$', '', parts[0]).strip()
        t2 = re.sub(r'^[\s\-–/]+', '', parts[1]).strip()
        if len(t1) >= 2 and len(t2) >= 2:
            return t1, t2
    return "", ""

def parse_events(html):
    soup = BeautifulSoup(html, "html.parser")
    raw_events = []
    seen_keys = set()
    timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
    current_category = "Generale"

    elements = soup.select("main.container h2, main.container .category-label, main.container .match-card")
    if not elements:
        elements = soup.select("h2, .category-label, .match-card")

    for node in elements:
        classes = node.get("class", [])

        if node.name == "h2" or "category-label" in classes:
            text = clean_text(node)
            if text:
                current_category = text
            continue

        if "match-card" not in classes:
            continue

        # Estrazione titolo ed eventuali loghi
        teams_box = node.find("div", class_="teams-box")
        home_logo = ""
        away_logo = ""
        
        if teams_box:
            # Estrazione loghi
            imgs = teams_box.find_all("img")
            if len(imgs) >= 1:
                home_logo = urllib.parse.urljoin(BASE_SITE, imgs[0].get("src", "").strip())
            if len(imgs) >= 2:
                away_logo = urllib.parse.urljoin(BASE_SITE, imgs[1].get("src", "").strip())
            
            teams_copy = BeautifulSoup(str(teams_box), "html.parser")
            for badge in teams_copy.find_all(class_=["score-badge", "live-badge", "vs-txt"]):
                badge.decompose()
            title = clean_text(teams_copy) or "Evento live"
        else:
            title = "Evento live"

        # Estrazione dell'orario
        time_box = node.find("div", class_="time-box")
        time_element = time_box.find(class_="ora-txt") if time_box else None
        event_time = clean_text(time_element or time_box)
        if not event_time:
            event_time = "LIVE"

        button_group = node.find("div", class_="btn-group")
        if not button_group:
            continue

        sources = []
        seen_urls = set()

        for anchor in button_group.find_all("a", href=True):
            raw_url = anchor.get("href", "").strip()
            if not raw_url or raw_url.startswith(("javascript:", "mailto:")):
                continue

            full_url = urllib.parse.urljoin(BASE_SITE, raw_url)
            parsed = urllib.parse.urlparse(full_url)
            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                continue

            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)

            sources.append({
                "name": clean_text(anchor) or f"Canale {len(sources) + 1}",
                "url": full_url,
            })

        if not sources:
            continue

        key = (current_category, title, event_time)
        if key in seen_keys:
            continue
        seen_keys.add(key)

        home, away = split_teams(title)
        raw_events.append({
            "id": len(raw_events) + 1,
            "title": title,
            "home_team": home,
            "away_team": away,
            "league": current_category,
            "time": event_time,
            "home_logo": home_logo,
            "away_logo": away_logo,
            "start_time": timestamp,
            "status": "live",
            "has_stream": True,
            "sources": sources,
        })

    print(f"Estrazione link player reali per {sum(len(e['sources']) for e in raw_events)} canali...")
    with requests.Session() as session:
        def process_source(source):
            source["url"] = resolve_direct_player_url(session, source["url"])
            return source

        with ThreadPoolExecutor(max_workers=8) as executor:
            for ev in raw_events:
                ev["sources"] = list(executor.map(process_source, ev["sources"]))

    return raw_events

# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    html = get_html_directly()

    if not html:
        fallback = os.path.join(script_dir, "htsport.org.html")
        try:
            with open(fallback, "r", encoding="utf-8") as file:
                html = file.read()
            print(f"Uso il file locale: {fallback}")
        except OSError as exc:
            print(f"Errore lettura file locale: {exc}")
            sys.exit(1)

    events = parse_events(html)
    if not events:
        print("Attenzione: nessun evento estratto.")

    data_json = json.dumps(
        {"data": events},
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("</", "<\\/")

    # Iniezione dei Dati e della Data Corrente
    current_date = datetime.datetime.now().strftime("%d/%m/%Y")
    final_html = HTML_TEMPLATE.replace("__DATA_PLACEHOLDER__", data_json)
    final_html = final_html.replace("__DATE_PLACEHOLDER__", current_date)
    
    output_path = os.path.join(script_dir, "index.html")

    with open(output_path, "w", encoding="utf-8") as file:
        file.write(final_html)

    print(f"File salvato con successo in {output_path} ({len(events)} eventi).")

if __name__ == "__main__":
    main()
