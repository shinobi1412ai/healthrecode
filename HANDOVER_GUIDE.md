# Health Recode — Master Handover Guide

> **Für eine neue Claude-Session (Cowork ODER Claude Code):** Lies diesen kompletten Guide bevor du Fragen beantwortest. Er enthält das gesamte System, alle Lessons Learned, und den exakten Setup-Pfad für eine neue Instagram-Seite.

---

## 1. Was dieses Projekt macht

Vollautomatischer **Instagram-Carousel-Generator** für medizinische/Health-Anatomie-Inhalte:

- **2× täglich** wird ein Post automatisch erstellt (09:00 + 17:00 UTC via GitHub Actions)
- Topic kommt aus `topics.txt` (FIFO-Queue, ~100 Topics vorgeladen, Auto-Refill via Gemini bei <10 übrig)
- Gemini Flash generiert Slide-Plan (3-15 Slides + 1 Outro)
- Bilder von Pexels (Lifestyle) + Together AI FLUX 1.1 Pro (Anatomie)
- Playwright rendert HTML → 1080×1350 PNGs
- Cloudinary hostet die Bilder
- Instagram Graph API postet als Carousel
- **Style-Inspiration**: @explaining.medicals, @genuinely.healthy, @mentality_facts

**Total Kosten**: ~$10/Monat (nur AI-Bilder via Together AI). Alles andere ist gratis.

---

## 2. Architektur

```
┌────────────────────────────────────────────────────────────┐
│  GitHub Actions Cron (täglich 09:00 + 17:00 UTC)           │
│  workflow: .github/workflows/daily_post.yml                │
└───────────────────────┬────────────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────────────┐
│  cloud_pipeline.py (Master-Orchestrator)                    │
│  1. Topic aus topics.txt lesen                              │
│  2. slide_planner.py → Gemini → 3-15 Slide-Plan (JSON)     │
│  3. Outro angehängt (OUTRO_FINAL)                           │
│  4. generate_carousel.py:                                   │
│     - get_slide_image: Pexels / AI / Google                 │
│     - HTML bauen mit Brand + Vital-Signs-Strip              │
│     - Playwright → 1080×1350 PNGs                           │
│  5. Cloudinary Upload → public URLs                         │
│  6. Instagram API (graph.instagram.com) → Carousel-Post     │
│  7. Topic aus Queue entfernen                               │
│  8. topic_refresher.py: bei <10 Topics, Gemini → 50 neue   │
└────────────────────────────────────────────────────────────┘
```

---

## 3. Code-Dateien

| Datei | Funktion |
|-------|----------|
| `generate_carousel.py` | Kern: Bilder holen (Pexels/AI/Google), HTML bauen, PNG-Export via Playwright. Brand-Konfig oben (BRAND_NAME, BRAND_PRIMARY, BRAND_HANDLE). Enthält `OUTRO_FINAL` (immer-letzte-Slide). |
| `slide_planner.py` | Gemini Flash API Caller. Topic in → 3-15-Slide-JSON-Plan out. **Strict System-Prompt** mit Visual-Matching-Rules. |
| `cloud_pipeline.py` | Orchestrator. Ruft slide_planner + generate_carousel + Cloudinary + Instagram-API auf. Defensiv (None-Filter, Try-Except für AI/Google-Fallbacks). |
| `topic_refresher.py` | Auto-Refill: bei <10 Topics generiert Gemini 50 neue, hängt an `topics.txt` an. |
| `setup_meta_credentials.py` | Einmal-Skript zum Long-Lived-Token-Holen + IG_USER_ID. (Wird mit der neuen Instagram Login API ggf. nicht gebraucht — Token wird direkt via Graph API Explorer geholt.) |
| `verify_*.py` | Smoke-Tests für jede API einzeln (Pexels, Pixabay, Cloudinary, Instagram, Replicate, Together, Gemini). |
| `.github/workflows/daily_post.yml` | Cron + manueller Trigger. Liest Secrets, schreibt `.env`, läuft `cloud_pipeline.py --upload --post`. |
| `topics.txt` | Topic-Queue. Eine Zeile = ein Topic. `#` = Kommentar. Auto-Refresh wenn fast leer. |
| `requirements.txt` | Python deps: requests, python-dotenv, playwright, cloudinary, Pillow. |

**Brand-Assets** (im Projekt-Root):
- `logo.png` — optional, oben-links Logo (aktuell ausgeblendet)
- `healthrecodeicon.png` — Mini-Icon zwischen "HEALTH" und "RECODE" im Logo-Block
- `healthrecodefollow.jpg` — Profile-Card-Screenshot, embedded auf Outro-Slide

---

## 4. API-Keys & Services (alle benötigt)

| Service | Zweck | Free? | Wo holen |
|---------|-------|-------|----------|
| **Pexels** | Stock-Photos (primary) | ✅ unbegrenzt | https://www.pexels.com/api/ |
| **Pixabay** | Stock-Fotos (fallback) | ✅ 100/min | https://pixabay.com/api/docs/ |
| **Together AI** | FLUX 1.1 Pro für AI-Renders (Anatomie) | $5 = ~120 Bilder | https://api.together.ai/settings/api-keys (kreditbasiert) |
| **Gemini Flash** | Slide-Plan + Caption-Generation | ✅ Free Tier | https://aistudio.google.com/app/apikey |
| **Google Custom Search** | Optional: echte Promi-Fotos via Google Images | ✅ 100/Tag (nach Billing-Setup) | https://programmablesearchengine.google.com |
| **Cloudinary** | Bild-Hosting für Instagram | ✅ 25 GB free | https://cloudinary.com/users/register/free |
| **Instagram API** | Carousel-Posting | ✅ Free | https://developers.facebook.com (siehe Setup-Guide) |

**Optional zusätzlich:**
- **Replicate**: Alternative AI-Bildquelle (FLUX 1.1 Pro Ultra, etwas teurer)
- **Anthropic Haiku**: Alternative zu Gemini für Slide-Plan ($0.80/M tokens)

---

## 5. Setup für eine NEUE Brand-Seite — komplett

**Voraussetzung**: GitHub-Account, Python 3.11+, Git installiert.

### Schritt 1 — Brand-Identität klären (Fragen an User)
- Brand-Name (z.B. "Mind Recode")
- Instagram-Handle (z.B. `@mindrecode`)
- Brand-Primärfarbe (Hex, z.B. `#FFB800` für Gold)
- Brand-Icon (PNG, ~512×512, transparent) → wird zu `mindrecodeicon.png`
- Profile-Screenshot vom IG-Profil → wird zu `mindrecodefollow.jpg`
- Topic-Bereich (medizinisch, mental health, fitness, etc.)

### Schritt 2 — Repo klonen + Brand-Konfig anpassen
```bash
git clone https://github.com/shinobi1412ai/healthrecode <new-brand>
cd <new-brand>
git remote remove origin
# (neues Repo erstellen + remote add origin neu)
```

In `generate_carousel.py` ändern:
- `BRAND_NAME`, `BRAND_HANDLE`, `BRAND_DISPLAY`
- `BRAND_WORD_LEFT`, `BRAND_WORD_RIGHT`
- `BRAND_CENTER_ICON` = neuer Icon-Filename
- `BRAND_PRIMARY` = neue Hex-Farbe
- Im `OUTRO_FINAL`: `embed_profile_card` = neuer Profile-Screenshot-Filename, `big_follow_cta_parts` mit neuem Handle

### Schritt 3 — Brand-Assets ins Projekt
- Icon (transparent) → `<brand>icon.png`
- Profile-Screenshot vom IG-Profil → `<brand>follow.jpg`
- Optional: Logo top-left → `logo.png` (oder Code-Zeile auskommentieren)

### Schritt 4 — Alle API-Keys neu holen
**Wiederverwendbar von vorheriger Brand**: Pexels, Pixabay, Together AI, Gemini, Google CSE, Cloudinary

**Neu pro Brand benötigt**:
- Eigene Facebook-Page (verlinkt mit IG-Account)
- IG-Account muss Business/Creator sein (in IG-App umstellen)
- Meta Developer App (siehe Schritt 5)

### Schritt 5 — Instagram API Setup (~30 Min, einmalig pro Brand)
1. **IG auf Business**: Instagram-App → Profil → Einstellungen → Kontotyp → Auf professionelles Konto.
2. **Facebook-Page erstellen** falls nicht vorhanden: facebook.com/pages/create
3. **IG mit FB-Page verknüpfen**: Meta Business Suite (business.facebook.com) → Konten → Instagram-Konten → Hinzufügen.
4. **Meta Developer App**: developers.facebook.com → Meine Apps → App erstellen → Business → "Messaging und Content auf Instagram verwalten" Use Case auswählen.
5. **Instagram-Tester**: App-Rollen → Person hinzufügen → Rolle "Instagram-Tester" → @<handle> eingeben.
6. **Tester-Einladung annehmen**: Auf instagram.com mit @<handle> einloggen → Einstellungen → Apps und Websites → Tester-Einladungen → Annehmen.
7. **Permission `instagram_content_publish` aktivieren**: App-Dashboard → Anwendungsfälle → "Personalisieren" → Berechtigungen-Liste → `instagram_content_publish` → "+ Hinzufügen". (Nicht "Zur App-Review hinzufügen" — Bereit zum Testen reicht für eigenes Konto.)
8. **Token generieren**: App → API-Einrichtung mit Instagram-Login → "2. Zugriffstokens generieren" → "Token generieren" Link → Login mit @<handle> → Token kopieren (beginnt mit `IGAA...`).
9. **IG_USER_ID**: Wird neben dem Token angezeigt (17-stellige Zahl).

### Schritt 6 — `.env` befüllen + GitHub Repo pushen
```bash
# .env (NIEMALS committen!)
PEXELS_API_KEY=...
PIXABAY_API_KEY=...
TOGETHER_API_KEY=...
GEMINI_API_KEY=...
GOOGLE_API_KEY=...
GOOGLE_CSE_ID=...
CLOUDINARY_CLOUD_NAME=...
CLOUDINARY_API_KEY=...
CLOUDINARY_API_SECRET=...
IG_APP_ID=...
IG_APP_SECRET=...
IG_USER_ID=...
IG_USER_ACCESS_TOKEN=IGAA...
```

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://<USER>:<PAT>@github.com/<USER>/<REPO>.git
git push -u origin main
```

**PAT mit `repo` + `workflow` Scope**: github.com/settings/tokens → Generate new token (classic).

### Schritt 7 — GitHub Secrets + Test-Run
1. Auf `https://github.com/<USER>/<REPO>/settings/secrets/actions`: alle 13 Werte aus `.env` als einzelne Secrets eintragen.
2. Actions → Daily Health Recode Post → Run workflow → Dry-Run = false → Run.
3. Nach ~3 Min sollte Carousel auf @<handle> live sein.

---

## 6. Brand-Customization in `generate_carousel.py`

Konfigurations-Block oben:
```python
BRAND_NAME = "Health Recode"
BRAND_HANDLE = "@healthrecode"
BRAND_DISPLAY = "HEALTH RECODE"
BRAND_WORD_LEFT = "HEALTH"
BRAND_WORD_RIGHT = "RECODE"
BRAND_CENTER_ICON = "healthrecodeicon.png"

BRAND_PRIMARY = "#00CFE8"   # Cyan (Health Recode)
                              # Andere Brands: #C8252C (rot), #FFB800 (gold), #00FFAA (mint)
```

Outro-Profile-Card im `OUTRO_FINAL`:
```python
"embed_profile_card": "healthrecodefollow.jpg",
"big_follow_cta_parts": [
    ("FOLLOW ", "normal"),
    ("@HEALTHRECODE", "primary"),
    ("<br>TO NOT MISS MORE!", "normal"),
],
```

---

## 7. Häufige Fehler / Lessons Learned (BITTE LESEN)

### 7.1 Cloudinary "Request forbidden — actions=create"
- **Ursache**: API-Key hat keine Upload-Permission
- **Fix**: Cloudinary Console → Security → API Keys → Edit → Roles → "Master Admin"

### 7.2 Custom Search API "blocked-by-allowlist" oder "API not enabled"
- **Ursache**: API ist nicht aktiviert ODER Billing-Account fehlt
- **Fix**: console.cloud.google.com/apis/library/customsearch.googleapis.com → Aktivieren. Plus Billing aktivieren (Trial-$300 reicht ewig).
- **Workaround wenn ohne Billing**: `google_query` einfach nicht setzen — Fallback ist Pexels.

### 7.3 Instagram "Entwickler-Rolle nicht ausreichend"
- **Ursache**: Account ist nicht als Instagram-Tester registriert ODER Tester-Einladung nicht angenommen
- **Fix**: App-Rollen → "+ Person..." → Instagram-Tester → @<handle> hinzufügen → DANN auf instagram.com mit @<handle> einloggen → Apps und Websites → Tester-Einladung annehmen.

### 7.4 `instagram_content_publish` Permission "Bereit zum Testen" reicht
- **NICHT zur App-Review hinzufügen** — das verlangt Tech-Provider-Status den wir nicht brauchen
- "Bereit zum Testen" reicht für eigenes Konto in Dev-Mode

### 7.5 Gemini 503 "high demand"
- **Ursache**: Google-API kurzzeitig überlastet
- **Fix**: Pipeline hat 3 Retries mit exponential backoff. Falls trotzdem fehlschlägt, fällt sie auf Anthropic Haiku zurück (falls `ANTHROPIC_API_KEY` gesetzt).

### 7.6 Together AI "image may contain NSFW content" (false positive)
- **Ursache**: Filter triggert bei harmlosen Anatomie-Prompts
- **Fix**: `get_slide_image` hat try-except → Fallback auf Pexels bei AI-Fehler.

### 7.7 GitHub Push "refusing to allow PAT — workflow scope"
- **Ursache**: PAT hat nur `repo` Scope, nicht `workflow`
- **Fix**: Neuen Token mit BEIDEN Scopes (`repo` + `workflow`).

### 7.8 GitHub Actions "Re-run jobs" nimmt alten Code
- **Ursache**: Re-run nimmt Original-Commit
- **Fix**: Neuen Run via "Run workflow" Button starten — nimmt neuesten Commit.

### 7.9 OUTRO_COMMENT war None nach Refactor
- **Ursache**: Wir haben 2 Outros zu einem gemerged, aber `cloud_pipeline.py` fügte beide an
- **Fix**: `outros = [o for o in (OUTRO_FOLLOW, OUTRO_COMMENT) if o]` filter None.

### 7.10 Bilder unpassend / abstract
- **Ursache**: Pexels-Queries waren zu generisch ("metabolism concept", "energy")
- **Fix**: System-Prompt in `slide_planner.py` zwingt JETZT konkrete visuelle Beschreibungen + AI-Render für Anatomie-Slides.

### 7.11 Cloudinary upload nur 7 von 8 Slides
- **Ursache**: `range(1, 8)` hardcoded statt dynamisch
- **Fix**: `output.glob("slide_*.png")` — nimmt alle automatisch.

### 7.12 Instagram-Posting "no_meta_setup"
- **Ursache**: `post_to_instagram` prüfte alte Env-Vars (`IG_BUSINESS_ACCOUNT_ID`, `META_LONG_LIVED_TOKEN`)
- **Fix**: Neue Funktion nutzt `IG_USER_ID` + `IG_USER_ACCESS_TOKEN` und Endpoint `graph.instagram.com/v22.0`.

---

## 8. Fragen die du dem User direkt stellen solltest (neue Brand)

1. **Brand-Name** und **Instagram-Handle**?
2. **Hauptthemen** der Seite (medizinisch / mental health / fitness / lifestyle / business / etc.)?
3. **Brand-Farbe** (Hex-Code, oder Beschreibung wie "warmes Gold #FFB800")?
4. **Logo + Profile-Screenshot** schon bereit?
5. **Instagram-Account** bereits Business/Creator mit Facebook-Page verknüpft?
6. **Posting-Frequenz** (täglich, 2× täglich, 3× täglich)?
7. **Erste 10-20 Topics** vom User, oder soll Gemini sie generieren?
8. **Sprache** (englisch / deutsch / mix)?
9. **Style** (news-bombast wie @explaining.medicals oder editorial wie @genuinely.healthy)?
10. **Existierende API-Keys vorhanden**? (Pexels, Together AI, Gemini, Cloudinary, Meta App)

---

## 9. Cron Schedule + Topic Management

`.github/workflows/daily_post.yml`:
```yaml
schedule:
  - cron: "0 9 * * *"     # 09:00 UTC = 10/11 DE
  - cron: "0 17 * * *"    # 17:00 UTC = 18/19 DE
```

Anpassen via Cron-Syntax z.B. `"0 7,12,18 * * *"` für 3× täglich.

**Topic-Pflege**:
- `topics.txt` editieren auf GitHub (https://github.com/<repo>/edit/main/topics.txt)
- Eine Zeile = ein Topic
- Auto-Refill: `topic_refresher.py` aktiv wenn <10 Topics

---

## 10. Kosten

| Komponente | Pro Carousel | Pro Monat (60 Posts) |
|-----------|-------------|------------|
| Pexels | $0 | $0 |
| Pixabay | $0 | $0 |
| Gemini Flash | ~$0,001 | $0,06 |
| Together AI (3-4 AI-Bilder à $0,04) | $0,12-0,16 | $7-10 |
| Cloudinary | $0 | $0 |
| Instagram API | $0 | $0 |
| GitHub Actions | $0 | $0 |
| **Total** | **~$0,15** | **~$7-10** |

Bei 2 Posts/Tag → **~$15-20/Monat**. Beim Schnell-Modell statt Pro Ultra → **~$3-5/Monat**.

---

## 11. Wichtige Style-Regeln (Memory Lessons)

- **Engagement-CTA Pflicht**: jeder Post bekommt Follow/Like/Comment-Prompt (im Outro automatisch).
- **Slide-Count flexibel**: 3-15 content + 1 outro je nach Topic-Tiefe.
- **Hero-Slide MUSS visuell hooken**: kein generisches "person meditating" — entweder AI-Render der Topic-Anatomie oder Pexels-Foto mit klarer Emotion.
- **Anatomie-Slides immer AI-Render**: Pexels hat keine guten Anatomie-Bilder.
- **Pexels-Queries müssen konkret sein**: "woman holding stomach" NICHT "metabolism concept".
- **Bold/Regular Mix in Headlines**: Verbindungswörter `regular` (light), Keywords `bold`/`primary`.
- **Topic-Restriction**: alles muss medizinisch/health/anatomy bleiben — kein generisches Lifestyle.

---

## 12. Inspiration-Datenbank

Pflege `inspiration/database.md` mit Patterns von Konkurrenz-Pages. Wenn User Screenshots schickt, analysieren + speichern. Pages bisher gesichtet:
- @explaining.medicals (rot, news-style, klinische Fakten)
- @genuinely.healthy (cyan, Studien + Wellness)
- @mentality_facts (gold, bold/regular weight mix)
- @sferro.ai (für AI-Bild-Style-Inspiration)

---

## 13. Kontakt-Info / Bestehende Setup-Daten (Health Recode)

- GitHub Repo: https://github.com/shinobi1412ai/healthrecode
- IG Handle: @healthrecode
- Brand-Color: `#00CFE8` (Cyan)
- IG_USER_ID: 17841408331390991
- Meta App: HealthRecode (App-ID: 1704678274040059)
- Cloudinary Cloud: `dzpo48ngf`
- Google CSE: `06acc5c209c1a4dc9`

---

## 14. Schnell-Reference: Standard-Befehle

```bash
# Lokal testen (1 Slide)
python generate_carousel.py --only 1

# Lokal komplett-Test
python cloud_pipeline.py "Vitamin D deficiency" --upload --post

# Topic refreshen
python topic_refresher.py

# GitHub Actions manuell triggern
# → https://github.com/<repo>/actions/workflows/daily_post.yml → Run workflow

# Push Änderungen
git add . && git commit -m "Update" && git push
```

---

## 15. NEXT STEPS für neue Brand

1. User fragen: Brand-Name, IG-Handle, Brand-Color, Themen, vorhandene Keys
2. Repo forken / klonen
3. Brand-Konfig in `generate_carousel.py` updaten
4. Brand-Assets (icon, logo, follow-screenshot) hinzufügen
5. Falls Keys fehlen: Setup-Schritte 4-5 durchgehen (Instagram API ist der zähste, ~30 Min)
6. GitHub Secrets eintragen
7. Erste Test-Run (Dry-Run = false)
8. Live-Post auf neuer Seite checken
9. Bei Erfolg: Cron läuft autonom — User muss nur Topics nachschieben (oder Gemini macht's automatisch)

---

**Ende des Handover-Guides**. Bei Fragen: User direkt fragen, NICHT raten.
