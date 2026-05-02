"""
test_list_slide.py — Lokaler Smoke-Test für KOMPLETTES Carousel inkl. neuer list-Slide.

Generiert 5 Slides:
  1. HERO (Bild via Pexels)
  2. CONTENT (Bild via Pexels)
  3. CONTENT (Bild via Pexels)
  4. LIST (kein Bild — dunkles Solid + nummerierte Tipps)
  5. OUTRO (Universum/Sterne via AI render — Fallback Pexels bei Fehler)

Aufruf (im Projekt-Ordner):
    python test_list_slide.py

Nutzt deine echten API-Keys aus .env (Pexels + Together AI für Outro).
"""

import asyncio
import importlib.util
from pathlib import Path

ROOT = Path(__file__).parent
spec = importlib.util.spec_from_file_location("gc", ROOT / "generate_carousel.py")
gc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gc)


# === Test-Carousel: Topic "Master Your First Hour" ===
TEST_SLIDES = [
    # Slide 1: HERO mit Bild + Hook
    {
        "type": "hero",
        "tag": "MORNING ROUTINE",
        "headline_parts": [
            ("THE FIRST 60 MINUTES ", "white"),
            ("CONTROL", "primary"),
            (" THE NEXT 23 HOURS", "white"),
        ],
        "subhead_parts": [
            ("YOUR CORTISOL ", "regular"),
            ("PEAKS 50%", "primary"),
            (" IN THE FIRST HOUR — HOW YOU SPEND IT REWIRES YOUR DAY", "regular"),
        ],
        "pexels_query": "man waking up sunrise window light bedroom",
        "pexels_color": "orange",
        "show_logo_block": True,
        "show_swipe_cta": True,
    },
    # Slide 2: Content — Mechanismus
    {
        "type": "content",
        "tag": "HOUR 0–15",
        "headline_parts": [
            ("YOUR BRAIN'S ", "white"),
            ("CORTISOL SPIKE", "primary"),
            (" SETS YOUR FOCUS WINDOW", "white"),
        ],
        "subhead_parts": [
            ("Cortisol peaks 30-45 min after waking — protect this window from screens and noise.", "regular"),
        ],
        "pexels_query": "person looking at sunrise mountain peaceful morning",
        "pexels_color": "orange",
        "show_logo_block": True,
        "show_swipe_cta": True,
    },
    # Slide 3: Content — Wissenschaft
    {
        "type": "content",
        "tag": "HYDRATION",
        "headline_parts": [
            ("YOU LOSE ", "white"),
            ("1L OF WATER", "primary"),
            (" OVERNIGHT — REPLACE IT FIRST", "white"),
        ],
        "subhead_parts": [
            ("Drinking 500ml within 10 min raises alertness by 14% in 30 min (study, 2018).", "regular"),
        ],
        "pexels_query": "glass of water morning sunlight kitchen",
        "pexels_color": "teal",
        "show_logo_block": True,
        "show_swipe_cta": True,
    },
    # Slide 4: NEUE LIST-SLIDE (Action Plan ohne Bild)
    {
        "type": "list",
        "tag": "ACTION PLAN",
        "headline_parts": [
            ("MASTER YOUR ", "white"),
            ("FIRST HOUR", "primary"),
        ],
        "list_items": [
            {
                "number": "01",
                "title": "THE SILENT AWAKENING",
                "description": "Resist screens for the first 30 minutes. Let your mind clear, not react.",
            },
            {
                "number": "02",
                "title": "HYDRATE & MOVE",
                "description": "Drink 500ml water immediately. Perform 10-15 minutes of light movement.",
            },
            {
                "number": "03",
                "title": "PLAN YOUR ATTACK",
                "description": "Review your top 3 priorities. Visualize their execution before starting.",
            },
            {
                "number": "04",
                "title": "IMMERSION ZONE",
                "description": "Tackle your most important task for 60-90 minutes, distraction-free.",
            },
        ],
        "show_logo_block": True,
        "show_swipe_cta": True,
    },
]


def main():
    print("=== Test: KOMPLETTES Carousel mit list-Slide ===\n")

    # Vorab aufräumen — alte slide_*.png + image_cache leeren
    # für Variety in jedem Test-Run (random Pexels-Pick)
    old_pngs = list(gc.OUTPUT_DIR.glob("slide_*.png"))
    for p in old_pngs:
        p.unlink()
    cache_files = list(gc.IMG_CACHE.glob("slide_*"))
    for p in cache_files:
        p.unlink()
    if old_pngs or cache_files:
        print(f"[0] {len(old_pngs)} alte PNGs + {len(cache_files)} Cache-Files gelöscht\n")

    # Outro automatisch anhängen (mit neuem Universum-Hintergrund)
    full_slides = TEST_SLIDES + [gc.OUTRO_FINAL]
    gc.SLIDES = full_slides

    # Bilder holen
    print(f"[1] Bilder für {len(full_slides)} Slides holen...")
    slides_with_imgs = []
    for i, slide in enumerate(full_slides):
        try:
            path = gc.get_slide_image(slide, i + 1)
            b64 = gc.img_to_base64(path)
            slides_with_imgs.append((slide, b64))
            print(f"    [{i+1}] {slide.get('type', 'content')} → {Path(path).name}")
        except Exception as e:
            print(f"    [{i+1}] FEHLER: {e}")
            return

    # HTML
    print("\n[2] HTML bauen...")
    html = gc.build_html(slides_with_imgs)
    html_path = gc.OUTPUT_DIR / "test_full_carousel.html"
    html_path.write_text(html, encoding="utf-8")
    print(f"    OK → {html_path}")

    # Render-Sanity
    print("\n[3] Sanity-Checks:")
    checks = [
        ("Hero-Slide gerendert", "id=\"slide-1\"" in html),
        ("List-Slide gerendert", "list-items" in html),
        ("List-Stack-Klasse", "list-stack" in html),
        ("Vital-Strip vorhanden", "vitals-strip" in html),
        ("Outro big-follow-cta", "big-follow-cta" in html),
    ]
    for name, ok in checks:
        print(f"    {'OK' if ok else 'FAIL'} — {name}")

    # PNG Export
    print("\n[4] Playwright Export → PNG (alle Slides)...")
    asyncio.run(gc.export_slides(html_path, len(slides_with_imgs)))

    pngs = sorted(gc.OUTPUT_DIR.glob("slide_*.png"))
    print(f"\n=== FERTIG: {len(pngs)} PNGs ===")
    for p in pngs:
        print(f"  {p}")

    # Stacked Preview HTML: alle Slides untereinander zum Scrollen im Browser
    preview = ['<!DOCTYPE html><html><head><meta charset="utf-8"><title>All Slides Preview</title>',
               '<style>body{margin:0;padding:30px;background:#1a1a1a;display:flex;flex-direction:column;align-items:center;gap:24px;}',
               'img{width:420px;height:525px;border-radius:12px;box-shadow:0 8px 24px rgba(0,0,0,0.6);display:block;}',
               '.label{color:#888;font-family:Inter,sans-serif;font-size:13px;margin-bottom:-12px;}</style></head><body>']
    for p in pngs:
        preview.append(f'<div class="label">{p.name}</div>')
        preview.append(f'<img src="{p.name}" />')
    preview.append("</body></html>")
    preview_path = gc.OUTPUT_DIR / "preview_all.html"
    preview_path.write_text("\n".join(preview), encoding="utf-8")

    print(f"\nIG-Preview (1 slide):    {html_path}")
    print(f"Alle Slides untereinander: {preview_path}")


if __name__ == "__main__":
    main()
