#!/usr/bin/env python3
"""Sistema i tratti/marker che citano una FRAZIONE/LOCALITA' geolocalizzandola con
Nominatim e agganciandola al fiume (come per le strade). Gate: il luogo deve cadere
vicino al comune (<8km) e vicino al fiume (<400m). Riusa road_bridges.apply_fix per il taglio.

Uso: python3 place_resolver.py          # diagnostica
     python3 place_resolver.py --apply  # applica dove affidabile e migliora il corrente
"""
import sys, json, glob, re, time, urllib.request, urllib.parse
from pathlib import Path
import resolve_tracts as R
import tract_agent_tool as T
import road_bridges as RB

ROOT = Path(__file__).parent
GC = ROOT / "data/processed/geocode_cache.json"
_gc = json.load(open(GC)) if GC.exists() else {}
PLACE = re.compile(r'\b(?:frazione|fraz\.|localit[aà]|loc\.|borgata)\s+([A-ZÀ-Ù][a-zà-ù]+(?:\s+[A-ZÀ-Ù][a-zà-ù]+)?)')
SKIP = {"comune","comuni","localita","prossimita","tutto","corrispondenza","direzione","loc"}

def _nominatim(q):
    u="https://nominatim.openstreetmap.org/search?"+urllib.parse.urlencode({"q":q,"format":"json","limit":1})
    try:
        d=json.load(urllib.request.urlopen(urllib.request.Request(u,headers={"User-Agent":"pesca/0.1"}),timeout=20))
        return (float(d[0]["lat"]),float(d[0]["lon"])) if d else None
    except Exception: return None

def _overpass_place(name,comune):
    q=(f'[out:json][timeout:40];area[name="{comune}"][admin_level=8]->.c;'
       f'(node[place][name="{name}"](area.c);nwr["name"="{name}"](area.c););out center 1;')
    for _ in range(2):
        try:
            r=json.load(urllib.request.urlopen(urllib.request.Request("https://overpass-api.de/api/interpreter",
                data=urllib.parse.urlencode({"data":q}).encode(),headers={"User-Agent":"pesca/0.1"}),timeout=50))
            for e in r["elements"]:
                lat=e.get("lat") or e.get("center",{}).get("lat"); lon=e.get("lon") or e.get("center",{}).get("lon")
                if lat: time.sleep(1.5); return (lat,lon)
            time.sleep(1.5); return None
        except Exception: time.sleep(8)
    return None

def geocode(q, place=None, comune=None):
    if q in _gc: return tuple(_gc[q]) if _gc[q] else None
    r=_nominatim(q); time.sleep(1.0)
    if r is None and place and comune:           # fallback Overpass per luoghi oscuri
        r=_overpass_place(place, comune)
    _gc[q]=list(r) if r else None; json.dump(_gc,open(GC,"w"),ensure_ascii=False); return r

def main(apply=False):
    comuni=json.load(open(ROOT/"data/processed/comuni_coords.json"))
    geo={}
    for gj in glob.glob(str(ROOT/"data/processed/*/tracts_*.geojson")):
        for f in json.load(open(gj))["features"]:
            g=f["geometry"]
            if g["type"]=="LineString":
                c=g["coordinates"]; geo[f["properties"]["id"]]=(c[len(c)//2][1],c[len(c)//2][0])
    fixes=0
    for zf in sorted(glob.glob(str(ROOT/"data/processed/*/zone_*.json"))):
        z=json.load(open(zf)); prov=z["provincia"]
        for it in z["zone"]:
            places=[p for p in PLACE.findall(it.get("tratto","")) if p.lower() not in SKIP]
            if not places: continue
            cm=it["comune"].split(" - ")[0].split("/")[0].strip()
            cc=comuni.get(f"{cm}|{prov}"); cpt=(cc["lat"],cc["lon"]) if cc else None
            rpts,comps=RB.river_pts(prov,it["corso_acqua"])
            if not comps: continue
            line=R.pick_component(comps,cpt) if cpt else comps[0]
            # prova il primo luogo che geocodifica vicino a comune+fiume
            anchor=None; used=None
            for pl in places:
                g=geocode(f"{pl}, {cm}, {prov}, Italia", place=pl, comune=cm)
                if not g: continue
                if cpt and R.hav(g,cpt)>8000: continue
                j=R.nearest_idx(line,g); snap=R.hav(line[j],g)
                if snap>400: continue
                anchor=line[j]; used=pl; break
            if not anchor: continue
            cur=geo.get(it["id"]); dist=R.hav(cur,anchor) if cur else None
            status = "MARKER->tratto" if cur is None else (f"sposta {dist/1000:.1f}km" if dist and dist>500 else "ok (vicino)")
            print(f"  {it['id']:12} {it['corso_acqua'][:16]:16} '{used}' -> {status}")
            if apply and (cur is None or (dist and dist>500)):
                RB.apply_fix(prov,it["id"],it,anchor,comps); fixes+=1
    if apply: print("applicati/corretti:",fixes)

if __name__=="__main__":
    main(apply="--apply" in sys.argv)
