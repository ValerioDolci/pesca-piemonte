# PIPELINE — aggiungere una nuova area (provincia/regione)

Flusso end-to-end per portare una nuova area dalla fonte ufficiale alla mappa.
Diviso in **lavoro umano/LLM** (1-2: la parte difficile = il dato) e **automatico** (3-7).

Convenzione: `<Area>` = nome con maiuscola usato in `provincia` dei JSON (es. `Lombardia`, `Imperia`).
Le cartelle dati usano `<area>` minuscolo: `data/processed/<area>/` e `data/sources/<area>/`.

---

## 1. Fonte ufficiale (umano)
- Trovare il documento ufficiale (vademecum provinciale / carta ittica regionale / decreto zone).
  Preferire **regione con fonte unica** (es. Liguria) a province frammentate.
- Scaricare in `data/sources/<area>/<nome>.pdf`. Tracciare in `SOURCES.md` (file, ente, data, validità).
- Estrarre il testo: `pdftotext` o `pypdf`. Salvare `data/processed/<area>/<area>_text.txt`.
- **Gotcha**: alcuni siti rispondono **403** → aggiungere header `Referer` + User-Agent browser.
  Se la fonte non è pubblica (sito dismesso) è un **gap onesto** → documentarlo (vedi Novara/Asti).

## 2. Estrazione zone + geocodifica comuni (umano/LLM)
- Produrre `data/processed/<area>/zone_<area>.json`:
  ```json
  {"provincia":"<Area>","fonte":"...","fonte_file":"data/sources/...","zone":[
    {"id":"XX-PROT-01","tipo":"protezione","comune":"Nome",
     "corso_acqua":"Torrente Y","tratto":"dalla confluenza ... al ponte ...",
     "regola":"divieto assoluto","fonte_pagina":12,
     "estremi":{"da":{"confluenza":"Z"},"a":{"luogo":"Frazione W, Comune, <Area>"}}}
  ]}
  ```
  - `tipo` ∈ protezione · divieto · no_kill · no_kill_cmto · turistica · ddep · concessione · riserva · campo_gara · salmonicola
  - `estremi` (opzionale ma molto utile): hint curati per il taglio deterministico —
    `confluenza`/`sorgente`/`luogo`/`intero`/`offset_m`/`punto`.
  - `comune` può essere vuoto se la zona elenca i comuni solo nel testo (es. DDEP "nei Comuni di X,Y").
    In quel caso il marker cade sul **centroide del corso** (vedi build_map.river_centroid).
- Geocodificare i comuni nuovi in `data/processed/comuni_coords.json` (chiave `"Comune|<Area>"`, Nominatim 1 req/s).

## 3. Download OSM (automatico)
- Idrografia: Overpass `area["ISO3166-2"="<ISO>"]` → `data/processed/<area>/osm_waterways.json`.
- Confine: relation per ISO → aggiungere a `data/processed/province_boundaries.json`.
- **ISO** in `road_bridges.ISO` (IT-TO/BI/NO/VB/VC/CN/AL/IT-23...). Per una nuova area aggiungere la voce lì.

## 4-6. Geometria + QA + build (automatico)  →  `./run_region.sh <Area>`
Ordine (dal più economico/affidabile al più costoso):
1. `auto_estremi.py <Area>`     — estrae hint estremi dal testo
2. `resolve_tracts.py <Area>`   — taglio deterministico sulla linea OSM (gate: snap>250m o <15m → marker)
3. `road_bridges.py --apply`    — incrocio reale strada×fiume (gate: incrocio <6km dal comune)
4. `place_resolver.py --apply`  — frazioni/località via Nominatim (gate: <8km comune, <400m fiume)
5. `sonnet_resolve.py <Area> --markers [--web]` — tratti difficili via Sonnet subscription
6. `whole_rivers.py <Area>`     — salmonicole + DDEP/concessioni *davvero* interi-corso
7. `lakes_geocode.py --apply`   — laghi sullo specchio d'acqua (Nominatim + fallback Overpass)
8. `qa_audit.py <Area>`         — DEVE dare 0 bloccanti
9. `build_map.py` + `cp mappa/index.html index.html`

## 7. Pubblicazione (umano, dopo review)
```
git add -A && git commit --author "ValerioDolci <valerio.dolci89@gmail.com>" -m "..."
git push origin main          # push semplice non traccia upstream: usare 'origin main'
```
Pages si ribuilda in ~1 min: https://valeriodolci.github.io/pesca-piemonte/

---

## Lezioni apprese (gotcha che costano tempo)
- **DDEP/concessioni ≠ interi fiumi**. Disegnare l'intero corso SOLO se il testo dice "tutto/intero il corso"
  oppure "dalle origini → **alla confluenza/foce/sbocco**". "Nei Comuni di X,Y" o "da A a B" = tratto specifico.
  (Bug reale: tutto il Po/Dora marcati €12.)
- **Laghi**: geocodificare per **nome**, NON al centro del comune (errore reale fino a ~5 km: Sirio, Pistono).
  Gate 10 km dal comune. Fallback Overpass `natural=water`/`reservoir` per invasi alpini assenti da Nominatim.
- **pick_component**: vicino a un frammento corto scegliere la **componente fiume più lunga** (evita di tagliare
  su uno spezzone OSM da 500 m mentre il fiume vero scorre 100 m più in là).
- **Ordine coordinate**: GeoJSON è `[lon,lat]`; `comuni_coords.json` è `{lat,lon}`. Confrontare con cura
  (un lat/lon invertito dava "5500 km dal comune" nel QA).
- **Rate limit**: Nominatim 1 req/s. **Overpass** banna duro (HTTP 429) e va in timeout se martellato →
  spaziare ≥3-8 s, backoff sul 429, usare il mirror `https://overpass.kumi.systems/api/interpreter`.
- **Sonnet**: `claude --print --model sonnet` (subscription, no costo API). Serve `PATH` con `/opt/homebrew/bin`
  (node). Prompt via **STDIN** (il flag variadico `--allowedTools` mangerebbe l'argomento prompt).
- **Soglie geometria**: snap>250m → marker; tratto<15m → scarta (foci/degeneri); salto interno: i fiumi grandi
  hanno nodi OSM radi (400-700 m), non è artefatto se diffuso — sospetto solo se è UN salto isolato grande.
- **Non riscrivere**: copiare lo script più simile e cambiare solo le parti diverse.
