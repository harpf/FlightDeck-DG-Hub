# Lösungsdokument als PDF bauen (inkl. Mermaid-Diagramme)

Erzeugt aus `docs/PRAXISARBEIT.md` ein druckfertiges PDF. Die Mermaid-Diagramme
werden clientseitig zu SVG gerendert; ein headless Chromium/Edge druckt die
Seite nach PDF. Benötigt nur **Python** und einen **Chromium-basierten Browser**
(Edge oder Chrome) – kein pandoc/LaTeX.

## 1. Markdown → self-contained HTML

```bash
python scripts/md2html.py docs/PRAXISARBEIT.md build/PRAXISARBEIT.html
```

## 2. HTML → PDF (headless Edge/Chrome)

Windows (Edge), aus dem Repo-Root:

```powershell
$edge = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
$abs  = (Resolve-Path build).Path -replace '\\','/'
& $edge --headless=new --disable-gpu --no-pdf-header-footer `
  --run-all-compositor-stages-before-draw --virtual-time-budget=20000 `
  --print-to-pdf="$abs/PRAXISARBEIT.pdf" "file:///$abs/PRAXISARBEIT.html"
```

Linux/macOS (Chrome/Chromium – Pfad ggf. anpassen):

```bash
chrome --headless=new --disable-gpu --no-pdf-header-footer \
  --run-all-compositor-stages-before-draw --virtual-time-budget=20000 \
  --print-to-pdf="$PWD/build/PRAXISARBEIT.pdf" "file://$PWD/build/PRAXISARBEIT.html"
```

`--virtual-time-budget` gibt Mermaid Zeit zum Rendern; `--no-pdf-header-footer`
entfernt die Standard-Kopf-/Fusszeilen des Browsers.

## 3. Alternative ohne Kommandozeile

`build/PRAXISARBEIT.html` einfach im Browser öffnen und **Drucken → Als PDF
speichern** (A4). Das Print-CSS (A4-Ränder, Seitenumbrüche) ist bereits im HTML.

> `build/` ist in `.gitignore` – das PDF wird also nicht eingecheckt, sondern
> jeweils frisch erzeugt und auf Complesis hochgeladen.
