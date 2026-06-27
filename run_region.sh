#!/usr/bin/env bash
# Orchestratore geometria -> QA -> build per una nuova area.
# Prerequisiti (lavoro umano, vedi PIPELINE.md):
#   - data/processed/<area>/zone_<area>.json   (zone estratte dalla fonte)
#   - data/processed/<area>/osm_waterways.json (Overpass per ISO)
#   - comuni geocodificati in comuni_coords.json
#   - voce ISO in road_bridges.ISO
# NON pubblica: il push resta manuale dopo review.
#
# Uso: ./run_region.sh <Area>            es. ./run_region.sh Liguria
#      ./run_region.sh <Area> --web      (raffina i [bassa] con WebSearch, piu' lento)
set -euo pipefail
cd "$(dirname "$0")"
PY="/Users/flaviacasini/claude-bot/venv/bin/python3"
export PATH="/opt/homebrew/bin:$PATH"          # node per claude/sonnet
AREA="${1:?Uso: ./run_region.sh <Area> [--web]}"
WEB=""; [ "${2:-}" = "--web" ] && WEB="--web"
al=$(echo "$AREA" | tr '[:upper:]' '[:lower:]')

[ -f "data/processed/$al/zone_$al.json" ]      || { echo "manca zone_$al.json"; exit 1; }
[ -f "data/processed/$al/osm_waterways.json" ] || { echo "manca osm_waterways.json (Overpass per ISO)"; exit 1; }

echo "==> 1/8 estremi deterministici";       $PY auto_estremi.py   "$AREA" || true
echo "==> 2/8 taglio sulla linea OSM";        $PY resolve_tracts.py "$AREA" || true
echo "==> 3/8 incroci strada x fiume";        $PY road_bridges.py   --apply  || true
echo "==> 4/8 frazioni/localita (Nominatim)"; $PY place_resolver.py --apply  || true
echo "==> 5/8 tratti difficili (Sonnet)";     $PY sonnet_resolve.py "$AREA" --markers $WEB || true
echo "==> 6/8 interi-corso (salmonicole/DDEP)";$PY whole_rivers.py  "$AREA"  || true
echo "==> 7/8 laghi sullo specchio d'acqua";  $PY lakes_geocode.py  --apply  || true
echo "==> QA";                                 $PY qa_audit.py       "$AREA"  || echo "QA: bloccanti da risolvere!"
echo "==> 8/8 build mappa";                    $PY build_map.py
cp mappa/index.html index.html
echo "FATTO. Rivedi la mappa, poi: git add -A && git commit ... && git push origin main"
