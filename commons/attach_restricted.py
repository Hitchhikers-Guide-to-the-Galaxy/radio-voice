"""Attach the full text to every restricted (publisher-copyright) constitution
page on constitution.legalcommons.org — David's decision, 5 September 2026:
the site is non-commercial, which is what the Constitute Project's CC BY-NC
3.0 terms allow, so the 55 translations excerpted at import get the same three
files as the other 185, plus a SOURCE.md carrying the rights line.

Edits each page in place: the note under `# Assets` is rewritten and the edit
journalled. Idempotent — a page already carrying the new note is skipped.
"""
import sys, os
sys.path.insert(0, os.path.expanduser("~/.claude/skills/fedwiki-lib")); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fedwiki, commons as C
from gen_constitution import write_assets, FARM

PROV = "restricted texts attached for non-commercial use — David's decision 2026-09-05, attach_restricted.py"


def main(dry=False):
    done = skipped = 0
    for cid in sorted(C.CONS):
        c = C.CONS[cid]
        rclass, rnote = C.rights(c)
        if rclass != "restricted":
            continue
        title = C.page_title(c); slug = fedwiki.as_slug(title)
        path = f"{FARM}/pages/{slug}"
        page = fedwiki.load_page(path)
        story = page["story"]
        k = next((i for i, it in enumerate(story) if it.get("type") == "assets"), None)
        if k is None or k + 1 >= len(story):
            print("no assets item:", slug); continue
        note = story[k + 1]
        if "attached for non-commercial use" in note.get("text", ""):
            skipped += 1; continue
        if dry:
            print("would attach", cid, "->", slug); done += 1; continue
        us = C.units_for(cid)
        note["text"] = write_assets(cid, c, us, rclass, rnote, title, slug)
        fedwiki.add_journal(page, "edit", note, provenance=PROV)
        fedwiki.save_page(path, page)
        done += 1
        print(done, cid, "->", slug, flush=True)
    print(f"attached {done}, already done {skipped}")


if __name__ == "__main__":
    main(dry="--dry-run" in sys.argv)
