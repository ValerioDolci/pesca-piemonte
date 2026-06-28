#!/usr/bin/env python3
"""Ingestion Novara dalla fonte UFFICIALE provinciale 'bacini_acqua_pesca.pdf'
(estratta in bacini_novara_raw.csv: corso|tipo|comuni|gestione|inizio|sviluppo|termine|fishing_tour).

Opzione B (decisa con Valerio): si tengono SOLO le acque gestite/speciali
(concessioni FIPSAS/APD/Associazioni/Comuni/Consorzi + diritti esclusivi/riserve),
le ~168 'LIBERA' restano baseline (citate nel note del file, non mappate).

Preserva le zone del mirror 2023 (NO-NK/CG/SALM) e incrocia la lista FIPSAS Fishing Tour
(BLU/PREMIUM/ROSSE) per marcare i no-kill espliciti.

Produce data/processed/novara/zone_novara.json e geocodifica i comuni mancanti
in comuni_coords.json. La geometria la fa poi run_region.sh (auto_estremi -> resolve_tracts ...).
"""
import csv, json, re, time, urllib.request, urllib.parse
from pathlib import Path

ROOT = Path(__file__).parent
RAW = ROOT / "data/processed/novara/bacini_novara_raw.csv"
ZONE = ROOT / "data/processed/novara/zone_novara.json"
COORDS = ROOT / "data/processed/comuni_coords.json"
PROV = "Novara"
FONTE = "Gestione dei corsi d'acqua e dei bacini della Provincia di Novara ai fini della pesca (fonte UFFICIALE provinciale)"
FONTE_FILE = "data/sources/novara/bacini_acqua_pesca.pdf"

# --- normalizzazione comune --------------------------------------------------
ABBR = {
    "NOV.": "Novarese", "NOV": "Novarese", "D'A.": "d'Agogna",
    "S.": "San", "C.NA": "", "FR.": "", "FRAZ.": "",
}
# correzioni di refusi/parse della fonte (comune normalizzato -> comune reale)
CORR = {
    "Casalbeltrtame": "Casalbeltrame", "Vinzagio": "Vinzaglio",
    "Trecate Cerano": "Trecate",
}
def norm_comune(comuni_cell):
    """Primo comune della colonna Comuni, ripulito ed espanso. '' se acqua non attiva/assente."""
    if not comuni_cell or re.search(r"NON\s+ATTIV", comuni_cell, re.I):
        return ""
    # toglie note tra parentesi e prende il primo token su separatori
    s = re.sub(r"\(.*?\)", "", comuni_cell)
    first = re.split(r"\s*[-/,;]\s*", s.strip())[0].strip()
    # espande abbreviazioni
    out = []
    for w in first.split():
        wu = w.upper().rstrip(".") + ("." if w.endswith(".") else "")
        out.append(ABBR.get(w.upper(), ABBR.get(wu, w)))
    res = " ".join(t for t in out if t).strip()
    res = res.title() if res.isupper() else res
    return CORR.get(res, res)

# --- classificazione gestione -> tipo ---------------------------------------
def _dedot(s):
    return re.sub(r"[.\s]", "", (s or "").upper())

def classify(gest):
    g = (gest or "").upper()
    gn = _dedot(gest)            # senza punti/spazi: 'A.P.D.'->'APD', 'F.I.P.S.A.S'->'FIPSAS'
    if not g.strip():
        return None  # gestione assente -> scarta (non classificabile)
    if "DIRITTOESCLUSIVO" in gn or "RISERVA" in gn or "PRIVATA" in gn:
        return ("riserva", "diritto esclusivo di pesca (riservato al concessionario)")
    if "FIPSAS" in gn:
        return ("concessione", "acqua in gestione/concessione FIPSAS (permesso associativo)")
    if "APD" in gn:
        return ("concessione", "acqua in gestione APD - Associazione Pescatori Dilettanti (permesso)")
    if "ASSOC" in gn or "PESCAT" in gn or "SOCIETA" in gn:
        return ("concessione", "acqua gestita da associazione pescatori (permesso)")
    if "COMUNE" in gn:
        return ("concessione", "acqua in concessione al Comune (permesso comunale)")
    if "CONSINTERCOM" in gn or "CONSORZIO" in gn:
        return ("concessione", "acqua in gestione a consorzio (permesso)")
    if "LIBER" in gn:
        return None  # LIBERA / EST SESIA-LIBERA -> baseline, esclusa
    # nessuna keyword nota e non libera: diritto esclusivo a nome di persona
    return ("riserva", f"diritto esclusivo / gestione: {gest.strip()}")

GESTORE_RE = [
    ("FIPSAS", "FIPSAS"), ("APD", "APD"), ("TRECATESI", "Ass. Pescatori Trecatesi"),
    ("SOZZAGO", "Ass. Pescatori Sozzago"), ("GALLIATESI", "Ass. Pescatori Galliatesi"),
    ("FONTANA MOTTA", "Ass. Pesc. Fontana Motta"), ("MOLINARA", "Cons. Roggia Molinara"),
    ("COMUNE", "Comune"), ("PARCO", "Parco del Ticino"), ("BORROMEO", "Princ. Borromeo"),
]
def gestore(gest):
    gn = _dedot(gest)
    for k, v in GESTORE_RE:
        if _dedot(k) in gn:
            return v
    return gest.strip()

# --- cross-ref FIPSAS no-kill (BLU/PREMIUM/ROSSE) ---------------------------
# match grezzo su nome corso per marcare no-kill espliciti dalla lista FIPSAS
NOKILL_HINTS = ["LAMA DI ROMAGNANO", "SESIA TRATTO A", "SESIA TRATTO B",
                "TERDOPPIO", "ROGGIA MORA"]

def main():
    rows = list(csv.DictReader(open(RAW)))
    # zone esistenti del mirror 2023 da preservare (solo gli id originali, NON i NO-BAC
    # eventualmente scritti da una run precedente -> script idempotente)
    old = json.load(open(ZONE))
    mirror = [z for z in old.get("zone", []) if not z["id"].startswith("NO-BAC")]

    zone = list(mirror)  # parte dalle zone mirror, aggiunge le bacini
    kept = excl = skipped = 0
    seen = set((z.get("corso_acqua","").lower(), z.get("comune","").lower()) for z in mirror)
    i = 0
    for r in rows:
        cl = classify(r["gestione"])
        if cl is None:
            excl += 1
            continue
        tipo, regola = cl
        corso = r["corso"].strip().title()
        tipo_w = re.split(r"\s*\(", r["tipo"])[0].strip().title()  # 'Roggia', 'Fiume'...
        corso_acqua = f"{tipo_w} {corso}".strip()
        comune = norm_comune(r["comuni"])
        if not comune:
            skipped += 1   # acqua non attiva / comune assente -> non mappabile, esclusa
            continue
        tratto_parts = [p for p in (r["inizio"], r["sviluppo"], r["termine"]) if p.strip()]
        tratto = " — ".join(tratto_parts) if tratto_parts else r["comuni"]
        key = (corso_acqua.lower(), comune.lower())
        if key in seen:
            continue
        seen.add(key)
        # no-kill override dalla lista FIPSAS
        blob = f"{corso_acqua} {tratto}".upper()
        note = None
        if any(h in blob for h in NOKILL_HINTS):
            note = "tratto/i con regolamento no-kill (lista FIPSAS Fishing Tour 2026)"
        i += 1
        z = {
            "id": f"NO-BAC-{i:03d}",
            "tipo": tipo,
            "comune": comune,
            "corso_acqua": corso_acqua,
            "tratto": tratto[:600],
            "regola": regola,
            "gestore": gestore(r["gestione"]),
            "fonte_pagina": None,
        }
        if note:
            z["nota"] = note
        zone.append(z)
        kept += 1

    out = {
        "provincia": PROV,
        "fonte": FONTE,
        "fonte_file": FONTE_FILE,
        "note": (f"Inventario UFFICIALE provinciale: 353 corsi d'acqua totali. "
                 f"Mappate {kept} acque gestite/speciali (concessioni FIPSAS/APD/Associazioni/"
                 f"Comuni/Consorzi + diritti esclusivi/riserve). Le ~{excl} acque a gestione LIBERA "
                 f"sono pesca libera (baseline regionale, non mappate come zone speciali). "
                 f"Permessi/no-kill specifici incrociati con lista FIPSAS Fishing Tour 2026 "
                 f"(data/sources/novara/fipsas_elenco_acque_2026.pdf). "
                 f"Conserva le {len(mirror)} zone del mirror 2023 (no-kill Agogna, campi gara, salmonicole)."),
        "zone": zone,
    }
    json.dump(out, open(ZONE, "w"), ensure_ascii=False, indent=2)
    print(f"Scritte {len(zone)} zone ({len(mirror)} mirror + {kept} bacini) | "
          f"escluse LIBERA/non-class: {excl} | saltate (non attive/no comune): {skipped}")
    return out


# --- geocodifica comuni mancanti --------------------------------------------
def _nominatim(q):
    u = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
        {"q": q, "format": "json", "limit": 1})
    try:
        d = json.load(urllib.request.urlopen(
            urllib.request.Request(u, headers={"User-Agent": "pesca/0.1"}), timeout=20))
        return (float(d[0]["lat"]), float(d[0]["lon"])) if d else None
    except Exception:
        return None

def geocode_comuni(out):
    coords = json.load(open(COORDS))
    comuni = sorted({z["comune"] for z in out["zone"] if z.get("comune")})
    miss = [c for c in comuni if f"{c}|{PROV}" not in coords]
    print(f"Comuni da geocodificare: {len(miss)}/{len(comuni)}")
    ok = fail = 0
    for c in miss:
        r = _nominatim(f"{c}, provincia di Novara, Italia")
        time.sleep(1.0)
        if not r:
            r = _nominatim(f"{c}, Piemonte, Italia"); time.sleep(1.0)
        if r:
            coords[f"{c}|{PROV}"] = {"lat": r[0], "lon": r[1]}; ok += 1
        else:
            fail += 1; print(f"  [no geocode] {c}")
    json.dump(coords, open(COORDS, "w"), ensure_ascii=False, indent=1)
    print(f"Geocodificati {ok}, falliti {fail}")

if __name__ == "__main__":
    out = main()
    geocode_comuni(out)
