"""Constitute HTML -> units.jsonl. A unit is the text under one heading
(an article, or the preamble), plus every paragraph on its own, with the
heading path and the union of topic tags on the enclosing sections."""
import json, re, sys, os, glob
from html.parser import HTMLParser

ONT = "http://www.constituteproject.org/ontology/"

class P(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []          # open elements: (tag, section_topics or None)
        self.heads = []          # heading path: (level, text)
        self.cur_head = None     # (level, [chars]) while inside a heading
        self.in_p = False; self.pbuf = []
        self.paras = []          # (head_path_tuple, topics_set, text)
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        tops = None
        if tag == "div" and a.get("class") == "section":
            tops = {t.replace(ONT, "") for t in a.get("data-topics", "").split(",") if t}
        self.stack.append((tag, tops))
        if tag in ("h1","h2","h3","h4","h5","h6"):
            self.cur_head = (int(tag[1]), [])
        if tag == "p" and a.get("class") == "content":
            self.in_p = True; self.pbuf = []
    def handle_endtag(self, tag):
        if self.cur_head and tag == f"h{self.cur_head[0]}":
            lvl, chars = self.cur_head
            text = re.sub(r"\s+", " ", "".join(chars)).strip()
            self.heads = [h for h in self.heads if h[0] < lvl] + [(lvl, text)]
            self.cur_head = None
        if tag == "p" and self.in_p:
            text = re.sub(r"\s+", " ", "".join(self.pbuf)).strip()
            if text:
                tops = set()
                for _, t in self.stack:
                    if t: tops |= t
                self.paras.append((tuple(h[1] for h in self.heads), tops, text))
            self.in_p = False
        # pop to the matching open tag
        for i in range(len(self.stack)-1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]; break
    def handle_data(self, d):
        if self.cur_head: self.cur_head[1].append(d)
        if self.in_p: self.pbuf.append(d)

def wc(s): return len(s.split())

def units_for(cid, meta, html):
    p = P(); p.feed(html)
    # group consecutive paragraphs by heading path
    groups = []
    for hp, tops, text in p.paras:
        if groups and groups[-1][0] == hp:
            groups[-1][1] |= tops; groups[-1][2].append(text)
        else:
            groups.append([hp, set(tops), [text]])
    out = []
    for hp, tops, texts in groups:
        base = dict(cons_id=cid, country=meta["country_id"], title=meta["title"],
                    year=meta.get("year_enacted"), in_force=bool(meta.get("in_force")), heading=" / ".join(hp[1:]) or (hp[0] if hp else ""),
                    topics=sorted(tops))
        whole = " ".join(texts)
        out.append(dict(base, kind="article", text=whole, words=wc(whole)))
        if len(texts) > 1:
            for t in texts:
                if wc(t) >= 12:
                    out.append(dict(base, kind="paragraph", text=t, words=wc(t)))
            # one run per start: the shortest run of consecutive paragraphs
            # that reaches the speakable band (no overlapping explosion)
            for i in range(len(texts)):
                run = []
                for j in range(i, len(texts)):
                    run.append(texts[j]); s = " ".join(run); n = wc(s)
                    if n > 100: break
                    if j > i and n >= 38:
                        out.append(dict(base, kind="run", text=s, words=n)); break
    return out

if __name__ == "__main__":
    cons = {c["id"]: c for c in json.load(open("raw/constitutions.json"))}
    files = sys.argv[1:] or sorted(glob.glob("raw/html/*.json"))
    n = 0
    with open("units.jsonl", "w") as f:
        for fn in files:
            cid = os.path.basename(fn)[:-5]
            if cid not in cons: continue
            try: html = json.load(open(fn))["html"]
            except Exception as e: print("skip", cid, e, file=sys.stderr); continue
            for u in units_for(cid, cons[cid], html):
                f.write(json.dumps(u, ensure_ascii=False) + "\n"); n += 1
    print(n, "units from", len(files), "constitutions")
