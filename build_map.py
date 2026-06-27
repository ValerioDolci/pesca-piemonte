#!/usr/bin/env python3
"""Genera la mappa interattiva (Leaflet). Per ogni provincia usa, se presente,
data/processed/<prov>/tracts_<prov>.geojson (tratti precisi LineString + Point fallback);
altrimenti i marker da data/processed/<prov>/zone_<prov>.json (geocodifica comune).
Riproducibile.   Uso: python3 build_map.py  ->  mappa/index.html
"""
import json, glob, html, re
from pathlib import Path

ROOT = Path(__file__).parent
OUT = ROOT / "mappa"; OUT.mkdir(exist_ok=True)
coords = json.load(open(ROOT / "data/processed/comuni_coords.json"))

TIPI = {
    "protezione":   {"label": "Zona di protezione (divieto)", "color": "#9f1239"},
    "no_kill":      {"label": "No-kill",                       "color": "#0f766e"},
    "no_kill_cmto": {"label": "No-kill gestione CMTO",         "color": "#3b5b80"},
    "turistica":    {"label": "Zona turistica",                "color": "#b45309"},
    "ddep":         {"label": "Diritti esclusivi (D.D.E.P.)",  "color": "#6b21a8"},
    "concessione":  {"label": "Acque in concessione/riserva",  "color": "#a16207"},
    "riserva":      {"label": "Riserva",                       "color": "#0d9488"},
    "campo_gara":   {"label": "Campo gara permanente",         "color": "#155e75"},
    "salmonicola":  {"label": "Acque salmonicole",             "color": "#3f6212"},
}

feats, fonti = [], {}

def add_line(props, latlngs):
    feats.append({"kind": "line", **props, "latlngs": latlngs})
def add_point(props, lat, lon):
    feats.append({"kind": "point", **props, "lat": lat, "lon": lon})
def add_multiline(props, lines):
    feats.append({"kind": "multiline", **props, "lines": lines})

# 1) tratti precisi (e punti) dai geojson
added_ids = set()
for gj in sorted(glob.glob(str(ROOT / "data/processed/*/tracts_*.geojson"))):
    fc = json.load(open(gj)); prov = fc["provincia"]; fonti[prov] = fc["fonte"]
    for f in fc["features"]:
        p = f["properties"]; g = f["geometry"]; added_ids.add(p["id"])
        base = {"prov": prov, "tipo": p["tipo"], "comune": p["comune"], "corso": p["corso"],
                "tratto": p["tratto"], "regola": p.get("regola", ""), "conf": p.get("conf", ""),
                "len_m": p.get("len_m"), "id": p["id"]}
        if g["type"] == "LineString":
            add_line(base, [[c[1], c[0]] for c in g["coordinates"]])
        elif g["type"] == "MultiLineString":
            add_multiline(base, [[[c[1], c[0]] for c in seg] for seg in g["coordinates"]])
        else:
            add_point(base, g["coordinates"][1], g["coordinates"][0])

# 2) marker per OGNI zona non gia' resa come tratto/punto (cosi' nulla sparisce dalla mappa)
for zf in sorted(glob.glob(str(ROOT / "data/processed/*/zone_*.json"))):
    z = json.load(open(zf)); prov = z["provincia"]; fonti.setdefault(prov, z["fonte"])
    for it in z["zone"]:
        if it["id"] in added_ids: continue
        pc = None
        for cand in [it["comune"]] + re.split(r"\s*-\s*|/", it["comune"]):
            pc = coords.get(f"{cand.strip()}|{prov}")
            if pc: break
        if not pc: continue
        add_point({"prov": prov, "tipo": it["tipo"], "comune": it["comune"],
                   "corso": it.get("corso_acqua", ""), "tratto": it.get("tratto", ""),
                   "regola": it.get("regola", ""), "conf": "", "len_m": None, "id": it["id"]},
                  pc["lat"], pc["lon"])

bpath = ROOT / "data/processed/province_boundaries.json"
boundaries = json.load(open(bpath)) if bpath.exists() else {}
boundaries_js = json.dumps(boundaries, ensure_ascii=False)
data_js = json.dumps(feats, ensure_ascii=False)
tipi_js = json.dumps(TIPI, ensure_ascii=False)
fonti_html = "<br>".join(f"<b>{html.escape(p)}</b>: {html.escape(f)}" for p, f in fonti.items())
n_line = sum(1 for f in feats if f["kind"] == "line")
n_pt = sum(1 for f in feats if f["kind"] == "point")

HTML = f"""<!DOCTYPE html>
<html lang="it"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Carta Idrografica della Pesca - Piemonte</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  :root {{ --paper:#ece3d0; --paper-2:#e3d8be; --ink:#2c2419; --ink-soft:#5d503b;
    --line:#bcae8e; --copper:#b45309;
    --serif:"Iowan Old Style","Palatino Linotype",Palatino,Charter,Georgia,serif;
    --sans:ui-sans-serif,-apple-system,"Helvetica Neue",sans-serif; }}
  * {{ box-sizing:border-box; }}
  html,body {{ margin:0; height:100%; font-family:var(--sans); color:var(--ink); background:var(--paper); }}
  #map {{ position:absolute; inset:0; }}
  .leaflet-container {{ background:var(--paper); }}
  .panel {{ position:absolute; z-index:1000; top:18px; left:18px; max-width:340px;
    background:linear-gradient(180deg,var(--paper),var(--paper-2)); border:1px solid var(--line);
    border-radius:3px; box-shadow:0 8px 30px rgba(44,36,25,.28), inset 0 0 0 4px rgba(255,255,255,.18);
    padding:18px 20px 16px; max-height:92vh; overflow:auto; }}
  .panel::before {{ content:""; position:absolute; inset:6px; border:1px solid rgba(120,100,60,.35);
    border-radius:2px; pointer-events:none; }}
  .kicker {{ font-size:10px; letter-spacing:.28em; text-transform:uppercase; color:var(--copper);
    font-weight:700; margin:0 0 6px; }}
  h1 {{ font-family:var(--serif); font-weight:600; font-size:23px; line-height:1.12; margin:0; }}
  .sub {{ font-family:var(--serif); font-style:italic; color:var(--ink-soft); font-size:13.5px; margin:8px 0 12px; }}
  .phead {{ display:flex; align-items:flex-start; justify-content:space-between; gap:10px; }}
  .toggle {{ display:none; border:1px solid var(--line); background:rgba(255,255,255,.4); color:var(--ink);
    font-size:20px; line-height:1; padding:6px 10px; border-radius:4px; cursor:pointer; flex:0 0 auto; }}
  .pbody {{ overflow:hidden; }}
  .panel.collapsed .pbody {{ display:none; }}
  .grp {{ font-size:9.5px; letter-spacing:.18em; text-transform:uppercase; color:var(--ink-soft);
    margin:12px 0 5px; font-weight:700; }}
  .row {{ display:flex; flex-wrap:wrap; gap:6px; }}
  .chip {{ font-size:11.5px; padding:3px 9px; border:1px solid var(--line); border-radius:999px;
    cursor:pointer; user-select:none; background:rgba(255,255,255,.25); transition:all .15s; }}
  .chip.off {{ opacity:.4; }}
  .legend {{ list-style:none; margin:6px 0 0; padding:0; }}
  .legend li {{ display:flex; align-items:center; gap:9px; padding:3px 0; font-size:12.5px;
    cursor:pointer; user-select:none; transition:opacity .15s; }}
  .legend li.off {{ opacity:.32; }}
  .legend .dot {{ width:14px; height:14px; border-radius:50%; border:2px solid rgba(0,0,0,.25);
    flex:0 0 auto; box-shadow:0 1px 2px rgba(0,0,0,.3); }}
  .legend .cnt {{ margin-left:auto; font-variant-numeric:tabular-nums; color:var(--ink-soft); font-size:11px; }}
  .foot {{ margin-top:14px; padding-top:10px; border-top:1px dashed var(--line);
    font-size:10.5px; line-height:1.5; color:var(--ink-soft); }}
  .foot b {{ color:var(--copper); }}
  .leaflet-popup-content-wrapper {{ background:var(--paper); color:var(--ink); border:1px solid var(--line);
    border-radius:3px; box-shadow:0 6px 22px rgba(44,36,25,.3); }}
  .leaflet-popup-tip {{ background:var(--paper); border:1px solid var(--line); }}
  .pop .pt {{ font-size:9.5px; letter-spacing:.22em; text-transform:uppercase; font-weight:700; }}
  .pop h3 {{ font-family:var(--serif); font-size:17px; margin:3px 0 2px; }}
  .pop .cm {{ font-style:italic; color:var(--ink-soft); font-size:12.5px; margin:0 0 8px; font-family:var(--serif); }}
  .pop .tr {{ font-size:13px; line-height:1.45; margin:0 0 8px; }}
  .pop .meta {{ font-size:11px; color:var(--ink-soft); line-height:1.5; }}
  .pop .cf {{ display:inline-block; font-size:10px; padding:1px 6px; border-radius:2px; margin-top:4px; }}
  @media (max-width:640px) {{
    .panel {{ max-width:none; left:8px; right:8px; top:8px; padding:12px 14px; }}
    .toggle {{ display:block; }}
    h1 {{ font-size:20px; }}
    .legend li {{ padding:6px 0; font-size:13.5px; }}
    .chip {{ padding:5px 11px; font-size:12.5px; }}
  }}
</style></head><body>
<div id="map"></div>
<div class="panel" id="panel">
  <div class="phead" id="phead">
    <div><p class="kicker">Carta idrografica</p><h1>Dove si pesca</h1></div>
    <button class="toggle" id="toggle" aria-label="Apri/chiudi legenda">&#9776;</button>
  </div>
  <div class="pbody" id="pbody">
    <p class="sub">Piemonte &mdash; tratti e zone per la pesca dilettantistica</p>
    <div class="grp">Provincia</div><div class="row" id="prov"></div>
    <div class="grp">Tipo di zona</div><ul class="legend" id="legend"></ul>
    <div class="foot">
      🧪 <b>Progetto hobbistico, in beta</b> &mdash; dato <b>non ufficiale</b>, può contenere errori. Verifica sempre il regolamento ufficiale.<br>
      Linea = tratto preciso (geometria OSM); cerchio = posizione al comune (da rifinire).<br>
      {fonti_html}
    </div>
  </div>
</div>
<script>
const DATA = {data_js};
const TIPI = {tipi_js};
const BOUNDS = {boundaries_js};
const PROVS = [...new Set(DATA.map(f=>f.prov))].sort();
const activeProv = new Set(PROVS), activeTipo = new Set(Object.keys(TIPI));

const map = L.map('map', {{ zoomControl:true }}).setView([45.5, 8.0], 10);
L.tileLayer('https://{{s}}.basemaps.cartocdn.com/light_all/{{z}}/{{x}}/{{y}}{{r}}.png', {{
  attribution:'&copy; OpenStreetMap, &copy; CARTO', maxZoom:19, opacity:0.9 }}).addTo(map);

// confini provinciali (ogni provincia = soprattassa/licenza separata)
const PROVCOL = {{Torino:'#9f1239', Biella:'#0f766e', Novara:'#155e75', VCO:'#6b21a8', Vercelli:'#7c2d12', "Valle d'Aosta":'#1e3a8a', Cuneo:'#854d0e', Alessandria:'#0f766e'}};
const boundLayers = {{}};
Object.entries(BOUNDS).forEach(([prov,segs])=>{{
  const lg=L.layerGroup();
  segs.forEach(s=>L.polyline(s,{{color:PROVCOL[prov]||'#555',weight:2,opacity:.55,dashArray:'6 5',interactive:false}}).addTo(lg));
  lg.addTo(map); boundLayers[prov]=lg;
}});

const CONFBG = {{alta:'#15803d', media:'#b45309', bassa:'#9f1239'}};
function popup(f){{
  const info=TIPI[f.tipo]||{{}}; const col=info.color||'#555';
  const cf=f.conf? `<span class="cf" style="background:${{CONFBG[f.conf]||'#777'}};color:#fff">conf. ${{f.conf}}</span>`:'';
  return `<div class="pop"><div class="pt" style="color:${{col}}">${{info.label||f.tipo}} &middot; ${{f.prov}}</div>
    <h3>${{f.corso||''}}</h3><p class="cm">${{f.comune}}</p><p class="tr">${{f.tratto||''}}</p>
    <div class="meta">${{f.regola?'<b>'+f.regola+'</b><br>':''}}${{f.len_m?'Lunghezza ~'+f.len_m+' m<br>':''}}Fonte: vademecum</div>${{cf}}</div>`;
}}
const objs=[];
function addObj(o,f,clickable){{ if(clickable) o.bindPopup(popup(f),{{maxWidth:300}}); o._f=f; o.addTo(map); objs.push(o); }}
DATA.forEach(f=>{{
  const col=(TIPI[f.tipo]||{{}}).color||'#555';
  if(f.kind==='line'){{
    // alone invisibile largo = bersaglio di tocco generoso
    addObj(L.polyline(f.latlngs,{{color:'#000',weight:26,opacity:0,lineCap:'round',lineJoin:'round'}}),f,true);
    addObj(L.polyline(f.latlngs,{{color:col,weight:5,opacity:.95,dashArray:f.conf==='bassa'?'7':null,interactive:false}}),f,false);
  }} else if(f.kind==='multiline'){{
    // intero corso del fiume: ogni segmento OSM separato (niente salti)
    f.lines.forEach(seg=>{{
      addObj(L.polyline(seg,{{color:'#000',weight:20,opacity:0,lineCap:'round'}}),f,true);
      addObj(L.polyline(seg,{{color:col,weight:3.5,opacity:.8,interactive:false}}),f,false);
    }});
  }} else {{
    // cerchio-bersaglio invisibile + pallino visibile sopra
    addObj(L.circleMarker([f.lat,f.lon],{{radius:16,opacity:0,fillOpacity:0,weight:0}}),f,true);
    addObj(L.circleMarker([f.lat,f.lon],{{radius:7,color:'#2c2419',weight:1.4,fillColor:col,fillOpacity:.85,interactive:false}}),f,false);
  }}
}});
function refresh(){{ objs.forEach(o=>{{ const f=o._f, on=activeProv.has(f.prov)&&activeTipo.has(f.tipo);
  if(on&&!map.hasLayer(o)) o.addTo(map); else if(!on&&map.hasLayer(o)) map.removeLayer(o); }});
  Object.entries(boundLayers).forEach(([p,lg])=>{{ const on=activeProv.has(p);
    if(on&&!map.hasLayer(lg)) lg.addTo(map); else if(!on&&map.hasLayer(lg)) map.removeLayer(lg); }}); }}

const provBox=document.getElementById('prov');
PROVS.forEach(p=>{{ const c=document.createElement('span'); c.className='chip'; c.textContent=p;
  c.onclick=()=>{{ c.classList.toggle('off'); activeProv.has(p)?activeProv.delete(p):activeProv.add(p); refresh(); }};
  provBox.appendChild(c); }});
const leg=document.getElementById('legend');
Object.entries(TIPI).forEach(([t,info])=>{{ const n=DATA.filter(f=>f.tipo===t).length; if(!n) return;
  const li=document.createElement('li');
  li.innerHTML=`<span class="dot" style="background:${{info.color}}"></span><span>${{info.label}}</span><span class="cnt">${{n}}</span>`;
  li.onclick=()=>{{ li.classList.toggle('off'); activeTipo.has(t)?activeTipo.delete(t):activeTipo.add(t); refresh(); }};
  leg.appendChild(li); }});

const grp=L.featureGroup(objs); if(objs.length) map.fitBounds(grp.getBounds().pad(0.1));

// pannello collassabile (parte chiuso su mobile)
const panel=document.getElementById('panel');
document.getElementById('toggle').onclick=()=>panel.classList.toggle('collapsed');
if(window.innerWidth<=640) panel.classList.add('collapsed');
</script></body></html>
"""
(OUT / "index.html").write_text(HTML, encoding="utf-8")
print(f"Scritto {OUT/'index.html'}  | tratti(linee):{n_line}  marker:{n_pt}")
