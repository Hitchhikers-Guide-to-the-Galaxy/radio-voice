"""Top CLC candidates, one per passage: best unit per (constitution, heading),
at most 3 per constitution, top N overall -> shortlist.md for the reading pass."""
import json, sys
N = int(sys.argv[1]) if len(sys.argv) > 1 else 150
us = [json.loads(l) for l in open("clc.jsonl")]
best = {}
for u in us:
    k = (u["cons_id"], u["heading"])
    if k not in best or u["score"] > best[k]["score"]: best[k] = u
rows = sorted(best.values(), key=lambda u: -u["score"])
per = {}; out = []
for u in rows:
    if per.get(u["cons_id"], 0) >= 3: continue
    per[u["cons_id"]] = per.get(u["cons_id"], 0) + 1
    out.append(u)
    if len(out) >= N: break
with open("shortlist.jsonl", "w") as f:
    for u in out: f.write(json.dumps(u, ensure_ascii=False) + "\n")
with open("shortlist.md", "w") as f:
    for i, u in enumerate(out, 1):
        f.write(f"### {i}. {u['title']} — {u['heading'][:70]}\n{u['score']:.3f} d{u['d']} c{u['c']} l{u['l']} {u['words']}w [{', '.join(u['clc'][:6])}]\n\n{u['text']}\n\n")
print(len(out), "shortlisted from", len(rows), "passages across", len(per), "constitutions")
