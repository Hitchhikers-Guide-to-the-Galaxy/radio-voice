"""Category pages for the clause site: every ontology key that is a parent of a
generated clause page but has no clauses of its own."""
import sys, os
sys.path.insert(0, os.path.expanduser("~/.claude/skills/fedwiki-lib")); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fedwiki, commons as C
FARM = os.path.expanduser("~/Nextcloud/fedwiki/clause.legalcommons.org")
existing = set(os.listdir(f"{FARM}/pages"))
slug_of = {k: fedwiki.as_slug(t["label"]) for k, t in C.TOPICS.items()}
def title_for(k):   # match gen_clause_all's disambiguation for the one label collision
    return C.TOPICS[k]["label"] if k != "elections" or slug_of[k] not in existing else C.TOPICS[k]["label"]
n = 0
for key, t in C.TOPICS.items():
    slug = slug_of[key]
    if slug in existing: continue
    kids = [k for k, v in C.TOPICS.items() if v["parent"] == key]
    if not kids: continue
    present = [k for k in kids if slug_of[k] in existing]
    if not present: continue
    parent = C.TOPICS.get(t["parent"], {}).get("label")
    items = [
      "This page is an AI generated [[Stub]] — a category in the Constitute Project's topic ontology, built by the [[Import Constitutions Plan]].",
      f"**{t['label']}** — {t['desc'] or 'a category of topics.'} Key `{key}`" + (f", under [[{parent}]]" if parent else "") + f". {len(present)} topics beneath it have clause pages.",
      "# Topics",
      "\n".join(f"- [[{C.TOPICS[k]['label']}]] — {C.TOPICS[k]['count']} constitutions tagged" for k in sorted(present, key=lambda k: C.TOPICS[k]["label"])),
    ]
    page = fedwiki.make_page(t["label"], items, provenance="Import Constitutions Plan, gen_categories.py, 3 September 2026")
    fedwiki.ensure_see(page, ["[[Welcome Visitors]] · [[Import Constitutions Plan]]"], journal=False)
    fedwiki.save_page(f"{FARM}/pages/{slug}", page); existing.add(slug); n += 1
print(n, "category pages written")
