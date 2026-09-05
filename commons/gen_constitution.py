"""One constitution page for constitution.legalcommons.org."""
import sys, os, json, shutil, re
sys.path.insert(0, os.path.expanduser("~/.claude/skills/fedwiki-lib")); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fedwiki, commons as C
from collections import Counter
FARM = os.path.expanduser("~/Nextcloud/fedwiki/constitution.legalcommons.org")
TOPIC_DF = None
def topic_df():
    global TOPIC_DF
    if TOPIC_DF is None:
        df = Counter(); by = {}
        for l in open(f"{C.MILL}/units.jsonl"):
            u = json.loads(l)
            if u["kind"] == "article": by.setdefault(u["cons_id"], set()).update(u["topics"])
        for s in by.values(): df.update(s)
        TOPIC_DF = (df, len(by))
    return TOPIC_DF
def write_assets(cid, c, us, rclass, rnote, title, slug):
    """Write the page's assets folder and return the note item's text.
    Every text is attached — the restricted (publisher-copyright) translations
    too, since 5 September 2026 (David): the site is non-commercial, which is
    what the Constitute Project's CC BY-NC 3.0 terms allow, and SOURCE.md
    carries the rights line so a reader knows whose translation it is."""
    A = f"{FARM}/assets/pages/{slug}"; os.makedirs(A, exist_ok=True)
    shutil.copy(f"{C.MILL}/raw/html/{cid}.json", f"{A}/{cid}.json")
    open(f"{A}/{cid}.txt", "w").write(C.plain_text(cid))
    with open(f"{A}/{cid}.fragments.jsonl", "w") as f:
        for u in us:
            if u["kind"] != "run": f.write(json.dumps({k: u[k] for k in ("fid","kind","article","heading","topics","words","text","score")}, ensure_ascii=False) + "\n")
    files = f"`{cid}.json` is the original download from the Constitute Project, untouched. `{cid}.txt` is the plain text. `{cid}.fragments.jsonl` is every article and paragraph with its fragment id, topics and score."
    if rclass == "restricted":
        open(f"{A}/SOURCE.md", "w").write(f"# {title}\n\nThis translation is {rnote}.\n\nAttached here for non-commercial use under the Constitute Project's CC BY-NC 3.0 terms; the source copy is https://www.constituteproject.org/constitution/{cid}. Anything commercial needs the rights holder's permission first.\n")
        return files + f" The translation is {rnote} — attached for non-commercial use, see `SOURCE.md`."
    return files
def build(cid):
    c = C.CONS[cid]; us = C.units_for(cid); title = C.page_title(c); pre = C.prefix(cid)
    arts = [u for u in us if u["kind"] == "article"]; paras = [u for u in us if u["kind"] == "paragraph"]
    status = "in force" if c["in_force"] else ("a draft" if c["is_draft"] else "no longer in force")
    rclass, rnote = C.rights(c)
    words = c.get("word_length") or sum(u["words"] for u in arts)
    tops = Counter(t for u in arts for t in u["topics"])
    df, N = topic_df()
    rare = sorted((t for t in tops if t in C.TOPICS), key=lambda t: df[t])[:5]
    # speaking picks: best-scored paragraph-or-run units in the speakable band, one per article
    best = {}
    for u in us:
        if u["kind"] == "article" and u["words"] > 100: continue
        if u["c"] < 0.5 or u["words"] < 12: continue
        a = u["article"]
        if a not in best or u["score"] > best[a]["score"]: best[a] = u
    picks = sorted(best.values(), key=lambda u: -u["score"])[:6]
    pre_u = next((u for u in picks if u["article"] == "p"), None)
    if not pre_u:
        cand = [u for u in us if u["article"] == "p" and u["kind"] != "article" and u["words"] >= 12]
        if cand: picks = [max(cand, key=lambda u: u["score"])] + picks[:5]
    items = [
      "This page is an AI generated [[Stub]]. Built from the [[Constitution Corpus]] by the [[Import Constitutions Plan]]; the quotes are verbatim, the commentary is mechanical.",
      f"The **{title}** — {c['title_long']} — is {status}. {words:,} words in {len(arts)} articles and headings, {len(paras)} paragraphs, tagged with {len(tops)} of the Constitute Project's topics. Rights: {rnote}.",
      "# Record",
      {"type": "code", "language": "yaml", "text": "\n".join([
        f"constitution: {pre}", f"title: {title}", f"country: {c['country']}", f"region: {c['region']}",
        f"enacted: {c.get('year_enacted')}", f"revised: {c.get('year_revised') or '-'}", f"status: {status}",
        f"words: {words}", f"articles: {len(arts)}", f"paragraphs: {len(paras)}", f"topics: {len(tops)}",
        f"rights: {rclass}", f"translator: {c.get('translator') or '-'}", f"copyright: {c.get('copyright') or '-'}",
        f"source: https://www.constituteproject.org/constitution/{cid}", f"fragment_ids: {pre}:{{article}}.{{paragraph}}",
        f"pulled: 2026-09-02"])},
      "# For Speaking",
      "The fragments the [[Fragment Mill]] scores highest here — short enough to read aloud, complete enough to stand alone, and in the words that make this text unlike the others. Cite them by fragment id.",
    ]
    for u in picks:
        items.append(f"`{u['fid']}` — {u['heading'].split(' / ')[-1][:70]}\n\n> {u['text']}")
    items += ["# Notable",
      f"The topics this constitution carries that fewest others do — {N} constitutions in the corpus."]
    for t in rare:
        ex = next((u for u in paras if t in u["topics"] and 12 <= u["words"] <= 100), None) or next((u for u in arts if t in u["topics"]), None)
        line = f"- [[{C.TOPICS[t]['label']}]] — in {df[t]} of {N}"
        if ex: line += f". `{ex['fid']}`: \"{ex['text'][:160].rstrip()}{'…' if len(ex['text'])>160 else ''}\""
        items.append(line)
    items.append("# Structure")
    ol = C.outline(us)
    items.append("\n".join(f"- {h[:90]} — {n}" for h, n in ol[:40]) + (f"\n- … {len(ol)-40} more" if len(ol) > 40 else ""))
    items.append("# Topics")
    items.append("The most tagged topics, each a door to the same clause in every other constitution.")
    items.append("\n".join(f"- [[{C.TOPICS[t]['label']}]] — {n}" for t, n in tops.most_common(12) if t in C.TOPICS))
    # assets
    slug = fedwiki.as_slug(title)
    anote = write_assets(cid, c, us, rclass, rnote, title, slug)
    items += ["# Assets", {"type": "assets", "text": f"pages/{slug}"}, anote]
    page = fedwiki.make_page(title, items, provenance="Import Constitutions Plan, gen_constitution.py, 2 September 2026")
    fedwiki.ensure_see(page, ["[[Constitution Corpus]] · [[Import Constitutions Plan]] · [[Fragment Mill]]"], journal=False)
    page["journal"].append(fedwiki.fork_entry("clause.legalcommons.org"))   # topic links live on the clause site
    fedwiki.save_page(f"{FARM}/pages/{slug}", page)
    return slug, len(page["story"])
if __name__ == "__main__":
    ids = sorted(C.CONS) if sys.argv[1:] == ["--all"] else sys.argv[1:]
    for i, cid in enumerate(ids, 1):
        try: print(i, build(cid), flush=True)
        except Exception as e: print(i, cid, "FAILED", type(e).__name__, str(e)[:120], flush=True)
