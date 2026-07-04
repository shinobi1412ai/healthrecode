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

---

## ✅ Was in dieser Session gebaut/gefixt wurde

### 1. Groq als primäres LLM (Gemini war kaputt)
**Problem:** Gemini 2.5-flash gab seit 17. Mai 403-Fehler → Carousel-Generation komplett tot.

**Fix:** Groq API (llama-3.3-70b-versatile) als primäres LLM eingebaut.
- Kostenlos, 14.400 req/day, OpenAI-kompatibel
- Fallback-Kette: Groq → Gemini → Anthropic
- GROQ_API_KEY: `[GROQ_KEY — siehe CLAUDE.md]`
- Als GitHub Secret hinterlegt: ✅

**Datei:** `slide_planner.py` → `call_groq()` Funktion + `plan_slides()` Auto-Fallback

---

### 2. "Posts OHNE Bilder" Fix (PNG vs. JPEG)
**Problem:** Instagram Carousel API akzeptiert **nur JPEG** — PNG wird still ignoriert → leere Slides.

**Fix 1:** Cloudinary Upload mit `format="jpg"` → alle Slides werden als JPEG hochgeladen.

**Fix 2:** `_ensure_jpeg()` in `post_from_queue.py` → alte PNG-URLs werden on-the-fly zu JPEG konvertiert:
```
/upload/ → /upload/f_jpg,q_auto:good/
```

**Datei:** `cloud_pipeline.py` (Cloudinary upload) + `post_from_queue.py` (URL-Fix)

---

### 3. Dunkle/falsche/wiederholte Bilder Fix (Pollinations → Pexels)
**Problem:** System-Prompt hatte Widerspruch:
- Text sagte: `ai_render: true on EVERY slide` → Pollinations.ai generierte dunkle, falsche KI-Bilder (Gardinenstangen, Pflanzenstiele, Schwarz-Weiß)
- JSON-Template sagte: `ai_render: false`

Zusätzlich: Groq folgte manchmal dem Text → gleiche Pollinations-Query → gleiches Foto für alle Slides.

**Fix:** VISUAL MATCHING Section im SYSTEM_PROMPT komplett neu geschrieben:
```
GOLDEN RULE: ai_render is ALWAYS false. NEVER use ai_prompt.
ALWAYS use pexels_query for every slide.
NEVER repeat same pexels_query in one carousel.
```

Mit konkreten Query-Beispielen:
- Gut health → "woman eating healthy bowl"
- Brain anxiety → "woman meditating peaceful nature"
- etc.

**Datei:** `slide_planner.py` → SYSTEM_PROMPT `## VISUAL MATCHING` Section

---

### 4. `_fix_parts()` Defensive Helper
**Problem:** Groq gibt manchmal 1-Element-Tupel `("text",)` statt `("text", "modifier")` → `ValueError: not enough values to unpack`

**Fix:** `_fix_parts()` normalisiert alle headline_parts/subhead_parts defensiv.

**Datei:** `cloud_pipeline.py` → `_fix_parts()` + `_normalize_slide()`

---

### 5. Reel-Pipeline (NEU — komplett gebaut)
**Was:** Automatische Erstellung von Instagram Reels aus denselben Carousel-Assets.

**Ablauf:**
```
Pexels Video Intro (10s, thematisch) 
+ Slide 1 JPEG → Ken Burns Zoom + TTS Voice (7-8s)
+ Slide 2 JPEG → Ken Burns Zoom + TTS Voice (7-8s)
+ ... (alle 7 Content-Slides)
= reel_TIMESTAMP.mp4 (~11-15 MB)
→ Cloudinary Upload (video)
→ REEL_TIMESTAMP.json in queue/
```

**TTS Stimme:** `en-US-AriaNeural` (Microsoft edge-tts, kostenlos, kein API-Key)

**Ken Burns:** Langsamer Zoom von 1.0 auf 1.08, zentriert, 25fps

**Test:** Erfolgreich getestet mit "Why women gain weight after 40"
- Video: `https://res.cloudinary.com/dzpo48ngf/video/upload/v1781389830/medical-reels/medical_reel_20260613_2229.mp4`
- 11.6 MB, 7 Slides + Intro = ~60 Sekunden

**Neue Dateien:**
- `reel_pipeline.py` — komplette Reel-Pipeline
- `requirements.txt` — `edge-tts>=7.0.0` hinzugefügt

---

### 6. post_from_queue.py — Reel-Support
**Was:** `post_from_queue.py` erkennt jetzt automatisch Dateityp:
- `POST_*.json` → Instagram **Carousel** (8 Bilder)
- `REEL_*.json` → Instagram **Reel** (Video, media_type: REELS)

Wartet bis zu 5 Minuten auf Video-Processing bei Instagram.

**Neue Funktionen:**
- `post_reel_to_instagram()` — Reel-Container → FINISHED warten → Publish
- `post_reel_to_facebook()` — Cross-Post als FB Video
- `find_oldest_queue_file()` — sucht jetzt beide Typen (POST_ + REEL_)

---

### 7. Workflow-Updates (generate_carousels.yml)
- Timeout: 25min → **45min** (Reels brauchen mehr Zeit)
- Neuer Step: `sudo apt-get install -y ffmpeg` (war nicht vorinstalliert → Reel-Crash)
- Neues Input: `skip_reel: true/false` (Manual Override)
- Reel-Generation nach jedem Carousel automatisch
- Artifacts: jetzt auch `output/reel_*.mp4`

---

## 📅 Tagesablauf (vollautomatisch)

| Zeit | Was | Workflow |
|---|---|---|
| **02:00 UTC** | 2x Carousel + 2x Reel generieren | `generate_carousels.yml` |
| **08:00 UTC** | Ältestes POST_*.json posten (Carousel) | `post_from_queue.yml` |
| **16:00 UTC** | Ältestes REEL_*.json posten (Reel) | `post_from_queue.yml` |

---

## 🗂️ Dateistruktur (GitHub Repo)

```
healthrecode/
├── slide_planner.py        ← Groq/Gemini/Anthropic LLM → Slide-Plan JSON
├── cloud_pipeline.py       ← Haupt-Orchestrator: Plan → Slides → Cloudinary → Queue
├── reel_pipeline.py        ← NEU: Slides → TTS → Video → Cloudinary → Queue
├── post_from_queue.py      ← Postet POST_*.json (Carousel) oder REEL_*.json (Reel)
├── generate_carousel.py    ← Pexels Bilder + HTML + Playwright → slide_N.png
├── refill_topics.py        ← Auto-Refill topics.txt wenn < 50 Topics
├── topics.txt              ← Queue der nächsten Topics (100 Buffer)
├── queue/                  ← Wartende Posts: POST_*.json + REEL_*.json
├── posted/                 ← Bereits gepostete Posts (Archiv)
├── output/                 ← Temporär: PNGs, HTML, Plan-JSON, Reel-MP4
└── .github/workflows/
    ├── generate_carousels.yml   ← Täglich 02:00 UTC
    └── post_from_queue.yml      ← Täglich 08:00 + 16:00 UTC
```

---

## 🔑 GitHub Secrets (alle gesetzt)

| Secret | Was |
|---|---|
| `GROQ_API_KEY` | llama-3.3-70b-versatile (primäres LLM) |
| `PEXELS_API_KEY` | Bilder + Intro-Videos |
| `CLOUDINARY_CLOUD_NAME/API_KEY/API_SECRET` | Image + Video Upload |
| `IG_USER_ID` | Instagram User ID |
| `IG_USER_ACCESS_TOKEN` | Instagram Login API Token |
| `FB_PAGE_ID` | Facebook Page ID |
| `FB_PAGE_ACCESS_TOKEN` | Facebook Page Token (läuft nie ab) |
| `GEMINI_API_KEY` | Fallback LLM |
| `ANTHROPIC_API_KEY` | Last-Resort LLM |
| `SMTP_USER/SMTP_PASS` | Failure-Email |

---

## ❌ Was NICHT fertig / noch offen ist

### 1. Hintergrundmusik im Reel
User fragte nach "welche .wav Datei" — meinte vermutlich Hintergrundmusik.
Aktuell: NUR TTS-Voice, kein Musik-Background.

**Plan:** Eine leise Ambient/Chill-Musik-Datei (`.mp3`) ins Repo, ffmpeg mischt TTS + Musik:
```bash
ffmpeg -i slide_video.mp4 -i music.mp3 -filter_complex \
"[1:a]volume=0.15[bg];[0:a][bg]amix=inputs=2:duration=first" output.mp4
```
Musik bei ~15% Volume unter TTS. Health-Content-Stil: ruhig, motivierend.

**Status: Nicht implementiert — TODO**

### 2. Reel noch nicht live auf Instagram gepostet (nur generiert)
Das Reel vom Test (14.06.) liegt in `queue/REEL_20260613_2229.json` — wurde automatisch gepostet durch den 16:00 Cron. Ob es auf IG sichtbar ist → nicht verifiziert.

### 3. Lokale Windows-Kopie nicht synchron
`cloud_pipeline.py` und `post_from_queue.py` wurden direkt via VPS SSH gepusht. Die lokale Windows-Kopie in `C:\Users\myshi\Documents\Claude\Projects\Medical-Stuff\` ist veraltet.

**Fix:**
```powershell
cd "C:\Users\myshi\Documents\Claude\Projects\Medical-Stuff"
git pull
```

### 4. IG Access Token Ablauf
Instagram User Access Tokens laufen nach 60 Tagen ab. Wenn Posting plötzlich stoppt → Token erneuern.

Workflow erkennt das automatisch (Exit Code 78 → Cron deaktiviert sich selbst), aber Token muss manuell erneuert und als GitHub Secret neu gesetzt werden.

### 5. Cloudinary Free Tier
- 25 GB Bandwidth/Monat
- 25 GB Storage
- Videos brauchen mehr als Bilder — bei 2 Reels/Tag à ~15 MB = ~900 MB/Monat → im Rahmen

---

## 🔧 Schnellbefehle

```powershell
# Manuell einen Carousel + Reel für spezifisches Topic generieren:
# → GitHub Actions → generate_carousels.yml → "Run workflow" → topic eingeben

# Queue ansehen:
ssh -o StrictHostKeyChecking=no root@100.108.25.54 'ls /root/projects/healthrecode/queue/ 2>/dev/null || echo "Queue via GitHub"'

# Workflow-Status:
# → https://github.com/shinobi1412ai/healthrecode/actions

# Test-Reel Video ansehen:
# https://res.cloudinary.com/dzpo48ngf/video/upload/v1781389830/medical-reels/medical_reel_20260613_2229.mp4
```

---

## 📊 Technischer Stack

| Layer | Tool | Kosten |
|---|---|---|
| **LLM** | Groq llama-3.3-70b | Kostenlos (14.400 req/day) |
| **Bilder** | Pexels API | Kostenlos |
| **Intro-Video** | Pexels Videos API | Kostenlos |
| **TTS** | edge-tts (Microsoft Azure) | Kostenlos |
| **Video** | ffmpeg | Kostenlos |
| **Image Upload** | Cloudinary | Kostenlos (25GB) |
| **Video Upload** | Cloudinary | Kostenlos (25GB) |
| **CI/CD** | GitHub Actions | Kostenlos (2000 min/Monat) |
| **Posting** | Instagram Login API | Kostenlos |

**Gesamtkosten: 0 €/Monat**

---

## 🚀 Nächste Session — Wo weitermachen

1. **Hintergrundmusik** ins Reel einbauen (`.mp3` im Repo, ffmpeg amix)
2. **Reel auf IG verifizieren** — war das generierte Reel sichtbar und gut?
3. **Stimme testen** — `en-US-AriaNeural` passt? Oder andere edge-tts Stimme?
4. **Lokale Windows-Dateien** mit `git pull` synchronisieren

---

*Erstellt: 04.07.2026 — HealthRecode Auto-Pipeline Handoff*
