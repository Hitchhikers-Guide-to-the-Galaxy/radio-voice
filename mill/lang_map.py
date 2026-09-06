#!/usr/bin/env python3
"""The language map: the page-level GMap of the two legalcommons sites with every
constitution house coloured by the language its text was enacted in
(languages.json by country), clause pages as small grey dots, regions as faint
sheets. Reads the atlas map.json; writes an SVG whose houses link to their pages.

  python3 lang_map.py MAP_JSON OUT_SVG [--json OUT_JSON]
"""
import json, sys, os, html
from collections import Counter
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "commons"))
import commons as C

FAMILY = {  # language -> family colour; anything else is "other"
    "en": ("English", "#4f6d8f"), "es": ("Spanish", "#d9822b"), "ar": ("Arabic", "#2e8b57"), "fr": ("French", "#8e5ea2"),
    "pt": ("Portuguese", "#c94c4c"), "de": ("German", "#b8a034"), "ru": ("Russian", "#7a5c3e"), "zh": ("Chinese", "#c2185b"),
}
OTHER = ("other", "#9aa5ad")

def family(lang):
    return FAMILY.get((lang or "").split("-")[0], OTHER)

def main():
    mp = json.load(open(sys.argv[1])); out = sys.argv[2]
    by_title = {c["title"]: cid for cid, c in C.CONS.items()}
    vx, vy, vw, vh = mp["viewBox"]
    S = vw / 1600.0
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vx:.0f} {vy:.0f} {vw:.0f} {vh:.0f}" font-family="\'Helvetica Neue\',Helvetica,Arial,sans-serif">',
         f'<rect x="{vx:.0f}" y="{vy:.0f}" width="{vw:.0f}" height="{vh:.0f}" fill="#eef2f5"/>']
    for r in mp["regions"]:
        for P in r.get("polygons", []):
            o.append(f'<polygon fill="#dfe6ec" stroke="#cfd8e0" stroke-width="{1.5*S:.1f}" points="' + " ".join(f"{x:.0f},{y:.0f}" for x, y in P) + '"/>')
    counts = Counter(); rows = []; others = 0
    for n in mp["nodes"]:
        x, y = n["x"], n["y"]; site, slug = n["site"], n["slug"]
        if site.startswith("clause"):
            o.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{3*S:.1f}" fill="#b7c0c8"/>'); continue
        cid = by_title.get(n["title"]); e = C.enactment(cid) if cid else None
        if not e:  # a corpus page that is not a constitution (statute, category, accreditation): small and grey
            o.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{3*S:.1f}" fill="#b7c0c8"/>'); others += 1; continue
        lang = e["language"]
        name, col = family(lang)
        counts[name] += 1
        rows.append(dict(id=n["id"], slug=slug, title=n["title"], language=lang, family=name, region=n.get("region"), district=n.get("district")))
        multi = e and len(e["languages"]) > 1
        o.append(f'<a href="https://{site}/view/{slug}" target="_blank"><title>{html.escape(n["title"])} — {html.escape(lang or "unknown")}</title>'
                 f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{7*S:.1f}" fill="{col}" stroke="{"#222" if multi else "#ffffff"}" stroke-width="{(2.2 if multi else 1.2)*S:.1f}"/></a>')
    # legend
    lx, ly = vx + 30 * S, vy + 40 * S
    o.append(f'<g font-size="{26*S:.0f}"><rect x="{lx-14*S:.0f}" y="{ly-30*S:.0f}" width="{330*S:.0f}" height="{(len(counts)+2)*36*S:.0f}" rx="{8*S:.0f}" fill="#ffffff" fill-opacity="0.88"/>'
             f'<text x="{lx:.0f}" y="{ly:.0f}" font-weight="bold">Language of enactment</text>')
    i = 1
    for name, cnt in counts.most_common():
        col = next((c for _, (n2, c) in FAMILY.items() if n2 == name), OTHER[1] if name == "other" else "#ffffff")
        o.append(f'<circle cx="{lx+10*S:.0f}" cy="{ly+i*36*S-9*S:.0f}" r="{9*S:.0f}" fill="{col}" stroke="#fff" stroke-width="{1.2*S:.1f}"/>'
                 f'<text x="{lx+32*S:.0f}" y="{ly+i*36*S:.0f}">{name} · {cnt}</text>')
        i += 1
    o.append(f'<text x="{lx:.0f}" y="{ly+i*36*S:.0f}" font-size="{20*S:.0f}" fill="#555">dark ring = enacted in several languages · small grey = clause and other corpus pages</text></g></svg>')
    open(out, "w").write("\n".join(o))
    if "--json" in sys.argv:
        json.dump(dict(built=mp.get("built"), edition=mp.get("epoch"), counts=counts, houses=rows), open(sys.argv[sys.argv.index("--json") + 1], "w"), indent=1, ensure_ascii=False)
    print("houses", sum(counts.values()), dict(counts), "other corpus pages", others, "->", out, os.path.getsize(out), "bytes")

if __name__ == "__main__":
    main()
