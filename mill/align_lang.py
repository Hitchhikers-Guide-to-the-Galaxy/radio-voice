"""Align a non-English Constitute edition with the English one, section by
section. Constitute renders every edition from the same section tree
(div.section id="section/N"), so section N in raw/html-<lang>/<id>.json is
the translation of section N in raw/html/<id>.json — whatever the heading
says. Output: raw/aligned/<cons_id>.<lang>.jsonl, one line per section with
the English fragment id prefix ({constitution}:{article}), both headings and
both paragraph lists. Paragraph counts may differ between editions; that is
reported, not hidden.

  python3 align_lang.py es Spain_2011          # one
  python3 align_lang.py es --all               # every pulled edition
  python3 align_lang.py ar --all --report      # coverage table only
"""
import json, re, sys, os, glob
from html.parser import HTMLParser
sys.path.insert(0, os.path.expanduser("~/Code/radio-voice/commons"))
from commons import prefix, article_no

class Sections(HTMLParser):
    """Paragraphs grouped under the innermost section, in document order."""
    def __init__(self):
        super().__init__()
        self.stack = []; self.secs = []; self.cur_head = None
        self.in_p = False; self.pbuf = []; self.heads = []
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "div" and a.get("class") == "section":
            sec = {"id": a.get("id"), "heading": None, "path": None, "paras": []}
            self.secs.append(sec); self.stack.append(sec)
        elif tag in ("h1","h2","h3","h4","h5","h6"):
            self.cur_head = (int(tag[1]), [])
        elif tag == "p" and a.get("class") == "content":
            self.in_p = True; self.pbuf = []
        else:
            self.stack.append(None)
        if tag == "div" and a.get("class") != "section":
            pass
    def handle_endtag(self, tag):
        if self.cur_head and tag == f"h{self.cur_head[0]}":
            lvl, chars = self.cur_head
            text = re.sub(r"\s+", " ", "".join(chars)).strip()
            self.heads = [h for h in self.heads if h[0] < lvl] + [(lvl, text)]
            for s in reversed(self.stack):
                if s is not None:
                    if s["heading"] is None:
                        s["heading"] = text; s["path"] = " / ".join(h[1] for h in self.heads[1:]) or text
                    break
            self.cur_head = None
        if tag == "p" and self.in_p:
            text = re.sub(r"\s+", " ", "".join(self.pbuf)).strip()
            if text:
                for s in reversed(self.stack):
                    if s is not None:
                        if s["path"] is None:  # no heading of its own: inherit the heading path
                            s["path"] = " / ".join(h[1] for h in self.heads[1:]) or (self.heads[0][1] if self.heads else "")
                        s["paras"].append(text); break
            self.in_p = False
        if tag == "div" and self.stack:
            self.stack.pop()
    def handle_data(self, d):
        if self.cur_head: self.cur_head[1].append(d)
        if self.in_p: self.pbuf.append(d)

def sections(path):
    p = Sections(); p.feed(json.load(open(path))["html"]); return p.secs

def align(cid, lang):
    en = sections(f"raw/html/{cid}.json"); xx = sections(f"raw/html-{lang}/{cid}.json")
    by_id = {s["id"]: s for s in xx}
    rows = []; para_mismatch = 0
    for s in en:
        t = by_id.get(s["id"])
        if not t or not s["paras"]: continue
        art = article_no(s["path"] or s["heading"] or "")
        if len(t["paras"]) != len(s["paras"]): para_mismatch += 1
        rows.append({"section": s["id"], "fid": f"{prefix(cid)}:{art}",
                     "heading_en": s["heading"], f"heading_{lang}": t["heading"],
                     "paras_en": s["paras"], f"paras_{lang}": t["paras"],
                     "aligned_paragraphs": len(t["paras"]) == len(s["paras"])})
    return rows, len(en), len(xx), para_mismatch

if __name__ == "__main__":
    lang = sys.argv[1]; report = "--report" in sys.argv
    ids = [os.path.basename(f)[:-5] for f in sorted(glob.glob(f"raw/html-{lang}/*.json"))] if "--all" in sys.argv else [a for a in sys.argv[2:] if not a.startswith("--")]
    os.makedirs("raw/aligned", exist_ok=True)
    print("constitution\tsections_en\tsections_%s\taligned\tpara_mismatch" % lang)
    for cid in ids:
        if not os.path.exists(f"raw/html/{cid}.json"): print(f"{cid}\tNO ENGLISH PULL"); continue
        rows, n_en, n_xx, mm = align(cid, lang)
        if not report:
            with open(f"raw/aligned/{cid}.{lang}.jsonl", "w") as f:
                for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"{cid}\t{n_en}\t{n_xx}\t{len(rows)}\t{mm}")
