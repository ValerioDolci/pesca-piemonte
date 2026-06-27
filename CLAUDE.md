# CLAUDE.md — Pesca Piemonte

Tool personale per capire **cosa / dove / come** andare a pesca nelle province di
**Torino, Biella, Novara, VCO**. Obiettivo finale: **mappa interattiva** che evidenzi
i tratti d'acqua e la regola che vi si applica (no-kill, turistica, protezione, salmonicola, ecc.).

## Stato corrente (2026-06-26)

**Fase 1 — base di conoscenza (2 livelli) + mappa v0.2 (TO + BI).**

Architettura a 2 livelli (decisa con Valerio):
- **Livello 0 — baseline regionale** (vale per tutte le province): `data/processed/regione/regole_generali.json` da Reg. 1/R 2012 (Art.13-16 + Allegato B specie/periodi/misure + Allegato C). È il "come/quando/quanto" generale.
- **Livello 1 — zone provinciali** (la mappa): `data/processed/<prov>/zone_<prov>.json`.

Fatto:
- ✅ Fonti scaricate (`SOURCES.md`) + testi estratti in `data/processed/*/*_text.txt`.
- ✅ Baseline regionale normalizzata (18 specie con misure/periodi/limiti, licenze, divieti, orari).
- ✅ **Torino**: 20 zone (9 turistiche, 7 no-kill, 4 no-kill CMTO). ⚠️ Mancano ancora ~80 zone di protezione (Decreto 353/2025, tabella pp.26-32) + acque salmonicole.
- ✅ **Biella**: 19 zone (13 protezione/divieto, 6 no-kill) + deroghe provinciali (fario 24cm salmonicole, salmonidi 6/giorno, mar/ven divieto). Salmonicole = area delimitata (non ancora mappata).
- ✅ **Mappa v0.2** `mappa/index.html`, multi-provincia, rigenerabile `python3 build_map.py`. Estetica "Carta Idrografica". Filtri provincia + tipo. Marker a livello COMUNE. Cache comuni condivisa `data/processed/comuni_coords.json` (29 comuni, Nominatim). Inviata 2026-06-26.

**Motore tratti precisi (semi-automatico OSM)** — `resolve_tracts.py`:
- Scarica rete idrografica provinciale da Overpass (`osm_waterways.json`), per ogni zona risolve gli estremi (hint `estremi` curati a mano: `confluenza`/`sorgente`/`luogo`/`intero`/`offset_m`/`punto`) sulla linea reale e taglia il tratto → `tracts_<prov>.geojson` (LineString + Point fallback, con `conf`).
- `build_map.py` ora preferisce il geojson tratti (linee) e ripiega su marker dove non risolvibile.
- **Biella a precisione-tratto**: 8 tratti disegnati (lunghezze combaciano col vademecum, es. no-kill Sessera ~810m vs 800) + 11 marker (4 rii assenti da OSM + estremi ambigui, es. Caneglio da rifinire a mano). PoC validato: no-kill Cervo Chiavazza→Tollegno ~3,2km.

**VCO (priorità Valerio)** — `zone_vco.json` 46 zone: 39 divieto (tabella Decreto 119/2019) + 5 concessione/FIPSAS (Toce, Strona, Lago Maggiore, Lago Orta-Omegna) + 1 DDEP (Suna ex Cuzzi Lamberti) + 1 riserva no-kill (San Bernardino) + divieti foci Lago Maggiore. Geocodificati 26 comuni. **Per ora a marker**, tratti precisi = prossimo step.

Tipi zona supportati: protezione, no_kill, no_kill_cmto, turistica, ddep, concessione, salmonicola.

**FASE A — inventario completo (in corso, quasi chiuso)**. Metodo deciso con Valerio: prima il dataset testuale completo di TUTTI i tratti, poi (Fase B) la geometria in un colpo solo. Dataset consolidato esportato in `data/processed/tutti_i_tratti.csv` (+`.json`) rigenerabile.
- **Dataset: 232 zone, 4 province** — Torino 161 (20 turistiche/no-kill + 118 protezione Decreto353/2025 + 23 salmonicole), Biella 19, VCO 46, Novara 6.
- Parser tabella protezione TO: script inline (slice pagine 26-31, split per numero record + word-boundary su keyword corso/descrizione). 4 record fixati a mano + 5 comuni corretti. Geocodificati 118/118.
- Tipi: protezione, divieto, no_kill, no_kill_cmto, turistica, ddep, concessione, riserva, campo_gara, salmonicola.

**Fase A CHIUSA — 281 zone.** Torino 210 COMPLETO (+27 DDEP interi corsi +22 DEP/UC/concessioni FIPSAS), Biella 19, VCO 46, Novara 6.
- **Novara INCOMPLETO (limite fonte non colmabile)**: tabella divieti/protezione non disponibile pubblicamente (sito provinciale dismesso, provincia delega i diritti alle associazioni).

**FASE B — geometria precisa** (in corso). Due strumenti:
1. `auto_estremi.py` + `resolve_tracts.py` — deterministico, gratis: estrae hint estremi dal testo (confluenza/sorgente/intero/luogo/offset) e taglia sulla linea OSM. Per i tratti facili.
2. **`tract_agent_tool.py` (TOOL subagente)** — per i tratti difficili con riferimenti locali (dighe/sbarramenti/briglie/ponti/frazioni non in OSM). Workflow: `prep <Prov> <ID>` → input polilinea+descrizione → subagente general-purpose (usa WebSearch) restituisce coord inizio/fine → `apply` aggancia alla linea OSM, taglia, **verifica la lunghezza** vs dichiarata, aggiorna `tracts_<prov>.geojson`. Prompt in `PROMPT_TRATTO.md`. Parser robusto al testo extra. **Validato**: VCO 5 tratti (Toce/Anza/Diveria/Bogna/Ri) tutti con lunghezza coerente (151/150, 548/500, 1027/1000, 3582/3500).

**TOOL EFFICIENTE `sonnet_resolve.py`** (sostituisce i subagenti, su richiesta Valerio): chiama `/opt/homebrew/bin/claude --print --model sonnet` (SUBSCRIPTION, no costo API extra), 1 chiamata/tratto, ragionamento nel subprocess (non nel contesto). NB PATH con /opt/homebrew/bin (node). Uso: `python3 sonnet_resolve.py <Prov> --markers [--web]`. GATE qualità: scarta estremi >250m dal fiume o tratti <15m (foci/degeneri). `apply_data` in `tract_agent_tool.py`.

Stato Fase B (post refinement --web + pulizia): **157 tratti precisi** — 11 alta, 106 media (ben delineati), 40 bassa (approssimati, landmark locali tipo dighe/briglie non pinpointabili in automatico). ~124 zone restano marker/non-disegnate (corso non in OSM: rogge/canali/rii/laghi, o interi-corsi salmonicole/ddep). OSM waterways scaricati tutte le province (`["ISO3166-2"="IT-XX"]`). Refinement `--web` (bassa→re-resolve con WebSearch, prompt via STDIN per il flag variadico --allowedTools) ha migliorato alcuni, revertiti 8 rotti (>8km su tipi tratto-corto, fino a 100km = componente fiume sbagliata). LIMITE raggiunto: l'automazione plateaua, i 40 bassa + i marker richiedono disegno MANUALE sulle acque prioritarie di Valerio. Mappa inviata 2026-06-26.

Priorità Valerio: **mappa con inizio/fine dei tratti** > misure/periodi; zone gestite/FIPSAS incluse (✅). Ordine: prima inventario completo, poi geometria su tutto.

Decisioni Valerio (2026-06-26): **mappa interattiva** + **mappatura zona-per-zona** (geometrie reali) + **uso personale** (per ora). Next step dopo la base di conoscenza.

## Il vincolo critico: accuratezza del dato

La parte difficile NON è il software, è il **dato normativo**: regionale di cornice,
ma **zonale e annuale** nel dettaglio. Errore su misura minima / periodo divieto → multa.
Regole non negoziabili:
1. **Ogni regola tracciata a una fonte** (campo `fonte` → riga di `SOURCES.md` + pagina).
2. **Disclaimer sempre visibile**: "Dato non ufficiale, verifica sempre il vademecum ufficiale".
3. **Modello dati pensato per l'aggiornamento annuale** (sostituire fonte → rigenerare, non riscrivere a mano).
4. Citare **misura minima, periodo di chiusura, limite giornaliero** sempre con la provincia di riferimento (variano!).

## Identificazione geometrie tratti (la parte manuale)

Le zone speciali nei documenti sono descritte **a parole** ("dal ponte di X al ponte di Y",
"dalla confluenza con il rio Z a monte"). Non esistono (quasi certamente) shapefile ufficiali.
→ Le geometrie dei tratti vanno **disegnate a mano** su base cartografica, traducendo la
descrizione testuale in una polyline. Workflow previsto (da definire nei next step):
estrarre le descrizioni testuali → geolocalizzare i punti di riferimento → tracciare la linea.

## Modello dati (bozza, da `data/processed/`)

- **acque**: id, nome, tipo (fiume/torrente/lago/canale), provincia, classificazione (salmonicola/ciprinicola), corso, geometria.
- **zone**: id, nome, tipo (`no_kill` | `turistica` | `protezione` | `ddep` | `ripopolamento` | `divieto`), provincia, acqua_id, descrizione_tratto (verbatim), regole, periodo, geometria, fonte.
- **specie**: nome comune/scientifico, provincia, periodo_chiusura, misura_minima_cm, limite_giornaliero, note, fonte.
- **regole_generali**: provincia, orari, attrezzi, modalità vietate, distanze, fonte.
- **licenze**: tipo (B/D, permessi temporanei), costo, validità, come ottenere, esenzioni, fonte.

## Struttura cartelle

```
pesca-piemonte/
  CLAUDE.md            # questo file
  SOURCES.md           # inventario fonti tracciato (verità sulle fonti)
  README.md
  data/
    sources/{torino,biella,novara,vco,regione}/   # PDF ufficiali (NON modificare)
    processed/         # knowledge base normalizzata (JSON/YAML) — da costruire
  docs/                # note di lavoro
```

## Interi corsi + confini + UX
- **`whole_rivers.py`**: per zone salmonicole/DDEP/"tutto il corso" disegna TUTTI i segmenti OSM del fiume come **MultiLineString** (no stitching → no salti dritti). 19 interi-corso Torino. build_map rende MultiLineString.
- **Confini provinciali**: `data/processed/province_boundaries.json` (Overpass relation ISO IT-TO/BI/NO/VB), render tratteggiato per provincia (ogni provincia = soprattassa/licenza separata; Torino in evidenza). Si nasconde col filtro provincia.
- **Fat-click**: aloni invisibili (26px linee / 20px multilinee / cerchio 16px) per tocco facile su mobile.
- **stitch() corretto**: non ricuce buchi >250m. Post-check revert tratti con salti interni >400m (artefatti).
- Pipeline rigenerazione completa: `auto_estremi`→`resolve_tracts`→`road_bridges --apply`→`place_resolver --apply`→`sonnet_resolve --markers [--web]`→`whole_rivers`→`lakes_geocode --apply`→`qa_audit`→`build_map`→ cp index.html → push.
- **Orchestratore nuova area**: `./run_region.sh <Area> [--web]` esegue tutta la geometria→QA→build (no push). Vedi **`PIPELINE.md`** per il flusso e2e completo + lezioni apprese (DDEP non-interi, laghi per nome, ordine lon/lat, rate-limit Overpass, ecc.).
- **`lakes_geocode.py`**: laghi sullo specchio d'acqua (Nominatim per nome + fallback Overpass natural=water), non al centro comune. Output `data/processed/laghi_coords.json`.
- **`qa_audit.py [Area]`**: gate QA (id duplicati, zone invisibili = BLOCCANTE; salti interni, over-long, lontano-da-comune, laghi-da-geocodare = warning). DEVE dare 0 bloccanti.

## Pubblicazione (GitHub Pages)
- **LIVE**: https://valeriodolci.github.io/pesca-piemonte/ — repo PUBBLICO `ValerioDolci/pesca-piemonte` (solo `index.html` self-contained + README, in cartella locale `site/`).
- Mappa mobile-friendly: pannello collassabile (☰), parte chiuso su schermi ≤640px.
- **Aggiornare**: `python3 build_map.py` → `cp mappa/index.html index.html` → `git add -A && git commit --author "ValerioDolci <valerio.dolci89@gmail.com>" -m ...` → `git push origin main` (repo = questa cartella, serve `index.html` in ROOT; non c'è più `site/`). Pages si ribuilda in ~1 min.

## Ambiente

- Python venv: `/Users/flaviacasini/claude-bot/venv/bin/python3` (3.14). `pypdf` disponibile.
- Per consegnare file/grafici/mappe a Valerio: `tg-file` / `tg-photo` (la chat non scarica i path).

## Regole operative
Valgono quelle del workspace (`../CLAUDE.md`): partner non yes-man, non riscrivere script
esistenti, comunicare mentre si agisce, misurare prima di stimare, niente task lunghi senza ok.
