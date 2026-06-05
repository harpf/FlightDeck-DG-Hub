# Dokumentation

| Datei | Inhalt |
| --- | --- |
| `PRAXISARBEIT.md` | Lösungsdokument für die Abgabe (Management Summary, Anforderungen, User Manual, API, Architektur mit Diagrammen, Testprotokoll, Reflexion) |
| `INSTALL.md` | Installationsanleitung (lokal mit venv/SQLite, lokal mit Docker, produktiver Server) |
| `ARCHITEKTUR.md` | Detaillierte Architektur und Begründung |
| `DEPLOYMENT.md` | Deployment-Anleitung für die Lab-VM |

## PDF erzeugen

Das Lösungsdokument enthält Mermaid-Diagramme. Möglichkeiten zur PDF-Erzeugung:

- **VS Code:** Erweiterung „Markdown Preview Mermaid Support“ + „Markdown PDF“.
- **Typora:** öffnet `.md` mit gerenderten Mermaid-Diagrammen, Export → PDF.
- **pandoc** (mit Diagramm-Filter):
  ```bash
  npm install -g @mermaid-js/mermaid-cli mermaid-filter
  pandoc docs/PRAXISARBEIT.md -o Praxisarbeit.pdf -F mermaid-filter
  ```

Vor der Abgabe: `<GitHub-URL eintragen>`, Live-URL und Admin-Zugangsdaten im
Dokument ergänzen.
