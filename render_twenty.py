"""Render the Fragment Mill's twenty through the proposed palette. One Kokoro
instance held for the whole batch. Each cue = framing line by the announcer,
a breath, the fragment in its assigned voice, a tail. Writes out/twenty/."""
import json, os, subprocess, time, numpy as np, soundfile as sf
from kokoro_onnx import Kokoro
ROOT = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(ROOT, "out/twenty"); os.makedirs(OUT, exist_ok=True)
REG = json.load(open(f"{ROOT}/voices.json")); REG.pop("_comment", None)
top = json.load(open(f"{ROOT}/mill/top20.json"))
ANNOUNCER = "george"
# palette by hand: British for old-world texts, American for the Americas/Pacific, retro for the two oldest
ASSIGN = {1:"heart", 2:"michael", 3:"emma", 4:"emma", 5:"george", 6:"emma", 7:"heart", 8:"george", 9:"emma",
          10:"michael", 11:"heart", 12:"michael", 13:"heart", 14:"michael", 15:"george-retro", 16:"emma",
          17:"george", 18:"heart", 19:"emma", 20:"george-retro"}
k = Kokoro(f"{ROOT}/models/kokoro-v1.0.onnx", f"{ROOT}/models/voices-v1.0.bin")
SR = 24000
def speak(name, text):
    v = REG[name.split("-")[0]]
    s, sr = k.create(text, voice=v["voice"], speed=1.0, lang=v.get("lang", "en-us"))
    assert sr == SR; return s
def fx(wav_in, wav_out, preset):
    subprocess.run(["voice", "fx", "--in", wav_in, "--out", wav_out, "--fx", preset], check=True, capture_output=True)
sil = lambda sec: np.zeros(int(SR * sec), dtype=np.float32)
t0 = time.time(); manifest = []
for o in top:
    n = o["n"]; vname = ASSIGN[n]; slug = f"{n:02d}-{o['cons_id'].lower()}"
    frame = speak(ANNOUNCER, o["frame"])
    body = speak(vname, o["text"])
    bpath = f"{OUT}/{slug}.body.wav"; sf.write(bpath, body, SR)
    if vname.endswith("-retro"):
        fx(bpath, bpath + ".fx.wav", "retro"); body, _ = sf.read(bpath + ".fx.wav", dtype="float32"); os.unlink(bpath + ".fx.wav")
    os.unlink(bpath)
    cue = np.concatenate([sil(0.3), frame, sil(0.7), body, sil(1.0)])
    sf.write(f"{OUT}/{slug}.wav", cue, SR)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", f"{OUT}/{slug}.wav", "-c:a", "aac", "-b:a", "96k", f"{OUT}/{slug}.m4a"], check=True)
    dur = len(cue) / SR
    manifest.append(dict(n=n, slug=slug, voice=vname, announcer=ANNOUNCER, seconds=round(dur, 1), title=o["title"], heading=o["heading"], frame=o["frame"], text=o["text"], cons_id=o["cons_id"]))
    print(f"{n:2d} {vname:13s} {dur:5.1f}s  {o['title'][:40]}", flush=True)
json.dump(manifest, open(f"{OUT}/manifest.json", "w"), indent=1, ensure_ascii=False)
tot = sum(m["seconds"] for m in manifest)
print(f"{len(manifest)} cues, {tot/60:.1f} min of audio, rendered in {(time.time()-t0)/60:.1f} min")
# one preview file, all twenty in order
with open(f"{OUT}/list.txt", "w") as f:
    for m in manifest: f.write(f"file '{OUT}/{m['slug']}.wav'\n")
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", f"{OUT}/list.txt", "-c:a", "aac", "-b:a", "96k", f"{OUT}/constitution-twenty.m4a"], check=True)
print("preview:", f"{OUT}/constitution-twenty.m4a")
