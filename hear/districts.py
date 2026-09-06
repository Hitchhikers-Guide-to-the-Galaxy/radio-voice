#!/usr/bin/env python3
"""districts.py — districts inside each site from the semantic vectors (their first use).

Reads status/semantic-vectors.json for each site on the map, clusters each
site's pages by k-means on the 384-dim vectors (seeded, so districts are
stable between runs), names each district by the words its titles share, and
writes districts.json beside map.json while stamping every map node with its
district.  Reports how districts fall across the GMap regions, which were found
from links alone — the two readings of the same corpus, compared.

    districts.py --map MAP.json --k 8 [--out districts.json]
"""
import argparse, collections, json, os, re, math
import numpy as np
ap = argparse.ArgumentParser()
ap.add_argument("--map", required=True); ap.add_argument("--k", type=int, default=8); ap.add_argument("--out", default=None)
ap.add_argument("--farm", default=os.path.expanduser("~/Nextcloud/fedwiki")); ap.add_argument("--seed", type=int, default=11)
a = ap.parse_args()
m = json.load(open(a.map))
STOP = set("the of and a in on for to by rev reinst state states republic constitution constitutional right rights court courts 1 2 3".split())

def kmeans(X, k, seed, iters=60):
    rng = np.random.default_rng(seed)
    C = X[rng.choice(len(X), k, replace=False)].copy()
    for _ in range(iters):
        d = ((X[:, None, :] - C[None, :, :]) ** 2).sum(-1); lab = d.argmin(1)
        newC = np.array([X[lab == j].mean(0) if (lab == j).any() else C[j] for j in range(k)])
        if np.allclose(newC, C): break
        C = newC
    return lab, C

out = {"k": a.k, "seed": a.seed, "sites": {}}
node_district = {}
for site in m["sites"]:
    vec = json.load(open(os.path.join(a.farm, site, "status", "semantic-vectors.json")))
    rows = [v for v in vec if f"{site}/{v['slug']}" in {n["id"] for n in m["nodes"]}]
    X = np.array([v["vector"] for v in rows], dtype=np.float32); X /= (np.linalg.norm(X, axis=1, keepdims=True) + 1e-9)
    lab, C = kmeans(X, a.k, a.seed)
    nodes = {n["id"]: n for n in m["nodes"]}
    districts = []
    for j in range(a.k):
        members = [rows[i] for i in range(len(rows)) if lab[i] == j]
        words = collections.Counter(w for v in members for w in re.findall(r"[a-z]{4,}", v["title"].lower()) if w not in STOP)
        topics = collections.Counter(nodes[f"{site}/{v['slug']}"].get("topic") for v in members)
        topics.pop(None, None)
        name = (topics.most_common(1)[0][0] if topics and topics.most_common(1)[0][1] >= max(3, len(members) * 0.2)
                else " ".join(w for w, _ in words.most_common(2)).title() or f"District {j}")
        regions = collections.Counter(nodes[f"{site}/{v['slug']}"].get("region") for v in members)
        did = f"{site.split('.')[0]}-{j}"
        for v in members: node_district[f"{site}/{v['slug']}"] = did
        districts.append(dict(id=did, name=name, pages=len(members), slugs=[v["slug"] for v in members],
                              top_words=[w for w, _ in words.most_common(5)], regions=dict(regions),
                              region_purity=round(regions.most_common(1)[0][1] / max(1, len(members)), 2),
                              centroid=[round(float(x), 5) for x in C[j]]))
    out["sites"][site] = dict(pages=len(rows), districts=sorted(districts, key=lambda d: -d["pages"]))
    print(f"{site}: {len(rows)} pages -> {a.k} districts")
    for d in out["sites"][site]["districts"]:
        print(f"   {d['id']:<16} {d['pages']:>4}  region-purity {d['region_purity']:.2f}  {d['name']}  [{', '.join(d['top_words'][:4])}]")
for n in m["nodes"]:
    n["district"] = node_district.get(n["id"])
m["districts_file"] = os.path.basename(a.out or "districts.json")
json.dump(m, open(a.map, "w"), separators=(",", ":"))
json.dump(out, open(a.out or os.path.join(os.path.dirname(a.map), "districts.json"), "w"), indent=1)
print("stamped", sum(1 for n in m["nodes"] if n.get("district")), "nodes with a district")
