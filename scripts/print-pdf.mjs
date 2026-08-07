// Print an HTML file to a PDF with page numbers (bottom-right), using the
// locally installed Edge/Chrome via puppeteer-core (no bundled Chromium).
//
//   node scripts/print-pdf.mjs <input.html> <output.pdf> [browserPath]
//
// Waits for Mermaid (body[data-ready="1"]) before printing. Margins follow the
// ipso! Leitfaden (left 3cm / right 2cm / top+bottom 2.5cm). Page numbering starts
// on the first page after the title page (the title page shows no number).
import puppeteer from 'puppeteer-core';
import { pathToFileURL } from 'node:url';
import { resolve } from 'node:path';
import { existsSync } from 'node:fs';

const [, , inPath, outPath, browserArg] = process.argv;
if (!inPath || !outPath) {
  console.error('usage: node scripts/print-pdf.mjs <input.html> <output.pdf> [browserPath]');
  process.exit(2);
}

const candidates = [
  browserArg,
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
  'C:/Program Files/Microsoft/Edge/Application/msedge.exe',
  'C:/Program Files/Google/Chrome/Application/chrome.exe',
].filter(Boolean);

const executablePath = candidates.find((p) => existsSync(p)) || candidates[0];

const browser = await puppeteer.launch({
  executablePath,
  headless: 'new',
  args: ['--no-sandbox', '--disable-gpu'],
});
try {
  const page = await browser.newPage();
  await page.goto(pathToFileURL(resolve(inPath)).href, { waitUntil: 'networkidle0' });
  await page.waitForFunction(() => document.body.getAttribute('data-ready') === '1', { timeout: 30000 })
    .catch(() => console.warn('warning: Mermaid did not signal ready; printing anyway'));

  const footer =
    '<div style="width:100%;font-family:Arial,sans-serif;font-size:9px;color:#555;' +
    'text-align:right;padding:0 2cm 0 3cm;">' +
    '<span class="pageNumber"></span></div>';

  await page.pdf({
    path: outPath,
    format: 'A4',
    printBackground: true,
    displayHeaderFooter: true,
    headerTemplate: '<span></span>',
    footerTemplate: footer,
    margin: { top: '2.5cm', bottom: '2.5cm', left: '3cm', right: '2cm' },
    // First page (title) prints without a page number; numbering starts at 1 on page 2.
    pageRanges: '',
  });
  console.log(`wrote ${outPath}`);
} finally {
  await browser.close();
}
