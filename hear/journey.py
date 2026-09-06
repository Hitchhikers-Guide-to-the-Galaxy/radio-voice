#!/usr/bin/env python3
"""journey.py — the first multilingual flight as a cue sheet of language zones
(Multilingual City Plan, Phase 4). Reads the atlas map.json and city-media.json
(with Phase 3's `language`/`native` per house), finds where the languages live on
the map, and writes journey.json: zones with a mix, an allow-list, a place in
map coordinates, a height and a duration. The plugin's guided flight (JOURNEY
line) and mux_journey.py (Phase 5, Blender) read the same file. Also draws the
flight path over the spoken-language map as an SVG.

  journey.py MAP.json CITY_MEDIA.json OUT.json [--svg SPOKEN_MAP.svg OUT.svg]
"""
import json, sys, math, re, collections
mp = json.load(open(sys.argv[1])); cm = json.load(open(sys.argv[2])); out = sys.argv[3]
nodes = {n["slug"]: n for n in mp["nodes"] if n["site"].startswith("constitution")}
houses = {h["slug"]: h for h in cm["houses"]}
def centroid(slugs):
    pts = [(nodes[s]["x"], nodes[s]["y"]) for s in slugs if s in nodes]
    return [round(sum(p[0] for p in pts) / len(pts), 1), round(sum(p[1] for p in pts) / len(pts), 1)] if pts else None
def speaking(lang): return [s for s, h in houses.items() if h.get("native") and h["language"].split("-")[0] == lang]
es = speaking("es"); ar = speaking("ar"); pt = speaking("pt")
# the Latin-American quarter is the bulk of the Spanish houses; Spain and the Portuguese houses form Iberia with Brazil
latam = [s for s in es if not s.startswith("spain")]
iberia = [s for s in es if s.startswith("spain")] + pt
vx, vy, vw, vh = mp["viewBox"]
zones = [
    dict(name="Latin America, in Spanish", mix="solo", languages=["es"], at=centroid(latam), height=22, seconds=28, houses=latam,
         says="pure Spanish: twenty-odd houses of the Latin-American quarter, one intelligible at a time"),
    dict(name="Iberia and Brazil, Spanish with Portuguese", mix="pair", languages=["es", "pt"], at=centroid(iberia), height=18, seconds=22, houses=iberia,
         says="two languages sharing the street, one intelligible voice each"),
    dict(name="The centre, every language", mix="polyphonic", languages=[], at=[round(vx + vw / 2, 1), round(vy + vh / 2, 1)], height=30, seconds=26, houses=[],
         says="polyphonic: every language a strand, none louder than the rest"),
    dict(name="The Arabic quarter", mix="solo", languages=["ar"], at=centroid(ar), height=22, seconds=28, houses=ar,
         says="pure Arabic; the Egyptian preamble is the beacon"),
    dict(name="Descent to one house", mix="native", languages=[], at=[nodes["bolivia-plurinational-state-of-2009"]["x"], nodes["bolivia-plurinational-state-of-2009"]["y"]], height=2, seconds=20, houses=["bolivia-plurinational-state-of-2009"], descend="bolivia-plurinational-state-of-2009",
         says="native: the English reading gives way to the original at the threshold"),
]
doc = dict(schema_version="0.1.0", journey_id="multilingual-flight-1", built=__import__("time").strftime("%Y-%m-%dT%H:%M:%SZ", __import__("time").gmtime()),
           rule="a zone begins pure and ends pure; polyphony sits between two solos", edition=cm.get("edition"), zones=zones,
           total_seconds=sum(z["seconds"] for z in zones))
json.dump(doc, open(out, "w"), indent=1, ensure_ascii=False)
print("zones", [(z["name"], z["mix"], z["languages"], z["at"], len(z["houses"])) for z in zones], "total", doc["total_seconds"], "s")

if "--svg" in sys.argv:
    src, dst = sys.argv[sys.argv.index("--svg") + 1], sys.argv[sys.argv.index("--svg") + 2]
    svg = open(src).read(); S = vw / 1600.0
    pts = [z["at"] for z in zones]
    path = " ".join(f"{x:.0f},{y:.0f}" for x, y in pts)
    extra = [f'<polyline points="{path}" fill="none" stroke="#1a1208" stroke-width="{5*S:.1f}" stroke-dasharray="{14*S:.0f},{10*S:.0f}" stroke-linejoin="round" opacity="0.85"/>']
    for i, z in enumerate(zones, 1):
        x, y = z["at"]; r = 26 * S
        extra.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r:.0f}" fill="#1a1208" fill-opacity="0.85"/><text x="{x:.0f}" y="{y+9*S:.0f}" text-anchor="middle" font-size="{26*S:.0f}" fill="#fff" font-weight="bold">{i}</text>'
                     f'<text x="{x+34*S:.0f}" y="{y+8*S:.0f}" font-size="{24*S:.0f}" fill="#1a1208" font-weight="bold">{z["mix"]}{" " + " ".join(z["languages"]) if z["languages"] else ""} · {z["seconds"]} s</text>')
    svg = svg.replace("</svg>", "\n".join(extra) + "\n</svg>")
    open(dst, "w").write(svg); print("flight path ->", dst)
