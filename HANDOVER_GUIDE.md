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

---

## 16. Original Design-Foundation (Cindi Zhu Carousel Generator)

Das Projekt basiert ursprünglich auf dem **"Instagram Carousel Generator"** Project-Prompt von **@cindiezhu** (Notion-URL hat User: das ist die Quelle des Stil-Frameworks). Die wichtigsten Prinzipien daraus, die in unserem `generate_carousel.py` implementiert sind:

### 16.1 Slide-Format
- **4:5 Aspect Ratio** (Instagram-Carousel-Standard)
- HTML wird bei **420×525px** gerendert, mit `device_scale_factor=2.5714` zu **1080×1350px** skaliert (KEIN Viewport-Reflow)
- Jede Slide ist self-contained — alle UI-Elemente in der Slide, keine Overlays

### 16.2 Color-System (6-Token aus 1 Primary)
Aus einer einzigen Brand-Color werden 6 abgeleitet:
- `BRAND_PRIMARY` — User-Color (Akzent)
- `BRAND_LIGHT` — primary +20% lightness
- `BRAND_DARK` — primary -30% lightness
- `LIGHT_BG` — getintetes Off-White
- `LIGHT_BORDER` — ~1 Schritt dunkler als LIGHT_BG
- `DARK_BG` — Near-black mit Brand-Tint

### 16.3 Typography
Cindis empfohlene Pairings:
- Editorial: Playfair Display + DM Sans
- Modern: Plus Jakarta Sans
- Warm: Lora + Nunito Sans
- Technical: Space Grotesk
- Bold: Fraunces + Outfit
- Health-Recode nutzt: **Oswald + Inter + JetBrains Mono** (Vital-Signs-Strip)

### 16.4 Slide-Architektur (adaptiert)
Cindis Original-Sequenz: Hero → Problem → Solution → Features → Details → How-To → CTA

**Unsere Health-Recode-Adaption**:
- Hero (3-6 Wörter Hook)
- Content-Slides (3-15 stufenweise Erklärung)
- Outro (Engagement + Profile-Card + Share-CTA)

### 16.5 Export-Methode (kritisch!)
Aus Cindi's Prompt direkt übernommen:
- **HTML wird mit Python erzeugt** (NICHT Shell — `$` und Backticks zerstören Inhalte)
- **Bilder als base64-data-URIs** im HTML eingebettet (nicht externe URLs während Generierung)
- **Playwright `device_scale_factor=2.5714`** statt Viewport-Resize (Layout bleibt identisch zwischen Preview und Export)
- **`wait_for_timeout(3000)` für Fonts** (sonst Fallback-Fonts)
- **Vor Screenshot**: IG-Frame-Chrome ausblenden (`.ig-header,.ig-dots,.ig-actions,.ig-caption`)
- **Carousel-Track per JS verschieben**: `track.style.transform = 'translateX(' + (-idx * 420) + 'px)'`

### 16.6 Reusable Components (von Cindi inspiriert)
- Tag/Category-Label (10px uppercase 2px-letter-spacing)
- Logo-Lockup (40px circle BRAND_PRIMARY + Initial)
- Strikethrough-Pills für "what's being replaced"
- Numbered-Steps für Workflows
- Color-Swatches für Customization-Slides
- Watermark (optional, opacity 0.04-0.06)

### 16.7 Cindi Zhus Design-Prinzipien (alle befolgt)
1. ✅ Every slide is export-ready (UI baked in, nicht overlay)
2. ✅ Light/dark alternation (in unserem Fall: dunkler Hintergrund mit Photo dominiert, Outro mit cosmic black)
3. ✅ Heading + body font pairing
4. ✅ Brand-derived palette
5. ✅ Progress bar + arrow guide forward motion (in unserem Style: nur Pfeil, IG handled Dots automatisch)
6. ✅ Last slide special (no arrow, full progress)
7. ✅ Consistent components
8. ✅ Content padding clears UI
9. ✅ Iterate fast (slide-by-slide, not full rebuild)

### 16.8 Was wir ÜBER Cindi Zhus Original hinaus gebaut haben:
- **Vital-Signs-Strip** (HR/SpO₂/T° in JetBrains Mono) — unsere Signature
- **Bold/Regular Mix** (mentality_facts inspiriert) — Connector-Wörter dünn, Keywords fett
- **Multi-Source Image Pipeline** (Pexels → Pixabay → AI → Google Images) mit gracefuller Fallback
- **Auto-Slide-Plan via Gemini** statt manueller Topic-Eingabe
- **Auto-Topic-Refresh** wenn Queue leer
- **Embedded Profile-Card** im Outro (statt nur Logo)
- **Cron-Schedule + GitHub Actions** für 24/7 autonomen Betrieb
- **Cloudinary + Instagram Graph API Integration** (Cindi's Prompt postet nicht selbst)

---

---

## 17. STYLE BIBLE — Exakte visuelle Spezifikation (Pflicht-Look)

**JEDER Slide muss diesen Look haben.** Inspiriert von @mentality_facts, @explaining.medicals, @genuinely.healthy.

### 17.1 Layout-Komponenten von oben nach unten:

```
┌───────────────────────────────────────────┐
│  [Vital-Signs Strip oben rechts]          │ ← Top 4-8% (HR ✱ SpO₂ ✱ T)
│                                           │
│                                           │
│                                           │
│       [Foto-Hintergrund — full-bleed]    │ ← Top 0-55%
│       (Pexels/AI, EmotionsHook)           │
│                                           │
│       [optional: Kreis-Inset oben rechts] │ ← optional, runder Frame
│                                           │
│  ─────  HEALTH 🌿 RECODE  ─────           │ ← Logo-Block ~55%
│                                           │
│  HEADLINE H1 (Bold/Regular Mix)           │ ← H1 ~60%
│  Subhead H2 (kleiner, mit cyan Keywords)  │ ← H2 ~70%
│  Description (kleinster Text)             │ ← optional
│                                           │
│  FOLLOW @HEALTHRECODE TO NOT MISS MORE    │ ← Follow-CTA cyan
│                                           │
│         SWIPE FOR MORE  >                 │ ← Bottom 92%
└───────────────────────────────────────────┘
```

### 17.2 Konkrete CSS-Werte (PFLICHT — nicht überschreiben!)

```css
/* Vital-Signs oben rechts */
.vitals-strip { top: 14px; right: 14px; padding: 3px 8px;
  background: rgba(0,0,0,0.18); backdrop-filter: blur(4px);
  font-family: 'JetBrains Mono'; font-size: 7.5px;
  color: rgba(255,255,255,0.55); }
.vitals-strip .value { color: rgba(0,207,232,0.75); font-weight: 700; }
.vitals-strip .pulse-dot { 4×4px circle, brand-cyan, glow }

/* Bottom-Stack mit Logo + Headlines */
.bottom-stack { position: absolute; bottom: 70px; top: 55%;
  display: flex; flex-direction: column; gap: 6px;
  text-align: center; padding: 0 24px; }

/* Logo-Block: ─── HEALTH (icon) RECODE ─── */
.logo-block { gap: 5px; }
.logo-line { 70px wide, 1px height, gradient cyan }
.logo-text { Inter 600, 11px, 2.5px letter-spacing, weiß }
.logo-center-icon { 16×16px contain }

/* Headline Auto-Sized (15% kleiner als brutaler default) */
.headline { Oswald 700, line-height 1.0, letter-spacing 0.3px,
  text-shadow: 0 3px 12px rgba(0,0,0,0.55), 0 1px 3px rgba(0,0,0,0.40);
  font-size auto: 39 (kurz) → 17 (sehr lang) }

/* Subhead — Oswald 600, kleiner */
.subhead { font-weight 600, line-height 1.05,
  color rgba(255,255,255,0.92), shadow stark }

/* Follow-CTA dezent unter Headlines */
.follow-cta { Inter 600, 8px, 1px letter-spacing, brand-cyan,
  margin-top 2px }

/* Swipe-CTA ganz unten (mit > Pfeil!) */
.swipe-cta { bottom: 30px, gap 6px text + chevron-svg-mini }
.swipe-arrow-mini { 11×11px chevron, rgba(255,255,255,0.85) }

/* Right-Edge Swipe-Pfeil-Pill (auf jeder Slide außer letzter) */
.swipe-arrow-right { 28×28px circle, rgba(255,255,255,0.18),
  backdrop-filter blur(4px), chevron weiß, rechts mittig }

/* Background-Gradient — STARK von unten nach oben */
.bg-gradient { linear-gradient 180deg:
  0% transparent → 25% transparent →
  40% rgba(10,10,15,0.35) → 55% 0.75 → 70% 0.92 →
  85% 0.98 → 100% 1.0 }
```

### 17.3 Typography-Hierarchie (Pflicht)

| Element | Font | Weight | Size | Color |
|---------|------|--------|------|-------|
| Vital-Strip | JetBrains Mono | 400/700 | 7.5px | white-55%, primary-75% values |
| Logo-Text | Inter | 600 | 11px | white |
| H1 Headline | Oswald | 700 | auto 17-39px | white + primary keywords |
| H2 Subhead | Oswald | 600 | ~60% of H1 | white-92% + primary keywords |
| Description | Oswald | 600 | 15px | white |
| Follow-CTA | Inter | 600 | 8px | primary cyan |
| Swipe-CTA | Inter | 600 | 10px | white-85% |
| Big Follow CTA (Outro) | Oswald | 400 | 22px | mixed white + primary |
| Share-CTA (Outro) | Oswald | 500 | 13px | white-95% |

### 17.4 Bold/Regular/Primary Mix-Regel (mentality_facts inspired)

In jeder Headline/Subhead-Zeile:
- **Verbindungswörter** ("the", "is", "and", "your", "in", "of") → `regular` (font-weight: 300, light)
- **Keywords / Aktionen** → `bold` (font-weight: 700, weiß)
- **Topic-Hauptbegriffe / Zahlen** → `primary` (cyan, weight: 700)
- **Default** → `white` (weiß bold)

Beispiel-Zeile:
```python
("AT HOUR 12, ", "regular"),   # dünn
("KETOSIS", "primary"),          # cyan bold
(" BEGINS — YOUR BODY ", "regular"),  # dünn
("EATS ITS OWN FAT", "bold"),    # weiß bold
```

### 17.5 Image-Regeln (Pflicht!)

**Hero-Slide MUSS visuelle Emotion zeigen**:
- ✅ Person in Topic-relevanter Aktion (laufend, schlafend, an Brust greifend)
- ✅ Hyperrealistic AI-Render der Topic-Anatomie (Herz, Hirn, Zellen)
- ❌ NIE generisches "person meditating", "sunset silhouette", "calm woman"

**Anatomie-Slides → IMMER `ai_render: true`**:
- Pexels hat KEINE guten Anatomie-Renders
- AI-Prompt MUSS spezifisch sein: "Photorealistic 3D render of human heart muscle, anatomically accurate, dramatic studio lighting, deep red tones, medical textbook quality, 8k"

**Lifestyle-Slides → Pexels mit konkreter Szene**:
- ✅ "young woman holding stomach in pain"
- ✅ "man drinking water at sunrise"
- ❌ "energy concept", "metabolism vitality", "depletion mood"

### 17.6 Engagement-Elemente (auf JEDEM Slide außer letzter)

1. **SWIPE FOR MORE >** Text + chevron unten zentriert
2. **Right-edge Pfeil-Pill** mittig rechts (außer letzter Slide)
3. **Vital-Signs Strip** oben rechts (gibt Glaubwürdigkeit als "Medical Monitor")
4. **FOLLOW @HEALTHRECODE...** über dem Swipe-CTA

### 17.7 Outro-Slide (letzte Slide) — Spezialregeln

- KEIN Foto-Hintergrund — sondern AI-Render "dark cosmic minimalist" oder schwarz
- KEIN Vital-Strip rechts (oder dezent)
- KEIN Right-edge Pfeil
- KEIN "SWIPE FOR MORE" — stattdessen "Share this with your Friends →"
- Logo-Block AUSGEBLENDET (nur die Engagement-Hierarchie)
- 4 Text-Ebenen: H1 (DROP A 🔥), H2 (IF YOU LEARNED / SOMETHING NEW!), Description (WHICH FACT SHOCKED YOU MOST?), Big Follow CTA
- **Profile-Card** (`healthrecodefollow.jpg`) als embedded Box mit Cyan-Border
- Position: alles oben (top: 40px), Profile-Card unten

### 17.8 Brand-Color-Treatment (cyan @ Health Recode)

- Primary: `#00CFE8` (Cyan)
- Niemals zu viele cyan Wörter pro Headline (max 1-2 Keywords)
- Cyan sollte AUFFALLEN, nicht dominieren
- Bei dunklem Hintergrund: cyan glüht
- Bei hellem Hintergrund: stark abdunkeln den BG (gradient)

### 17.9 EXAKTE ZAHLEN-REFERENZ (alle px/%/% Werte zentral)

#### Slide-Layout
| Wert | Pixel/Prozent |
|------|---------------|
| HTML-Render-Width | `420px` (interner Layout) |
| HTML-Render-Height | `525px` (4:5 ratio) |
| Export-Output-Width | `1080px` |
| Export-Output-Height | `1350px` |
| Device-Scale-Factor | `2.5714` (1080/420) |
| Slide-Padding-X | `0 24px` (default) |

#### Background-Gradient (exakte Stops!)
```css
.bg-gradient {
  background: linear-gradient(
    180deg,
    rgba(10,10,15,0.0)  0%,    /* oben transparent */
    rgba(10,10,15,0.0)  25%,   /* bleibt klar bis 25% */
    rgba(10,10,15,0.35) 40%,   /* ab 40% leicht abdunkeln */
    rgba(10,10,15,0.75) 55%,   /* mitte stark dunkel */
    rgba(10,10,15,0.92) 70%,   /* fast voll dunkel */
    rgba(10,10,15,0.98) 85%,   /* near-black */
    rgba(10,10,15,1.0)  100%   /* unten 100% schwarz */
  );
}
```
- **Photo bleibt klar** in oberen 25% des Slides
- **Fade beginnt bei 40%** vom oberen Rand
- **Texte ab 55-70%** liegen auf dunklem Bereich → max Lesbarkeit
- **WICHTIG**: nie unter 0.92 in den unteren 30% — sonst Texte zu schwach lesbar

#### Element-Positionen (exakte Pixel von oben/unten)
| Element | Position |
|---------|----------|
| Vital-Strip | `top: 14px; right: 14px` |
| Logo-Block (im Bottom-Stack) | `bottom: 70px; top: 55%` (Bottom-Stack Container) |
| Bottom-Stack `gap` zwischen Items | `6px` |
| Right-Edge Swipe-Arrow | `right: 12px; top: 50%; transform: translateY(-50%)` |
| Swipe-CTA | `bottom: 30px` (zentriert) |
| Profile-Card (Outro) | `bottom: 50px; left: 24px; right: 24px` |
| Share-CTA | `bottom: 32px` (zentriert) |

#### Element-Größen
| Element | Pixel |
|---------|-------|
| Vital-Strip Padding | `3px 8px` |
| Vital-Strip Pulse-Dot | `4×4px` (`box-shadow: 0 0 4px primary`) |
| Logo-Block Gap | `5px` (zwischen den Wörtern + Icon) |
| Logo-Line | `flex: 0 0 70px; height: 1px` |
| Logo-Center-Icon | `16×16px` |
| Right-Edge Swipe-Arrow | `28×28px` (Circle, blur 4px BG) |
| Swipe-Arrow-Mini (chevron) | `11×11px` |
| Profile-Card Border | `1.5px solid rgba(0,207,232,0.55)` |

#### Text-Shadow Werte (kritisch für Lesbarkeit)
| Element | Shadow |
|---------|--------|
| Headline H1 | `0 3px 12px rgba(0,0,0,0.55), 0 1px 3px rgba(0,0,0,0.40)` |
| Subhead H2 | `0 2px 10px rgba(0,0,0,0.50), 0 1px 3px rgba(0,0,0,0.35)` |
| Description | `0 2px 8px rgba(0,0,0,0.45), 0 1px 2px rgba(0,0,0,0.30)` |
| Big Follow CTA | `0 3px 12px rgba(0,0,0,0.55), 0 1px 3px rgba(0,0,0,0.40)` |
| Share-CTA | `0 2px 6px rgba(0,0,0,0.30)` |

#### Auto-Headline-Size (calc_headline_size)
| Total Zeichen | Font-Size |
|---------------|-----------|
| < 25 | **39px** (1-3 Wörter) |
| < 40 | **34px** (kurz) |
| < 55 | **30px** (mittel-kurz) |
| < 75 | **26px** (mittel) |
| < 100 | **22px** (lang) |
| < 130 | **20px** (sehr lang) |
| ≥ 130 | **17px** (extra lang) |

#### Subhead-Size = ~60% der Headline-Size
```python
subhead_size = max(14, int(headline_size * 0.55))
```

#### Color-Tokens (Health Recode)
```python
BRAND_PRIMARY = "#00CFE8"        # Cyan
BRAND_LIGHT_TINT = "#FAF6F2"     # warm cream
BRAND_DARK_TINT = "#1A1918"      # near-black warm
WHITE_92 = "rgba(255,255,255,0.92)"   # für regular subhead
WHITE_55 = "rgba(255,255,255,0.55)"   # für vitals labels
WHITE_35 = "rgba(255,255,255,0.35)"   # für vitals dividers
PRIMARY_75 = "rgba(0,207,232,0.75)"   # für vitals values
```

#### Font-Weight Mapping (in render_headline)
```python
"primary" → font-weight: 700, color: BRAND_PRIMARY
"bold"    → font-weight: 700, color: white
"regular" → font-weight: 300, color: rgba(255,255,255,0.92)
"normal"  → font-weight: 400, color: white
"white"   → font-weight: 700, color: white  (default)
```

#### Slide-Count-Range
| Topic-Tiefe | Content-Slides | Total (mit Outro) |
|-------------|----------------|-------------------|
| Quick fact | 3-4 | 4-5 |
| Standard explainer | 5-7 | 6-8 |
| Deep dive | 8-15 | 9-16 |

#### Cron-Schedule (.github/workflows/daily_post.yml)
```yaml
schedule:
  - cron: "0 9 * * *"     # 09:00 UTC = 10/11 DE
  - cron: "0 17 * * *"    # 17:00 UTC = 18/19 DE
```

#### Topic-Refresh-Threshold
- **<10 Topics** in topics.txt → Auto-Refresh via Gemini
- **+50 neue** werden generiert und angehängt
- Alte Topics bleiben auskommentiert (für History)

---

---

## 18. Token-Lifecycle (KRITISCH — sonst stoppt die Pipeline nach 60 Tagen!)

### 18.1 Instagram Access Token (IGAA...) — läuft nach 60 Tagen ab
- Wird automatisch refreshed durch Aufruf von `verify_instagram.py` (call to `/access_token` mit `grant_type=ig_refresh_token`)
- **Lösung 1 (manuell)**: Alle 50-58 Tage `verify_instagram.py` lokal laufen lassen → kopiert neuen Token in .env, dann GitHub Secret updaten
- **Lösung 2 (automatisch)**: Build a `refresh_token.py` Workflow der monatlich via GitHub Actions läuft + Secret per API updated (komplexer, später)
- **Erkennung**: Wenn `Status: error: ... access_token invalid` in den Logs erscheint → Token abgelaufen

### 18.2 GitHub Personal Access Token
- Wenn `expiration: No expiration` gewählt → läuft nicht ab
- Sonst: alle 30/60/90 Tage neu generieren
- Im Repo Remote-URL ersetzen: `git remote set-url origin https://USER:NEW_TOKEN@github.com/...`

### 18.3 Andere API-Keys (statisch, kein Refresh nötig)
- Pexels, Pixabay, Together AI, Gemini, Cloudinary, Google CSE — laufen NICHT ab
- Können bei Verlust/Leak rotiert werden im jeweiligen Dashboard

---

## 19. Caption-Format & Hashtag-Strategie

Gemini generiert Captions automatisch nach folgendem Schema (im System-Prompt von slide_planner.py):
- **200-400 Wörter** Story/Erklärung
- **3-5 Faktencluster** im Body
- **5 Emojis** zur Auflockerung (📌 🔬 💡 🧠 ✅ etc.)
- **8 Hashtags** am Ende (Mix aus Topic + Category + Brand + Generic)

Beispiel:
```
Ever wondered what truly happens inside your body during an extended fast? 🤔

The 72-hour fast is a powerful metabolic intervention...

[200 words narrative + science]

#FastingBenefits #72HourFast #Autophagy #MetabolicHealth
#HealthRecode #ExtendedFasting #CellularRepair #Ketosis
```

**Best practices**:
- Hashtags **am Ende** (nicht im Body)
- 5-10 Hashtags reicht (mehr wird vom Algo abgewertet)
- **Erste 125 Zeichen** sind kritisch (preview im Feed) → starker Hook
- Keine Health-Claims die als "medizinische Beratung" durchgehen könnten (FTC/Meta Guidelines)

---

## 20. Failure Recovery & Monitoring

### 20.1 Was kann schiefgehen
1. **Gemini 503** → Retry Logic (3× exponential backoff) → fallback Anthropic Haiku
2. **Pexels 0 Treffer** → Pixabay Fallback → vereinfachte Query
3. **Together AI NSFW false-positive** → fallback Pexels
4. **Cloudinary upload fail** → Pipeline stoppt, kein Post
5. **IG Token expired** → Status "error: invalid token", kein Post
6. **Google CSE billing fehlt** → optionale Permission, Fallback ist Pexels
7. **Carousel-Container "ERROR" Status bei Publish** → IG hat Bild abgelehnt (zu groß, falsches Format)

### 20.2 Monitoring
- **GitHub Actions History**: https://github.com/<repo>/actions
- **Logs aufrufen**: Failed Run → Job → expand jeden Step
- **Email-Alerts**: aktivierbar in Repo Settings → Notifications → "Failed Workflows"

### 20.3 Manuelle Recovery
- Failed Run → "Re-run jobs" (für temporäre API-Fehler) — ABER: nimmt alten Commit, nicht latest!
- Nach Code-Änderung: Always **"Run workflow"** (neuer Run mit aktuellem Code)
- Bei IG-Token-Expiry: neu generieren via Graph API Explorer → Secret updaten

---

## 21. First-Post Checklist (vor erstem Live-Post)

Bevor du dry_run=false aktivierst, prüfe:

- [ ] `.env` lokal komplett (alle 13 Werte)
- [ ] Alle Werte als GitHub Secrets eingetragen
- [ ] Logo + Icon + Profile-Card im Repo (push erfolgreich)
- [ ] `BRAND_NAME`, `BRAND_HANDLE`, `BRAND_PRIMARY` im Code aktualisiert
- [ ] Mindestens 3 Test-Topics in `topics.txt`
- [ ] Erster Run als Dry-Run = true → Slides als Artifact prüfen
- [ ] Slides visuell akzeptabel (Layout, Lesbarkeit, Bild-Match)
- [ ] Caption gelesen (Tonalität, Hashtags, Länge)
- [ ] Instagram-Account hat:
  - [ ] Business/Creator Status
  - [ ] Verknüpfte FB-Page
  - [ ] App als Instagram-Tester registriert
  - [ ] Tester-Einladung angenommen
- [ ] Cloudinary Master-Admin-Permissions gesetzt
- [ ] Falls Cross-Post zu FB gewünscht: Account Center IG↔FB Page verknüpft

Erst wenn alle ✅ → dry_run = false → Live-Post.

---

## 22. Multi-Account-Scaling

Wenn du mehrere IG-Seiten betreust (Health Recode + andere Brand):

### 22.1 Repo-Strategie
**Option A: Separate Repos** (empfohlen für Setup-Klarheit)
- Pro Brand ein Fork dieses Repos
- Eigene topics.txt, eigene Brand-Config, eigene Secrets
- Eigener Cron-Schedule

**Option B: Multi-Brand im selben Repo**
- Branches pro Brand: `main` = Health Recode, `mindrecode` = Mind Recode
- Workflow-Files pro Branch
- Secrets pro Branch (mehr Verwaltungsaufwand)

### 22.2 Wiederverwendbare Keys
Diese können brand-übergreifend genutzt werden:
- Pexels, Pixabay, Together AI, Gemini, Google CSE → 1 Account reicht für alle
- Cloudinary → 1 Account, separate Folders pro Brand

### 22.3 Brand-spezifisch (neu pro Account)
- Eigene FB-Page
- Eigener IG_USER_ACCESS_TOKEN
- Eigener IG_USER_ID
- Optional: separate Meta Dev App (sonst kann eine App mehrere IGs verwalten)
- Eigene Brand-Color, Logo, Profile-Card

---

## 23. Topic-Guidelines (was funktioniert, was nicht)

### 23.1 GUTE Topics (hoher Engagement-Score)
- Konkrete Studien mit Zahlen ("120 Frauen", "8 Wochen", "99%")
- Skurrile/überraschende Fakten ("81 Zähne", "Mütter-Zellen bleiben")
- Anatomie mit Aha-Effekt ("warum Frauen-Gehirn schrumpft")
- Schritt-für-Schritt Mechanismen ("was passiert nach Stunde X")
- Bekannte Conditions mit neuer Perspektive ("Diabetes ist reversibel")

### 23.2 SCHLECHTE Topics (vermeiden)
- Vage Lifestyle-Tipps ohne Wissenschaft ("trink mehr Wasser")
- Politik / kontroverse Themen
- Promi-Klatsch ohne medizinischen Anker
- Werbung für spezifische Marken/Produkte
- Gefährliche Behauptungen ("X heilt Krebs") → Meta sperrt
- Mental-Health-Krisen-Inhalte (Suizid, Selbstverletzung) → strikte IG-Regeln

### 23.3 IG-Banned-List (auto-blocken in Topics-Generator)
Wörter/Themen die IG flaggen kann:
- explizite Krankheits-Heilungs-Versprechen
- Diet-Pills / Supplement-Hype
- "Mirale Cures", "Big Pharma Lies"
- Skin-bleaching
- COVID/Vaccine-conspiracy
- Eating-Disorder-Triggerwörter

→ slide_planner.py System-Prompt erwähnt: "stay strictly medical/health/anatomy" → Gemini hält sich daran.

---

## 24. Performance & Optimization (späterer Ausbau)

### 24.1 Was tracken
- IG Insights pro Post (nach 7-14 Tagen): Likes, Comments, Saves, Reach, Impressions
- Welche Topics performen am besten?
- Welche Bild-Style (AI vs Pexels) bringt mehr Engagement?

### 24.2 Auto-Remix erfolgreicher Posts
Geplant (siehe `project_remix_feature.md` in Memory):
- Top 25% performende Posts → automatisch nach 14 Tagen remixen
- Gleiches Topic, andere Bilder, leicht abgewandelte Headlines
- A/B-Test welche Variante besser performt

### 24.3 Image-Cache Cleanup
`image_cache/` Folder wächst über Zeit. Empfohlen:
- Alle 30 Tage: `rm -rf image_cache/*` (forces fresh fetches)
- Oder: GitHub Action Cleanup-Job einbauen

---

## 25. Local Development Setup (Testen vor Push)

```bash
# Erstmaliges Setup
cd <repo>
pip install -r requirements.txt
python -m playwright install chromium

# Lokal komplett laufen lassen (NICHT posten)
python cloud_pipeline.py "Test Topic" --upload   # nur Cloudinary
python cloud_pipeline.py "Test Topic" --upload --post  # auch IG (live!)

# Nur 1 Slide rendern für Layout-Test
python generate_carousel.py --only 1

# Topic-Plan ohne Carousel anzeigen
python slide_planner.py "Vitamin D deficiency" --out plan.json

# Topics-Refresh manuell triggern
python topic_refresher.py --force

# Verify-Skripte
python verify_pexels.py
python verify_instagram.py
python verify_cloudinary.py
```

---

---

## 26. ⚠️ API-Versions WICHTIG! (2024+ Instagram API vs 2018 Meta Graph API)

**Es gibt 2 unterschiedliche Wege Instagram-Posts zu automatisieren. NIEMALS den alten 2018er Weg verwenden!**

### 26.1 Vergleich der zwei API-Wege:

| Aspekt | ❌ ALT: Meta Graph API (2018-2023) | ✅ NEU: Instagram Login API (2024+) |
|--------|----------------------------|--------------------------|
| Endpoint | `graph.facebook.com/v21.0/{ig-business-id}/...` | `graph.instagram.com/v22.0/{ig-user-id}/...` |
| Token Format | `EAAxxx...` (FB Long-lived) | `IGAAxxx...` (IG direkt) |
| Token-Quelle | Graph API Explorer (FB-Login + Page-Access) | Instagram Login Flow (direkt vom IG-Account) |
| App-Setup | Meta Dev App + Facebook-Page-Verknüpfung + viele Permissions | Instagram-API Use-Case + Tester-Invite |
| Permissions nötig | `instagram_basic`, `instagram_content_publish`, `pages_*` | `instagram_business_basic`, `instagram_content_publish` |
| Tech-Provider-Status nötig? | Oft ja (für `instagram_content_publish`) | Nein für eigenes Konto in Dev-Mode |
| FB-Page-Verknüpfung | Pflicht | Praktisch nicht nötig (nur für Cross-Posting) |
| App Review nötig? | Ja für Production | Nein für eigenes Konto (Dev-Mode reicht) |
| Token-Lebensdauer | 60 Tage refreshable | 60 Tage refreshable |
| Setup-Zeit | 1-3 Stunden + Wartezeit auf Tech-Provider-Approval | 30 Min |

### 26.2 ⚠️ KRITISCH — In `cloud_pipeline.py` MUSS dieser Code stehen:

```python
# RICHTIG (2024+):
BASE = "https://graph.instagram.com/v22.0"
ig_id = os.environ.get("IG_USER_ID")
token = os.environ.get("IG_USER_ACCESS_TOKEN")  # Beginnt mit "IGAA..."
r = requests.post(f"{BASE}/{ig_id}/media", ...)
```

```python
# FALSCH (2018er Meta Graph API — vermeiden!):
BASE = "https://graph.facebook.com/v21.0"
ig_id = os.environ.get("IG_BUSINESS_ACCOUNT_ID")  # über FB-Page!
token = os.environ.get("META_LONG_LIVED_TOKEN")  # Beginnt mit "EAA..."
r = requests.post(f"{BASE}/{ig_id}/media", ...)
```

### 26.3 So erkennt der neue Claude welche API du benutzt:

- **Token beginnt mit `IGAA...`** → Neue Instagram Login API ✅ (was wir nutzen)
- **Token beginnt mit `EAA...`** → Alte Meta Graph API ❌ (nicht nutzen)

Falls beide vorhanden in `.env`: nimm den `IGAA...` Token, ignoriere `EAA...`.

### 26.4 Wenn du auf eine neue Brand umsteigst:

1. Folge dem Instagram-Login-Flow (Schritt 5.1-5.9 in Sektion 5)
2. Token via Graph API Explorer **NICHT** nutzen — gibt dir den falschen `EAA...` Token
3. Stattdessen via App-Dashboard → "API-Einrichtung mit Instagram-Login" → "2. Zugriffstokens generieren" → "Token generieren"
4. Du bekommst den `IGAA...` Token (richtig)

### 26.5 Warum die alte API NICHT mehr empfohlen ist:

- Meta wird sie irgendwann deprecaten (Datum noch nicht angekündigt aber kommt)
- Komplizierteres Setup (Tech-Provider-Approval, App-Review)
- Mehr Failure-Points (FB-Page-Disconnect, Permission-Drift)
- Weniger Zukunftssicherheit
- Die neue API ist für Solo-Creator und kleinere Brands optimiert

**Wenn du jemand anderen siehst die `graph.facebook.com` für Instagram nutzt: das ist die alte Methode. Neue Implementierungen IMMER auf `graph.instagram.com` setzen.**

---

## 27. Engagement-Banner (mid-carousel SAVE-CTA)

Bereits implementiert in `generate_carousel.py` via `engagement_text` Feld.

### 27.1 Wann einsetzen
Bei langen Carousels (8+ Slides) auf einer mittleren Slide einen Engagement-Nudge. Beispiele:
- "💾 SAVE THIS POST — IT'S ABOUT TO GET INTERESTING"
- "❤️ DOUBLE-TAP IF YOU LEARNED SOMETHING NEW"
- "📌 SAVE FOR LATER"
- "🔥 KEEP SCROLLING — BEST FACT COMING"

### 27.2 Wie aktivieren in der Slide-Config:
```python
{
    "type": "engagement",
    "headline_parts": [...],
    "subhead_parts": [...],
    "engagement_text": "💾 SAVE THIS POST — IT'S ABOUT TO GET INTERESTING",
    ...
}
```

### 27.3 Visual:
- Cyan Hintergrund (`BRAND_PRIMARY`)
- Schwarzer Text bold
- Padding 10px 14px
- Border-radius 4px
- Erscheint unter dem Description-Text auf der entsprechenden Slide

### 27.4 Best Practice:
Bei Carousels mit 8+ Slides → Engagement-CTA auf Slide 4 oder 5 (mitten drin, wo User entscheiden ob er weiter scrollt). Bei 6-7 Slides eher nicht — wirkt überladen.

---

---

## 28. 🔄 FALLBACK-CHAINS & FAILURE-ROUTING (PFLICHT-LESEN!)

**GRUNDPRINZIP**: Die Pipeline darf NIEMALS bei einem API-Fehler komplett abbrechen. Jede Komponente hat eine **Fallback-Kette** — wenn X fehlschlägt, automatisch zu Y, dann Z. Erst wenn ALLE durch sind, abbrechen.

### 28.1 Bild-Quellen-Routing (in `generate_carousel.py` → `get_slide_image()`)

```
1. solid_color gesetzt?      → Generiere Solid-Color-PNG (Pillow) → fertig
2. local_bg gesetzt?         → Lade Datei aus Projekt-Ordner → fertig
3. google_query gesetzt?     → Google Images CSE
                               ├── 200 OK? → fertig
                               └── Fail? → fallthrough zu Stufe 4 (Pexels)
4. ai_render: True?          → Together AI FLUX 1.1 Pro
                               ├── 200 OK? → fertig
                               ├── 422 NSFW false-positive? → fallthrough zu 5
                               ├── Network error? → fallthrough zu 5
                               └── Anderes? → fallthrough zu 5
5. Default: Pexels           → mit color filter
                               ├── Treffer > 0? → fertig
                               └── 0 Treffer? → fallthrough zu 6
6. Pexels ohne color         → vereinfachte Query (color removed)
                               └── 0 Treffer? → fallthrough zu 7
7. Pexels simplified query   → Erste 2 Wörter der Query
                               └── 0 Treffer? → fallthrough zu 8
8. Pixabay                   → wenn PIXABAY_API_KEY gesetzt
                               └── Fail? → finale RuntimeError (kein Bild möglich)
```

**Code-Pattern** (in `get_slide_image()`):
```python
if slide.get("ai_render"):
    try:
        return fetch_ai_image(prompt, idx)
    except Exception as e:
        print(f"  [{idx}] AI render failed ({e}), fallback Pexels")
return fetch_pexels_image(...)  # Pexels selber hat eingebaute Fallbacks
```

**KRITISCH**: jeder API-Call MUSS in try-except. Bei Exception → print Warning + fallthrough zur nächsten Stufe. KEIN `raise` wenn nur eine Quelle nicht antwortet.

### 28.2 Slide-Plan-Routing (in `slide_planner.py` → `plan_slides()`)

```
1. Gemini Flash (kostenlos)
   ├── 200 OK? → fertig
   ├── 503 high demand? → 3 Retries mit exponential backoff (5s, 10s, 20s)
   ├── Nach 3 Retries weiter Fail? → fallthrough zu Anthropic
   └── 429 rate limit? → ebenfalls Retry + fallthrough
2. Anthropic Claude Haiku (falls ANTHROPIC_API_KEY gesetzt)
   ├── 200 OK? → fertig
   └── Fail? → finale Exception (Pipeline kann nicht ohne Slide-Plan)
```

**WICHTIG**: Fallback zu Anthropic nur wenn `ANTHROPIC_API_KEY` in `.env`. Sonst klare Error-Message dass User den Key setzen soll ODER Gemini später nochmal versuchen.

### 28.3 Cloudinary-Upload-Routing

Cloudinary hat keinen Fallback (ohne ihn kann nichts gepostet werden). Bei Fehlern:
```
1. Cloudinary upload
   ├── 200 OK? → fertig
   ├── 401/403 (auth fail)? → klare Error: "API-Key Permissions prüfen, Master-Admin nötig"
   ├── Network error? → 3 Retries
   └── Nach Retries fail? → Pipeline mit klarer Error-Message abbrechen
```

**Future enhancement**: Imgur als Backup-Image-Host wenn Cloudinary down (~30 Min Code-Aufwand). Aktuell nicht implementiert.

### 28.4 Instagram-Posting-Routing

```
1. Validate Token (IG_USER_ACCESS_TOKEN existiert + beginnt mit "IGAA")
   └── Fehlt/falsch? → "no_meta_setup" returnen, Posting skippen
2. Container pro Bild erstellen
   ├── 200 OK? → next image
   ├── 400 invalid image? → log error, skip diesen Slide
   └── 401 invalid token? → finale "error: token expired" → manueller Token-Refresh nötig
3. Carousel-Container
   └── Wie oben
4. Wait until status = FINISHED (poll alle 2s, max 60s)
   ├── FINISHED? → Publish
   ├── ERROR? → log + return "error: container processing failed"
   └── Timeout? → return "error: container timeout"
5. Publish
   ├── 200 OK? → return "posted: <id>"
   └── Fail? → return "error: <details>"
```

**Pipeline läuft weiter** auch wenn Posting fehlschlägt — Slides + Caption sind in `output/` gespeichert. User kann manuell posten.

### 28.5 Topic-Refresh-Routing

```
1. Count active topics in topics.txt
   └── > 10? → kein Refresh nötig, return 0
2. Active <= 10 → Gemini call für 50 neue Topics
   ├── 200 OK? → append + return Anzahl
   └── Fail? → log warning, KEIN abort der Pipeline (Pipeline läuft weiter mit existierenden Topics)
```

### 28.6 GENERELLE FAILURE-PHILOSOPHIE

**Reihenfolge der Resilienz** (vom wichtigsten Service zum unwichtigsten):

| Service | Was passiert wenn down |
|---------|------------------------|
| **Cloudinary** | Pipeline ABBRUCH (kann nichts hosten) — kritisch |
| **Instagram API** | Pipeline läuft durch, Slides liegen in `output/`, kein Live-Post |
| **Gemini** | Fallback Anthropic Haiku → wenn auch down: ABBRUCH |
| **Together AI** | Fallback Pexels für AI-Slides — Pipeline läuft weiter |
| **Google CSE** | Fallback Pexels — Pipeline läuft weiter |
| **Pexels** | Fallback Pixabay — Pipeline läuft weiter |
| **Pixabay** | Letzter Image-Fallback — wenn auch down: ABBRUCH |

**Maxim**: **Lieber posten mit suboptimalem Bild als gar nicht posten.** Bilder können später ersetzt werden, ein verpasster Tag im Auto-Posting ruiniert den Algo.

### 28.7 Code-Pattern für jeden API-Call (Template)

```python
def fetch_with_fallback(query, idx):
    """Beispiel-Pattern für API-Call mit Fallback."""
    api_key = os.environ.get("PRIMARY_KEY", "").strip()
    if not api_key:
        # Statt raise → fallthrough zur Backup-Funktion
        print(f"  [{idx}] Primary key not set, using fallback")
        return fetch_backup(query, idx)
    
    for attempt in range(3):
        try:
            r = requests.get(URL, params={...}, timeout=30)
            if r.status_code == 200:
                return process(r.json())
            elif r.status_code in (503, 429):
                time.sleep(5 * (2 ** attempt))
                continue
            else:
                # Fataler Fehler → Fallback nutzen statt abbrechen
                break
        except requests.exceptions.RequestException as e:
            time.sleep(5 * (2 ** attempt))
            continue
    
    # Nach allen Retries → Fallback
    print(f"  [{idx}] Primary failed after retries, using fallback")
    return fetch_backup(query, idx)


def fetch_backup(query, idx):
    """Backup-Implementierung (z.B. Pexels statt Together AI)."""
    try:
        return fetch_alternative_api(query, idx)
    except Exception as e:
        # Wenn auch Backup fail → letzte Ausnahme erlauben
        raise RuntimeError(f"Both primary and backup failed: {e}")
```

### 28.8 Was der neue Claude TUN MUSS bei API-Fehlern:

1. **NIEMALS** `raise` als ersten Reflex bei API-Fehler. Erst Fallback versuchen.
2. **IMMER** `try/except` um externe API-Calls.
3. **IMMER** Retry-Logik mit exponential backoff für 5xx Status Codes.
4. **IMMER** im Log-Output deutlich machen welche Quelle gerade genutzt wird (`print(f"  [{idx}] Pexels search ...")`).
5. **NIE** alle Fallbacks mit `raise` beenden ohne final-error message die dem User sagt was zu tun ist.
6. **TIMEOUT immer setzen** (`timeout=30` oder höher) — kein Endless-Loop.

---

---

## 29. TEXT-HIERARCHIE: H1 / H2 / Description / CTA — Wann was nutzen

**4 Text-Ebenen pro Slide. Jede hat eine Funktion. Niemals mischen.**

### 29.1 Die 4 Ebenen

| Ebene | Was | Größe | Wann nutzen | Pflicht? |
|-------|-----|-------|-------------|----------|
| **H1 (headline_parts)** | Hauptaussage, Hook | 17-39px (auto) | IMMER auf jedem Slide | ✅ Pflicht |
| **H2 (subhead_parts)** | Erklärung des Hooks, ~60% der H1-Größe | ~14-23px | Wenn Hook erweitert werden soll | ⚪ Optional |
| **Description (description_parts)** | Dritte Ebene, kleinste | 15px (fix) | Nur Outro-Slide oder spezielle Slides | ⚪ Selten |
| **CTA (follow_cta automatisch)** | Engagement-Hinweis | 8px (klein) ODER 22px (Outro big) | Auf allen Slides außer letzter | Auto |

### 29.2 H1 — die wichtigste Ebene

**Funktion**: Stoppt den Scroll. 3-15 Wörter. UPPERCASE. Bold (Oswald 700).

**Style-Mix Regel**: Verbindungswörter dünn, Keywords fett, Topic-Hauptbegriffe in cyan.

```python
# BEISPIEL — HERO SLIDE H1:
"headline_parts": [
    ("FASTING ", "regular"),       # dünn (Verbindungswort + Action)
    ("72 HOURS", "primary"),        # cyan bold (Topic-Hauptbegriff = Zahl)
],
# Output: "FASTING 72 HOURS" — "FASTING" dünn, "72 HOURS" cyan-bold
```

```python
# BEISPIEL — CONTENT SLIDE H1 (mehr Wörter):
"headline_parts": [
    ("AT HOUR 12, ", "regular"),       # dünn (Zeitangabe-Connector)
    ("KETOSIS", "primary"),              # cyan (Schlüsselbegriff)
    (" BEGINS — YOUR BODY ", "regular"), # dünn
    ("EATS ITS OWN FAT", "bold"),        # bold weiß (Kern-Aussage)
],
# Output: "AT HOUR 12, KETOSIS BEGINS — YOUR BODY EATS ITS OWN FAT"
# Visuell: KETOSIS cyan, EATS ITS OWN FAT bold weiß, Rest dünn weiß
```

### 29.3 H2 — die Erklärungs-Ebene

**Funktion**: Erläutert/expandiert die H1. ~60% der H1-Größe. Auch UPPERCASE und Oswald aber 600 weight.

```python
# BEISPIEL — Hero Slide H2 (unter H1 "72 HOURS WITHOUT FOOD"):
"subhead_parts": [
    ("WHAT IT DOES TO YOUR BODY WILL ", "white"),  # bold weiß
    ("SHOCK", "primary"),                            # cyan
    (" YOU", "white"),                               # bold weiß
],
# Output: "WHAT IT DOES TO YOUR BODY WILL SHOCK YOU"
```

**Wann H2 weglassen**:
- Bei sehr kurzen H1 die alleine stark genug sind ("FASTING 72 HOURS" + ohne H2)
- Wenn das Bild die Erklärung trägt
- Wenn slide-Inhalt komplex ist und H2 zu viel zusätzliche Info wäre

**Wann H2 nutzen**:
- Hero-Slide (Hook + Promise)
- Wenn H1 zu kurz ist um den Punkt zu machen
- Wenn der User mehr Kontext braucht bevor er swipt

### 29.4 Description — die Detail-Ebene (selten)

**Nur auf Outro-Slide** oder wenn ein Slide echt eine 3. Text-Ebene braucht.

```python
# BEISPIEL — Outro Slide Description:
"description_parts": [
    ("WHICH FACT ", "regular"),
    ("SHOCKED", "primary"),
    (" YOU MOST?<br>TELL ME IN THE ", "regular"),
    ("COMMENTS", "bold"),
    (" 👇", "primary"),
],
```

`<br>` für Zeilenumbruch erlaubt. 15px fix size, Oswald 600.

### 29.5 CTA — automatisch generiert

**Auf jedem Slide außer letzter** wird automatisch unter H1/H2 dieser CTA angefügt:
```
FOLLOW @HEALTHRECODE TO NOT MISS MORE
```
- 8px Inter 600 cyan
- Wird automatisch von `slide_html()` eingefügt wenn `is_cta=False`
- Auf der LETZTEN Outro-Slide wird stattdessen `big_follow_cta_parts` benutzt (groß, mehrere Zeilen)

### 29.6 Style-Markers im Code (Auswahl)

```python
"primary"   → cyan #00CFE8, font-weight: 700  (Brand-Akzent für 1-2 Keywords)
"bold"      → white, font-weight: 700          (Keywords / wichtige Aussagen)
"regular"   → white-92%, font-weight: 300      (Verbindungswörter, dünn)
"normal"    → white, font-weight: 400          (Standard-Text, nicht bold/nicht dünn)
"white"     → white, font-weight: 700          (Default fallback, bold)
```

### 29.7 Mix-Faustregeln (PFLICHT befolgen!)

1. **Maximum 2 cyan/primary Wörter pro Headline** — sonst Overload
2. **Verbindungswörter immer regular** ("the", "is", "and", "your", "in", "of", "on", "to", "for")
3. **Schlüsselbegriffe immer bold oder primary** ("KETOSIS", "BRAIN", "STUDY", Zahlen)
4. **Niemals 3+ aufeinanderfolgende Wörter in primary** (ergibt cyan-Wand, schwer lesbar)
5. **Default-Fall**: wenn unsicher → "white" (bold weiß) — sicher und lesbar

### 29.8 Visual-Hierarchy-Test (vor Posting)

Frag dich:
- Kann ich die **wichtigste Aussage in 1 Sekunde** erkennen? → H1 muss diesen Punkt machen
- Hilft H2 mir das zu verstehen oder ist es Lärm? → wenn Lärm: H2 weglassen
- Sticht **mindestens 1 cyan Wort** raus für visuellen Anker? → falls nein: ein Schlüsselwort als primary markieren
- Ist die Headline **kürzer als 100 Zeichen**? → falls nein: kürzer fassen, sonst auto-size schrumpft sie zu klein

---

---

## 30. HTML-Template & Playwright-Export (komplett)

Das EXAKTE HTML/CSS Setup damit der neue Claude bei einer neuen Brand 1:1 reproduzieren kann.

### 30.1 HTML-Grundstruktur einer einzelnen Slide

```html
<div class="slide" id="slide-{idx}">
  <!-- 1. Foto-Hintergrund (Pexels/AI/Solid-Color) -->
  <img class="bg-photo" src="data:image/jpeg;base64,..." />
  
  <!-- 2. Dunkler Gradient von unten nach oben -->
  <div class="bg-gradient"></div>
  
  <!-- 3. Vital-Signs Strip oben rechts -->
  <div class="vitals-strip">
    <span class="pulse-dot"></span>
    <span class="label">HR</span> <span class="value">72</span>
    <span class="label">·</span>
    <span class="label">SpO₂</span> <span class="value">98%</span>
    <span class="label">·</span>
    <span class="label">T</span> <span class="value">36.7°C</span>
  </div>
  
  <!-- 4. Right-Edge Pfeil-Pill (außer letzter Slide) -->
  <div class="swipe-arrow-right">
    <svg viewBox="0 0 24 24"><path d="M9 6l6 6-6 6"/></svg>
  </div>
  
  <!-- 5. Bottom-Stack: Logo + Headlines + CTAs -->
  <div class="bottom-stack">
    <!-- 5a. Logo-Block (außer Outro) -->
    <div class="logo-block">
      <div class="logo-line left"></div>
      <span class="logo-text">HEALTH</span>
      <img class="logo-center-icon" src="data:image/png;base64,..." />
      <span class="logo-text">RECODE</span>
      <div class="logo-line right"></div>
    </div>
    
    <!-- 5b. H1 Headline (auto-size) -->
    <h1 class="headline" style="font-size:30px">
      <span style="color:#fff;font-weight:300">AT HOUR 12, </span>
      <span style="color:#00CFE8;font-weight:700">KETOSIS</span>
      <span style="color:#fff;font-weight:300"> BEGINS</span>
    </h1>
    
    <!-- 5c. H2 Subhead (optional) -->
    <h2 class="subhead" style="font-size:18px">...</h2>
    
    <!-- 5d. Description (optional, meist Outro) -->
    <div class="description">...</div>
    
    <!-- 5e. Follow-CTA (auf jedem Slide außer Outro) -->
    <div class="follow-cta">FOLLOW @HEALTHRECODE TO NOT MISS MORE</div>
    
    <!-- 5f. Engagement-Banner (mid-carousel, optional) -->
    <div class="engagement-banner">💾 SAVE THIS POST — IT'S ABOUT TO GET INTERESTING</div>
  </div>
  
  <!-- 6. Profile-Card Embed (NUR Outro-Slide) -->
  <div class="profile-card-embed">
    <img src="data:image/jpeg;base64,..." />
  </div>
  
  <!-- 7. Swipe-CTA unten (außer Outro) -->
  <div class="swipe-cta">
    <span>SWIPE FOR MORE</span>
    <svg class="swipe-arrow-mini" viewBox="0 0 24 24"><path d="M9 6l6 6-6 6"/></svg>
  </div>
  
  <!-- 8. Share-CTA (NUR Outro-Slide) -->
  <div class="share-cta">Share this with your Friends →</div>
</div>
```

### 30.2 Carousel-Wrapper (mehrere Slides nebeneinander)

```html
<!DOCTYPE html>
<html>
<head>
  <link href="https://fonts.googleapis.com/css2?family=Anton&family=Inter:wght@300;400;600;700;800&family=Oswald:wght@300;400;600;700&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
  <style>/* ... siehe Sektion 30.3 ... */</style>
</head>
<body>
  <div class="ig-frame">
    <div class="carousel-viewport">
      <div class="carousel-track" id="track">
        <!-- Mehrere .slide divs hier -->
      </div>
    </div>
  </div>
</body>
</html>
```

**WICHTIG**:
- `.ig-frame` MUSS exakt **420px breit** sein
- `.carousel-viewport` MUSS **420×525** mit `overflow:hidden`
- `.carousel-track` ist horizontal flex: wenn 8 Slides → 8 × 420 = 3360px breit, wird per JS verschoben

### 30.3 Vollständiges CSS (kopierbar)

Alle Styles in `<style>`-Tag im `<head>`. Hier die kritischen Klassen mit exakten Werten:

```css
* { box-sizing: border-box; margin: 0; padding: 0; }
body { background: #1a1a1a; font-family: 'Inter', sans-serif; color: white; padding: 20px; display: flex; flex-wrap: wrap; gap: 20px; justify-content: center; }
.ig-frame { width: 420px; overflow: hidden; }
.carousel-viewport { width: 420px; height: 525px; position: relative; }
.carousel-track { display: flex; transition: none; transform: translateX(0); }

.slide { flex: 0 0 420px; width: 420px; height: 525px; position: relative; overflow: hidden; background: #0A0A0F; color: white; font-family: 'Inter', sans-serif; }

.bg-photo { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; filter: saturate(1.05) contrast(1.05); }

.bg-gradient { position: absolute; inset: 0; background: linear-gradient(180deg,
    rgba(10,10,15,0.0) 0%, rgba(10,10,15,0.0) 25%,
    rgba(10,10,15,0.35) 40%, rgba(10,10,15,0.75) 55%,
    rgba(10,10,15,0.92) 70%, rgba(10,10,15,0.98) 85%,
    rgba(10,10,15,1.0) 100%); }

.vitals-strip { position: absolute; top: 14px; right: 14px; z-index: 6; display: flex; align-items: center; gap: 6px; padding: 3px 8px; background: rgba(0,0,0,0.18); backdrop-filter: blur(4px); border-radius: 3px; border: 1px solid rgba(255,255,255,0.05); font-family: 'JetBrains Mono', 'Courier New', monospace; font-size: 7.5px; color: rgba(255,255,255,0.55); letter-spacing: 0.3px; }
.vitals-strip .label { color: rgba(255,255,255,0.35); }
.vitals-strip .value { color: rgba(0,207,232,0.75); font-weight: 700; }
.vitals-strip .pulse-dot { width: 4px; height: 4px; border-radius: 50%; background: rgba(0,207,232,0.75); margin-right: 1px; box-shadow: 0 0 4px rgba(0,207,232,0.5); }

.bottom-stack { position: absolute; bottom: 70px; top: 55%; left: 0; right: 0; padding: 0 24px; display: flex; flex-direction: column; align-items: center; justify-content: flex-end; gap: 6px; z-index: 5; text-align: center; overflow: visible; }
.bottom-stack.top-position { top: 40px; bottom: auto; gap: 10px; }

.logo-block { display: flex; align-items: center; justify-content: center; gap: 5px; }
.logo-line { flex: 0 0 70px; height: 1px; background: linear-gradient(to right, transparent, #00CFE8, #00CFE8); }
.logo-line.right { background: linear-gradient(to left, transparent, #00CFE8, #00CFE8); }
.logo-text { font-family: 'Inter', sans-serif; font-weight: 600; font-size: 11px; letter-spacing: 2.5px; color: white; }
.logo-center-icon { width: 16px; height: 16px; object-fit: contain; margin: 0; filter: drop-shadow(0 1px 2px rgba(0,0,0,0.3)); }

.headline { font-family: 'Oswald', 'Anton', sans-serif; font-weight: 700; text-transform: uppercase; line-height: 1.0; letter-spacing: 0.3px; color: white; margin-bottom: 2px; text-shadow: 0 3px 12px rgba(0,0,0,0.55), 0 1px 3px rgba(0,0,0,0.40); }
.subhead { font-family: 'Oswald', 'Anton', sans-serif; font-weight: 600; text-transform: uppercase; line-height: 1.05; letter-spacing: 0.3px; color: rgba(255,255,255,0.92); margin-bottom: 0; margin-top: 2px; text-shadow: 0 2px 10px rgba(0,0,0,0.50), 0 1px 3px rgba(0,0,0,0.35); }

.tag { display: none; }

.follow-cta { font-family: 'Inter', sans-serif; font-size: 8px; font-weight: 600; letter-spacing: 1px; color: #00CFE8; text-transform: uppercase; margin-top: 2px; }

.big-follow-cta { font-family: 'Oswald', sans-serif; font-weight: 400; font-size: 22px; line-height: 1.2; letter-spacing: 0.4px; text-transform: uppercase; margin-top: 18px; text-shadow: 0 3px 12px rgba(0,0,0,0.55), 0 1px 3px rgba(0,0,0,0.40); }

.description { font-family: 'Oswald', sans-serif; font-weight: 600; font-size: 15px; line-height: 1.25; letter-spacing: 0.2px; text-transform: uppercase; margin-top: 14px; text-shadow: 0 2px 8px rgba(0,0,0,0.45), 0 1px 2px rgba(0,0,0,0.30); }

.engagement-banner { margin-top: 14px; padding: 10px 14px; background: #00CFE8; color: black; font-family: 'Inter', sans-serif; font-size: 10.5px; font-weight: 700; letter-spacing: 0.5px; border-radius: 4px; text-align: center; text-transform: uppercase; }

.swipe-cta { position: absolute; bottom: 30px; left: 0; right: 0; z-index: 6; display: flex; align-items: center; justify-content: center; gap: 6px; }
.swipe-cta span { font-family: 'Inter', sans-serif; font-size: 10px; letter-spacing: 3px; color: rgba(255,255,255,0.85); font-weight: 600; }
.swipe-arrow-mini { width: 11px; height: 11px; stroke: rgba(255,255,255,0.85); }

.swipe-arrow-right { position: absolute; right: 12px; top: 50%; transform: translateY(-50%); width: 28px; height: 28px; border-radius: 50%; background: rgba(255,255,255,0.18); backdrop-filter: blur(4px); display: flex; align-items: center; justify-content: center; z-index: 7; }
.swipe-arrow-right svg { width: 14px; height: 14px; stroke: white; }

.profile-card-embed { position: absolute; bottom: 50px; left: 24px; right: 24px; z-index: 4; border-radius: 8px; overflow: hidden; border: 1.5px solid rgba(0,207,232,0.55); box-shadow: 0 4px 16px rgba(0,0,0,0.5); }
.profile-card-embed img { width: 100%; display: block; object-fit: cover; }

.share-cta { position: absolute; bottom: 32px; left: 0; right: 0; z-index: 5; text-align: center; font-family: 'Oswald', sans-serif; font-weight: 500; font-size: 13px; color: rgba(255,255,255,0.95); letter-spacing: 0.6px; text-shadow: 0 2px 6px rgba(0,0,0,0.30); }
```

### 30.4 Playwright-Export-Skript (HTML → 1080×1350 PNG)

```python
async def export_slides(html_path: Path, total_slides: int, only: int = None):
    from playwright.async_api import async_playwright
    
    VIEW_W, VIEW_H = 420, 525
    SCALE = 1080 / 420  # = 2.5714 — KRITISCH: keine Viewport-Resize!
    
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(
            viewport={"width": VIEW_W, "height": VIEW_H},
            device_scale_factor=SCALE,  # ← magic, scaled output ohne Layout-Reflow
        )
        
        await page.set_content(html_path.read_text(), wait_until="networkidle")
        await page.wait_for_timeout(3500)  # Fonts laden!
        
        # IG-Frame-Chrome ausblenden (falls vorhanden)
        await page.evaluate("""() => {
            document.body.style.cssText = 'padding:0;margin:0;display:block;overflow:hidden;background:#0A0A0F;';
            const f = document.querySelector('.ig-frame');
            f.style.cssText = 'width:420px;height:525px;overflow:hidden;margin:0;';
            const v = document.querySelector('.carousel-viewport');
            v.style.cssText = 'width:420px;height:525px;overflow:hidden;position:relative;';
        }""")
        await page.wait_for_timeout(500)
        
        # Pro Slide: track per JS verschieben + Screenshot
        for i in range(total_slides):
            await page.evaluate("""(idx) => {
                const t = document.getElementById('track');
                t.style.transition = 'none';
                t.style.transform = 'translateX(' + (-idx * 420) + 'px)';
            }""", i)
            await page.wait_for_timeout(400)
            slide_num = only if only else (i + 1)
            await page.screenshot(
                path=f"output/slide_{slide_num}.png",
                clip={"x": 0, "y": 0, "width": VIEW_W, "height": VIEW_H},
            )
        
        await browser.close()
```

**Pitfalls beim Export**:
1. ❌ NIEMALS `viewport` auf 1080×1350 setzen — Layout reflowt, Schriften zu klein.
2. ✅ IMMER `device_scale_factor=2.5714` — DPI hochgesetzt, Layout bleibt 420×525.
3. ✅ IMMER 3000-3500ms warten nach `set_content` damit Google Fonts laden.
4. ❌ NIEMALS Bilder als externe URLs im HTML — IMMER base64-data-URIs einbetten (Playwright kann sonst Bilder nicht laden).
5. ✅ HTML mit Python `Path.write_text()` erzeugen — niemals via Shell mit `echo` (`$` und `{}` werden interpoliert).

### 30.5 Build-HTML-Funktion (Python-Wrapper)

```python
def build_html(slides_with_images):
    total = len(slides_with_images)
    brand_logo = load_brand_logo()      # base64 vom logo.png (falls da)
    center_icon = load_center_icon()    # base64 vom healthrecodeicon.png
    
    slide_blocks = "\n".join(
        slide_html(i + 1, s, total, img, brand_logo, center_icon)
        for i, (s, img) in enumerate(slides_with_images)
    )
    
    return f"""<!DOCTYPE html>
<html>
<head>
  <link href="..google fonts..." rel="stylesheet">
  <style>{COMPLETE_CSS}</style>
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
</html>"""
```

### 30.6 Bilder als base64 einbetten (PFLICHT!)

```python
def img_to_base64(path: Path) -> str:
    data = path.read_bytes()
    mime = "jpeg" if path.suffix.lower() in (".jpg", ".jpeg") else "png"
    return f"data:image/{mime};base64,{base64.b64encode(data).decode()}"
```

**Warum**: Playwright `set_content()` lädt externe URLs unzuverlässig. Base64-Embed garantiert dass Bild im HTML ist beim Render.

### 30.7 Render-Pipeline-Steps (komplette Übersicht)

```
1. fetch_*_image()          → lokale Datei (jpg/png)
2. img_to_base64()           → embed in HTML
3. slide_html(...)           → erzeugt 1 Slide-Div mit allen Elements
4. build_html(slides)        → fügt alle Slide-Divs zu Carousel zusammen + CSS + Fonts
5. .write_text(html_path)    → speichert als output/carousel.html
6. export_slides(html, n)    → Playwright öffnet Headless Chromium, screenshotted N Slides
7. Output: output/slide_1.png ... slide_N.png  (1080×1350)
```

---

---

## 31. 🐛 KOMPLETTE FEHLER-BIBEL — Alle Fehler die wir hatten + Fix

**Diese Liste ist GOLD WERT** — jeder Eintrag ist ein echter Fehler aus dem Setup-Prozess. Der neue Claude liest dies bevor er irgendwas macht damit er die Stunden Frust nicht erneut durchlebt.

### 31.1 Setup-Fehler (Service-Konfiguration)

#### CLOUDINARY
| Fehler | Ursache | Fix |
|--------|---------|-----|
| `Invalid cloud_name "medical"` | User hat **API-Key-Label** statt Cloud-Name verwendet | Cloud-Name ist auto-generiert (`dxxx...`-Format) — im Dashboard top-section, NICHT im "API Keys"-Tab |
| `Request forbidden — actions=["create"]` | API-Key ohne Master-Admin-Permission | Cloudinary Console → API Keys → Edit Key → Roles → **"Master Admin"** wählen |
| Upload nur 7 statt 8 Slides | `range(1, 8)` hardcoded in cloud_pipeline.py | Glob-Pattern `output.glob("slide_*.png")` mit dynamischer ID-Extraction |

#### GOOGLE CUSTOM SEARCH (für echte Personen)
| Fehler | Ursache | Fix |
|--------|---------|-----|
| `blocked-by-allowlist` in Sandbox | Domain nicht im Sandbox-Allowlist | Skript MUSS auf User-PC oder GitHub Actions laufen, nicht in Cowork-Sandbox |
| `403 — Custom Search API not enabled` | API nicht aktiviert in Cloud-Projekt | https://console.cloud.google.com/apis/library/customsearch.googleapis.com → Aktivieren |
| `403 — API method blocked` | API-Key hatte Restriction nur auf Gemini | Neue API-Key OHNE Restrictions ODER Custom Search API zur Allowlist hinzufügen |
| `403 — Project does not have access` | Billing-Konto fehlt im Cloud-Projekt | Cloud-Projekt mit aktivem Billing-Account verlinken (Trial $300 reicht ewig) |
| Toggle "Search entire web" fehlt | Google hat das deprecated | Liste manuell mit Sites füllen (`wikipedia.org`, `flickr.com`, `pinterest.com`) ODER Quelle skippen |

#### INSTAGRAM API
| Fehler | Ursache | Fix |
|--------|---------|-----|
| `Entwickler-Rolle nicht ausreichend` | @handle nicht als Instagram-Tester registriert | App-Rollen → "+ Person..." → Rolle "Instagram-Tester" → Username eingeben |
| Permission `instagram_content_publish` lässt sich nicht aktivieren | User hat die "business"-Variante versucht (`instagram_business_content_publish`), die braucht Tech-Provider-Status | **Die ältere `instagram_content_publish`** (ohne "business" prefix) nehmen — funktioniert in Dev-Mode |
| Tester-Status bleibt "Ausstehend" | Einladung nicht im IG-Account angenommen | Auf instagram.com **als @handle** einloggen → Einstellungen → Apps und Websites → Tester-Einladungen → **Annehmen** |
| Token beginnt mit `EAA...` statt `IGAA...` | User hat Token via Graph API Explorer geholt (alte API) | Token via App-Dashboard → "API-Einrichtung mit Instagram-Login" → "2. Zugriffstokens generieren" holen |
| `Instagram Posting: no_meta_setup` | post_to_instagram() prüft alte Env-Vars (`IG_BUSINESS_ACCOUNT_ID`, `META_LONG_LIVED_TOKEN`) | Nutze NEUE Env-Vars: `IG_USER_ID` + `IG_USER_ACCESS_TOKEN` mit Endpoint `graph.instagram.com/v22.0` |

#### GITHUB
| Fehler | Ursache | Fix |
|--------|---------|-----|
| `Repository not found` beim Push | PAT (Personal Access Token) ohne Permissions ODER falsche URL | PAT mit `repo` Scope erstellen, URL prüfen: `https://USER:TOKEN@github.com/USER/REPO.git` |
| `refusing to allow PAT — workflow scope` | PAT hat nur `repo` Scope, nicht `workflow` | NEUEN PAT mit BEIDEN Scopes (`repo` + `workflow`) erstellen |
| `fatal: unable to auto-detect email` | Git-Config nicht gesetzt | `git config --global user.email "..."` und `user.name "..."` |
| "Re-run jobs" nutzt ALTEN Code | GitHub Actions Re-Run nimmt Original-Commit, nicht latest | NEUEN Run via "Run workflow" Button (workflow_dispatch) starten — nimmt latest commit |

### 31.2 Code-Bugs (Pipeline-Crashes)

| Fehler | Ursache | Fix |
|--------|---------|-----|
| `TypeError: 'NoneType' object is not subscriptable` | OUTRO_COMMENT war None nach Refactor, wurde aber noch in Liste appended | `outros = [o for o in (...) if o]` — None filtern. Plus defensive `if slide is None: continue` in iteration |
| `KeyError: 'pexels_query'` in `_normalize_slide()` | Hardcoded required field, Gemini gab manchmal nur `ai_render` oder `google_query` | Alle Felder als `s.get(field, default)` — niemals `s["field"]` direkt |
| `Together AI fail: 422 image may contain NSFW content` | False-positive Filter bei "healthy body cells" Prompt | try/except um `fetch_ai_image()` → Fallback `fetch_pexels_image()` |
| `Gemini API fail: 503 high demand` | Google API überlastet | 3 Retries mit exponential backoff (5s/10s/20s) → fallback Anthropic Haiku falls Key gesetzt |
| Cloudinary Upload nur 7 Bilder bei 8 Slides | `range(1, 8)` hardcoded | `output.glob("slide_*.png")` dynamisch zählen |

### 31.3 Visual-Bugs (Layout-Probleme)

| Problem | Ursache | Fix |
|---------|---------|-----|
| Text unleserlich auf hellem Foto-Hintergrund | Background-Gradient zu schwach (`0.65` opacity max) | Stärkerer Gradient: `0.35→0.75→0.92→0.98→1.0` ab 40% von oben |
| Text-Shadow zu subtil | `0.10` opacity ist fast unsichtbar | Stärker: `text-shadow: 0 3px 12px rgba(0,0,0,0.55), 0 1px 3px rgba(0,0,0,0.40)` |
| H1 zu groß | Auto-Size Default zu groß | `calc_headline_size()` überall um 15% verkleinern (39→34→30→26 statt 46→40→35→30) |
| Bottom-Stack nimmt 70% des Slides | Kein max-height enforced | `top: 55%` als upper-bound — zwingt Stack in untere 45% |
| Logo zu weit weg von Headline | `gap: 14px` im flex container | `gap: 6px` — tighter |
| Logo top-left nervig/unnötig | Icon doppelt mit Logo-Block in Mitte | `brand_logo_html = ""` — komplett ausgeblendet |
| Vital-Strip zu prominent | Transparenz nur 45% schwarz, Text 85% weiß | Reduzieren: 18% schwarz, Text 55% weiß, Werte 75% cyan |
| "@YOUR_HANDLE" steht auf Slide | `BRAND_HANDLE` nicht aktualisiert | Pro neue Brand: `BRAND_HANDLE = "@<handle>"` ganz oben in generate_carousel.py setzen |
| Dots auf Slide doppelt mit Instagram-Dots | IG fügt eigene Dots hinzu beim Posten | `dots_html = ""` — keine Dots in HTML einbauen |

### 31.4 Visual-Content-Bugs (schlechte Bilder)

**Häufigster Fehler**: Pexels liefert random unpassende Stock-Photos weil Query zu abstrakt.

| Schlechte Query | Was zurückkam | Bessere Query |
|-----------------|---------------|---------------|
| `"metabolism concept energy conversion"` | random food/abstract | `"young woman holding stomach hungry"` |
| `"energy depletion"` | random landscapes | `"empty water glass on wooden table"` |
| `"vitality concept"` | abstract sunset | `"man drinking water at sunrise"` |
| `"person meditating calm serene"` | generic sunset profile | `"3D anatomical render human heart"` (für Hero — AI render) |
| `"healthy gut food metabolism"` | random foods | `"3D render human stomach anatomy"` (AI render) |
| `"brain energy focus"` | generic abstract | `"3D anatomical render brain neurons firing"` (AI render) |

**FIX im slide_planner.py System-Prompt** (Sektion 17.5):
- Verboten: abstrakte Wörter wie "energy", "metabolism", "concept", "vitality", "depletion"
- Erlaubt: konkrete Szenen "young woman holding stomach in pain", "scientist examining microscope"
- Anatomie/Prozess → IMMER AI-Render mit detailliertem 3D-Prompt, NICHT Pexels

### 31.5 Token & Auth-Bugs

| Fehler | Ursache | Fix |
|--------|---------|-----|
| Replicate `402 Insufficient credit` | $1 Trial-Credit gibt's nicht mehr seit 2025 | Konto aufladen ($5 minimum) ODER auf Together AI/Pollinations switchen |
| Together AI `402 Credit limit exceeded` | Free-Tier Modelle (`FLUX.1-schnell-Free`) blockiert | $5 Aufladung — mit FLUX Schnell ~1700 Bilder = 240 Carousels |
| Pollinations `Bad quality` | Free-Tier ohne Premium-Modelle | Skippen — bei medizinischem Content reicht es nicht |
| Gemini `429 quota exceeded` für image gen | Free-Tier hat **kein** Bild-Generation Credit | Bilder via Together AI/Replicate, nicht Gemini |

### 31.6 Cross-Posting / Distribution

| Problem | Ursache | Fix |
|---------|---------|-----|
| Posts erscheinen nicht auf Facebook | IG-FB Cross-Posting nicht aktiviert | Instagram-App → Profil → Account Center → "Synchronisierte Beiträge" → FB-Page aktivieren |
| Cross-Post will auf privates FB-Profil statt Page | Account Center verbindet Personal-Profile | Page-Verknüpfung in Meta Business Suite separat konfigurieren |
| Carousels haben keine Musik | IG Music-API existiert nicht für Carousel-Posts | Manuell in IG-App: Post → Bearbeiten → "Musik hinzufügen" (10 Sek/Post) |

### 31.7 Konfiguration / Brand-Setup

| Fehler | Ursache | Fix |
|--------|---------|-----|
| Logo-Block zeigt "MEDICAL INSTA" statt "HEALTH RECODE" | Default-Werte nicht überschrieben | `BRAND_NAME`, `BRAND_DISPLAY`, `BRAND_WORD_LEFT`, `BRAND_WORD_RIGHT` in generate_carousel.py top-section setzen |
| Profile-Card im Outro fehlt/falsch | `embed_profile_card` zeigt auf nicht-existente Datei | Profile-Screenshot als `<brand>follow.jpg` speichern + Pfad updaten |
| Center-Icon zu groß/klein | Standard 16×16px passt nicht zu allen Logos | `.logo-center-icon { width: Xpx; }` anpassen, Icon-PNG mit transparentem Hintergrund |

### 31.8 Was funktioniert NICHT (deprecated/blocked):

- ❌ **Replicate $1 Trial** — gibt es nicht mehr automatisch
- ❌ **Together AI Free-Tier-Modelle** — komplett deaktiviert seit 2025
- ❌ **Unsplash für Auto-Posting** — ToS verbietet "non-automated use"
- ❌ **Google CSE "Search entire web"** Toggle — deprecated
- ❌ **Instagram Music API für Carousels** — existiert nicht, nur manuell in App
- ❌ **GitHub Actions "Re-run jobs"** für Code-Updates — nimmt alten Commit
- ❌ **Pollinations.ai für medizinischen Content** — Qualität unzureichend
- ❌ **`graph.facebook.com/v21.0` für Instagram-Posts** — alte API, fragil

### 31.9 GOLDENE REGELN (basierend auf allen Fehlern)

1. **Bei API-Setup IMMER alle 4 Schritte prüfen**: Account angemeldet, API in Cloud aktiviert, API-Key mit richtigen Permissions, Billing falls nötig.
2. **NIEMALS Test-Run via "Re-run jobs"** — IMMER frischen "Run workflow"-Trigger.
3. **NIEMALS Instagram-Token via Graph API Explorer** für die neue Instagram Login API — IMMER via App-Dashboard "API-Einrichtung mit Instagram-Login".
4. **IMMER `git push` nach Code-Änderung** vor neuem Workflow-Run, sonst läuft alter Code.
5. **IMMER 5 Min warten nach Cloud-Permission-Änderung** (Google/Meta brauchen Propagationszeit).
6. **Pexels-Queries IMMER konkret und visuell**, niemals abstrakte Konzepte.
7. **Anatomie/Prozesse IMMER via AI-Render**, NIEMALS via Pexels.
8. **Image-Cache vor Test-Lauf manchmal löschen** (`rm -rf image_cache/*`) — sonst zeigt cached oldes Bild trotz neuer Query.
9. **`.env` NIEMALS in Repo** — `.gitignore` muss korrekt sein, sonst Keys public.
10. **Nach allen Tests vor Live-Post IMMER Dry-Run = true** — visual checken, dann erst echtes Posting.

---

---

## 32. 🎣 HOOK-REGELN (KRITISCH — bestimmt ob Post viral geht oder floppt!)

**Ein schwacher Hook = Post scrollt vorbei. Pflichtlektüre für jeden neuen Claude.**

### 32.1 Was IST ein Hook?

Der Hook ist die **Headline + Subhead Kombination auf Slide 1**. Er muss in **<2 Sekunden** den Daumen stoppen und Neugier auslösen, **bevor** der User weiterscrollt.

### 32.2 Anatomie eines starken Hooks

Jeder Hook braucht 3 von diesen 5 Zutaten:

1. **Spezifität** (Zahlen, Namen, konkrete Begriffe)
   - ❌ "EARLY MORNING ROUTINE"
   - ✅ "WHY 4:17 AM IS THE EXACT WAKE-UP TIME ELITE PERFORMERS USE"

2. **Curiosity Gap** (Information promise, die nur durch Swipe befriedigt wird)
   - ❌ "MORNING TIPS"
   - ✅ "THE 1 THING ELITE PERFORMERS DO BEFORE 5 AM THAT 99% OF PEOPLE SKIP"

3. **Stakes/Konsequenz** (was passiert wenn man's NICHT macht)
   - ❌ "BENEFITS OF EARLY RISING"
   - ✅ "WAKING UP AFTER 7 AM CRASHES YOUR CORTISOL — HERE'S THE FIX"

4. **Authority/Studie/Quelle** (Glaubwürdigkeit)
   - ❌ "FASTING IS GOOD"
   - ✅ "HARVARD STUDY: 72-HOUR FAST TRIGGERS A NOBEL-PRIZE PROCESS"

5. **Schock/Überraschung** (counterintuitive Aussage)
   - ❌ "EATING HEALTHY"
   - ✅ "STUDY SHOWS BUTTER MAY ACTUALLY BE HEALTHIER THAN OLIVE OIL"

### 32.3 Bad Hook Beispiele (REAL aus diesem Projekt — vermeiden!)

| ❌ Schlechter Hook | Warum es nicht funktioniert |
|----|----|
| "THE 4 AM ADVANTAGE" | 3 Wörter, keine Spezifik, generisch — niemand weiß was drin ist |
| "MORNING ROUTINE TIPS" | Klingt wie 1 Million andere Posts |
| "FASTING IS GOOD" | Kein Gap, kein Stakes, vage |
| "BENEFITS OF MEDITATION" | Generisch, kein Hook-Element |
| "HEALTHY EATING" | Reines Topic, kein Hook |
| "WHY YOU SHOULD SLEEP MORE" | Keine Spezifik, kein Curiosity-Gap |

### 32.4 Good Hook Beispiele (verwenden!)

| ✅ Starker Hook | Was funktioniert |
|----|----|
| "WHAT 72 HOURS WITHOUT FOOD DOES TO YOUR BODY WILL SHOCK YOU" | Spezifische Zahl + Schock-Curiosity |
| "AT HOUR 24 OF FASTING, YOUR CELLS START EATING THEMSELVES" | Spezifik + Counterintuitive + Anatomie-Detail |
| "THE 4-7-8 BREATHING TECHNIQUE NAVY SEALS USE TO FALL ASLEEP IN 60 SECONDS" | Authority + Spezifik + Konkretes Outcome |
| "ELITE PERFORMERS WAKE AT 4:30 AM — BUT THE REAL SECRET IS WHAT THEY DO BEFORE 5 AM" | Curiosity-Gap + Authority + Versprechen |
| "120 WOMEN, 8 WEEKS, 1 SUPPLEMENT — RESULTS BEAT FLUOXETINE" | Pure Spezifik (Studien-Daten) |
| "YOUR MOTHER'S CELLS NEVER LEFT YOUR BODY — HERE'S WHAT THAT MEANS" | Schock-Aussage + Curiosity-Gap |

### 32.5 H1 + H2 Hook-Pattern (das was wir bauen sollen)

**Pattern: H1 = Setup (kurze provokante Aussage), H2 = Payoff Promise (was du im Carousel lernst)**

```python
# RICHTIG — Setup + Payoff Promise:
"headline_parts": [
    ("4 AM CLUB", "primary"),
    (" — REAL SECRET", "white"),
],
"subhead_parts": [
    ("THE 3-PART POWER PROTOCOL ELITE PERFORMERS USE", "white"),
    (" BEFORE THE WORLD WAKES UP", "regular"),
],
```

```python
# FALSCH — nur generischer Titel ohne Promise:
"headline_parts": [
    ("THE 4 AM ADVANTAGE", "white"),  # zu vage
],
"subhead_parts": None,  # H2 fehlt komplett — Hook stirbt
```

**REGEL**: 
- **H1 alleine ist NIE genug** außer er ist extrem provokant ("YOU'RE DYING SLOWER THAN YOU THINK")
- **H2 ist meist Pflicht** um den Hook zu zementieren ("HERE'S WHY" / "BACKED BY 5 STUDIES" / "THE PROTOCOL INSIDE")

### 32.6 Hook-Test (vor jedem Post)

Bevor ein Post live geht, frag dich:
1. Würde **ein Stranger im Feed** das in 2 Sekunden klicken?
2. Erzeugt H1+H2 zusammen einen **Curiosity-Gap** (= "ich MUSS wissen was im Carousel ist")?
3. Gibt es **mindestens 1 Spezifik** (Zahl, Name, Studie, Mechanismus)?
4. Wird **klar gemacht was der Reader bekommt** wenn er swipt?

Wenn 1 davon "nein" → Hook neu schreiben.

### 32.7 Hook-Templates (für Gemini im System-Prompt erzwingen)

Erweiter slide_planner.py System-Prompt mit:

```
HOOK MANDATE FOR HERO SLIDE (slide 1):
The H1 + H2 must form a strong hook. Required:
- H1 must contain at least ONE specific number, name, or concrete term (NEVER pure abstract concepts).
- H2 must promise WHAT the reader learns by swiping (the payoff).
- Together they must trigger curiosity-gap or shock.
- BAD examples to AVOID: "morning routine tips", "the X advantage", "benefits of Y", "why you should Z"
- GOOD pattern: "[NUMBER] + [SPECIFIC ACTION/PROCESS] + [SHOCKING/CURIOSITY OUTCOME]"

Examples of MANDATORY hook quality:
✅ H1: "72 HOURS WITHOUT FOOD" / H2: "WHAT IT DOES TO YOUR BODY WILL SHOCK YOU"
✅ H1: "ELITE PERFORMERS WAKE AT 4:17 AM" / H2: "BUT THE REAL SECRET IS THE 3-PART PROTOCOL THEY USE BEFORE 5 AM"
✅ H1: "NOBEL PRIZE 2016" / H2: "THE PROCESS YOUR CELLS START AT HOUR 24 OF FASTING"

If you can't write a strong hook in this format, REPHRASE the topic until you can.
```

### 32.8 Wichtige Don'ts

- ❌ Generic "THE [X] [Y]" Pattern ohne Substanz
- ❌ Reine Topic-Aussage ("Healthy Eating", "Better Sleep")
- ❌ Clickbait OHNE Wahrheit ("This will change your life forever") — IG erkennt das, downranked
- ❌ H1 alleine ohne H2 wenn H1 < 5 Wörter
- ❌ Fragen als Hook ("DO YOU KNOW...?") — funktioniert selten, zu kommune
- ❌ Buzzwords-Stapelung ("MAXIMIZE YOUR POTENTIAL UNLOCK YOUR POWER") — leer

### 32.9 Connection zum slide_planner.py

Der Hook-Mandate aus 32.7 MUSS in den System-Prompt von `slide_planner.py` einfließen, sonst generiert Gemini weiter Generic-Hooks. Die Stelle:

```python
SYSTEM_PROMPT = """...existing...

## HOOK MANDATE FOR HERO SLIDE (slide 1):
[Inhalt aus 32.7]
"""
```

---

## 33. 📋 LIST/TIPS SLIDE TYPE (Action-Plan-Slide ohne Bild)

Eine zusätzliche Slide-Variante für **actionable Inhalte** — keine Bilder, nur nummerierte Tipps mit dunklem Solid-Hintergrund.

### 33.1 Wann eine list-Slide einsetzen?

Bei strukturierten Aktionen — Tipps, Signale, Schritte, Don'ts, Habits.
**Trigger-Patterns:** "5 Anzeichen für ...", "7 Tipps gegen ...", "Schritte zur Behandlung ...", "Mistakes that ruin..."

**Wo platzieren?** Letzte Content-Slide (Action-Plan), oder als Mid-Carousel-Summary in 10+ Slide Carousels.

### 33.2 list-Slide JSON-Schema

```json
{
  "type": "list",
  "tag": "ACTION PLAN",
  "headline_parts": [["MASTER YOUR ", "white"], ["FIRST HOUR", "primary"]],
  "list_items": [
    {"number": "01", "title": "THE SILENT AWAKENING", "description": "Resist screens for the first 30 minutes."},
    {"number": "02", "title": "HYDRATE & MOVE", "description": "Drink water immediately. 10-15 min light movement."},
    {"number": "03", "title": "PLAN YOUR ATTACK", "description": "Review your top 3 priorities for the day."},
    {"number": "04", "title": "IMMERSION ZONE", "description": "Tackle most important task 60-90 min, distraction-free."}
  ]
}
```

KEIN `pexels_query`/`ai_render`/`google_query` nötig — Renderer setzt automatisch dunkles Solid (`BRAND_BG_DARK`).

### 33.3 Regeln

| Feld | Constraints |
|---|---|
| `number` | "01"-"06", 2-stellig |
| `title` | 2-4 Wörter, ALL CAPS, aktivierend (NICHT "BE HEALTHY") |
| `description` | 8-20 Wörter, konkret + spezifisch |
| Item-Anzahl | 3 bis 6 (4 ist Sweet Spot) |

### 33.4 Layout

- BG: Solid `#0A0A0F`, kein Bild
- Logo-Block top: 80px, H1 max 30px
- `.list-num` 28px Cyan, `.list-title` 18px weiß, `.list-desc` 14.5px weiß 78%
- Trenner zwischen Items, Swipe-Pfeil ausgeblendet

### 33.5 Don'ts

- Bilder hinzufügen, Generic-Titel ("BE HEALTHY"), >6 oder <3 Items, Description >20 Wörter

---

## 34. ⏰ OFF-PEAK GENERATION + ENGAGEMENT-PEAK POSTING (Cron-Split)

Generierung und Posten laufen in **zwei getrennten GitHub Actions Workflows** für maximale Stabilität.

### 34.1 Warum split?

| Aspekt | Begründung |
|---|---|
| Gemini Stability | ~80% weniger 503 "high demand" um 02-04 UTC |
| AI-Bilder | Together AI FLUX hat nachts seltener Timeouts |
| IG-Engagement | Audience aktiv 09-12 + 17-20 lokal — nachts gepostet = vergrabene Reichweite |
| Stabilität | 6+ Stunden Buffer zwischen Gen-Fail und Post-Slot |

### 34.2 Workflow-Architektur

```
.github/workflows/
  ├── generate_carousels.yml   ← 02:00 UTC (Off-Peak)
  │      Gemini-Plan + Cloudinary Upload + queue/POST_<ts>.json
  ├── post_from_queue.yml      ← 08:00 + 16:00 UTC (Peak)
  │      Liest queue, postet zu IG, → posted/
  └── daily_post.yml           ← DEPRECATED (Manual-Fallback)
```

### 34.3 Queue-Format

`queue/POST_<timestamp>.json`:
```json
{
  "timestamp": "20260502_0200",
  "topic": "Vitamin D deficiency",
  "language": "en",
  "caption": "...",
  "image_urls": ["https://res.cloudinary.com/.../slide_1.png", "..."],
  "generated_at": "2026-05-02T02:00:00"
}
```

Nach Post: Verschoben nach `posted/`, mit `instagram_status` + `posted_at` erweitert.

### 34.4 CLI

`cloud_pipeline.py --save-to-queue` → schreibt nur queue/, kein IG-Post.

```bash
python post_from_queue.py              # postet ältestes
python post_from_queue.py --dry-run    # zeigt nur was gepostet würde
python post_from_queue.py --pick FILE  # bestimmtes File
```

### 34.5 ⏰ POSTING-ZEITEN nach Sprache/Region (WICHTIG bei neuer Brand!)

Beim Onboarding NEUE Brand → IMMER fragen: "Welche Sprache + Welche Hauptregion?"

| Audience | Sprache | Beste Posting-Zeiten (lokal) | Cron in UTC (Sommerzeit) | Cron in UTC (Winter) |
|---|---|---|---|---|
| **DE/AT/CH** | Deutsch | 09:00 + 13:00 + 19:00 | 07/11/17 UTC | 08/12/18 UTC |
| **EU general** | Englisch | 08:00 + 12:00 + 18:00 lokal | 07/11/17 UTC | 07/11/17 UTC |
| **USA East** | Englisch | 08:00 + 12:00 + 18:00 EST | 13/17/23 UTC | 13/17/23 UTC |
| **USA West** | Englisch | 08:00 + 12:00 + 18:00 PST | 16/20/02 UTC | 16/20/02 UTC |
| **USA mixed** | Englisch | 11:00 EST = 08:00 PST | 16:00 UTC + 20:00 UTC | 16:00 UTC + 20:00 UTC |
| **UK** | Englisch | 08:00 + 13:00 + 19:00 GMT | 07/12/18 UTC | 08/13/19 UTC |
| **Indien** | Englisch/Hindi | 08:30 + 14:00 + 20:00 IST | 03/08:30/14:30 UTC | 03/08:30/14:30 UTC |
| **Latam (Spanisch)** | Spanisch | 09:00 + 14:00 + 20:00 (CT) | 14/19/01 UTC | 15/20/02 UTC |
| **Australia** | Englisch | 08:00 + 12:00 + 19:00 AEST | 22/02/09 UTC | 21/01/08 UTC |

**Health/Wellness/Anatomy-Content** performt am besten:
- Morgens 09:00 lokal (Health-Routinen werden geplant)
- Abends 19:00 lokal (Reflektions- & Recherche-Zeit)

**Fitness-Content** performt am besten:
- 06:00 lokal (Pre-Workout) und 18:00-20:00 lokal (Post-Workout)

**Business/Mindset-Content** performt am besten:
- 07:00-09:00 lokal (Morgenroutine) und 12:00 lokal (Lunchbreak)

### 34.6 Cron-Werte konvertieren

GitHub Actions cron läuft in **UTC**. Konvertierung:
- DE Sommer (CEST = UTC+2): lokale Stunde - 2 = UTC
- DE Winter (CET = UTC+1): lokale Stunde - 1 = UTC
- USA East Sommer (EDT = UTC-4): lokale Stunde + 4 = UTC
- USA East Winter (EST = UTC-5): lokale Stunde + 5 = UTC
- USA West Sommer (PDT = UTC-7): lokale Stunde + 7 = UTC
- USA West Winter (PST = UTC-8): lokale Stunde + 8 = UTC

GitHub Actions berücksichtigt KEINE Sommerzeit-Umstellung. Wenn präzise lokale Zeit kritisch ist:
- Workflow zwischen Sommer/Winter manuell anpassen (2x pro Jahr)
- ODER: Mehrere cron-Slots setzen die beide Zeitzonen abdecken
- ODER: Im Skript Local-Time-Check + early-exit nutzen

### 34.7 Anpassen für höhere Frequenz

3 Posts pro Tag:
- Generation: `count: 3` über workflow_dispatch
- Posting: 3 cron-Slots in `post_from_queue.yml`

---

## 35. 🎯 ADAPTIVE THEME-AWARE IMAGE LOGIC

Damit Bilder IMMER zum Thema passen — und nicht "Business-Mann im Anzug" für einen Vitamin-D-Post — muss der Slide-Planner das Topic verstehen und das passende Subject auswählen.

### 35.1 Brand-Vertical bestimmt Image-Pool

Der `slide_planner.py` SYSTEM_PROMPT enthält eine **Theme → Subject Mapping**-Tabelle, die spezifisch für die jeweilige Brand-Vertical sein MUSS.

Health Recode (medical/health/anatomy):
| Topic theme | Subject choice |
|---|---|
| Fasting / metabolism | Person silhouette at sunrise, AI render of cells, glass of water |
| Vitamin / mineral deficiency | Specific food source, concerned face, blood-test scene |
| Sleep / circadian | Person sleeping, dark bedroom, brain wave AI render |
| Hormones | AI render of gland, person reacting |
| Heart / cardiovascular | AI render of heart muscle, person clutching chest, BP cuff |
| Brain / mental health | AI render of brain regions, person looking pensive |
| Gut / digestion | AI render of gut microbiome, food photo, person holding stomach |
| Cancer / cell biology | AI render of cell mitosis, lab scene |
| Workout / muscle recovery | Athlete in dim gym, AI render of muscle fibers |
| Women's health | Female silhouette, AI render of ovaries/uterus |

### 35.2 Bei NEUER Brand: Mapping-Tabelle KOMPLETT umschreiben

Wenn ein neuer Claude diesen Guide für eine andere Vertical adaptiert (Fitness, Finance, Mindset), muss die Tabelle in `slide_planner.py` SYSTEM_PROMPT komplett ersetzt werden.

Beispiel **Fitness-Brand**:
| Topic theme | Subject choice |
|---|---|
| Hypertrophy | Person doing barbell row, AI render of muscle fiber |
| Mobility | Person doing yoga pose, foam roller |
| Cardio | Athlete running outdoor, heart-rate monitor |
| Recovery | Athlete in ice bath, sleep tracker |

Beispiel **Finance-Brand**:
| Topic theme | Subject choice |
|---|---|
| Investing | Charts on screen, calm person at desk |
| Saving | Person counting bills, savings tracker |

### 35.3 Adaptive Logic — Topics außerhalb der Tabelle

> "Read the topic carefully → identify the BODY SYSTEM or PROCESS involved → pick the most CONCRETE visual that DIRECTLY shows what the slide says"

- "ADHD focus tricks" → person mit focused eyes / single light source
- "Burnout" → exhausted face / cracked phone / collapsed posture
- "Fear" → dark room / clenched hand / silhouette in shadow

NIEMALS Default: "person meditating sunset" oder "businessman in suit".

### 35.4 Gender-Rotation

Im SYSTEM_PROMPT erzwungen:
- ~50/50 Mann/Frau über Carousel
- Gender-neutral wenn unisex (silhouettes, abstract body parts)
- Female-specific (period, menopause, pregnancy) → weibliche Subjects
- Male-specific (testosterone, prostate) → männliche Subjects

### 35.5 Brand-Vertical Override (No-Go-List)

Health Recode darf NIEMALS zeigen:
- Suit-and-tie Business-Fotos
- Hustle-Culture / Gold / Geld / "Erfolg"
- Generic Stock "Thumbs up" / "High Five"
- Office / Laptop (außer Topic ist Screen-Time)

Bei NEUER Brand: Liste komplett neu definieren.

### 35.6 Onboarding-Erweiterung (Sektion 8 ergänzen)

Beim ersten Setup zusätzlich fragen:
- "Vertical?" (medical/fitness/finance/mindset/business/...)
- "Sprache + Hauptregion?" (siehe Sektion 34.5 für Posting-Zeiten)
- "Image-Subjects erlaubt?" (Mensch/Tier/Anatomie/Objekt/Abstract)
- "Image-Subjects verboten?" (Brand-No-Gos)
- "Demographic?" (für Gender/Alter-Rotation)

Mit diesen Antworten Mapping-Tabelle in slide_planner.py NEU SCHREIBEN.

### 35.8 HERO IMAGE VARIETY — Anti-Sameness Rule

**Problem:** Gemini fällt zu oft auf "man face close-up" als Hero-Default zurück. Dadurch sehen alle Carousels gleich aus → Algorithmus-Stagnation, Audience-Müdigkeit.

**Lösung:** Im SYSTEM_PROMPT von `slide_planner.py` ist eine **8-Kategorien-Rotation** für Hero-Bilder erzwungen:

1. **Anatomical AI Render** — Organ/System Close-up
2. **Action Shot** — Person beim TUN (laufen, schlafen, trinken)
3. **Object Hero** — Topic-Kernobjekt allein (Pille, Glas Wasser, Frühstück)
4. **Environment Shot** — Weite Aufnahme des Raums (Schlafzimmer, Labor, Küche)
5. **Body Part Detail** — Extreme Close-up von Hand/Fuß/Auge/Haut (kein Gesicht)
6. **Silhouette / Backlit** — Person im Schatten (Gender-neutral)
7. **Macro / Microscopic** — Zellen, Microbiome, Neuronen
8. **Split-Frame Concept** — Vorher/Nachher, kontrastierende Zustände

**Verboten als Hero (ohne explizit faciale Topic-Begründung):**
- "Man's face close to camera"
- "Concerned woman with hand on forehead"
- "Smiling person at sunset"
- "Suit person at desk"
- "Yoga pose at sunset"
- "Person holding vegetable smiling"

**Topic-Mapping:**
| Topic-Typ | Hero-Kategorie |
|---|---|
| Hormone/Mechanismus | Anatomical Render / Macro |
| Routine/Habit | Action Shot / Environment |
| Symptom/Warnsignal | Body Part Detail / Silhouette |
| Transformation | Split-Frame |
| Nahrungsmittel | Object Hero (Lebensmittel allein) |

**Wenn doch Gesicht nötig:** Nur Side-Profile oder 3/4-Angle, kein direkter Close-up.

**Innerhalb EINES Carousels:** Niemals zwei Slides aus derselben Kategorie. Hero=Render → Content-Slides müssen Action/Object/Environment/Macro sein.

**Bei NEUER Brand:** Diese 8 Kategorien anpassen je nach Vertical. Z.B. Fitness-Brand → "Spotter pushing barbell", "ice bath water surface", "shoes laces close-up". Finance-Brand → "stock chart screen detail", "coin stack object", "office window environment".

### 35.9 WOMAN VARIETY — Aktivität an Topic anpassen

**Problem:** Gemini fällt für "Frauen-Bilder" zu oft auf "Businesswoman im Anzug" oder "Frau mit Hand am Kopf besorgt close-up" zurück. Das ist langweilig und passt selten zum Topic.

**Lösung:** Aktivität RICHTIG am Topic ausrichten — nicht Default-Business-Outfit.

**Topic → Frauen-Kontext (für Health/Fitness Brand):**

| Topic | Frauen-Aktivität |
|---|---|
| Fitness / Workout / Muscle | Hanteln heben, Yoga-Flow, draußen laufen, Boxen im Gym |
| Nutrition / Wasser / Fasten | Wasser trinken bei Sonnenaufgang, Obst halten, kochen |
| Schlaf / Circadian | Schlafend im dunklen Schlafzimmer, friedlich aufwachen |
| Hormone / Periode / Fertility | Hand auf Bauch, Frauen-Silhouette, Period-Tracker in Hand |
| Stress / Mental Health | Frau in Natur nachdenklich (KEIN direktes Gesicht), Silhouette am Fenster |
| Skin / Beauty (nur wenn Topic) | Side-Profile Skincare, Hand Serum auftragen, NICHT Stare in Kamera |
| Pregnancy / Motherhood | Bauch haltend, Mutter+Baby, abstrakte Silhouette |
| Mindset / Focus | Buch lesend, Journaling, Wandern mit Rucksack |
| Recovery / Yoga | Krieger-Pose, Foam-Rolling, Stretching zuhause |
| Business (NUR bei Medical: stress-from-work) | DANN Anzug ok, sonst NIE |

**Verboten als Default:**
- "Businesswoman im Blazer am Schreibtisch"
- "Frau Hand am Kopf besorgt" (außer Topic ist explizit Kopfschmerzen)
- Direkter Close-up Stare in Kamera (außer Gesichts-Anatomie-Topic)
- Stock "lächelnde Frau mit grünem Smoothie + Daumen hoch"

**Bei NEUER Brand (Vertical-spezifisch):**
- Fitness-Brand → Workout-Aktivitäten dominant
- Finance-Brand → Frau im Anzug ok (passt dann)
- Mindset-Brand → Frau lesend / journaling / nachdenklich
- Cooking-Brand → Frau in Küche kochend
Tabelle entsprechend anpassen je nach Brand-Vertical.

### 35.7 Connection zu generate_carousel.py

Renderer (`get_slide_image()`) interpretiert:
- `pexels_query` → Pexels (Stock-Photos)
- `ai_render: true` + `ai_prompt` → Together AI FLUX (Anatomie/Konzepte)
- `google_query` → Google Custom Search (echte Personen)
- `solid_color` → einfarbig (List-Slides)

Adaptive Logic gehört IM PLANNER (nicht im Renderer). Renderer ist dumm — er nimmt was der Planner ihm gibt.

---

## 36. 🎨 COMPLETE STYLE BIBLE — Copy-paste-ready Specs

Alle Pixel-Werte, Fonts, Farben, CSS-Klassen und HTML-Templates an einem Ort. Damit ein neuer Claude die Carousel-Renderer 1:1 nachbauen kann ohne Trial-and-Error.

### 36.1 Google Fonts URL (alle benötigten Fonts)

```html
<link href="https://fonts.googleapis.com/css2?family=Anton&family=Bebas+Neue&family=Caveat:wght@500;700&family=Inter:wght@300;400;600;700;800&family=Oswald:wght@300;400;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
```

| Font | Verwendung |
|---|---|
| **Oswald** | H1 Headlines (Content/Hero/List Slides) — kondensierter Sans, fettbar |
| **Bebas Neue** | Outro-Texte (extra kondensiert, sieht edel/clean aus) |
| **Inter** | Body-Text, List-Description, Subtle UI |
| **Plus Jakarta Sans** | Profile-Card Inhalt (modern, lesbar) |
| **Caveat** | "Share this with your Friends →" Cursive-Footer |
| **JetBrains Mono** | Vital-Signs Strip (HR/SpO₂/T) — Monospace medizinisch |
| **Anton** | Fallback für Oswald (sehr kondensiert) |

### 36.2 Brand Constants (Health Recode)

```python
BRAND_DISPLAY = "HEALTH RECODE"
BRAND_WORD_LEFT = "HEALTH"
BRAND_WORD_RIGHT = "RECODE"
BRAND_HANDLE = "@healthrecode"
BRAND_PRIMARY = "#00CFE8"      # Cyan/Türkis
BRAND_BG_DARK = "#0A0A0F"      # Near-black
```

Bei NEUER Brand alle 6 Werte neu setzen + Logo-PNG-Files austauschen.

### 36.3 Slide-Größen (FIX, nicht ändern)

```python
VIEW_W, VIEW_H = 420, 525     # Render-Viewport
SCALE = 1080 / 420            # 2.5714 — für 1080×1350 Export
# Final Output: 1080 × 1350 (Instagram 4:5)
```

### 36.4 H1 Headline (Content/Hero Slides)

```css
.headline {
  font-family: 'Oswald', 'Anton', sans-serif;
  font-weight: 700;
  text-transform: uppercase;
  line-height: 1.0;
  letter-spacing: 0.3px;
  color: white;
  margin-bottom: 2px;
  text-shadow: 0 3px 12px rgba(0,0,0,0.55), 0 1px 3px rgba(0,0,0,0.40);
  /* font-size kommt per inline style aus calc_headline_size() */
}
```

**Auto-Size-Logik** (`calc_headline_size`):
| Char-Count | Größe |
|---|---|
| <25 | 39px |
| 25-40 | 34px |
| 40-55 | 30px |
| 55-75 | 26px |
| 75-100 | 22px |
| 100-130 | 20px |
| >130 | 17px |

### 36.5 H2 Subhead (Content/Hero Slides)

```css
.subhead {
  font-family: 'Oswald', 'Anton', sans-serif;
  font-weight: 400;            /* NICHT default-bold */
  text-transform: uppercase;
  line-height: 1.18;
  letter-spacing: 0.3px;
  color: rgba(255,255,255,0.92);
  margin-bottom: 0;
  margin-top: 14px;
  text-shadow: 0 2px 10px rgba(0,0,0,0.50);
}
```

**Größe:** `max(20, headline_size * 0.75 + 2)` (= ~22-29px)

### 36.6 Style-Segmente (per-Wort-Stile in headline_parts)

Aus `render_headline()`:

| Style | CSS |
|---|---|
| `"primary"` | `color: #00CFE8; font-weight: 700` (Brand-Farbe, fett) |
| `"bold"` | `color: white; font-weight: 700` (weiß, fett) |
| `"regular"` | `color: rgba(255,255,255,0.92); font-weight: 300` (weiß, dünn) |
| `"normal"` | `color: white; font-weight: 400` (weiß, regulär) |
| `"white"` | `color: white; font-weight: 700` (Default, weiß fett) |

Mische pro Zeile für Rhythm: `[("AT HOUR ", "regular"), ("12", "primary"), (", BODY ENTERS ", "regular"), ("KETOSIS", "bold")]`

### 36.7 Description (3. Text-Ebene, klein)

```css
.description {
  font-family: 'Oswald', sans-serif;
  font-weight: 600;
  font-size: 17px;
  line-height: 1.4;
  letter-spacing: 0.3px;
  text-transform: uppercase;
  margin-top: 22px;
}
.description.outro-desc {  /* Override für Outro-Slides */
  font-size: 15px;
  line-height: 1.45;
  margin-top: 18px;
  font-weight: 500;
}
```

### 36.8 Logo Block (zwischen H1 und Bild)

```html
<div class="logo-block">
  <div class="logo-line left"></div>
  <span class="logo-text">HEALTH</span>
  <img class="logo-center-icon" src="..." alt="logo"/>
  <span class="logo-text">RECODE</span>
  <div class="logo-line right"></div>
</div>
```

```css
.logo-block { display: flex; align-items: center; justify-content: center; gap: 5px; }
.logo-line { flex: 0 0 70px; height: 1px; background: linear-gradient(to right, transparent, #00CFE8, #00CFE8); }
.logo-line.right { background: linear-gradient(to left, transparent, #00CFE8, #00CFE8); }
.logo-text { font-family: 'Inter'; font-weight: 600; font-size: 11px; letter-spacing: 2.5px; color: white; }
.logo-center-icon { width: 16px; height: 16px; object-fit: contain; }
```

### 36.9 Vital-Signs Strip (Top-Right Signature)

```html
<div class="vitals-strip">
  <span class="pulse-dot"></span>
  <span class="label">HR</span> <span class="value">72</span>
  <span class="label">·</span>
  <span class="label">SpO₂</span> <span class="value">98%</span>
  <span class="label">·</span>
  <span class="label">T</span> <span class="value">36.7°C</span>
</div>
```

```css
.vitals-strip {
  position: absolute; top: 14px; right: 14px; z-index: 6;
  display: flex; align-items: center; gap: 6px;
  padding: 3px 8px;
  background: rgba(0,0,0,0.18);
  backdrop-filter: blur(4px);
  border-radius: 3px;
  border: 1px solid rgba(255,255,255,0.05);
  font-family: 'JetBrains Mono', monospace;
  font-size: 7.5px;
  color: rgba(255,255,255,0.55);
  letter-spacing: 0.3px;
}
.vitals-strip .label { color: rgba(255,255,255,0.35); }
.vitals-strip .value { color: rgba(0,207,232,0.75); font-weight: 700; }
.vitals-strip .pulse-dot { width: 4px; height: 4px; border-radius: 50%; background: rgba(0,207,232,0.75); }
```

Werte rotieren pro Slide aus `vitals_values` Array (HR 68-76, SpO₂ 97-99%, T 36.5-36.8°C).

### 36.10 Swipe-CTA (Bottom "SWIPE FOR MORE")

```html
<div class="swipe-cta">
  <span>SWIPE FOR MORE</span>
  <svg class="swipe-arrow-mini" viewBox="0 0 24 24" fill="none">
    <path d="M9 6l6 6-6 6" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
  </svg>
</div>
```

```css
.swipe-cta {
  position: absolute; bottom: 30px; left: 0; right: 0; z-index: 6;
  display: flex; align-items: center; justify-content: center; gap: 6px;
}
.swipe-cta span { font-family: 'Inter'; font-size: 13px; letter-spacing: 3px; color: rgba(255,255,255,0.85); font-weight: 600; }
.swipe-arrow-mini { width: 11px; height: 11px; stroke: rgba(255,255,255,0.85); }
```

NICHT auf List-Slides, NICHT auf CTA, NICHT auf Outro.

### 36.11 Right-Arrow (Pfeil mitte rechts)

```html
<div class="swipe-arrow-right">
  <svg viewBox="0 0 24 24" fill="none">
    <path d="M9 6l6 6-6 6" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
  </svg>
</div>
```

```css
.swipe-arrow-right {
  position: absolute; right: 12px; top: 50%; transform: translateY(-50%);
  width: 28px; height: 28px; border-radius: 50%;
  background: rgba(255,255,255,0.18);
  backdrop-filter: blur(4px);
  display: flex; align-items: center; justify-content: center; z-index: 7;
}
.swipe-arrow-right svg { width: 14px; }
```

NICHT auf List, CTA, Outro.

### 36.12 Follow-CTA Klein (Standard, über Swipe)

```css
.follow-cta {
  font-family: 'Inter';
  font-size: 9px;             /* dezent, ~18% kleiner als H2 */
  font-weight: 300;           /* dünn, nicht aufdringlich */
  letter-spacing: 1.4px;
  color: #00CFE8;
  text-transform: uppercase;
  margin-top: 14px;           /* deutlicher Abstand zum H2-Block */
}
```

Inhalt: `FOLLOW @HEALTHRECODE TO NOT MISS MORE`

### 36.13 List-Slide (Tipp-Slide, kein Bild)

```css
.bottom-stack.list-stack {
  top: 80px; bottom: 70px;
  justify-content: flex-start;
  gap: 8px; padding: 0 28px;
}
.list-items { display: flex; flex-direction: column; width: 100%; margin-top: 14px; text-align: left; }
.list-row {
  display: flex; align-items: flex-start; gap: 14px; padding: 10px 0;
  border-top: 1px solid rgba(255,255,255,0.10);
}
.list-row:first-child { border-top: none; }
.list-num {
  flex: 0 0 38px;
  font-family: 'Oswald'; font-size: 28px; font-weight: 600;
  color: #00CFE8; line-height: 1; letter-spacing: 0.5px;
}
.list-title {
  font-family: 'Oswald'; font-weight: 700;
  text-transform: uppercase; font-size: 18px;
  letter-spacing: 0.5px; color: white; line-height: 1.15;
}
.list-desc {
  font-family: 'Inter'; font-weight: 400;
  font-size: 14.5px; line-height: 1.4;
  color: rgba(255,255,255,0.78);
}
```

### 36.14 Outro-Slide (Ronin-Style, vollständig inline-styled)

Outro ist KEIN Standard-Slide. Es nutzt komplett eigene HTML-Struktur (siehe `slide_html()` `if is_outro_final:` Branch).

**Layout-Stack (von oben nach unten):**

1. **BG-Image** (athletic silhouette via AI render) + dark overlay 85→97%
2. **Vital-Signs Strip** (Top-Right)
3. **DROP A 🔥** (Bebas Neue 34px, weight 400, ls 1.5px, margin-bottom 14px)
4. **IF YOU LEARNED &nbsp; SOMETHING NEW!** (Bebas Neue 20px, ls 1.5px, margin-bottom 16px)
5. **WHICH FACT [SHOCKED] YOU MOST?** (Bebas Neue 17px, ls 1.5px, margin-bottom 4px)
6. **TELL ME IN THE [COMMENTS] 👇** (Bebas Neue 17px, ls 1.5px, margin-bottom 18px)
7. **FOLLOW [@HEALTHRECODE] TO NOT MISS MORE!** (Bebas Neue 22px, ls 1.5px, line-height 1.05, white-space nowrap, margin-bottom 18px)
8. **Profile-Card** (siehe 36.15)
9. **"Share this with your Friends →"** (Caveat 20px, weight 600, opacity 0.9)

[SHOCKED], [COMMENTS], [@HEALTHRECODE] = Brand-Color Cyan #00CFE8

**Container:**
```html
<div style="position:absolute;inset:0;z-index:5;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:60px 28px 30px;">
```

### 36.15 Profile-Card (Outro, HTML-Built statt JPEG)

```html
<div style="width:96%;max-width:340px;border:1px solid #00CFE8;border-radius:8px;
            padding:12px 14px;display:flex;align-items:flex-start;gap:12px;
            margin-bottom:14px;text-align:left;background:rgba(0,0,0,0.5);">
  <!-- Avatar -->
  <div style="width:62px;height:62px;border-radius:50%;flex-shrink:0;overflow:hidden;
              background:#0A0A0F;border:1.5px solid #00CFE8;">
    <img src="<healthrecodeicon.png base64>" style="width:100%;height:100%;object-fit:cover;"/>
  </div>
  <!-- Content -->
  <div style="flex:1;min-width:0;">
    <div style="display:flex;align-items:center;gap:5px;margin-bottom:3px;">
      <span style="font-family:'Plus Jakarta Sans';font-weight:700;color:#fff;font-size:14px;">healthrecode</span>
      <span style="color:#999;font-size:12px;">⋯</span>
    </div>
    <div style="font-family:'Plus Jakarta Sans';font-size:11px;color:#fff;margin-bottom:5px;">
      Health | Fitness | Medical | Mindset
    </div>
    <div style="display:flex;gap:11px;font-family:'Plus Jakarta Sans';font-size:10.5px;color:#fff;margin-bottom:5px;">
      <span><b>98</b> Posts</span>
      <span><b>610</b> Followers</span>
      <span><b>572</b> Following</span>
    </div>
    <div style="font-family:'Plus Jakarta Sans';font-size:10px;color:#999;line-height:1.35;">
      Recode your body. Transform your life. Daily science-backed health.
    </div>
  </div>
</div>
```

Bei NEUER Brand: Border-Color tauschen, Avatar-PNG, Handle, Bio-Text, Counts.

### 36.16 BG-Gradient Standard (Content-Slides)

```css
.bg-gradient {
  position: absolute; inset: 0;
  background: linear-gradient(180deg,
    rgba(10,10,15,0.55) 0%,
    rgba(10,10,15,0.30) 18%,
    rgba(10,10,15,0.20) 30%,
    rgba(10,10,15,0.45) 45%,
    rgba(10,10,15,0.78) 60%,
    rgba(10,10,15,0.94) 75%,
    rgba(10,10,15,0.99) 90%,
    rgba(10,10,15,1.0) 100%
  );
}
```

Sorgt für: Bild oben durchsichtig, Text unten klar lesbar.

### 36.17 Bottom-Stack (Standard-Container für Text)

```css
.bottom-stack {
  position: absolute;
  bottom: 70px; top: 55%;     /* Text in unteren 45% des Slides */
  left: 0; right: 0;
  padding: 0 24px;
  display: flex; flex-direction: column;
  align-items: center; justify-content: flex-end;
  gap: 6px; z-index: 5;
  text-align: center;
}
.bottom-stack.top-position { top: 40px; bottom: auto; gap: 10px; }
.bottom-stack.list-stack { top: 80px; bottom: 70px; justify-content: flex-start; gap: 8px; padding: 0 28px; }
```

### 36.18 Engagement-Banner (auf Mid-Carousel "💾 SAVE THIS POST")

```css
.engagement-banner {
  margin-top: 14px;
  padding: 12px 16px;
  background: #00CFE8;       /* Brand Primary */
  color: black;              /* Bewusster Kontrast */
  font-family: 'Inter';
  font-size: 14px;
  font-weight: 700;
  letter-spacing: 0.5px;
  border-radius: 4px;
  text-align: center;
  text-transform: uppercase;
}
```

### 36.19 Slide-Type → Komponenten-Matrix

| Slide-Type | Logo-Block | H1 | H2 | Description | Engagement-Banner | Big-Follow-CTA | Profile-Card | Swipe-Arrow Right | Swipe-CTA Bottom | List-Items |
|---|---|---|---|---|---|---|---|---|---|---|
| `hero` | ✅ | ✅ | ✅ | – | – | – | – | ✅ | ✅ | – |
| `content` | ✅ | ✅ | ✅ | – | optional | – | – | ✅ | ✅ | – |
| `engagement` | ✅ | ✅ | ✅ | – | ✅ | – | – | ✅ | ✅ | – |
| `cta` | ✅ | ✅ | ✅ | – | – | – | – | – | – | – |
| `list` | ✅ | ✅ | – | – | – | – | – | – | – | ✅ |
| `outro_final` | – | inline | inline | inline | – | inline | ✅ | – | – | – |

### 36.20 Playwright Export (FIX, nicht ändern)

```python
VIEW_W, VIEW_H = 420, 525
SCALE = 1080 / 420  # 2.5714

await page.evaluate("""() => {
  document.body.style.cssText = 'padding:0;margin:0;display:block;overflow:hidden;background:#0A0A0F;';
  const frame = document.querySelector('.ig-frame');
  frame.style.cssText = 'width:420px;height:525px;overflow:hidden;margin:0;';
  const vp = document.querySelector('.carousel-viewport');
  vp.style.cssText = 'width:420px;height:525px;overflow:hidden;position:relative;';
}""")

# Pro Slide:
await page.evaluate("""(idx) => {
  const t = document.getElementById('track');
  t.style.transition = 'none';
  t.style.transform = 'translateX(' + (-idx * 420) + 'px)';
}""", i)
await page.screenshot(path=..., clip={x:0,y:0,width:420,height:525})
```

`device_scale_factor=2.5714` → liefert 1080×1350 PNG aus 420×525 Layout.

---

**Wenn ein neuer Claude alles aus Sektion 36 verwendet (gepaart mit Sektion 17 aus dem Original-Style-Bible), kann er das komplette Carousel-System für eine andere Brand nachbauen indem er nur folgendes ändert:**
1. Brand Constants (36.2)
2. Logo-PNGs (healthrecodeicon.png, healthrecordlogotrans.png)
3. Profile-Card Inhalt (36.15) — Handle, Bio, Counts
4. Optional: Brand-Color (#00CFE8) → andere Farbe in allen CSS-Werten
5. Optional: Theme-Mapping in slide_planner.py SYSTEM_PROMPT (Sektion 35)

---

## 37. 📝 CAPTION CTA RULE — Engagement-Closer am Ende jedes Posts

Jede IG-Caption MUSS mit einem klaren Engagement-CTA enden (vor den Hashtags). Das ist im `slide_planner.py` SYSTEM_PROMPT erzwungen — Gemini generiert es automatisch.

### 37.1 Pflicht-Bestandteile (alle 4):

1. **Save-Reminder** — "Save this so you don't lose it" / "Save for later"
2. **Share-Prompt** — "Share with someone who needs this" / "Send to a friend"
3. **Follow-Nudge** — "Follow @healthrecode for daily science" / "Follow for more"
4. **Don't-forget-Closer** — "Don't forget!" / "Pinky promise it'll change your week"

### 37.2 Beispiel-Variationen (Gemini rotiert sie):

```
💾 Save this so you don't lose it. Tag a friend who needs to see this.
Follow @healthrecode for daily science-backed health.
Don't forget — your future body will thank you.
```

```
Save it. Share with someone who's been asking about this.
Follow @healthrecode for more like this — daily.
Don't sleep on this 🔥
```

```
If this hit, save it for later, send to a friend,
and follow @healthrecode for daily medical breakdowns.
Don't miss the next one!
```

### 37.3 Caption-Struktur (komplett, von oben nach unten):

1. **Hook-Line** (1 Satz, knackig — same vibe as Slide 1 H1)
2. **3-5 educational facts** (science-backed, mit Zahlen/Hormonnamen)
3. **5 Emoji** verteilt (nicht gestapelt)
4. **CTA-Block** (4 Bestandteile aus 37.1)
5. **8 Hashtags** ganz am Ende

### 37.4 Tone

Warm, freundlich, **NICHT salesy**. Sprich wie ein wissender Freund — nicht wie eine Werbeanzeige.

### 37.5 Bei NEUER Brand

Falls eine andere Brand (z.B. Fitness statt Medical), nur den Handle (`@healthrecode`) und die Brand-Persönlichkeit anpassen. Die 4 CTA-Bestandteile bleiben gleich (Save/Share/Follow/Don't-forget) — das ist universal Engagement-Psychologie für IG-Algorithmus.

---

## 38. ♾️ FOREVER-TOKEN STRATEGY — Pipeline läuft ohne manuellen Token-Refresh

Standard-Problem: IG-Tokens laufen nach 60 Tagen ab → Pipeline stirbt → manueller Refresh nötig. **Lösung: Auto-Refresh per Cron.** Token läuft dadurch unendlich, ohne Eingriff.

### 38.1 Wie es funktioniert

Instagram Login API Tokens (`IGAA...`, 60 Tage gültig) können UNBEGRENZT verlängert werden, solange sie alle <60 Tage refresht werden. Das passiert automatisch:

```
.github/workflows/refresh_token.yml
  Cron: alle 50 Tage (7x/Jahr) um 03:00 UTC
  → ruft refresh_ig_token.py auf
  → POST https://graph.instagram.com/refresh_access_token
  → bekommt neuen Token (60 Tage gültig)
  → schreibt neuen Token via `gh secret set` in Repo-Secret zurück
```

Sicherheits-Buffer: 10 Tage (Refresh nach 50 von 60 Tagen).

### 38.2 Setup einmalig (Forever-Token aktivieren)

1. **GitHub Personal Access Token erstellen** mit `repo` + `workflow` + `secrets:write` Scopes:
   - https://github.com/settings/tokens → "Generate new token (classic)"
   - Name: "Health Recode Token Refresh"
   - Scopes: `repo`, `workflow`, `admin:repo_hook` (für secrets:write brauchst du fine-grained PAT mit Repository-secrets:write)

2. **PAT als Repo-Secret speichern:**
   - Settings → Secrets and variables → Actions → New repository secret
   - Name: `GH_PAT_FOR_SECRETS`
   - Value: `<dein-PAT>`

3. **Manueller Test-Run:**
   - Actions → "Auto-Refresh IG Token (Forever)" → Run workflow
   - Checken ob "OK — Repo-Secret aktualisiert" im Log steht

4. **Fertig.** Cron läuft danach 7x/Jahr automatisch.

### 38.3 Files

| File | Zweck |
|---|---|
| `refresh_ig_token.py` | Standalone-Script, refresht Token via IG-API. CLI: `--quiet` (nur Token), `--update-env` (lokal in .env schreiben) |
| `.github/workflows/refresh_token.yml` | Cron-Workflow, läuft alle 50 Tage |

### 38.4 Alternative: Facebook Page Access Token (NIEMALS abläuft)

**Wenn du komplett ohne Refresh willst:** Switch zu Meta Graph API (statt IG Login API) mit Page Access Token.

| Token-Typ | Lebensdauer |
|---|---|
| User Access Token (User-Login) | 60 Tage, refresh nötig |
| Long-Lived User Token (über setup_meta_credentials.py) | 60 Tage, refresh nötig |
| **Page Access Token** (aus Long-Lived User Token abgeleitet) | **NIEMALS abläuft** ⭐ |

**Page Token bekommen** (einmalig):
1. Long-Lived User Token erzeugen (Graph API Explorer oder OAuth-Flow)
2. Page-Token ableiten:
   ```
   GET https://graph.facebook.com/v21.0/me/accounts
     ?access_token=<long_lived_user_token>
   ```
3. Im Response findest du das `access_token` für deine Page → DAS läuft nicht ab.
4. Speichern als `FB_PAGE_ACCESS_TOKEN` in Repo-Secrets.

**Für IG-Posting via Page Token:**
- Endpoint: `https://graph.facebook.com/v21.0/{ig-business-account-id}/media`
- Auth: `?access_token={FB_PAGE_ACCESS_TOKEN}`
- Funktioniert wenn FB-Page mit IG-Business-Account verknüpft ist (Account-Center)

**Page Token läuft nur ab wenn:**
- FB-App gelöscht wird
- Token manuell widerrufen wird
- User-Passwort-Reset triggert (selten)

### 38.5 Welcher Weg ist besser?

| Aspekt | IG Login API + Auto-Refresh | FB Page Token (forever) |
|---|---|---|
| Setup-Komplexität | Mittel (PAT + Workflow) | Hoch (FB-App, Page, Account-Center) |
| Wartung | Cron läuft 7x/Jahr | Nie |
| Bricht wenn... | GH PAT abläuft (max 1 Jahr) | FB-App gelöscht / Passwort reset |
| Empfohlen für | Aktuelles Health Recode Setup | Neue Brands ohne Legacy |

**Empfehlung für Health Recode (UPDATED):** Nutze FB Page Access Token (38.4) als PRIMÄRE Auth — läuft NIE ab, kein Cron-Refresh nötig.
- Pipeline ist seit Mai 2026 so umgestellt: postet zuerst zu IG (mit IG_USER_ACCESS_TOKEN), dann Cross-Post zu FB Page (mit FB_PAGE_ACCESS_TOKEN).
- IG-Token weiterhin alle 50 Tage auto-refresht (Backup), aber FB Page Token ist primärer "Forever-Anker".

### 38.7 ⭐ FB Cross-Posting

**Es gibt 2 Wege — wähle nach Komfort:**

#### WEG A — Meta Account Center (EMPFOHLEN, KEIN Code/Setup nötig)

Wenn dein IG Business Account mit einer FB Page über das Meta Account Center verknüpft ist, postet Meta automatisch jeden IG-Post auch zu deiner FB Page. **Null Code-Aufwand, null Tokens.**

So einrichten in der Instagram App:
1. **Profil → Menü (≡) → Account Center**
2. **"Connected experiences" → "Sharing across profiles"**
3. **"Recommend on Facebook"** für deinen IG-Account aktivieren
4. **"Auto-share to Facebook"** ON

Nach Aktivierung: Jeder IG-Post (auch von der API) wird automatisch zu FB geposted. Deine Pipeline braucht keine FB-Secrets mehr.

✅ **Marwan hat das aktiviert (Mai 2026) — die Health-Recode Pipeline läuft mit dieser Methode.** Der Code in `post_to_facebook()` (siehe WEG B) bleibt als Backup im Repo, ist aber inaktiv solange `FB_PAGE_ACCESS_TOKEN` Secret leer ist.

#### WEG B — FB Page Token via Meta Graph API (Code-basiert, falls Account Center nicht funktioniert)

Wenn aus irgendeinem Grund Account Center Cross-Post NICHT funktioniert (z.B. Account-Trennung, Region-Restriktion, neue Brand ohne FB-Verknüpfung), kann die Pipeline explizit zu FB posten via FB Page Access Token:

```
[Post IG] Sende zu Instagram...   → IG_USER_ACCESS_TOKEN (60d, auto-refresh)
[Post FB] Cross-Post zu Facebook... → FB_PAGE_ACCESS_TOKEN (FOREVER)
```

Code in `cloud_pipeline.py` + `post_from_queue.py` ruft beide Endpoints auf. Wird aktiviert wenn `FB_PAGE_ACCESS_TOKEN` + `FB_PAGE_ID` als Repo-Secrets gesetzt sind. Sonst Status: `skipped (FB_PAGE_ID/FB_PAGE_ACCESS_TOKEN fehlt)`.

**Setup einmalig:**

1. **FB Page erstellen** (falls noch nicht vorhanden):
   - facebook.com → "Page erstellen" → Business or Brand → "Health Recode"

2. **FB App erstellen** auf https://developers.facebook.com/apps:
   - Type: Business
   - Name: "Health Recode Auto-Post"
   - Add Product: "Facebook Login" + "Pages API"

3. **Long-Lived User Token erzeugen** im Graph API Explorer:
   - graph.facebook.com/v21.0/oauth/access_token?grant_type=fb_exchange_token
   - Permissions: `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`, `instagram_basic`, `instagram_content_publish`

4. **Page Access Token ableiten** (das ist der FOREVER-Token):
   ```bash
   curl "https://graph.facebook.com/v21.0/me/accounts?access_token=<long_lived_user_token>"
   ```
   Im Response findest du dein FB Page-Objekt mit `access_token` Feld → DAS ist der Token den du brauchst.
   Auch die `id` deiner Page brauchst du (FB_PAGE_ID).

5. **Als Repo-Secrets speichern**:
   - Settings → Secrets → New
   - `FB_PAGE_ACCESS_TOKEN` = `<page_token>` (läuft NIE ab)
   - `FB_PAGE_ID` = `<numerische page_id>`

6. **Test**: Manueller Run von `post_from_queue.yml` → checken ob "FB Status: fb_posted: ..." im Log steht.

**Was passiert dann:**
- Carousel wird zu IG gepostet (Carousel-Format)
- Gleichzeitig zu FB Page gepostet (als Multi-Photo-Album)
- Beide nutzen identische Caption + Bilder
- Reach verdoppelt sich potenziell

### 38.6 Bei NEUER Brand

- Falls du komplett neu startest: Page Access Token (38.4) ist eleganter (kein Refresh nötig, keine PAT-Abhängigkeit)
- Falls du bereits IG Business Account ohne FB-App-Setup hast: IG Login API + Auto-Refresh (38.1) ist schneller einzurichten

In beiden Fällen: **kein manueller Token-Refresh mehr** — die Pipeline läuft selbstständig.

---

## 39. 🚨 LESSONS LEARNED — 44 Bugs aus Vorgänger-Build (PFLICHT-LEKTÜRE)

Diese Sektion sammelt ALLE Fehler die im Ronin-Codex Build gemacht wurden (separates Brand-Projekt mit gleicher Pipeline-Architektur). **Jeder Bug hat Stunden gekostet.** Ein neuer Claude MUSS diese Sektion zuerst lesen — sonst wiederholen sich diese Fehler garantiert.

### 39.1 ⚡ TL;DR — Die 3 wichtigsten Lessons

1. **PIPELINE END-TO-END TESTEN BEVOR PUSH** — Live-Post auf IG zeigte nur Background-Foto OHNE Layout, weil Render-Step nicht integriert war. Verifiziere visuell den finalen Output gegen Reference-Image, BEVOR du irgendwas zu GitHub pushst.

2. **EXAMPLES = SOURCE OF TRUTH** — Existierender `example_carousel/export_slides.py` war von Anfang an im Repo, wurde ignoriert, deshalb wurden rohe Background-Bilder gepostet statt gerenderter Carousels. Bei jedem Pipeline-Schritt fragen: "Existiert ein Example? Wenn ja → INTEGRIEREN, nicht umgehen."

3. **MULTI-FILE-UPDATES MIT GREP-SEARCH** — Wenn du eine Sache in einem File fixt, MUSST du grep alle Stellen wo dieser Pattern vorkommt. Niemals "ich hab Slide 4 gefixt" sagen wenn 5 weitere Slides die gleiche Stelle haben.

### 39.2 🟢 PFLICHT-Fragen vor erster Code-Zeile (spart >20 Stunden)

**Bevor du irgendwas baust**, frage den User diese 8 Punkte. Ohne klare Antworten BAU NICHT AN:

1. **Visual-Direction** — schickt der User 3-5 Reference-Bilder?
2. **Audience** — Männer / Frauen / beide? Welches Alter? Sprache? Region?
3. **Posting-Frequenz** — 1x/Tag, 2x, 3x?
4. **Auto-Post oder manuell?**
5. **Wartungs-Toleranz** — Forever-Run oder OK mit wöchentlicher Maintenance?
6. **Topic-Pillars** — 3-5 konkrete Themen-Säulen
7. **Slide-Count** — 8, 9, 10, oder dynamisch 3-15?
8. **CTA-Style** — Reference-Image für die letzte Slide

Erst klären, dann coden.

### 39.3 ⚡ Vor jedem Push — 3-Punkt Sanity-Check

Bevor du auch nur EINE Zeile zu GitHub pushst:

1. **"Macht das Code überhaupt das was beabsichtigt war?"** — Read your own code
2. **"Habe ich End-to-End getestet — visuell?"** — Final-Output gegen Reference-Image
3. **"Habe ich alle Stellen gefixt wo dieser Pattern vorkommt?"** — Grep-Search

Wenn nein zu auch nur EINER → noch nicht pushen. Mehr code = mehr bugs.

### 39.4 🔴 7 Root-Causes — Warum so viele Fehler passiert sind

| # | Root-Cause | Prevention |
|---|---|---|
| 1 | Pipeline NIE End-to-End getestet | Lokaler Manual-Test mit visueller Verifikation vor JEDEM Push |
| 2 | Style-Direction 4× geflippt | Visual-Direction am Anfang locken mit 3-5 Reference-Bildern + AskUserQuestion |
| 3 | Examples ignoriert die schon existierten | Examples = Source-of-Truth. Bei jedem Step fragen: "Existiert ein Example?" |
| 4 | Multi-File-Updates inkonsistent | Grep alle Stellen VOR dem Update, dann ALLE auf einmal |
| 5 | User-Frustration ignoriert | Bei "ich hab das schon gesagt" → STOP, scrollback, neu lesen |
| 6 | GitHub-Setup vor lokal-stable | Lokal grün = Voraussetzung für Push (inkl Python-Version-Match) |
| 7 | Layout-Polishing vor Functionality | Functional-First, Polish-Second. Live-Post-Check vor Pixel-Anpassungen |

### 39.5 🔴 KRITISCHER BUG — Render-Step nicht integriert (BUG #32)

**Symptom:** Live-Post auf Instagram zeigt NUR das rohe Hintergrundfoto. KEIN Headline, KEIN Logo, KEIN Save-Banner, KEIN Layout.

**Root Cause:** Pipeline lädt rohe Background-Photos direkt zu Cloudinary hoch. Der Playwright-Render-Step (HTML-zu-PNG mit allen Text-Overlays) wurde nicht aufgerufen.

**Pipeline-Korrektur:**
```
ALT (broken):
  generate → background_images → Cloudinary → IG (nur Background-Photo postet)

NEU (richtig):
  generate → carousel.html (mit Text-Overlays in HTML)
    → export_slides.py (Playwright Screenshots, alles eingebrannt)
    → Cloudinary → IG (volles Carousel)
```

**Lesson für Guide:** NIEMALS rohe Hintergrund-Bilder direkt zu IG hochladen. HTML-Carousel MUSS via headless-Browser gerendert + screenshotted werden. Im aktuellen Setup macht das `generate_carousel.py::export_slides()` via Playwright — der MUSS in der Pipeline-Kette sein.

### 39.5b 🔴 KRITISCHER BUG #45 — IG "Share to Facebook" Toggle funktioniert NICHT bei API-Posts

**Symptom:** User aktiviert in IG-App "Auto-share to Facebook" / "Recommend on Facebook" via Account Center. Posts via API erscheinen trotzdem NICHT auf Facebook.

**Root Cause:** Meta-Bug (offiziell bestätigt). Das Account-Center-Toggle "Share to Facebook" funktioniert nur bei MANUELLEN Posts in der IG-App, NICHT bei API-Posts (Graph API / Instagram Login API).

**Fix:** Expliziter FB-Page-Post via `graph.facebook.com/v21.0/{page_id}/photos` + `/feed` mit `FB_PAGE_ACCESS_TOKEN`. Ist im aktuellen Code als `post_to_facebook()` implementiert in `post_from_queue.py` und `cloud_pipeline.py`. Wird aufgerufen NACH erfolgreichem IG-Post.

**Pflicht-Secrets damit FB-Cross-Post läuft:**
- `FB_PAGE_ACCESS_TOKEN` (aus `me/accounts` API-Call abgeleitet — siehe Sektion 38.7 Schritt 4)
- `FB_PAGE_ID` (aus gleichem API-Call, `id` Feld)

**Verifikation dass es funktioniert:**
```
[Post FB] Cross-Post zu Facebook...
FB Status: fb_posted: 1234567890_123456789
```

Wenn `FB Status: skipped (FB_PAGE_ID/FB_PAGE_ACCESS_TOKEN fehlt)` → Secrets nicht gesetzt.
Wenn `FB Status: fb_error: ...` → Token-Permissions oder Page-Verknüpfung prüfen.

**Lesson für Guide:** NIEMALS auf Account-Center-Toggle vertrauen für API-basiertes Cross-Posting. IMMER expliziten Graph-API-Call zur FB Page implementieren.

---

### 39.6 ⚙️ Setup & Tooling Bugs

| # | Bug | Root Cause | Fix |
|---|---|---|---|
| 9 | Replicate-SDK Python-3.14-inkompatibel | Pydantic V1 vs Python 3.14 | HTTP-Calls statt SDK |
| 10 | f-string Backslash auf Py 3.11 | GitHub Actions verwendet 3.11 | Backslash in temp-Variable, dann f-string |
| 11 | JSON-Parse-Errors Gemini | Unescaped quotes in Strings | `json-repair` Library als Fallback |

### 39.7 🖼 Image-API Bugs

| # | Bug | Root Cause | Fix |
|---|---|---|---|
| 4 | Together AI: "height must be multiple of 16" | 1080 nicht durch 16 teilbar | width=1024, height=1280 (4:5) |
| 5 | Together AI: "non-serverless model" | FLUX.1-schnell-Free umgezogen | FLUX.1-schnell (ohne -Free) |
| 6 | Pexels/Pixabay 403 Forbidden | Custom User-Agent geblockt | Standard Chrome User-Agent |
| 7 | Replicate 402 Payment Required | Account-Balance $0 | $5 aufladen ODER aus Chain entfernen |
| 8 | Gemini 503 überlastet | Google-Server peaks | 8-Modell-Fallback-Chain + 02:30 CET runtime |

**Gemini Fallback-Chain (PFLICHT):**
```
gemini-2.5-flash → gemini-2.5-flash-lite → gemini-2.5-pro
→ gemini-2.0-flash → gemini-2.0-flash-exp
→ gemini-1.5-flash → gemini-1.5-flash-8b → gemini-1.5-pro
```

**Pexels/Pixabay UA (PFLICHT):**
```
Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36
```

### 39.8 📱 Meta Graph API Bugs

| # | Bug | Root Cause | Fix |
|---|---|---|---|
| 17 | "Error validating client secret" | Instagram-App-Secret ≠ Meta-App-Secret | Meta-App-Secret aus App Settings → Basic |
| 18 | Falsche Use-Case bei App-Erstellung | App Ads / WhatsApp / Threads gewählt | "Messaging und Content auf Instagram verwalten" |
| 19 | Token im falschen Format (IGAA vs EAA) | IG-Login statt FB-Login API gewählt | "API-Einrichtung mit Facebook-Log..." wählen |
| 20 | "Keine Pages mit IG-Verknüpfung" | Token ohne `instagram_basic` generiert | ALLE 5 Permissions ankreuzen |
| 21 | 60-Tage-Token-Expiry-Sorge | User Token läuft ab | FB_PAGE_ACCESS_TOKEN benutzen — läuft NIE ab (siehe Sektion 38) |

**Bei Token-Generieren PFLICHT-Permissions:**
- `instagram_basic`
- `instagram_content_publish`
- `pages_show_list`
- `pages_read_engagement`
- `business_management`

**Klar unterscheiden:**
- **Meta-App-Geheimcode** → App Settings → Basic
- **Instagram-App-Geheimcode** → Use Case → API Setup
- Beide existieren, sehen ähnlich aus, sind ABER VERSCHIEDEN

**Token-Format-Check:**
- **EAA...** → Graph API (graph.facebook.com), mit FB-Page-Setup
- **IGAA...** → Instagram Login API (graph.instagram.com), ohne FB-Page

### 39.9 🔧 Cloudinary Bug

| # | Bug | Root Cause | Fix |
|---|---|---|---|
| 22 | "Invalid api_key" | Cloud_Name / API_Key / Secret im GitHub Secrets verwechselt | Strikt unterscheiden: |

- `CLOUDINARY_CLOUD_NAME` = kurzer **Text** (z.B. `dzpo48ngf`)
- `CLOUDINARY_API_KEY` = NUR **Zahlen** (z.B. `812416893654214`)
- `CLOUDINARY_API_SECRET` = **Mix** aus Buchstaben+Zahlen

### 39.10 🎨 Layout & Style Bugs

| # | Bug | Root Cause | Fix |
|---|---|---|---|
| 23 | `[GOLD]word[/GOLD]` zeigt sich roh | gold_marks() nur auf headline angewendet | Auf JEDEN Text-Field anwenden (body, subheadline, steps, tips) |
| 24 | `[SECRET]` statt `[GOLD]SECRET[/GOLD]` | Gemini schreibt manchmal nur Brackets | gold_marks() permissiv: `[WORD]` + `**word**` auch akzeptieren |
| 25 | Anton zu condensed/quetschig | Headlines unleserlich bei langem Text | Bebas Neue als Default + 1.5px letter-spacing |
| 26 | Body-Text immer 13px (zu klein) | Statische Größe | Dynamic body-sizing: 22px-13px je nach Länge |
| 27 | Foto-Fade zu hart | Gradient bei 50% direkt schwarz | Soft gradient: transparent 0-35%, fade bis 75% |
| 28 | Slide 1 immer "man face close-up" | Gemini fällt auf erste Beispiel-Kategorie zurück | 10 Kategorien-Rotation Pflicht im Prompt (siehe Sektion 35.8) |
| 29 | Frauen immer "Businesswoman close-up" | Zu enge Vorgabe | Gender + Topic-aware Variety pro Pillar (siehe Sektion 35.9) |
| 30 | Topic-Bild-Mismatch (Snow für Business) | "Looks cinematic" wichtiger als "matches topic" | CRITICAL TOPIC-RELEVANCE RULE im Prompt |
| 31 | Save-Banner zu prominent | Voll-breit gold | Rectangle, dark bg, subtle gold border |
| 32 | CTA zwei-zeilig statt eins | Gemini interpretiert Zeilenumbrüche frei | Single-line erzwingen mit `&nbsp;` |
| 33 | CTA-Profile-Pic war 🥷 Emoji | Brand-Icon nicht eingebunden | Brand-Icon als base64 in HTML |
| 34 | SWIPE FOR MORE zu klein/dunkel | Default-Style zu subtle | 46px großer Glas-Effekt-Button mit SVG-Pfeil |
| 35 | H2-Texte zu klein/groß flip-flop | Statische Größen pro Slide | Dynamisch +30%, +20% iterativ |
| 36 | Body-Text zu nah am SWIPE FOR MORE | bottom: 54px | bottom: 90-100px für Atmungsraum |

### 39.11 🚀 Posting & GitHub Actions Bugs

| # | Bug | Root Cause | Fix |
|---|---|---|---|
| 37 | Workflow generiert nichts wenn ein Bild fehlt | Hardcoded slide_count | Dynamic slide_count aus carousel.json |
| 38 | post_carousel.py lädt rohe Background-Bilder | `images/` statt `slides/` | Posting greift auf `slides/` (gerendert) zu |
| 42 | UTC vs CET-Verwechslung | GitHub Cron in UTC, User dachte CET | Im YAML beide Zeiten kommentieren |

### 39.12 🌍 Audience & Content Bugs

| # | Bug | Root Cause | Fix |
|---|---|---|---|
| 39 | Tagline "for men" | Definition zu eng | "for those who refuse mediocrity" + Frauen ergänzen |
| 40 | Brand-Name = Topic-Verwechslung | "Ronin Codex" → User dachte Samurai-Inhalte | Brand-Name vs Topic vs Visual klar trennen |
| 41 | Engagement-CTAs nicht gut platziert | Nur am Ende | Mid-Engagement-Banner + Final-CTA-Slide |
| 43 | Caption-CTA zu schwach | Nur generic Follow-Aufforderung | 4-Zeilen-CTA-Block: Save+Like+Share+Follow (siehe Sektion 37) |

### 39.13 🚨 META-LESSONS — Process-Fehler die ich (Claude) gemacht hab

**M1. Pipeline NIE End-to-End getestet, bevor weitergebaut wurde.** Generate, Render und Post als getrennte Schritte gebaut, ohne EIN MAL alles zusammen laufen zu lassen mit visuellem Output-Check.
→ **Lesson:** Zuerst END-TO-END-Test mit echtem Output, DANN Features hinzufügen. Lokaler Manual-Test ist Pflicht vor jedem GitHub-Run. "müsste theoretisch funktionieren" zählt nicht.

**M2. Style-Direction 4× geflippt** (Editorial → Vintage Etching → Photorealistic → Samurai → Topic-relevant).
→ **Lesson:** Visual-Richtung am Anfang des Setups festnageln mit konkreten Reference-Bildern. Nie auf "ach das könnte auch so sein"-Pivots reagieren — erst NACH Setup-Lock optimieren.

**M3. Zu viele Clarifying-Questions verpasst.** Direkt mit Code-Bauen losgelegt nach 1-2 Fragen.
→ **Lesson:** Am Anfang 5-10 Min mit präzisen Setup-Fragen investieren (siehe 39.2). Spart später 5-10 Stunden Iterationen.

**M4. Beim Code-Update Inkonsistenzen erzeugt.** Font-Size in Slide 2 geändert, vergaß Slide 3, 4, 7.
→ **Lesson:** Multi-File / Multi-Slide-Updates IMMER mit Grep-Search nach allen Stellen, dann konsistent updaten.

**M5. Example-File ignoriert das die Lösung war.** `example_carousel/export_slides.py` war von Anfang an im Repo — wurde ignoriert.
→ **Lesson:** Example-Code ist Source-of-Truth. Bei jedem Pipeline-Schritt: Existiert ein Example? Wenn ja → integrieren, nicht ignorieren.

**M6. User-Frustration ignoriert.** Mehrfach hat User gesagt "ich hab das schon gesagt", "wieso machst du das doppelt".
→ **Lesson:** Wenn User Frustration zeigt → STOP, neu lesen, neu verstehen, dann erst Code. Nicht weiter "produktiv aussehen".

**M7. Fehler-Diagnose ohne Logs.** Mehrmals Fixes deployed, OHNE auf die exakten Error-Logs zu warten.
→ **Lesson:** Bei Fehlern ZUERST Logs lesen, dann fixen. Nie "wahrscheinlich ist es das" raten.

**M8. Forever-Setup-Frage nicht früh gestellt.**
→ **Lesson:** "Wie lange soll das laufen ohne Wartung?" als Setup-Frage. Determines token strategy, scheduler architecture, error-recovery.

**M9. GitHub-Setup gestartet bevor lokal stable.** Code zu GitHub gepusht, GitHub Actions zeigt f-string-Backslash-Error den ich lokal nie gesehen hätte.
→ **Lesson:** Lokal komplett grün = Voraussetzung für GitHub-Push. Inkl Python-Version-Match (lokal 3.14, prod 3.11).

**M10. Layout-Polishing zu früh, Funktionalität zu spät.** Stunden in CSS-Feinheiten investiert bevor verifiziert war dass das Layout überhaupt richtig nach Instagram kommt.
→ **Lesson:** Functional zuerst, polish zweitens.

**M11. Overengineered Provider-Fallback bevor Single-Provider stabil.** 5-Provider-Chain gebaut bevor auch nur EINER konsistent funktionierte.
→ **Lesson:** Erst 1 Provider stabil, DANN Fallbacks dazu. Nicht alle 5 gleichzeitig.

**M12. Keine "Sanity Check"-Phase.** 50+ Iterations-Cycles weil keine Vor-Push-Verifikation.
→ **Lesson:** 3-Punkt Sanity-Check vor jedem Push (siehe 39.3).

### 39.14 📋 Komplette Process-Checklist für nächsten Brand-Setup

**Vor Code-Schreiben:**
- [ ] Visual-Direction mit 3-5 Reference-Bildern festnageln
- [ ] Audience genau (Geschlecht, Alter, Sprache, Region)
- [ ] Posting-Frequenz (1x/Tag? 2x?)
- [ ] Auto-Post oder manuell
- [ ] Wartungs-Toleranz (Forever-Run? Wöchentlicher Refresh OK?)
- [ ] Topic-Pillars (3-5 konkret)
- [ ] Slide-Count fix (8? 9? 10? oder dynamisch)
- [ ] CTA-Style fix (mit Reference-Image)

**Setup-Schritte:**
- [ ] Python-Version checken (3.11 für GitHub Actions, 3.12+ lokal — Code muss 3.11-kompat sein)
- [ ] requirements.txt mit `json-repair`, NICHT `replicate` (HTTP-only)
- [ ] Together AI Modell ohne `-Free` Suffix
- [ ] Pexels/Pixabay mit Standard Chrome User-Agent
- [ ] Multi-Model Gemini Fallback-Chain (8 Modelle)
- [ ] Multi-Provider Image Fallback (Gemini → Together → Replicate → Pexels → Pixabay) — aber NUR wenn 1 Provider 100% stabil
- [ ] Meta App: Use-Case "Messaging und Content auf Instagram verwalten" + "Alles auf deiner Seite verwalten"
- [ ] Beim Token-Generieren ALLE 5 Permissions
- [ ] FB-Login-API-Pfad (`graph.facebook.com`), NICHT Instagram-Login-API
- [ ] FB_PAGE_ACCESS_TOKEN als primary Token (forever-running, siehe Sektion 38)
- [ ] Cloudinary Cloud Name / API Key / API Secret klar unterscheiden
- [ ] Bebas Neue als Headline-Font, NICHT Anton
- [ ] gold_marks() auf JEDEM Text-Field
- [ ] Slide-1-Hook mit 10-Kategorien-Rotation (Sektion 35.8)
- [ ] Topic-Relevance-Rule im Image-Prompt
- [ ] Audience gender-inklusiv definieren
- [ ] CTA-Slide 1:1 nach Reference-Image bauen
- [ ] Save-Banner dezent unten, NICHT prominent oben
- [ ] Engagement an 2 Punkten (mid + end)
- [ ] GitHub Actions cron in UTC mit CET-Kommentar
- [ ] Verify-Step nach Generation (Hard fail wenn <3 Bilder)
- [ ] dots_row() dynamisch mit slide-count
- [ ] Brand-Name vs Topic im Prompt klar trennen

**Während Code-Schreiben:**
- [ ] Multi-File-Updates IMMER mit Grep-Search verifizieren
- [ ] Bei Style-Changes: alle Slides prüfen
- [ ] Examples = Source-of-Truth, NICHT ignorieren
- [ ] Lokal Python-Version matchen mit GitHub Actions Python-Version

**Vor jedem Push / Deploy:**
- [ ] Lokaler End-to-End-Test mit echtem Output
- [ ] Visual-Verify: Sieht der finale Post wie das Reference-Image aus?
- [ ] Logs lesen, nicht raten
- [ ] Sanity-Check (3-Punkt aus 39.3)
- [ ] Alle Stellen wo eine Sache gefixt wurde — auch andere ähnliche Stellen?

### 39.15 🎯 Ergebnis bei richtiger Anwendung

Mit dieser Checklist + dem Pipeline-Render-Fix (39.5) + den Process-Lessons (M1-M12):
**Nächster Brand-Setup in <2 Stunden statt >30 Stunden.**

---

**Ende des Handover-Guides**. Bei Fragen: User direkt fragen, NICHT raten.

**WICHTIG für neuen Claude**:

🚨 **ZUERST SEKTION 39 LESEN** — 44 Bugs aus dem Vorgänger-Build, jeder einzelne hat Stunden gekostet. Wenn du diese nicht kennst, wirst du sie wiederholen.
 
- Lies diesen Guide KOMPLETT vor erster Aktion (besonders Sektion 31 — Fehler-Bibel!)
- Frag den User die Punkte aus Sektion 8
- Halte dich an Style-Bibel (Sektion 17 + 17.9 exakte Zahlen)
- Nutze NUR die NEUE Instagram-API (Sektion 26)
- Bei API-Fehlern IMMER Fallbacks nutzen (Sektion 28)
- Text-Hierarchie H1/H2/Description/CTA strikt befolgen (Sektion 29)
- HTML/CSS/Playwright-Setup 1:1 wie in Sektion 30 — keine Abweichungen
- **Fehler-Bibel (Sektion 31) als Lookup nutzen** wenn was schiefgeht — niemals raten
- **Hook-Regeln (Sektion 32) auf JEDEN Post anwenden** — schwacher Hook = Post stirbt
- **List/Tips-Slides (Sektion 33) für actionable Topics** nutzen — nummerierte Tipps ohne Bilder
- **Cron-Split (Sektion 34) verstehen** — Generation 02:00 UTC, Posting Peak-Zeit (siehe Tabelle 34.5)
- **Posting-Zeit per Sprache/Region** wählen (Sektion 34.5) — DE != EU != USA != IN
- **Adaptive Image-Logic (Sektion 35) bei NEUER Brand** — Mapping-Tabelle in slide_planner.py umschreiben
- **Woman Variety (Sektion 35.9)** — Frauen-Aktivität an Topic anpassen, NIEMALS Default Businesswoman/Close-up
- **Style-Bible (Sektion 36)** — alle Pixel/Fonts/CSS für H1/H2/Description/Logo/Vitals/Swipe/Outro/Profile-Card direkt zum Copy-paste
- **Caption CTA (Sektion 37)** — JEDE Caption muss mit Save/Share/Follow/Don't-forget enden (bevor Hashtags)
- **Forever-Token (Sektion 38)** — Auto-Refresh alle 50 Tage ODER FB Page Token (nie abläuft) — KEIN manueller Refresh mehr
- **Auto Topic Refill (Sektion 40)** — `refill_topics.py` läuft VOR jedem Generate; topics.txt < 15 → AI füllt auf 50 auf (Gemini Primary, Anthropic Fallback)
- **New Brand Setup (Sektion 41)** — Step-by-Step Checklist für jedes neue Brand (IG-Account → FB-Page → Tokens → GitHub Secrets via gh CLI)
- **API Strategy (Sektion 42)** — Was MUSS pro Brand neu sein vs was bleibt geteilt; Limits-Math für 10 Brands × 4 Carousels/Tag
- **FB Forever Token (Sektion 43)** — `get_forever_fb_token.py` Script + komplette UI-Walkthrough (Deutsche Meta-UI hat Eigenheiten)
- **Email Alerts (Sektion 44)** — Gmail SMTP Setup, App-Password, Failure-Email-Templates, Success-Email für Posts
- **gh CLI Workflow (Sektion 45)** — Alle Setup-Steps via Command-Line statt Browser-Klicken (Marwan bevorzugt das stark)
- **Bug-Log dieser Session (Sektion 46)** — Bugs #45-52 mit Root-Cause + Fix
- **Volume Math (Sektion 47)** — Mit aktueller Single-Account-Strategie skaliert die Pipeline auf 100+ Carousels/Tag ohne Limits zu reißen

---

## 40. 🤖 AUTO TOPIC REFILL — Topics.txt füllt sich selbst

**Problem (war):** Marwan musste manuell `topics.txt` mit 50+ Topics pflegen. Wenn die Liste leer wurde → Pipeline crashed.

**Lösung (jetzt):** `refill_topics.py` läuft **VOR jedem Generate-Run** im GitHub Actions Workflow. Wenn `topics.txt` weniger als 15 Einträge hat, wird via Gemini AI automatisch auf 50 aufgefüllt.

### 40.1 Wie es funktioniert

1. **Pre-Check**: `python refill_topics.py --min 15 --target 50`
2. **Liest**: aktuelles `topics.txt` + alle bereits geposteten Topics aus `posted/POST_*.json`
3. **Wenn zu wenig**: AI generiert N neue medizinische Topics
4. **Dedupe**: case-insensitive gegen alle bereits-genutzten Topics
5. **Schreibt zurück**: aktualisierte `topics.txt` ans Repo (wird im selben Workflow-Step committed)

### 40.2 Quality-Bar im SYSTEM_PROMPT

Jedes Topic muss:
- SPECIFIC sein (nicht "be healthy", sondern "Cortisol's 90-minute morning window controls your day")
- MECHANISM-DRIVEN (das WIE, nicht nur das WAS)
- HOOK-WORTHY (Zahlen, Hormone, Körpersysteme, Forschungsergebnisse)
- NICHE: medizinisch/biologisch/anatomisch — KEIN generisches Wellness-Bla

### 40.3 Kategorien-Rotation (10 Buckets)

Damit der Content abwechslungsreich bleibt, rotiert AI über:
1. Hormones (cortisol, insulin, dopamine, testosterone, estrogen, melatonin, leptin, ghrelin)
2. Organs & Systems (liver detox, gut microbiome, brain plasticity, lymph)
3. Sleep & Circadian
4. Fasting & Metabolism (autophagy, ketosis, mTOR)
5. Nutrition Science (vitamin/mineral mechanisms)
6. Neuro & Mental (anxiety, focus, depression biology)
7. Exercise Physiology
8. Aging & Longevity (telomeres, NAD+, senescence)
9. Stress Physiology (HPA axis, vagal tone)
10. Women's Health (cycle phases, perimenopause)

### 40.4 Workflow-Integration (DOPPELTES Safety-Net)

**Layer 1 — Pre-Check vor Generate** (täglich, in `generate_carousels.yml`):

```yaml
- name: Auto-refill topics (aggressive — keep buffer at 100)
  run: |
    python refill_topics.py --min 50 --target 100

- name: Generate carousels ...
```

**Layer 2 — Wöchentlicher Standalone-Refill** (in `refill_topics.yml`):

Läuft jeden Sonntag 01:00 UTC zusätzlich, falls Layer 1 mal failed. Cron: `0 1 * * 0`. Pushst topics.txt zurück ins Repo + sendet Email-Alert wenn fail.

**Defaults sind aggressive** (Marwan will NULL manuelle Pflege):
- `--min 50` (refilled wenn unter 50 Topics)
- `--target 100` (auf 100 auffüllen — großer Buffer)

**Memory-Reminder für zukünftige Claude:** Wenn der User sagt "auch ab 50 soll es nachfüllen" → Defaults sind bereits 50/100 (aggressive). Nicht zurück auf 15/50 ändern!

### 40.5 Manueller Override

```bash
# Sofort auf 100 auffüllen (auch wenn schon viele drin sind):
python refill_topics.py --force --target 100

# Höhere Schwelle (wenn 30 Brands gleichzeitig laufen):
python refill_topics.py --min 50 --target 200
```

### 40.6 Was bei einem neuen Brand angepasst werden muss

`refill_topics.py` hat einen `SYSTEM_PROMPT` der für **HealthRecode (Medical/Health)** geschrieben ist. Bei einem neuen Brand mit anderer Niche:

1. Kopiere `refill_topics.py` zu `brands/<brand>/refill_topics.py` (oder pass es im Multi-Tenant-Refactor an `brand` parameter an)
2. Update den SYSTEM_PROMPT mit:
   - Brand-Audience (Alter, Interessen)
   - Niche-spezifische Categorien (z.B. für FitnessBrand: Strength Training, Endurance, Mobility, Recovery, Nutrition for Athletes, etc.)
   - Beispiele guter/schlechter Topics für diese Niche

---

## 41. 🏗️ NEW BRAND SETUP CHECKLIST — Step-by-Step für jedes neue Brand

**Wenn der User sagt "neuer Brand X", führst du ihn EXAKT diese Schritte durch.** Pro neuem Brand 30-45 Min Setup, Rest läuft autonom.

### 41.1 PRE-FLIGHT (vor dem ersten Schritt)

Du fragst den User:
1. **Brand-Name?** (z.B. "FitLearn", "NutritionCode")
2. **Niche?** (1 Satz Beschreibung — bestimmt Content-Stil)
3. **Brand-Farbe?** (Hex-Code für Akzent, z.B. cyan #00CFE8 für HealthRecode)
4. **Logo vorhanden?** (oder soll ich generieren?)
5. **Existierender IG-Account oder neuer?** (siehe 41.2 Warm-Up Strategie)
6. **Existierende FB-Page oder neue?** (1 IG = 1 FB-Page Pflicht)

### 41.2 Warm-Up vs sofortige Automation

⚠️ **KRITISCH:** Neue oder lange inaktive IG-Accounts dürfen NICHT sofort auto-posten — Meta flaggt sie als Bot/Spam → Shadowban oder Ban.

**Empfohlene Reihenfolge (immer):**

| Woche | Action | Posting-Modus |
|---|---|---|
| **1** | Profil-Update (Bio, Foto, Highlights, 3-5 Stories) + 3-4 manuelle Posts vom Handy | Manuell (vom Handy) |
| **2** | 1 manueller Post + 1 API-Post pro Tag (Pipeline-Test ohne Risiko) | Mix |
| **3+** | Volle Automation 2-4×/Tag via Pipeline | API |

**Bei einem Account der "ein paar Jahre alt" ist + 0 Posts:** GENAU dieselbe Warm-Up-Strategie. Alter ist OK aber plötzliche Aktivität ohne Warm-Up = Spam-Flag.

### 41.3 Step 1 — Instagram Account vorbereiten

1. Im IG-App login (mit dem gewünschten Account)
2. Settings → Account type and tools → **Switch to professional account** → wähle **Creator** oder **Business**
3. Profil-Update: Name, Bio, Profilbild (cyan/brand-color icon), Link
4. Edit Profile → **Page** → Connect to existing FB Page → wähle die Brand-FB-Page (oder erstelle eine neue)

**Falls keine FB-Page existiert:** vor diesem Schritt FB-Page erstellen unter `https://www.facebook.com/pages/create`

### 41.4 Step 2 — Meta App Setup (1× pro Brand-Cluster, kann shared sein)

**Wichtig:** EIN Meta-App reicht für ALLE Brands. Du musst nicht pro Brand eine neue App erstellen.

Wenn schon eine App existiert (z.B. die HealthRecode-App):
- Nichts machen — gleiche `FB_APP_ID` + `FB_APP_SECRET` für alle Brands nutzen
- **ABER prüfe** dass der Use Case **"Alles auf deiner Seite verwalten"** GRÜN-HAKEN-konfiguriert ist (siehe 41.4b unten)

Wenn keine App existiert:
1. `https://developers.facebook.com/apps` → **Create App**
2. Use Case wählen: **"Other"** → Type: **Business**
3. Name: `MultiContentPipeline` oder ähnlich
4. **Settings → Basic** → App ID + App Secret kopieren
5. Use Cases hinzufügen (PFLICHT-Schritt — siehe 41.4b):
   - **Instagram API with Instagram Login** (für IG)
   - **Manage everything on your Page** (für FB-Posting)
6. App-Mode: **"In Development"** lassen (nicht Live setzen — Live braucht App Review)
7. Add Roles: dich selbst als Admin/Tester (Settings → Roles)

### 41.4b 🔴 KRITISCH — Use Cases freischalten BEVOR Graph Explorer

⚠️ **Reihenfolge ist Pflicht: Use Case Setup ZUERST, dann Graph Explorer.**

Permissions wie `pages_manage_posts` (Pflicht für FB-Cross-Posting) erscheinen im Graph API Explorer **NICHT**, bis der zugehörige Use Case in der Meta-App freigeschaltet ist. Symptom wenn übersprungen: Permission ist im "Berechtigung hinzufügen" Such-Dropdown nicht zu finden → Token wird ohne Permission generiert → FB-Post failed.

**Nach App-Erstellung (oder bei existierender App ohne grünen Haken):**

1. App-Dashboard öffnen
2. Liste **"App-Anpassung und Anforderungen"** suchen
3. Klick auf `>` rechts neben **"Den Anwendungsfall „Alles auf deiner Seite verwalten" personalisieren"**
4. Auf der nächsten Seite Permissions aktivieren:
   - `pages_show_list`
   - `pages_read_engagement`
   - **`pages_manage_posts`** ← die kritische
   - `pages_manage_metadata`
   - `pages_manage_engagement` (optional, hilfreich)
5. Speichern
6. Zurück im Dashboard prüfen: Use Case hat jetzt **🟢 grünen Haken**

**ERST DANN** zum Graph Explorer (Sektion 41.5/41.6) wechseln. Permissions sind jetzt verfügbar.

**Detail-Reference:** siehe Sektion 43.2a für visuell-detaillierte Walkthrough mit Screenshot-Beschreibungen.

### 41.5 Step 3 — IG-Token holen

1. `https://developers.facebook.com/tools/explorer/`
2. Meta-App Dropdown → wähle deine App
3. User or Page → "Get User Access Token"
4. Permissions adden:
   - `instagram_business_basic`
   - `instagram_business_content_publish`
   - `instagram_business_manage_messages`
   - `instagram_business_manage_comments`
5. **Generate Access Token** → mit dem Account einloggen (NICHT dem Brand-Account, sondern dem Meta-Admin-Account)
6. **Wichtig:** im Permission-Popup wird gefragt, welche IG-Accounts/Pages → wähle den Brand
7. Token im Feld kopieren (User Token, Short-Lived 1h)
8. Im Dropdown auf "**\<Brand-IG-Name\>**" wechseln (unter "Instagram Accounts")
9. Token im Feld ist jetzt der **IG_USER_ACCESS_TOKEN**
10. URL-Bar: `me?fields=id` → Senden → die zurückgegebene `id` ist die **IG_USER_ID**

**Long-Lived Token holen (60 Tage statt 1h):**

```bash
curl "https://graph.instagram.com/access_token?grant_type=ig_exchange_token&client_secret=<APP_SECRET>&access_token=<SHORT_TOKEN>"
```

→ Returns Long-Lived Token. Auto-Refresh läuft via `refresh_ig_token.yml` Workflow alle 50 Tage = NIE abgelaufen.

### 41.6 Step 4 — FB Forever Page Token holen (siehe Sektion 43)

Run `python get_forever_fb_token.py`:
- App-ID + App-Secret eingeben (gleich für alle Brands)
- User Token aus Graph Explorer eingeben
- Im Output: `FB_PAGE_ID = ...` + `FB_PAGE_ACCESS_TOKEN = ...` (Forever)
- Script schreibt automatisch in GitHub Secrets via gh CLI

### 41.7 Step 5 — GitHub Secrets setzen (via gh CLI)

```powershell
$BRAND = "fitlearn"  # oder welches neue Brand

# Brand-spezifisch
echo "<IG_USER_ID>" | gh secret set "IG_USER_ID_${BRAND}".ToUpper() --repo shinobi1412ai/healthrecode
echo "<IG_TOKEN>" | gh secret set "IG_USER_ACCESS_TOKEN_${BRAND}".ToUpper() --repo shinobi1412ai/healthrecode
echo "<FB_PAGE_ID>" | gh secret set "FB_PAGE_ID_${BRAND}".ToUpper() --repo shinobi1412ai/healthrecode
echo "<FB_TOKEN>" | gh secret set "FB_PAGE_ACCESS_TOKEN_${BRAND}".ToUpper() --repo shinobi1412ai/healthrecode

# Geteilt (1× setzen, dann nicht mehr ändern):
# GEMINI_API_KEY, ANTHROPIC_API_KEY, PEXELS_API_KEY, TOGETHER_API_KEY,
# CLOUDINARY_*, FB_APP_ID, FB_APP_SECRET, SMTP_USER, SMTP_PASS
```

### 41.8 Step 6 — Brand-Config

`brands/<brand>/config.yaml`:
```yaml
name: FitLearn
ig_handle: fitlearn
brand_color: "#FF6B35"   # orange für Fitness
secondary_color: "#0A1F33"
logo_path: brands/fitlearn/logo.png
font_main: Bebas Neue
font_body: Plus Jakarta Sans
caption_voice: "energetic, action-oriented, gym-bro friendly"
```

`brands/<brand>/topics.txt` — initial 5-10 Topics (rest wird via Auto-Refill aufgefüllt)

### 41.9 Step 7 — Test + Live

```powershell
# 1. Generate-Workflow manuell triggern (mit count=1)
gh workflow run generate_carousels.yml --field brand=$BRAND --field count=1 --repo shinobi1412ai/healthrecode

# 2. ~6 Min warten, dann Status:
gh run list --repo shinobi1412ai/healthrecode --workflow=generate_carousels.yml --limit 1

# 3. Wenn grün: Post-Workflow triggern
gh workflow run post_from_queue.yml --field brand=$BRAND --repo shinobi1412ai/healthrecode

# 4. ~3 Min warten, dann Log:
$RUN_ID = gh run list --repo shinobi1412ai/healthrecode --workflow=post_from_queue.yml --limit 1 --json databaseId --jq ".[0].databaseId"
gh run view $RUN_ID --log | Select-String "Status"

# Erwartet:
# IG Status: posted: <id>
# FB Status: fb_posted: <id>
```

---

## 42. 🔑 API ACCOUNT STRATEGY — Shared vs Per-Brand

**Goldene Regel:** Was kann shared bleiben? Alles was kein Account-spezifisches Limit hat. Was muss neu sein? IG- und FB-Account selbst (sind brand-defining).

### 42.1 Per-Brand NEU (Pflicht)

| Item | Warum | Wo zu holen |
|---|---|---|
| **Instagram Account** | 1 IG = 1 Brand | manuell in IG-App erstellen + Business-Modus |
| **Facebook Page** | 1 FB-Page = 1 IG-Account (für IG ↔ FB Verknüpfung) | facebook.com/pages/create |
| **IG_USER_ID** | identifiziert IG-Account in Graph API | Graph Explorer: `me?fields=id` mit IG-Account ausgewählt |
| **IG_USER_ACCESS_TOKEN** | 60-Tage-Token, alle 50 Tage auto-refresht | Graph Explorer → Long-Lived-Exchange |
| **FB_PAGE_ID** | identifiziert FB-Page | aus Page-URL oder Graph Explorer |
| **FB_PAGE_ACCESS_TOKEN** | Forever-Token (nie expired) | `get_forever_fb_token.py` Script |

### 42.2 Geteilt (1× setzen, gilt für alle Brands)

| Item | Warum geteilt | Free-Tier-Limit | Verbrauch bei 10 Brands × 4/Tag |
|---|---|---|---|
| **GEMINI_API_KEY** | 1500 Reqs/Tag free | 1500/Tag | 40 Reqs/Tag = 2,7% |
| **ANTHROPIC_API_KEY** | Pay-as-you-go, ~$0.001/Plan | unbegrenzt | $0.04/Tag = $1.20/Monat |
| **PEXELS_API_KEY** | 200 Reqs/h, 20k/Monat | 20k/Monat | 240 Reqs/Tag = 7200/Monat = 36% |
| **TOGETHER_API_KEY** | Pay-as-you-go, $0.04/Bild | unbegrenzt | 40 Bilder/Tag = $1.60/Tag = $48/Monat |
| **CLOUDINARY_*** | 25GB Storage Free | 25GB | 320 PNGs/Tag × 90 Tage × 500KB = 14GB → in Limit |
| **FB_APP_ID + FB_APP_SECRET** | EIN Meta-App reicht für alle Brands | unbegrenzt | egal |
| **ANTHROPIC_API_KEY** (caption fallback) | siehe oben | siehe oben | siehe oben |
| **SMTP_USER + SMTP_PASS** | 1 Gmail App-Password für Failure-Alerts | unbegrenzt | egal |

### 42.3 Anti-Patterns (NICHT TUN)

❌ **Mehrere Gemini Accounts**: gegen Google ToS (siehe Sektion 47.4) → Total-Ban-Risiko
❌ **Mehrere FB Apps pro Brand**: unnötig, App ist neutral, nur Pages sind brand-spezifisch
❌ **Mehrere Cloudinary Accounts**: 25GB pro Account reicht; ggf. Brand-Folder nutzen (`folder=fitlearn/` im Upload)
❌ **Mehrere Pexels API Keys**: 20k/Monat reicht für 30+ Brands

### 42.4 Wenn ein API-Limit doch reißt

| Limit erreicht | Option 1 | Option 2 |
|---|---|---|
| Gemini 1500/Tag | Anthropic-Fallback (schon implementiert) | Upgrade auf Pay-as-you-go ($0.075/1M tokens, vernachlässigbar) |
| Pexels 200/h | Spread Generation über 1h (nicht alle 10 Brands gleichzeitig) | Pixabay-Fallback (schon implementiert) |
| Cloudinary 25GB | Retention auf 60 Tage senken | Pay-as-you-go ($1/GB Bandbreite) |
| Together AI Cost | Switch zu Pollinations.ai (free, niedrigere Quali) für niedrig-Priority Brands | — |

---

## 43. ♾️ FB FOREVER PAGE TOKEN — Komplette Anleitung mit deutscher UI

**Was ist das:** Ein FB Page Access Token der NIE abläuft. Wird derived von einem Long-Lived User Token. Solange dein FB-Account selbst nicht gelöscht/gesperrt wird, läuft der Page-Token forever.

### 43.1 Voraussetzungen

- FB-Page existiert + ist mit IG-Account verknüpft
- Meta-App existiert (siehe Sektion 41.4) im "In Development" Mode
- Du bist Admin der App + der FB-Page

### 43.2 Permissions die der User Token haben muss

Im Graph API Explorer **bevor "Generate Access Token"** musst du diese Permissions adden:

1. `pages_show_list` — Pages auflisten
2. `pages_read_engagement` — Engagement-Daten lesen
3. **`pages_manage_posts`** ← ⚠️ **NICHT vergessen, sondern erscheint NICHT im Explorer wenn nicht freigeschaltet!** (siehe 43.2a)
4. `pages_manage_metadata` — Page-Metadaten

### 43.2a 🔴 KRITISCH — `pages_manage_posts` ERST in Meta-App freischalten, DANN im Graph Explorer

**Korrektur einer häufigen Falsch-Annahme:** Diese Permission wird oft als "vergessen" beschrieben — das ist FALSCH. Die Permission **erscheint nicht im Graph Explorer Permission-Search** bis sie über die Meta-App's **Use Cases Dashboard** für die App freigeschaltet wurde.

**Wenn du also im Graph Explorer nach `pages_manage_posts` suchst und es kommt nichts → das ist KEIN Bug, sondern fehlendes Use-Case-Setup in der App.**

**So schaltest du es frei (Pflicht-Schritt VOR Graph Explorer):**

1. `https://developers.facebook.com/apps` → deine App öffnen (z.B. HealthRecode)
2. Im Dashboard siehst du eine Liste mit **"App-Anpassung und Anforderungen"** (oder ähnlich) — dort sind verschiedene **Use Cases** als Zeilen mit grünen/grauen Haken
3. Such die Zeile: **"Den Anwendungsfall „Alles auf deiner Seite verwalten" personalisieren"**
4. Klick auf den **`>` Pfeil rechts** in dieser Zeile (oder direkt auf den Zeilentitel)
5. Auf der nächsten Seite siehst du eine Liste der Permissions die zu diesem Use Case gehören:
   - `pages_show_list`
   - `pages_read_engagement`
   - `pages_manage_posts` ← **HIER wird sie sichtbar/aktiviert**
   - `pages_manage_metadata`
   - `pages_manage_engagement`
   - etc.
6. **Aktiviere** alle die du brauchst (mind. die 4 oben)
7. **Speichern/Bestätigen** im Use-Case-Editor

**Erst NACH Schritt 7** erscheint `pages_manage_posts` im Graph API Explorer und kann zu einem Token added werden.

**Symptom wenn du diesen Schritt überspringst:**
- Im Graph Explorer "Berechtigung hinzufügen" → Suche nach `pages_manage_posts` → keine Ergebnisse
- Oder: Permission erscheint mit grauem Schloss-Icon (nicht aktivierbar)
- Folge: Token wird ohne diese Permission generiert → FB-Cross-Post failed mit `(#200) The permission(s) pages_manage_posts are not available`

**Dieser Schritt ist 1× pro Meta-App nötig.** Wenn die App schon "Alles auf deiner Seite verwalten" konfiguriert hat (grüner Haken im Dashboard), kannst du Schritt 1-7 überspringen und direkt zum Graph Explorer.

### 43.2b Wo der grüne Haken ist (Visual-Hinweis für deutsche UI)

Im App-Dashboard die Zeilen mit Use Cases haben am LINKEN Rand ein Icon:
- 🟢 **Grüner Haken** in Kreis = Use Case schon vollständig konfiguriert → Permissions sind im Explorer verfügbar
- ⚪ **Grauer leerer Kreis** = Use Case noch nicht konfiguriert → Permissions sind im Explorer NICHT verfügbar → erst konfigurieren

**Häufiges Setup für HealthRecode/ähnliche Brands** (alle sollten grünen Haken haben):
- Den Anwendungsfall „Messaging und Content auf Instagram verwalten" personalisieren
- Den Anwendungsfall „Facebook-, Instagram- und Threads-Content auf anderen Websites einbetten" personalisieren
- Den Anwendungsfall „Auf die Live Video API zugreifen" personalisieren
- Den Anwendungsfall **„Alles auf deiner Seite verwalten"** personalisieren ← KRITISCH für FB-Cross-Posting
- Testing-Anforderungen überprüfen und abschließen

### 43.3 Deutsche UI-Eigenheiten (Marwan-spezifische Gotchas)

Wenn der User die deutsche Meta-UI nutzt:

| Englisch | Deutsch | Wo zu finden |
|---|---|---|
| User or Page | Nutzer oder Seite | rechtes Panel mittig |
| Get User Access Token | Nutzer-Zugriffstoken anfordern | Dropdown im "Nutzer oder Seite" |
| Page Access Tokens | Seiten-Zugriffstokens | unten im Dropdown |
| Add a Permission | Berechtigung hinzufügen | unten im Permissions-Block |
| Generate Access Token | Generate Access Token (bleibt englisch!) | großer blauer Button |
| App Settings → Basic | App-Einstellungen → Allgemeines | linkes App-Menü |

⚠️ **Häufige Verwirrung:** Wenn der User die "neue Meta Use Cases UI" hat (Dashboard mit grünen Haken-Liste), nicht die alte Permissions-UI:
- Use Case "Alles auf deiner Seite verwalten" enthält automatisch `pages_manage_posts` + `pages_show_list` + `pages_read_engagement`
- Wenn dieser Use Case grünen Haken hat → Permissions sind verfügbar im Graph Explorer

### 43.4 Script: get_forever_fb_token.py

Liegt im Repo-Root. Was es macht:

1. Fragt interaktiv `FB_APP_ID`, `FB_APP_SECRET` (falls nicht in .env)
2. Fragt nach **User Token** (NICHT Page Token!) aus Graph Explorer
3. Tauscht Short-Lived → Long-Lived User Token (60 Tage) via `oauth/access_token?grant_type=fb_exchange_token`
4. Holt aus `/me/accounts` die Pages + deren Page-Tokens (forever, weil derived von Long-Lived)
5. Wenn `gh` CLI installiert ist: schreibt direkt `FB_PAGE_ID` + `FB_PAGE_ACCESS_TOKEN` in GitHub Secrets
6. Falls `gh` nicht installiert: gibt Tokens auf Console aus, User trägt manuell ein

### 43.5 Häufige Fehler beim Forever-Token-Holen

| Fehler | Root Cause | Fix |
|---|---|---|
| `Tried accessing nonexisting field (accounts)` | User hat **Page Token** ans Script gegeben statt User Token | Im Graph Explorer Dropdown auf "Nutzertoken" wechseln, dann Token kopieren |
| `(#200) pages_manage_posts not available` | User Token wurde ohne `pages_manage_posts` Permission generiert | Im Graph Explorer Permission adden + Token NEU generieren |
| `OAuthException 190` | App ID oder App Secret falsch | Settings → Basic in Meta App, beide Werte neu kopieren |
| Token works but FB-Post failed `code 200` | Page Token hat nicht ALLE Permissions vom User Token geerbt | User Token mit ALLEN 4 Permissions neu generieren |
| Mehrere Pages erscheinen | User ist Admin von mehreren Pages | Script fragt interaktiv welche → User wählt Brand |

### 43.6 Forever-Token testen

```python
import requests
TOKEN = "EAA..."  # dein neuer Forever Page Token
PAGE_ID = "..."  # deine FB_PAGE_ID

# Test 1: Token gültig?
r = requests.get(f"https://graph.facebook.com/v21.0/{PAGE_ID}",
    params={"fields": "id,name", "access_token": TOKEN})
print(r.json())  # sollte {"id": "...", "name": "...", "id": "..."}

# Test 2: Permissions OK?
r = requests.get(f"https://graph.facebook.com/v21.0/{PAGE_ID}/feed?limit=1",
    params={"access_token": TOKEN})
print(r.status_code)  # sollte 200
```

---

## 44. 📧 EMAIL FAILURE ALERTS — Gmail SMTP Setup

**Was:** Bei Workflow-Fail kommt eine Email zu `makevision1412@gmail.com` mit Subject `🚨 Auto Run Bug — \<workflow\>` und direktem Log-Link. Bei erfolgreichen Posts kommt `✅ Auto-Post live`.

⚠️ **HÄUFIGE VERWIRRUNG (Marwan ist drauf reingefallen):** SMTP_PASS ist NICHT das normale Gmail-Passwort. Es ist ein speziell für Apps generiertes 16-stelliges Passwort. Ohne 2FA kann man keines erstellen.

### 44.1 Setup (1× — folge GENAU dieser Reihenfolge)

**Schritt 1: 2FA aktivieren** (falls noch nicht — Pflicht für App-Passwords):
1. Geh zu `https://myaccount.google.com/security`
2. Bei **"2-Step Verification"** → klicken → aktivieren
3. Phone-Verification durchgehen (SMS-Code eingeben)

**Schritt 2: App-Password generieren:**
1. Geh zu `https://myaccount.google.com/apppasswords`
2. Bei **"App name"** eingeben: `HealthRecode Pipeline` (oder beliebigen Namen)
3. Klick **"Create"**
4. Es erscheint ein **16-stelliger Code** in Format `xxxx xxxx xxxx xxxx`
5. **WICHTIG:** Code SOFORT kopieren — wird nur EINMAL angezeigt
6. **Leerzeichen entfernen** beim Pasten → 16 Buchstaben am Stück, also aus `abcd efgh ijkl mnop` wird `abcdefghijklmnop`

**Schritt 3: In GitHub Secrets eintragen** (via gh CLI — kein Browser-Klicken nötig):
```powershell
# Email-Adresse als SMTP_USER
echo "makevision1412@gmail.com" | gh secret set SMTP_USER --repo shinobi1412ai/healthrecode

# App-Password (16 Zeichen, OHNE Leerzeichen) als SMTP_PASS
echo "abcdefghijklmnop" | gh secret set SMTP_PASS --repo shinobi1412ai/healthrecode
```

**Schritt 4: Verifizieren dass beide Secrets da sind:**
```powershell
gh secret list --repo shinobi1412ai/healthrecode | Select-String "SMTP"
# Erwartete Ausgabe:
# SMTP_PASS    Updated <jetzt>
# SMTP_USER    Updated <jetzt>
```

**Schritt 5: Test-Email triggern** (optional aber empfohlen):
```powershell
# Triggert absichtlich einen Fail im Generate-Workflow um Email zu testen
# Topic mit invaliden Zeichen → Crash → Failure-Email sollte kommen
gh workflow run generate_carousels.yml --field topic="ZZZ_INVALID_TEST_FAIL" --field count=1 --repo shinobi1412ai/healthrecode

# Warte 5 Min, dann Inbox checken auf:
# Subject: "🚨 Auto Run Bug — Generate Carousels failed"
```

### 44.1b Wichtige Klarstellung (für zukünftige Claude-Sessions)

**Wenn der User fragt "was für ein Passwort? PW von was?" → er meint SMTP_PASS.**

Antwort-Pattern:
1. Klar machen: "NICHT dein normales Gmail-Passwort"
2. Erklären: "Ein 16-stelliges App-Password — separater Code nur für diese Pipeline"
3. Direkt-Link geben: `https://myaccount.google.com/apppasswords`
4. Voraussetzung erwähnen: "2FA muss aktiv sein, sonst geht App-Password nicht"
5. Final-Step: gh CLI Command zum Eintragen

**Niemals den User fragen "kennst du dein Gmail-Passwort?"** — das ist eine Sicherheitsverletzung und auch nicht das was er braucht.

### 44.1c Was passiert ohne SMTP-Secrets

Workflows laufen trotzdem, aber:
- Email-Step `dawidd6/action-send-mail@v3` schlägt fehl
- Workflow wird ROT angezeigt (auch wenn IG/FB-Post erfolgreich war)
- Marwan denkt fälschlich "Pipeline ist kaputt"

**Fix:** Email-Steps haben `continue-on-error: true` (für Success-Email). Failure-Emails sind kritischer aber failen nur silent (ohne Workflow als gescheitert zu markieren wenn das eigentliche Posting funktioniert hat).

### 44.2 Email-Templates (in Workflows)

Alle 3 Workflows haben einen `dawidd6/action-send-mail@v3` Step:

**Generate Carousels** — bei Fail:
```yaml
- name: Send failure email
  if: failure()
  uses: dawidd6/action-send-mail@v3
  with:
    server_address: smtp.gmail.com
    server_port: 465
    secure: true
    username: ${{ secrets.SMTP_USER }}
    password: ${{ secrets.SMTP_PASS }}
    subject: "🚨 Auto Run Bug — Generate Carousels failed"
    to: makevision1412@gmail.com
    from: HealthRecode Pipeline <${{ secrets.SMTP_USER }}>
    body: |
      ❌ Generate Carousels Workflow ist gescheitert.
      Run: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}
      Häufigste Ursachen: Gemini/Anthropic API down, Pexels Quota, Cloudinary, git push permissions
```

**Post from Queue** — bei Fail UND bei Success:
- Failure-Subject: `🚨 Auto Run Bug — Post from Queue failed`
- Success-Subject: `✅ Auto-Post live — HealthRecode`

**Refresh Token** — KRITISCH falls fail:
- Subject: `🚨 Auto Run Bug — IG Token Refresh failed (KRITISCH)`
- Body warnt vor dem 10-Tage-Buffer bevor Token expired

### 44.3 Was die Failure-Email enthält

- Workflow-Name, Repository, Trigger, Branch, Commit
- **Direkter Link** zum Run-Log (klickbar)
- **Häufigste Ursachen** mit konkreten Fixes (zur Selbsthilfe ohne Claude)
- **Manueller Retry** Anleitung (z.B. "Gehe zu GitHub → Actions → Run workflow")

### 44.4 Email-Spam vermeiden

Failure-Emails haben `if: failure()` — nur wenn Workflow rot wird.
Success-Emails haben `if: success()` — bei jedem grünen Post.
**Bei 4 Posts/Tag = 4 Success-Emails/Tag.** Falls zu viel, einfach den Success-Step entfernen oder auf "alle 7 Tage Summary" ändern (Future-Improvement).

---

## 45. 💻 gh CLI WORKFLOW — Alles ohne UI-Klicken

**User-Präferenz (siehe Memory):** Marwan will minimum manual UI clicks. Default zu Scripts + gh CLI.

### 45.1 Installation (1×)

```powershell
winget install GitHub.cli
# Neues PowerShell öffnen (PATH-Refresh)
gh auth login
# Wähle: GitHub.com → HTTPS → Login with web browser
```

### 45.2 Cheat-Sheet — alle wichtigen Commands

```powershell
# Secrets setzen (statt UI klicken)
echo "VALUE" | gh secret set SECRET_NAME --repo shinobi1412ai/healthrecode

# Secrets auflisten (mit Updated-Time)
gh secret list --repo shinobi1412ai/healthrecode

# Workflow triggern (statt "Run workflow" klicken)
gh workflow run WORKFLOW.yml --repo shinobi1412ai/healthrecode --field key=value

# Run-Status der letzten 5 Runs
gh run list --repo shinobi1412ai/healthrecode --limit 5

# Letzte Run-ID eines bestimmten Workflows
$RUN_ID = gh run list --repo shinobi1412ai/healthrecode --workflow=post_from_queue.yml --limit 1 --json databaseId --jq ".[0].databaseId"

# Log eines Runs (nur Status-Zeilen)
gh run view $RUN_ID --repo shinobi1412ai/healthrecode --log | Select-String "Status"

# Run abbrechen (wenn er hängt)
gh run cancel $RUN_ID --repo shinobi1412ai/healthrecode

# Hängenden Workflow live verfolgen
gh run watch --repo shinobi1412ai/healthrecode
```

### 45.3 Häufige PowerShell-Fallen

**Problem:** "Die Benennung 'gh' wurde nicht erkannt"
**Cause:** PATH nicht refresht nach Installation
**Fix:**
```powershell
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
```
Oder: PowerShell schließen + neu öffnen.

**Problem:** Git-Lock blockiert Push (`File exists. Another git process...`)
**Fix:**
```powershell
Remove-Item -Force .git\index.lock -ErrorAction SilentlyContinue
Remove-Item -Force .git\refs\remotes\origin\main.lock -ErrorAction SilentlyContinue
```

### 45.4 End-to-End Test eines Brand (komplett gh-CLI):

```powershell
$BRAND = "healthrecode"

# 1. Generate
gh workflow run generate_carousels.yml --repo shinobi1412ai/$BRAND --field topic="" --field count=1
Start-Sleep -Seconds 360

# 2. Status check
gh run list --repo shinobi1412ai/$BRAND --limit 3

# 3. Post
gh workflow run post_from_queue.yml --repo shinobi1412ai/$BRAND
Start-Sleep -Seconds 180

# 4. Final status
$RUN_ID = gh run list --repo shinobi1412ai/$BRAND --workflow=post_from_queue.yml --limit 1 --json databaseId --jq ".[0].databaseId"
gh run view $RUN_ID --repo shinobi1412ai/$BRAND --log | Select-String "Status"
```

---

## 46. 🐛 BUGS DIESER SESSION — #45 bis #52 (Append zur Fehler-Bibel Sektion 31)

### Bug #45 — `(#200) The permission(s) pages_manage_posts are not available`

**Wann:** FB Cross-Post failed obwohl FB_PAGE_ACCESS_TOKEN gesetzt ist
**Root Cause:** ⚠️ **NICHT** "vergessen im Graph Explorer" — sondern: Permission `pages_manage_posts` ist im Graph Explorer **gar nicht erst verfügbar/sichtbar**, bis sie in der Meta-App's **Use Cases Dashboard** (über "Den Anwendungsfall „Alles auf deiner Seite verwalten" personalisieren") freigeschaltet wurde. Wenn der User im Explorer-Dropdown sucht und sie nicht findet, ist das KEIN Bug der Suche — es bedeutet die Use Case ist nicht konfiguriert in der App.

**Fix in 2 Phasen (Reihenfolge wichtig!):**

**Phase 1 — Permission in Meta-App freischalten** (1× pro App):
1. `https://developers.facebook.com/apps` → deine App
2. Dashboard → Use Case Liste → klick auf `>` rechts neben **"Den Anwendungsfall „Alles auf deiner Seite verwalten" personalisieren"**
3. Auf der detail-Seite: aktiviere `pages_manage_posts`, `pages_show_list`, `pages_read_engagement`, `pages_manage_metadata`
4. Speichern → grüner Haken im Dashboard

**Phase 2 — Token mit Permission generieren** (im Graph Explorer):
1. `https://developers.facebook.com/tools/explorer/`
2. "Berechtigung hinzufügen" → **JETZT** erscheinen die Permissions in der Suche → alle 4 selektieren
3. **NEU "Generate Access Token"** klicken (nicht refreshen)
4. Im Permission-Popup ALLE 4 zustimmen
5. Dann erst Forever-Token-Script ausführen

**Prevention:** Sektion 43.2a dokumentiert den Use-Case-Freischalt-Schritt explizit; Setup-Checklist Sektion 41 listet ihn als Pflicht-Schritt VOR dem Graph Explorer; Sektion 43.2b zeigt visuell wie man die grünen Haken im Dashboard erkennt.

**Marwan-Memory:** Marwan hat sich darüber beschwert weil ich initial geschrieben hatte "Permission oft vergessen". Korrekt: "Permission muss erst in App freigeschaltet werden, sonst erscheint sie im Explorer gar nicht."

### Bug #46 — `Tried accessing nonexisting field (accounts)` (Code 100)

**Wann:** `get_forever_fb_token.py` failed bei Step `[2] Hole Pages + Forever Page Tokens`
**Root Cause:** User hat **Page Token** ans Script gegeben statt **User Token**. `/me/accounts` Endpoint funktioniert NUR mit User Tokens. Bei Page Tokens ist `/me` = die Page selbst (keine `accounts`-Field).
**Fix:** Im Graph Explorer Dropdown auf **"Nutzertoken"** wechseln (NICHT auf eine spezifische Page) → dann Token kopieren → ans Script.
**Prevention:** Script-Output erklärt jetzt klarer "Token einfuegen (NICHT Page Token, sondern User Token aus Dropdown 'Nutzertoken')".

### Bug #47 — Workflow grün, aber `queue/POST_*.json` nicht im Repo

**Wann:** Generate Carousels lief erfolgreich, aber `queue/` auf GitHub bleibt leer (404)
**Root Cause:** `permissions: contents: write` fehlte im Workflow → GITHUB_TOKEN war read-only → `git push` failed → aber `|| true` versteckte den Error → Workflow grün
**Fix:**
```yaml
permissions:
  contents: write

jobs:
  generate:
    steps:
      - uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
          persist-credentials: true   # ← KRITISCH
      ...
      - name: Commit + push
        run: |
          # KEIN "|| true" — Errors müssen sichtbar sein
          git push
```
**Prevention:** Beide Workflow-Files (generate + post) haben jetzt `permissions: contents: write` + `persist-credentials: true` + Debug-Step der `ls -la queue/` zeigt vor dem Commit.

### Bug #48 — Gemini malformed JSON crash

**Wann:** `cloud_pipeline.py` failed mit `Expecting ',' delimiter: line 29 column 164`
**Root Cause:** Gemini gibt manchmal JSON mit trailing commas zurück oder unescaped quotes in Strings (besonders bei langen Captions mit `'s` oder `"don't"`)
**Fix:** `_parse_json()` in `slide_planner.py` hat jetzt 3-stufiges Fallback:
1. Strict JSON parse
2. Trailing-comma cleanup (regex `,\s*[}\]]` → ohne Komma)
3. `json-repair` Library als finaler Fix für unescaped quotes
**Prevention:** `requirements.txt` hat `json-repair>=0.30.0` als Dependency. Auch wenn Gemini malformed JSON returned, der Plan wird trotzdem geparsed.

### Bug #49 — `ANTHROPIC_API_KEY fehlt in .env` im GitHub Actions Runner

**Wann:** Anthropic-Fallback failed weil Secret nicht gesetzt war
**Root Cause:** Workflow schreibt `ANTHROPIC_API_KEY=${{ secrets.ANTHROPIC_API_KEY }}` ins .env, aber das Secret war nicht in GitHub gesetzt → leerer Wert → Fallback-Crash
**Fix:** User muss `ANTHROPIC_API_KEY` als GitHub Secret setzen. Mit `gh secret set ANTHROPIC_API_KEY` (Wert von `https://console.anthropic.com/settings/keys`)
**Prevention:** Setup-Checklist Sektion 41.7 listet ALLE benötigten Secrets explizit auf. Ohne Anthropic ist Pipeline anfälliger; mit Anthropic 100% reliability.

### Bug #50 — `gh` Command nicht erkannt nach `winget install GitHub.cli`

**Wann:** Sofort nach Installation in derselben PowerShell-Session
**Root Cause:** PATH wird in der laufenden PowerShell-Session nicht aktualisiert; nur neue Sessions sehen den neuen PATH
**Fix:** PowerShell schließen + neu öffnen ODER manuell PATH refresh:
```powershell
$env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
```
**Prevention:** Nach jeder Installation eines CLI-Tools direkt erwähnen "Bitte PowerShell neu öffnen".

### Bug #51 — Topics.txt manuell pflegen war Bottleneck

**Wann:** Marwan musste regelmäßig 50+ Topics manuell pflegen, sonst Pipeline crashed
**Root Cause:** Keine Auto-Refill-Logik → topics.txt lief leer → cloud_pipeline.py konnte kein Topic mehr ziehen → exit
**Fix:** `refill_topics.py` (siehe Sektion 40) läuft VOR jedem Generate. Wenn topics.txt < 15 → Gemini generiert auf 50. Mit Dedupe gegen `posted/` damit keine bereits-genutzten Topics nochmal kommen.
**Prevention:** Im Workflow als erster Step direkt vor Generate. Bei neuem Brand `refill_topics.py` SYSTEM_PROMPT an Niche anpassen (siehe 40.6).

### Bug #52 — Wrong-token-confusion bei Forever-Token-Setup

**Wann:** User updated `FB_PAGE_ACCESS_TOKEN` mit Token aus Graph Explorer (Short-Lived 1h) statt mit Token aus Script-Output (Forever)
**Root Cause:** Beide Tokens beginnen mit `EAA...` und sehen optisch ähnlich aus. User dachte Graph Explorer Page Token = Script-Output Page Token.
**Fix:** Klare Unterscheidung im Guide (Sektion 43.5) + im Script-Output explizit: "Dieser Token expired NIE (derived from Long-Lived User Token). Token aus Graph Explorer wäre Short-Lived und würde nach 1h sterben."
**Prevention:** Script schreibt jetzt direkt via `gh CLI` ins Secret (wenn verfügbar) — User muss nicht mehr selber zwischen 2 Tokens wählen.

---

## 47. 📊 VOLUME MATH — Wie weit skaliert die aktuelle Architektur?

**Frage:** "10 IG Pages × 3-4 Carousels/Tag — reicht 1 API-Account pro Service?"

**Antwort:** **JA, mit massivem Headroom.** Die aktuelle Single-Account-Strategie reicht für 100+ Brands × 4 Carousels/Tag.

### 47.1 Verbrauch pro Carousel

| API | Calls/Carousel | Cost/Carousel |
|---|---|---|
| Gemini Slide-Plan | 1 | $0 (free tier) |
| Pexels Image Search | 6 (eine pro Content-Slide) | $0 |
| Together AI Outro Background | 1 | $0.04 |
| Cloudinary Uploads | 8 (eine pro Slide) | $0 (free tier) |
| Cloudinary Storage (90 days × 500KB × 8) | persistent | ~$0 |
| IG API Container + Publish | 10 (8 Children + 1 Carousel + 1 Publish) | $0 |
| FB API Photos + Album Post | 9 (8 Photos + 1 Album) | $0 |

**Total: $0.04 pro Carousel** (nur Together AI für AI-Background)

### 47.2 Skalierung — Vergleichstabelle

| Setup | Carousels/Tag | Gemini % | Pexels % | Cloudinary % | Cost/Monat |
|---|---|---|---|---|---|
| 1 Brand × 2 = 2/Tag (aktuell) | 2 | 0.13% | 1.8%/h | 0.05% | $2.40 |
| 10 Brands × 4 = 40/Tag | 40 | 2.7% | 36%/h | 1% | $48 |
| 30 Brands × 4 = 120/Tag | 120 | 8% | rate-limit ⚠️ | 3% | $144 |
| 100 Brands × 4 = 400/Tag | 400 | 27% | rate-limit ⚠️ | 10% | $480 |

### 47.3 Erste Limits die brechen würden (theoretisch)

**Pexels rate limit (200/h):**
- 10 Brands × 6 Pexels-calls × 4 Carousels = 240/h wenn ALLE Brands gleichzeitig generieren
- Fix: Generate-Cron auf 4 Stunden verteilen (matrix mit time-offsets) statt 1 Cron für alle
- Alternativ: Pixabay-Fallback aktivieren (ist schon implementiert)

**Cloudinary 25GB Storage:**
- 400 PNGs/Tag × 90 Tage × 500KB = ~17GB
- Fix: Retention auf 60 Tage senken (12GB) oder Pay-Tier ($1/GB)

**Together AI Cost:**
- Bei 400 Carousels/Tag = $16/Tag = $480/Monat
- Optimization: AI-Background nur bei Outro (1× pro Carousel), nicht bei Hero → bleibt bei aktueller Logik

### 47.4 ⚠️ NICHT-OPTIONEN — Multi-Account Anti-Pattern

User-Anfrage: "Kann ich mehrere Gemini-Accounts machen?"

**Antwort: Strikt NEIN.**

Reasons:
1. **Google ToS Verstoß** (https://policies.google.com/terms): "You may not create multiple accounts to circumvent rate limits"
2. **Detection-Mechanismen:**
   - IP-basiert (gleiche IP für mehrere Accounts = Flag)
   - Browser-Fingerprint
   - Phone-Verification (1 Nummer = 1 Account)
   - Payment-Method (1 Card = 1 Account)
3. **Ban-Risiko:** Wenn Detection greift, werden ALLE deine Accounts gebannt — auch der echte Brand-Account
4. **Volume-Math:** Sogar 100 Brands × 4 Carousels/Tag = 400 Reqs/Tag, free tier ist 1500 — d.h. **27% Auslastung auf EINEM Account**. Du hättest 3.7× Headroom auf einem einzigen Free-Tier-Account.

**Memory-Reminder:** Wenn der User in Zukunft fragt "kann ich mehrere Gemini-Accounts machen", IMMER nein sagen + Math zeigen + Anthropic-Fallback erwähnen.

### 47.5 Realistic Scaling Plan für Marwan (10+ Brands)

| Brand-Count | Setup-Aufwand | Monthly Cost | Notes |
|---|---|---|---|
| 1 (HealthRecode jetzt) | ~6 Stunden | $2.40 | DONE ✓ |
| 5 | +2.5h pro Brand = 12.5h | $12 | Multi-Tenant Refactor empfohlen |
| 10 | +12.5h für nächste 5 | $48 | Pexels-Rate-Limit beobachten |
| 20 | +25h für nächste 10 | $96 | Cron-Spread implementieren |
| 50+ | +Architektur-Refactor (Queue-Worker statt Cron) | $240+ | Eigenes Server-Setup mit RabbitMQ/Redis |

**Empfehlung Phase-Plan (siehe Memory `project_multi_brand_scaling.md`):**
- Phase 1 (jetzt): HealthRecode 30+ erfolgreiche Posts
- Phase 2 (Woche 2-3): Multi-Tenant-Refactor mit `brands/<brand>/config.yaml`
- Phase 3 (Monat 2): 5 Brands live
- Phase 4 (Monat 3-4): 10 Brands live
- Phase 5 (Monat 6+): Video-Pipeline (TikTok/Reels/Shorts)

---

## 48. ✅ FINAL SETUP-CHECKLISTE für neue Brand (Quick-Reference)

Wenn der User sagt "neuer Brand X", führe ihn DIESE Liste durch (ohne lange Diskussion — einfach machen):

```
[ ] 1. Brand-Name + Niche + Farbe geklärt
[ ] 2. IG-Account existiert + Business-Modus + FB-Page verknüpft
[ ] 3. Warm-Up-Strategie geklärt (1 Woche manuell vor Auto)
[ ] 4. Meta-App reused (1 App reicht für alle Brands)
[ ] 5. IG_USER_ID + IG_USER_ACCESS_TOKEN via Graph Explorer geholt
[ ] 6. python get_forever_fb_token.py → FB_PAGE_ID + FB_PAGE_ACCESS_TOKEN (Forever)
[ ] 7. GitHub Secrets via gh CLI gesetzt (Brand-suffix wenn Multi-Tenant)
[ ] 8. brands/<brand>/config.yaml mit Brand-Style
[ ] 9. brands/<brand>/topics.txt mit 5-10 initialen Topics
[ ] 10. refill_topics.py SYSTEM_PROMPT an neue Niche angepasst (falls anders als Medical)
[ ] 11. Test-Generate manuell triggern (count=1)
[ ] 12. Wenn Generate grün: Test-Post manuell triggern
[ ] 13. IG + FB visuell checken (beide Posts sichtbar)
[ ] 14. Auto-Cron Schedule überprüfen (verschoben falls Brand andere Zeitzone bedient)
[ ] 15. Email-Alerts werden empfangen (test mit absichtlichem Fail)
```

**Wenn alle 15 Haken: Brand ist fully live & autonomous.**

