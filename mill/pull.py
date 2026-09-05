import json, time, urllib.request, os, sys
B = "https://www.constituteproject.org/service/html?lang=en&cons_id="
cons = json.load(open("raw/constitutions.json"))
os.makedirs("raw/html", exist_ok=True)
done = 0
for c in cons:
    cid = c["id"]; out = f"raw/html/{cid}.json"
    if os.path.exists(out) and os.path.getsize(out) > 1000: done += 1; continue
    try:
        with urllib.request.urlopen(B + cid, timeout=60) as r:
            open(out, "wb").write(r.read())
        done += 1
    except Exception as e:
        print("FAIL", cid, e, file=sys.stderr)
    time.sleep(0.4)
print("pulled", done, "of", len(cons))
