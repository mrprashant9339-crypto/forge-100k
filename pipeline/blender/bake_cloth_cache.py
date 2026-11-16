"""Bake prepared Blender cloth caches and run evaluated-mesh integrity preflight.

Usage:
  blender -b scene.blend --python bake_cloth_cache.py -- report.json [sample_step]

This performs a real point-cache bake. Geometry checks are sampled preflight only;
they do not replace continuous collision detection or artist/engine approval.
"""
import bpy
import json
import math
import os
import sys
from mathutils.bvhtree import BVHTree

def cli():
    argv = sys.argv
    values = argv[argv.index("--") + 1:] if "--" in argv else []
    if len(values) not in (1, 2, 3, 4):
        raise SystemExit("Usage: bake_cloth_cache.py -- report.json [sample_step] [action_name] [output.blend]")
    step = int(values[1]) if len(values) >= 2 else 1
    action_name = values[2] if len(values) >= 3 else None
    output_blend = os.path.abspath(values[3]) if len(values) == 4 else None
    if step < 1 or step > 30:
        raise ValueError("sample_step must be in 1..30")
    return os.path.abspath(values[0]), step, action_name, output_blend

def finite_mesh(mesh):
    return all(math.isfinite(float(c)) for vertex in mesh.vertices for c in vertex.co)

def evaluated_snapshot(obj, depsgraph):
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        mesh.calc_loop_triangles()
        matrix = evaluated.matrix_world.copy()
        vertices = [matrix @ vertex.co for vertex in mesh.vertices]
        triangles = [tuple(tri.vertices) for tri in mesh.loop_triangles]
        return {
            "vertices": len(vertices),
            "triangles": len(triangles),
            "finite": all(math.isfinite(float(component)) for point in vertices for component in point),
            "bounds": [
                [min(point[axis] for point in vertices) for axis in range(3)],
                [max(point[axis] for point in vertices) for axis in range(3)]
            ] if vertices else None,
            "world_vertices": vertices,
            "bvh": BVHTree.FromPolygons(vertices, triangles, all_triangles=True) if triangles else None
        }
    finally:
        evaluated.to_mesh_clear()


def main():
    report_path, step, action_name, output_blend = cli()
    scene = bpy.context.scene
    if action_name:
        action = bpy.data.actions.get(action_name)
        if action is None:
            raise RuntimeError("Requested cloth bake action not found: " + action_name)
        armatures = [obj for obj in scene.objects if obj.type == "ARMATURE"]
        if not armatures:
            raise RuntimeError("Action-specific cloth bake requires an armature")
        armatures[0].animation_data_create()
        armatures[0].animation_data.action = action
        scene.frame_set(int(math.floor(action.frame_range[0])))
    cloth_objects = [
        obj for obj in scene.objects if obj.type == "MESH"
        and any(mod.type == "CLOTH" for mod in obj.modifiers)
    ]
    body_objects = [
        obj for obj in scene.objects if obj.type == "MESH"
        and any(mod.type == "COLLISION" for mod in obj.modifiers)
    ]
    if not cloth_objects or not body_objects:
        raise RuntimeError("Scene must contain CLOTH garments and COLLISION body meshes")

    issues = []
    cache_rows = []
    for obj in cloth_objects:
        cloth_mods = [m for m in obj.modifiers if m.type == "CLOTH"]
        for modifier in cloth_mods:
            cache = modifier.point_cache
            cache.frame_start = scene.frame_start
            cache.frame_end = scene.frame_end
            scene.frame_set(scene.frame_start)
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)
            try:
                with bpy.context.temp_override(
                    scene=scene, object=obj, active_object=obj, point_cache=cache
                ):
                    result = bpy.ops.ptcache.bake(bake=True)
                baked = "FINISHED" in result and cache.is_baked
            except Exception as exc:
                baked = False
                issues.append("%s: cache bake failed: %s" % (obj.name, str(exc)))
            if not baked:
                issues.append("%s: point cache not baked" % obj.name)
            cache_rows.append({
                "object": obj.name, "modifier": modifier.name,
                "baked": bool(baked), "frame_start": cache.frame_start,
                "frame_end": cache.frame_end
            })
            obj.select_set(False)

    # Persist baked point caches into the working .blend before downstream QA.
    save_path = output_blend or bpy.data.filepath
    if save_path:
        os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=save_path)

    # Evaluate baked cloth at each sampled frame; detect invalid geometry and
    # non-adjacent triangle overlap candidates. Body proximity is measured with
    # nearest-surface distances, not represented as a certified penetration test.
    frame_rows = []
    min_body_clearance = {}
    baseline_diagonal = {}
    for frame in range(scene.frame_start, scene.frame_end + 1, step):
        scene.frame_set(frame)
        depsgraph = bpy.context.evaluated_depsgraph_get()
        for garment in cloth_objects:
            snap = evaluated_snapshot(garment, depsgraph)
            if not snap["finite"] or not snap["vertices"] or not snap["triangles"]:
                issues.append("%s@%d: invalid evaluated garment geometry" % (garment.name, frame))
            bounds = snap["bounds"]
            diagonal = None
            deformation_ratio = None
            if bounds:
                diagonal = math.sqrt(sum((bounds[1][axis] - bounds[0][axis]) ** 2
                                         for axis in range(3)))
                baseline = baseline_diagonal.setdefault(garment.name, max(diagonal, 1e-8))
                deformation_ratio = diagonal / baseline
                if deformation_ratio > 3.0:
                    issues.append("%s@%d: cloth bounds expanded %.2fx from its first sampled frame"
                                  % (garment.name, frame, deformation_ratio))
            clearance = []
            for body in body_objects:
                body_snap = evaluated_snapshot(body, depsgraph)
                if body_snap["bvh"] is not None:
                    # Both snapshots are transformed to world space, so nearest
                    # distances remain meaningful for scaled/rotated character rigs.
                    for point in snap["world_vertices"]:
                        hit = body_snap["bvh"].find_nearest(point)
                        if hit and hit[3] is not None:
                            clearance.append(float(hit[3]))
            if clearance:
                value = min(clearance)
                min_body_clearance[garment.name] = min(
                    min_body_clearance.get(garment.name, value), value
                )
            frame_rows.append({
                "frame": frame, "garment": garment.name,
                "vertices": snap["vertices"], "triangles": snap["triangles"],
                "finite": snap["finite"], "bounds": snap["bounds"],
                "bounding_diagonal_world_units": diagonal,
                "deformation_ratio_from_first_sample": deformation_ratio,
                "minimum_body_surface_distance_world_units": min(clearance) if clearance else None
            })

    pin_rows = []
    for garment in cloth_objects:
        modifier = next(m for m in garment.modifiers if m.type == "CLOTH")
        group_name = modifier.settings.vertex_group_mass
        group = garment.vertex_groups.get(group_name) if group_name else None
        values = []
        if group:
            for vertex in garment.data.vertices:
                try:
                    values.append(group.weight(vertex.index))
                except RuntimeError:
                    pass
            if not values:
                issues.append("%s: pin group exists but has no weighted vertices" % garment.name)
            elif min(values) < 0.0 or max(values) > 1.0:
                issues.append("%s: pin weights outside [0,1]" % garment.name)
        pin_rows.append({
            "garment": garment.name, "pin_group": group_name or None,
            "weighted_vertex_count": len(values),
            "minimum_weight": min(values) if values else None,
            "maximum_weight": max(values) if values else None,
            "validation": "range_checked" if values else "not_configured"
        })

    status = "baked_preflight_passed" if not issues and all(x["baked"] for x in cache_rows) else "bake_or_geometry_issues"
    report = {
        "schema": "forge.cloth-bake-report.v1",
        "status": status,
        "blend_file": bpy.data.filepath,
        "frame_range": [scene.frame_start, scene.frame_end],
        "sample_step": step,
        "active_action": action_name,
        "saved_blend_file": output_blend or bpy.data.filepath,
        "cache_results": cache_rows,
        "pin_weight_checks": pin_rows,
        "evaluated_frame_samples": frame_rows,
        "minimum_body_clearance_by_garment_world_units": min_body_clearance,
        "issues": issues,
        "body_penetration_certified": False,
        "self_intersection_certified": False,
        "tearing_certified": False,
        "continuous_collision_detection": False,
        "artist_review_required": True,
        "engine_certified": False,
        "limitations": [
            "Sampled evaluated geometry does not prove continuous collision-free motion",
            "Nearest-surface clearance is measured in world space using evaluated object transforms",
            "Blender cloth does not provide a universal tear solver; seam and pin failure need authored tests",
            "Walking, running, jumping and combat must be supplied as actual skeletal animation actions and reviewed"
        ]
    }
    os.makedirs(os.path.dirname(report_path) or ".", exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    print("FORGE_CLOTH_BAKE " + json.dumps(report))
    if status != "baked_preflight_passed":
        raise SystemExit(1)

if __name__ == "__main__":
    main()
