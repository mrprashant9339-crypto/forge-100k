"""Create and validate an authored seam-tear workflow for Blender cloth garments.

This is an authored, deterministic tear system: seam edges are split in mesh
topology and a shape key animates the seam opening. It is not a stress-driven
finite-element tear solver. It can be baked with the cloth cache and exported
as a pre-authored tear animation where the target format supports morphs.

Usage (open a .blend first):
  blender -b scene.blend --python authored_cloth_tear.py -- output.blend report.json [gap_m]
"""
import bpy
import bmesh
import json
import math
import os
import sys
from collections import defaultdict
from mathutils import Vector

SEAM_GROUP = "Forge_Tear_Seam"
PIN_GROUPS = ("Forge_Cloth_Pin", "cloth_pin", "pin")
TEAR_KEY = "Forge_Tear_Progress"
EPSILON = 1e-6


def cli():
    values = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if len(values) not in (2, 3):
        raise SystemExit("Usage: -- output.blend report.json [gap_m]")
    gap = float(values[2]) if len(values) == 3 else 0.025
    if not math.isfinite(gap) or gap <= 0.0 or gap > 0.25:
        raise ValueError("gap_m must be finite and in (0, 0.25]")
    return os.path.abspath(values[0]), os.path.abspath(values[1]), gap


def group_weights(obj, group_name):
    group = obj.vertex_groups.get(group_name)
    if group is None:
        return {}
    result = {}
    group_index = group.index
    for vertex in obj.data.vertices:
        membership = next((item for item in vertex.groups if item.group == group_index), None)
        if membership is not None:
            result[vertex.index] = float(membership.weight)
    return result


def pin_report(obj):
    group = next((obj.vertex_groups.get(name) for name in PIN_GROUPS
                  if obj.vertex_groups.get(name) is not None), None)
    if group is None:
        return {"status": "missing", "group": None, "weighted_vertices": 0}
    values = list(group_weights(obj, group.name).values())
    valid = bool(values) and all(math.isfinite(v) and 0.0 <= v <= 1.0 for v in values)
    return {
        "status": "range_validated" if valid else "invalid",
        "group": group.name,
        "weighted_vertices": len(values),
        "minimum": min(values) if values else None,
        "maximum": max(values) if values else None,
        "unweighted_vertices": len(obj.data.vertices) - len(values)
    }


def duplicate_seam_pairs(obj, seam_group):
    weights = group_weights(obj, seam_group)
    buckets = defaultdict(list)
    for vertex in obj.data.vertices:
        if weights.get(vertex.index, 0.0) >= 0.5:
            key = tuple(round(float(c) / EPSILON) for c in vertex.co)
            buckets[key].append(vertex.index)
    pairs = []
    invalid = []
    for indices in buckets.values():
        if len(indices) == 2:
            pairs.append(tuple(sorted(indices)))
        elif len(indices) > 2:
            invalid.append(indices)
    return pairs, invalid


def process_garment(obj, scene, gap):
    if obj.data.shape_keys is not None:
        raise RuntimeError("%s already has shape keys; apply/merge them before seam splitting" % obj.name)
    seam_group = obj.vertex_groups.get(SEAM_GROUP)
    if seam_group is None:
        raise RuntimeError("%s is missing required vertex group %s" % (obj.name, SEAM_GROUP))
    seam_weights = group_weights(obj, SEAM_GROUP)
    seam_indices = {index for index, weight in seam_weights.items() if weight >= 0.5}
    if len(seam_indices) < 2:
        raise RuntimeError("%s seam group needs at least two marked vertices" % obj.name)

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    seam_edges = [
        edge for edge in bm.edges
        if len(edge.link_faces) == 2
        and all(vertex.index in seam_indices for vertex in edge.verts)
    ]
    if not seam_edges:
        bm.free()
        raise RuntimeError("%s seam group does not mark any interior seam edges" % obj.name)
    split_edge_count = len(seam_edges)
    bmesh.ops.split_edges(bm, edges=seam_edges)
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()

    pairs, invalid = duplicate_seam_pairs(obj, SEAM_GROUP)
    if invalid or not pairs:
        raise RuntimeError("%s seam split did not produce unambiguous duplicate vertex pairs" % obj.name)

    basis = obj.shape_key_add(name="Basis", from_mix=False)
    tear = obj.shape_key_add(name=TEAR_KEY, from_mix=False)
    axis = Vector((1.0, 0.0, 0.0))
    half_gap = gap * 0.5
    for left, right in pairs:
        tear.data[left].co = basis.data[left].co - axis * half_gap
        tear.data[right].co = basis.data[right].co + axis * half_gap
    tear.slider_min = 0.0
    tear.slider_max = 1.0
    tear.value = 0.0
    tear.keyframe_insert(data_path="value", frame=scene.frame_start)
    tear.value = 1.0
    tear.keyframe_insert(data_path="value", frame=scene.frame_end)
    tear.value = 0.0

    key_data = obj.data.shape_keys
    if key_data.animation_data and key_data.animation_data.action:
        for fcurve in key_data.animation_data.action.fcurves:
            for point in fcurve.keyframe_points:
                point.interpolation = "LINEAR"

    pin = pin_report(obj)
    row = {
        "mesh": obj.name,
        "status": "authored_tear_ready",
        "seam_group": SEAM_GROUP,
        "seam_marked_vertices_before_split": len(seam_indices),
        "seam_edges_split": split_edge_count,
        "duplicated_seam_vertex_pairs": len(pairs),
        "tear_shape_key": TEAR_KEY,
        "tear_animation_frames": [scene.frame_start, scene.frame_end],
        "tear_gap_m": gap,
        "pin_weights": pin,
        "topology_split": True,
        "tear_progress_animated": bool(key_data.animation_data and key_data.animation_data.action)
    }
    obj["forge_authored_tear_system"] = "seam_split_shape_key_v1"
    obj["forge_tear_seam_group"] = SEAM_GROUP
    obj["forge_tear_shape_key"] = TEAR_KEY
    obj["forge_tear_pair_count"] = len(pairs)
    return row


def main():
    output_blend, report_path, gap = cli()
    scene = bpy.context.scene
    garments = [obj for obj in scene.objects if obj.type == "MESH"
                and any(mod.type == "CLOTH" for mod in obj.modifiers)]
    if not garments:
        raise RuntimeError("No mesh with a Cloth modifier was found")
    rows, issues = [], []
    for garment in garments:
        try:
            rows.append(process_garment(garment, scene, gap))
        except Exception as exc:
            issues.append("%s: %s" % (garment.name, exc))
    status = "authored_tear_ready" if rows and not issues else "authored_tear_blocked"
    report = {
        "schema": "forge.authored-cloth-tear.v1",
        "status": status,
        "workflow": "authored_seam_split_shape_key",
        "is_physics_driven_tear_solver": False,
        "frame_range": [scene.frame_start, scene.frame_end],
        "garments": rows,
        "issues": issues,
        "limitations": [
            "This is an authored seam-opening animation, not a stress-driven tear solver",
            "The seam path must be marked by the garment author in Forge_Tear_Seam",
            "Artist review is required for seam placement, fabric behavior and target-engine playback"
        ]
    }
    os.makedirs(os.path.dirname(output_blend) or ".", exist_ok=True)
    os.makedirs(os.path.dirname(report_path) or ".", exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=output_blend)
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    print("FORGE_AUTHORED_CLOTH_TEAR " + json.dumps(report))
    if issues:
        raise SystemExit("Authored cloth tear setup failed: " + "; ".join(issues))


if __name__ == "__main__":
    main()
