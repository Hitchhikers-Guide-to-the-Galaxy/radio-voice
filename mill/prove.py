"""Does the score surface the known-strange? For each probe, find the best-
scoring in-force unit that contains the phrase, and report its rank inside its
own constitution and across the whole corpus."""
import json, re
PROBES = [
  ("Ecuador_2021",  r"Pacha ?Mama|rights? of nature|Nature.*right to integral respect"),
  ("Bhutan_2008",   r"Gross National Happiness"),
  ("German_Federal_Republic_2014", r"Amendments to this Basic Law affecting the division|inadmissible"),
  ("Japan_1946",    r"renounce war|forever renounce"),
  ("Bolivia_2009",  r"mountains arose|Mother Earth"),
  ("Iceland_2013",  r"nature"),
  ("South_Africa_2012", r"belongs to all who live in it"),
]
us = [json.loads(l) for l in open("scored.jsonl")]
inf = [u for u in us if u.get("in_force")]
gl = {id(u): i+1 for i, u in enumerate(inf)}
for cid, pat in PROBES:
    own = [u for u in inf if u["cons_id"] == cid]
    hits = [u for u in own if re.search(pat, u["text"], re.I)]
    if not hits: print(f"{cid:30s} NO MATCH for /{pat}/ in {len(own)} units"); continue
    b = hits[0]
    print(f"{cid:30s} corpus #{gl[id(b)]:6d} of {len(inf)}  own #{own.index(b)+1:4d} of {len(own):4d}  score {b['score']:.3f} d{b['d']} c{b['c']} b{b['b']} l{b['l']} {b['words']}w")
    print("     ", b["text"][:200])
