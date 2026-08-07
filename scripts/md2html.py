#!/usr/bin/env python3
"""Render a Markdown file (with ```mermaid blocks) to a self-contained HTML page.

The HTML renders Markdown via marked and Mermaid diagrams client-side, styled to
the ipso! Leitfaden layout (Arial 11pt, tables 10pt, A4 margins 3/2/2.5/2.5 cm,
justified text, page numbers) and generates an Inhaltsverzeichnis from the
``[[TOC]]`` marker. Open it in a browser and "Print -> Save as PDF", or drive a
headless Chromium/Edge with --print-to-pdf (see scripts/build-praxisarbeit-pdf.md).

Usage:  python scripts/md2html.py <input.md> <output.html>
"""
import json
import sys
from pathlib import Path

TEMPLATE = r"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<title>__TITLE__</title>
<style>
  /* --- Leitfaden layout: A4, margins left 3cm / right 2cm / top+bottom 2.5cm --- */
  @page { size: A4; margin: 2.5cm 2cm 2.5cm 3cm; }
  @page { @bottom-right { content: counter(page); font-family: Arial, sans-serif; font-size: 9pt; color: #555; } }
  html { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  body { font-family: Arial, Helvetica, sans-serif; font-size: 11pt; line-height: 1.3;
         color: #111; text-align: justify; hyphens: auto; }
  h1 { font-size: 22pt; margin: 0 0 6px; }
  h2 { font-size: 15pt; margin: 1.3em 0 0.4em; border-bottom: 1px solid #d8e0d8; padding-bottom: 2px; }
  h3 { font-size: 12.5pt; margin: 1.1em 0 0.3em; }
  h4 { font-size: 11pt; margin: 0.9em 0 0.3em; }
  h1, h2, h3, h4 { break-after: avoid; text-align: left; }
  p { margin: 0.5em 0; }
  table { border-collapse: collapse; width: 100%; margin: 0.5em 0; font-size: 10pt; text-align: left; }
  th, td { border: 1px solid #b9c4b9; padding: 4px 7px; vertical-align: top; }
  th { background: #eef4ee; }
  code { background: #f2f4f2; padding: 1px 4px; border-radius: 3px; font-size: 9.5pt; }
  pre { background: #f7f9f7; border: 1px solid #e2e8e2; border-radius: 5px; padding: 8px 10px;
        overflow-x: auto; font-size: 8.5pt; text-align: left; }
  pre code { background: none; padding: 0; }
  pre.mermaid { background: #fff; border: none; text-align: center; break-inside: avoid; }
  pre.mermaid svg { max-width: 100%; height: auto; }
  blockquote { border-left: 3px solid #b9c9b9; margin: 0.6em 0; padding: 0.1em 0.9em; color: #444; }
  a { color: #1b5e20; text-decoration: none; word-break: break-word; }
  em { color: #555; }                              /* figure/table captions */
  table, pre, blockquote { break-inside: avoid; }

  /* --- Title page --- */
  .titlepage { text-align: center; padding-top: 3cm; }
  .titlepage h1 { font-size: 26pt; }
  .titlepage h2 { border: none; font-size: 14pt; font-weight: normal; color: #333; text-align: center; }
  .titlepage table { width: auto; margin: 0 auto; font-size: 11pt; text-align: left; }
  .titlepage th, .titlepage td { border: none; padding: 2px 10px; }

  /* --- Page breaks --- */
  .pagebreak { break-after: page; page-break-after: always; height: 0; }

  /* --- Table of contents --- */
  .toc ul { list-style: none; margin: 0; padding: 0; }
  .toc li { margin: 2px 0; }
  .toc li.h3 { padding-left: 1.6em; font-size: 10.5pt; }
  .toc a { color: #111; }

  /* --- Eigenständigkeitserklärung box --- */
  .declaration { border: 1px solid #333; padding: 14px 16px; margin: 0.6em 0; text-align: left; }
</style>
</head>
<body>
<div id="content"></div>
<script type="application/json" id="md-src">__MD_JSON__</script>
<script src="https://cdn.jsdelivr.net/npm/marked@4.3.0/marked.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js"></script>
<script>
  const md = JSON.parse(document.getElementById('md-src').textContent);
  marked.use({ renderer: {
    code(code, infostring) {
      if ((infostring || '').trim() === 'mermaid') {
        const esc = code.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
        return '<pre class="mermaid">' + esc + '</pre>';
      }
      return false;
    }
  }});
  const content = document.getElementById('content');
  content.innerHTML = marked.parse(md);

  // Build the Inhaltsverzeichnis from headings (skip the title page + the TOC heading).
  const toc = document.createElement('div');
  toc.className = 'toc';
  const ul = document.createElement('ul');
  let i = 0;
  content.querySelectorAll('h2, h3').forEach((h) => {
    if (h.closest('.titlepage')) return;
    const text = h.textContent.trim();
    if (text === 'Inhaltsverzeichnis') return;
    const id = 'sec-' + (i++);
    h.id = id;
    const li = document.createElement('li');
    li.className = h.tagName.toLowerCase();
    const a = document.createElement('a');
    a.href = '#' + id;
    a.textContent = text;
    li.appendChild(a);
    ul.appendChild(li);
  });
  toc.appendChild(ul);
  content.querySelectorAll('p').forEach((p) => {
    if (p.textContent.trim() === '[[TOC]]') p.replaceWith(toc);
  });

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
    title = "FlightDeck DG Hub – Praxisarbeit"
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
