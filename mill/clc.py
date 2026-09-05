"""CLC 2026 filter: Protocols / Holding and Letting Go. Keeps units carrying
the topics that speak to holding (unamendable, tenure, term), letting go
(secession, emergency, referendum), and the commons (environment, resources,
water, indigenous self-governance, customary law, solidarity, dignity), plus
every preamble — the most quotable part of any constitution."""
import json, sys
KEYS = {"unamend","amend","seccess","em","referen","env","resrce","water","indpolgr6",
        "custlaw","solid","dignity","preamble","motive","god","selfdet","proprght",
        "transfer","econplan","hosterml","hogterml","lhtrmlim","conlim","intprop"}
WORDS = ("generation","future","commons","common heritage","steward","trust","hold in trust",
         "posterity","unborn","forever","perpetual","eternal","never","time","silence",
         "protocol","custom","ancestor","mother earth","nature","land","water","forest","sea")
us = [json.loads(l) for l in open("scored.jsonl")]
keep = []
for u in us:
    if not u.get("in_force"): continue
    tk = KEYS & set(u["topics"]); tw = [w for w in WORDS if w in u["text"].lower()]
    if tk or tw:
        u["clc"] = sorted(tk) + tw; keep.append(u)
with open("clc.jsonl", "w") as f:
    for u in keep: f.write(json.dumps(u, ensure_ascii=False) + "\n")
print(len(keep), "CLC candidates of", sum(1 for u in us if u.get("in_force")), "in-force units")
