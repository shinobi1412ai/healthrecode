# Medical Auto-Posting Pipeline

Vollautomatischer Workflow von Topic-Idee bis Instagram-Post.

## Aktueller Status

Die Pipeline wird Schritt für Schritt aufgebaut. Aktuell:

| Modul | Status |
|-------|--------|
| Setup-Anleitung | erledigt → siehe `auto-posting-setup.md` |
| Gemini API-Key | gespeichert in `.env` |
| Gemini Verify-Skript | bereit zum Testen → `verify_gemini.py` |
| Andere Keys (Meta, Cloudinary, Higgsfield) | ausstehend |
| Slide-Plan-Generator | in Arbeit |
| Bildgenerierung-Modul | in Arbeit |
| HTML-Carousel + PNG-Export | in Arbeit |
| Cloudinary Upload | in Arbeit |
| Instagram Posting | in Arbeit |
| `run.py` Wrapper | in Arbeit |

## Erstes Mal: Setup auf deinem PC

1. Terminal/PowerShell im Projekt-Ordner öffnen:
   ```
   cd C:\Users\myshi\Documents\Claude\Projects\Medical-Stuff
   ```

2. Python-Pakete installieren (einmalig):
   ```
   pip install -r requirements.txt
   ```

3. Gemini-Key testen:
   ```
   python verify_gemini.py
   ```

   **Erwartung:** das Skript schreibt eine Datei `test_image.png` mit einem AI-generierten anatomischen Herz-Bild. Falls Fehler kommen, schick mir die Ausgabe im Chat.

## Dateien

- `.env` — alle API-Keys (NIE teilen, NIE auf GitHub pushen)
- `.gitignore` — schützt `.env` automatisch falls Git
- `auto-posting-setup.md` — komplette Setup-Anleitung für alle Services
- `requirements.txt` — Python-Abhängigkeiten
- `verify_gemini.py` — Smoke-Test für Gemini API
- `README.md` — diese Datei
