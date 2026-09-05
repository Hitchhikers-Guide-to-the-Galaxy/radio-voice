#!/usr/bin/env python3
"""Write the fixtures: one valid street manifest, one valid policy, and the
invalid cases the Hear Crowds Plan names (file names carry the code the
validator must raise)."""
import copy, json, os
HERE = os.path.dirname(os.path.abspath(__file__))
H = "sha256:" + "0" * 64
valid = {
  "schema_version": "0.1.0",
  "manifest_id": "media:constitution.legalcommons.org/bolivia-plurinational-state-of-2009:2026-09-05",
  "map_edition_id": "legalcommons-pages-epoch-3",
  "semantic_target": {
    "wiki_city_id": "page:constitution.legalcommons.org/bolivia-plurinational-state-of-2009",
    "entity_type": "page_house",
    "canonical_uri": "https://constitution.legalcommons.org/bolivia-plurinational-state-of-2009.json",
    "title": "Bolivia (Plurinational State of) 2009",
    "source_revision": H,
    "access_policy_uri": "policy:public"
  },
  "assets": [{
    "asset_id": "voice:bolivia-2009:p.1:v1",
    "media_type": "audio", "role": "verbatim_fragment", "language": "en-US",
    "title": "Preamble, read by a synthetic voice",
    "delivery": [{"uri": "bolivia-2009-p.1.opus", "mime": "audio/ogg; codecs=opus", "sha256": H, "bytes": 1},
                 {"uri": "bolivia-2009-p.1.m4a", "mime": "audio/mp4", "sha256": H, "bytes": 1}],
    "master": {"uri": "bolivia-2009-p.1.wav", "sha256": H},
    "duration_seconds": 40.6,
    "loudness": {"integrated_lufs": -16.1, "true_peak_dbtp": -1.6, "lra": 6.2, "target": "I=-16:TP=-1.5:LRA=11"},
    "transcript_uri": "bolivia-2009-p.1.vtt", "transcript_text_uri": "bolivia-2009-p.1.txt",
    "source_text": {"kind": "verbatim", "text_uri": "bolivia-2009-p.1.txt", "fragment_id": "bolivia-2009:p.1",
                    "heading": "Preamble", "words": 82, "input_revision": H, "review_status": "machine_selected"},
    "provenance": {"kind": "synthetic_voice", "generator": "radio-voice/hear/build_street.py", "model": "kokoro-v1.0.onnx",
                   "model_version": "1.0", "model_sha256": H, "voice_id": "heart", "voice_registry": "radio-voice/voices.json",
                   "pipeline": "kokoro -> loudnorm I=-16:TP=-1.5:LRA=11 -> libopus 48k / aac 96k",
                   "generated_at": "2026-09-05T20:00:00Z"},
    "rights": {"source_licence": "CC-BY-NC-3.0 (Constitute Project)", "source_rights_class": "restricted",
               "voice_licence": "Apache-2.0 (Kokoro)", "consent_record_uri": None, "public_render": True,
               "attribution": "Constitute Project; © Oxford University Press, Inc. — Max Planck Institute"},
    "spatial": {"anchor": "threshold", "distance_model": "inverse", "ref_distance": 4.0, "max_distance": 45.0,
                "rolloff_factor": 1.2, "cone_inner_angle": 180, "cone_outer_angle": 270, "cone_outer_gain": 0.2,
                "occlusion": True, "reverb_zone": "small_room"},
    "playback": {"trigger": "focus_or_threshold", "loop": False, "priority": 70, "bus": "synthetic_speech", "cooldown_seconds": 90}
  }],
  "live_room": {"enabled": False, "room_key": "page:constitution.legalcommons.org/bolivia-plurinational-state-of-2009",
                "provider": "livekit", "access_policy_uri": "policy:public", "recording": "off", "transcription": "off",
                "e2ee": "required_when_enabled", "agent_participation": "disclosed_opt_in"}
}
policy = {
  "schema_version": "0.1.0", "policy_id": "hear-crowds-street-0.1.0",
  "max_active_emitters": 8, "max_intelligible_speech": 2, "focus_duck_db": -14,
  "crossfade_ms": 900, "crossfade_law": "equal_power",
  "hysteresis": {"deadband": 0.08, "min_dwell_ms": 900},
  "selection_weights": {"proximity": 0.40, "explicit_focus": 0.25, "journey_relevance": 0.15, "view_direction": 0.10, "semantic_relevance": 0.10},
  "buses": ["human_speech", "synthetic_speech", "live_room", "music", "ambience", "ui"],
  "acoustic_lod": [
    {"scale": "region", "what_sounds": "one regional motif; no speech", "max_intelligible": 0},
    {"scale": "city", "what_sounds": "at most two beacon voices, the rest a murmur", "max_intelligible": 2},
    {"scale": "street", "what_sounds": "fragments from the nearest houses, two intelligible", "max_intelligible": 2},
    {"scale": "threshold", "what_sounds": "the house you face dominates; the street ducks", "max_intelligible": 1},
    {"scale": "interior", "what_sounds": "this page only, full transcript alongside", "max_intelligible": 1}
  ],
  "consent": {"gate_required": True, "gate_text": "Enter the soundscape"}
}
def w(sub, name, doc):
    p = os.path.join(HERE, "fixtures", sub, name); os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump(doc, open(p, "w"), indent=1); print("wrote", sub, name)
w("valid", "street-bolivia.json", valid)
w("valid", "soundscape-policy.json", policy)
d = copy.deepcopy(valid); d["semantic_target"]["source_revision"] = "unknown"; w("invalid", "missing-source-revision_S00.json", d)
d = copy.deepcopy(valid); d["assets"][0]["rights"]["source_licence"] = "unknown"; w("invalid", "unknown-rights_M01.json", d)
d = copy.deepcopy(valid); d["assets"][0]["rights"]["attribution"] = ""; w("invalid", "no-attribution_M02.json", d)
d = copy.deepcopy(valid); d["assets"][0]["transcript_uri"] = "bolivia-2009-p.1.txt"; w("invalid", "missing-transcript_M03.json", d)
d = copy.deepcopy(valid); d["semantic_target"]["canonical_uri"] = "https://clause.legalcommons.org/right-to-amparo.json"; w("invalid", "bad-target_M04.json", d)
d = copy.deepcopy(valid); d["assets"][0]["source_text"]["heading"] = "National Anthem"; d["assets"][0]["source_text"]["fragment_id"] = "bolivia-2009:anthem.1"; w("invalid", "anthem_M05.json", d)
d = copy.deepcopy(valid); d["assets"][0]["loudness"]["integrated_lufs"] = -23.0; w("invalid", "quiet-clip_M07.json", d)
d = copy.deepcopy(policy); d["hysteresis"]["min_dwell_ms"] = 300; w("invalid", "policy-dwell-below-fade_M08.json", d)
d = copy.deepcopy(policy); d["selection_weights"]["proximity"] = 0.6; w("invalid", "policy-weights_M09.json", d)
