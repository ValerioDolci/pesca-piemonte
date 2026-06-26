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

## Novara (Provincia) — sito provinciale dismesso (410)

| File | Documento | Fonte | Data | Pagine |
|------|-----------|-------|------|--------|
| `data/sources/novara/regolamento_provincia_novara_2023.pdf` | Regolamento Provincia di Novara | mirror pescafiume.it (orig. Provincia Novara) | 2023 | — |

⚠️ Fonte secondaria (mirror). Da ri-verificare con fonte ufficiale Novara o regionale. Acque principali: Sesia, Ticino, Terdoppio, Agogna, canali (Cavour, Q. Sella, Regina Elena), Lago d'Orta.

## Verbano-Cusio-Ossola (Provincia)

| File | Documento | Fonte | Data | Pagine |
|------|-----------|-------|------|--------|
| `data/sources/vco/libretto_pesca_2022.pdf` | Libretto/Regolamento pesca (giugno 2022) | provincia.verbano-cusio-ossola.it | giu 2022 | 28 |
| `data/sources/vco/regolamento_verbania.pdf` | Regolamento di pesca prov. Verbania | mirror pescafiume.it | (più datato) | — |

⚠️ Documento più datato del set (2022). Piano Provinciale approvato con DCP 7/2023. Il "Segnacatture 2026" (registro catture) è annuale ma non cambia il regolamento. Lago Maggiore = convenzione italo-svizzera. Zona no-kill mosca su torrente San Bernardino. FIPSAS VCO gestisce acque in concessione (fipsasvco.it).

## TODO reperimento
- [ ] L.R. 37/2006 testo PDF (norma primaria) da Arianna
- [ ] Novara: fonte ufficiale (non mirror) — sito provinciale dismesso, valutare regionale/FIPSAS
- [ ] VCO: cercare libretto/piano più recente del 2022 (DCP 7/2023)
- [ ] Manifesto annuale Torino (sintesi 1 pagina) se utile
- [ ] Eventuali shapefile/mappe ufficiali zone (per geometrie) — probabilmente assenti, da disegnare a mano
