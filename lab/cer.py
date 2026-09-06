"""Whisper back-transcription of every clip in out/ against article-one.json; character error rate after folding case and punctuation.
Writes cer-results.json keyed by file name."""
import json, os, re, sys, unicodedata, difflib, glob, time
from faster_whisper import WhisperModel
HERE = os.path.dirname(os.path.abspath(__file__)); texts = json.load(open(os.path.join(HERE, "article-one.json")))
WL = {"ar": "ar", "ar-JO": "ar", "de": "de", "es": "es", "es-MX": "es", "fr": "fr", "pt-BR": "pt", "pt-PT": "pt", "it": "it", "de-CH": "de", "fr-CH": "fr", "it-CH": "it", "rm": None, "ja": "ja", "zh": "zh"}
def norm(s):
    s = unicodedata.normalize("NFC", s).lower()
    s = re.sub(r"[ً-ْ]", "", s)  # Arabic diacritics
    s = re.sub(r"[^\w\s]", "", s); return re.sub(r"\s+", " ", s).strip()
def cer(ref, hyp):
    """Levenshtein edit distance over characters, divided by the reference length (difflib's ratio is unreliable past 200 chars)."""
    a, b = norm(ref), norm(hyp)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return round(prev[-1] / max(1, len(a)), 3)
m = WhisperModel("small", device="cpu", compute_type="int8")
out = json.load(open(os.path.join(HERE, "cer-results.json"))) if os.path.exists(os.path.join(HERE, "cer-results.json")) else {}
for f in sorted(glob.glob(os.path.join(HERE, "out", "*.wav"))):
    name = os.path.basename(f)
    if name in out and "--redo" not in sys.argv: continue
    lang = max((k for k in texts if name.startswith(k + "-")), key=len, default=None)
    if lang not in texts: print("skip", name); continue
    t0 = time.time(); segs, info = m.transcribe(f, language=WL.get(lang) or None, beam_size=5); hyp = " ".join(s.text.strip() for s in segs)
    out[name] = dict(lang=lang, cer=cer(texts[lang]["text"], hyp), whisper_s=round(time.time() - t0, 1), hyp=hyp)
    print(name, out[name]["cer"], flush=True)
    json.dump(out, open(os.path.join(HERE, "cer-results.json"), "w"), indent=1, ensure_ascii=False)
