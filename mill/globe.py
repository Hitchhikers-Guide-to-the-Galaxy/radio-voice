#!/usr/bin/env python3
"""Build the Constitution Globe data assets from the constitution pages.

Reads every `# Record` code item on constitution.legalcommons.org (the pages
clc.py generated), joins each in-force text to a Natural Earth country
polygon (or a capital pin for the microstates the 110m map lacks), and writes
the files globe.html loads:

  constitutions.json  every Record, flattened, plus iso3/slug/site/how
  countries.geojson   ne_110m admin-0 slimmed to {iso3, name, geometry}
  pins.json           microstates without a polygon: {iso3, name, lat, lng}
  iso-map.json        the reviewable join: slug, title, country_id, iso3, how

Idempotent — re-run after any page change. Stdlib only.
"""
import json
import os
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path

sys.path.insert(0, os.path.expanduser("~/.claude/skills/fedwiki-lib"))
import fedwiki  # noqa: E402

SITE = "constitution.legalcommons.org"
SITE_DIR = fedwiki.PUBLIC_FARM / SITE
OUT = SITE_DIR / "assets" / "constitution-globe"
DATASETS = fedwiki.PUBLIC_FARM / "david.hitchhikers.earth" / "assets" / "datasets"
COUNTRIES = DATASETS / "ne_110m_admin_0_countries.geojson"
PLACES = DATASETS / "ne_110m_populated_places_simple.geojson"
LISTING = Path.home() / "Code/radio-voice/mill/raw/constitutions.json"

# Spellings the map and the corpus disagree on, by Constitute country_id.
HAND = {
    "Swaziland": "SWZ", "Eswatini": "SWZ",
    "Viet_Nam": "VNM",
    "The_former_Yugoslav_Republic_of_Macedonia": "MKD",
    "Democratic_Republic_of_the_Congo": "COD",
    "Congo": "COG",
    "Bosnia_and_Herzegovina": "BIH",
    "Equatorial_Guinea": "GNQ",
    "Papua_New_Guinea": "PNG",
    "Trinidad_and_Tobago": "TTO",
    "United_Arab_Emirates__the": "ARE",
    "United_Kingdom_of_Great_Britain_and_Northern_Ireland__the": "GBR",
    "United_States_of_America": "USA",
}
# Capitals the populated-places file lacks.
EXTRA_PINS = {"NRU": ("Nauru", "Yaren", -0.5477, 166.9209)}


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z ]", "", s.lower()).strip()


def iso_of(props):
    iso = props.get("ISO_A3")
    return iso if iso and iso != "-99" else props.get("ADM0_A3")


def records():
    out = []
    for path in sorted((SITE_DIR / "pages").iterdir()):
        try:
            page = fedwiki.load_page(path)
        except Exception:
            continue
        for item in page.get("story", []):
            if item.get("type") == "code" and item.get("text", "").startswith("constitution:"):
                rec = {}
                for line in item["text"].splitlines():
                    if ":" in line:
                        k, v = line.split(":", 1)
                        rec[k.strip()] = v.strip()
                rec["slug"] = path.name
                rec["title"] = page["title"]
                rec["site"] = SITE
                out.append(rec)
                break
    return out


def main():
    countries = json.load(open(COUNTRIES))
    places = json.load(open(PLACES))
    listing = {c["id"].lower().replace("_", "-"): c for c in json.load(open(LISTING))}

    # name -> iso3 over every name field the map carries
    # Two passes: a feature's own names first, sovereignty last — otherwise
    # "France" lands on the French Southern Lands (SOVEREIGNT France).
    name_idx = {}
    for fields in (("ADMIN", "NAME", "NAME_LONG", "FORMAL_EN", "GEOUNIT", "SUBUNIT",
                    "BRK_NAME", "NAME_SORT", "NAME_CIAWF"), ("SOVEREIGNT",)):
        for f in countries["features"]:
            p = f["properties"]
            iso = iso_of(p)
            for k in fields:
                if p.get(k):
                    name_idx.setdefault(norm(p[k]), iso)
    polygon_iso = {iso_of(f["properties"]) for f in countries["features"]}

    # capitals by country name -> (iso3, name, lat, lng)
    cap_idx = {}
    for f in places["features"]:
        p = f["properties"]
        if "capital" not in str(p.get("featurecla", "")).lower():
            continue
        row = (p["adm0_a3"], p["adm0name"], p["latitude"], p["longitude"])
        for k in ("adm0name", "sov0name"):
            if p.get(k):
                cap_idx.setdefault(norm(p[k]), row)
    for iso, (name, cap, lat, lng) in EXTRA_PINS.items():
        cap_idx[norm(name)] = (iso, name, lat, lng)

    recs = records()
    pins = {}
    iso_map = []
    for r in recs:
        listed = listing.get(r["constitution"]) or listing.get(r["slug"]) or {}
        cid = listed.get("country_id", "")
        short = re.sub(r"\s+\d{4}.*$", "", r["title"])
        short2 = re.sub(r"\s*\(.*?\)", "", short).strip()
        cands = [cid.replace("_", " ").strip(), r.get("country", ""), short, short2,
                 short2.split(",")[0]]
        iso, how = None, None
        if cid in HAND:
            iso, how = HAND[cid], "hand"
        else:
            for c in cands:
                if norm(c) in name_idx:
                    iso, how = name_idx[norm(c)], "auto"
                    break
        if iso is None:
            for c in cands:
                if norm(c) in cap_idx:
                    piso, pname, lat, lng = cap_idx[norm(c)]
                    iso, how = piso, "pin"
                    pins[piso] = {"iso3": piso, "name": pname, "lat": lat, "lng": lng}
                    break
        if iso and iso not in polygon_iso and how != "pin":
            # matched by name but the 110m map has no polygon: pin it
            for c in cands:
                if norm(c) in cap_idx:
                    piso, pname, lat, lng = cap_idx[norm(c)]
                    pins[iso] = {"iso3": iso, "name": pname, "lat": lat, "lng": lng}
                    how = "pin"
                    break
        r["iso3"] = iso
        r["how"] = how
        r["country_id"] = cid
        for k in ("enacted", "revised", "words", "articles", "paragraphs", "topics"):
            v = r.get(k, "-")
            r[k] = int(v) if v not in ("-", "", None) and v.isdigit() else None
        iso_map.append({"slug": r["slug"], "title": r["title"], "status": r["status"],
                        "country_id": cid, "iso3": iso, "how": how})

    inforce = [r for r in recs if r["status"] == "in force"]
    missing = [r["title"] for r in inforce if not r["iso3"]]
    dup = [k for k, v in Counter(r["iso3"] for r in inforce).items() if v > 1]
    print(f"records {len(recs)}  in force {len(inforce)}  "
          f"how {Counter(r['how'] for r in inforce)}  pins {len(pins)}")
    if missing or dup:
        print("UNMAPPED:", missing)
        print("DUPLICATE ISO3:", dup)
        sys.exit(1)

    OUT.mkdir(parents=True, exist_ok=True)
    slim = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {"iso3": iso_of(f["properties"]),
                                            "name": f["properties"]["ADMIN"]},
         "geometry": f["geometry"]}
        for f in countries["features"] if f["properties"].get("ISO_A2") != "AQ"]}
    json.dump(slim, open(OUT / "countries.geojson", "w"), separators=(",", ":"))
    json.dump(recs, open(OUT / "constitutions.json", "w"), indent=1, ensure_ascii=False)
    json.dump(sorted(pins.values(), key=lambda p: p["name"]),
              open(OUT / "pins.json", "w"), indent=1, ensure_ascii=False)
    json.dump(iso_map, open(OUT / "iso-map.json", "w"), indent=1, ensure_ascii=False)
    for f in ("countries.geojson", "constitutions.json", "pins.json", "iso-map.json"):
        print(f"{f}\t{(OUT / f).stat().st_size:,} bytes")


if __name__ == "__main__":
    main()
