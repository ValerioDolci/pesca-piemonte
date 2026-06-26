#!/usr/bin/env python3
"""TOOL geolocalizzazione tratti via subagente — pipeline pulita e riusabile.

Due modi:
  prep  <Prov> <ID>            -> scrive tmp/agent_in_<ID>.json (polyline fiume + descrizione)
                                  da dare in pasto al subagente (vedi PROMPT in PROMPT_TRATTO.md)
  apply <Prov> <ID> <file.json>-> legge l'output JSON del subagente (inizio/fine coord),
                                  aggancia alla geometria OSM reale, taglia il tratto,
                                  verifica la lunghezza e AGGIORNA tracts_<prov>.geojson

Il subagente puo' usare WebSearch per i riferimenti locali (dighe, ponti, sbarramenti, frazioni).
Per i tratti "facili" (confluenza/sorgente/intero/luogo/offset) usare prima resolve_tracts.py:
il subagente serve solo per i tratti con riferimenti locali non in OSM.
"""
import sys, json, re
from pathlib import Path
import resolve_tracts as R

ROOT = Path(__file__).parent
TMP = ROOT / "tmp"; TMP.mkdir(exist_ok=True)

def river_line(prov, zone):
    ways = R.load_ways(prov)
    comuni = json.load(open(ROOT / "data/processed/comuni_coords.json"))
    cm = zone["comune"].split(" - ")[0].split("/")[0].strip()
    cc = comuni.get(f"{cm}|{prov}")
    cpt = (cc["lat"], cc["lon"]) if cc else None
    rkey = re.sub(r"\b(torrente|rio|fiume|lago|canale|lanca|lanche|t\.)\b", "",
                  zone["corso_acqua"].lower()).strip().split("(")[0].strip()
    comps = R.river_components(ways, rkey) if rkey else []
    line = R.pick_component(comps, cpt) if (comps and cpt) else (comps[0] if comps else None)
    return line, cpt

def load_zone(prov, zid):
    z = json.load(open(ROOT / f"data/processed/{prov.lower()}/zone_{prov.lower()}.json"))
    for it in z["zone"]:
        if it["id"] == zid: return it
    raise SystemExit(f"id {zid} non trovato")

def prep(prov, zid):
    zone = load_zone(prov, zid)
    line, cpt = river_line(prov, zone)
    if not line:
        print(f"ATTENZIONE: '{zone['corso_acqua']}' non trovato in OSM per {prov}. Tratto non disegnabile su linea.")
    samp = []
    if line and cpt:
        near = [p for p in line if R.hav(p, cpt) < 5000] or line
        step = max(1, len(near)//60)
        samp = [{"idx": k, "lat": round(p[0],5), "lon": round(p[1],5)} for k,p in enumerate(near[::step])]
    out = {"id": zid, "provincia": prov, "comune": zone["comune"], "corso_acqua": zone["corso_acqua"],
           "descrizione_tratto": zone.get("tratto",""),
           "comune_coord": ({"lat":round(cpt[0],5),"lon":round(cpt[1],5)} if cpt else None),
           "fiume_polyline_da_monte_a_valle": samp,
           "compito": "individua coordinate di INIZIO e FINE del tratto descritto, sulla polilinea del fiume"}
    p = TMP / f"agent_in_{zid}.json"; json.dump(out, open(p,"w"), ensure_ascii=False, indent=2)
    print(f"scritto {p}  ({len(samp)} punti polyline)")

def _parse_agent(text):
    # scorre tutti i "{" da sinistra e ritorna il primo oggetto bilanciato che contiene 'inizio'
    starts = [m for m in range(len(text)) if text[m] == "{"]
    for s in starts:
        depth = 0
        for e in range(s, len(text)):
            if text[e] == "{": depth += 1
            elif text[e] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        obj = json.loads(text[s:e+1])
                        if isinstance(obj, dict) and "inizio" in obj and "fine" in obj:
                            return obj
                    except Exception:
                        pass
                    break
    raise SystemExit("nessun JSON valido (con inizio/fine) nell'output del subagente")

def apply_data(prov, zid, data, line=None, zone=None):
    """applica un dict gia' parsato {inizio,fine,...} -> aggiorna geojson, ritorna (len_m, conf, snap_in, snap_fin)."""
    zone = zone or load_zone(prov, zid)
    if line is None:
        line, _ = river_line(prov, zone)
    if not line: raise SystemExit("fiume non in OSM: impossibile agganciare")
    ini = (data["inizio"]["lat"], data["inizio"]["lon"])
    fin = (data["fine"]["lat"], data["fine"]["lon"])
    ia, ib = R.nearest_idx(line, ini), R.nearest_idx(line, fin)
    da, db = R.hav(line[ia], ini), R.hav(line[ib], fin)
    a, b = sorted((ia, ib)); seg = line[a:b+1]
    L = sum(R.hav(seg[i], seg[i+1]) for i in range(len(seg)-1))
    conf_in = data["inizio"].get("confidenza","?"); conf_fi = data["fine"].get("confidenza","?")
    conf = "bassa" if "bassa" in (conf_in, conf_fi) else ("alta" if conf_in==conf_fi=="alta" else "media")
    gj = ROOT / f"data/processed/{prov.lower()}/tracts_{prov.lower()}.geojson"
    fc = json.load(open(gj)) if gj.exists() else {"type":"FeatureCollection","provincia":prov,
          "fonte": json.load(open(ROOT/f'data/processed/{prov.lower()}/zone_{prov.lower()}.json'))["fonte"],"features":[]}
    feat = {"type":"Feature","properties":{"id":zid,"tipo":zone["tipo"],"comune":zone["comune"],
            "corso":zone["corso_acqua"],"tratto":zone.get("tratto",""),"regola":zone.get("regola",""),
            "conf":conf,"len_m":round(L),"metodo":data.get("_metodo","sonnet")},
            "geometry":{"type":"LineString","coordinates":[[p[1],p[0]] for p in seg]}}
    fc["features"]=[f for f in fc["features"] if f["properties"]["id"]!=zid]+[feat]
    json.dump(fc, open(gj,"w"), ensure_ascii=False)
    return round(L), conf, round(da), round(db)

def apply(prov, zid, agent_file):
    zone = load_zone(prov, zid)
    line, cpt = river_line(prov, zone)
    if not line: raise SystemExit("fiume non in OSM: impossibile agganciare")
    data = _parse_agent(open(agent_file).read())
    ini = (data["inizio"]["lat"], data["inizio"]["lon"])
    fin = (data["fine"]["lat"], data["fine"]["lon"])
    ia, ib = R.nearest_idx(line, ini), R.nearest_idx(line, fin)
    da, db = R.hav(line[ia], ini), R.hav(line[ib], fin)
    a, b = sorted((ia, ib)); seg = line[a:b+1]
    L = sum(R.hav(seg[i], seg[i+1]) for i in range(len(seg)-1))
    conf_in = data["inizio"].get("confidenza","?"); conf_fi = data["fine"].get("confidenza","?")
    conf = "bassa" if "bassa" in (conf_in, conf_fi) else ("alta" if conf_in==conf_fi=="alta" else "media")
    # aggiorna tracts geojson
    gj = ROOT / f"data/processed/{prov.lower()}/tracts_{prov.lower()}.geojson"
    fc = json.load(open(gj)) if gj.exists() else {"type":"FeatureCollection","provincia":prov,
          "fonte": json.load(open(ROOT/f'data/processed/{prov.lower()}/zone_{prov.lower()}.json'))["fonte"],"features":[]}
    feat = {"type":"Feature","properties":{"id":zid,"tipo":zone["tipo"],"comune":zone["comune"],
            "corso":zone["corso_acqua"],"tratto":zone.get("tratto",""),"regola":zone.get("regola",""),
            "conf":conf,"len_m":round(L),"metodo":"subagente"},
            "geometry":{"type":"LineString","coordinates":[[p[1],p[0]] for p in seg]}}
    fc["features"]=[f for f in fc["features"] if f["properties"]["id"]!=zid]+[feat]
    json.dump(fc, open(gj,"w"), ensure_ascii=False)
    exp = data.get("lunghezza_attesa_m")
    chk = f" | attesa ~{exp}m -> {'OK' if exp and abs(L-exp)<max(80,exp*0.4) else 'DA VERIFICARE' if exp else 'n/d'}"
    print(f"{zid}: tratto {round(L)}m [{conf}] snap(in {da:.0f}m, fin {db:.0f}m){chk}")

if __name__ == "__main__":
    mode = sys.argv[1]
    if mode=="prep": prep(sys.argv[2], sys.argv[3])
    elif mode=="apply": apply(sys.argv[2], sys.argv[3], sys.argv[4])
    else: raise SystemExit("modi: prep <Prov> <ID> | apply <Prov> <ID> <file.json>")
