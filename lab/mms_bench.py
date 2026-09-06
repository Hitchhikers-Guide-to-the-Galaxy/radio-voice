"""Meta MMS-TTS (VITS, one checkpoint per language, CC-BY-NC 4.0) on Article 1; realtime factor and peak RSS on this machine."""
import json, os, time, resource, sys, platform
import torch, soundfile as sf
from transformers import VitsModel, AutoTokenizer
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)
texts = json.load(open(os.path.join(HERE, "article-one.json")))
LANGS = {"ar": "ara", "de": "deu", "es": "spa", "fr": "fra", "pt-BR": "por", "it": "ita"}
machine = sys.argv[1] if len(sys.argv) > 1 else platform.node()
res = []
for lang, iso in LANGS.items():
    try:
        t0 = time.time(); model = VitsModel.from_pretrained(f"facebook/mms-tts-{iso}"); tok = AutoTokenizer.from_pretrained(f"facebook/mms-tts-{iso}"); load = time.time() - t0
        inputs = tok(texts[lang]["text"], return_tensors="pt")
        t0 = time.time()
        with torch.no_grad(): wav = model(**inputs).waveform[0].numpy()
        el = time.time() - t0; sr = model.config.sampling_rate; dur = len(wav) / sr
        out = os.path.join(OUT, f"{lang}-mms-{iso}.wav"); sf.write(out, wav, sr)
        rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6
        if platform.system() == "Darwin": rss /= 1  # ru_maxrss is bytes on macOS
        res.append(dict(lang=lang, voice=f"mms-tts-{iso}", engine="mms", machine=machine, seconds=round(dur, 1), render_s=round(el, 2), rtf=round(dur / el, 2), load_s=round(load, 1), max_rss_mb=round(rss), file=os.path.basename(out)))
        print(lang, iso, f"{dur:.1f}s in {el:.1f}s = {dur/el:.2f}x load {load:.1f}s rss {rss:.0f}MB", flush=True)
    except Exception as e:
        res.append(dict(lang=lang, voice=f"mms-tts-{iso}", engine="mms", error=str(e)[:200])); print("FAIL", iso, e, flush=True)
json.dump(res, open(os.path.join(HERE, f"mms-results-{machine}.json"), "w"), indent=1, ensure_ascii=False)
