"""legislation.gov.uk CLML -> witness pages (one per provision) + instrument page.
Witness text is verbatim: Text nodes only, Commentary annotations and CommentaryRef
markers dropped, amendment wrappers (Addition/Substitution/Repeal) kept as the
current text they contain. Fragment ids: {instrument}:{section} / :p / :sch{n}."""
import sys, os, re, json, hashlib, html
import xml.etree.ElementTree as ET
sys.path.insert(0, os.path.expanduser("~/.claude/skills/fedwiki-lib")); import fedwiki
NS = {"l": "http://www.legislation.gov.uk/namespaces/legislation", "ukm": "http://www.legislation.gov.uk/namespaces/metadata", "dc": "http://purl.org/dc/elements/1.1/"}
L = "{%s}" % NS["l"]
FARM = os.path.expanduser("~/Nextcloud/fedwiki/constitution.legalcommons.org")
ROOT = os.path.dirname(os.path.abspath(__file__))
TODAY = "2026-09-03"
SKIP = {L + "Commentary", L + "CommentaryRef", L + "Commentaries", L + "Figure", L + "Image"}
ROMAN = {"I":1,"V":5,"X":10,"L":50,"C":100,"D":500,"M":1000}
def roman(s):
    s = s.strip().upper()
    if not s or not all(ch in ROMAN for ch in s): return None
    t = 0
    for i, ch in enumerate(s):
        v = ROMAN[ch]; t += -v if i + 1 < len(s) and ROMAN[s[i+1]] > v else v
    return t
def itext(el):
    """All text under el, skipping annotation subtrees."""
    if el is None: return ""
    out = []
    def walk(e):
        if e.tag in SKIP: return
        if e.text: out.append(e.text)
        for c in e:
            walk(c)
            if c.tail: out.append(c.tail)
    walk(el)
    return re.sub(r"\s+", " ", "".join(out)).strip()
def num(el):
    n = el.find("l:Pnumber", NS); return itext(n) if n is not None else ""
def lines(el, depth=0):
    """Yield (depth, label, text) units for a P1/Schedule body in order."""
    for c in el:
        tag = c.tag
        if tag in SKIP: continue
        if tag in (L+"P1para", L+"P2para", L+"P3para", L+"P4para", L+"P5para"):
            for g in c:
                if g.tag == L+"Text": yield depth, "", itext(g)
                elif g.tag in (L+"P2", L+"P3", L+"P4", L+"P5"): yield from lines(g, depth + 1)
                elif g.tag in SKIP: continue
                else: yield from lines(g, depth)
        elif tag in (L+"P2", L+"P3", L+"P4", L+"P5"):
            label = num(c)
            first = True
            for d, lab, t in lines(c, depth + 1):
                yield d, (f"({label})" if first and label and not lab else lab), t; first = False
        elif tag == L+"Pnumber": continue
        elif tag == L+"Text": yield depth, "", itext(c)
        elif tag in (L+"Title", L+"TitleBlock"): yield depth, "#", itext(c)
        else: yield from lines(c, depth)
def render(units):
    plain, htm = [], []
    for d, lab, t in units:
        if not t: continue
        if lab == "#": plain.append(f"\n{t}\n"); htm.append(f"<h4>{html.escape(t)}</h4>"); continue
        s = f"{lab} {t}".strip()
        plain.append(("  " * d) + s)
        htm.append(f'<p style="margin-left:{d*1.4}em">{html.escape(s)}</p>')
    return "\n".join(plain).strip(), "\n".join(htm)
def sha(s): return "sha256:" + hashlib.sha256(s.encode()).hexdigest()

def parse(slug, lid):
    r = ET.parse(f"{ROOT}/raw/{slug}.xml").getroot()
    title = r.findtext(".//dc:title", namespaces=NS).strip()
    meta = dict(title=title, lid=lid, version_date=r.get("RestrictStartDate"), modified=r.findtext(".//dc:modified", namespaces=NS),
                language=r.get("{http://www.w3.org/XML/1998/namespace}lang", "en"), extent=r.get("RestrictExtent"))
    prov = []
    # preamble: introductory text in the prelims + bare P blocks in the body
    pre = []
    for p in r.findall(".//l:PrimaryPrelims//l:IntroductoryText//l:P", NS) + [c for c in r.find(".//l:Primary/l:Body", NS) if c.tag == L+"P"]:
        t = itext(p)
        if t: pre.append((0, "", t))
    if pre:
        pl, ht = render(pre)
        prov.append(dict(kind="preamble", num="p", label="Preamble", title="Preamble", plain=pl, html=ht, status="in_force", uri=f"https://www.legislation.gov.uk/{lid}/introduction"))
    # sections: every P1 in the body, in order, with its group title and part/chapter path
    body = r.find(".//l:Primary/l:Body", NS)
    def path_of(el, anc):
        out = []
        for a in anc:
            if a.tag in (L+"Part", L+"Chapter", L+"Pblock"):
                n = a.find("l:Number", NS); tt = a.find("l:Title", NS)
                lab = " ".join(x for x in (itext(n), itext(tt)) if x)
                if lab: out.append(lab)
        return " / ".join(out)
    def walk(el, anc):
        for c in el:
            if c.tag in SKIP: continue
            if c.tag == L+"P1":
                n = num(c); grp = anc[-1] if anc and anc[-1].tag == L+"P1group" else None
                gt = itext(grp.find("l:Title", NS)) if grp is not None else ""
                pl, ht = render(list(lines(c)))
                status = "in_force" if pl.strip(". …") else "repealed"
                arabic = n if n.isdigit() else (str(roman(n)) if roman(n) else re.sub(r"[^0-9A-Za-z–-]", "", n))
                prov.append(dict(kind="section", num=n, id=arabic, label=f"Section {n}", title=gt, path=path_of(c, anc), plain=pl, html=ht, status=status,
                                 uri=c.get("DocumentURI", "").replace("http://", "https://")))
            else:
                walk(c, anc + [c])
    walk(body, [])
    # schedules: one witness per schedule
    for i, s in enumerate(r.findall(".//l:Schedules/l:Schedule", NS), 1):
        n = itext(s.find("l:Number", NS)) or f"SCHEDULE {i}"; tt = itext(s.find("l:TitleBlock", NS)) or itext(s.find("l:Title", NS))
        units = []
        for c in s:
            if c.tag in (L+"Number", L+"TitleBlock", L+"Title", L+"Reference") or c.tag in SKIP: continue
            units += list(lines(c))
        pl, ht = render(units)
        m = re.search(r"\d+", n); sid = m.group(0) if m else str(i)
        prov.append(dict(kind="schedule", num=sid, id=f"sch{sid}", label=n.title(), title=tt, plain=pl, html=ht, status="in_force" if pl.strip(". …") else "repealed",
                         uri=f"https://www.legislation.gov.uk/{lid}/schedule/{sid}"))
    return meta, prov

def short(title):   # "Well-being of Future Generations (Wales) Act 2015" stays; "Magna Carta (1297)" -> "Magna Carta 1297"; "Bill of Rights [1688]" -> "Bill of Rights 1688"
    return re.sub(r"[\[\(](\d{4})[\]\)]", r"\1", title).strip()

def write(slug, lid, dry=False):
    meta, prov = parse(slug, lid); inst = short(meta["title"]); fid = slug
    live = [p for p in prov if p["status"] == "in_force"]
    if dry:
        print(f"{inst}: {len(prov)} provisions, {len(live)} in force; preamble={'yes' if prov and prov[0]['kind']=='preamble' else 'no'}; sections={sum(p['kind']=='section' for p in prov)}; schedules={sum(p['kind']=='schedule' for p in prov)}")
        if prov and prov[0]["kind"] == "preamble": print("   preamble:", prov[0]["plain"][:160])
        return
    PROV = f"Imported by Claude Code from legislation.gov.uk ({lid}) under the Open Government Licence v3.0, {TODAY}; canonical text unmodified"
    toc = []
    for p in prov:
        if p["status"] != "in_force":
            toc.append(f"- {p['label']} {('— ' + p['title']) if p.get('title') else ''} — repealed"); continue
        ptitle = f"{inst} {p['label']}"; pslug = fedwiki.as_slug(ptitle)
        fragment = f"{fid}:{p['id'] if p['kind']!='preamble' else 'p'}"
        rec = {"jurisdiction": "United Kingdom" if not slug.endswith("wales-act-2015") else "Wales, United Kingdom", "instrument": inst, "provision": p["label"] + (f" — {p['title']}" if p.get("title") else ""),
               "fragment_id": fragment, "version_date": meta["version_date"], "status": p["status"], "text_language": meta["language"], "translation_source": "none — original",
               "translation_rights": "n/a", "source_url": p["uri"], "source_format": "xml (CLML)", "rights": "OGL v3 — Open Government Licence", "retrieved_at": TODAY,
               "source_hash": sha(p["plain"]), "canonical_text_modified": "false"}
        if p.get("path"): rec["path"] = p["path"]
        items = [
          {"type": "html", "text": f'<div class="witness">{p["html"]}</div>'},
          "# Record", {"type": "code", "language": "yaml", "text": "\n".join(f"{k}: {v}" for k, v in rec.items())},
        ]
        page = fedwiki.make_page(ptitle, items, provenance=PROV)
        fedwiki.ensure_see(page, [f"[[{inst}]] · [[Seed Collection]] · [[UK Legislation]]"], journal=False)
        fedwiki.save_page(f"{FARM}/pages/{pslug}", page)
        toc.append(f"- [[{ptitle}]]" + (f" — {p['title']}" if p.get("title") else "") + (f" ({p['path']})" if p.get("path") else ""))
    # instrument page
    islug = fedwiki.as_slug(inst); A = f"{FARM}/assets/pages/{islug}"; os.makedirs(A, exist_ok=True)
    raw = open(f"{ROOT}/raw/{slug}.xml", "rb").read(); open(f"{A}/{slug}.data.xml", "wb").write(raw)
    open(f"{A}/{slug}.txt", "w").write("\n\n".join(f"[{p['label']}{(' — ' + p['title']) if p.get('title') else ''}]\n{p['plain']}" for p in prov if p["status"] == "in_force"))
    words = sum(len(p["plain"].split()) for p in live)
    rec = {"jurisdiction": "United Kingdom", "instrument": inst, "legislation_id": lid, "fragment_ids": f"{fid}:{{section}} · {fid}:p · {fid}:sch{{n}}", "version_date": meta["version_date"],
           "source_modified": meta["modified"], "extent": meta["extent"] or "-", "status": "in_force", "provisions_in_force": len(live), "provisions_repealed": len(prov) - len(live), "words_in_force": words,
           "text_language": meta["language"], "source_url": f"https://www.legislation.gov.uk/{lid}", "source_format": "xml (CLML), data.xml", "rights": "OGL v3 — Open Government Licence",
           "retrieved_at": TODAY, "source_hash": sha(raw.decode("utf-8", "ignore"))}
    items = [
      f"This page was imported by [[Claude Code]] from legislation.gov.uk on {TODAY}, to the [[Import Constitutions Plan]]. It is an instrument page in the [[Witness Reading Instrument]] sense: a table of contents whose every entry is a verbatim witness page.",
      f"The **{inst}** — {meta['title']} — as it stands on legislation.gov.uk at version date {meta['version_date']}: {len(live)} provisions in force ({words:,} words) and {len(prov)-len(live)} repealed. Crown copyright, reused under the Open Government Licence v3.0.",
      "# Record", {"type": "code", "language": "yaml", "text": "\n".join(f"{k}: {v}" for k, v in rec.items())},
      "# Provisions", "\n".join(toc),
      "# Assets", {"type": "assets", "text": f"pages/{islug}"},
      f"`{slug}.data.xml` is the original download, untouched. `{slug}.txt` is the plain text of every provision in force.",
    ]
    page = fedwiki.make_page(inst, items, provenance=PROV)
    fedwiki.ensure_see(page, ["[[Seed Collection]] · [[UK Legislation]] · [[Constitutional Sources]] · [[Witness Reading Instrument]]"], journal=False)
    fedwiki.save_page(f"{FARM}/pages/{islug}", page)
    print(f"{inst}: {len(live)} witness pages + instrument page ({len(prov)-len(live)} repealed listed)")

if __name__ == "__main__":
    ids = json.load(open(f"{ROOT}/ids.json")); dry = "--dry" in sys.argv
    for slug, lid in ids.items(): write(slug, lid, dry=dry)
