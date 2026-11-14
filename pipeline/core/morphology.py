"""Deterministic morphology and module validation for Forge 100K Phase 2."""
from __future__ import annotations
import hashlib
import random

FACE_CONTROLS = {
    "jaw_width": (0.65, 1.35),
    "jaw_height": (0.70, 1.30),
    "cheek_fullness": (0.0, 1.0),
    "eye_scale": (0.75, 1.25),
    "eye_spacing": (0.80, 1.20),
    "nose_width": (0.70, 1.30),
    "nose_length": (0.70, 1.30),
    "mouth_width": (0.75, 1.25),
    "brow_depth": (0.0, 1.0),
    "chin_projection": (0.70, 1.30)
}
BODY_CONTROLS = {
    "height": (0.75, 1.25),
    "shoulder_width": (0.75, 1.30),
    "torso_ratio": (0.75, 1.25),
    "arm_length": (0.80, 1.20),
    "leg_length": (0.80, 1.20),
    "muscle": (0.0, 1.0),
    "mass": (0.0, 1.0)
}
SLOTS = {"headwear", "hair", "face", "torso", "back", "shoulder", "hands", "legs", "feet", "accessory"}
def clamp_controls(values, controls):
    unknown=set(values)-set(controls)
    if unknown: raise ValueError("Unknown controls: "+", ".join(sorted(unknown)))
    out={}
    for key,(lo,hi) in controls.items():
        value=float(values.get(key,(lo+hi)/2))
        if not lo <= value <= hi: raise ValueError(f"{key} must be in [{lo}, {hi}]")
        out[key]=round(value,4)
    return out
def stable_seed(asset_id, seed, namespace):
    raw=f"{asset_id}|{int(seed)}|{namespace}".encode()
    return int.from_bytes(hashlib.sha256(raw).digest()[:8],"big")
def validate_modules(module_ids, catalog, species=None):
    seen=set(); occupied=set(); chosen=[]
    for module_id in module_ids:
        if module_id in seen: raise ValueError(f"Duplicate module: {module_id}")
        seen.add(module_id)
        item=catalog.get(module_id)
        if not item: raise ValueError(f"Unknown module: {module_id}")
        if species and species not in item.get("species",[]):
            raise ValueError(f"Module {module_id} is not compatible with species {species}")
        slot=item["slot"]
        if slot in occupied: raise ValueError(f"Slot conflict: {slot}")
        occupied.add(slot); chosen.append(item)
    return chosen
def seeded_face_profile(asset_id, seed):
    rng=random.Random(stable_seed(asset_id,seed,"face"))
    return {k:round(rng.uniform(lo,hi),4) for k,(lo,hi) in FACE_CONTROLS.items()}
def seeded_body_profile(asset_id, seed):
    rng=random.Random(stable_seed(asset_id,seed,"body"))
    return {k:round(rng.uniform(lo,hi),4) for k,(lo,hi) in BODY_CONTROLS.items()}
