"""Deterministic Blender batch worker for Forge 100K.

Run:
  blender --background --python pipeline/blender/generate_batch.py -- pipeline/manifests/sample-batch.json

This creates stylized blockout geometry, UVs and a GLB. Rigging, animation,
production topology and final textures remain separate gated stages.
"""
import bpy
import json
import math
import os
import random
import sys
from pathlib import Path

def args_after_separator():
    argv = sys.argv
    return argv[argv.index("--") + 1:] if "--" in argv else []

def material(name, color, metallic=0.0, roughness=0.65):
    mat = bpy.data.materials.new(name=name)
    mat.diffuse_color = (*color, 1.0)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (*color, 1.0)
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Roughness"].default_value = roughness
    return mat

def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.materials, bpy.data.armatures):
        for item in list(datablocks):
            if item.users == 0:
                datablocks.remove(item)

def add_uv_sphere(name, location, scale, mat, segments=24, rings=16):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    return obj

def add_beveled_cube(name, location, scale, mat, bevel=0.08):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    if bevel:
        mod = obj.modifiers.new("SoftEdges", "BEVEL")
        mod.width = bevel
        mod.segments = 2
        obj.modifiers.new("WeightedNormals", "WEIGHTED_NORMAL")
    return obj

def build_character(job):
    rng = random.Random(int(job["seed"]))
    palette = {
        "armored": ((0.12, 0.19, 0.28), (0.72, 0.78, 0.86)),
        "space": ((0.12, 0.22, 0.42), (0.25, 0.82, 0.92)),
        "royal": ((0.34, 0.12, 0.28), (0.92, 0.68, 0.22)),
        "normal": ((0.22, 0.42, 0.28), (0.75, 0.54, 0.38))
    }
    cloth_color, accent_color = palette.get(job.get("style", "normal").lower(), palette["normal"])
    cloth = material("M_Cloth", cloth_color)
    accent = material("M_Accent", accent_color, metallic=0.55 if job["species"] == "robot" else 0.15)
    skin = material("M_Base", (0.55, 0.34, 0.24) if job["species"] == "human" else accent_color)
    dark = material("M_Details", (0.025, 0.04, 0.06), metallic=0.25)
    parts = []
    is_robot = job["species"] == "robot"
    parts.append(add_beveled_cube("Torso", (0, 0, 1.45), (0.9, 0.48, 0.9), accent if is_robot else cloth))
    parts.append(add_uv_sphere("Head", (0, 0, 2.15), (0.34, 0.32, 0.38), accent if is_robot else skin))
    parts.append(add_beveled_cube("Pelvis", (0, 0, 0.92), (0.66, 0.42, 0.32), cloth))
    for side, label in ((-1, "L"), (1, "R")):
        parts.append(add_beveled_cube("Arm_" + label, (side * 0.62, 0, 1.48), (0.24, 0.34, 0.82), accent if job["style"] in ("armored", "space") else cloth))
        parts.append(add_beveled_cube("Leg_" + label, (side * 0.22, 0, 0.43), (0.28, 0.38, 0.78), dark))
        parts.append(add_beveled_cube("Boot_" + label, (side * 0.22, -0.12, 0.08), (0.34, 0.58, 0.18), accent))
        eye_x = side * 0.12
        parts.append(add_uv_sphere("Eye_" + label, (eye_x, -0.292, 2.19), (0.045, 0.025, 0.055), dark, 12, 8))
    if job["style"] in ("armored", "royal", "space"):
        parts.append(add_beveled_cube("ChestPlate", (0, -0.255, 1.48), (0.58, 0.08, 0.48), accent, 0.035))
        parts.append(add_uv_sphere("Shoulder_L", (-0.62, 0, 1.88), (0.2, 0.22, 0.18), accent))
        parts.append(add_uv_sphere("Shoulder_R", (0.62, 0, 1.88), (0.2, 0.22, 0.18), accent))
    # Stable deterministic micro-variation; geometry remains inside the starter blockout tier.
    for obj in parts:
        obj["forge_asset_id"] = job["asset_id"]
        obj["forge_seed"] = int(job["seed"])
    bpy.ops.object.select_all(action="DESELECT")
    for obj in parts:
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        if obj.type == "MESH":
            bpy.ops.object.mode_set(mode="OBJECT") if bpy.context.object.mode != "OBJECT" else None
            bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.select_all(action="SELECT")
            bpy.ops.uv.smart_project(island_margin=0.02)
            bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    root = bpy.data.objects.new(job["asset_id"], None)
    bpy.context.collection.objects.link(root)
    for obj in parts:
        obj.parent = root
    root["forge_asset_id"] = job["asset_id"]
    root["forge_species"] = job["species"]
    root["forge_archetype"] = job["archetype"]
    root["forge_quality_tier"] = "blockout"
    root["forge_rigging_status"] = "pending"
    root["forge_seed"] = int(job["seed"])
    return root

def process_job(job, output_dir):
    clear_scene()
    root = build_character(job)
    bpy.ops.object.select_all(action="DESELECT")
    root.select_set(True)
    for child in root.children:
        child.select_set(True)
    bpy.context.view_layer.objects.active = root
    os.makedirs(output_dir, exist_ok=True)
    out = os.path.abspath(os.path.join(output_dir, job["asset_id"] + ".glb"))
    bpy.ops.export_scene.gltf(
        filepath=out, export_format="GLB", use_selection=True,
        export_apply=True, export_texcoords=True, export_normals=True,
        export_materials="EXPORT", export_cameras=False, export_lights=False
    )
    report = {
        "asset_id": job["asset_id"], "file": out, "status": "generated",
        "quality_tier": "blockout", "rigging_status": "pending",
        "animation_status": "pending", "provenance": job.get("provenance", {}),
        "seed": int(job["seed"])
    }
    with open(out + ".report.json", "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    print("FORGE_GENERATED " + json.dumps(report))

def main():
    args = args_after_separator()
    if not args:
        raise SystemExit("Manifest path required after --")
    manifest_path = os.path.abspath(args[0])
    with open(manifest_path, "r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    if manifest.get("schema_version") != "1.0.0" or not isinstance(manifest.get("jobs"), list):
        raise ValueError("Unsupported manifest schema or missing jobs array")
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(manifest_path)))
    output_dir = os.path.abspath(os.path.join(base_dir, manifest.get("output_dir", "artifacts")))
    for job in manifest["jobs"]:
        required = ("asset_id", "archetype", "species", "style", "seed", "provenance")
        missing = [key for key in required if key not in job]
        if missing:
            raise ValueError("Job missing required fields: " + ", ".join(missing))
        process_job(job, output_dir)

if __name__ == "__main__":
    main()
