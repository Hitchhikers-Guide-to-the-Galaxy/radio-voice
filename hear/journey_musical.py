#!/usr/bin/env python3
"""journey_musical.py — the second route through the city, shaped like a piece of music
(Multilingual City Plan, the Listening Game). Where the first journey (journey.py) walks
the mixes in order, this one alternates the crowd and the single voice: every language at
city height, then one door; one language, then two; one language, then one door; and the
crowd again. Zones carry `alone` (only that house sounds) beside `descend`.

  journey_musical.py MAP.json CITY_MEDIA.json OUT.json [--svg SPOKEN_MAP.svg OUT.svg]
"""
import json, sys, time
mp = json.load(open(sys.argv[1])); cm = json.load(open(sys.argv[2])); out = sys.argv[3]
nodes = {n["slug"]: n for n in mp["nodes"] if n["site"].startswith("constitution")}
houses = {h["slug"]: h for h in cm["houses"]}
def centroid(slugs):
    pts = [(nodes[s]["x"], nodes[s]["y"]) for s in slugs if s in nodes]
    return [round(sum(p[0] for p in pts) / len(pts), 1), round(sum(p[1] for p in pts) / len(pts), 1)]
def speaking(lang): return [s for s, h in houses.items() if h.get("native") and h["language"].split("-")[0] == lang]
def at(slug): return [nodes[slug]["x"], nodes[slug]["y"]]
es = speaking("es"); ar = speaking("ar"); pt = speaking("pt")
latam = [s for s in es if not s.startswith("spain")]; iberia = [s for s in es if s.startswith("spain")] + pt
vx, vy, vw, vh = mp["viewBox"]; centre = [round(vx + vw / 2, 1), round(vy + vh / 2, 1)]
EGYPT = "egypt-2014-rev-2019"; BOLIVIA = "bolivia-plurinational-state-of-2009"
zones = [
    dict(name="Overture: the crowd", mix="polyphonic", languages=[], at=centre, height=44, seconds=24, houses=[],
         says="every language the city speaks, from high up: a crowd of tongues, one strand each, none louder than the rest"),
    dict(name="One voice: Egypt", mix="native", languages=[], at=at(EGYPT), height=2, seconds=20, houses=[EGYPT], descend=EGYPT, alone=True,
         says="down to one door and nothing else sounds: the English reading, then the Arabic from its first word"),
    dict(name="The Arabic quarter, one language", mix="solo", languages=["ar"], at=centroid(ar), height=20, seconds=22, houses=ar,
         says="pure Arabic across the quarter, one house intelligible at a time"),
    dict(name="Two languages: Portuguese with Spanish", mix="pair", languages=["pt", "es"], at=centroid(iberia), height=16, seconds=22, houses=iberia,
         says="two tongues share the street, each owed a voice: Portugal and Brazil beside Spain"),
    dict(name="Latin America, one language", mix="solo", languages=["es"], at=centroid(latam), height=22, seconds=22, houses=latam,
         says="pure Spanish over the widest quarter"),
    dict(name="One voice: Bolivia", mix="native", languages=[], at=at(BOLIVIA), height=2, seconds=20, houses=[BOLIVIA], descend=BOLIVIA, alone=True,
         says="one door again: the English gives way to the original at the threshold, alone"),
    dict(name="Coda: the crowd", mix="polyphonic", languages=[], at=centre, height=44, seconds=20, houses=[],
         says="back up into every language, the way the piece began"),
]
doc = dict(schema_version="0.1.0", journey_id="multilingual-flight-musical", name="The musical route",
           built=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           rule="crowd, one voice, one language, two languages, one language, one voice, crowd: an arch, loud and soft in turn",
           edition=cm.get("edition"), zones=zones, total_seconds=sum(z["seconds"] for z in zones))
json.dump(doc, open(out, "w"), indent=1, ensure_ascii=False)
print("zones", [(z["name"], z["mix"], z["languages"], z.get("alone", False)) for z in zones], "total", doc["total_seconds"], "s")
if "--svg" in sys.argv:
    src, dst = sys.argv[sys.argv.index("--svg") + 1], sys.argv[sys.argv.index("--svg") + 2]
    svg = open(src).read(); S = vw / 1600.0
    path = " ".join(f"{x:.0f},{y:.0f}" for x, y in (z["at"] for z in zones))
    extra = [f'<polyline points="{path}" fill="none" stroke="#7a1f1f" stroke-width="{5*S:.1f}" stroke-dasharray="{14*S:.0f},{10*S:.0f}" stroke-linejoin="round" opacity="0.85"/>']
    for i, z in enumerate(zones, 1):
        x, y = z["at"]; r = 26 * S; dy = (i % 2) * 40 * S   # stagger the labels where zones share a place
        extra.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r:.0f}" fill="#7a1f1f" fill-opacity="0.9"/><text x="{x:.0f}" y="{y+9*S:.0f}" text-anchor="middle" font-size="{26*S:.0f}" fill="#fff" font-weight="bold">{i}</text>'
                     f'<text x="{x+34*S:.0f}" y="{y+8*S+dy:.0f}" font-size="{24*S:.0f}" fill="#7a1f1f" font-weight="bold">{"one voice" if z.get("alone") else z["mix"]}{" " + " ".join(z["languages"]) if z["languages"] else ""} · {z["seconds"]} s</text>')
    svg = svg.replace("</svg>", "\n".join(extra) + "\n</svg>")
    open(dst, "w").write(svg); print("flight path ->", dst)
