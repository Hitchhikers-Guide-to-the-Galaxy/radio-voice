"""Constitution commons — shared helpers for the import generators.
Fragment id scheme:  {constitution}:{article}.{paragraph}
  constitution = Constitute cons_id lowercased, '_' -> '-'   e.g. bhutan-2008
  article      = the number in the innermost heading (Article 5 -> 5; 79 -> 79; Preamble -> p)
  paragraph    = 1-based index of the paragraph inside that article (omitted for the whole article)
  run          = a.b-c for consecutive paragraphs b..c
"""
import json, re, os, math
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
_ART = re.compile(r"^(?:Article|Art\.?|Section|Sec\.?|§|Clause|Rule)\s*([0-9]+[A-Za-z]?(?:\.[0-9]+)?)", re.I)
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
