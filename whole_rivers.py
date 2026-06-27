#!/usr/bin/env python3
"""Disegna gli INTERI corsi di fiume (salmonicole, DDEP, concessioni "tutto il corso")
come MultiLineString: tutti i segmenti OSM con quel nome, SENZA stitching (ogni segmento
e' geometria reale -> niente salti dritti). Aggiorna tracts_<prov>.geojson.

Uso: python3 whole_rivers.py [Prov]   (default tutte)
"""
import sys, re, json, glob, unicodedata
from pathlib import Path
import resolve_tracts as R

def deacc(s):
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

ROOT = Path(__file__).parent
TYPES_WHOLE = {"salmonicola", "ddep", "concessione"}  # interi-corso / diritti esclusivi su intero tratto
WHOLE_HINT = ("tutto il corso", "tutto il suo corso", "per tutto", "dalle origini", "intero corso")

def river_keys(corso):
    """Ritorna 1+ chiavi (gestisce nomi composti: 'Torrenti X - Y', 'X e Y')."""
    s = corso.lower()
    s = re.sub(r"\b(torrenti|torrente|rio|rii|fiume|lago|laghi|canale|rogge|roggia|bealera|bacino di|t\.)\b", " ", s)
    s = re.split(r"\b(e suoi|e affluent|e defluent|dalle |dal |per tutto|nei comuni|gestione|\()", s)[0]
    parts = re.split(r"\s+[-–]\s+|\s+e\s+", s)  # split su " - " e " e "
    return [re.sub(r"\s+", " ", p).strip() for p in parts if len(re.sub(r"\s+", " ", p).strip()) >= 2]

def matches(name, key):
    return bool(key) and len(key) >= 2 and re.search(r"\b" + re.escape(deacc(key)) + r"\b", deacc(name.lower()))

SPECIFIC = re.compile(r'\b(dal|dalla|dall\'|da)\b.{0,80}\b(al|alla|all\'|fino|sino|alla foce|allo sbocco|al ponte|alla confluenza)\b', re.I)
def is_whole(z):
    tr = z.get("tratto", "").lower()
    # un tratto con estremi espliciti "dal X al Y" NON è intero-corso (è specifico)
    if SPECIFIC.search(tr) and not any(h in tr for h in WHOLE_HINT): return False
    if z["tipo"] == "salmonicola": return True
    if z["tipo"] in ("ddep", "concessione"):
        return any(h in tr for h in WHOLE_HINT) or "tratto scorrente nei comuni" in tr or z["tipo"] == "ddep"
    return False

def run(prov):
    wf = ROOT / f"data/processed/{prov.lower()}/osm_waterways.json"
    if not wf.exists(): print(f"{prov}: nessun osm_waterways"); return 0
    ways = [{"name": w["tags"]["name"], "geom": [(p["lat"], p["lon"]) for p in w.get("geometry", [])]}
            for w in json.load(open(wf))["elements"] if w.get("tags", {}).get("name") and len(w.get("geometry", [])) >= 2]
    zone = json.load(open(ROOT / f"data/processed/{prov.lower()}/zone_{prov.lower()}.json"))
    gj = ROOT / f"data/processed/{prov.lower()}/tracts_{prov.lower()}.geojson"
    fc = json.load(open(gj)) if gj.exists() else {"type":"FeatureCollection","provincia":prov,"fonte":zone["fonte"],"features":[]}
    done = {f["properties"]["id"] for f in fc["features"] if f["geometry"]["type"] in ("LineString","MultiLineString")
            and f["properties"].get("conf") not in (None, "", "corso-intero")}
    n = 0
    for z in zone["zone"]:
        if not is_whole(z) or z["id"] in done: continue
        keys = river_keys(z["corso_acqua"])
        segs = [w["geom"] for w in ways if any(matches(w["name"], k) for k in keys)]
        if not segs: continue
        coords = [[[p[1], p[0]] for p in s] for s in segs]  # lon,lat per GeoJSON
        feat = {"type":"Feature","properties":{"id":z["id"],"tipo":z["tipo"],"comune":z["comune"],
                "corso":z["corso_acqua"],"tratto":z.get("tratto",""),"regola":z.get("regola",""),
                "conf":"corso-intero","len_m":None,"metodo":"osm-multiline"},
                "geometry":{"type":"MultiLineString","coordinates":coords}}
        fc["features"] = [f for f in fc["features"] if f["properties"]["id"] != z["id"]] + [feat]
        n += 1
    json.dump(fc, open(gj, "w"), ensure_ascii=False)
    print(f"{prov}: {n} interi-corso disegnati come MultiLinea")
    return n

if __name__ == "__main__":
    provs = [sys.argv[1]] if len(sys.argv) > 1 else ["Torino","Biella","Novara","VCO"]
    tot = sum(run(p) for p in provs)
    print("TOTALE interi-corso:", tot)
