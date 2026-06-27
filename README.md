# 🎣 Carta Idrografica della Pesca — Piemonte nord-ovest + Valle d'Aosta

Mappa interattiva delle zone di pesca dilettantistica (protezione/divieto, no-kill, zone
turistiche, acque salmonicole, diritti esclusivi D.D.E.P., acque in concessione FIPSAS/
associazioni) di **8 aree**: Torino, Cuneo, VCO, Vercelli, Biella, Alessandria,
Valle d'Aosta, Novara.

## 🔗 Mappa live
**https://valeriodolci.github.io/pesca-piemonte/**

Ottimizzata mobile (pannello collassabile, tocco facilitato). Filtri per area e per tipo di
zona. Tocca un tratto/marker per regola, descrizione, lunghezza e fonte.

⚠️ **Strumento non ufficiale.** Verifica sempre il vademecum/regolamento ufficiale della
provincia prima di pescare. La normativa cambia ogni anno e zona per zona.

## Cosa contiene
| Area | Zone | Fonte ufficiale |
|---|---:|---|
| Torino | 210 | Vademecum del Pescatore 2026 (Città Metropolitana) |
| Cuneo | 87 | Carta delle acque pescabili 2025 |
| VCO | 58 | Libretto 2022 + acque in concessione FIPSAS |
| Vercelli | 22 | Decreto Prov. 25/2024 + acque SVPS Valsesia |
| Biella | 19 | Vademecum del pescatore biellese 2026 |
| Alessandria | 15 | Pescare in Provincia di Alessandria 2025 |
| Valle d'Aosta | 14 | Calendario Ittico 2026 + Consorzio Pesca VdA |
| Novara | 6 | (mirror 2023, incompleto) |

**~431 zone**: 219 tratti precisi (linee) + 37 interi-corsi (multilinee) + 175 marker.
Dataset consolidato: [`data/processed/tutti_i_tratti.csv`](data/processed/tutti_i_tratti.csv).

## Come funziona (in breve)
Per ogni area: fonte ufficiale → estrazione dati → la descrizione testuale di ogni tratto
("dal ponte X alla confluenza Y") viene tradotta in una **linea reale** sulla rete
idrografica OpenStreetMap, con controlli di qualità automatici. Dove l'aggancio non è
affidabile, la zona resta **marker** (mai inventata).

➡️ **Il metodo a step completo è in [`PROCESS.md`](PROCESS.md)**
➡️ **La struttura del progetto e la pipeline in [`STRUCTURE.md`](STRUCTURE.md)**
➡️ **Le fonti tracciate in [`SOURCES.md`](SOURCES.md)**

## Struttura
```
├── PROCESS.md / STRUCTURE.md / SOURCES.md   ← documentazione (metodo, struttura, fonti)
├── *.py                                     ← pipeline (vedi STRUCTURE.md)
├── data/sources/<area>/                     ← PDF ufficiali
├── data/processed/<area>/                   ← dati normalizzati + geometrie (geojson)
├── mappa/index.html  +  index.html          ← mappa generata (Pages serve la root)
```

## Rigenerare la mappa
```bash
python3 build_map.py
cp mappa/index.html index.html
```
Richiede Python 3 con `pypdf`. Le geometrie usano OpenStreetMap (Overpass) e Leaflet (CDN).

## Crediti dati
Vademecum e regolamenti delle Province/Regioni indicate · geometrie © OpenStreetMap
contributors · tiles © CARTO. Progetto personale, dato non ufficiale.
