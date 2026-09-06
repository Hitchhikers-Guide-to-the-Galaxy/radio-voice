"""Kokoro-82M on Article 1 for the languages it covers; one model instance; realtime factor and peak RSS."""
import json, os, time, resource, sys
import soundfile as sf
sys.path.insert(0, os.path.expanduser("~/Code/radio-voice"))
from kokoro_onnx import Kokoro
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)
texts = json.load(open(os.path.join(HERE, "article-one.json")))
VOICES = {"es": [("ef_dora", "es"), ("em_alex", "es"), ("em_santa", "es")], "fr": [("ff_siwis", "fr-fr")], "pt-BR": [("pf_dora", "pt-br"), ("pm_alex", "pt-br"), ("pm_santa", "pt-br")], "it": [("if_sara", "it"), ("im_nicola", "it")], "fr-CH": [("ff_siwis", "fr-fr")], "it-CH": [("if_sara", "it")]}
k = Kokoro(os.path.expanduser("~/Code/radio-voice/models/kokoro-v1.0.onnx"), os.path.expanduser("~/Code/radio-voice/models/voices-v1.0.bin"))
res = []
for lang, vs in VOICES.items():
    for vn, kl in vs:
        t0 = time.time(); s, sr = k.create(texts[lang]["text"], voice=vn, speed=1.0, lang=kl); el = time.time() - t0
        out = os.path.join(OUT, f"{lang}-kokoro-{vn}.wav"); sf.write(out, s, sr); dur = len(s) / sr
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6
        res.append(dict(lang=lang, voice=vn, engine="kokoro", machine="laptop M2 8GB", seconds=round(dur, 1), render_s=round(el, 2), rtf=round(dur / el, 2), max_rss_mb=round(rss), file=os.path.basename(out)))
        print(lang, vn, f"{dur:.1f}s in {el:.1f}s = {dur/el:.2f}x rss {rss:.0f}MB", flush=True)
json.dump(res, open(os.path.join(HERE, "kokoro-results.json"), "w"), indent=1, ensure_ascii=False)
