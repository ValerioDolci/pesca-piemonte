#!/usr/bin/env python3
"""Geocodifica le zone-LAGO per NOME (Nominatim) e le mette sullo specchio d'acqua
invece che al centro del comune (Sirio/Pistono/... erano fino a ~5km fuori posto).
Gate: il punto deve cadere entro GATE_KM dal comune della zona, altrimenti si scarta
(resta al comune). Scrive data/processed/laghi_coords.json {id: [lat,lon]}.

Uso: python3 lakes_geocode.py            # diagnostica
     python3 lakes_geocode.py --apply    # scrive laghi_coords.json
"""
import sys, json, glob, re
from pathlib import Path
import resolve_tracts as R
import place_resolver as P

ROOT = Path(__file__).parent
GATE_KM = 10.0
OUT = ROOT / "data/processed/laghi_coords.json"

def lake_name(corso):
    """Estrae un nome-lago pulito: rimuove ripetizioni-artefatto e tronca alle parole utili."""
    s = re.sub(r'\s+', ' ', corso).strip()
    w = s.split()
    if len(w) % 2 == 0 and w[:len(w)//2] == w[len(w)//2:]:  # 'Lago Di Alice Lago Di Alice'
        w = w[:len(w)//2]
    s = " ".join(w)
    # tieni dalla prima occorrenza di Lago/Laghi/Laghetto in poi
    m = re.search(r'lagh\w*.*', s, re.I)
    s = (m.group(0) if m else s).strip()
    s = re.sub(r'\([^)]*\)', '', s)                       # togli '(Pallanza)' '(Suna)'
    s = re.sub(r'\bsponda\b.*', '', s, flags=re.I)        # togli 'sponda sx/destra'
    s = re.split(r'\s+\b[eE]\b\s+', s)[0]                 # tronca a ' e Canale/Immissario...'
    return re.sub(r'\s+', ' ', s).strip()

def main(apply=False):
    comuni = json.load(open(ROOT / "data/processed/comuni_coords.json"))
    out = {}; kept = 0; skip = 0
    for zf in sorted(glob.glob(str(ROOT / "data/processed/*/zone_*.json"))):
        z = json.load(open(zf)); prov = z["provincia"]
        for it in z["zone"]:
            c = it.get("corso_acqua", "")
            if "lag" not in c.lower(): continue
            cm = it["comune"].split(" - ")[0].split("/")[0].strip()
            cc = comuni.get(f"{cm}|{prov}"); cpt = (cc["lat"], cc["lon"]) if cc else None
            name = lake_name(c)
            q = f"{name}, {cm}, {prov}, Italia" if cm else f"{name}, {prov}, Italia"
            g = P.geocode(q, place=name, comune=cm or None)
            ok = bool(g) and (cpt is None or R.hav(g, cpt) <= GATE_KM * 1000)
            d = (R.hav(g, cpt) / 1000) if (g and cpt) else None
            if ok:
                out[it["id"]] = [round(g[0], 6), round(g[1], 6)]; kept += 1
                print(f"  OK   {it['id']:13} {name[:30]:30} scarto-comune {d:.1f}km" if d is not None else f"  OK   {it['id']:13} {name[:30]:30}")
            else:
                skip += 1
                why = "no-geocode" if not g else f"{d:.1f}km > {GATE_KM}km"
                print(f"  skip {it['id']:13} {name[:30]:30} ({why}) -> resta al comune")
    print(f"\nlaghi localizzati: {kept} | scartati (restano al comune): {skip}")
    if apply:
        json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=0)
        print("scritto", OUT)

if __name__ == "__main__":
    main(apply="--apply" in sys.argv)
