"""fly_journey.py — the multilingual flight: the camera follows journey.json's language zones
(Multilingual City Plan, Phase 5).  Same rung-2 render as fly_street.py; the path is the
cue sheet's: fly to each zone at its height during the first 40% of its seconds, hold over it
for the rest, and on the zone with `descend` come down to that house's door as the street
flight does.  Zone times are the cue sheet's, so the soundtrack (mux_native.py) and the
picture share one clock.

    blender -b city/out/street.blend --python city/fly_journey.py -- --journey JOURNEY.json --map MAP.json \
        --out city/out --measure 6 --label journey [--res 1280 720] [--samples 48] [--fps 12]
    blender -b city/out/street.blend --python city/fly_journey.py -- --journey … --map … --out city/out --film --label journey
"""
import bpy, json, math, os, sys, time, platform, resource
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
import argparse
ap = argparse.ArgumentParser()
ap.add_argument("--journey", required=True); ap.add_argument("--map", required=True); ap.add_argument("--out", required=True)
ap.add_argument("--measure", type=int, default=0); ap.add_argument("--film", action="store_true")
ap.add_argument("--res", type=int, nargs=2, default=(1280, 720)); ap.add_argument("--samples", type=int, default=48); ap.add_argument("--fps", type=int, default=12)
ap.add_argument("--seed", type=int, default=7); ap.add_argument("--label", default="journey")
ap.add_argument("--no-volume", action="store_true"); ap.add_argument("--no-rt", action="store_true"); ap.add_argument("--exposure", type=float, default=0.0)
a = ap.parse_args(argv)

J = json.load(open(a.journey)); m = json.load(open(a.map))
scene = bpy.context.scene; cam = scene.camera; target = bpy.data.objects["CamTarget"]
S = scene["wiki_city_scale_m_per_unit"]; square = scene["wiki_city_square"]
sq = next(n for n in m["nodes"] if n["id"] == square)
def W(x, y): return ((x - sq["x"]) * S, -(y - sq["y"]) * S)
fps = a.fps; zones = J["zones"]; seconds = float(J["total_seconds"]); n_total = int(round(seconds * fps))
scene.render.fps = fps; scene.frame_start = 1; scene.frame_end = n_total
def at(t): return max(1, min(n_total, int(round(t * fps)) + 1))
speakers = [o for o in bpy.data.objects if o.type == "SPEAKER"]

# ------------------------------------------------------------ the path from the zones
cam_keys = []; t = 0.0; sections = {}
nodes = {n["slug"]: n for n in m["nodes"] if n["site"].startswith("constitution")}
for i, z in enumerate(zones):
    x, y = W(*z["at"]); h = float(z.get("height", 20))
    nxt = zones[i + 1] if i + 1 < len(zones) else None
    tx, ty = W(*nxt["at"]) if nxt else (x, y)
    look = (x + (tx - x) * 0.25, y + (ty - y) * 0.25, 0.5)          # a little ahead, at the roofs
    if i == 0: cam_keys.append((0.0, (x - 18, y - 24, h + 12), look))   # begin high and behind the first zone
    if z.get("descend"):
        sp = [o for o in speakers if z["descend"].split("-")[0] in o.name.lower()]
        hx, hy = (sp[0].location.x, sp[0].location.y) if sp else W(nodes[z["descend"]]["x"], nodes[z["descend"]]["y"])
        d = math.hypot(hx, hy) or 1
        cam_keys += [(t + 0.15 * z["seconds"], (hx - hx / d * 10.0, hy - hy / d * 10.0, 6.5), (hx, hy, 1.8)),
                     (t + 0.55 * z["seconds"], (hx - hx / d * 5.5, hy - hy / d * 5.5, 5.2), (hx - hx / d * 1.1, hy - hy / d * 1.1, 1.6)),
                     (t + 0.85 * z["seconds"], (hx - hx / d * 3.2, hy - hy / d * 3.2, 4.4), (hx - hx / d * 1.1, hy - hy / d * 1.1, 1.3)),
                     (t + z["seconds"], (hx - hx / d * 3.0, hy - hy / d * 3.0, 4.3), (hx - hx / d * 1.1, hy - hy / d * 1.1, 1.4))]
    else:
        cam_keys += [(t + 0.4 * z["seconds"], (x, y - 6, h), look), (t + z["seconds"], (x + 3, y - 4, h * 0.95), look)]
    sections[z["name"]] = [round(t, 1), round(t + z["seconds"], 1)]
    t += z["seconds"]
bpy.context.preferences.edit.keyframe_new_interpolation_type = "BEZIER"
for sec, cpos, tpos in cam_keys:
    f = at(sec); cam.location = cpos; cam.keyframe_insert("location", frame=f); target.location = tpos; target.keyframe_insert("location", frame=f)

# ------------------------------------------------------------ rung 2, as fly_street does it
ids = [i.identifier for i in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
scene.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in ids else "BLENDER_EEVEE"
scene.render.resolution_x, scene.render.resolution_y = a.res; scene.render.resolution_percentage = 100
scene.render.use_motion_blur = False; scene.render.use_compositing = False
if hasattr(scene, "compositing_node_group"): scene.compositing_node_group = None
ee = scene.eevee; ee.taa_render_samples = a.samples; ee.use_shadows = True; ee.use_raytracing = not a.no_rt
scene.view_settings.exposure = a.exposure
if a.no_volume and scene.world and scene.world.use_nodes:
    wo = scene.world.node_tree.nodes["World Output"]
    for l in list(scene.world.node_tree.links):
        if l.to_socket == wo.inputs["Volume"]: scene.world.node_tree.links.remove(l)
ee.ray_tracing_method = "SCREEN"; ee.ray_tracing_options.resolution_scale = "1"; ee.ray_tracing_options.screen_trace_quality = 0.5
if hasattr(ee.ray_tracing_options, "use_backface_hit"): ee.ray_tracing_options.use_backface_hit = True
ee.shadow_ray_count = 2; ee.shadow_step_count = 8; ee.shadow_resolution_scale = 1.0
ee.volumetric_start = 0.1; ee.volumetric_end = 260.0; ee.volumetric_samples = 64; ee.volumetric_tile_size = "4"; ee.use_volumetric_shadows = True
cam.data.dof.use_dof = True; cam.data.dof.focus_object = target; cam.data.dof.aperture_fstop = 2.8

def rss_mb():
    r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss; return round(r / (1024 * 1024 if platform.system() == "Darwin" else 1024), 1)
marks = {"t0": None, "ms": []}
def _pre(*_): marks["t0"] = time.perf_counter()
def _post(*_):
    if marks["t0"] is not None: marks["ms"].append(round((time.perf_counter() - marks["t0"]) * 1000.0, 1)); print(f"  frame {len(marks['ms'])} {marks['ms'][-1]:.0f} ms", flush=True)
bpy.app.handlers.render_pre.append(_pre); bpy.app.handlers.render_post.append(_post)
os.makedirs(a.out, exist_ok=True)
scene.render.image_settings.file_format = "JPEG"; scene.render.image_settings.quality = 90

if a.measure:
    scene.frame_step = max(1, n_total // a.measure); scene.frame_end = 1 + scene.frame_step * (a.measure - 1)
    frames_dir = os.path.join(a.out, f"measure-{a.label}-frames"); os.makedirs(frames_dir, exist_ok=True)
    scene.render.filepath = os.path.join(frames_dir, "f")
    t_all = time.perf_counter(); bpy.ops.render.render(animation=True); wall = time.perf_counter() - t_all
    ms = marks["ms"]; warm = sorted(ms[1:]) or sorted(ms)
    stills = sorted(os.listdir(frames_dir)); keep = []
    for i, name in enumerate(stills):
        dst = os.path.join(a.out, f"still-{a.label}-{i:02d}.jpg"); os.replace(os.path.join(frames_dir, name), dst); keep.append(dst)
    os.rmdir(frames_dir)
    rec = dict(rung=2, label=a.label, resolution=list(a.res), samples=a.samples, fps=fps, frames=len(ms), cold_ms=ms[0], warm_median_ms=warm[len(warm) // 2],
               warm_p90_ms=warm[int(len(warm) * 0.9) - 1 if len(warm) > 1 else 0], wall_s=round(wall, 1), peak_rss_mb=rss_mb(),
               film_estimate_min=round(n_total * warm[len(warm) // 2] / 60000.0, 1), total_frames=n_total, stills=keep, blender=bpy.app.version_string)
    json.dump(rec, open(os.path.join(a.out, f"measure-{a.label}.json"), "w"), indent=1)
    print("MEASURE", json.dumps({k: rec[k] for k in ("warm_median_ms", "warm_p90_ms", "peak_rss_mb", "film_estimate_min", "total_frames")}))

if a.film:
    scene.frame_step = 1; scene.frame_end = n_total
    frames_dir = os.path.join(a.out, f"{a.label}-frames"); os.makedirs(frames_dir, exist_ok=True)
    scene.render.filepath = os.path.join(frames_dir, "f")
    t_all = time.perf_counter(); bpy.ops.render.render(animation=True); wall = time.perf_counter() - t_all
    ms = marks["ms"]; warm = sorted(ms[1:]) or sorted(ms)
    path = dict(fps=fps, seconds=seconds, frames=n_total, seed=a.seed, resolution=list(a.res), samples=a.samples,
                keys=[dict(t=s, camera=list(c), target=list(tg)) for s, c, tg in cam_keys], sections=sections, journey_id=J.get("journey_id"),
                render=dict(frames_rendered=len(ms), warm_median_ms=warm[len(warm) // 2] if warm else None, wall_min=round(wall / 60, 1), blender=bpy.app.version_string, engine=scene.render.engine, peak_rss_mb=rss_mb()),
                frames_dir=frames_dir, frame_pattern="f%04d.jpg")
    json.dump(path, open(os.path.join(a.out, f"{a.label}-camera-path.json"), "w"), indent=1)
    print("FILM", frames_dir, f"{len(ms)} frames in {wall/60:.1f} min")
