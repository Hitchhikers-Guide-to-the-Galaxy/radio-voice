"""Pull the non-English editions Constitute publishes (es, ar) for every
constitution in that edition's catalogue -> raw/html-<lang>/<id>.json.
Same service as pull.py, same politeness (0.4 s between calls)."""
import json, time, urllib.request, os, sys
LANGS = sys.argv[1:] or ["es", "ar"]
for lang in LANGS:
    cat = f"raw/constitutions.{lang}.json"
    if not os.path.exists(cat):
        with urllib.request.urlopen(f"https://www.constituteproject.org/service/constitutions?lang={lang}", timeout=60) as r:
            open(cat, "wb").write(r.read())
    cons = json.load(open(cat))
    os.makedirs(f"raw/html-{lang}", exist_ok=True)
    done = 0
    for c in cons:
        cid = c["id"]; out = f"raw/html-{lang}/{cid}.json"
        if os.path.exists(out) and os.path.getsize(out) > 1000: done += 1; continue
        try:
            with urllib.request.urlopen(f"https://www.constituteproject.org/service/html?lang={lang}&cons_id={cid}", timeout=90) as r:
                open(out, "wb").write(r.read())
            done += 1
        except Exception as e:
            print("FAIL", lang, cid, e, file=sys.stderr)
        time.sleep(0.4)
    print("pulled", lang, done, "of", len(cons), flush=True)
