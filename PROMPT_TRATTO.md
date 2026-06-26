# Tool: geolocalizzazione tratti via subagente

Pipeline per disegnare con precisione l'inizio/fine di un tratto di pesca, quando la
descrizione cita riferimenti locali (dighe, sbarramenti, briglie, ponti, frazioni) non
presenti in OpenStreetMap.

## Workflow (1 chiamata subagente per tratto)
1. `python3 tract_agent_tool.py prep <Prov> <ID>` → `tmp/agent_in_<ID>.json`
   (contiene descrizione + polilinea reale del fiume da monte a valle).
2. Chiama un subagente `general-purpose` con il PROMPT qui sotto + il path del file input.
3. Salva l'output JSON del subagente in `tmp/agent_out_<ID>.json`.
4. `python3 tract_agent_tool.py apply <Prov> <ID> tmp/agent_out_<ID>.json`
   → aggancia le coord alla geometria OSM, taglia il tratto, verifica la lunghezza,
   aggiorna `data/processed/<prov>/tracts_<prov>.geojson`.
5. `python3 build_map.py` per rigenerare la mappa.

I tratti "facili" (confluenza / sorgente / intero corso / paese / offset) si risolvono
gratis con `auto_estremi.py` + `resolve_tracts.py`. Il subagente serve SOLO per i difficili.

## PROMPT (template, riusabile)

> Sei un geolocalizzatore di tratti fluviali per una mappa della pesca in Piemonte.
> Leggi il file `<PATH agent_in_ID.json>`. Contiene: comune, corso d'acqua,
> descrizione_tratto, comune_coord e `fiume_polyline_da_monte_a_valle` (punti {idx,lat,lon}
> del fiume da monte verso valle).
>
> COMPITO: individua le coordinate di INIZIO e FINE del tratto descritto, lungo la polilinea.
> - Identifica i due estremi dalla descrizione (es. "dallo sbarramento ENEL ... al ponte SP ...").
> - Per localizzarli usa WebSearch (coordinate di dighe/ponti/sbarramenti/frazioni), la tua
>   conoscenza geografica, e il ragionamento sulla polilinea. I punti DEVONO cadere sul fiume.
> - Se la descrizione indica una lunghezza (es. "~150 m", "per 500 m"), usala come verifica:
>   la distanza inizio↔fine deve essere coerente.
> - Attento al verso: la polilinea è ordinata da monte (idx 0) a valle (idx max).
>
> Restituisci SOLO questo JSON (niente altro):
> ```json
> {
>   "id": "<id>",
>   "inizio": {"lat": <float>, "lon": <float>, "riferimento": "<cosa>", "confidenza": "alta|media|bassa", "metodo": "web|conoscenza|polyline"},
>   "fine":   {"lat": <float>, "lon": <float>, "riferimento": "<cosa>", "confidenza": "alta|media|bassa", "metodo": "web|conoscenza|polyline"},
>   "lunghezza_attesa_m": <int|null>,
>   "note": "<incertezze>"
> }
> ```
> Sii onesto sulla confidenza: se un estremo è incerto, mettilo sul punto più probabile e segna "bassa".

## Note di affinamento (dall'uso reale)
- Il subagente spesso premette ragionamento al JSON: il parser di `apply` estrae il primo
  oggetto bilanciato che contiene `inizio`/`fine` (robusto al testo extra).
- `apply` riporta lo snap (distanza coord→fiume) e il check lunghezza (OK/DA VERIFICARE):
  se "DA VERIFICARE" o snap >150 m, rivedere a mano o richiamare il subagente affinando.
- Caso validato: VCO-DIV-08 (Toce, sbarramento ENEL Crevola→ponte Val Vigezzo) → 151 m vs 150 attesi.
