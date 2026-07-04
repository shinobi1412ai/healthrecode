# HANDOFF — HealthRecode Instagram Pipeline
**Stand: 04.07.2026 | Repo: github.com/shinobi1412ai/healthrecode**

---

## 🎯 Das Ziel

HealthRecode ist eine **vollautomatische Instagram + Facebook Content-Pipeline** für Health-Content (Frauen, 30-50, Hormone, Gewicht, Schlaf, Darm, Gehirn).

**Vision:** Kein manueller Aufwand. Täglich erscheint automatisch:
- **08:00 UTC** → Instagram Carousel (8 Slides, Pexels-Fotos, Groq-AI-Text)
- **16:00 UTC** → Instagram Reel (dasselbe Topic als Video mit TTS-Voiceover)
- **Parallel** → Facebook Cross-Post beider Formate

Die Pipeline läuft auf GitHub Actions — kein Server, keine Kosten, 24/7.

**Langfristiges Ziel:** Die Pipeline soll nicht nur HealthRecode-Carousels posten,
sondern als allgemeine Upload-Infrastruktur für alle Content-Typen dienen —
UGC-Videos, einzelne Fotos, Stories, alles automatisch.

---

## 📡 Wie der Instagram Upload funktioniert (API)

Das ist das Fundament — wenn man das versteht, kann man alles bauen.

### Grundprinzip
Instagram lädt Dateien **nie direkt** — du schickst nur eine öffentliche URL.
Instagram holt sich das Bild/Video selbst davon.
Deshalb brauchen wir Cloudinary als Zwischenspeicher.

```
Datei (lokal) → Cloudinary (öffentliche URL) → Instagram API → Live auf IG
```

### Flow: Einzelnes Foto
```
1. POST https://graph.instagram.com/v22.0/{ig_user_id}/media
   Body: { image_url: "https://cloudinary.com/...", caption: "Text" }
   → Antwort: { id: "container_id" }

2. POST https://graph.instagram.com/v22.0/{ig_user_id}/media_publish
   Body: { creation_id: "container_id" }
   → Post ist live
```

### Flow: Carousel (mehrere Bilder)
```
1. Für JEDES Bild einen Container erstellen:
   POST /media { image_url: "...", is_carousel_item: true }
   → container_id_1, container_id_2, ...

2. Carousel-Container:
   POST /media { media_type: "CAROUSEL", children: "id1,id2,...", caption: "..." }
   → carousel_container_id

3. Warten bis status_code == "FINISHED"

4. Publish:
   POST /media_publish { creation_id: carousel_container_id }
```

### Flow: Reel (Video)
```
1. POST /media { media_type: "REELS", video_url: "https://cloudinary.com/...mp4", caption: "..." }
   → container_id

2. Warten bis status_code == "FINISHED" (30s bis 5min)

3. POST /media_publish { creation_id: container_id }
   → Reel ist live
```

### Was du brauchst
| Credential | Läuft ab? |
|---|---|
| IG_USER_ID | Nie |
| IG_USER_ACCESS_TOKEN | Nach 60 Tagen! |
| Cloudinary Account | Nie (Free Tier reicht) |

### Was alles hochgeladen werden kann
| Content-Typ | API media_type |
|---|---|
| Einzelfoto | (default) |
| Carousel | CAROUSEL |
| Reel | REELS |
| Story Foto | STORIES |
| Story Video | STORIES |

---

## ✅ Was in dieser Session gebaut wurde

### 1. Groq als primäres LLM
Gemini war seit 17. Mai kaputt (403). Groq (llama-3.3-70b-versatile) eingebaut.
Fallback: Groq → Gemini → Anthropic. GitHub Secret gesetzt.
Datei: `slide_planner.py`

### 2. PNG→JPEG Fix (Posts OHNE Bilder)
Instagram akzeptiert nur JPEG. Cloudinary upload mit format="jpg".
_ensure_jpeg() konvertiert alte PNG-URLs on-the-fly.
Dateien: `cloud_pipeline.py`, `post_from_queue.py`

### 3. Dunkle/falsche Bilder Fix
Pollinations.ai generierte Müll (Gardinenstangen, Schwarz-Weiß).
SYSTEM_PROMPT neu: Pexels only, kein ai_render, unique query pro Slide.
Datei: `slide_planner.py`

### 4. _fix_parts() Crash-Fix
Groq gab manchmal kaputte Tupel → ValueError. Defensiver Fix.
Datei: `cloud_pipeline.py`

### 5. Reel-Pipeline (NEU)
Pexels Intro-Video (10s) + 7 Slides mit Ken Burns + TTS Voice → MP4 → Cloudinary → Queue.
TTS: en-US-AriaNeural (edge-tts, kostenlos).
Test: https://res.cloudinary.com/dzpo48ngf/video/upload/v1781389830/medical-reels/medical_reel_20260613_2229.mp4
Neue Datei: `reel_pipeline.py`

### 6. post_from_queue.py — Reel-Support
POST_*.json → Carousel-Flow
REEL_*.json → Reel-Flow
Datei: `post_from_queue.py`

### 7. Workflow-Updates
Timeout 25→45min, ffmpeg install, skip_reel Input.
Datei: `.github/workflows/generate_carousels.yml`

---

## 📅 Tagesablauf

| Zeit | Was |
|---|---|
| 02:00 UTC | 2x Carousel + 2x Reel generieren |
| 08:00 UTC | Ältestes POST_*.json → Carousel posten |
| 16:00 UTC | Ältestes REEL_*.json → Reel posten |

---

## 🗂️ Dateistruktur

```
healthrecode/
├── slide_planner.py        ← Groq LLM → Slide-Plan JSON
├── cloud_pipeline.py       ← Plan → Slides → Cloudinary → Queue
├── reel_pipeline.py        ← Slides → TTS → Video → Cloudinary → Queue
├── post_from_queue.py      ← Postet POST_*.json oder REEL_*.json
├── generate_carousel.py    ← Pexels + HTML + Playwright → slide_N.png
├── refill_topics.py        ← Auto-Refill topics.txt
├── topics.txt              ← Topic-Queue (100 Buffer)
├── queue/                  ← POST_*.json + REEL_*.json (wartend)
├── posted/                 ← Archiv geposteter Posts
└── .github/workflows/
    ├── generate_carousels.yml
    └── post_from_queue.yml
```

---

## 🔑 GitHub Secrets

| Secret | Was |
|---|---|
| GROQ_API_KEY | Primäres LLM |
| PEXELS_API_KEY | Bilder + Videos |
| CLOUDINARY_* (3x) | Upload |
| IG_USER_ID | Instagram ID |
| IG_USER_ACCESS_TOKEN | ⚠️ Läuft nach 60 Tagen ab! |
| FB_PAGE_ID + FB_PAGE_ACCESS_TOKEN | Facebook |
| GEMINI_API_KEY | Fallback LLM |
| ANTHROPIC_API_KEY | Last-Resort LLM |
| SMTP_USER + SMTP_PASS | Failure-Email |

---

## ❌ Offene TODOs

### 1. Hintergrundmusik im Reel (Prio 1)
Aktuell: nur TTS, keine Musik.
Plan: .mp3 ins Repo, ffmpeg amix bei 15% Volume.

### 2. Reel auf IG verifizieren
War das Test-Reel (13.06.) auf Instagram sichtbar und gut?

### 3. Lokale Windows-Dateien synchronisieren
C:\Users\myshi\Documents\Claude\Projects\Medical-Stuff\ ist veraltet.
Fix: git pull

### 4. IG Token Monitoring
Token läuft nach 60 Tagen ab. Bei Ausfall: Token erneuern → GitHub Secret neu setzen.

---

## 💰 Kosten

**Gesamt: 0 EUR/Monat** — Groq, Pexels, edge-tts, ffmpeg, Cloudinary Free, GitHub Actions Free, Instagram API alle kostenlos.

---

## 🚀 Nächste Session

1. Hintergrundmusik einbauen
2. Reel-Qualität auf IG prüfen
3. TTS-Stimme testen (Aria gut?)
4. git pull lokal
5. Optional: UGC-Videos, Einzelfotos für andere Accounts

---

*Stand: 04.07.2026*
