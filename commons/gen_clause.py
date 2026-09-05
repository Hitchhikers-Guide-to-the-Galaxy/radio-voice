"""One clause page per Constitute topic key: the same clause in every constitution."""
import sys, os, json
sys.path.insert(0, os.path.expanduser("~/.claude/skills/fedwiki-lib")); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fedwiki, commons as C
FARM = os.path.expanduser("~/Nextcloud/fedwiki/constitution.legalcommons.org")
def build(key, cap=40):
    t = C.TOPICS[key]; rows = []
    for cid, c in sorted(C.CONS.items(), key=lambda kv: kv[1]["country"]):
        if not c["in_force"]: continue
        us = [u for u in C.units_for(cid) if key in u["topics"] and u["kind"] != "run" and u["words"] >= 8]
        if not us: continue
        u = min(us, key=lambda u: (u["kind"] != "paragraph", abs(u["words"] - 50)))
        rows.append((c, u))
    parent = C.TOPICS.get(t["parent"], {}).get("label")
    items = [
      "This page is an AI generated [[Stub]]. Built from the [[Constitution Corpus]] by the [[Import Constitutions Plan]]; every quote is verbatim and cited by fragment id.",
      f"**{t['label']}** — {t['desc'] or 'a topic in the Constitute Project ontology'} Key `{key}`" + (f", under {parent}" if parent else "") + f". Found in {len(rows)} constitutions in force; the first {min(cap, len(rows))} follow, one clause each, chosen as the paragraph nearest fifty words so like reads against like.",
      "# The Clause, Constitution by Constitution",
    ]
    for c, u in rows[:cap]:
        items.append(f"`{u['fid']}` — [[{c['title']}]], {u['heading'].split(' / ')[-1][:60]}\n\n> {u['text'][:700]}{'…' if len(u['text'])>700 else ''}")
    if len(rows) > cap: items.append(f"… and {len(rows)-cap} more. The full set is in the page's data asset.")
    slug = fedwiki.as_slug(t["label"]); A = f"{FARM}/assets/pages/{slug}"; os.makedirs(A, exist_ok=True)
    with open(f"{A}/{key}.jsonl", "w") as f:
        for c, u in rows:
            if c.get("copyright"): continue      # restricted translations stay as page excerpts only
            f.write(json.dumps(dict(fid=u["fid"], constitution=c["title"], heading=u["heading"], text=u["text"]), ensure_ascii=False) + "\n")
    items += ["# Assets", {"type": "assets", "text": f"pages/{slug}"}, f"`{key}.jsonl` — every clause tagged `{key}` in a constitution in force whose translation is not under a publisher's copyright, with fragment ids. The library the drafting agent reads."]
    page = fedwiki.make_page(t["label"], items, provenance="Import Constitutions Plan, gen_clause.py, 2 September 2026")
    fedwiki.ensure_see(page, ["[[Constitution Corpus]] · [[Import Constitutions Plan]]"], journal=False)
    fedwiki.save_page(f"{FARM}/pages/{slug}", page)
    return slug, len(rows)
if __name__ == "__main__":
    for k in sys.argv[1:]: print(build(k))
