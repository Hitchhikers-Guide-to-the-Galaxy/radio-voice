import time, sys, soundfile as sf
from kokoro_onnx import Kokoro

TEXT = ("We, the people of South Africa, recognise the injustices of our past; "
        "honour those who suffered for justice and freedom in our land; "
        "respect those who have worked to build and develop our country; and believe "
        "that South Africa belongs to all who live in it, united in our diversity.")

k = Kokoro("models/kokoro-v1.0.onnx", "models/voices-v1.0.bin")
names = sorted(k.get_voices())
print(f"{len(names)} voices available")
print(" ".join(names))
print()
for v in sys.argv[1:]:
    t0 = time.time()
    samples, sr = k.create(TEXT, voice=v, speed=1.0, lang="en-gb" if v[0]=="b" else "en-us")
    el = time.time() - t0
    dur = len(samples)/sr
    sf.write(f"bench_{v}.wav", samples, sr)
    print(f"{v:12s} {dur:5.1f}s audio in {el:5.2f}s  = {dur/el:5.2f}x realtime")
