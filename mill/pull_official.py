#!/usr/bin/env python3
"""Official originals for languages Constitute does not serve (Multilingual City
Plan, Phase 1). Each source is fetched once into raw/official-src/, parsed into
articles, and written as raw/official/{cid}.{lang}.jsonl with the English fragment
id ({constitution}:{article}) so it aligns with the mill by article number.
Sources and their terms are recorded on the Source Register page of the lab.

  python3 pull_official.py [de|fr|pt-BR|pt-PT|it ...]   # default: all
"""
import json, os, re, sys, html, urllib.request, zipfile
from html.parser import HTMLParser
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "commons"))
import commons as C

SRC = "raw/official-src"; OUT = "raw/official"
UA = "Mozilla/5.0 (Macintosh) radio-voice-mill/0.1"
SOURCES = {
  "de":    dict(cid="German_Federal_Republic_2014", url="https://www.gesetze-im-internet.de/gg/xml.zip", file="gg.xml.zip",
                source="gesetze-im-internet.de (Bundesministerium der Justiz), Grundgesetz, XML", terms="official work, free of copyright (§5 UrhG)"),
  "fr":    dict(cid="France_2024", url="https://www.conseil-constitutionnel.fr/le-bloc-de-constitutionnalite/texte-integral-de-la-constitution-du-4-octobre-1958-en-vigueur", file="fr.html",
                source="Conseil constitutionnel, texte intégral de la Constitution du 4 octobre 1958 en vigueur", terms="official text; site terms to confirm"),
  "pt-BR": dict(cid="Brazil_2017", url="https://www.planalto.gov.br/ccivil_03/constituicao/constituicao.htm", file="br.html",
                source="Planalto (Presidência da República), Constituição de 1988, texto compilado", terms="official act of the Brazilian state"),
  "pt-PT": dict(cid="Portugal_2005", url="https://www.parlamento.pt/Legislacao/Paginas/ConstituicaoRepublicaPortuguesa.aspx", file="pt.html",
                source="Assembleia da República, Constituição da República Portuguesa (VII revisão)", terms="official text; site terms to confirm"),
  "de-CH": dict(cid="Switzerland_2014", url="https://fedlex.data.admin.ch/filestore/fedlex.data.admin.ch/eli/cc/1999/404/20240303/de/html/fedlex-data-admin-ch-eli-cc-1999-404-20240303-de-html-10.html", file="ch-de.html",
                source="Fedlex (Bundeskanzlei), Bundesverfassung, Stand 3. März 2024", terms="Swiss federal law is not copyright protected (Art. 5 URG)"),
  "fr-CH": dict(cid="Switzerland_2014", url="https://fedlex.data.admin.ch/filestore/fedlex.data.admin.ch/eli/cc/1999/404/20240303/fr/html/fedlex-data-admin-ch-eli-cc-1999-404-20240303-fr-html-10.html", file="ch-fr.html",
                source="Fedlex (Chancellerie fédérale), Constitution fédérale, état le 3 mars 2024", terms="Swiss federal law is not copyright protected (Art. 5 URG)"),
  "it-CH": dict(cid="Switzerland_2014", url="https://fedlex.data.admin.ch/filestore/fedlex.data.admin.ch/eli/cc/1999/404/20240303/it/html/fedlex-data-admin-ch-eli-cc-1999-404-20240303-it-html-10.html", file="ch-it.html",
                source="Fedlex (Cancelleria federale), Costituzione federale, stato 3 marzo 2024", terms="Swiss federal law is not copyright protected (Art. 5 URG)"),
  "rm":    dict(cid="Switzerland_2014", url="https://fedlex.data.admin.ch/filestore/fedlex.data.admin.ch/eli/cc/1999/404/20240303/rm/html/fedlex-data-admin-ch-eli-cc-1999-404-20240303-rm-html-8.html", file="ch-rm.html",
                source="Fedlex (Chanzlia federala), Constituziun federala, versiun dals 3 da mars 2024", terms="Swiss federal law is not copyright protected (Art. 5 URG)"),
  "it":    dict(cid="Italy_2020", url="https://it.wikisource.org/wiki/Italia,_Repubblica_-_Costituzione", file="it.html",
                source="Wikisource (it), Costituzione della Repubblica Italiana", terms="official act, not copyright protected in Italy (art. 5 l. 633/1941); Wikisource page CC BY-SA"),
}

def fetch(url, path):
    if os.path.exists(path) and os.path.getsize(path) > 1000: return
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=90) as r: open(path, "wb").write(r.read())

class Lines(HTMLParser):
    """HTML -> text lines. Block tags break lines; struck-through text (revoked clauses) is dropped."""
    BLOCK = {"p", "div", "br", "h1", "h2", "h3", "h4", "h5", "h6", "li", "tr", "td", "table", "section", "article"}
    DROP = {"s", "strike", "del", "script", "style", "sup"}
    def __init__(self):
        super().__init__(); self.lines = [[]]; self.drop = 0
    def handle_starttag(self, tag, attrs):
        if tag in self.DROP: self.drop += 1
        if tag in self.BLOCK: self.lines.append([])
    def handle_endtag(self, tag):
        if tag in self.DROP and self.drop: self.drop -= 1
        if tag in self.BLOCK: self.lines.append([])
    def handle_data(self, d):
        if not self.drop: self.lines[-1].append(d)
    def text(self):
        out = []
        for l in self.lines:
            t = re.sub(r"\s+", " ", html.unescape("".join(l))).strip()
            if t: out.append(t)
        return out

def html_lines(path, enc="utf-8"):
    p = Lines(); p.feed(open(path, encoding=enc, errors="replace").read()); return p.text()

def cut_articles(lines, art_re, stop_re, start_at=None, end_at=None):
    """Walk text lines; an article starts at art_re (group 1 = number) and ends at the next
    article or a structural heading (stop_re). Text on the article line after the marker is
    its first paragraph."""
    arts = []; cur = None; on = start_at is None
    for l in lines:
        if not on:
            if re.search(start_at, l): on = True
            else: continue
        if end_at and re.search(end_at, l) and arts: break
        m = art_re.match(l)
        if m:
            cur = dict(article=m.group(1), heading=l[:80], paras=[]); arts.append(cur)
            rest = l[m.end():].strip(" .-–—:")
            if rest: cur["paras"].append(rest)
            continue
        if cur is None: continue
        if stop_re.match(l): cur = None; continue
        cur["paras"].append(l)
    return tidy(arts)

def tidy(arts):
    """Pages carry a table of contents that repeats every marker without text: keep, per article
    number, the occurrence with the most paragraphs. A short first line with no full stop is the
    article's title, not its text."""
    best = {}
    for a in arts:
        if a["article"] not in best or len(a["paras"]) > len(best[a["article"]]["paras"]): best[a["article"]] = a
    out = []
    for a in best.values():
        if a["paras"] and len(a["paras"][0]) < 70 and not a["paras"][0].rstrip().endswith((".", ";", ":")):
            a["heading"] = (a["heading"].split(" ")[0] + " " + a["article"] + " — " + a["paras"].pop(0))[:80]
        out.append(a)
    return out

def parse_de(path):
    z = zipfile.ZipFile(path); name = [n for n in z.namelist() if n.endswith(".xml")][0]
    x = z.read(name).decode("utf-8")
    arts = []
    for norm in re.findall(r"<norm[^>]*>(.*?)</norm>", x, re.S):
        eb = re.search(r"<enbez>([^<]*)</enbez>", norm)
        if not eb: continue
        m = re.match(r"Art\.?\s*(\d+[a-z]?)$", eb.group(1).strip())
        if not m: continue
        body = re.search(r"<textdaten>(.*?)</textdaten>", norm, re.S)
        if not body: continue
        paras = []
        for p in re.findall(r"<P>(.*?)</P>", body.group(1), re.S):
            t = re.sub(r"<[^>]+>", " ", p); t = re.sub(r"\s+", " ", html.unescape(t)).strip()
            if t: paras.append(t)
        arts.append(dict(article=m.group(1), heading=eb.group(1).strip(), paras=paras))
    return arts

def parse_fr(path):
    lines = html_lines(path)
    art = re.compile(r"^ARTICLE\s+(PREMIER|\d+(?:-\d+)?)\.?\s*(.*)$")
    fixed = []
    for l in lines:
        m = art.match(l)
        if m: l = "ARTICLE " + ("1" if m.group(1) == "PREMIER" else m.group(1)) + " " + m.group(2)
        fixed.append(l)
    return cut_articles(fixed, re.compile(r"^ARTICLE\s+(\d+(?:-\d+)?)\b\.?"), re.compile(r"^(TITRE|Titre|PRÉAMBULE|Préambule|DÉCLARATION|Charte)\b"),
                        start_at=r"^PR[ÉE]AMBULE", end_at=r"^TITRE XVII|Fin du texte")

def parse_pt_br(path):
    lines = html_lines(path, enc="cp1252")
    return cut_articles(lines, re.compile(r"^Art\.\s*(\d+)[ºo°]?[\.\s-]*"), re.compile(r"^(TÍTULO|CAPÍTULO|Seção|SEÇÃO|Subseção|ATO DAS DISPOSIÇÕES|ADCT|PREÂMBULO)\b"),
                        start_at=r"^PREÂMBULO|^T[ÍI]TULO I\b", end_at=r"^ATO DAS DISPOSIÇÕES CONSTITUCIONAIS")

def parse_pt_pt(path):
    lines = html_lines(path)
    return cut_articles(lines, re.compile(r"^Artigo\s+(\d+)\.?[ºo°]?\s*"), re.compile(r"^(TÍTULO|CAPÍTULO|PARTE|Título|Capítulo|Parte|Secção|SECÇÃO|Preâmbulo|PREÂMBULO)\b"),
                        start_at=r"^Pre[âa]mbulo|^PRE[ÂA]MBULO")

def parse_it(path):
    lines = html_lines(path)
    return cut_articles(lines, re.compile(r"^Art\.\s*(\d+)\.?\s*"), re.compile(r"^(TITOLO|Titolo|PARTE|Parte|Sezione|SEZIONE|Principi fondamentali|PRINCIPI FONDAMENTALI|Disposizioni transitorie|DISPOSIZIONI TRANSITORIE)\b"),
                        start_at=r"^Principi fondamentali|^PRINCIPI FONDAMENTALI", end_at=r"^Disposizioni transitorie|^DISPOSIZIONI TRANSITORIE")

def parse_fedlex(path):
    x = open(path, encoding="utf-8").read(); arts = []
    starts = [(m.start(), m.group(1)) for m in re.finditer(r'<article id="art_([0-9]+[a-z]*)"', x)]
    for i, (pos, num) in enumerate(starts):
        block = x[pos:starts[i + 1][0] if i + 1 < len(starts) else len(x)]
        m = type("M", (), {"group": lambda self, k=1: num})()
        h = re.search(r'<h6 class="heading"[^>]*>(.*?)</h6>', block, re.S)
        heading = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", h.group(1)))).strip() if h else f"Art. {m.group(1)}"
        paras = []
        for p in re.findall(r'<p\b[^>]*class="absatz[^"]*"[^>]*>(.*?)</p>', block, re.S):
            t = re.sub(r"<sup>.*?</sup>", "", p, flags=re.S); t = re.sub(r"<[^>]+>", " ", t); t = re.sub(r"\s+", " ", html.unescape(t)).strip()
            if t: paras.append(t)
        arts.append(dict(article=m.group(1), heading=heading[:80], paras=paras))
    return arts

PARSERS = {"de": parse_de, "de-CH": parse_fedlex, "fr-CH": parse_fedlex, "it-CH": parse_fedlex, "rm": parse_fedlex, "fr": parse_fr, "pt-BR": parse_pt_br, "pt-PT": parse_pt_pt, "it": parse_it}

def main():
    langs = sys.argv[1:] or list(SOURCES)
    os.makedirs(SRC, exist_ok=True); os.makedirs(OUT, exist_ok=True)
    print("lang\tcid\tarticles\tin_english\tmatched\tempty\tfirst")
    for lang in langs:
        s = SOURCES[lang]; path = os.path.join(SRC, s["file"]); fetch(s["url"], path)
        arts = PARSERS[lang](path)
        cid = s["cid"]; pre = C.prefix(cid)
        en = {u["article"] for u in C.units_for(cid) if u["kind"] == "article"}
        rows = []; matched = empty = 0
        for a in arts:
            fid = f"{pre}:{a['article']}"
            hit = a["article"] in en; matched += hit; empty += (not a["paras"])
            rows.append(dict(fid=fid, article=a["article"], in_english=hit, heading=a["heading"], paras=a["paras"], language=lang, source=s["source"], terms=s["terms"]))
        with open(f"{OUT}/{cid}.{lang}.jsonl", "w") as f:
            for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")
        first = (rows[0]["paras"][0][:70] if rows and rows[0]["paras"] else "")
        print(f"{lang}\t{cid}\t{len(rows)}\t{len(en)}\t{matched}\t{empty}\t{first}")

if __name__ == "__main__":
    main()
