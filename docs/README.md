# Dokumentation

| Datei | Inhalt |
| --- | --- |
| `PRAXISARBEIT.md` | Lösungsdokument für die Abgabe (Management Summary, Anforderungen, User Manual, API, Architektur mit Diagrammen, Testprotokoll, Reflexion) |
| `INSTALL.md` | Installationsanleitung (lokal mit venv/SQLite, lokal mit Docker, produktiver Server) |
| `ARCHITEKTUR.md` | Detaillierte Architektur und Begründung |
| `DEPLOYMENT.md` | Deployment-Anleitung für die Lab-VM |

## PDF erzeugen

Das Lösungsdokument enthält Mermaid-Diagramme und ist auf das ipso!-Leitfaden-
Layout ausgelegt (Arial 11 pt, A4-Ränder, Inhaltsverzeichnis, Seitenzahlen).
Empfohlener Weg über die mitgelieferten Skripte (siehe
[`../scripts/build-praxisarbeit-pdf.md`](../scripts/build-praxisarbeit-pdf.md)):

```bash
# einmalig: PUPPETEER_SKIP_DOWNLOAD=1 npm install --no-save puppeteer-core
python scripts/md2html.py docs/PRAXISARBEIT.md build/PRAXISARBEIT.html
node   scripts/print-pdf.mjs build/PRAXISARBEIT.html build/PRAXISARBEIT.pdf
```

Ohne Kommandozeile: `build/PRAXISARBEIT.html` im Browser öffnen und **Drucken →
Als PDF speichern** (A4).

Vor der Abgabe im Dokument ergänzen: Titelblatt-Platzhalter (Adresse, E-Mail,
Klasse, Abgabedatum, Examinator/in), Management Summary und Reflexion in eigenen
Worten, KI-Deklaration prüfen und die **Eigenständigkeitserklärung unterschreiben**.
GitHub-URL: https://github.com/harpf/FlightDeck-DG-Hub · Live-URL:
https://lab10.ifalabs.org
