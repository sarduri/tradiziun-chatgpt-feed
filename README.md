# tradiziun-chatgpt-feed

Erzeugt täglich den Produktfeed (OpenAI-Format, JSONL) aus dem öffentlichen `/products.json` von https://tradiziun.ch
und veröffentlicht ihn über GitHub Pages: `https://sarduri.github.io/tradiziun-chatgpt-feed/feed.jsonl`

- Skript: `tools/chatgpt_feed.py` (nur Python-Standardbibliothek)
- Workflow: `.github/workflows/chatgpt-feed.yml` (täglich + manuell startbar)
- Enthält ausschliesslich öffentliche Produktdaten.
