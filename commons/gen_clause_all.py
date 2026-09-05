"""Every clause page in one pass: load the in-force paragraphs and articles once,
then one page per topic key that has at least one clause."""
import sys, os, json
sys.path.insert(0, os.path.expanduser("~/.claude/skills/fedwiki-lib")); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fedwiki, commons as C
from collections import defaultdict
FARM = os.path.expanduser("~/Nextcloud/fedwiki/clause.legalcommons.org")
CAP = 40
bykey = defaultdict(dict)     # key -> cid -> best unit
for cid, c in C.CONS.items():
    if not c["in_force"]: continue
    for u in C.units_for(cid):
        if u["kind"] == "run" or u["words"] < 8: continue
        for k in u["topics"]:
            b = bykey[k].get(cid)
            if b is None or (u["kind"] != "paragraph", abs(u["words"] - 50)) < (b["kind"] != "paragraph", abs(b["words"] - 50)):
                bykey[k][cid] = u
print(len(bykey), "keys with clauses", flush=True)
seen_slugs = {}
for key in sorted(bykey, key=lambda k: C.TOPICS.get(k, {}).get("label", k)):
    t = C.TOPICS.get(key)
    if not t: continue
    rows = sorted(bykey[key].items(), key=lambda kv: C.CONS[kv[0]]["country"])
    title = t["label"]; slug = fedwiki.as_slug(title)
    if slug in seen_slugs: title = f"{t['label']} ({key})"; slug = fedwiki.as_slug(title)
    seen_slugs[slug] = key
    parent = C.TOPICS.get(t["parent"], {}).get("label")
    items = [
      "This page is an AI generated [[Stub]]. Built from the [[Constitution Corpus]] by the [[Import Constitutions Plan]]; every quote is verbatim and cited by fragment id.",
      f"**{t['label']}** — {t['desc'] or 'a topic in the Constitute Project ontology.'} Key `{key}`" + (f", under [[{parent}]]" if parent else "") + f". Found in {len(rows)} constitutions in force; the first {min(CAP, len(rows))} follow, one clause each, chosen as the paragraph nearest fifty words so like reads against like.",
      "# The Clause, Constitution by Constitution",
    ]
    for cid, u in rows[:CAP]:
        c = C.CONS[cid]
        items.append(f"`{u['fid']}` — [[{C.page_title(c)}]], {u['heading'].split(' / ')[-1][:60]}\n\n> {u['text'][:700]}{'…' if len(u['text'])>700 else ''}")
    if len(rows) > CAP: items.append(f"… and {len(rows)-CAP} more. The full set is in the page's data asset.")
    A = f"{FARM}/assets/pages/{slug}"; os.makedirs(A, exist_ok=True)
    with open(f"{A}/{key}.jsonl", "w") as f:
        for cid, u in rows:
            if C.CONS[cid].get("copyright"): continue
            f.write(json.dumps(dict(fid=u["fid"], constitution=C.page_title(C.CONS[cid]), heading=u["heading"], text=u["text"]), ensure_ascii=False) + "\n")
    items += ["# Assets", {"type": "assets", "text": f"pages/{slug}"}, f"`{key}.jsonl` — every clause tagged `{key}` in a constitution in force whose translation is not under a publisher's copyright, with fragment ids. The library the drafting agent reads."]
    page = fedwiki.make_page(title, items, provenance="Import Constitutions Plan, gen_clause_all.py, 3 September 2026")
    fedwiki.ensure_see(page, ["[[Constitution Corpus]] · [[Import Constitutions Plan]] · [[Welcome Visitors]]"], journal=False)
    page["journal"].append(fedwiki.fork_entry("constitution.legalcommons.org"))   # constitution links live on the register
    fedwiki.save_page(f"{FARM}/pages/{slug}", page)
print(len(seen_slugs), "clause pages written", flush=True)
# site pages
PROV = "Claude Code, in dialogue with David Bovill, 3 September 2026"
def tree_lines():
    out = []
    for key, t in C.TOPICS.items():
        if t["parent"] is None and key in bykey:
            kids = [k for k, v in C.TOPICS.items() if v["parent"] == key and k in bykey]
            out.append(f"- [[{t['label']}]] — {len(bykey[key])} constitutions" + (f"; " + " · ".join(f"[[{C.TOPICS[k]['label']}]]" for k in sorted(kids, key=lambda k: C.TOPICS[k]['label'])[:12]) + (f" · and {len(kids)-12} more" if len(kids) > 12 else "") if kids else ""))
    return "\n".join(out)
w = fedwiki.make_page("Welcome Visitors", [
  "Welcome to the **Clause Library** — one page per topic in the Constitute Project's ontology, each showing the same clause as it is written in every constitution in force. Read like against like: how forty constitutions say what may never be amended, how sixty name a right to water, how the preambles begin.",
  f"{len(seen_slugs)} clause pages, built from the [[Constitution Corpus]] to the [[Import Constitutions Plan]]. Every quote is verbatim and cited by fragment id — `bhutan-2008:5.3` is Bhutan, 2008, Article 5, third paragraph — and each id links back to its constitution's page on the register at constitution.legalcommons.org.",
  "Each page carries a data asset with the full set of clauses under its key: the library a drafting agent reads when it helps write a constitution of our own.",
  "# Topics",
  tree_lines(),
], provenance=PROV)
fedwiki.ensure_see(w, ["[[Import Constitutions Plan]] · [[Constitution Corpus]] · [[About]]"], journal=False)
w["journal"].append(fedwiki.fork_entry("constitution.legalcommons.org"))
fedwiki.save_page(f"{FARM}/pages/welcome-visitors", w)
a = fedwiki.make_page("About", [
  "The site record for clause.legalcommons.org, per the [[Wiki Naming Convention]]. This page is never renamed.",
  "# Site Record",
  {"type": "code", "language": "yaml", "text": "\n".join(["site: clause.legalcommons.org", "host: pi5 (public mirror, /mnt/wikimedia/fedwiki)", "owner:", "  id: david", "  name: David Bovill",
    "purpose: the clause library — one page per Constitute topic key, the same clause across every constitution in force", "status: generated 2026-09-03 (Import Constitutions Plan, Phase 4)", "created: 2026-09-03",
    "twins: []", "siblings: [constitution.legalcommons.org, draft.legalcommons.org (proposed)]", "source: Constitute Project, constituteproject.org, non-commercial use", "formerly: []"])},
], provenance=PROV)
fedwiki.ensure_see(a, ["[[Import Constitutions Plan]] · [[Welcome Visitors]]"], journal=False)
fedwiki.save_page(f"{FARM}/pages/about", a)
# corpus + plan twins so the local links resolve
for slug in ("constitution-corpus", "import-constitutions-plan"):
    src = fedwiki.load_page(os.path.expanduser(f"~/Nextcloud/fedwiki/constitution.legalcommons.org/pages/{slug}"))
    src["journal"] = list(src["journal"]) + [fedwiki.fork_entry("constitution.legalcommons.org")]
    fedwiki.save_page(f"{FARM}/pages/{slug}", src)
print("site pages done")
