#!/usr/bin/env python3
"""Write the language of enactment onto every constitution page's # Record
(Multilingual City Plan, Phase 1). Adds, after the `translator:` line:

  language: es                 the language a native voice reads first (BCP-47)
  languages: [de, fr, it, rm]  only when the text was enacted in several
  language_confidence: high    high | medium | low, from languages.json
  native_edition: es           which edition in the mill IS the original: en, es, ar, or - (none yet)

Idempotent: a Record that already carries `language:` is left alone.
  python3 record_language.py [--farm DIR] [--dry-run]
"""
import json, os, sys, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.expanduser("~/.claude/skills/fedwiki-lib"))
import commons as C
import fedwiki as fw

FARM = os.path.expanduser("~/Nextcloud/fedwiki/constitution.legalcommons.org")
if "--farm" in sys.argv: FARM = sys.argv[sys.argv.index("--farm") + 1]
DRY = "--dry-run" in sys.argv
BY_PREFIX = {C.prefix(cid): cid for cid in C.CONS}

done = skipped = missing = 0; report = []
for path in sorted(glob.glob(os.path.join(FARM, "pages", "*"))):
    page = fw.load_page(path)
    rec = next((it for it in page["story"] if it.get("type") == "code" and it.get("text", "").startswith("constitution:")), None)
    if not rec: continue
    lines = rec["text"].split("\n")
    if any(l.startswith("language:") for l in lines): skipped += 1; continue
    pre = lines[0].split(":", 1)[1].strip()
    cid = BY_PREFIX.get(pre)
    e = C.enactment(cid) if cid else None
    if not e:
        missing += 1; report.append((os.path.basename(path), pre, "no entry")); continue
    lang = e["language"]; base = lang.split("-")[0]
    native = "en" if base == "en" else next((l for l in ("es", "ar") if base == l and os.path.exists(f"{C.MILL}/raw/aligned/{cid}.{l}.jsonl")), "-")
    new = [f"language: {lang}"]
    if len(e["languages"]) > 1: new.append("languages: [" + ", ".join(e["languages"]) + "]")
    new += [f"language_confidence: {e['confidence']}", f"native_edition: {native}"]
    at = next((i for i, l in enumerate(lines) if l.startswith("translator:")), len(lines) - 1)
    lines[at + 1:at + 1] = new
    rec["text"] = "\n".join(lines)
    fw.add_journal(page, "edit", rec)
    if not DRY: fw.save_page(path, page)
    done += 1; report.append((os.path.basename(path), pre, lang, native))
print(f"written {done}, already had language {skipped}, no entry {missing}{' (dry run)' if DRY else ''}")
for r in report:
    if r[2] == "no entry": print("  MISSING", r[0], r[1])
from collections import Counter
print("by language:", Counter(r[2] for r in report if r[2] != "no entry").most_common())
print("native editions:", Counter(r[3] for r in report if len(r) > 3))
