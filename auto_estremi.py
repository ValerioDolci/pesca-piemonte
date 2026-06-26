#!/usr/bin/env python3
"""Auto-estrattore di hint 'estremi' dal testo italiano del tratto.
Legge ogni zona di un file zone_<prov>.json e, se non ha gia' 'estremi', prova a
dedurli dalla descrizione (campo 'auto':true). Euristico: copre i casi chiari,
il resto resta senza estremi (-> marker nel motore geometria).

Uso: python3 auto_estremi.py <Provincia>
"""
import sys, re, json
from pathlib import Path
ROOT = Path(__file__).parent

CONFL = re.compile(r"conflu\w*\s+(?:con\s+)?(?:il|lo|la|l'|i)?\s*"
                   r"(?:fiume|torrente|rio|lago|canale|t\.)?\s*([A-ZÀ-Ù][\wàèéìòùÀ-Ù']+(?:\s+[A-ZÀ-Ù][\wàèéìòùÀ-Ù']+)?)",
                   re.I)
FRAZ = re.compile(r"(?:frazione|fraz\.|localit[aà]|loc\.)\s+([A-ZÀ-Ù][\wàèéìòù']+(?:\s+[A-ZÀ-Ù][\wàèéìòù']+)?)", re.I)
OFFSET = re.compile(r"(?:per\s+(?:una\s+lunghezza\s+di\s+)?|per\s+)?(?:circa\s+)?(\d+(?:[.,]\d+)?)\s*(km|chilometr\w*|m\b|mt\b|metri)", re.I)

def has(t, *words): return any(w in t for w in words)

def extract(tratto, comune):
    t = tratto.strip(); tl = t.lower()
    if not tl: return None
    # intero corso
    if has(tl, "tutto il corso", "tutto il suo corso", "intero corso", "per tutto il"):
        return {"da": {"intero": True}, "a": {"intero": True}, "auto": True}
    da = a = None
    # primo e secondo riferimento per ordine: split sui connettori "a valle/a monte/fino/al/alla/sino"
    # endpoint DA (parte iniziale "dal/dalla X")
    head = re.split(r"\b(?:a valle|a monte|fino|sino|al ponte|alla conflu|alla foce|all'immission)\b", tl, maxsplit=1)
    first = head[0]
    rest = tl[len(first):]
    def res_ref(seg):
        m = CONFL.search(seg)
        if m: return {"confluenza": m.group(1).strip().title()}
        if has(seg, "sorgent", "origin"): return {"sorgente": True}
        if has(seg, "foce", "sbocco"): return {"foce": True}
        m = FRAZ.search(seg)
        if m: return {"luogo": f"{m.group(1).strip()}, {comune}"}
        return None
    da = res_ref(first)
    a = res_ref(rest)
    # offset: "per N m a monte/valle" -> un estremo offset relativo all'altro
    mo = OFFSET.search(t)
    if mo and (da or a):
        val = float(mo.group(1).replace(",", ".")); unit = mo.group(2).lower()
        meters = int(val*1000) if unit.startswith(("km", "chilom")) else int(val)
        # se manca un estremo, usalo come offset dall'altro
        if da and not a: a = {"offset_m": meters, "auto": True}
        elif a and not da: da = {"offset_m": meters, "auto": True}
    if da and a:
        return {"da": da, "a": a, "auto": True}
    return None

def main(prov):
    p = ROOT / f"data/processed/{prov.lower()}/zone_{prov.lower()}.json"
    d = json.load(open(p)); n = 0
    for z in d["zone"]:
        if z.get("estremi"): continue
        e = extract(z.get("tratto", ""), z["comune"].split(" - ")[0].split("/")[0].strip())
        if e: z["estremi"] = e; n += 1
    json.dump(d, open(p, "w"), ensure_ascii=False, indent=2)
    print(f"{prov}: estremi auto-estratti per {n}/{len(d['zone'])} zone")

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "VCO")
