"""
generate_carousel.py — Vollständige Carousel-Generierung in einem Schritt.

Topic: 72-Stunden-Fasten
- 7 Slides geplant (hard-coded für ersten Test)
- Holt echte Bilder von Pexels
- Baut HTML im @genuinely.healthy / @explaining.medicals Style
- Exportiert 7 PNGs (1080×1350) via Playwright

Aufruf:
    python generate_carousel.py

Output:
    ./output/slide_1.png ... slide_7.png
    ./output/carousel.html (für Preview)
"""

import asyncio
import base64
import json
import os
import sys
import urllib.parse
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")

PEXELS_KEY = os.environ.get("PEXELS_API_KEY", "").strip()
if not PEXELS_KEY:
    print("FEHLER: PEXELS_API_KEY fehlt in .env"); sys.exit(1)

OUTPUT_DIR = ROOT / "output"
OUTPUT_DIR.mkdir(exist_ok=True)
IMG_CACHE = ROOT / "image_cache"
IMG_CACHE.mkdir(exist_ok=True)

# === BRAND-EINSTELLUNGEN ===
BRAND_DISPLAY = "HEALTH RECODE"          # auf Slides angezeigt
BRAND_WORD_LEFT = "HEALTH"               # links vom Center-Symbol
BRAND_WORD_RIGHT = "RECODE"              # rechts vom Center-Symbol
BRAND_CENTER_ICON = "healthrecodeicon.png"  # Datei im Projekt-Ordner
BRAND_HANDLE = "@healthrecode"           # IG-Handle
BRAND_PRIMARY = "#00CFE8"                # Cyan (genuinely.healthy Style)
BRAND_BG_DARK = "#0A0A0F"

# === SLIDE-PLAN (hard-coded für 72-Stunden-Fasten) ===
SLIDES = [
    {
        "type": "hero",
        "tag": "FASTING SCIENCE",
        "headline_parts": [
            ("FASTING ", "regular"),
            ("72 HOURS", "primary"),
        ],
        "subhead_parts": [
            ("ACTIVATES A ", "regular"),
            ("NOBEL-PRIZE", "primary"),
            (" PROCESS THAT MAKES YOUR ", "regular"),
            ("CELLS EAT THEMSELVES", "bold"),
        ],
        "subline": "",
        "pexels_query": "minimalist sunrise silhouette aesthetic golden hour person",
        "pexels_color": "teal",
        "show_logo_block": True,
        "show_swipe_cta": True,
    },
    {
        "type": "content",
        "tag": "HOUR 0–12",
        "headline_parts": [
            ("AFTER JUST ", "white"),
            ("12 HOURS", "primary"),
            (", YOUR BODY DESPERATELY BURNS THROUGH ITS ", "white"),
            ("LAST GLYCOGEN", "primary"),
            (" RESERVES", "white"),
        ],
        "subline": "",
        "pexels_query": "minimalist aesthetic water glass dark moody cinematic editorial",
        "pexels_color": "teal",
        "show_logo_block": True,
        "show_swipe_cta": True,
    },
    {
        "type": "content",
        "tag": "HOUR 12–24",
        "headline_parts": [
            ("AT HOUR 12, YOUR BODY ENTERS ", "white"),
            ("KETOSIS", "primary"),
            (" — AND STARTS ", "white"),
            ("EATING ITSELF", "primary"),
            (" FOR FUEL", "white"),
        ],
        "subline": "",
        "pexels_query": "athletic silhouette running golden hour cinematic dark moody",
        "pexels_color": "orange",
        "show_logo_block": True,
        "show_swipe_cta": True,
    },
    {
        "type": "engagement",
        "tag": "HOUR 24–48",
        "headline_parts": [
            ("AT HOUR 24, YOUR CELLS BEGIN A ", "white"),
            ("SELF-CLEANING", "primary"),
            (" PROCESS THAT WON THE ", "white"),
            ("NOBEL PRIZE", "primary"),
        ],
        "subline": "",
        "pexels_query": "abstract macro cell beautiful blue glow scientific moody",
        "pexels_color": "blue",
        "show_logo_block": True,
        "show_swipe_cta": True,
        "engagement_text": "💾 SAVE THIS POST — IT'S ABOUT TO GET INTERESTING",
    },
    {
        "type": "content",
        "tag": "HOUR 48–72",
        "headline_parts": [
            ("AT HOUR 48, YOUR ENTIRE ", "white"),
            ("IMMUNE SYSTEM", "primary"),
            (" STARTS REGENERATING FROM ", "white"),
            ("STEM CELLS", "primary"),
        ],
        "subline": "",
        "pexels_query": "modern laboratory science aesthetic minimalist editorial dark",
        "pexels_color": "blue",
        "show_logo_block": True,
        "show_swipe_cta": True,
    },
    {
        "type": "content",
        "tag": "BREAKING THE FAST",
        "headline_parts": [
            ("ONE WRONG MEAL CAN ", "white"),
            ("UNDO", "primary"),
            (" 72 HOURS OF FASTING IN ", "white"),
            ("MINUTES", "primary"),
        ],
        "subline": "",
        "pexels_query": "cinematic still life bowl broth minimalist dark moody",
        "pexels_color": "brown",
        "show_logo_block": True,
        "show_swipe_cta": True,
    },
    {
        "type": "cta",
        "tag": "FOLLOW FOR MORE",
        "headline_parts": [
            ("FOLLOW ", "white"),
            ("@HEALTHRECODE", "primary"),
            (" FOR MORE MEDICAL SCIENCE THAT SOUNDS ", "white"),
            ("UNBELIEVABLE", "primary"),
        ],
        "subline": "Save this post · Tag a friend · Comment your next topic 👇",
        "pexels_query": "minimalist abstract human body silhouette dark aesthetic editorial",
        "pexels_color": "black",
        "show_logo_block": True,
        "show_swipe_cta": True,
    },
]


# === FINAL OUTRO Slide (ein einziger Slide am Ende, kombiniert Engagement + Profile-Card) ===
OUTRO_FINAL = {
    "type": "outro_final",
    # H1 — nur "DROP A 🔥" auf einer Zeile, BIG
    "headline_parts": [
        ("DROP A ", "bold"),
        ("🔥", "primary"),
    ],
    # H2 — kleiner, 2 Zeilen mit explizitem Umbruch
    "subhead_parts": [
        ("IF YOU LEARNED<br>", "regular"),
        ("SOMETHING NEW!", "bold"),
    ],
    # Description — dritte Ebene, noch kleiner
    "description_parts": [
        ("WHICH FACT ", "regular"),
        ("SHOCKED", "primary"),
        (" YOU MOST?<br>TELL ME IN THE ", "regular"),
        ("COMMENTS", "bold"),
        (" 👇", "primary"),
    ],
    # BIG Follow CTA — normal (nicht bold), 2-zeilig
    "big_follow_cta_parts": [
        ("FOLLOW ", "normal"),
        ("@HEALTHRECODE", "primary"),
        ("<br>TO NOT MISS MORE!", "normal"),
    ],
    "subline": "",
    # Dunkler kosmischer Hintergrund via AI
    "ai_render": True,
    "ai_prompt": (
        "Minimalist dark cosmic background, deep black with subtle white dust particles "
        "and faint star specks, editorial moody atmosphere, cinematic lighting, "
        "ultra clean aesthetic, suitable as text overlay background, 8k"
    ),
    "pexels_query": "dark cosmic stars black aesthetic minimalist",
    "pexels_color": "black",
    "text_position": "top",
    "show_logo_block": False,
    "show_swipe_cta": False,
    # Spezial: Profile-Card unten als eingebettetes Bild rendern
    "embed_profile_card": "healthrecodefollow.jpg",
    "show_follow_cta_above_card": True,
    # Share-CTA ganz unten
    "share_cta_text": "Share this with your Friends →",
}

# Outro immer am Ende ankleben (jetzt nur noch 1 Slide statt 2)
SLIDES = SLIDES + [OUTRO_FINAL]
# Backward-compat exports für cloud_pipeline.py
OUTRO_FOLLOW = OUTRO_FINAL
OUTRO_COMMENT = None  # nicht mehr benutzt


# === PEXELS-FETCH ===
def fetch_unsplash_image(query: str, idx: int) -> Path:
    """Unsplash-Fallback. Free Tier: 50 Requests/h. High Quality."""
    import hashlib
    api_key = os.environ.get("UNSPLASH_ACCESS_KEY", "").strip()
    if not api_key:
        raise RuntimeError("UNSPLASH_ACCESS_KEY fehlt")
    key = hashlib.md5(query.encode()).hexdigest()[:10]
    cache = IMG_CACHE / f"slide_{idx}_unsplash_{key}.jpg"
    if cache.exists() and cache.stat().st_size > 5000:
        return cache
    print(f"  [{idx}] Unsplash search: '{query}'")
    r = requests.get(
        "https://api.unsplash.com/search/photos",
        headers={"Authorization": f"Client-ID {api_key}"},
        params={"query": query, "per_page": 5, "orientation": "portrait"},
        timeout=20,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Unsplash fail: {r.status_code} {r.text[:200]}")
    results = r.json().get("results", [])
    if not results:
        raise RuntimeError(f"Unsplash: 0 Treffer für '{query}'")
    url = results[0]["urls"].get("regular") or results[0]["urls"].get("full")
    img_r = requests.get(url, timeout=60)
    img_r.raise_for_status()
    cache.write_bytes(img_r.content)
    return cache


def fetch_pixabay_image(query: str, idx: int) -> Path:
    """Pixabay-Fallback wenn Pexels nichts hat. Free Tier: 100 Calls/Min."""
    import hashlib
    api_key = os.environ.get("PIXABAY_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("PIXABAY_API_KEY fehlt — als Fallback empfohlen")
    key = hashlib.md5(query.encode()).hexdigest()[:10]
    cache = IMG_CACHE / f"slide_{idx}_pixabay_{key}.jpg"
    if cache.exists() and cache.stat().st_size > 5000:
        return cache
    print(f"  [{idx}] Pixabay search: '{query}'")
    r = requests.get(
        "https://pixabay.com/api/",
        params={
            "key": api_key, "q": query, "image_type": "photo",
            "orientation": "vertical", "per_page": 5, "safesearch": "true",
        }, timeout=20,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Pixabay fail: {r.status_code}")
    hits = r.json().get("hits", [])
    if not hits:
        raise RuntimeError(f"Pixabay: 0 Treffer für '{query}'")
    url = hits[0].get("largeImageURL") or hits[0].get("webformatURL")
    img_r = requests.get(url, timeout=60)
    img_r.raise_for_status()
    cache.write_bytes(img_r.content)
    return cache


def fetch_pexels_image(query: str, idx: int, color: str = None) -> Path:
    """Sucht das beste Pexels-Foto für die Query und cached es lokal.
    Bei 0 Treffern → Fallback auf Pixabay → Fallback auf vereinfachte Query."""
    import hashlib
    key = hashlib.md5(f"{query}|{color or ''}".encode()).hexdigest()[:10]
    cache = IMG_CACHE / f"slide_{idx}_{key}.jpg"
    if cache.exists() and cache.stat().st_size > 5000:
        print(f"  [{idx}] Cache hit: {cache.name}")
        return cache

    print(f"  [{idx}] Pexels search: '{query}' (color={color or 'any'})")
    params = {"query": query, "per_page": 8, "orientation": "portrait"}
    if color:
        params["color"] = color
    r = requests.get(
        "https://api.pexels.com/v1/search",
        headers={"Authorization": PEXELS_KEY},
        params=params,
        timeout=20,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Pexels search fail: {r.status_code} {r.text[:200]}")
    photos = r.json().get("photos", [])
    if not photos:
        # Stufe 1: Fallback ohne color
        params.pop("color", None)
        r = requests.get(
            "https://api.pexels.com/v1/search",
            headers={"Authorization": PEXELS_KEY},
            params=params, timeout=20,
        )
        photos = r.json().get("photos", [])
    if not photos:
        # Stufe 2: Vereinfachte Query (erste 2 Wörter)
        simple = " ".join(query.split()[:2])
        if simple != query:
            print(f"  [{idx}] Pexels: 0 Treffer → vereinfachte Query '{simple}'")
            r = requests.get(
                "https://api.pexels.com/v1/search",
                headers={"Authorization": PEXELS_KEY},
                params={"query": simple, "per_page": 5}, timeout=20,
            )
            photos = r.json().get("photos", [])
    if not photos:
        # Stufe 3: Pixabay-Fallback
        if os.environ.get("PIXABAY_API_KEY"):
            print(f"  [{idx}] Pexels: 0 Treffer → Pixabay-Fallback")
            try:
                return fetch_pixabay_image(query, idx)
            except Exception as e:
                print(f"  Pixabay auch fehlgeschlagen: {e}")
    if not photos:
        raise RuntimeError(f"Keine Pexels-Treffer für '{query}'")

    photo = photos[0]
    img_url = photo["src"].get("portrait") or photo["src"]["large"]
    print(f"  [{idx}] Photographer: {photo.get('photographer')} → DL")
    img_r = requests.get(img_url, timeout=60)
    img_r.raise_for_status()
    cache.write_bytes(img_r.content)
    return cache


def img_to_base64(path: Path) -> str:
    data = path.read_bytes()
    mime = "jpeg" if path.suffix.lower() in (".jpg", ".jpeg") else "png"
    return f"data:image/{mime};base64,{base64.b64encode(data).decode()}"


def fetch_ai_image(prompt: str, idx: int) -> Path:
    """Generiert AI-Bild via Together AI FLUX 1.1 Pro (~$0,04/Bild). 4:5 Aspect."""
    import hashlib
    key = hashlib.md5(prompt.encode()).hexdigest()[:10]
    cache = IMG_CACHE / f"slide_{idx}_ai_{key}.png"
    if cache.exists() and cache.stat().st_size > 5000:
        print(f"  [{idx}] AI Cache hit: {cache.name}")
        return cache

    api_key = os.environ.get("TOGETHER_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("TOGETHER_API_KEY fehlt für AI-Rendering")

    print(f"  [{idx}] AI Render (FLUX 1.1 Pro): '{prompt[:80]}...'")
    r = requests.post(
        "https://api.together.xyz/v1/images/generations",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": "black-forest-labs/FLUX.1.1-pro",
            "prompt": prompt,
            "width": 1024,
            "height": 1280,
            "steps": 28,
            "n": 1,
            "response_format": "b64_json",
        },
        timeout=180,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Together AI fail: {r.status_code} {r.text[:300]}")
    b64 = r.json()["data"][0]["b64_json"]
    cache.write_bytes(base64.b64decode(b64))
    return cache


def fetch_google_image(query: str, idx: int) -> Path:
    """Google Custom Search für echte Personen / spezifische Themen.
    Erfordert: GEMINI_API_KEY (oder GOOGLE_API_KEY) + GOOGLE_CSE_ID in .env."""
    import hashlib
    key = hashlib.md5(query.encode()).hexdigest()[:10]
    cache = IMG_CACHE / f"slide_{idx}_google_{key}.jpg"
    if cache.exists() and cache.stat().st_size > 5000:
        print(f"  [{idx}] Google Cache hit: {cache.name}")
        return cache

    api_key = (os.environ.get("GOOGLE_API_KEY", "")
               or os.environ.get("GEMINI_API_KEY", "")).strip()
    cx = os.environ.get("GOOGLE_CSE_ID", "").strip()
    if not api_key or not cx:
        raise RuntimeError(
            "Google Images braucht GEMINI_API_KEY + GOOGLE_CSE_ID in .env. "
            "Erstelle CSE bei https://programmablesearchengine.google.com → "
            "Image Search aktivieren → CX-ID kopieren."
        )

    print(f"  [{idx}] Google Images: '{query}'")
    r = requests.get(
        "https://www.googleapis.com/customsearch/v1",
        params={
            "key": api_key,
            "cx": cx,
            "q": query,
            "searchType": "image",
            "imgSize": "xlarge",
            "imgType": "photo",
            "safe": "active",
            "num": 5,
        },
        timeout=20,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Google CSE fail: {r.status_code} {r.text[:300]}")
    items = r.json().get("items", [])
    if not items:
        raise RuntimeError(f"Keine Google-Treffer für '{query}'")

    # Erstes erreichbares Bild nehmen
    for item in items:
        url = item.get("link")
        try:
            img_r = requests.get(url, timeout=30,
                                 headers={"User-Agent": "Mozilla/5.0"})
            if img_r.status_code == 200 and img_r.content[:4] in (b'\xff\xd8\xff\xe0', b'\xff\xd8\xff\xe1', b'\x89PNG', b'GIF8'):
                cache.write_bytes(img_r.content)
                return cache
        except Exception:
            continue
    raise RuntimeError(f"Kein Google-Bild downloadbar für '{query}'")


def get_slide_image(slide: dict, idx: int) -> Path:
    """Wählt Bild-Quelle:
       - solid_color: rein einfarbiger Hintergrund (z.B. '#000000' für schwarz)
       - local_bg: Datei aus Projekt-Ordner (für Outro-Slides mit fixen Bildern)
       - google_query: Google Images (echte Personen, spezifische Themen)
       - ai_render / ai_prompt: Together AI FLUX
       - sonst: Pexels (Standard für Lifestyle)"""
    if slide.get("solid_color"):
        # Generiere Solid-Color-PNG zur Laufzeit
        from PIL import Image
        color_hex = slide["solid_color"].lstrip("#")
        rgb = tuple(int(color_hex[i:i+2], 16) for i in (0, 2, 4))
        cache = IMG_CACHE / f"solid_{color_hex}.png"
        if not cache.exists():
            Image.new("RGB", (1080, 1350), rgb).save(cache)
        return cache
    if slide.get("local_bg"):
        path = ROOT / slide["local_bg"]
        if not path.exists():
            raise RuntimeError(f"local_bg Datei fehlt: {path}")
        return path
    if slide.get("google_query"):
        return fetch_google_image(slide["google_query"], idx)
    if slide.get("ai_render") or slide.get("ai_prompt"):
        prompt = slide.get("ai_prompt") or slide.get("pexels_query")
        return fetch_ai_image(prompt, idx)
    return fetch_pexels_image(
        slide["pexels_query"], idx, slide.get("pexels_color")
    )


def load_brand_logo() -> str:
    """Lädt das Brand-Logo (top-left). Sucht erst healthrecordlogotrans.png, dann logo.png."""
    for name in ("healthrecordlogotrans.png", "logo.png"):
        p = ROOT / name
        if p.exists() and p.stat().st_size > 1000:
            return img_to_base64(p)
    return ""


def load_center_icon() -> str:
    """Lädt healthrecode.png (Logo-Center-Symbol zwischen 'HEALTH' und 'RECODE')."""
    icon_path = ROOT / BRAND_CENTER_ICON
    if icon_path.exists() and icon_path.stat().st_size > 200:
        return img_to_base64(icon_path)
    return ""


# === HEADLINE-RENDERN ===
def render_headline(parts):
    """Konvertiert Headline-Parts zu HTML.
    Unterstützte Stile pro Segment:
       'primary' → Brand-Farbe, fett
       'bold'    → weiß, fett (für Keywords)
       'regular' → weiß, dünn (für Verbindungswörter — mentality_facts Style)
       'white'   → weiß, fett (Standard)"""
    out = []
    for text, style in parts:
        if style == "primary":
            css = f"color:{BRAND_PRIMARY};font-weight:700"
        elif style == "bold":
            css = "color:white;font-weight:700"
        elif style == "regular":
            css = "color:rgba(255,255,255,0.92);font-weight:300"
        elif style == "normal":
            css = "color:white;font-weight:400"
        else:  # 'white' Default
            css = "color:white;font-weight:700"
        out.append(f'<span style="{css}">{text}</span>')
    return "".join(out)


def calc_headline_size(parts):
    """Auto-skalierte Schriftgröße je nach Textlänge.
    Wenige Wörter = groß. Viele Wörter = kleiner. (15% kleiner als vorher.)"""
    total = sum(len(t) for t, _ in parts)
    if total < 25:    return 39  # 1-3 Wörter
    elif total < 40:  return 34  # kurz
    elif total < 55:  return 30  # mittel-kurz
    elif total < 75:  return 26  # mittel
    elif total < 100: return 22  # lang
    elif total < 130: return 20  # sehr lang
    else:             return 17  # extra lang


def calc_subhead_size(parts):
    """Subhead ist immer ~60% der Hauptzeile."""
    return max(14, int(calc_headline_size(parts) * 0.55))


# === SLIDE-HTML ===
def slide_html(idx: int, slide: dict, total: int, image_b64: str, brand_logo_b64: str, center_icon_b64: str = "") -> str:
    headline = render_headline(slide["headline_parts"])
    subline = slide.get("subline", "")
    subhead_parts = slide.get("subhead_parts")
    show_swipe = slide.get("show_swipe_cta", True)
    engagement_text = slide.get("engagement_text", "")
    is_cta = slide["type"] == "cta"
    headline_size = calc_headline_size(slide["headline_parts"])
    subhead_html = ""
    if subhead_parts:
        subhead_size = calc_subhead_size(subhead_parts)
        subhead_html = (
            f'<h2 class="subhead" style="font-size:{subhead_size}px">'
            f'{render_headline(subhead_parts)}</h2>'
        )

    # Top-Left Logo entfernt — Brand erscheint nur im Bottom-Stack zwischen H1/Bild
    brand_logo_html = ""

    # Optional: eingebettete Profile-Card unten (für finale Outro-Slide)
    profile_card_html = ""
    pc_file = slide.get("embed_profile_card")
    if pc_file:
        pc_path = ROOT / pc_file
        if pc_path.exists():
            pc_b64 = img_to_base64(pc_path)
            profile_card_html = (
                f'<div class="profile-card-embed">'
                f'<img src="{pc_b64}" alt="profile"/></div>'
            )

    # Description (dritte Text-Ebene zwischen H2 und Follow-CTA)
    description_html = ""
    if slide.get("description_parts"):
        description_html = (
            f'<div class="description">{render_headline(slide["description_parts"])}</div>'
        )

    # Follow-CTA: entweder klein (Standard) oder BIG mit mixed colors (für Outro)
    follow_cta_html = ""
    if slide.get("big_follow_cta_parts"):
        follow_cta_html = (
            f'<div class="big-follow-cta">{render_headline(slide["big_follow_cta_parts"])}</div>'
        )
    elif not is_cta:
        follow_cta_html = (
            f'<div class="follow-cta">FOLLOW {BRAND_HANDLE.upper()} TO NOT MISS MORE</div>'
        )

    swipe_html = ""
    if show_swipe and not is_cta:
        swipe_html = """
        <div class="swipe-cta">
          <span>SWIPE FOR MORE</span>
          <svg class="swipe-arrow-mini" viewBox="0 0 24 24" fill="none">
            <path d="M9 6l6 6-6 6" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </div>
        """

    # Dots werden NICHT mehr gerendert — Instagram zeigt automatisch eigene Dots
    dots_html = ""

    engagement_html = ""
    if engagement_text:
        engagement_html = f"""
        <div class="engagement-banner">
          {engagement_text}
        </div>
        """

    swipe_arrow_html = ""
    if show_swipe and not is_cta:
        swipe_arrow_html = """
        <div class="swipe-arrow-right">
          <svg viewBox="0 0 24 24" fill="none">
            <path d="M9 6l6 6-6 6" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </div>
        """

    # Vital-Signs Strip (Signature-Element, oben rechts) — variiert pro Slide leicht
    vitals_values = [
        ("72", "98", "36.7"),
        ("68", "97", "36.6"),
        ("74", "98", "36.8"),
        ("70", "99", "36.7"),
        ("76", "98", "36.5"),
        ("69", "97", "36.6"),
        ("73", "98", "36.7"),
    ]
    hr, spo2, temp = vitals_values[(idx - 1) % len(vitals_values)]
    vitals_html = f"""
    <div class="vitals-strip">
      <span class="pulse-dot"></span>
      <span class="label">HR</span> <span class="value">{hr}</span>
      <span class="label">·</span>
      <span class="label">SpO₂</span> <span class="value">{spo2}%</span>
      <span class="label">·</span>
      <span class="label">T</span> <span class="value">{temp}°C</span>
    </div>
    """

    return f"""
    <div class="slide" id="slide-{idx}">
      <img class="bg-photo" src="{image_b64}" />
      <div class="bg-gradient"></div>

      <!-- Logo top-left -->
      {brand_logo_html}

      <!-- Vital-Signs Monitor-Strip oben rechts (Signature) -->
      {vitals_html}

      <!-- Pfeil rechts -->
      {swipe_arrow_html}

      <!-- Bottom-Stack: Logo-Block + H1 + (H2) + Follow-CTA — alle gruppiert -->
      <div class="bottom-stack {('top-position' if slide.get('text_position') == 'top' else '')}">
        {('' if slide.get('show_logo_block') is False else f'''<div class="logo-block">
          <div class="logo-line left"></div>
          <span class="logo-text">{BRAND_WORD_LEFT}</span>
          {f'<img class="logo-center-icon" src="{center_icon_b64}" alt="logo" />' if center_icon_b64 else ''}
          <span class="logo-text">{BRAND_WORD_RIGHT}</span>
          <div class="logo-line right"></div>
        </div>''')}
        <h1 class="headline" style="font-size:{headline_size}px">{headline}</h1>
        {subhead_html}
        {description_html}
        {follow_cta_html}
        {engagement_html}
      </div>

      {profile_card_html}
      {f'<div class="share-cta">{slide["share_cta_text"]}</div>' if slide.get("share_cta_text") else ""}
      {swipe_html}
      {dots_html}
    </div>
    """


def build_html(slides_with_images):
    total = len(slides_with_images)
    brand_logo = load_brand_logo()
    center_icon = load_center_icon()
    slide_blocks = "\n".join(
        slide_html(i + 1, s, total, img, brand_logo, center_icon)
        for i, (s, img) in enumerate(slides_with_images)
    )

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Carousel Preview</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Anton&family=Inter:wght@300;400;600;700;800&family=Oswald:wght@300;400;600;700&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: #1a1a1a;
    font-family: 'Inter', sans-serif;
    color: white;
    padding: 20px;
    display: flex;
    flex-wrap: wrap;
    gap: 20px;
    justify-content: center;
  }}
  .ig-frame {{
    width: 420px;
    overflow: hidden;
  }}
  .carousel-viewport {{
    width: 420px;
    height: 525px;
    position: relative;
  }}
  .carousel-track {{
    display: flex;
    transition: none;
    transform: translateX(0);
  }}
  .slide {{
    flex: 0 0 420px;
    width: 420px;
    height: 525px;
    position: relative;
    overflow: hidden;
    background: {BRAND_BG_DARK};
    color: white;
    font-family: 'Inter', sans-serif;
  }}
  .bg-photo {{
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
    filter: saturate(1.05) contrast(1.05);
  }}
  .bg-gradient {{
    position: absolute;
    inset: 0;
    background: linear-gradient(
      180deg,
      rgba(10,10,15,0.0) 0%,
      rgba(10,10,15,0.0) 25%,
      rgba(10,10,15,0.35) 40%,
      rgba(10,10,15,0.75) 55%,
      rgba(10,10,15,0.92) 70%,
      rgba(10,10,15,0.98) 85%,
      rgba(10,10,15,1.0) 100%
    );
  }}
  .brand-corner {{ display: none; }}
  .brand-mark {{ display: none; }}

  .bottom-stack {{
    position: absolute;
    bottom: 70px;
    top: 55%;            /* erzwingt: Text-Stack maximal in unteren 45% des Slides */
    left: 0;
    right: 0;
    padding: 0 24px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: flex-end;
    gap: 6px;
    z-index: 5;
    text-align: center;
    overflow: visible;
  }}
  .bottom-stack.top-position {{
    top: 40px;
    bottom: auto;
    gap: 10px;
  }}

  /* Eingebettete Profile-Card unten auf finaler Outro-Slide */
  .profile-card-embed {{
    position: absolute;
    bottom: 50px;
    left: 24px;
    right: 24px;
    z-index: 4;
    border-radius: 8px;
    overflow: hidden;
    border: 1.5px solid rgba(0,207,232,0.55);
    box-shadow: 0 4px 16px rgba(0,0,0,0.5);
  }}
  .profile-card-embed img {{
    width: 100%;
    display: block;
    object-fit: cover;
  }}
  /* Share-CTA ganz unten — "Share this with your Friends →" */
  .share-cta {{
    position: absolute;
    bottom: 18px;
    left: 0;
    right: 0;
    z-index: 5;
    text-align: center;
    font-family: 'Oswald', sans-serif;
    font-weight: 500;
    font-size: 13px;
    color: rgba(255,255,255,0.95);
    letter-spacing: 0.6px;
    text-shadow: 0 2px 6px rgba(0,0,0,0.30);
  }}
  .logo-block {{
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 5px;
  }}
  .logo-line {{
    flex: 0 0 70px;
    height: 1px;
    background: linear-gradient(to right, transparent, {BRAND_PRIMARY}, {BRAND_PRIMARY});
  }}
  .logo-line.right {{
    background: linear-gradient(to left, transparent, {BRAND_PRIMARY}, {BRAND_PRIMARY});
  }}
  .logo-text {{
    font-family: 'Inter', sans-serif;
    font-weight: 600;
    font-size: 11px;
    letter-spacing: 2.5px;
    color: white;
  }}
  .logo-center-icon {{
    width: 16px;
    height: 16px;
    object-fit: contain;
    margin: 0 0;
    filter: drop-shadow(0 1px 2px rgba(0,0,0,0.3));
  }}

  .headline-block {{
    position: absolute;
    bottom: 70px;
    left: 0;
    right: 0;
    padding: 0 24px;
    z-index: 5;
    text-align: center;
  }}
  .tag {{
    display: none;  /* nicht in Referenz-Style */
  }}
  .headline {{
    font-family: 'Oswald', 'Anton', sans-serif;
    font-weight: 700;
    text-transform: uppercase;
    line-height: 1.0;
    letter-spacing: 0.3px;
    color: white;
    margin-bottom: 2px;
    text-shadow: 0 3px 12px rgba(0,0,0,0.55), 0 1px 3px rgba(0,0,0,0.40);
    /* font-size wird per inline style gesetzt (auto-scaled) */
  }}
  .subhead {{
    font-family: 'Oswald', 'Anton', sans-serif;
    font-weight: 600;
    text-transform: uppercase;
    line-height: 1.05;
    letter-spacing: 0.3px;
    color: rgba(255,255,255,0.92);
    margin-bottom: 0;
    margin-top: 2px;
    text-shadow: 0 2px 10px rgba(0,0,0,0.50), 0 1px 3px rgba(0,0,0,0.35);
    /* font-size wird per inline style gesetzt */
  }}

  /* Vital-Signs Monitor-Strip ganz rechts oben — Signature, transparent */
  .vitals-strip {{
    position: absolute;
    top: 14px;
    right: 14px;
    z-index: 6;
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 3px 8px;
    background: rgba(0,0,0,0.18);
    backdrop-filter: blur(4px);
    -webkit-backdrop-filter: blur(4px);
    border-radius: 3px;
    border: 1px solid rgba(255,255,255,0.05);
    font-family: 'JetBrains Mono', 'Courier New', monospace;
    font-size: 7.5px;
    color: rgba(255,255,255,0.55);
    letter-spacing: 0.3px;
  }}
  .vitals-strip .label {{
    color: rgba(255,255,255,0.35);
  }}
  .vitals-strip .value {{
    color: rgba(0,207,232,0.75);
    font-weight: 700;
  }}
  .vitals-strip .pulse-dot {{
    width: 4px;
    height: 4px;
    border-radius: 50%;
    background: rgba(0,207,232,0.75);
    margin-right: 1px;
    box-shadow: 0 0 4px rgba(0,207,232,0.5);
  }}
  .subline {{
    font-family: 'Inter', sans-serif;
    font-size: 11.5px;
    font-weight: 400;
    line-height: 1.4;
    color: rgba(255,255,255,0.85);
    max-width: 95%;
  }}

  .engagement-banner {{
    margin-top: 14px;
    padding: 10px 14px;
    background: {BRAND_PRIMARY};
    color: black;
    font-family: 'Inter', sans-serif;
    font-size: 10.5px;
    font-weight: 700;
    letter-spacing: 0.5px;
    border-radius: 4px;
    text-align: center;
    text-transform: uppercase;
  }}

  .swipe-cta {{
    position: absolute;
    bottom: 30px;
    left: 0;
    right: 0;
    z-index: 6;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
  }}
  .swipe-cta span {{
    font-family: 'Inter', sans-serif;
    font-size: 10px;
    letter-spacing: 3px;
    color: rgba(255,255,255,0.85);
    font-weight: 600;
  }}
  .swipe-arrow-mini {{
    width: 11px;
    height: 11px;
    stroke: rgba(255,255,255,0.85);
  }}

  /* Rechter Pfeil "Weiter swipen" wie bei Jackie-Chan-Beispiel */
  .swipe-arrow-right {{
    position: absolute;
    right: 12px;
    top: 50%;
    transform: translateY(-50%);
    width: 28px;
    height: 28px;
    border-radius: 50%;
    background: rgba(255,255,255,0.18);
    backdrop-filter: blur(4px);
    -webkit-backdrop-filter: blur(4px);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 7;
  }}
  .swipe-arrow-right svg {{
    width: 14px;
    height: 14px;
    stroke: white;
  }}

  /* Follow-CTA unter H1/H2 */
  .follow-cta {{
    font-family: 'Inter', sans-serif;
    font-size: 8px;
    font-weight: 600;
    letter-spacing: 1px;
    color: {BRAND_PRIMARY};
    text-transform: uppercase;
    margin-top: 2px;
  }}
  /* BIG Follow-CTA für Outro-Slide — nicht bold, mehrzeilig */
  .big-follow-cta {{
    font-family: 'Oswald', sans-serif;
    font-weight: 400;
    font-size: 22px;
    line-height: 1.2;
    letter-spacing: 0.4px;
    text-transform: uppercase;
    margin-top: 18px;
    text-shadow: 0 3px 12px rgba(0,0,0,0.55), 0 1px 3px rgba(0,0,0,0.40);
  }}
  /* Beschreibung — dritte Text-Ebene unter H2 */
  .description {{
    font-family: 'Oswald', sans-serif;
    font-weight: 600;
    font-size: 15px;
    line-height: 1.25;
    letter-spacing: 0.2px;
    text-transform: uppercase;
    margin-top: 14px;
    text-shadow: 0 2px 8px rgba(0,0,0,0.45), 0 1px 2px rgba(0,0,0,0.30);
  }}

  /* Logo top-left — transparent (das neue Logo hat eigenen Hintergrund) */
  .brand-logo-corner {{
    position: absolute;
    top: 12px;
    left: 12px;
    width: 55px;
    height: 55px;
    z-index: 7;
    overflow: visible;
    filter: drop-shadow(0 2px 6px rgba(0,0,0,0.35));
  }}
  .brand-logo-corner img {{
    width: 100%;
    height: 100%;
    object-fit: contain;
  }}
  .brand-logo-corner.fallback {{
    display: flex;
    align-items: center;
    justify-content: center;
    color: {BRAND_PRIMARY};
    font-family: 'Anton', sans-serif;
    font-size: 18px;
    font-weight: 800;
    background: linear-gradient(135deg, rgba(0,0,0,0.6), rgba(0,0,0,0.3));
  }}

  .dots {{
    position: absolute;
    bottom: 14px;
    left: 0;
    right: 0;
    display: flex;
    justify-content: center;
    gap: 5px;
    z-index: 6;
  }}
  .dots .dot {{
    width: 4px;
    height: 4px;
    border-radius: 50%;
    background: rgba(255,255,255,0.35);
  }}
  .dots .dot.active {{
    background: rgba(255,255,255,0.85);
  }}

  .slide-counter {{ display: none; }}
</style>
</head>
<body>
  <div class="ig-frame">
    <div class="carousel-viewport">
      <div class="carousel-track" id="track">
        {slide_blocks}
      </div>
    </div>
  </div>
</body>
</html>
"""


# === EXPORT MIT PLAYWRIGHT ===
async def export_slides(html_path: Path, total_slides: int, only: int = None):
    from playwright.async_api import async_playwright

    print("\n=== Export mit Playwright (HTML → 1080×1350 PNG) ===")

    VIEW_W, VIEW_H = 420, 525
    SCALE = 1080 / 420  # 2.5714

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(
            viewport={"width": VIEW_W, "height": VIEW_H},
            device_scale_factor=SCALE,
        )

        html = html_path.read_text(encoding="utf-8")
        await page.set_content(html, wait_until="networkidle")
        await page.wait_for_timeout(3500)  # Fonts laden

        # Body-Style anpassen damit nur ein Slide auf einmal sichtbar ist
        await page.evaluate("""() => {
          document.body.style.cssText = 'padding:0;margin:0;display:block;overflow:hidden;background:#0A0A0F;';
          const frame = document.querySelector('.ig-frame');
          frame.style.cssText = 'width:420px;height:525px;overflow:hidden;margin:0;';
          const vp = document.querySelector('.carousel-viewport');
          vp.style.cssText = 'width:420px;height:525px;overflow:hidden;position:relative;';
        }""")
        await page.wait_for_timeout(500)

        for i in range(total_slides):
            await page.evaluate("""(idx) => {
              const t = document.getElementById('track');
              t.style.transition = 'none';
              t.style.transform = 'translateX(' + (-idx * 420) + 'px)';
            }""", i)
            await page.wait_for_timeout(400)
            slide_num = only if only else (i + 1)
            out = OUTPUT_DIR / f"slide_{slide_num}.png"
            await page.screenshot(
                path=str(out),
                clip={"x": 0, "y": 0, "width": VIEW_W, "height": VIEW_H},
            )
            print(f"  Exported {out.name}")

        await browser.close()


# === HAUPT-PIPELINE ===
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Carousel-Generator")
    parser.add_argument("--only", type=int, default=None,
                        help="Nur Slide N generieren (1-7). Schneller Test.")
    args = parser.parse_args()

    if args.only:
        if args.only < 1 or args.only > len(SLIDES):
            print(f"FEHLER: --only muss 1-{len(SLIDES)} sein.")
            sys.exit(1)
        active_slides = [SLIDES[args.only - 1]]
        print(f"=== Test-Modus: nur Slide {args.only} ===\n")
    else:
        active_slides = SLIDES
        print("=== Carousel-Generator: 72-Stunden-Fasten ===\n")

    # 1. Bilder von Pexels holen
    print("Schritt 1: Bilder von Pexels holen")
    slides_with_imgs = []
    for i, slide in enumerate(active_slides):
        idx = (args.only if args.only else i + 1)
        path = get_slide_image(slide, idx)
        b64 = img_to_base64(path)
        slides_with_imgs.append((slide, b64))
    print(f"  → {len(slides_with_imgs)} Bilder bereit\n")

    # 2. HTML bauen
    print("Schritt 2: HTML-Carousel bauen")
    html = build_html(slides_with_imgs)
    html_path = OUTPUT_DIR / ("test_slide.html" if args.only else "carousel.html")
    html_path.write_text(html, encoding="utf-8")
    print(f"  → {html_path}\n")

    # 3. Export via Playwright
    print("Schritt 3: PNG-Export starten")
    asyncio.run(export_slides(html_path, len(slides_with_imgs), args.only))

    print(f"\n=== FERTIG ===")
    if args.only:
        print(f"Test-Slide: {OUTPUT_DIR}/slide_{args.only}.png")
    else:
        print(f"Slides: {OUTPUT_DIR}/slide_1.png ... slide_{len(SLIDES)}.png")
    print(f"HTML-Preview: {html_path}")


if __name__ == "__main__":
    main()
