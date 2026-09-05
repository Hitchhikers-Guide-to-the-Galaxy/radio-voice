"""Constitution Hour page: every rendered cue as an audio item — framing line,
fragment text, voice, source — from out/twenty/manifest.json. Uploads are
absolute https URLs on the radio-agentic site."""
import sys, os, json, shutil
sys.path.insert(0, os.path.expanduser("~/.claude/skills/fedwiki-lib"))
import fedwiki
ROOT = os.path.dirname(os.path.abspath(__file__)); SITE = "https://radio-agentic.private.fish"
man = json.load(open(f"{ROOT}/out/twenty/manifest.json"))
OUT = f"{ROOT}/pages"; A = f"{OUT}/assets/constitution-hour"; os.makedirs(A, exist_ok=True)
for m in man: shutil.copy(f"{ROOT}/out/twenty/{m['slug']}.m4a", A)
shutil.copy(f"{ROOT}/out/twenty/constitution-twenty.m4a", A); shutil.copy(f"{ROOT}/out/twenty/manifest.json", A)
tot = sum(m["seconds"] for m in man)
PROV = "Claude Code, in dialogue with David Bovill, 2 September 2026"
def player(name, cap):
    return {"type": "html", "text": f'<audio controls preload="none" style="width:100%" src="{SITE}/assets/pages/constitution-hour/{name}.m4a"></audio>\n<p><i>{cap}</i></p>'}
items = [
 "This page was written by [[Claude Code]] in dialogue with [[David Bovill]], 2 September 2026. Phase 2 of the [[Radio Voice Plan]] — the first cut.",
 player("constitution-twenty", f"All twenty cues in order, {tot/60:.0f} minutes. The framing line is read by george; each fragment by its assigned voice."),
 f"The **Constitution Hour** is the [[Fragment Mill]]'s twenty, rendered through the [[Voice Bench]] palette as radio cues. Each cue is a framing line — what this is, where it comes from — then a breath, then the fragment. This first cut runs {tot/60:.0f} minutes; the hour fills out from the next twenty and the idents. Texts from the [[Constitution Corpus]] (Constitute Project, non-commercial use, attributed).",
 "# The Cues",
]
for m in man:
    items.append(player(m["slug"], f"{m['n']}. {m['title']} — {m['heading'][:70]}. Voice {m['voice']}, {m['seconds']:.0f} s."))
    items.append(f"{m['frame']}\n\n> {m['text']}")
items += [
 "# How It Was Made",
 "`render_twenty.py` in `~/Code/radio-voice/` holds one Kokoro instance for the batch and writes each cue as 0.3 s of silence, the framing line by the announcer, 0.7 s, the fragment, 1 s. Two cues — Magna Carta and Denmark — go through the retro chain. Total render time is on the page's manifest. Nothing here has touched the station yet: the next checkpoint adds these files to the Mini as their own playlist source beneath live.",
]
slug = "constitution-hour"
page = fedwiki.make_page("Constitution Hour", items, provenance=PROV)
fedwiki.ensure_assets(page, f"pages/{slug}", journal=False)
fedwiki.ensure_see(page, ["[[Radio Voice Plan]] · [[Fragment Mill]] · [[Voice Bench]] · [[Constitution Corpus]]", "[[Constitutional Radio]] · [[The Station As It Stands]]"], journal=False)
fedwiki.save_page(f"{OUT}/{slug}", page)
print("built", slug, len(man), "cues,", f"{tot/60:.1f} min")
