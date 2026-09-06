#!/usr/bin/env python3
"""Join the bench results (kokoro, piper, mms) with the Whisper CER scores into
lab-results.json, choose a provisional default voice per language, and draw the
voice quality chart (CER against realtime factor; listener score axis reserved).

  python3 aggregate.py            # writes lab-results.json, voice-quality.svg, palette.json
"""
import json, os, glob, collections
HERE = os.path.dirname(os.path.abspath(__file__))
def load(p): return json.load(open(p)) if os.path.exists(p) else []
rows = []
for f in ("kokoro-results.json", "piper-results.json", "piper-extra.json", "kokoro-extra.json") + tuple(os.path.basename(p) for p in glob.glob(os.path.join(HERE, "mms-results-*.json"))):
    for r in load(os.path.join(HERE, f)):
        if "error" in r: rows.append(dict(r, cer=None)); continue
        rows.append(r)
cer = load(os.path.join(HERE, "cer-results.json")) or {}
if isinstance(cer, list): cer = {}
listeners = load(os.path.join(HERE, "listeners.json")) or {}
if isinstance(listeners, list): listeners = {}
for r in rows:
    c = cer.get(r.get("file", ""))
    r["cer"] = c["cer"] if c else None; r["hyp"] = c["hyp"][:160] if c else ""
    L = listeners.get(r.get("file", ""))
    r["listener"] = L.get("score") if L else None; r["radio_ok"] = L.get("radio_ok") if L else None
    r["provenance"] = {"kokoro": "Kokoro-82M via kokoro-onnx, Apache-2.0, voice trained on read speech by hexgrad", "piper": "Piper (rhasspy) VITS voice, per-voice licence in its card, single native speaker unless noted", "mms": "Meta MMS-TTS VITS, CC-BY-NC 4.0, single speaker from read Bible audio"}.get(r.get("engine"), "")
rows.sort(key=lambda r: (r["lang"], r["cer"] if r["cer"] is not None else 9, -(r.get("rtf") or 0)))
# provisional palette: lowest CER per language; ties broken by realtime factor; listener score overrides when present
palette = {}
by_lang = collections.defaultdict(list)
for r in rows:
    if r["cer"] is not None and not r["lang"].endswith("-CH") and r["lang"] != "rm": by_lang[r["lang"]].append(r)   # the Swiss roll-call rows measure Whisper, not the voice
for lang, rs in by_lang.items():
    rated = [r for r in rs if r["listener"] is not None]
    best = sorted(rated, key=lambda r: (-r["listener"], r["cer"]))[0] if rated else sorted(rs, key=lambda r: (r["cer"], -r["rtf"]))[0]
    runner = [r for r in sorted(rs, key=lambda r: (r["cer"], -r["rtf"])) if r is not best][:1]
    palette[lang] = dict(default=best["voice"], engine=best["engine"], cer=best["cer"], rtf=best["rtf"], machine=best["machine"], basis="listener" if rated else "provisional: lowest Whisper CER, then realtime factor; no native listener yet",
                         runner_up=(runner[0]["voice"] if runner else None), candidates=len(rs))
json.dump(rows, open(os.path.join(HERE, "lab-results.json"), "w"), indent=1, ensure_ascii=False)
json.dump(palette, open(os.path.join(HERE, "palette.json"), "w"), indent=1, ensure_ascii=False)

# chart: x = CER (0..0.5+), y = realtime factor (log), colour = engine, ring = provisional default; listener score would be the y axis once it exists
W, H = 1200, 640; ML, MR, MT, MB = 80, 40, 40, 70
pts = [r for r in rows if r["cer"] is not None and r.get("rtf")]
xmax = max(0.3, max(r["cer"] for r in pts) * 1.1); import math
ymin, ymax = min(r["rtf"] for r in pts) / 1.5, max(r["rtf"] for r in pts) * 1.5
def X(c): return ML + c / xmax * (W - ML - MR)
def Y(v): return MT + (1 - (math.log(v) - math.log(ymin)) / (math.log(ymax) - math.log(ymin))) * (H - MT - MB)
COL = {"kokoro": "#d9822b", "piper": "#4f6d8f", "mms": "#2e8b57"}
o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="\'Helvetica Neue\',Helvetica,Arial,sans-serif" font-size="13">',
     f'<rect width="{W}" height="{H}" fill="#fbf9f4"/>',
     f'<line x1="{ML}" y1="{H-MB}" x2="{W-MR}" y2="{H-MB}" stroke="#888"/><line x1="{ML}" y1="{MT}" x2="{ML}" y2="{H-MB}" stroke="#888"/>',
     f'<line x1="{X(0.05)}" y1="{MT}" x2="{X(0.05)}" y2="{H-MB}" stroke="#c94c4c" stroke-dasharray="4 4"/><text x="{X(0.05)+4}" y="{MT+14}" fill="#c94c4c">pass line: CER 0.05</text>',
     f'<line x1="{ML}" y1="{Y(1)}" x2="{W-MR}" y2="{Y(1)}" stroke="#999" stroke-dasharray="4 4"/><text x="{W-MR-90}" y="{Y(1)-4}" fill="#666">1x realtime</text>',
     f'<text x="{(ML+W-MR)/2}" y="{H-24}" text-anchor="middle">Whisper character error rate on Article 1 (lower is better)</text>',
     f'<text transform="translate(20,{(MT+H-MB)/2}) rotate(-90)" text-anchor="middle">realtime factor on the named machine (higher is faster)</text>']
for c in (0, 0.1, 0.2, 0.3, 0.4, 0.5):
    if c <= xmax: o.append(f'<text x="{X(c)}" y="{H-MB+16}" text-anchor="middle" fill="#666">{c:.2f}</text>')
for v in (0.25, 0.5, 1, 2, 4, 8):
    if ymin <= v <= ymax: o.append(f'<text x="{ML-8}" y="{Y(v)+4}" text-anchor="end" fill="#666">{v}x</text>')
for r in pts:
    x, y = X(r["cer"]), Y(r["rtf"]); col = COL.get(r["engine"], "#999"); dflt = palette.get(r["lang"], {}).get("default") == r["voice"]
    o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{9 if dflt else 6}" fill="{col}" stroke="{"#222" if dflt else "#fff"}" stroke-width="{2.5 if dflt else 1.2}"><title>{r["lang"]} · {r["voice"]} · CER {r["cer"]} · {r["rtf"]}x on {r["machine"]}</title></circle>')
    o.append(f'<text x="{x+11:.1f}" y="{y+4:.1f}" fill="#333">{r["lang"]} {r["voice"].replace("_", " ")[:22]}</text>')
o.append(f'<g font-size="13"><rect x="{W-330}" y="{MT+8}" width="290" height="88" rx="6" fill="#fff" fill-opacity="0.9"/>'
         f'<text x="{W-318}" y="{MT+28}" font-weight="bold">Voice quality, Phase 2 bench</text>'
         + "".join(f'<circle cx="{W-310}" cy="{MT+46+i*18}" r="6" fill="{c}"/><text x="{W-298}" y="{MT+50+i*18}">{n}</text>' for i, (n, c) in enumerate(COL.items()))
         + f'<circle cx="{W-140}" cy="{MT+46}" r="8" fill="#fff" stroke="#222" stroke-width="2.5"/><text x="{W-126}" y="{MT+50}">provisional default</text></g>')
o.append('</svg>')
open(os.path.join(HERE, "voice-quality.svg"), "w").write("\n".join(o))
print(len(rows), "results;", sum(1 for r in rows if r["cer"] is not None), "scored;", "palette:", {k: v["default"] for k, v in palette.items()})
