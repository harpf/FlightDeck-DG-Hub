# Lösungsdokument als PDF bauen (inkl. Mermaid, Layout, Seitenzahlen)

Erzeugt aus `docs/PRAXISARBEIT.md` ein Leitfaden-nahes PDF: Arial 11 pt (Tabellen
10 pt), A4-Ränder 3/2/2.5/2.5 cm, Blocksatz, automatisches Inhaltsverzeichnis,
gerenderte Mermaid-Diagramme und **Seitenzahlen** (unten rechts). Benötigt
**Python**, **Node.js** und einen installierten **Edge/Chrome** (kein
pandoc/LaTeX, keine gebündelte Chromium-Instanz).

## Einmalig: Node-Abhängigkeit

```bash
# lädt kein Chromium herunter – nutzt das installierte Edge/Chrome
PUPPETEER_SKIP_DOWNLOAD=1 npm install --no-save puppeteer-core
```

## 1. Markdown → self-contained HTML

```bash
python scripts/md2html.py docs/PRAXISARBEIT.md build/PRAXISARBEIT.html
```

## 2. HTML → PDF (mit Seitenzahlen)

```bash
node scripts/print-pdf.mjs build/PRAXISARBEIT.html build/PRAXISARBEIT.pdf
# optional expliziter Browser-Pfad als 3. Argument:
# node scripts/print-pdf.mjs build/PRAXISARBEIT.html build/PRAXISARBEIT.pdf "C:/Program Files/Google/Chrome/Application/chrome.exe"
```

Das Skript wartet auf das Mermaid-Rendering (`body[data-ready="1"]`), setzt die
Ränder gemäss Leitfaden und druckt die Seitenzahl über die Fusszeilen-Vorlage.

## Hinweise / Feinschliff

- **Titelblatt-Seitenzahl:** Die Zählung beginnt aktuell auf Seite 1 (Titelblatt).
  Der Leitfaden empfiehlt, erst ab der Seite *nach* dem Titelblatt zu nummerieren –
  ein optionaler Feinschliff (z. B. finaler Durchgang in Word).
- **Ohne Kommandozeile:** `build/PRAXISARBEIT.html` im Browser öffnen und
  **Drucken → Als PDF speichern** (A4). Layout/Seitenumbrüche stecken im HTML;
  Seitenzahlen kommen dann aus dem Druckdialog.
- `build/` und `node_modules/` sind in `.gitignore` – das PDF wird frisch erzeugt
  und auf Campus hochgeladen, nicht eingecheckt.
