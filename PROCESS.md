# Processo di lavoro — come è stata costruita la carta della pesca

Documento che spiega il **metodo a step** con cui ogni area è stata mappata: reperimento
fonti → estrazione dati → risoluzione geometrica → controllo qualità → pubblicazione.
Ogni passo ha i suoi strumenti e i suoi controlli.

---

## Principio guida
**L'accuratezza del dato viene prima della copertura.** Meglio un marker onesto con la
descrizione testuale che una linea disegnata nel posto sbagliato. Ogni geometria è
agganciata a dati reali (OpenStreetMap) e passa controlli automatici; dove l'automatismo
non è affidabile, la zona resta marker (segnalato), non viene "inventata".

---

## STEP 1 — Reperimento fonti (sourcing)
Per ogni provincia/regione si cerca la **fonte ufficiale più recente**:
- vademecum / carta delle acque pescabili / calendario ittico provinciale o regionale;
- decreti delle zone di protezione e no-kill;
- acque gestite da associazioni/consorzi (FIPSAS VCO, SVPS Valsesia, Consorzio Pesca VdA).

Output: PDF ufficiali in `data/sources/<area>/`, tracciati in `SOURCES.md` (con data e link).
**Controllo:** ogni regola deve poter puntare a una fonte. Fonti datate o mirror sono segnalate
come tali (es. Novara = mirror incompleto; VCO = libretto 2022).

## STEP 2 — Estrazione e normalizzazione (analysis)
Dal PDF si estrae il testo (`pypdf`) e si **normalizza** in dati strutturati:
`data/processed/<area>/zone_<area>.json` con, per ogni zona: `comune`, `corso_acqua`,
`tratto` (descrizione verbatim), `tipo`, `regola`, `fonte`.
- Tabelle pulite (Torino 118 protezione, Cuneo 87, Vercelli 14) → parser dedicato.
- Prose (Alessandria) → estrazione semi-manuale dei tratti chiari.
**Controllo (audit di completezza):** conteggio zone estratte vs sezioni della fonte
(es. Torino protezione 118/118, DDEP 27/27, DEP 22/22). Vedi l'audit in `CLAUDE.md`.

## STEP 3 — Risoluzione geometrica (work)
Trasformare la descrizione testuale ("dal ponte X alla confluenza Y") in una **linea reale**
sul corso d'acqua. Si usa la rete idrografica OpenStreetMap della provincia
(`osm_waterways.json`, scaricata via Overpass per codice ISO). Strumenti, dal più
affidabile al più euristico:

1. **`road_bridges.py`** — se la descrizione cita una strada (SP/SR/SS NNN): calcola
   l'**incrocio reale OSM strada×fiume**. È il metodo più preciso (gap tipico < 50 m).
   Gate: l'incrocio deve cadere vicino al comune (evita match di strade/fiumi omonimi).
2. **`place_resolver.py`** — se cita una frazione/località: la geolocalizza con
   **Nominatim**, con fallback **Overpass** per i luoghi oscuri, e la aggancia al fiume.
3. **`resolve_tracts.py`** (+ `auto_estremi.py`) — deterministico: confluenze, sorgenti,
   "tutto il corso", offset metrici ("per 500 m a valle") tagliati sulla geometria OSM.
4. **`whole_rivers.py`** — interi corsi (salmonicole, DDEP, diritti esclusivi): disegna
   **tutti i segmenti OSM** del fiume come MultiLineString (niente stitching → niente
   salti dritti).
5. **`sonnet_resolve.py`** — per i tratti con riferimenti locali ambigui: chiama il
   modello **Claude Sonnet** (via subscription, una chiamata per tratto) che, con la
   polilinea del fiume + ricerca web, stima gli estremi. È l'ultima risorsa (confidenza
   spesso "media/bassa"), usato in batch.

## STEP 4 — Controllo qualità (control)
Ogni risultato passa **gate automatici** (in `sonnet_resolve.py` e nei post-check):
- **snap > 250 m** dal fiume → estremo non sul corso → scartato (resta marker);
- **tratto < 15 m** (foce/degenere) → scartato;
- **salto interno > 400 m** nella polilinea → artefatto di stitching → revertito;
- **tipo-corto (protezione/no-kill) > 8–9 km** → lunghezza implausibile → revertito;
- **check lunghezza**: se la descrizione dichiara una misura ("~500 m"), si confronta.
Confidenza tracciata per ogni tratto: `alta` / `media` / `bassa`.
**Verifica umana:** errori segnalati dall'utente (Elvo, Oropa, Soana, Melezzo — l'LLM
sbagliava i landmark) sono stati corretti con i metodi 1–2 (incrocio/geocoding preciso),
che ora sono strumenti riusabili.

## STEP 5 — Assemblaggio e pubblicazione
- **`build_map.py`** assembla `mappa/index.html` (Leaflet): tratti precisi (linee),
  interi-corsi (multilinee), marker per ciò che non è disegnabile, confini provinciali
  (= aree-licenza), UI mobile (pannello collassabile, tocco facilitato).
- Export dataset consolidato `data/processed/tutti_i_tratti.csv` (ogni zona + stato geometria).
- Pubblicazione su **GitHub Pages**: https://valeriodolli.github.io/pesca-piemonte/

## Limiti noti (onestà)
- Dove il corso d'acqua **non è in OpenStreetMap** (piccoli rii, rogge, bealere, canali
  minori) non c'è geometria su cui agganciare → la zona resta **marker** con descrizione+fonte.
- **Novara** e **Asti**: le province non pubblicano l'elenco zone in formato utilizzabile.
- I tratti a confidenza **bassa** (riferimenti locali non geolocalizzabili) sono approssimati
  e vanno verificati sul campo.

## Riproducibilità — rigenerare la mappa
```
python3 build_map.py            # riassembla mappa/index.html dai dati
cp mappa/index.html index.html  # per GitHub Pages
git add -A && git commit && git push
```
Pipeline completa per una nuova area: vedi `STRUCTURE.md`.
