#!/usr/bin/env python3
"""QA della mappa: controlla le classi di bug incontrate durante la costruzione.
Riusabile su ogni area. Esce con codice !=0 se trova problemi BLOCCANTI.

Controlli:
  [BLOCCANTE] id duplicato in piu' feature                       (doppio render)
  [BLOCCANTE] zona invisibile (no geom, no comune, no lago, no corso OSM)
  [warn]      salto interno >GAP m in una LineString             (artefatto salto-dritto)
  [warn]      tratto >LONG km su tipo-corto (protezione/no_kill) (componente fiume sbagliata)
  [warn]      marker/tratto >FAR km dal comune della zona        (geocoding sbagliato)
  [info]      lago non sullo specchio d'acqua (candidato lakes_geocode)

Uso: python3 qa_audit.py [Area ...]   (default: tutte)
"""
import sys, json, glob, re, math, unicodedata
from pathlib import Path

ROOT = Path(__file__).parent
GAP, LONG_KM, FAR_KM = 600, 8.0, 12.0          # soglie (GAP 600: i fiumi grandi hanno nodi OSM radi)
SHORT = {"protezione", "no_kill", "turistica", "no_kill_cmto", "divieto"}

_osm = {}
def _deacc(x): return ''.join(c for c in unicodedata.normalize('NFD', x) if unicodedata.category(c) != 'Mn')
def corso_in_osm(prov, corso):
    """True se il corso e' presente in OSM -> render via river_centroid (come build_map)."""
    wf = ROOT / f"data/processed/{prov.lower()}/osm_waterways.json"
    if not wf.exists(): return False
    if prov not in _osm:
        _osm[prov] = [_deacc(w["tags"]["name"].lower()) for w in json.load(open(wf))["elements"]
                      if w.get("tags", {}).get("name")]
    s = re.sub(r'\b(torrenti|torrente|rio|rii|fiume|lago|laghi|canale|rogge|roggia|bealera|bacino di|t\.)\b', ' ', corso.lower())
    key = _deacc(re.split(r'\s+[-–]\s+|\s+e\s+|,', s)[0].strip())
    if len(key) < 2: return False
    rx = re.compile(r'\b' + re.escape(key) + r'\b')
    return any(rx.search(nm) for nm in _osm[prov])

def hav(a, b):
    R = 6371000; p = math.pi / 180
    return 2 * R * math.asin(math.sqrt(math.sin((b[1]-a[1])*p/2)**2 +
           math.cos(a[1]*p)*math.cos(b[1]*p)*math.sin((b[0]-a[0])*p/2)**2))

def centroid(geom):
    t = geom["type"]; c = geom["coordinates"]
    if t == "Point": return c
    if t == "LineString": return c[len(c)//2]
    if t == "MultiLineString": s = c[len(c)//2]; return s[len(s)//2]

def main(areas):
    comuni = json.load(open(ROOT / "data/processed/comuni_coords.json"))
    lf = ROOT / "data/processed/laghi_coords.json"
    laghi = json.load(open(lf)) if lf.exists() else {}
    blocking = 0; warn = 0
    seen = {}                                   # id -> n feature
    geo = {}                                    # id -> (geom, conf)
    for gj in sorted(glob.glob(str(ROOT / "data/processed/*/tracts_*.geojson"))):
        for f in json.load(open(gj))["features"]:
            p = f["properties"]; seen[p["id"]] = seen.get(p["id"], 0) + 1
            geo[p["id"]] = (f["geometry"], p.get("conf", ""))
    for i, n in seen.items():
        if n > 1: print(f"  [BLOCCANTE] id duplicato {i} in {n} feature"); blocking += 1

    for zf in sorted(glob.glob(str(ROOT / "data/processed/*/zone_*.json"))):
        z = json.load(open(zf)); prov = z["provincia"]
        if areas and prov not in areas: continue
        for it in z["zone"]:
            zid = it["id"]; tipo = it["tipo"]; corso = it.get("corso_acqua", "")
            cm = it.get("comune", "")
            cands = [c.strip() for c in [cm] + re.split(r"\s*-\s*|/|;|,", cm) if c.strip()]
            cc = next((comuni[f"{c}|{prov}"] for c in cands if f"{c}|{prov}" in comuni), None)
            cpt = (cc["lon"], cc["lat"]) if cc else None   # ordine GeoJSON [lon,lat] come centroid()
            g = geo.get(zid)
            # invisibile? (nessuna geom, nessun comune, nessun lago, e il corso non e' in OSM)
            if not g and zid not in laghi and not cpt and not corso_in_osm(prov, corso):
                print(f"  [BLOCCANTE] {zid} invisibile (no geom/comune/lago/corso-OSM): {corso[:34]}"); blocking += 1
            if g:
                geom, conf = g
                if geom["type"] == "LineString":
                    cs = geom["coordinates"]; segs = [hav(cs[i], cs[i+1]) for i in range(len(cs)-1)]
                    L = sum(segs)
                    if segs and max(segs) > GAP:
                        print(f"  [warn] {zid} salto interno {round(max(segs))}m (artefatto?)"); warn += 1
                    if tipo in SHORT and L > LONG_KM*1000:
                        print(f"  [warn] {zid} tratto {L/1000:.1f}km su tipo-corto '{tipo}'"); warn += 1
                if cpt:
                    d = hav(centroid(geom), cpt)
                    if d > FAR_KM*1000:
                        print(f"  [warn] {zid} geom a {d/1000:.1f}km dal comune {cm}"); warn += 1
            # lago non posato sull'acqua
            if "lag" in corso.lower() and zid not in laghi:
                print(f"  [info] {zid} lago al comune (candidato lakes_geocode): {corso[:30]}")
    print(f"\nQA: {blocking} bloccanti, {warn} warning")
    return blocking

if __name__ == "__main__":
    sys.exit(1 if main(sys.argv[1:]) else 0)
