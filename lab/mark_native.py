"""Write native: true (and runner_up_for) into voices.json from palette.json."""
import json, os
R = os.path.expanduser("~/Code/radio-voice"); v = json.load(open(f"{R}/voices.json")); p = json.load(open(f"{R}/lab/palette.json")); res = json.load(open(f"{R}/lab/lab-results.json"))
by_voice = {n: x for n, x in v.items() if isinstance(x, dict) and "voice" in x}
def reg(vid, engine): return next((n for n, x in by_voice.items() if x.get("engine") == engine and (x["voice"] == vid or x["voice"].endswith("/" + vid))), None)
for x in by_voice.values():
    for k in ("native", "native_basis", "lab_cer", "runner_up_for"): x.pop(k, None)
for lang, d in p.items():
    n = reg(d["default"], d["engine"])
    if n: v[n].update(native=True, native_basis=d["basis"], lab_cer=d["cer"], native_for=lang)
    ru = reg(d["runner_up"], next((r["engine"] for r in res if r["voice"] == d["runner_up"]), "")) if d.get("runner_up") else None
    if ru: v[ru]["runner_up_for"] = lang
    print(lang, "->", n, "| runner-up", ru)
json.dump(v, open(f"{R}/voices.json", "w"), indent=2, ensure_ascii=False)
