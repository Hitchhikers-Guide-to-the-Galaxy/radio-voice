import json, os, time, resource, sys, soundfile as sf
sys.path.insert(0, os.path.expanduser("~/Code/radio-voice")); from kokoro_onnx import Kokoro
HERE=os.path.dirname(os.path.abspath(__file__)); OUT=HERE+"/out"; texts=json.load(open(HERE+"/article-one.json"))
k=Kokoro(os.path.expanduser("~/Code/radio-voice/models/kokoro-v1.0.onnx"), os.path.expanduser("~/Code/radio-voice/models/voices-v1.0.bin")); res=[]
for lang, vn, kl in (("ja","jf_alpha","ja"),("ja","jm_kumo","ja"),("zh","zf_xiaobei","cmn"),("zh","zm_yunxi","cmn")):
    if lang not in texts: continue
    try:
        t0=time.time(); s,sr=k.create(texts[lang]["text"], voice=vn, speed=1.0, lang=kl); el=time.time()-t0
        out=f"{OUT}/{lang}-kokoro-{vn}.wav"; sf.write(out,s,sr); dur=len(s)/sr
        res.append(dict(lang=lang, voice=vn, engine="kokoro", machine="laptop M2 8GB", seconds=round(dur,1), render_s=round(el,2), rtf=round(dur/el,2), max_rss_mb=round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1e6), file=os.path.basename(out)))
        print(lang, vn, f"{dur:.1f}s {dur/el:.2f}x", flush=True)
    except Exception as e:
        res.append(dict(lang=lang, voice=vn, engine="kokoro", error=str(e)[:200])); print("FAIL", vn, e, flush=True)
json.dump(res, open(HERE+"/kokoro-extra.json","w"), indent=1)
