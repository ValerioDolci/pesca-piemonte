# Struttura del progetto — Pesca Piemonte

## Layout
```
pesca-piemonte/
├── CLAUDE.md            # stato progetto + regole + decisioni (fonte di verità operativa)
├── README.md           # descrizione pubblica
├── SOURCES.md          # inventario fonti ufficiali (ogni regola → fonte)
├── STRUCTURE.md        # questo file
├── PROMPT_TRATTO.md    # doc del tool subagente per geolocalizzare estremi
│
├── data/
│   ├── sources/        # PDF ufficiali scaricati (NON modificare) — per provincia + regione
│   └── processed/      # dati derivati
│       ├── <prov>/zone_<prov>.json        # INVENTARIO zone (testo+regola+fonte) — fonte dati
│       ├── <prov>/tracts_<prov>.geojson   # GEOMETRIE (Line/MultiLine/Point) per la mappa
│       ├── <prov>/osm_waterways.json      # rete idrografica OSM (cache, rigenerabile)
│       ├── <prov>/<prov>_text.txt         # testo estratto dai PDF
│       ├── comuni_coords.json             # cache geocoding comuni (chiave "Comune|Prov")
│       ├── geocode_cache.json             # cache geocoding luoghi (subagente/sonnet)
│       ├── province_boundaries.json       # confini province (OSM) per le aree-licenza
│       ├── regione/regole_generali.json   # baseline regionale (specie/periodi/misure)
│       ├── tutti_i_tratti.csv / .json     # DATASET CONSOLIDATO (export di tutte le zone)
│
├── mappa/index.html    # mappa generata (output di build_map.py)
├── site/               # repo PUBBLICO GitHub Pages (solo index.html + README) — git separato
└── tmp/                # scratch (gitignored, svuotabile)
```

## Script (pipeline) — ordine d'uso
1. **`resolve_tracts.py`** — motore geometrico base: OSM + hint `estremi` deterministici (confluenza/sorgente/intero/luogo/offset) → taglia tratto. Libreria usata dagli altri.
2. **`auto_estremi.py`** `<Prov>` — estrae hint `estremi` dal testo italiano dei tratti (per i casi facili).
3. **`tract_agent_tool.py`** `prep|apply <Prov> <ID>` — tool subagente (prep input / apply output). `apply_data` riusato da sonnet_resolve.
4. **`sonnet_resolve.py`** `<Prov> [--markers|ID...] [--web]` — risolve gli estremi chiamando Sonnet via `claude --print` (subscription). GATE qualità (scarta estremi >250m / tratti <15m). **Strumento principale Fase B.**
5. **`whole_rivers.py`** `[Prov]` — disegna gli interi corsi (salmonicole/DDEP) come MultiLineString (tutti i segmenti OSM, no stitching).
6. **`build_map.py`** → `mappa/index.html` — assembla la mappa: tratti (geojson) + marker fallback + interi-corsi + confini provinciali + UI mobile.

## Rigenerare la mappa dopo modifiche ai dati
```
python3 build_map.py
cp mappa/index.html site/index.html
cd site && git add -A && git commit -m "..." && git push   # → GitHub Pages
```

## Note
- Python: usare il venv `/Users/flaviacasini/claude-bot/venv/bin/python3`.
- `claude --print --model sonnet` richiede `/opt/homebrew/bin` nel PATH (node).
- I file `osm_waterways.json` sono grandi ma cache rigenerabile (Overpass, area ISO `["ISO3166-2"="IT-XX"]`).
