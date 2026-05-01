# Auto-Posting Pipeline — Setup-Anleitung

Ziel: Vollautomatischer Workflow von Topic-Idee bis Instagram-Post.
Pipeline: `Topic → Slide-Plan + Bild-Prompts → Higgsfield + Gemini Bilder → HTML-Carousel → 1080×1350 PNG-Export → Cloudinary Upload → Instagram Graph API Posting (mit Bestätigung)`

---

## Übersicht: Was du brauchst

| # | Service | Wofür | Kostenlos? |
|---|---------|-------|------------|
| 1 | Instagram Business/Creator-Account | Posting via API | Ja |
| 2 | Facebook-Seite (verknüpft mit IG) | Voraussetzung für IG Graph API | Ja |
| 3 | Meta for Developers App | Access Token + API-Berechtigungen | Ja |
| 4 | Higgsfield API-Key | AI-Bilder generieren | Plan-abhängig |
| 5 | Google Gemini API-Key | Nano Banana Pro Bilder | Ja (Free Tier) |
| 6 | Cloudinary Account | Bilder öffentlich hosten | Ja (Free Tier) |

---

## Schritt 1 — Instagram auf Business/Creator umstellen

Falls dein IG-Account noch privat ist:

1. Instagram-App öffnen → Profil → Menü (≡) oben rechts → **Einstellungen und Aktivität**
2. **Kontotyp und Tools** → **Auf professionelles Konto umstellen**
3. Wähle eine Kategorie (z.B. "Gesundheits- und Wellness-Website" oder "Bildung")
4. Wähle **Creator** oder **Business** (beides funktioniert für die API)
5. Verknüpfe den Account mit einer **Facebook-Seite** (in Schritt 2 erstellen, falls noch keine)

**Verifizieren:** Wenn du in den IG-Einstellungen "Business-Tools" siehst → fertig.

---

## Schritt 2 — Facebook-Seite erstellen (falls noch nicht vorhanden)

Die Instagram Graph API braucht eine verknüpfte Facebook-Seite — auch wenn du Facebook selbst nie nutzt.

1. https://www.facebook.com/pages/create öffnen
2. Seitenname (z.B. dein Brand-Name) + Kategorie ("Bildung" oder "Gesundheit/Schönheit") eingeben
3. Seite erstellen (kostenlos)
4. In den **Seiteneinstellungen** → **Verlinkte Konten** → Instagram-Account verbinden

**Verifizieren:** Wenn du in den IG-Einstellungen unter "Verknüpfte Konten" deine FB-Seite siehst → fertig.

---

## Schritt 3 — Meta Developer App + Access Token

Das ist der aufwändigste Schritt, aber einmal gemacht.

1. https://developers.facebook.com → einloggen mit deinem FB-Account
2. **Meine Apps** → **App erstellen**
3. App-Typ: **Business** wählen
4. Name: z.B. "Medical Auto Poster" — Speichern
5. Im App-Dashboard: **Produkte hinzufügen** → **Instagram Graph API** aktivieren
6. Auch **Facebook Login for Business** aktivieren

### Access Token erstellen

7. Im linken Menü: **Tools** → **Graph API Explorer**
8. Oben rechts deine App auswählen
9. **Get User Access Token** klicken
10. Folgende **Permissions** ankreuzen:
    - `instagram_basic`
    - `instagram_content_publish`
    - `instagram_manage_insights` (optional, für Statistiken)
    - `pages_show_list`
    - `pages_read_engagement`
    - `business_management`
11. **Generate Access Token** → bestätigen → kurzlebiges Token wird angezeigt
12. Token kopieren

### Token in Long-Lived umwandeln (60 Tage gültig)

Im Browser folgenden URL aufrufen (Felder ersetzen):
```
https://graph.facebook.com/v21.0/oauth/access_token?
  grant_type=fb_exchange_token&
  client_id={DEINE_APP_ID}&
  client_secret={DEIN_APP_SECRET}&
  fb_exchange_token={KURZLEBIGES_TOKEN}
```
Die Antwort enthält das `access_token` (60 Tage gültig). Das ist dein **Long-Lived Token**.

### Instagram Business Account ID herausfinden

Im Graph API Explorer:
- `GET me/accounts` → liefert deine Facebook-Seiten + IDs
- Nimm die `id` deiner Seite, dann: `GET {page-id}?fields=instagram_business_account`
- Die `id` darin = deine **Instagram Business Account ID**

**Was du an mich weitergeben sollst:**
```
META_APP_ID = ...
META_APP_SECRET = ...
META_LONG_LIVED_TOKEN = ...
IG_BUSINESS_ACCOUNT_ID = ...
FB_PAGE_ID = ...
```

---

## Schritt 4 — Replicate API-Token (primäre Bildquelle)

Wir nutzen **Replicate** mit FLUX-Modellen statt Gemini, weil Gemini Free Tier zu limitiert ist.

1. https://replicate.com/signin → mit GitHub einloggen (oder normaler Account)
2. Beim ersten Login bekommst du **$1 Trial-Credit** (reicht für ~17 Pro-Bilder oder 300+ Schnell-Bilder)
3. https://replicate.com/account/api-tokens → **Create token** → "Medical-Insta" als Name
4. Token kopieren (beginnt mit `r8_...`)

```
REPLICATE_API_TOKEN = r8_...
```

**Modelle, die wir nutzen werden:**
- `black-forest-labs/flux-1.1-pro-ultra` — Hero-Bilder (~$0,06/Bild)
- `black-forest-labs/flux-schnell` — Hintergründe, Fülltext-Slides (~$0,003/Bild)

Geschätzte Kosten: ~$0,30 pro Carousel mit 7 Bildern wenn alle Pro Ultra. Mit Schnell-Mix: ~$0,10/Carousel.

**Test-Befehl** nach dem Eintragen in `.env`:
```
python verify_replicate.py
```

---

## Schritt 5 — Google Gemini API-Key (Nano Banana Pro)

Komplett kostenlos im Free Tier.

1. https://aistudio.google.com → mit Google-Account einloggen
2. **Get API Key** (oben links)
3. **Create API Key in new project** klicken
4. Key kopieren

```
GEMINI_API_KEY = ...
```

Modell, das wir nutzen: `gemini-2.5-flash-image` (Nano Banana Pro).

---

## Schritt 6 — Cloudinary Account

1. https://cloudinary.com/users/register/free → kostenlosen Account erstellen
2. Im Dashboard oben siehst du:
   - **Cloud Name**
   - **API Key**
   - **API Secret**

```
CLOUDINARY_CLOUD_NAME = ...
CLOUDINARY_API_KEY = ...
CLOUDINARY_API_SECRET = ...
```

---

## Was passiert nach dem Setup

Wenn du mir alle Keys/Tokens in einer Nachricht schickst (kein Foto, einfach als Text), baue ich:

1. **`config.py`** — speichert die Keys lokal (nicht ins Memory, nur im Projekt-Ordner)
2. **`generate_carousel.py`** — Pipeline-Skript: Topic eingeben → komplettes Carousel (HTML + PNG-Export) entsteht
3. **`post_carousel.py`** — postet ein fertiges Carousel auf Instagram (mit Caption + Hashtags)
4. **`run.py`** — Wrapper: ruft alles auf und zeigt dir am Ende Preview + Caption zur Bestätigung

Workflow danach im Chat:
> "Mach ein Carousel zu 'Was passiert bei einem Herzinfarkt'"
> → Ich generiere alles, zeige dir die fertigen Slides + Caption
> → Du sagst "Posten" → es geht live

---

## Sicherheits-Hinweise

- **API-Keys niemals öffentlich teilen** (kein Screenshot in Stories, kein GitHub-Push). Sie geben Zugriff auf deinen Account.
- Long-Lived Token ist **60 Tage** gültig — wir bauen einen Refresh-Mechanismus.
- Ich poste nichts ohne deine explizite Bestätigung im Chat — auch wenn die Pipeline vollautomatisch läuft.
- Bei Verlust eines Keys: im jeweiligen Dashboard rotieren (alten löschen, neuen erstellen).

---

## Zeitschätzung

- Schritt 1+2 (IG + FB-Seite): ~10 Min
- Schritt 3 (Meta Dev App): ~30 Min (technischer Teil)
- Schritt 4-6 (API-Keys): je ~2 Min

**Insgesamt: ~45–60 Min für das einmalige Setup.** Danach ist alles automatisch.
