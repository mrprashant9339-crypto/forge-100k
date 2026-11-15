"""Rigging QA across animation samples for every Forge rig profile.

Checks skin influence limits, finite/nonnegative normalized weights, armature
binding, evaluated geometry health, animation movement and sampled pose bounds.
This is an automated prototype gate, not an artist or engine certification.
"""
import bpy
import json
import math
import os
import sys

def args_after_separator():
    argv = sys.argv
    return argv[argv.index("--") + 1:] if "--" in argv else []

def finite_vector(v):
    return all(math.isfinite(float(x)) for x in v)

def main():
    args = args_after_separator()
    if len(args) != 2:
        raise SystemExit("Usage: rig_deformation_qa.py -- input.glb report.json")
    source, report_path = map(os.path.abspath, args)
    if not os.path.isfile(source):
        raise FileNotFoundError(source)

    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=source)
    scene = bpy.context.scene
    meshes = [o for o in scene.objects if o.type == "MESH"]
    armatures = [o for o in scene.objects if o.type == "ARMATURE"]
    issues = []
    if not meshes:
        issues.append("No mesh objects")
    if len(armatures) != 1:
        issues.append("Expected exactly one armature")

    weight_reports = []
    for obj in meshes:
        groups = {g.index: g.name for g in obj.vertex_groups}
        max_influences = 0
        max_sum_error = 0.0
        weighted = 0
        for vertex in obj.data.vertices:
            values = [float(g.weight) for g in vertex.groups if g.weight > 1e-8]
            if any((not math.isfinite(w)) or w < 0.0 for w in values):
                issues.append(f"{obj.name}: invalid vertex weight")
            if values:
                weighted += 1
                max_influences = max(max_influences, len(values))
                error = abs(sum(values) - 1.0)
                max_sum_error = max(max_sum_error, error)
                if error > 1e-3:
                    issues.append(f"{obj.name}: non-normalized vertex weights")
                if len(values) > 4:
                    issues.append(f"{obj.name}: more than four influences")
        if weighted == 0:
            issues.append(f"{obj.name}: no weighted vertices")
        if not any(m.type == "ARMATURE" for m in obj.modifiers):
            issues.append(f"{obj.name}: missing armature modifier")
        if not obj.vertex_groups:
            issues.append(f"{obj.name}: missing vertex groups")
        weight_reports.append({
            "mesh": obj.name, "weighted_vertices": weighted,
            "max_influences": max_influences,
            "max_weight_sum_error": max_sum_error,
            "vertex_group_count": len(groups)
        })

    if armatures:
        arm = armatures[0]
        if len(arm.data.bones) == 0:
            issues.append("Armature has no bones")
        if not arm.animation_data or not arm.animation_data.action:
            issues.append("Armature has no active animation")
        action = arm.animation_data.action if arm.animation_data else None
        frames = {scene.frame_start, scene.frame_end}
        if action:
            for curve in action.fcurves:
                for key in curve.keyframe_points:
                    frames.add(int(round(key.co.x)))
        frames.update({1, 8, 16, 23, 30})
        frames = sorted(f for f in frames if scene.frame_start <= f <= scene.frame_end)
    else:
        frames = [scene.frame_start]

    pose_reports = []
    baseline = {}
    any_movement = False
    for frame in frames:
        scene.frame_set(frame)
        depsgraph = bpy.context.evaluated_depsgraph_get()
        frame_report = {"frame": frame, "meshes": []}
        for obj in meshes:
            evaluated = obj.evaluated_get(depsgraph)
            mesh = evaluated.to_mesh()
            coords = [evaluated.matrix_world @ v.co for v in mesh.vertices]
            finite_count = sum(1 for p in coords if finite_vector(p))
            if finite_count != len(coords):
                issues.append(f"{obj.name}@{frame}: non-finite vertex coordinates")
            if not coords:
                issues.append(f"{obj.name}@{frame}: empty evaluated mesh")
            if coords:
                mins = [min(p[i] for p in coords) for i in range(3)]
                maxs = [max(p[i] for p in coords) for i in range(3)]
                extents = [maxs[i] - mins[i] for i in range(3)]
                if max(extents) <= 1e-7:
                    issues.append(f"{obj.name}@{frame}: collapsed geometry")
            mesh.calc_loop_triangles()
            degenerate = sum(1 for tri in mesh.loop_triangles if tri.area <= 1e-12)
            if mesh.loop_triangles and degenerate == len(mesh.loop_triangles):
                issues.append(f"{obj.name}@{frame}: all triangles degenerate")
            previous = baseline.get(obj.name)
            if previous is None:
                baseline[obj.name] = coords
            elif len(previous) == len(coords):
                if any((a - b).length > 1e-5 for a, b in zip(previous, coords)):
                    any_movement = True
            frame_report["meshes"].append({
                "name": obj.name, "vertices": len(coords),
                "triangles": len(mesh.loop_triangles),
                "degenerate_triangles": degenerate,
                "bounds_extent": extents if coords else None
            })
            evaluated.to_mesh_clear()
        pose_reports.append(frame_report)

    if len(frames) > 1 and not any_movement:
        issues.append("No evaluated mesh movement across sampled animation frames")

    report = {
        "status": "pass" if not issues else "fail",
        "source": source,
        "armature_count": len(armatures),
        "bone_count": len(armatures[0].data.bones) if armatures else 0,
        "sampled_frames": frames,
        "weight_checks": weight_reports,
        "pose_checks": pose_reports,
        "issues": issues,
        "artist_review_required": True,
        "engine_certified": False
    }
    os.makedirs(os.path.dirname(report_path) or ".", exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    print("FORGE_RIG_DEFORMATION_QA " + json.dumps(report))
    if issues:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
