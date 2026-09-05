"""Score speakable units. distinctiveness = idf across constitutions (a word few
constitutions use is what makes this one sound unlike the others), tempered by
containment (does it stand alone?), brevity (15-40 s spoken) and a legalese
penalty. Topic bonus is separate so the CLC filter can be switched."""
import json, math, re, sys
from collections import Counter, defaultdict

STOP = set("""a an the and or but if of to in on at by for with from as is are was were be been being
that this these those it its they them their there here which who whom whose what when where how
shall may must will would should can could not no nor any all each every such other than then so
than too very into under over between within without upon about after before during through per
has have had having do does did done than also only both either neither same own more most less
one two three four five six seven eight nine ten""".split())
LEGAL = re.compile(r"\b(article|articles|paragraph|paragraphs|section|subsection|clause|pursuant|hereinafter|aforesaid|thereof|therein|hereof|provided that|in accordance with|referred to in|subject to|notwithstanding|as prescribed by|by law|the law|of this constitution|this article|preceding|foregoing)\b", re.I)
DEP = re.compile(r"^(\(?[a-z0-9ivx]{1,4}[\).]\s|and\b|or\b|but\b|which\b|that\b|whereas\b|provided\b|unless\b|except\b|if\b|in such|the same|such\b|it\b|they\b|he\b|she\b|this\b|these\b|those\b)", re.I)
NOISE_HEAD = re.compile(r"schedule|legislative list|annex|appendix|symbol|flag|emblem|arms|seal|coat|territor|boundar|oath|list of|transitional|transitory|final provisions|definitions|interpretation", re.I)
ANTHEM = re.compile(r"anthem|hymn", re.I)
def listiness(t):
    segs = [x for x in re.split(r"[;.]\s+", t) if x.strip()]
    if len(segs) < 4: return 0.0
    return sum(1 for x in segs if len(x.split()) <= 6) / len(segs)

FIRST = re.compile(r"\b(we|our|us)\b", re.I)
IMAGE = re.compile(r"\b(earth|land|water|river|sea|forest|mountain|sky|sun|moon|air|soil|seed|tree|animal|bird|fish|ancestor|ancestors|mother|children|generations|silence|song|dream|memory|heart|soul|spirit|blood|bread|fire|stone|garden)\b", re.I)

def toks(t):
    return [w for w in re.findall(r"[a-z][a-z'-]{2,}", t.lower()) if w not in STOP]

def brevity(n):
    if 38 <= n <= 100: return 1.0
    if 20 <= n < 38: return 0.9
    if 12 <= n < 20: return 0.6
    if n < 12: return 0.0
    return max(0.0, 1 - (n - 100) / 80)

DEFN = re.compile(r"[\"“”'‘’][^\"“”'‘’]{2,60}[\"“”'‘’]\s*(means|includes|shall mean|refers to)|\b(means|includes)\b.{0,40}\b(and includes|but does not include|but shall not include)", re.I)

def containment(t):
    s = 1.0
    if DEFN.search(t): s *= 0.15
    if re.match(r"^\s*[\"“'‘]", t): s *= 0.6
    if DEP.match(t.strip()): s *= 0.35
    if not t.strip()[0].isupper(): s *= 0.5
    if not re.search(r"[.!?;]\s*$", t.strip()): s *= 0.6
    if re.search(r"^\s*\d+\.?\s", t): s *= 0.7
    return s

def legalese(t, n):
    hits = len(LEGAL.findall(t)) + len(re.findall(r"\b\d+\b", t)) * 0.5
    return min(1.0, hits / max(8, n / 6))

def main():
    units = [json.loads(l) for l in open("units.jsonl")]
    # idf over constitutions: document = one constitution's full vocabulary
    vocab_by_cons = defaultdict(set)
    for u in units:
        if u["kind"] == "article":
            vocab_by_cons[u["cons_id"]].update(toks(u["text"]))
    N = len(vocab_by_cons)
    df = Counter()
    for v in vocab_by_cons.values(): df.update(v)
    idf = {w: math.log(N / c) for w, c in df.items()}
    # proper-noun-ish tokens: capitalised mid-sentence in the unit
    def distinct(u):
        t = u["text"]
        # mid-sentence capitals are usually proper nouns: drop the ones that name
        # the country itself, halve the rest (Gross National Happiness must survive)
        own = set(toks(u["country"] + " " + u["title"]))
        caps = {m.lower() for m in re.findall(r"(?<![.!?]\s)(?<!^)\b([A-Z][a-z]{2,})", t)}
        ws = [w for w in set(toks(t)) if w in idf and w not in own]
        if not ws: return 0.0
        vals = [idf[w] * (0.5 if w in caps else 1.0) for w in ws]
        top = sorted(vals, reverse=True)[:5]
        return sum(top) / len(top) / math.log(N)   # 0..1
    out = []
    for u in units:
        d = distinct(u); c = containment(u["text"]); b = brevity(u["words"])
        l = legalese(u["text"], u["words"])
        h = u["heading"]
        if ANTHEM.search(h) or ANTHEM.search(u["text"][:80]): c = 0.0   # lyrics: never
        elif NOISE_HEAD.search(h): c *= 0.3
        if listiness(u["text"]) > 0.5: c *= 0.3
        if u["text"].count("[") >= 3: c *= 0.6     # translator's bracketed glosses
        voice = 1 + 0.15 * min(3, len(FIRST.findall(u["text"]))) + 0.1 * min(4, len(IMAGE.findall(u["text"])))
        score = d * c * b * (1 - 0.8 * l) * voice
        u.update(dict(d=round(d,3), c=round(c,2), b=round(b,2), l=round(l,2), score=round(score,4)))
        out.append(u)
    out.sort(key=lambda u: -u["score"])
    with open("scored.jsonl", "w") as f:
        for u in out: f.write(json.dumps(u, ensure_ascii=False) + "\n")
    print(N, "constitutions,", len(out), "units scored;", len(idf), "vocab")

if __name__ == "__main__": main()
