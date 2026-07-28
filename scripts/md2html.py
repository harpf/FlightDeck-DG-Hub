#!/usr/bin/env python3
"""Render a Markdown file (with ```mermaid blocks) to a self-contained HTML page.

The HTML renders Markdown via marked and Mermaid diagrams client-side, styled for
A4 print. Open it in a browser and "Print -> Save as PDF", or drive a headless
Chromium/Edge with --print-to-pdf (see scripts/build-praxisarbeit-pdf.md).

Usage:  python scripts/md2html.py <input.md> <output.html>
"""
import json
import sys
from pathlib import Path

TEMPLATE = """<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<title>__TITLE__</title>
<style>
  @page { size: A4; margin: 18mm 16mm; }
  html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  body { font-family: -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
         font-size: 10.5pt; line-height: 1.5; color: #1a1a1a; max-width: 190mm; margin: 0 auto; }
  h1 { font-size: 20pt; border-bottom: 2px solid #2e7d32; padding-bottom: 4px; }
  h2 { font-size: 15pt; margin-top: 1.4em; border-bottom: 1px solid #d8e0d8; padding-bottom: 2px; }
  h3 { font-size: 12.5pt; margin-top: 1.2em; }
  h4 { font-size: 11pt; }
  h1, h2, h3, h4 { break-after: avoid; }
  table { border-collapse: collapse; width: 100%; margin: 0.6em 0; font-size: 9.5pt; }
  th, td { border: 1px solid #cbd5cb; padding: 4px 7px; text-align: left; vertical-align: top; }
  th { background: #eef4ee; }
  code { background: #f2f4f2; padding: 1px 4px; border-radius: 3px; font-size: 9pt; }
  pre { background: #f7f9f7; border: 1px solid #e2e8e2; border-radius: 5px; padding: 8px 10px;
        overflow-x: auto; font-size: 8.5pt; }
  pre code { background: none; padding: 0; }
  pre.mermaid { background: #fff; border: none; text-align: center; break-inside: avoid; }
  pre.mermaid svg { max-width: 100%; height: auto; }
  blockquote { border-left: 3px solid #b9c9b9; margin: 0.6em 0; padding: 0.1em 0.9em; color: #444; }
  a { color: #1b5e20; text-decoration: none; word-break: break-all; }
  table, pre, blockquote, img { break-inside: avoid; }
</style>
</head>
<body>
<div id="content"></div>
<script type="application/json" id="md">__MD_JSON__</script>
<script src="https://cdn.jsdelivr.net/npm/marked@4.3.0/marked.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js"></script>
<script>
  const md = JSON.parse(document.getElementById('md').textContent);
  marked.use({ renderer: {
    code(code, infostring) {
      if ((infostring || '').trim() === 'mermaid') {
        const esc = code.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        return '<pre class="mermaid">' + esc + '</pre>';
      }
      return false;
    }
  }});
  document.getElementById('content').innerHTML = marked.parse(md);
  mermaid.initialize({ startOnLoad: false, theme: 'neutral', securityLevel: 'loose' });
  mermaid.run({ querySelector: 'pre.mermaid' })
    .then(() => { document.body.setAttribute('data-ready', '1'); })
    .catch((e) => { console.error(e); document.body.setAttribute('data-ready', 'error'); });
</script>
</body>
</html>
"""


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: python scripts/md2html.py <input.md> <output.html>", file=sys.stderr)
        return 2
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    md = src.read_text(encoding="utf-8")
    title = md.splitlines()[0].lstrip("# ").strip() if md.strip() else src.stem
    # Embed as JSON so any characters survive without breaking the HTML/JS.
    html = (
        TEMPLATE
        .replace("__TITLE__", title)
        .replace("__MD_JSON__", json.dumps(md))
    )
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(html, encoding="utf-8")
    print(f"wrote {dst} ({len(html)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
