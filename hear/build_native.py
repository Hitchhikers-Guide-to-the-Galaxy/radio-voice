#!/usr/bin/env python3
"""build_native.py — give every house that has its text in the language it was
enacted in a NATIVE voice beside its English one (Multilingual City Plan,
Phase 3).  For each constitution page whose manifest already carries an English
verbatim fragment, this finds the same fragment in the language of enactment
(Constitute's Spanish or Arabic edition aligned by section id; the official
originals for German, French, Portuguese and Italian), renders it with the
palette voice chosen by the Voice Lab (native: true in voices.json — Kokoro
in-process on this machine, Piper over ssh on the MacMini), runs the same
closed-loop loudness pipeline as build_street.py, names the files per
Multilingual File Names ({fid}.{lang}.{ext}), appends the asset to the page's
wiki-city-media.json (schema 0.2.0), validates it (M11 checks the tag), and
adds an audio item plus a provenance line under # Multilingual on the page.

  build_native.py [--only SLUG] [--lang es] [--dry-run] [--no-write-page] [--limit N]
"""
import argparse, json, os, re, subprocess, sys, time, tempfile
HERE = os.path.dirname(os.path.abspath(__file__)); RV = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(RV, "commons")); sys.path.insert(0, os.path.expanduser("~/.claude/skills/fedwiki-lib"))
import fedwiki as fw, commons as C
from validate import validate_file
import build_street as B

PROV = "Multilingual City Plan Phase 3 — build_native.py (dialogue David Bovill / Claude Code)"
VOICES = json.load(open(os.path.join(RV, "voices.json"))); VOICES.pop("_comment", None)
NATIVE = {v["native_for"]: (name, v) for name, v in VOICES.items() if isinstance(v, dict) and v.get("native")}
BY_PREFIX = {C.prefix(cid): cid for cid in C.CONS}
FILE_TAG = lambda lang: lang  # the manifest language is the file tag (D2)
OFFICIAL_TERMS = {"de": "gesetze-im-internet.de, Grundgesetz; official work free of copyright (§5 UrhG)",
                  "fr": "Conseil constitutionnel, Constitution du 4 octobre 1958; official text",
                  "pt-BR": "Planalto, Constituição de 1988; official act of the Brazilian state",
                  "pt-PT": "Assembleia da República, Constituição da República Portuguesa; official text",
                  "it": "Wikisource (it), Costituzione della Repubblica Italiana; official act not copyright protected (art. 5 l. 633/1941)",
                  "de-CH": "Fedlex, Bundesverfassung, Stand 3. März 2024; not copyright protected (Art. 5 URG)",
                  "fr-CH": "Fedlex, Constitution fédérale; not copyright protected (Art. 5 URG)",
                  "it-CH": "Fedlex, Costituzione federale; not copyright protected (Art. 5 URG)"}


def native_text(cid, lang, frags, chosen_fid, en_words=60):
    """The fragment's text in the language of enactment: exact fid, then the article, then another
    fragment of the house, then Article 1, then the preamble. Returns (fid, heading, text, how)."""
    us = C.attach_languages(C.units_for(cid), cid)
    by = {u["fid"]: u for u in us}
    key = f"text_{lang}"
    def art_of(fid):
        head, tail = fid.split(":", 1)
        return f"{head}:{tail.rsplit('.', 1)[0]}" if re.search(r"\.(\d+|r)$", tail) else fid
    order = [(chosen_fid, "exact"), (art_of(chosen_fid), "article")]
    order += [(f["id"], "other fragment") for f in frags if f["id"] != chosen_fid] + [(art_of(f["id"]), "other article") for f in frags]
    order += [(f"{C.prefix(cid)}:1", "article 1"), (f"{C.prefix(cid)}:p", "preamble")]
    cap = max(160, 2 * en_words); last = None
    for fid, how in order:
        u = by.get(fid)
        if u and u.get(key):
            words = len(u[key].split())
            if words < 15 or words > cap:
                last = last or (fid, u["heading"].split(" / ")[-1], u[key], how + " (only text)", words); continue
            return fid, u["heading"].split(" / ")[-1], u[key], how, words
    return last


def render_native(voice_name, v, text, master):
    if v["engine"] == "kokoro":
        from kokoro_onnx import Kokoro
        global _K
        if "_K" not in globals(): _K = Kokoro(B.MODEL, os.path.join(RV, "models", "voices-v1.0.bin"))
        import soundfile as sf
        kl = {"zh": "cmn", "fr": "fr-fr", "pt-br": "pt-br"}.get(v.get("lang", "en-us").lower(), v.get("lang", "en-us").lower())
        s, sr = _K.create(text, voice=v["voice"], speed=1.0, lang=kl)
        sf.write(master, s, sr); return dict(model="kokoro-v1.0.onnx", model_version="1.0", model_sha256=B.model_hash(), pipeline=f"kokoro 24k -> {B.LOUD} closed loop -> libopus 48k 64kbps / aac 96k", machine="laptop M2 8GB")
    if v["engine"] == "piper":
        host, venv, models = v["host"], v["venv"], v["models"]
        remote = f"/tmp/native-{os.getpid()}.wav"
        r = subprocess.run(["ssh", host, f"{venv}/bin/piper -m {models}/{v['voice']}.onnx -f {remote} >/dev/null 2>&1 && cat {remote} && rm -f {remote}"], input=text.encode(), capture_output=True)
        if r.returncode or len(r.stdout) < 1000: raise RuntimeError(f"remote piper failed: {r.stderr.decode()[-300:]}")
        open(master, "wb").write(r.stdout)
        return dict(model=f"{v['voice']}.onnx", model_version="piper-1.8", model_sha256="sha256:" + ("0" * 64), pipeline=f"piper 22k on {host} -> {B.LOUD} closed loop -> libopus 48k 64kbps / aac 96k", machine=f"{host} M1 8GB")
    raise RuntimeError("engine " + v["engine"])


def multilingual_section(page):
    st = page["story"]
    i = fw.find_heading(st, "Multilingual")
    if i is not None: return i
    at = fw.find_heading(st, "Assets")
    if at is None: at = fw.find_heading(st, "See")
    if at is None: at = len(st)
    intro = fw.make_item("The same text in the language it was enacted in, from the [[Parallel Corpus]] (Constitute's own edition aligned by section id, or the official original); files carry the language tag before the extension per [[Multilingual File Names]]; the voice is the [[Voice Lab]]'s provisional choice for the language, under the [[Multilingual City Plan]].")
    head = fw.make_item("# Multilingual")
    prev = st[at - 1]["id"] if at > 0 else None
    for it in (head, intro):
        st.insert(at, it); fw.add_journal(page, "add", it, after=prev, provenance=PROV); prev = it["id"]; at += 1
    return fw.find_heading(st, "Multilingual")


def write_page(h, url, fid, heading, lang, voice_name, v, loud, dur, how, dry):
    page, st = h["page"], h["page"]["story"]
    i = multilingual_section(page)
    engine = "Kokoro" if v["engine"] == "kokoro" else "Piper"
    caption = f"{h['page']['title']} — {heading}, in {lang}, read by a synthetic voice ({voice_name}, {engine}). Fragment {fid}, {dur:.0f} seconds, {loud['integrated_lufs']} LUFS."
    audio = fw.make_item(f"{url}.m4a\n{caption}", "audio", unwrap=False)
    prov = fw.make_item(f"Native reading, {lang}: transcript [text]({url}.txt) · [WebVTT]({url}.vtt) · provenance [wiki-city-media.json]({url.rsplit('/', 1)[0]}/wiki-city-media.json). "
                        f"The text is {'the same fragment as the English reading' if how == 'exact' else 'the ' + how + ' of the house, the English fragment having no aligned text'}; the voice is provisional until a native listener has rated it ([Voice Lab](https://lab.voice.geek.fish/view/voice-lab)).")
    old = [it for it in st if it.get("type") == "audio" and f".{lang}.m4a" in it.get("text", "")]
    if old:
        it = old[0]; it["text"] = audio["text"]; fw.add_journal(page, "edit", it, provenance=PROV)
        j = st.index(it) + 1
        if j < len(st) and st[j].get("text", "").startswith("Native reading"):
            st[j]["text"] = prov["text"]; fw.add_journal(page, "edit", st[j], provenance=PROV)
    else:
        # after the section's intro line, before any existing fragment items
        at = i + 2 if i + 1 < len(st) and not st[i + 1].get("text", "").startswith("#") else i + 1
        prev = st[at - 1]["id"]
        for it in (audio, prov):
            st.insert(at, it); fw.add_journal(page, "add", it, after=prev, provenance=PROV); prev = it["id"]; at += 1
    if not dry: fw.save_page(h["path"], page)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only"); ap.add_argument("--lang"); ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--no-write-page", action="store_true"); ap.add_argument("--limit", type=int)
    a = ap.parse_args()
    cands = json.load(open(os.path.join(HERE, "native-candidates.json")))
    if a.only: cands = [c for c in cands if c["slug"] == a.only]
    if a.lang: cands = [c for c in cands if c["language"] == a.lang]
    if a.limit: cands = cands[:a.limit]
    print(f"native      {len(cands)} candidate houses; palette {sorted(NATIVE)}")
    log, skipped, t0 = [], [], time.time()
    for c in cands:
        slug = c["slug"]; h = B.house(slug); rec = h["rec"]; cid = BY_PREFIX.get(rec.get("constitution"))
        lang = rec.get("language", "").strip()
        if lang == "de" and "de-CH" in c["langs"]: lang = "de-CH"   # Switzerland: the Fedlex German text
        src_lang = lang if f"text_{lang}" else lang
        base = lang.split("-")[0]
        palette_key = lang if lang in NATIVE else (base if base in NATIVE else next((k for k in NATIVE if k.split("-")[0] == base), None))
        if palette_key not in NATIVE: skipped.append((slug, f"no palette voice for {lang}")); print(f"skip        {slug}: no palette voice for {lang}"); continue
        voice_name, v = NATIVE[palette_key]
        mp = os.path.join(B.FARM, "assets", "pages", slug, "hear", "wiki-city-media.json"); m = json.load(open(mp))
        en = next((x for x in m["assets"] if x["role"] == "verbatim_fragment" and x["language"].startswith("en")), m["assets"][0])
        nt = native_text(cid, lang, h["frags"], en["source_text"]["fragment_id"], en["source_text"].get("words", 60))
        if not nt: skipped.append((slug, f"no {lang} text")); print(f"skip        {slug}: no {lang} text"); continue
        fid, heading, text, how, words = nt
        tag = FILE_TAG(lang); stemname = fid.replace(":", "-").replace("/", "-") + "." + tag
        adir = os.path.dirname(mp); stem = os.path.join(adir, stemname); url = f"{B.BASE}/{slug}/hear/{stemname}"
        if a.dry_run: print(f"dry         {slug:<44} {lang:<6} {voice_name:<12} {how:<14} {fid} ({words} w)"); continue
        t1 = time.time()
        try: prov = render_native(voice_name, v, text, stem + ".wav")
        except Exception as e: skipped.append((slug, str(e)[:120])); print(f"FAIL        {slug}: {e}"); continue
        loud, dur = B.deliver(stem + ".wav", stem)
        open(stem + ".txt", "w").write(text + "\n"); open(stem + ".vtt", "w").write(B.vtt(text, dur))
        rights = dict(en["rights"]); rights["attribution"] = (OFFICIAL_TERMS[lang] if lang in OFFICIAL_TERMS else f"Constitute Project (constituteproject.org), {'Spanish' if lang == 'es' else 'Arabic'} edition") + "; original-language text of the constitution"
        if lang in OFFICIAL_TERMS: rights["source_licence"] = "official text (see attribution)"; rights["source_rights_class"] = "public_domain"
        rights["voice_licence"] = B.VOICE_LICENCE if v["engine"] == "kokoro" else f"Piper voice {v['voice']} (rhasspy/piper-voices, per-voice licence)"
        asset = {
            "asset_id": f"voice:{fid}:{tag}:v1", "media_type": "audio", "role": "verbatim_fragment", "language": lang,
            "title": f"{heading}, in {lang}, read by a synthetic voice",
            "delivery": [{"uri": f"{stemname}.opus", "mime": "audio/ogg; codecs=opus", "sha256": B.shaf(stem + ".opus"), "bytes": os.path.getsize(stem + ".opus")},
                         {"uri": f"{stemname}.m4a", "mime": "audio/mp4", "sha256": B.shaf(stem + ".m4a"), "bytes": os.path.getsize(stem + ".m4a")}],
            "master": {"uri": f"{stemname}.wav", "sha256": B.shaf(stem + ".wav")},
            "duration_seconds": round(dur, 2), "loudness": loud,
            "transcript_uri": f"{stemname}.vtt", "transcript_text_uri": f"{stemname}.txt",
            "source_text": {"kind": "verbatim", "text_uri": f"{stemname}.txt", "fragment_id": fid, "heading": heading, "words": words,
                            "input_revision": B.sha(text.encode()), "review_status": "machine_selected"},
            "provenance": {"kind": "synthetic_voice", "generator": "radio-voice/hear/build_native.py", "model": prov["model"], "model_version": prov["model_version"], "model_sha256": prov["model_sha256"],
                           "voice_id": voice_name, "voice_registry": "radio-voice/voices.json", "pipeline": prov["pipeline"], "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
            "rights": rights, "spatial": dict(en["spatial"]), "playback": dict(en["playback"]),
        }
        m["assets"] = [x for x in m["assets"] if x.get("language") != lang] + [asset]
        m["schema_version"] = "0.2.0"
        json.dump(m, open(mp, "w"), indent=1, ensure_ascii=False)
        r = validate_file(mp, "wiki-city-media", files=adir)
        if not r["ok"]:
            print(f"INVALID     {slug}: {r['errors']}", flush=True); skipped.append((slug, "invalid manifest")); continue
        if not a.no_write_page: write_page(h, url, fid, heading, lang, voice_name, v, loud, dur, how, a.dry_run)
        log.append(dict(slug=slug, language=lang, voice=voice_name, fragment_id=fid, how=how, words=words, seconds=round(dur, 1), loudness=loud, audio=url + ".m4a", opus=url + ".opus"))
        print(f"voiced      {slug:<44} {lang:<6} {voice_name:<12} {dur:5.1f}s {loud['integrated_lufs']:6.2f} LUFS {how:<14} {fid} ({time.time()-t1:.1f}s)", flush=True)
    json.dump(dict(built=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), houses=log, skipped=skipped), open(os.path.join(HERE, "native-media.json"), "w"), indent=1, ensure_ascii=False)
    if log and not a.dry_run and not a.no_write_page: print("indexes    ", fw.delete_indexes(B.FARM))
    print(f"done        {len(log)} native voices in {time.time()-t0:.0f}s; skipped {len(skipped)} {skipped[:6]}")


if __name__ == "__main__":
    main()
