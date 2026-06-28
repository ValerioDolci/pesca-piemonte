# Inventario fonti — Pesca Piemonte (TO / BI / NO / VCO)

> Ogni regola nella knowledge base DEVE puntare a una di queste fonti (campo `fonte`).
> Verificare sempre la versione più aggiornata sul sito ufficiale prima di una stagione di pesca.

## Cornice normativa regionale (vale per tutte le province)

| File | Documento | Fonte ufficiale | Data/Versione | Note |
|------|-----------|-----------------|---------------|------|
| `data/sources/regione/reg_regionale_1R_2012.pdf` | Regolamento Regionale 10/01/2012 n. 1/R | BU Regione Piemonte n.2 12/01/2012 — regione.piemonte.it | in vigore dal 26/02/2012 (agg. successivi su Arianna) | Attua art.9 c.3 L.R. 37/2006. Definisce licenze, attrezzi, periodi, misure minime. Allegato "C" = specie ciprinicole senza limiti. |

**Norma primaria**: L.R. Piemonte 29/12/2006 n. 37 — "Norme per la gestione della fauna acquatica, degli ambienti acquatici e regolamentazione della pesca". (testo non ancora scaricato in PDF — su Arianna Consiglio Regionale)

## Torino (Città Metropolitana) — fonte più ricca e aggiornata

| File | Documento | Fonte | Data | Pagine |
|------|-----------|-------|------|--------|
| `data/sources/torino/vademecum_2026.pdf` | Vademecum del Pescatore 2026 | cittametropolitana.torino.it | agg. 20/02/2026 | 32 |

Struttura (= modello dati): Classificazione acque · Modalità vietate · Acque salmonicole · D.D.E.P. (diritti demaniali esclusivi) · Acque in concessione pesca turistica e no-kill · Licenza e pagamento · Orari · Posto e distanze · Attrezzi · **Specie/periodi chiusura/misure minime/limiti giornalieri** · Specie con divieto · Specie ciprinicole senza limiti · **Zone di protezione**.

## Biella (Provincia) — aggiornato 2026

| File | Documento | Fonte | Data | Pagine |
|------|-----------|-------|------|--------|
| `data/sources/biella/vademecum_biellese_2026.pdf` | Vademecum del pescatore biellese 2026 | provincia.biella.it | pubbl. 30/12/2025 | 10 |

Contiene localizzazione zone di divieto e zone no-kill. Regole specifiche note: carpa solo no-kill 1–31 maggio, divieto carpa 1–30 giugno; salmonidi misura minima 24 cm.

## Novara (Provincia) — ✅ fonte UFFICIALE reperita (2026-06-28)

| File | Documento | Fonte | Data | Pagine |
|------|-----------|-------|------|--------|
| `data/sources/novara/bacini_acqua_pesca.pdf` | **Gestione dei corsi d'acqua e dei bacini della Provincia di Novara ai fini della pesca** (UFFICIALE) | Provincia di Novara (municipium) | 2025 | 15 |
| `data/sources/novara/fipsas_elenco_acque_2026.pdf` | Elenco acque FIPSAS Fishing Tour Novara (permessi BLU/PREMIUM/ROSSE + no-kill) | fishingtournovara.it | feb 2026 | 2 |
| `data/sources/novara/regolamento_provincia_novara_2023.pdf` | Regolamento Provincia di Novara (mirror, ora superato) | mirror pescafiume.it | 2023 | — |

✅ **Buco Novara colmato.** Il doc ufficiale è una tabella di **353 corsi d'acqua** con `Corso | Tipo | Comuni | Gestione | Inizio | Sviluppo | Termine`. Estratto pulito in `data/processed/novara/bacini_novara_raw.csv` (pdfplumber). Ingestion `ingest_novara_bacini.py` (Opzione B): mappate **163 acque gestite/speciali** (concessioni FIPSAS/APD/Associazioni/Comuni/Consorzi + 17 diritti esclusivi/riserve); le ~168 a gestione LIBERA = pesca libera baseline (non mappate). Conservate le 6 zone del mirror 2023 (no-kill Agogna, campi gara, salmonicole Sesia/Orta). Permessi/no-kill incrociati con la lista FIPSAS.
⚠️ Geometria: lo step Sonnet (`sonnet_resolve`) per promuovere i ~55 marker su-fiume a tratto richiede `claude` CLI autenticato (non disponibile nell'ambiente bot → da lanciare da sessione loggata).

## Verbano-Cusio-Ossola (Provincia)

| File | Documento | Fonte | Data | Pagine |
|------|-----------|-------|------|--------|
| `data/sources/vco/libretto_pesca_2022.pdf` | Libretto/Regolamento pesca (giugno 2022) | provincia.verbano-cusio-ossola.it | giu 2022 | 28 |
| `data/sources/vco/regolamento_verbania.pdf` | Regolamento di pesca prov. Verbania | mirror pescafiume.it | (più datato) | — |

⚠️ Documento più datato del set (2022). Piano Provinciale approvato con DCP 7/2023. Il "Segnacatture 2026" (registro catture) è annuale ma non cambia il regolamento. Lago Maggiore = convenzione italo-svizzera. Zona no-kill mosca su torrente San Bernardino. FIPSAS VCO gestisce acque in concessione (fipsasvco.it).

## TODO reperimento
- [ ] L.R. 37/2006 testo PDF (norma primaria) da Arianna
- [x] Novara: fonte ufficiale (non mirror) — ✅ trovata 2026-06-28 (`bacini_acqua_pesca.pdf` + FIPSAS Fishing Tour)
- [ ] VCO: cercare libretto/piano più recente del 2022 (DCP 7/2023)
- [ ] Manifesto annuale Torino (sintesi 1 pagina) se utile
- [ ] Eventuali shapefile/mappe ufficiali zone (per geometrie) — probabilmente assenti, da disegnare a mano

## Vercelli (Provincia) — fonte ufficiale 2024 ✅

| File | Documento | Fonte | Data |
|------|-----------|-------|------|
| `data/sources/vercelli/zone_protezione_2024_2028.pdf` | Zone di protezione fauna ittica | provincia.vercelli.it (Decreto Pres. 25 del 21/03/2024) | valide 2024-2028 |
| `data/sources/vercelli/zone_nokill_2024_2028.pdf` | Zone di pesca no-kill | provincia.vercelli.it (Decreto 25/2024) | valide 2024-2028 |

11 zone protezione + 3 no-kill. Acque: Sesia, Dora Baltea, Po, Elvo, Cervo, Rovasenda, Roggia Bona/Marcova, Roggione, Rio Venenza. Fonte ufficiale e attuale (a differenza di Novara).
