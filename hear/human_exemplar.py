#!/usr/bin/env python3
"""human_exemplar.py — the one human reading beside the synthetic ones (D8).

Cuts the Preamble from the LibriVox recording of the United States
Constitution (read by Laurie Anne Walden, public domain), runs it through the
same deliver() as the synthetic voices so it sits at the same loudness, writes
a WebVTT from Whisper word timings against the canonical text, and records it
as role human_reading / kind human_voice with a public-domain rights record.
Lands on the US constitution page exactly as the street houses do.

  human_exemplar.py [--dry-run] [--no-write-page]
"""
import argparse, json, os, re, subprocess, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_street as B
from validate import validate_file
from fedwiki import make_item, add_journal, ensure_assets, save_page, delete_indexes

SLUG = "united-states-of-america-1789-rev-1992"
SRC = os.path.join(HERE, "human", "constitution_01_unitedstates_64kb.mp3")
START, END = 25.30, 47.60                   # Whisper word timings: "We," 25.68 … "America." 46.98
ARCHIVE = "https://archive.org/details/usconstitution_1610_librivox"
READER = "Laurie Anne Walden"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--no-write-page", action="store_true")
    a = ap.parse_args()
    h = B.house(SLUG)
    frag = next(f for f in h["frags"] if f["id"].endswith(":p"))
    stemname = "united-states-of-america-1992-p-human"
    adir = os.path.join(B.FARM, "assets", "pages", SLUG, "hear"); os.makedirs(adir, exist_ok=True)
    stem = os.path.join(adir, stemname); url = f"{B.BASE}/{SLUG}/hear/{stemname}"
    # input-side seek: output-side seeking runs the filters over the whole file
    # first, so a fade-out timed for the clip fires inside the intro instead
    B.sh(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(START), "-to", str(END), "-i", SRC,
          "-af", "afade=t=in:d=0.15,afade=t=out:st=%.2f:d=0.35" % (END - START - 0.35), "-ar", "24000", "-ac", "1", stem + ".wav"])
    loud, dur = B.deliver(stem + ".wav", stem)
    # transcript: canonical words, Whisper timings by sentence share (one take)
    open(stem + ".txt", "w").write(frag["text"] + "\n")
    open(stem + ".vtt", "w").write(B.vtt(frag["text"], dur))
    src_sha = B.shaf(SRC)
    manifest = {
        "schema_version": "0.1.0",
        "manifest_id": f"media:{B.SITE}/{SLUG}:{time.strftime('%Y-%m-%d')}",
        "map_edition_id": "legalcommons-pages-epoch-4",
        "semantic_target": {"wiki_city_id": f"page:{B.SITE}/{SLUG}", "entity_type": "page_house",
                            "canonical_uri": f"https://{B.SITE}/{SLUG}.json", "title": h["page"]["title"],
                            "source_revision": h["page_sha"], "access_policy_uri": "policy:public"},
        "assets": [{
            "asset_id": "human:united-states-of-america-1992:p:v1",
            "media_type": "audio", "role": "human_reading", "language": "en-US",
            "title": "Preamble, read by a human voice",
            "delivery": [{"uri": f"{stemname}.opus", "mime": "audio/ogg; codecs=opus", "sha256": B.shaf(stem + ".opus"), "bytes": os.path.getsize(stem + ".opus")},
                         {"uri": f"{stemname}.m4a", "mime": "audio/mp4", "sha256": B.shaf(stem + ".m4a"), "bytes": os.path.getsize(stem + ".m4a")}],
            "master": {"uri": f"{stemname}.wav", "sha256": B.shaf(stem + ".wav")},
            "duration_seconds": round(dur, 2), "loudness": loud,
            "transcript_uri": f"{stemname}.vtt", "transcript_text_uri": f"{stemname}.txt",
            "source_text": {"kind": "reading", "text_uri": f"{stemname}.txt", "fragment_id": frag["id"], "heading": frag["heading"],
                            "words": frag["words"], "input_revision": B.sha(frag["text"].encode()), "review_status": "human_accepted"},
            "provenance": {"kind": "human_voice", "generator": "radio-voice/hear/human_exemplar.py", "reader": READER,
                           "recording_uri": ARCHIVE + "#constitution_01_unitedstates_64kb.mp3",
                           "pipeline": f"LibriVox mp3 (sha {src_sha[:23]}…) cut {START}-{END}s -> same compressor/gain/limiter loop as the synthetic voices -> libopus 64k / aac 96k",
                           "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
            "rights": {"source_licence": "public domain (US federal text)", "source_rights_class": "public_domain",
                       "voice_licence": "public domain (LibriVox: every recording is released to the public domain)",
                       "consent_record_uri": ARCHIVE, "public_render": True,
                       "attribution": f"Read by {READER} for LibriVox; archive.org usconstitution_1610_librivox"},
            "spatial": {"anchor": "threshold", "distance_model": "inverse", "ref_distance": 4.0, "max_distance": 45.0,
                        "rolloff_factor": 1.2, "cone_inner_angle": 180, "cone_outer_angle": 270, "cone_outer_gain": 0.2,
                        "occlusion": True, "reverb_zone": "small_room"},
            "playback": {"trigger": "focus_or_threshold", "loop": False, "priority": 80, "bus": "human_speech", "cooldown_seconds": 90}
        }],
        "live_room": {"enabled": False}
    }
    mp = os.path.join(adir, "wiki-city-media.json"); json.dump(manifest, open(mp, "w"), indent=1)
    r = validate_file(mp, "wiki-city-media", files=adir)
    if not r["ok"]:
        sys.exit(f"INVALID {r['errors']}")
    print(f"human       {SLUG} {dur:.1f}s {loud['integrated_lufs']} LUFS TP {loud['true_peak_dbtp']}  {frag['id']}")
    if a.no_write_page:
        return
    page, st = h["page"], h["page"]["story"]; i = h["fs_index"]
    caption = (f"{page['title']} — Preamble, read by a human voice: {READER} for LibriVox, public domain. "
               f"Fragment {frag['id']}, {dur:.0f} seconds, {loud['integrated_lufs']} LUFS — the one human reading beside the synthetic ones.")
    audio = make_item(f"{url}.m4a\n{caption}", "audio", unwrap=False)
    prov = make_item(f"Transcript: [text]({url}.txt) · [WebVTT]({url}.vtt) · Provenance: [wiki-city-media.json]({url.rsplit('/',1)[0]}/wiki-city-media.json) · "
                     f"Source recording: [archive.org]({ARCHIVE}). The human exemplar of the Hear Crowds Plan on "
                     f"[atlas.anarchive.earth](https://atlas.anarchive.earth/view/hear-crowds-plan).")
    old = [it for it in st if it.get("type") == "audio" and "/hear/" in it.get("text", "")]
    if old:
        old[0]["text"] = audio["text"]; add_journal(page, "edit", old[0], provenance=B.PROV)
    else:
        at = i + 2; prev = st[at - 1]["id"]
        for it in (audio, prov):
            st.insert(at, it); add_journal(page, "add", it, after=prev, provenance=B.PROV); prev = it["id"]; at += 1
    ensure_assets(page, f"pages/{SLUG}", journal=True)
    if not a.dry_run:
        save_page(h["path"], page); print("page        written;", delete_indexes(B.FARM))


if __name__ == "__main__":
    main()
