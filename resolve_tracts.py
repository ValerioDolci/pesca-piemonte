#!/usr/bin/env python3
"""Motore geometrico: trasforma le zone (con hint 'estremi') in tratti precisi
disegnati sulla geometria reale OSM. Deterministico.

Input  : data/processed/<prov>/zone_<prov>.json  (con campo opzionale 'estremi')
         data/processed/<prov>/osm_waterways.json (Overpass 'out geom')
         data/processed/comuni_coords.json
Output : data/processed/<prov>/tracts_<prov>.geojson (LineString risolti + Point fallback)

Hint estremi per zona:
  "estremi": {"da": <hint>, "a": <hint>}
  hint = {"confluenza":"Torrente X"} | {"sorgente":true} | {"foce":true}
       | {"luogo":"Frazione, Comune"} | {"intero":true} | {"punto":[lat,lon]}
       | {"offset_m": N, "verso":"monte|valle", "rispetto":<hint>}
Senza 'estremi' o river assente -> fallback Point sul comune (confidence 'bassa').

Uso: python3 resolve_tracts.py <provincia>     (es. Biella)
"""
import sys, json, math, time, urllib.request, urllib.parse
from pathlib import Path

ROOT = Path(__file__).parent
GEOCACHE = ROOT / "data/processed/geocode_cache.json"
_gc = json.load(open(GEOCACHE)) if GEOCACHE.exists() else {}

def hav(a, b):
    R = 6371000.0; p = math.pi / 180
    dlat = (b[0]-a[0])*p; dlon = (b[1]-a[1])*p
    x = math.sin(dlat/2)**2 + math.cos(a[0]*p)*math.cos(b[0]*p)*math.sin(dlon/2)**2
    return 2*R*math.asin(math.sqrt(x))

def geocode(q):
    if q in _gc: return tuple(_gc[q]) if _gc[q] else None
    u = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
        {"q": q, "format": "json", "limit": 1})
    try:
        d = json.load(urllib.request.urlopen(urllib.request.Request(
            u, headers={"User-Agent": "pesca-piemonte/0.1"}), timeout=20))
        r = (float(d[0]["lat"]), float(d[0]["lon"])) if d else None
    except Exception:
        r = None
    _gc[q] = list(r) if r else None
    json.dump(_gc, open(GEOCACHE, "w"), ensure_ascii=False, indent=2)
    time.sleep(1.1)
    return r

# ---- geometria fiumi da OSM ----
def load_ways(prov):
    osm = json.load(open(ROOT / f"data/processed/{prov.lower()}/osm_waterways.json"))
    out = []
    for w in osm["elements"]:
        nm = w.get("tags", {}).get("name")
        g = [(p["lat"], p["lon"]) for p in w.get("geometry", [])]
        if nm and len(g) >= 2: out.append({"name": nm, "geom": g})
    return out

def river_components(ways, name_key):
    """ Way con nome che contiene name_key -> componenti connesse (liste di polilinee)."""
    k = name_key.lower()
    sel = [w["geom"] for w in ways if k in w["name"].lower()]
    comps = []  # ogni comp = lista di segmenti
    for g in sel:
        placed = False
        for c in comps:
            for s in c:
                if min(hav(g[0], s[0]), hav(g[0], s[-1]),
                       hav(g[-1], s[0]), hav(g[-1], s[-1])) < 60:
                    c.append(g); placed = True; break
            if placed: break
        if not placed: comps.append([g])
    # ordina i segmenti di ogni componente in una polilinea continua
    return [stitch(c) for c in comps]

def stitch(segs, max_gap=250):
    """Ricuce i segmenti estendendo da entrambi i capi; si ferma se il segmento piu'
    vicino e' oltre max_gap (evita salti dritti tra tratti disgiunti)."""
    segs = [list(s) for s in segs]
    line = segs.pop(0)
    changed = True
    while changed and segs:
        changed = False
        be = bs = None  # best per coda (end) e per testa (start)
        for i, s in enumerate(segs):
            for rev, pt, other in ((False, s[0], s[-1]), (True, s[-1], s[0])):
                de = hav(pt, line[-1])
                if be is None or de < be[0]: be = (de, i, rev)
                ds = hav(pt, line[0])
                if bs is None or ds < bs[0]: bs = (ds, i, rev)
        if be and be[0] <= max_gap and (not bs or be[0] <= bs[0]):
            d, i, rev = be; s = segs.pop(i); line += (s[::-1] if rev else s); changed = True
        elif bs and bs[0] <= max_gap:
            d, i, rev = bs; s = segs.pop(i); line = (s if rev else s[::-1]) + line; changed = True
    return line

def pick_component(comps, near):
    return min(comps, key=lambda L: min(hav(v, near) for v in L)) if comps else None

def nearest_idx(line, pt): return min(range(len(line)), key=lambda i: hav(line[i], pt))

def walk(line, idx, meters, verso):
    """cammina lungo la polilinea da idx per ~meters; verso decide la direzione
    (verso 'sorgente'=verso indice 0 se 0 e' a monte). Qui semplice: prova entrambe e
    restituisce l'indice piu vicino in distanza-percorso."""
    step = 1 if verso == "up" else -1
    acc = 0; i = idx
    while 0 <= i+step < len(line) and acc < meters:
        acc += hav(line[i], line[i+step]); i += step
    return i

# ---- risoluzione estremo ----
def resolve_end(hint, line, ways, comune_pt):
    """ritorna (idx_sulla_linea, confidenza_str) oppure (None,None)."""
    if not hint: return None, None
    if "punto" in hint:
        return nearest_idx(line, tuple(hint["punto"])), "manuale"
    if "intero" in hint:  # gestito a monte
        return None, None
    if "sorgente" in hint:
        # estremo a quota maggiore (sorgente) = vertice piu lontano... uso: estremo con lat/quota?
        # euristica: l'estremo piu vicino al comune di montagna spesso e' la sorgente; meglio:
        # prendiamo l'estremo della polilinea piu lontano dal punto di valle noto -> gestito dal chiamante
        return ("EXTREME_SOURCE", "media")
    if "foce" in hint:
        return ("EXTREME_MOUTH", "media")
    if "confluenza" in hint:
        comps = river_components(ways, hint["confluenza"])
        other = pick_component(comps, comune_pt)
        if not other: return None, None
        # punto del fiume corrente piu vicino all'altro fiume
        best = None
        for i, v in enumerate(line):
            j = nearest_idx(other, v); d = hav(v, other[j])
            if best is None or d < best[0]: best = (d, i)
        return best[1], ("alta" if best[0] < 120 else "media")
    if "luogo" in hint:
        p = geocode(hint["luogo"])
        if not p: return None, None
        return nearest_idx(line, p), "media"
    return None, None

def resolve_zone(z, ways, comuni, prov):
    cm = z["comune"].split(" - ")[0].strip()
    comune_pt = None
    cc = comuni.get(f"{cm}|{prov}")
    if cc: comune_pt = (cc["lat"], cc["lon"])
    est = z.get("estremi")
    river = z.get("corso_acqua", "")
    rkey = river.lower().replace("torrente", "").replace("rio", "").replace("fiume", "").strip()
    comps = river_components(ways, rkey) if rkey else []
    line = pick_component(comps, comune_pt) if comps and comune_pt else None

    if not est or not line:
        return {"type": "Point", "pt": comune_pt, "conf": "bassa-marker"} if comune_pt else None

    if est.get("da", {}).get("intero") or est.get("a", {}).get("intero"):
        L = sum(hav(line[i], line[i+1]) for i in range(len(line)-1))
        return {"type": "LineString", "coords": line, "conf": "alta", "len_m": round(L)}

    da_h, a_h = est.get("da"), est.get("a")
    def is_off(h): return bool(h) and "offset_m" in h
    ia, ca = (None, None) if is_off(da_h) else resolve_end(da_h, line, ways, comune_pt)
    ib, cb = (None, None) if is_off(a_h) else resolve_end(a_h, line, ways, comune_pt)

    # gestisci estremi 'sorgente/foce': sono gli estremi della polilinea
    def extreme(tok, other_idx):
        # scegli l'estremo (0 o len-1) coerente: SOURCE = piu lontano dalla foce nota; qui
        # usiamo: SOURCE = estremo piu lontano dall'altro indice noto; MOUTH = piu vicino
        e0, e1 = 0, len(line)-1
        if other_idx is None: return e0 if tok == "EXTREME_SOURCE" else e1
        d0 = abs(e0-other_idx); d1 = abs(e1-other_idx)
        return (e0 if d0 > d1 else e1) if tok == "EXTREME_SOURCE" else (e0 if d0 < d1 else e1)

    if ia in ("EXTREME_SOURCE", "EXTREME_MOUTH"): ia = extreme(ia, ib if isinstance(ib, int) else None)
    if ib in ("EXTREME_SOURCE", "EXTREME_MOUTH"): ib = extreme(ib, ia if isinstance(ia, int) else None)

    # offset: cammina N metri dall'estremo gia' risolto verso l'estremo lontano del corso
    def walk_offset(i0, meters):
        far_end = 0 if abs(0 - i0) > abs(len(line)-1 - i0) else len(line)-1
        step = 1 if far_end > i0 else -1
        acc = 0; i = i0
        while 0 <= i+step < len(line) and acc < meters:
            acc += hav(line[i], line[i+step]); i += step
        return i
    if is_off(da_h) and isinstance(ib, int):
        ia, ca = walk_offset(ib, da_h["offset_m"]), "media"
    if is_off(a_h) and isinstance(ia, int):
        ib, cb = walk_offset(ia, a_h["offset_m"]), "media"

    if not isinstance(ia, int) or not isinstance(ib, int):
        return {"type": "Point", "pt": comune_pt, "conf": "bassa-marker"} if comune_pt else None

    a, b = sorted((ia, ib))
    seg = line[a:b+1]
    if len(seg) < 2:
        return {"type": "Point", "pt": comune_pt, "conf": "bassa-marker"} if comune_pt else None
    L = sum(hav(seg[i], seg[i+1]) for i in range(len(seg)-1))
    conf = "bassa" if "bassa" in (ca or "")+(cb or "") else ("alta" if ca == cb == "alta" else "media")
    return {"type": "LineString", "coords": seg, "conf": conf, "len_m": round(L)}

def main(prov):
    ways = load_ways(prov)
    comuni = json.load(open(ROOT / "data/processed/comuni_coords.json"))
    zone = json.load(open(ROOT / f"data/processed/{prov.lower()}/zone_{prov.lower()}.json"))
    feats = []
    rep = {"LineString": 0, "Point": 0, "none": 0}
    for z in zone["zone"]:
        r = resolve_zone(z, ways, comuni, prov)
        if not r: rep["none"] += 1; print(f"  --  {z['id']}  NESSUNA geom"); continue
        rep[r["type"]] += 1
        props = {"id": z["id"], "tipo": z["tipo"], "comune": z["comune"],
                 "corso": z.get("corso_acqua",""), "tratto": z.get("tratto",""),
                 "regola": z.get("regola",""), "conf": r["conf"], "len_m": r.get("len_m")}
        if r["type"] == "LineString":
            geom = {"type": "LineString", "coordinates": [[c[1], c[0]] for c in r["coords"]]}
            print(f"  LINE {z['id']:11} {z.get('corso_acqua',''):24} ~{r.get('len_m')}m  [{r['conf']}]")
        else:
            geom = {"type": "Point", "coordinates": [r["pt"][1], r["pt"][0]]}
            print(f"  pt   {z['id']:11} {z.get('corso_acqua',''):24} (marker)")
        feats.append({"type": "Feature", "properties": props, "geometry": geom})
    out = {"type": "FeatureCollection", "provincia": prov,
           "fonte": zone["fonte"], "features": feats}
    p = ROOT / f"data/processed/{prov.lower()}/tracts_{prov.lower()}.geojson"
    json.dump(out, open(p, "w"), ensure_ascii=False)
    print(f"\nScritto {p}  | linee:{rep['LineString']} marker:{rep['Point']} vuoti:{rep['none']}")

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "Biella")
