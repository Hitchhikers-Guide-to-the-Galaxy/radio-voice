"""Render Article 1 of each language with every Piper voice in VOICES; measure realtime factor and peak RSS.
Runs on the machine that holds the voices (the MacMini). Writes out/<lang>-<voice>.wav and piper-results.json."""
import json, os, sys, time, resource, wave
from piper import PiperVoice
HERE = os.path.dirname(os.path.abspath(__file__)); VDIR = os.path.expanduser("~/radio-voice/voices"); OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)
texts = json.load(open(os.path.join(HERE, "article-one.json")))
VOICES = {"ar": ["ar_JO-kareem-medium"], "de": ["de_DE-thorsten-medium", "de_DE-thorsten-high"], "es": ["es_ES-sharvard-medium", "es_ES-davefx-medium", "es_MX-claude-high"],
          "fr": ["fr_FR-siwis-medium", "fr_FR-upmc-medium", "fr_FR-tom-medium"], "pt-BR": ["pt_BR-faber-medium", "pt_BR-cadu-medium"], "pt-PT": ["pt_PT-tugão-medium"],
          "it": ["it_IT-riccardo-x_low", "it_IT-paola-medium", "it_IT-serena-medium"], "de-CH": ["de_DE-thorsten-medium"], "fr-CH": ["fr_FR-siwis-medium"], "it-CH": ["it_IT-paola-medium"]}
res = []
for lang, voices in VOICES.items():
    t = texts[lang]["text"]
    for vn in voices:
        path = os.path.join(VDIR, vn + ".onnx")
        if not os.path.exists(path): res.append(dict(lang=lang, voice=vn, error="model missing")); print("MISSING", vn); continue
        try:
            v = PiperVoice.load(path)
            out = os.path.join(OUT, f"{lang}-{vn}.wav"); t0 = time.time()
            with wave.open(out, "wb") as w: v.synthesize_wav(t, w)
            el = time.time() - t0
            with wave.open(out) as w: dur = w.getnframes() / w.getframerate()
            rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6
            res.append(dict(lang=lang, voice=vn, engine="piper", machine="macmini M1 8GB", seconds=round(dur, 1), render_s=round(el, 2), rtf=round(dur / el, 2), max_rss_mb=round(rss), file=os.path.basename(out)))
            print(lang, vn, f"{dur:.1f}s in {el:.1f}s = {dur/el:.2f}x rss {rss:.0f}MB", flush=True)
        except Exception as e:
            res.append(dict(lang=lang, voice=vn, error=str(e)[:200])); print("FAIL", vn, e, flush=True)
json.dump(res, open(os.path.join(HERE, "piper-results.json"), "w"), indent=1, ensure_ascii=False)
