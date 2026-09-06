#!/usr/bin/env python3
"""The spoken-language map: the page-level GMap with every voiced house coloured by the language
it now SPEAKS (city-media.json 'language'), grey-blue where it still speaks English only.
  python3 spoken_map.py MAP_JSON CITY_MEDIA_JSON OUT_SVG"""
import json, sys, html
from collections import Counter
FAMILY = {"es": ("Spanish", "#d9822b"), "ar": ("Arabic", "#2e8b57"), "fr": ("French", "#8e5ea2"), "pt": ("Portuguese", "#c94c4c"), "de": ("German", "#b8a034"), "it": ("Italian", "#3f8f8f")}
mp = json.load(open(sys.argv[1])); cm = json.load(open(sys.argv[2])); out = sys.argv[3]
spoken = {h["slug"]: h for h in cm["houses"]}
vx, vy, vw, vh = mp["viewBox"]; S = vw / 1600.0
o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vx:.0f} {vy:.0f} {vw:.0f} {vh:.0f}" font-family="\'Helvetica Neue\',Helvetica,Arial,sans-serif">', f'<rect x="{vx:.0f}" y="{vy:.0f}" width="{vw:.0f}" height="{vh:.0f}" fill="#eef2f5"/>']
for r in mp["regions"]:
    for P in r.get("polygons", []): o.append(f'<polygon fill="#dfe6ec" stroke="#cfd8e0" stroke-width="{1.5*S:.1f}" points="' + " ".join(f"{x:.0f},{y:.0f}" for x, y in P) + '"/>')
counts = Counter(); silent = 0
for n in mp["nodes"]:
    x, y = n["x"], n["y"]; h = spoken.get(n["slug"]) if n["site"].startswith("constitution") else None
    if not h: o.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{3*S:.1f}" fill="#b7c0c8"/>'); continue
    if h.get("native"):
        name, col = FAMILY.get(h["language"].split("-")[0], (h["language"], "#9aa5ad")); counts[name] += 1; rr = 8
    else:
        name, col = "English only", "#4f6d8f"; counts[name] += 1; rr = 5
    o.append(f'<a href="https://{n["site"]}/view/{n["slug"]}" target="_blank"><title>{html.escape(n["title"])} — speaks {html.escape(h["language"])}</title><circle cx="{x:.0f}" cy="{y:.0f}" r="{rr*S:.1f}" fill="{col}" stroke="#fff" stroke-width="{1.2*S:.1f}"/></a>')
lx, ly = vx + 30 * S, vy + 40 * S
o.append(f'<g font-size="{26*S:.0f}"><rect x="{lx-14*S:.0f}" y="{ly-30*S:.0f}" width="{360*S:.0f}" height="{(len(counts)+2)*36*S:.0f}" rx="{8*S:.0f}" fill="#fff" fill-opacity="0.88"/><text x="{lx:.0f}" y="{ly:.0f}" font-weight="bold">What each house speaks</text>')
i = 1
for name, cnt in counts.most_common():
    col = next((c for k, (n2, c) in FAMILY.items() if n2 == name), "#4f6d8f")
    o.append(f'<circle cx="{lx+10*S:.0f}" cy="{ly+i*36*S-9*S:.0f}" r="{9*S:.0f}" fill="{col}" stroke="#fff"/><text x="{lx+32*S:.0f}" y="{ly+i*36*S:.0f}">{name} · {cnt}</text>'); i += 1
o.append(f'<text x="{lx:.0f}" y="{ly+i*36*S:.0f}" font-size="{20*S:.0f}" fill="#555">large = speaks its own language beside English · small grey = not voiced</text></g></svg>')
open(out, "w").write("\n".join(o)); print(dict(counts), "->", out)
