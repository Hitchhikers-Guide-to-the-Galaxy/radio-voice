#!/usr/bin/env python3
"""validate.py — validate Wiki City media manifests and soundscape policies.

Structural checks come from the JSON Schemas in schema/.  Semantic checks are
the ones a schema cannot express and the ones the Hear Crowds Plan names:
  M01 unknown rights            source_licence is 'unknown' or empty
  M02 attribution missing       public_render with no attribution
  M03 transcript missing        an audio asset without a .vtt transcript
  M04 bad target                canonical_uri does not name the wiki_city_id page
  M05 anthem                    song lyrics never air (heading or fragment id says anthem/hymn)
  M06 delivery unreadable       (with --files DIR) a delivery uri is absent or its sha256 differs
  M07 loudness off target       integrated loudness not within 1 LU of -16, true peak above -1.5
  M08 dwell below fade          policy: min_dwell_ms < crossfade_ms (voices would flicker)
  M09 weights do not sum to 1   policy: selection weights
  M10 intelligible > active     policy: max_intelligible_speech > max_active_emitters
  M11 language tag mismatch     a delivery/transcript file name's language tag (Multilingual File
                                Names: {fid}.{lang}.{ext}, bare = English) disagrees with the asset's language

Diagnostics are machine-readable: one JSON object per file on stdout with
{"file", "kind", "ok", "errors": [{"code", "path", "message"}]}.  Exit 1 if any
file fails.

  validate.py manifest.json [more.json ...] [--files DIR] [--json]
  validate.py --policy soundscape-policy.json
  validate.py --self-test            # runs the fixtures: valid must pass, invalid must fail
"""
import argparse, hashlib, json, os, re, sys
import jsonschema

HERE = os.path.dirname(os.path.abspath(__file__))
SCHEMAS = {k: json.load(open(os.path.join(HERE, "schema", f"{k}.schema.json")))
           for k in ("wiki-city-media", "soundscape-policy")}
ANTHEM = re.compile(r"anthem|hymn", re.I)
# Multilingual File Names: the dotted segment before the extension, when it parses as a BCP-47 tag
FILE_TAG = re.compile(r"(?:\.(?P<lang>[a-z]{2,3}(?:-[A-Z][a-z]{3})?(?:-[A-Z]{2})?))?\.(?P<ext>wav|opus|m4a|mp3|txt|vtt)$")


def tag_matches(uri, language):
    """A bare name is English; a tagged name must be the asset's language or a prefix of it (es ~ es-GT)."""
    m = FILE_TAG.search(uri or "")
    if not m: return True
    tag = m.group("lang")
    if tag is None: return (language or "").split("-")[0] == "en"
    return language == tag or (language or "").startswith(tag + "-")


def structural(doc, kind):
    v = jsonschema.Draft202012Validator(SCHEMAS[kind], format_checker=jsonschema.FormatChecker())
    return [dict(code="S00", path="/" + "/".join(str(p) for p in e.absolute_path), message=e.message)
            for e in sorted(v.iter_errors(doc), key=lambda e: list(e.absolute_path))]


def semantic_manifest(doc, files=None):
    errs = []
    st = doc.get("semantic_target", {})
    m = re.match(r"^page:([^/]+)/(.+)$", st.get("wiki_city_id", ""))
    if m:
        want = f"https://{m.group(1)}/{m.group(2)}.json"
        if st.get("canonical_uri") != want:
            errs.append(dict(code="M04", path="/semantic_target/canonical_uri",
                             message=f"bad target: expected {want}"))
    for i, a in enumerate(doc.get("assets", [])):
        p = f"/assets/{i}"
        r = a.get("rights", {})
        lic = (r.get("source_licence") or "").strip().lower()
        if lic in ("", "unknown", "?"):
            errs.append(dict(code="M01", path=p + "/rights/source_licence", message="unknown rights"))
        if r.get("public_render") and not (r.get("attribution") or "").strip():
            errs.append(dict(code="M02", path=p + "/rights/attribution", message="public render without attribution"))
        if a.get("media_type") == "audio" and not (a.get("transcript_uri") or "").endswith(".vtt"):
            errs.append(dict(code="M03", path=p + "/transcript_uri", message="audio without a WebVTT transcript"))
        stx = a.get("source_text", {})
        if ANTHEM.search(stx.get("heading", "") or "") or ANTHEM.search(stx.get("fragment_id", "") or ""):
            errs.append(dict(code="M05", path=p + "/source_text", message="anthem: song lyrics never air"))
        for j, d in enumerate(a.get("delivery", [])):
            if not tag_matches(d.get("uri"), a.get("language")):
                errs.append(dict(code="M11", path=f"{p}/delivery/{j}/uri",
                                 message=f"file tag of {d.get('uri')} disagrees with language {a.get('language')}"))
        for key in ("transcript_uri", "transcript_text_uri"):
            if a.get(key) and not tag_matches(a[key], a.get("language")):
                errs.append(dict(code="M11", path=f"{p}/{key}", message=f"file tag of {a[key]} disagrees with language {a.get('language')}"))
        lo = a.get("loudness")
        if lo:
            if abs(lo.get("integrated_lufs", -16) + 16) > 1.0:
                errs.append(dict(code="M07", path=p + "/loudness/integrated_lufs",
                                 message=f"integrated {lo['integrated_lufs']} LUFS, target -16 ±1"))
            if lo.get("true_peak_dbtp", -99) > -1.5 + 0.1:
                errs.append(dict(code="M07", path=p + "/loudness/true_peak_dbtp",
                                 message=f"true peak {lo['true_peak_dbtp']} dBTP above -1.5"))
        if files:
            for j, d in enumerate(a.get("delivery", [])):
                fp = os.path.join(files, d["uri"])
                if not os.path.exists(fp):
                    errs.append(dict(code="M06", path=f"{p}/delivery/{j}/uri", message=f"missing file {d['uri']}"))
                    continue
                h = "sha256:" + hashlib.sha256(open(fp, "rb").read()).hexdigest()
                if h != d.get("sha256"):
                    errs.append(dict(code="M06", path=f"{p}/delivery/{j}/sha256", message="sha256 differs from file"))
            for key in ("transcript_uri", "transcript_text_uri"):
                if a.get(key) and not os.path.exists(os.path.join(files, a[key])):
                    errs.append(dict(code="M06", path=f"{p}/{key}", message=f"missing file {a[key]}"))
    return errs


def semantic_policy(doc):
    errs = []
    h = doc.get("hysteresis", {})
    if h.get("min_dwell_ms", 0) < doc.get("crossfade_ms", 0):
        errs.append(dict(code="M08", path="/hysteresis/min_dwell_ms", message="dwell shorter than the crossfade: voices would flicker"))
    w = doc.get("selection_weights", {})
    if w and abs(sum(w.values()) - 1.0) > 1e-6:
        errs.append(dict(code="M09", path="/selection_weights", message=f"weights sum to {sum(w.values()):.3f}, not 1"))
    if doc.get("max_intelligible_speech", 0) > doc.get("max_active_emitters", 0):
        errs.append(dict(code="M10", path="/max_intelligible_speech", message="more intelligible voices than active emitters"))
    return errs


def validate_file(path, kind, files=None):
    try:
        doc = json.load(open(path))
    except Exception as e:
        return dict(file=path, kind=kind, ok=False, errors=[dict(code="S00", path="/", message=f"not JSON: {e}")])
    errs = structural(doc, kind)
    errs += semantic_manifest(doc, files) if kind == "wiki-city-media" else semantic_policy(doc)
    return dict(file=path, kind=kind, ok=not errs, errors=errs)


def self_test():
    ok = True
    fx = os.path.join(HERE, "fixtures")
    for name in sorted(os.listdir(os.path.join(fx, "valid"))):
        kind = "soundscape-policy" if "policy" in name else "wiki-city-media"
        r = validate_file(os.path.join(fx, "valid", name), kind)
        print(f"{'PASS' if r['ok'] else 'FAIL'}  valid/{name}  {[e['code'] for e in r['errors']]}")
        ok &= r["ok"]
    for name in sorted(os.listdir(os.path.join(fx, "invalid"))):
        kind = "soundscape-policy" if "policy" in name else "wiki-city-media"
        r = validate_file(os.path.join(fx, "invalid", name), kind)
        want = name.split(".")[0].split("_")[-1].upper()          # e.g. missing-transcript_M03.json
        codes = {e["code"] for e in r["errors"]}
        hit = (not r["ok"]) and (want in codes)
        print(f"{'PASS' if hit else 'FAIL'}  invalid/{name}  rejected with {sorted(codes)} (wanted {want})")
        ok &= hit
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--policy", action="store_true", help="the files are soundscape policies")
    ap.add_argument("--files", help="directory the delivery uris are relative to; checks presence and sha256")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        sys.exit(0 if self_test() else 1)
    if not a.paths:
        ap.error("give manifest files, --policy files, or --self-test")
    kind = "soundscape-policy" if a.policy else "wiki-city-media"
    results = [validate_file(p, kind, a.files) for p in a.paths]
    for r in results:
        if a.json:
            print(json.dumps(r))
        else:
            print(f"{'ok  ' if r['ok'] else 'FAIL'} {r['file']}")
            for e in r["errors"]:
                print(f"      {e['code']} {e['path']}: {e['message']}")
    sys.exit(0 if all(r["ok"] for r in results) else 1)


if __name__ == "__main__":
    main()
