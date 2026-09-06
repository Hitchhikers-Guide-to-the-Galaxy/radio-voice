"""Constitution commons — shared helpers for the import generators.
Fragment id scheme:  {constitution}:{article}.{paragraph}
  constitution = Constitute cons_id lowercased, '_' -> '-'   e.g. bhutan-2008
  article      = the number in the innermost heading (Article 5 -> 5; 79 -> 79; Preamble -> p)
  paragraph    = 1-based index of the paragraph inside that article (omitted for the whole article)
  run          = a.b-c for consecutive paragraphs b..c
"""
import json, re, os, math, glob
from collections import Counter, defaultdict
MILL = os.path.expanduser("~/Code/radio-voice/mill")
CONS = {c["id"]: c for c in json.load(open(f"{MILL}/raw/constitutions.json"))}
def topics_tree():
    t = json.load(open(f"{MILL}/raw/topics.json")); out = {}
    def walk(n, parent=None):
        for x in n:
            out[x["key"]] = dict(label=x["label"], desc=x["description"], count=x["count"], parent=parent)
            walk(x.get("topics", []), x["key"])
    walk(t); return out
TOPICS = topics_tree()
def prefix(cid): return cid.lower().replace("_", "-")
_ART = re.compile(r"^(?:Article|Art\.?|Section|Sec\.?|§|Clause|Rule|Artículo|Artigo|Artikel|Articolo|Artykuł|Artikkel|Madde|المادة)\s*([0-9]+[A-Za-z]?(?:\.[0-9]+)?)", re.I)
_NUM = re.compile(r"^([0-9]+[A-Za-z]?)[.\s)]")
def article_no(heading):
    h = heading.split(" / ")[-1].strip()
    if re.match(r"^preamble", h, re.I): return "p"
    m = _ART.match(h) or _NUM.match(h)
    return m.group(1) if m else re.sub(r"[^a-z0-9]+", "-", h.lower()).strip("-")[:24]
def units_for(cid):
    """All units of one constitution with fragment ids assigned."""
    us = [json.loads(l) for l in open(f"{MILL}/by_cons/{cid}.jsonl")]
    para_idx = defaultdict(int); seen_art = {}
    for u in us:
        art = article_no(u["heading"]); u["article"] = art
        if u["kind"] == "article": u["fid"] = f"{prefix(cid)}:{art}"
        elif u["kind"] == "paragraph":
            para_idx[u["heading"]] += 1; u["fid"] = f"{prefix(cid)}:{art}.{para_idx[u['heading']]}"
        else: u["fid"] = f"{prefix(cid)}:{art}.r"
    return us
def outline(us):
    """Top-level headings with article counts, in document order."""
    seen = []; counts = Counter()
    for u in us:
        if u["kind"] != "article": continue
        top = u["heading"].split(" / ")[0]
        if top not in counts: seen.append(top)
        counts[top] += 1
    return [(h, counts[h]) for h in seen]
def rights(c):
    if c.get("copyright"): return "restricted", f"{c['copyright'].strip()}" + (f" — {c['translator']}" if c.get("translator") else "")
    if c.get("translator"): return "credited", c["translator"]
    return "open", "no copyright or translator recorded by the Constitute Project"
def plain_text(cid):
    us = units_for(cid); return "\n\n".join(f"[{u['heading']}]\n{u['text']}" for u in us if u["kind"] == "article")

_dups = {t for t in Counter(c["title"] for c in CONS.values()) if Counter(c["title"] for c in CONS.values())[t] > 1}
def page_title(c):
    """Constitute title, disambiguated where two texts share one (Chile 2023 drafts)."""
    return c["title"] if c["title"] not in _dups else f"{c['title']} ({c['id'].replace('_', ' ')})"

# ── other languages (Multilingual City Plan, Phase 1) ─────────────────────────
LANGS = ("es", "ar")
def aligned_rows(cid, lang):
    """raw/aligned/{cid}.{lang}.jsonl as {fid: row}, or {} when the edition is absent."""
    p = f"{MILL}/raw/aligned/{cid}.{lang}.jsonl"
    if not os.path.exists(p): return {}
    return {r["fid"]: r for r in (json.loads(l) for l in open(p))}
def official_rows(cid):
    """raw/official/{cid}.{lang}.jsonl (official originals, article level) as {lang: {fid: row}}."""
    out = {}
    for p in glob.glob(f"{MILL}/raw/official/{cid}.*.jsonl"):
        lang = os.path.basename(p)[len(cid) + 1:-6]
        out[lang] = {r["fid"]: r for r in (json.loads(l) for l in open(p)) if r["paras"]}
    return out
def attach_languages(us, cid, langs=LANGS):
    """Give every unit text_{lang} from the aligned editions, keyed by the English
    fragment id: an article gets the whole section, a paragraph its counterpart
    (only where paragraph counts agree), a run the whole section. Sets u["languages"]."""
    editions = {l: aligned_rows(cid, l) for l in langs}
    for u in us:
        u["languages"] = ["en"]
        fid = u["fid"]; art_fid = fid.rsplit(".", 1)[0] if u["kind"] != "article" else fid
        for l, rows in editions.items():
            r = rows.get(art_fid)
            if not r: continue
            paras = r[f"paras_{l}"]
            if u["kind"] == "paragraph":
                n = int(fid.rsplit(".", 1)[1])
                if not r["aligned_paragraphs"] or n > len(paras): continue
                t = paras[n - 1]
            else:
                t = " ".join(paras)
            if t: u[f"text_{l}"] = t; u["languages"].append(l)
        for l, rows in official_rows(cid).items():   # official originals: article level only
            r = rows.get(art_fid)
            if r and u["kind"] == "article":
                u[f"text_{l}"] = " ".join(r["paras"]); u["languages"].append(l)
    return us
LANGUAGES = json.load(open(f"{MILL}/languages.json")) if os.path.exists(f"{MILL}/languages.json") else {}
def enactment(cid):
    """(language, languages, confidence, note) of the text as enacted, from languages.json by country."""
    c = CONS.get(cid); e = LANGUAGES.get(c["country_id"]) if c else None
    if not e: return None
    return dict(language=e["language"], languages=e.get("languages", [e["language"]]), confidence=e.get("confidence", "low"), note=e.get("note", ""))
