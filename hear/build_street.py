#!/usr/bin/env python3
"""build_street.py — give every house on the street a voice.

For each constitution page on the street (the cross-site neighbours of the
square in map.json) this renders its first speakable For Speaking fragment
through one held Kokoro instance, normalises it to I=-16 LUFS / TP=-1.5 dBTP
/ LRA=11, delivers Opus 48 kHz with an m4a fallback, writes a WebVTT and a
plain transcript, and writes the provenance record as a wiki-city-media.json
manifest that validate.py accepts.  Everything lands farm-direct in the
constitution site's existing per-page assets folder (assets/pages/<slug>/,
the convention that site's importer set) under hear/, and a native audio item
plus a provenance line are inserted under # For Speaking on the page,
journaled with provenance.  Fork entries are never touched.

  build_street.py --map MAP.json [--only SLUG] [--dry-run] [--no-write-page] [--also SLUG ...]
"""
import argparse, hashlib, json, os, re, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
RV = os.path.dirname(HERE)
sys.path.insert(0, os.path.expanduser("~/.claude/skills/fedwiki-lib"))
sys.path.insert(0, HERE)
import fedwiki as fw
from validate import validate_file

SITE = "constitution.legalcommons.org"
FARM = os.path.expanduser(f"~/Nextcloud/fedwiki/{SITE}")
BASE = f"https://{SITE}/assets/pages"
PROV = "Hear Crowds Plan Phase 2 — build_street.py (dialogue David Bovill / Claude Code)"
LOUD = "I=-16:TP=-1.5:LRA=11"
MODEL = os.path.join(RV, "models", "kokoro-v1.0.onnx")
VOICES = json.load(open(os.path.join(RV, "voices.json"))); VOICES.pop("_comment", None)
# a fixed palette so a house keeps its voice between builds; heart kept where a cue already used it
PALETTE = ["michael", "emma", "george", "bella", "lewis", "sarah", "adam", "isabella",
           "fenrir", "alice", "onyx", "lily", "nicole", "daniel-k", "fable", "heart"]
KEEP_VOICE = {"bolivia-plurinational-state-of-2009": "heart", "nicaragua-1987-rev-2014": "heart",
              "ecuador-2008-rev-2021": "michael"}
ANTHEM = re.compile(r"anthem|hymn", re.I)
FRAG = re.compile(r"`([^`]+)`\s*[—-]\s*(.*?)\n\n>\s*(.*)", re.S)
LICENCE = "CC-BY-NC-3.0 (Constitute Project)"
VOICE_LICENCE = "Apache-2.0 (Kokoro-82M, hexgrad)"


def sha(b): return "sha256:" + hashlib.sha256(b).hexdigest()
def shaf(p): return sha(open(p, "rb").read())


def model_hash():
    c = os.path.join(HERE, ".model_sha256")
    if not os.path.exists(c):
        open(c, "w").write(shaf(MODEL))
    return open(c).read().strip()


def sh(cmd, capture=False):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"{cmd[0]} failed: {r.stderr[-600:]}")
    return r.stderr if capture else None


def house(slug):
    path = os.path.join(FARM, "pages", slug)
    page = fw.load_page(path)
    st = page["story"]
    rec = dict(re.findall(r"^([a-z_]+):\s*(.+)$", next(it["text"] for it in st if it["type"] == "code"), re.M))
    i = next((k for k, it in enumerate(st) if it.get("text", "").strip() == "# For Speaking"), None)
    frags = []
    if i is not None:
        for it in st[i + 1:]:
            t = it.get("text", "")
            if t.startswith("# "):
                break
            m = FRAG.match(t)
            if m:
                text = " ".join(l.lstrip("> ").strip() for l in m.group(3).split("\n")).strip()
                frags.append(dict(id=m.group(1), heading=m.group(2).strip(), text=text, item=it["id"], words=len(text.split())))
    return dict(slug=slug, path=path, page=page, rec=rec, fs_index=i, frags=frags, page_sha=shaf(path))


def choose(frags):
    ok = [f for f in frags if not ANTHEM.search(f["heading"]) and not ANTHEM.search(f["id"])]
    short = [f for f in ok if f["words"] <= 110]
    return (short or sorted(ok, key=lambda f: f["words"]) or [None])[0]


def rights_of(rec):
    cls = rec.get("rights", "open")
    parts = ["Constitute Project (constituteproject.org)"]
    if rec.get("copyright") and rec["copyright"] != "-":
        parts.append(rec["copyright"].strip())
    if rec.get("translator") and rec["translator"] != "-":
        parts.append(f"translated by {rec['translator'].strip()}")
    return dict(source_licence=LICENCE, source_rights_class=cls, voice_licence=VOICE_LICENCE,
                consent_record_uri=None, public_render=True, attribution="; ".join(parts))


def vtt(text, seconds):
    """Proportional cue timing by sentence — the reading is one take, so
    sentences are placed by their share of the characters."""
    sents = [s.strip() for s in re.split(r"(?<=[.;:!?])\s+", text) if s.strip()]
    total = sum(len(s) for s in sents) or 1
    out, t = ["WEBVTT", ""], 0.0
    for n, s in enumerate(sents, 1):
        d = seconds * len(s) / total
        f = lambda x: f"{int(x//3600):02d}:{int(x%3600//60):02d}:{x%60:06.3f}"
        out += [str(n), f"{f(t)} --> {f(t+d)}", s, ""]
        t += d
    return "\n".join(out)


def measure(path):
    err = sh(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-af", f"loudnorm={LOUD}:print_format=json", "-f", "null", "-"], capture=True)
    return json.loads(err[err.rfind("{"):err.rfind("}") + 1])


def render(k, voice, text, master):
    import soundfile as sf
    v = VOICES[voice]
    s, sr = k.create(text, voice=v["voice"], speed=1.0, lang=v.get("lang", "en-us"))
    sf.write(master, s, sr)
    return len(s) / sr


def deliver(master, stem):
    """Closed loop on the deliverable: gentle compression, gain, a limiter, then
    encode and MEASURE THE ENCODED CLIP, correcting the gain until the Opus
    itself reads -16 LUFS integrated.  Open-loop loudnorm cannot do this on a
    short peaky synthetic voice: its peak ceiling wins and the clip lands a
    decibel low, and the codecs shave another half."""
    pre = stem + ".pre.wav"
    sh(["ffmpeg", "-y", "-loglevel", "error", "-i", master, "-af",
        "acompressor=threshold=-22dB:ratio=3:attack=8:release=150:makeup=0dB", "-ar", "48000", pre])
    gain = -16.0 - float(measure(pre)["input_i"])
    limit = 0.596                                   # -4.5 dBFS sample ceiling before the codecs
    norm = stem + ".norm.wav"
    got = None
    for it in range(6):
        sh(["ffmpeg", "-y", "-loglevel", "error", "-i", pre, "-af",
            f"volume={gain:.2f}dB,alimiter=limit={limit:.3f}:attack=3:release=80:level=false", norm])
        sh(["ffmpeg", "-y", "-loglevel", "error", "-i", norm, "-c:a", "libopus", "-b:a", "64k", "-ac", "1", stem + ".opus"])
        sh(["ffmpeg", "-y", "-loglevel", "error", "-i", norm, "-c:a", "aac", "-b:a", "96k", "-ac", "1", stem + ".m4a"])
        got = measure(stem + ".opus"); m4 = measure(stem + ".m4a")
        I = float(got["input_i"]); TP = max(float(got["input_tp"]), float(m4["input_tp"]))
        if os.environ.get("HEAR_VERBOSE"):
            print(f"   loop {it}: gain {gain:+.2f} dB limit {limit:.3f} -> I {I:.2f} LUFS TP {TP:.2f} dBTP")
        if abs(I + 16.0) < 0.3 and TP <= -1.5:
            break
        if TP > -1.5:
            limit *= 10 ** ((-1.5 - TP - 0.4) / 20)     # lower the ceiling by the overshoot plus margin
        if abs(I + 16.0) >= 0.3:
            gain += -16.0 - I
    os.remove(pre); os.remove(norm)
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", stem + ".opus"],
                               capture_output=True, text=True).stdout.strip())
    return dict(integrated_lufs=round(float(got["input_i"]), 2),
                true_peak_dbtp=round(max(float(got["input_tp"]), float(m4["input_tp"])), 2),
                lra=round(float(got["input_lra"]), 2), target=LOUD), dur


def write_page(h, url, frag, voice, loud, dur, dry):
    page, st = h["page"], h["page"]["story"]
    i = h["fs_index"]
    caption = (f"{h['page']['title']} — {frag['heading']}, read by a synthetic voice ({voice}, Kokoro). "
               f"Fragment {frag['id']}, {dur:.0f} seconds, {loud['integrated_lufs']} LUFS.")
    audio = fw.make_item(f"{url}.m4a\n{caption}", "audio", unwrap=False)
    prov = fw.make_item(
        f"Transcript: [text]({url}.txt) · [WebVTT]({url}.vtt) · Provenance: [wiki-city-media.json]({url.rsplit('/',1)[0]}/wiki-city-media.json). "
        f"A verbatim fragment, unedited; the voice is synthetic and says so. Part of the Hear Crowds Plan on "
        f"[atlas.anarchive.earth](https://atlas.anarchive.earth/view/hear-crowds-plan).")
    old = [it for it in st if it.get("type") == "audio" and "/hear/" in it.get("text", "")]
    if old:
        it = old[0]; it["text"] = audio["text"]; fw.add_journal(page, "edit", it, provenance=PROV)
        j = st.index(it) + 1
        if j < len(st) and st[j].get("text", "").startswith("Transcript: ["):
            st[j]["text"] = prov["text"]; fw.add_journal(page, "edit", st[j], provenance=PROV)
    else:
        at = i + 2 if i is not None else len(st)      # after the For Speaking intro line
        prev = st[at - 1]["id"]
        for it in (audio, prov):
            st.insert(at, it); fw.add_journal(page, "add", it, after=prev, provenance=PROV); prev = it["id"]; at += 1
    fw.ensure_assets(page, f"pages/{h['slug']}", journal=True)
    if not dry:
        fw.save_page(h["path"], page)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--map", required=True)
    ap.add_argument("--only")
    ap.add_argument("--also", nargs="*", default=[], help="extra constitution slugs (not on the street)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-write-page", action="store_true")
    ap.add_argument("--edition", default=None)
    a = ap.parse_args()
    m = json.load(open(a.map))
    edition = a.edition or f"{m['name']}-pages-epoch-{m['epoch']}"
    slugs = [h.split("/", 1)[1] for h in m["street"]["houses"] if h.startswith(SITE + "/")] + list(a.also)
    if a.only:
        slugs = [a.only]
    print(f"street      {m['street']['square']} — {len(slugs)} houses to voice; edition {edition}")
    from kokoro_onnx import Kokoro
    k = Kokoro(MODEL, os.path.join(RV, "models", "voices-v1.0.bin"))
    mh = model_hash()
    index = []
    t0 = time.time()
    for n, slug in enumerate(sorted(slugs)):
        h = house(slug)
        frag = choose(h["frags"])
        if not frag:
            print(f"skip        {slug}: no speakable fragment"); continue
        voice = KEEP_VOICE.get(slug, PALETTE[n % len(PALETTE)])
        stemname = frag["id"].replace(":", "-").replace("/", "-")
        adir = os.path.join(FARM, "assets", "pages", slug, "hear")
        os.makedirs(adir, exist_ok=True)
        stem = os.path.join(adir, stemname)
        url = f"{BASE}/{slug}/hear/{stemname}"
        t1 = time.time()
        render(k, voice, frag["text"], stem + ".wav")
        loud, dur = deliver(stem + ".wav", stem)
        open(stem + ".txt", "w").write(frag["text"] + "\n")
        open(stem + ".vtt", "w").write(vtt(frag["text"], dur))
        manifest = {
            "schema_version": "0.1.0",
            "manifest_id": f"media:{SITE}/{slug}:{time.strftime('%Y-%m-%d')}",
            "map_edition_id": edition,
            "semantic_target": {"wiki_city_id": f"page:{SITE}/{slug}", "entity_type": "page_house",
                                "canonical_uri": f"https://{SITE}/{slug}.json", "title": h["page"]["title"],
                                "source_revision": h["page_sha"], "access_policy_uri": "policy:public"},
            "assets": [{
                "asset_id": f"voice:{frag['id']}:v1",
                "media_type": "audio", "role": "verbatim_fragment",
                "language": "en-GB" if VOICES[voice].get("lang") == "en-gb" else "en-US",
                "title": f"{frag['heading']}, read by a synthetic voice",
                "delivery": [{"uri": f"{stemname}.opus", "mime": "audio/ogg; codecs=opus", "sha256": shaf(stem + ".opus"), "bytes": os.path.getsize(stem + ".opus")},
                             {"uri": f"{stemname}.m4a", "mime": "audio/mp4", "sha256": shaf(stem + ".m4a"), "bytes": os.path.getsize(stem + ".m4a")}],
                "master": {"uri": f"{stemname}.wav", "sha256": shaf(stem + ".wav")},
                "duration_seconds": round(dur, 2),
                "loudness": loud,
                "transcript_uri": f"{stemname}.vtt", "transcript_text_uri": f"{stemname}.txt",
                "source_text": {"kind": "verbatim", "text_uri": f"{stemname}.txt", "fragment_id": frag["id"],
                                "heading": frag["heading"], "words": frag["words"],
                                "input_revision": sha(frag["text"].encode()), "review_status": "machine_selected"},
                "provenance": {"kind": "synthetic_voice", "generator": "radio-voice/hear/build_street.py",
                               "model": "kokoro-v1.0.onnx", "model_version": "1.0", "model_sha256": mh,
                               "voice_id": voice, "voice_registry": "radio-voice/voices.json",
                               "pipeline": f"kokoro 24k -> loudnorm {LOUD} two-pass linear -> libopus 48k 48kbps / aac 96k; VTT timing proportional by sentence",
                               "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
                "rights": rights_of(h["rec"]),
                "spatial": {"anchor": "threshold", "distance_model": "inverse", "ref_distance": 4.0, "max_distance": 45.0,
                            "rolloff_factor": 1.2, "cone_inner_angle": 180, "cone_outer_angle": 270, "cone_outer_gain": 0.2,
                            "occlusion": True, "reverb_zone": "small_room"},
                "playback": {"trigger": "focus_or_threshold", "loop": False, "priority": 70, "bus": "synthetic_speech", "cooldown_seconds": 90}
            }],
            "live_room": {"enabled": False, "room_key": f"page:{SITE}/{slug}", "provider": "livekit", "access_policy_uri": "policy:public",
                          "recording": "off", "transcription": "off", "e2ee": "required_when_enabled", "agent_participation": "disclosed_opt_in"}
        }
        mp = os.path.join(adir, "wiki-city-media.json")
        json.dump(manifest, open(mp, "w"), indent=1)
        r = validate_file(mp, "wiki-city-media", files=adir)
        if not r["ok"]:
            print(f"INVALID     {slug}: {r['errors']}"); sys.exit(1)
        if not a.no_write_page:
            write_page(h, url, frag, voice, loud, dur, a.dry_run)
        index.append(dict(slug=slug, title=h["page"]["title"], fragment_id=frag["id"], heading=frag["heading"], words=frag["words"],
                          voice=voice, seconds=round(dur, 1), loudness=loud, rights=h["rec"].get("rights"),
                          manifest=f"{BASE}/{slug}/hear/wiki-city-media.json", audio=url + ".m4a", opus=url + ".opus"))
        print(f"voiced      {slug:<44} {voice:<9} {dur:5.1f}s  {loud['integrated_lufs']:6.2f} LUFS  {frag['id']}  ({time.time()-t1:.1f}s)")
    json.dump(dict(street=m["street"], edition=edition, built=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), houses=index),
              open(os.path.join(HERE, "street-media.json"), "w"), indent=1)
    if not a.dry_run and not a.no_write_page:
        print("indexes    ", fw.delete_indexes(FARM))
    print(f"done        {len(index)} houses in {time.time()-t0:.0f}s -> {os.path.join(HERE, 'street-media.json')}")


if __name__ == "__main__":
    main()
