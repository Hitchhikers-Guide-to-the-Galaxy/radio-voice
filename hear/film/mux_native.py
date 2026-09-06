#!/usr/bin/env python3
"""mux_native.py — the soundtrack of the multilingual flight, from journey.json's zones and the
native clips Phase 3 put beside the English ones (Multilingual City Plan, Phase 5).

Per zone: solo and pair take the zone's houses in the allowed languages, the two nearest the
camera clear and the next four as a murmur; polyphonic takes one house per language the city
can speak (including English) as clear strands; the descent starts on Bolivia's English and
crosses to its Spanish from the first word, as the plugin does at the threshold.  Two-pass
loudnorm to -16 LUFS; frames assembled; a render receipt.  An interpretation, never a claim
to equal the browser mix (D7).

    mux_native.py --journey JOURNEY.json --media CITY_MEDIA.json --map MAP.json --camera-path PATH.json \
        --policy POLICY.json --frames DIR --fps 12 --out OUT.mp4 [--mix-only] [--blend X.blend] [--measure M.json]
"""
import argparse, hashlib, json, os, subprocess, time, math
ap = argparse.ArgumentParser()
ap.add_argument("--journey", required=True); ap.add_argument("--media", required=True); ap.add_argument("--map", required=True)
ap.add_argument("--camera-path", required=True); ap.add_argument("--policy", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--frames", default=None); ap.add_argument("--fps", type=int, default=12); ap.add_argument("--mix-only", action="store_true")
ap.add_argument("--blend", default=None); ap.add_argument("--measure", default=None)
a = ap.parse_args()
FARM = os.path.expanduser("~/Nextcloud/fedwiki/constitution.legalcommons.org/assets/pages/")
def sha(p): return "sha256:" + hashlib.sha256(open(p, "rb").read()).hexdigest()
J = json.load(open(a.journey)); media = json.load(open(a.media)); m = json.load(open(a.map)); path = json.load(open(a.camera_path))
nodes = {n["slug"]: n for n in m["nodes"] if n["site"].startswith("constitution")}
houses = {h["slug"]: h for h in media["houses"]}
def local(url): return url.replace("https://constitution.legalcommons.org/assets/pages/", FARM).rsplit(".", 1)[0] + ".wav"
def wav_native(h): return local(h["native_audio"]) if h.get("native") else None
def wav_en(h): return local(h["audio"])
def dur_of(p): return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", p], capture_output=True, text=True).stdout.strip() or 0)
def dist(slug, at): n = nodes.get(slug); return math.hypot(n["x"] - at[0], n["y"] - at[1]) if n else 1e9
def base(l): return (l or "en").split("-")[0]

cues = []
def cue(slug, wavp, start, end, gain_db, lowpass=None, pan=0.0, fade_in=1.0, fade_out=1.0, offset=0.0, note="", lang="en"):
    cues.append(dict(slug=slug, wav=wavp, start=round(start, 2), end=round(end, 2), gain_db=gain_db, lowpass_hz=lowpass, pan=pan, fade_in=fade_in, fade_out=fade_out, offset=offset, note=note, language=lang))
t = 0.0
for z in J["zones"]:
    t0, t1 = t, t + z["seconds"]; at = z["at"]
    if z.get("descend"):
        h = houses[z["descend"]]
        cue(h["slug"], wav_en(h), t0, t0 + 9.0, -3, pan=0.0, fade_in=1.5, fade_out=1.0, note="descent: the English reading, as at city scale")
        cue(h["slug"], wav_native(h), t0 + 8.2, t1, 0, pan=0.0, fade_in=0.9, fade_out=2.5, note="descent: the original from its first word at the threshold", lang=h["language"])
        near = sorted((s for s in houses if houses[s].get("native") and base(houses[s]["language"]) == base(h["language"]) and s != h["slug"]), key=lambda s: dist(s, at))[:2]
        for i, s in enumerate(near): cue(s, wav_native(houses[s]), t0, t1, -22, lowpass=1000, pan=(-0.7, 0.7)[i], fade_in=2, fade_out=2, note="descent: the quarter behind", lang=houses[s]["language"])
    elif z["mix"] in ("solo", "pair"):
        pool = [s for s in z["houses"] if s in houses and houses[s].get("native") and wav_native(houses[s]) and os.path.exists(wav_native(houses[s]))]
        pool.sort(key=lambda s: dist(s, at))
        clear, murmur = pool[:2], pool[2:6]
        for i, s in enumerate(clear):
            cue(s, wav_native(houses[s]), t0 + 0.5 + i * 2.5, t1, -3, pan=(-0.35, 0.35)[i], fade_in=1.5, fade_out=1.5, note=f"{z['mix']}: clear", lang=houses[s]["language"])
        for i, s in enumerate(murmur):
            cue(s, wav_native(houses[s]), t0 + 1.0 + i * 0.9, t1, -17, lowpass=1300, pan=-0.8 + i * 0.53, fade_in=2.5, fade_out=2.0, offset=i * 2.7, note=f"{z['mix']}: murmur", lang=houses[s]["language"])
    else:   # polyphonic: one strand per language, nearest the centre, plus English strands and a murmur of the rest
        bylang = {}
        for s, h in sorted(houses.items(), key=lambda kv: dist(kv[0], at)):
            l = base(h["language"]) if h.get("native") else "en"
            w = wav_native(h) if h.get("native") else wav_en(h)
            if l not in bylang and w and os.path.exists(w): bylang[l] = (s, w, h["language"] if h.get("native") else "en")
        strands = list(bylang.items())[:6]
        for i, (l, (s, w, lang)) in enumerate(strands):
            cue(s, w, t0 + 0.5 + i * 1.7, t1, -7, pan=-0.8 + i * (1.6 / max(1, len(strands) - 1)), fade_in=1.5, fade_out=1.5, note=f"polyphonic: {l}", lang=lang)
        extra = [s for s, h in sorted(houses.items(), key=lambda kv: dist(kv[0], at)) if s not in {x[1][0] for x in strands}][:3]
        for i, s in enumerate(extra):
            h = houses[s]; w = wav_native(h) if h.get("native") else wav_en(h)
            if w and os.path.exists(w): cue(s, w, t0 + 2 + i, t1, -20, lowpass=1200, pan=(-0.5, 0.0, 0.5)[i], fade_in=2, fade_out=2, offset=i * 3.0, note="polyphonic: murmur", lang=h["language"] if h.get("native") else "en")
    t = t1
seconds = float(J["total_seconds"])
for c in cues:   # a clip shorter than its window loops within it (the crowd does), a long one is trimmed to the window
    L = dur_of(c["wav"]); win = c["end"] - c["start"]
    c["loops"] = max(1, math.ceil((win + c["offset"]) / L)) if L else 1
sheet = dict(policy_id=json.load(open(a.policy)).get("policy_id"), journey_id=J.get("journey_id"), loudness_target="I=-16:TP=-1.5:LRA=11", zones=[dict(name=z["name"], mix=z["mix"], languages=z["languages"], seconds=z["seconds"]) for z in J["zones"]],
             cues=[{k: v for k, v in c.items() if k != "wav"} for c in cues], authored_by="mux_native.py (Multilingual City Plan Phase 5)",
             note="An interpretation of the flight for the film. The browser mix is chosen live by the soundscape policy and is not reproduced here (D7).")
out_dir = os.path.dirname(os.path.abspath(a.out)); os.makedirs(out_dir, exist_ok=True)
sheet_path = os.path.join(out_dir, "journey-cue-sheet.json"); json.dump(sheet, open(sheet_path, "w"), indent=1, ensure_ascii=False)

inputs, chains, labels = [], [], []
for i, c in enumerate(cues):
    inputs += ["-stream_loop", str(c["loops"] - 1), "-i", c["wav"]]
    win = c["end"] - c["start"]
    f = [f"atrim=start={c['offset']}:end={c['offset'] + win}", "asetpts=PTS-STARTPTS", f"afade=t=in:st=0:d={c['fade_in']}:curve=qsin", f"afade=t=out:st={max(0, win - c['fade_out']):.2f}:d={c['fade_out']}:curve=qsin", f"volume={c['gain_db']}dB"]
    if c["lowpass_hz"]: f.append(f"lowpass=f={c['lowpass_hz']}")
    L = (1 - c["pan"]) / 2 if c["pan"] > 0 else 1.0; R = (1 + c["pan"]) / 2 if c["pan"] < 0 else 1.0
    f += [f"pan=stereo|c0={L:.2f}*c0|c1={R:.2f}*c0", "aresample=48000", f"adelay={int(c['start'] * 1000)}|{int(c['start'] * 1000)}"]
    chains.append(f"[{i}:a]" + ",".join(f) + f"[c{i}]"); labels.append(f"[c{i}]")
graph = ";".join(chains) + f";{''.join(labels)}amix=inputs={len(labels)}:normalize=0:dropout_transition=0,atrim=0:{seconds}[mix]"
raw_wav = os.path.join(out_dir, "journey-native-raw.wav"); mix_wav = os.path.join(out_dir, "journey-native-mix.wav")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", graph, "-map", "[mix]", "-ar", "48000", raw_wav], check=True)
def measure(f):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", f, "-af", "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"], capture_output=True, text=True).stderr
    return json.loads(r[r.rfind("{"):r.rfind("}") + 1])
m1 = measure(raw_wav)
ln = f"loudnorm=I=-16:TP=-1.5:LRA=11:measured_I={m1['input_i']}:measured_TP={m1['input_tp']}:measured_LRA={m1['input_lra']}:measured_thresh={m1['input_thresh']}:offset={m1['target_offset']}:linear=true"
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", raw_wav, "-af", ln, "-ar", "48000", mix_wav], check=True); os.remove(raw_wav)
if a.mix_only:
    l = measure(mix_wav); print("MIX", mix_wav, "I", l["input_i"], "TP", l["input_tp"], "cues", len(cues)); raise SystemExit(0)
video = os.path.join(out_dir, "journey-silent.mp4")
if a.frames:
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(a.fps), "-i", os.path.join(a.frames, "f%04d.jpg"), "-c:v", "libx264", "-preset", "slow", "-crf", "19", "-pix_fmt", "yuv420p", "-movflags", "+faststart", video], check=True)
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", video, "-i", mix_wav, "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", a.out], check=True)
loud = measure(a.out)
receipt = dict(film=os.path.basename(a.out), film_sha256=sha(a.out), built=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               journey=dict(file=os.path.basename(a.journey), sha256=sha(a.journey), id=J.get("journey_id"), zones=len(J["zones"]), seconds=seconds),
               cue_sheet=dict(file="journey-cue-sheet.json", sha256=sha(sheet_path), cues=len(cues)),
               camera_path=dict(file=os.path.basename(a.camera_path), sha256=sha(a.camera_path), fps=path["fps"], frames=path["frames"], sections=path["sections"]),
               policy=dict(file=os.path.basename(a.policy), id=sheet["policy_id"], sha256=sha(a.policy)), map_sha256=sha(a.map), blend_sha256=sha(a.blend) if a.blend else None,
               measure=json.load(open(a.measure)) if a.measure and os.path.exists(a.measure) else None, render=path.get("render"),
               clips=[dict(slug=c["slug"], language=c["language"], wav_sha256=sha(c["wav"])) for c in cues],
               soundtrack_loudness=dict(integrated_lufs=float(loud["input_i"]), true_peak_dbtp=float(loud["input_tp"])),
               claim="An authored interpretation of the multilingual flight; the browser mix is chosen live by the soundscape policy and is not reproduced here (D7).")
json.dump(receipt, open(os.path.join(out_dir, "journey-render-receipt.json"), "w"), indent=1, ensure_ascii=False)
print("MUXED", a.out, os.path.getsize(a.out), "bytes; soundtrack", loud["input_i"], "LUFS; cues", len(cues))
