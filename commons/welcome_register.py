import sys, os, json
sys.path.insert(0, os.path.expanduser("~/.claude/skills/fedwiki-lib")); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fedwiki, commons as C
from collections import defaultdict
FARM = os.path.expanduser("~/Nextcloud/fedwiki/constitution.legalcommons.org")
cons = sorted(C.CONS.values(), key=lambda c: (c["region"] or "", c["country"], c["id"]))
inf = [c for c in cons if c["in_force"]]; sup = [c for c in cons if not c["in_force"] and not c["is_draft"]]; dr = [c for c in cons if c["is_draft"]]
byreg = defaultdict(list)
for c in inf: byreg[c["region"] or "Unplaced"].append(c)
def links(cs): return " · ".join(f"[[{C.page_title(c)}]]" for c in cs)
items = [
 "Welcome to the **Constitution Commons** — the world's constitutions on a federated wiki, one page per text, cut into fragments that can be cited, spoken on the radio, and compared clause by clause across countries on the [[Clause Library]] at clause.legalcommons.org.",
 f"{len(cons)} texts from the [[Constitution Corpus]] — {len(inf)} in force, {len(sup)} superseded, {len(dr)} drafts — built to the [[Import Constitutions Plan]]. Each page carries a Record, the fragments the [[Fragment Mill]] scores highest for speaking, the topics few others carry, the outline, and the original download where the translation's rights allow. Fragment ids read `bhutan-2008:5.3` — constitution, article, paragraph.",
 "# In Force, by Region",
]
for reg in sorted(byreg): items += [f"## {reg}", links(byreg[reg])]
items += ["# Superseded", "Earlier texts the Constitute Project still lists — replaced, suspended or reinstated since.", links(sup),
          "# Drafts", links(dr),
          "# Sites", "- [[Import Constitutions Plan]] — the plan and its checkpoints\n- [[Constitution Corpus]] — coverage, API, rights\n- [[Clause Library]] — the same clause across every constitution, on clause.legalcommons.org\n- [[About]] — the site record"]
w = fedwiki.make_page("Welcome Visitors", items, provenance="Claude Code, in dialogue with David Bovill, 3 September 2026")
fedwiki.ensure_see(w, ["[[Import Constitutions Plan]] · [[Clause Library]] · [[About]]"], journal=False)
w["journal"].append(fedwiki.fork_entry("clause.legalcommons.org"))
fedwiki.save_page(f"{FARM}/pages/welcome-visitors", w)
# a Clause Library page here that points at the other site's welcome
cl = fedwiki.make_page("Clause Library", [
 "The **Clause Library** lives at clause.legalcommons.org — one page per topic in the Constitute ontology, each showing the same clause as every constitution in force writes it. Start at its [[Welcome Visitors]] page, or open a topic from any constitution page's Topics section.",
 {"type": "reference", "site": "clause.legalcommons.org", "slug": "welcome-visitors", "title": "Welcome Visitors", "text": "The Clause Library — 329 topic pages, the same clause across every constitution in force."},
], provenance="Claude Code, in dialogue with David Bovill, 3 September 2026")
fedwiki.ensure_see(cl, ["[[Import Constitutions Plan]] · [[Welcome Visitors]]"], journal=False)
cl["journal"].append(fedwiki.fork_entry("clause.legalcommons.org"))
fedwiki.save_page(f"{FARM}/pages/clause-library", cl)
print("welcome:", len(inf), "in force in", len(byreg), "regions;", len(sup), "superseded;", len(dr), "drafts")
