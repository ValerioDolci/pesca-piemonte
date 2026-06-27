#!/usr/bin/env python3
"""Corregge i tratti che citano una strada (SP/SR/SS NNN) usando l'incrocio reale
OSM strada×fiume invece della stima LLM. Gate: l'incrocio deve cadere vicino al comune
della zona (default <6km) per evitare match sbagliati (strada/fiume omonimi altrove).

Uso: python3 road_bridges.py            # diagnostica tutti
     python3 road_bridges.py --apply    # applica le correzioni affidabili
"""
import sys, json, glob, re, math, time, urllib.request, urllib.parse, unicodedata
from pathlib import Path
import resolve_tracts as R
import tract_agent_tool as T

ROOT = Path(__file__).parent
ISO = {"Torino":"IT-TO","Biella":"IT-BI","Novara":"IT-NO","VCO":"IT-VB",
       "Vercelli":"IT-VC","Cuneo":"IT-CN","Alessandria":"IT-AL","Valle d'Aosta":"IT-23"}
ROAD = re.compile(r'\b(S\.?[PRS]\.?)\s*\.?\s*n?\.?\s*(\d{1,4})', re.I)
GATE_KM = 6.0
def deacc(s): return "".join(c for c in unicodedata.normalize("NFD",s) if unicodedata.category(c)!="Mn")
_rcache = {}

def fetch_road(prov, typ, num):
    key=(prov,typ,num)
    if key in _rcache: return _rcache[key]
    q=(f'[out:json][timeout:60];area["ISO3166-2"="{ISO[prov]}"]->.b;'
       f'way[highway][ref~"{typ} ?{num}([^0-9]|$)",i](area.b);out geom;')
    try:
        r=json.load(urllib.request.urlopen(urllib.request.Request("https://overpass-api.de/api/interpreter",
            data=urllib.parse.urlencode({"data":q}).encode(),headers={"User-Agent":"pesca/0.1"}),timeout=70))
        pts=[(p["lat"],p["lon"]) for w in r["elements"] if w.get("geometry") for p in w["geometry"]]
    except Exception: pts=[]
    _rcache[key]=pts; time.sleep(1.0); return pts

def river_pts(prov, river):
    ways=R.load_ways(prov)
    k=deacc(re.sub(r'\b(torrente|rio|fiume|canale|naviglio|rii|torrenti)\b','',river.lower())).split("(")[0].strip()
    k=re.split(r'\s+di\s+|\s+-\s+|,',k)[0].strip()
    if len(k)<2: return [],None
    line=None; comps=R.river_components(ways,k)
    pts=[p for w in ways if k and re.search(r'\b'+re.escape(k)+r'\b',deacc(w["name"].lower())) for p in w["geom"]]
    return pts, comps

def intersect(road, rpts):
    if not road or not rpts: return None
    return min(((R.hav(s,rp),rp) for s in road for rp in rpts), key=lambda x:x[0])

def main(apply=False):
    comuni=json.load(open(ROOT/"data/processed/comuni_coords.json"))
    fixes=[]
    for zf in sorted(glob.glob(str(ROOT/"data/processed/*/zone_*.json"))):
        z=json.load(open(zf)); prov=z["provincia"]
        for it in z["zone"]:
            m=ROAD.search(it.get("tratto",""))
            if not m: continue
            typ=m.group(1).upper().replace(".",""); num=m.group(2)
            cm=it["comune"].split(" - ")[0].split("/")[0].strip()
            cc=comuni.get(f"{cm}|{prov}"); cpt=(cc["lat"],cc["lon"]) if cc else None
            road=fetch_road(prov,typ,num)
            rpts,comps=river_pts(prov,it["corso_acqua"])
            inter=intersect(road,rpts)
            if not inter or inter[0]>200:
                print(f"  {it['id']:12} {typ}{num:4} SKIP (no incrocio pulito: {'road' if not road else 'fiume' if not rpts else 'gap %.0f'%inter[0]})"); continue
            gap,pt=inter
            dcom=R.hav(pt,cpt) if cpt else 0
            if cpt and dcom>GATE_KM*1000:
                print(f"  {it['id']:12} {typ}{num:4} SKIP (incrocio a {dcom/1000:.1f}km dal comune -> match sbagliato)"); continue
            fixes.append((prov,it["id"],it,pt,gap,comps))
            print(f"  {it['id']:12} {typ}{num:4} incrocio OK gap {gap:.0f}m, {dcom/1000:.1f}km dal comune -> {'APPLICO' if apply else 'pronto'}")
    if apply:
        for prov,zid,it,pt,gap,comps in fixes: apply_fix(prov,zid,it,pt,comps)
    return fixes

def apply_fix(prov,zid,it,pt,comps):
    """Posiziona l'estremo-ponte all'incrocio reale; l'altro estremo bounded:
    confluenza vera (se affluente in OSM e <3km) altrimenti tratto simmetrico attorno al ponte. Cap 3km."""
    line=R.pick_component(comps, pt) if comps else None
    if not line: print(f"    {zid}: niente linea"); return
    i_road=R.nearest_idx(line,pt)
    tr=deacc(it.get("tratto","").lower())
    def walk(i0,m,step):
        acc=0;i=i0
        while 0<=i+step<len(line) and acc<m: acc+=R.hav(line[i],line[i+step]); i+=step
        return i
    ways=R.load_ways(prov)
    # estensione (somma dei numeri "N m"); default 300
    nums=[int(x) for x in re.findall(r'(\d{2,4})\s*(?:m|metri)\b',tr)]
    half = (sum(nums) if nums else 600)//2
    half = min(half, 1500)  # cap lato a 1.5km
    other=None
    mc=re.search(r'conflu\w*\s+(?:con\s+)?(?:il|lo|la|l\'|del|dei)?\s*(?:fiume|torrente|rio)?\s*([a-zà-ù][\w\' ]+)',tr)
    if mc:
        trib=mc.group(1).split(" in ")[0].split(" all")[0].strip()
        k=re.split(r'\s+-\s+|,| del | della ',trib)[0].strip()
        tpts=[p for w in ways if len(k)>=3 and re.search(r'\b'+re.escape(k)+r'\b',deacc(w["name"].lower())) for p in w["geom"]]
        if tpts:
            j=min(range(len(line)),key=lambda i:min(R.hav(line[i],tp) for tp in tpts))
            if R.hav(line[i_road],line[j])<3000: other=j
    if other is None:
        a=walk(i_road,half,-1); b=walk(i_road,half,1); other=None
        i1,i2=a,b
    if other is not None: a,b=sorted((i_road,other))
    else: a,b=sorted((i1,i2))
    # cap totale 3km attorno al ponte
    while sum(R.hav(line[k],line[k+1]) for k in range(a,b))>3000:
        if abs(a-i_road)>abs(b-i_road) and a<i_road: a+=1
        elif b>i_road: b-=1
        else: break
    seg=line[a:b+1]
    if len(seg)<2: print(f"    {zid}: seg degenere"); return
    L=sum(R.hav(seg[k],seg[k+1]) for k in range(len(seg)-1))
    gj=ROOT/f"data/processed/{prov.lower()}/tracts_{prov.lower()}.geojson"; fc=json.load(open(gj))
    feat={"type":"Feature","properties":{"id":zid,"tipo":it["tipo"],"comune":it["comune"],
        "corso":it["corso_acqua"],"tratto":it.get("tratto",""),"regola":it.get("regola",""),
        "conf":"alta","len_m":round(L),"metodo":"osm-incrocio-strada"},
        "geometry":{"type":"LineString","coordinates":[[p[1],p[0]] for p in seg]}}
    fc["features"]=[f for f in fc["features"] if f["properties"]["id"]!=zid]+[feat]
    json.dump(fc,open(gj,"w"),ensure_ascii=False)
    print(f"    {zid}: tratto {round(L)}m [alta] applicato")

if __name__=="__main__":
    main(apply="--apply" in sys.argv)
