"""Build the Voice Bench page: every bench clip as an audio item with a caption
naming engine, voice, machine and realtime factor. Converts wav -> m4a into
pages/assets/voice-bench/ ready to scp to the site. Absolute https URLs."""
import sys, os, json, subprocess, glob
sys.path.insert(0, os.path.expanduser("~/.claude/skills/fedwiki-lib"))
import fedwiki
ROOT = os.path.dirname(os.path.abspath(__file__))
SITE = "https://radio-agentic.private.fish"
REG = json.load(open(os.path.join(ROOT, "voices.json"))); REG.pop("_comment", None)
STATS = json.load(open(os.path.join(ROOT, "out/bench/stats.json")))   # name -> {"rt": x, "machine": "..."}
OUT = os.path.join(ROOT, "pages"); A = os.path.join(OUT, "assets", "voice-bench"); os.makedirs(A, exist_ok=True)
PROV = "Claude Code, in dialogue with David Bovill, 2 September 2026"

def m4a(name):
    src = os.path.join(ROOT, "out/bench", name + ".wav"); dst = os.path.join(A, name + ".m4a")
    if not os.path.exists(dst):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-c:a", "aac", "-b:a", "96k", dst], check=True)
    d = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", dst],
                             capture_output=True, text=True).stdout)
    return dst, d

def player(name, caption):
    return {"type": "html", "text":
        f'<audio controls preload="none" style="width:100%" src="{SITE}/assets/pages/voice-bench/{name}.m4a"></audio>\n<p><i>{caption}</i></p>'}

GROUPS = [
 ("British — Kokoro, rendered on the Air", ["george","lewis","daniel-k","fable","emma","isabella","alice","lily"]),
 ("American — Kokoro, rendered on the Air", ["michael","adam","fenrir","onyx","heart","bella","nicole","sarah"]),
 ("The Pis — Piper on 02-pi4", ["northern","alan","alba","jenny"]),
 ("macOS compact voices — say, on the Air", ["daniel","moira","fred","whisper"]),
 ("Treated — the retro and telephone chains", ["george-retro","fred-retro","emma-phone"]),
]
items = [
 "This page was written by [[Claude Code]] in dialogue with [[David Bovill]], 2 September 2026. Phase 0 of the [[Radio Voice Plan]].",
 "The **Voice Bench** is one paragraph — the opening of the South African preamble, 48 words — read by every voice the tailnet can currently produce. Listen down the page and the palette chooses itself. Every clip was rendered by the same command, `voice render`, which dispatches to Kokoro on the Air or the Pi5, Piper on 02-pi4, or macOS `say`, and can pass the result through the retro or telephone chain.",
]
first = True
for title, names in GROUPS:
    items.append(f"# {title}")
    for n in names:
        base = n.split("-")[0] if n.endswith(("-retro","-phone")) else n
        v = REG[base]; st = STATS.get(n, {})
        path, dur = m4a(n)
        fx = " through the retro chain" if n.endswith("-retro") else (" through the telephone chain" if n.endswith("-phone") else "")
        who = f"{v.get('sex','?').upper()} {v.get('accent','')}".strip()
        cap = (f"{n} — {v['engine']}:{v.get('voice')}{fx}. {who}. {dur:.0f} s"
               + (f", {st['rt']:.1f}× realtime on the {st['machine']}" if st.get("rt") else "") + ".")
        items.append(player(n, cap))
items += [
 "# Machines",
 "Kokoro-82M on the M2 Air runs at 2.3 to 2.9 times realtime, CPU only, with 54 voices in the pack. " + STATS.get("_pi5_note", "") + " Piper on 02-pi4 is the voice the Marvin Station already speaks with; its models are 60 MB each and it needs no GPU. macOS `say` is instant and free but only the compact voices are installed — the Premium voices are a download in System Settings and are not yet on the bench.",
 "# The Retro Chain",
 "An ffmpeg filter preset, applied to any voice: a 300 to 3400 Hz band, 6:1 compression, a slow 0.45 Hz pitch wobble for tape, and a bed of pink noise. The telephone preset is narrower, with light bit-crushing and no wobble. Both live in the `voice` command as `--fx retro` and `--fx phone`.",
 "# The Palette",
 "A proposal, to be fixed by listening: two British, two American, one retro, one hero. British — **george** and **emma**. American — **michael** and **heart**. Retro — **george** through the retro chain, or **fred** for the 1990s Macintosh sound. Hero — pending an API key; nothing on this bench is the signature voice yet.",
]
slug = "voice-bench"
page = fedwiki.make_page("Voice Bench", items, provenance=PROV)
fedwiki.ensure_see(page, ["[[Radio Voice Plan]] · [[Fragment Mill]] · [[Constitution Hour]]"], journal=False)
fedwiki.save_page(os.path.join(OUT, slug), page)
print("built", slug, "with", sum(1 for i in page["story"] if i["type"]=="html"), "players;", len(os.listdir(A)), "m4a files")
