#!/usr/bin/env python3
"""Risolve gli estremi dei tratti chiamando Sonnet via `claude --print` (subscription).
Una chiamata per tratto: il ragionamento resta nel subprocess, NON nel contesto del chiamante.

Uso:
  python3 sonnet_resolve.py <Prov> ID1 ID2 ...      # tratti specifici
  python3 sonnet_resolve.py <Prov> --markers        # tutti i marker risolvibili (fiume in OSM)
  python3 sonnet_resolve.py <Prov> --markers --web   # consente WebSearch a Sonnet (piu' lento/preciso)
"""
import sys, json, subprocess, os, re
from pathlib import Path
import resolve_tracts as R
import tract_agent_tool as T

ROOT = Path(__file__).parent
CLAUDE = "/opt/homebrew/bin/claude"
ENV = {**os.environ, "PATH": "/opt/homebrew/bin:" + os.environ.get("PATH","")}

PROMPT = """Sei un geolocalizzatore di tratti fluviali per una mappa della pesca in Piemonte.
Ti do un tratto di fiume descritto in burocratese e la polilinea reale del fiume (punti idx,lat,lon da MONTE idx0 a VALLE).
Individua le coordinate di INIZIO e FINE del tratto, che DEVONO cadere sul fiume (vicino a un punto della polilinea).
Usa la descrizione, la tua conoscenza geografica del Piemonte e il ragionamento sulla polilinea (confluenze = nodi; "per N m a monte/valle" = cammina N metri lungo la linea; "tutto il corso" = intera polilinea; frazioni/paesi = posizione nota).
Se c'e' una lunghezza dichiarata, la distanza inizio-fine deve esserne coerente.

DATI:
{payload}

Rispondi con SOLO questo JSON su una riga, nessun altro testo:
{{"inizio":{{"lat":<f>,"lon":<f>,"riferimento":"<x>","confidenza":"alta|media|bassa"}},"fine":{{"lat":<f>,"lon":<f>,"riferimento":"<x>","confidenza":"alta|media|bassa"}},"lunghezza_attesa_m":<int|null>}}"""

def build_payload(prov, zone, line, cpt):
    near = [p for p in line if cpt and R.hav(p, cpt) < 6000] or line
    step = max(1, len(near)//50)
    samp = [{"idx": k, "lat": round(p[0],5), "lon": round(p[1],5)} for k,p in enumerate(near[::step])]
    return json.dumps({"comune": zone["comune"], "corso_acqua": zone["corso_acqua"],
                       "descrizione_tratto": zone.get("tratto",""),
                       "comune_coord": ({"lat":round(cpt[0],5),"lon":round(cpt[1],5)} if cpt else None),
                       "fiume_polyline_monte_a_valle": samp}, ensure_ascii=False)

def call_sonnet(prompt, web=False):
    # prompt via stdin: evita che il flag variadico --allowedTools si mangi il prompt
    cmd = [CLAUDE, "--print", "--model", "sonnet"]
    if web: cmd += ["--allowedTools", "WebSearch"]
    r = subprocess.run(cmd, input=prompt, env=ENV, capture_output=True, text=True, timeout=300)
    return r.stdout

def resolve(prov, zid, web=False):
    zone = T.load_zone(prov, zid)
    line, cpt = T.river_line(prov, zone)
    if not line:
        return f"  {zid}: SKIP (fiume non in OSM)"
    out = call_sonnet(PROMPT.format(payload=build_payload(prov, zone, line, cpt)), web)
    try:
        data = T._parse_agent(out)
    except SystemExit:
        return f"  {zid}: NO-JSON (rivedere)"
    # GATE qualita': controlla che gli estremi cadano sul fiume e il tratto non sia degenere
    ini = (data["inizio"]["lat"], data["inizio"]["lon"]); fin = (data["fine"]["lat"], data["fine"]["lon"])
    si = R.hav(line[R.nearest_idx(line, ini)], ini); sf = R.hav(line[R.nearest_idx(line, fin)], fin)
    if si > 250 or sf > 250:
        return f"  {zid}: SCARTATO (estremo a {round(max(si,sf))}m dal fiume) -> resta marker"
    data["_metodo"] = "sonnet-web" if web else "sonnet"
    L, conf, sid, sfd = T.apply_data(prov, zid, data, line=line, zone=zone)
    if L < 15:
        # tratto degenere (es. foce = punto): meglio marker
        gj = ROOT / f"data/processed/{prov.lower()}/tracts_{prov.lower()}.geojson"
        fc = json.load(open(gj)); fc["features"] = [f for f in fc["features"] if f["properties"]["id"] != zid]
        json.dump(fc, open(gj, "w"), ensure_ascii=False)
        return f"  {zid}: SCARTATO (tratto {L}m degenere/foce) -> resta marker"
    exp = data.get("lunghezza_attesa_m")
    chk = "" if not exp else (" OK" if abs(L-exp) < max(80, exp*0.4) else " ⚠len")
    return f"  {zid}: {L}m [{conf}] snap({sid},{sfd}){chk}"

def markers_todo(prov):
    gj = ROOT / f"data/processed/{prov.lower()}/tracts_{prov.lower()}.geojson"
    done = {f["properties"]["id"] for f in json.load(open(gj))["features"]
            if f["geometry"]["type"]=="LineString"} if gj.exists() else set()
    zone = json.load(open(ROOT / f"data/processed/{prov.lower()}/zone_{prov.lower()}.json"))["zone"]
    out = []
    for z in zone:
        if z["id"] in done: continue
        line, _ = T.river_line(prov, z)
        if line: out.append(z["id"])
    return out

if __name__ == "__main__":
    prov = sys.argv[1]; args = sys.argv[2:]
    web = "--web" in args; args = [a for a in args if a != "--web"]
    ids = markers_todo(prov) if "--markers" in args else args
    print(f"{prov}: risolvo {len(ids)} tratti via Sonnet{' +web' if web else ''}")
    for zid in ids:
        try: print(resolve(prov, zid, web), flush=True)
        except Exception as e: print(f"  {zid}: ERR {e}", flush=True)
