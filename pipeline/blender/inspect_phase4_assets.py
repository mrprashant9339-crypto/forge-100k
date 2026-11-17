"""Inspect real body/garment GLBs before Phase 4 production fitting.

Usage:
  blender -b --python pipeline/blender/inspect_phase4_assets.py -- body.glb garment.glb intake-report.json

Strict checks are intentionally fail-closed. For production garments, the
Blender source .blend may be needed because arbitrary pin/seam vertex groups
are not reliably represented as named groups in glTF.
"""
import bpy
import hashlib
import json
import math
import os
import sys

PIN_NAMES = ("Forge_Cloth_Pin", "Forge_Tear_Pin", "Cloth_Pin", "Pin")
SEAM_NAMES = ("Forge_Tear_Seam",)
MIN_WEIGHT = 1e-5


def cli_args():
    values = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if len(values) != 3:
        raise SystemExit("Usage: -- body.glb garment.glb intake-report.json")
    return [os.path.abspath(value) for value in values]


def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def import_asset(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    return [obj for obj in bpy.data.objects if obj not in before]


def mesh_record(obj):
    issues = []
    mesh = obj.data
    if len(mesh.vertices) < 3 or len(mesh.polygons) < 1:
        issues.append("mesh_empty_or_degenerate")
    if not mesh.uv_layers:
        issues.append("uv_map_missing")
    if not mesh.materials:
        issues.append("material_slot_missing")
    non_finite = 0
    for vertex in mesh.vertices:
        if not all(math.isfinite(float(axis)) for axis in vertex.co):
            non_finite += 1
    if non_finite:
        issues.append("non_finite_vertex_coordinates")
    mesh.calc_loop_triangles()
    degenerate = 0
    for tri in mesh.loop_triangles:
        a, b, c = (mesh.vertices[index].co for index in tri.vertices)
        if (b - a).cross(c - a).length <= 1e-10:
            degenerate += 1
    if degenerate:
        issues.append("degenerate_triangles")
    return {
        "name": obj.name,
        "vertices": len(mesh.vertices),
        "polygons": len(mesh.polygons),
        "triangles": len(mesh.loop_triangles),
        "uv_layers": [layer.name for layer in mesh.uv_layers],
        "materials": [mat.name if mat else None for mat in mesh.materials],
        "vertex_groups": [group.name for group in obj.vertex_groups],
        "degenerate_triangles": degenerate,
        "non_finite_vertices": non_finite,
        "issues": issues
    }


def group_weight_stats(obj, group_names):
    group_map = {group.name: group for group in obj.vertex_groups}
    result = {}
    for name in group_names:
        group = group_map.get(name)
        if group is None:
            result[name] = {"present": False, "weighted_vertices": 0, "min": None, "max": None}
            continue
        weights = []
        for vertex in obj.data.vertices:
            for membership in vertex.groups:
                if membership.group == group.index:
                    weights.append(float(membership.weight))
                    break
        result[name] = {
            "present": True,
            "weighted_vertices": len(weights),
            "min": min(weights) if weights else None,
            "max": max(weights) if weights else None
        }
    return result


def main():
    body_path, garment_path, report_path = cli_args()
    for path in (body_path, garment_path):
        if not os.path.isfile(path):
            raise FileNotFoundError(path)

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    body_objects = import_asset(body_path)
    garment_objects = import_asset(garment_path)
    body_meshes = [obj for obj in body_objects if obj.type == "MESH"]
    garment_meshes = [obj for obj in garment_objects if obj.type == "MESH"]
    body_rigs = [obj for obj in body_objects if obj.type == "ARMATURE"]
    garment_rigs = [obj for obj in garment_objects if obj.type == "ARMATURE"]
    errors, warnings = [], []

    if not body_meshes:
        errors.append("body_mesh_missing")
    if not garment_meshes:
        errors.append("garment_mesh_missing")
    if len(body_rigs) != 1:
        errors.append("body_requires_exactly_one_armature")
    if len(garment_rigs) != 1:
        errors.append("garment_requires_exactly_one_armature")
    body_bones = {bone.name for rig in body_rigs for bone in rig.data.bones}
    garment_bones = {bone.name for rig in garment_rigs for bone in rig.data.bones}
    if body_rigs and garment_rigs:
        missing = sorted(garment_bones - body_bones)
        if missing:
            errors.append("garment_bones_missing_from_body_rig:" + ",".join(missing))
        if not garment_bones:
            errors.append("garment_rig_has_no_bones")

    body_rows = [mesh_record(obj) for obj in body_meshes]
    garment_rows = []
    for obj in garment_meshes:
        record = mesh_record(obj)
        record["armature_modifiers"] = [
            modifier.object.name if modifier.object else None
            for modifier in obj.modifiers if modifier.type == "ARMATURE"
        ]
        record["cloth_groups"] = group_weight_stats(obj, PIN_NAMES + SEAM_NAMES)
        groups = record["cloth_groups"]
        pin = next((groups[name] for name in PIN_NAMES if groups[name]["present"]), None)
        seam = groups[SEAM_NAMES[0]]
        if pin is None or pin["weighted_vertices"] == 0:
            record["issues"].append("authored_cloth_pin_group_missing_or_empty")
        if not seam["present"] or seam["weighted_vertices"] < 2:
            record["issues"].append("authored_tear_seam_group_missing_or_too_small")
        if not record["armature_modifiers"] or not any(record["armature_modifiers"]):
            record["issues"].append("garment_armature_modifier_missing")
        if record["armature_modifiers"] and body_rigs:
            if any(name and name != body_rigs[0].name for name in record["armature_modifiers"]):
                warnings.append(obj.name + ": armature modifier must be remapped by bone name during fitting")
        if any(name == "Forge_Cloth_Pin" for name in groups) and pin:
            if pin["min"] is None or pin["min"] < 0.0 or pin["max"] > 1.0:
                record["issues"].append("pin_weights_out_of_range")
        errors.extend(obj.name + ":" + issue for issue in record["issues"])
        garment_rows.append(record)

    errors.extend("body:" + issue for row in body_rows for issue in row["issues"])
    if not body_meshes or not garment_meshes:
        warnings.append("Upload both body and garment GLBs generated from the same character scale and rest pose")
    report = {
        "schema_version": "1.0",
        "status": "asset_intake_passed" if not errors else "asset_intake_blocked",
        "body": {"path": body_path, "sha256": sha256(body_path), "mesh_count": len(body_meshes),
                 "armatures": [rig.name for rig in body_rigs], "bones": sorted(body_bones), "meshes": body_rows},
        "garment": {"path": garment_path, "sha256": sha256(garment_path), "mesh_count": len(garment_meshes),
                    "armatures": [rig.name for rig in garment_rigs], "bones": sorted(garment_bones), "meshes": garment_rows},
        "errors": sorted(set(errors)),
        "warnings": sorted(set(warnings)),
        "fit_allowed": not errors,
        "production_release_approved": False,
        "notes": [
            "This is an asset intake preflight, not a fit or collision certification.",
            "Keep the source Blender file when arbitrary pin/seam groups are not preserved in GLB.",
            "Passing intake does not replace pose cache baking, collision QA, artist review or target-engine validation."
        ]
    }
    os.makedirs(os.path.dirname(report_path) or ".", exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    print("FORGE_PHASE4_ASSET_INTAKE " + json.dumps(report))
    if errors:
        raise SystemExit("Phase 4 asset intake blocked")


if __name__ == "__main__":
    main()
