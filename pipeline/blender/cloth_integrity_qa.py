"""Full-frame cloth integrity QA in world space.

Usage:
  blender -b cloth-sim.blend --python pipeline/blender/cloth_integrity_qa.py -- report.json [sample_step]

Checks baked cache presence, finite evaluated geometry, body/cloth triangle
intersections, garment vertices inside closed body meshes, non-adjacent garment
triangle overlaps, topology stability and pin weights. These are geometric
preflight checks, not a mathematical proof of continuous collision freedom.
"""
import bpy
import json
import math
import os
import sys
from mathutils import Vector
from mathutils.bvhtree import BVHTree

REQUIRED_POSE_TERMS = {
    "walking": ("walk",),
    "running": ("run",),
    "jumping": ("jump",),
    "combat": ("combat", "fight", "attack")
}

def cli():
    argv = sys.argv
    values = argv[argv.index("--") + 1:] if "--" in argv else []
    if len(values) not in (1, 2):
        raise SystemExit("Usage: cloth_integrity_qa.py -- report.json [sample_step]")
    step = int(values[1]) if len(values) == 2 else 1
    if step < 1 or step > 30:
        raise ValueError("sample_step must be in 1..30")
    return os.path.abspath(values[0]), step

def world_mesh(obj, depsgraph):
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        matrix = evaluated.matrix_world.copy()
        vertices = [matrix @ vertex.co for vertex in mesh.vertices]
        # Explicit triangulation keeps BVH face indices aligned with exact tests.
        triangles = []
        for poly in mesh.polygons:
            indices = tuple(poly.vertices)
            for index in range(1, len(indices) - 1):
                triangles.append((indices[0], indices[index], indices[index + 1]))
        bvh = BVHTree.FromPolygons(vertices, triangles, all_triangles=True) if triangles else None
        return {
            "vertices": vertices,
            "polygons": triangles,
            "bvh": bvh,
            "vertex_count": len(vertices),
            "edge_count": len(mesh.edges),
            "polygon_count": len(mesh.polygons),
            "finite": all(math.isfinite(float(c)) for point in vertices for c in point),
            "bounds": [
                [min(point[i] for point in vertices) for i in range(3)],
                [max(point[i] for point in vertices) for i in range(3)]
            ] if vertices else None
        }
    finally:
        evaluated.to_mesh_clear()

def inside_closed_mesh(point, bvh):
    if bvh is None:
        return False
    direction = Vector((1.0, 0.000173, 0.000319)).normalized()
    origin = point.copy()
    hits = 0
    for _ in range(256):
        location, normal, face_index, distance = bvh.ray_cast(origin, direction, 1.0e6)
        if location is None:
            break
        hits += 1
        origin = location + direction * 1.0e-5
    return hits % 2 == 1

def overlap_pairs(a, b, same_mesh=False):
    if a["bvh"] is None or b["bvh"] is None:
        return []
    pairs = []
    for face_a, face_b in a["bvh"].overlap(b["bvh"]):
        if same_mesh:
            if face_a >= face_b:
                continue
            if set(a["polygons"][face_a]).intersection(a["polygons"][face_b]):
                continue
        tri_a = tuple(a["vertices"][index] for index in a["polygons"][face_a])
        tri_b = tuple(b["vertices"][index] for index in b["polygons"][face_b])
        # BVH overlap is a conservative candidate; report it for visual review.
        # Blender's bundled mathutils has no stable 3D triangle intersection API.
        pairs.append((face_a, face_b))
    return pairs

def inventory_actions(scene, armatures):
    names = set()
    for arm in armatures:
        if arm.animation_data:
            if arm.animation_data.action:
                names.add(arm.animation_data.action.name)
            for track in arm.animation_data.nla_tracks:
                names.add(track.name)
                for strip in track.strips:
                    names.add(strip.name)
                    if strip.action:
                        names.add(strip.action.name)
    return sorted(names)

def main():
    report_path, step = cli()
    scene = bpy.context.scene
    garments = [
        obj for obj in scene.objects if obj.type == "MESH"
        and any(mod.type == "CLOTH" for mod in obj.modifiers)
    ]
    bodies = [
        obj for obj in scene.objects if obj.type == "MESH"
        and any(mod.type == "COLLISION" for mod in obj.modifiers)
    ]
    armatures = [obj for obj in scene.objects if obj.type == "ARMATURE"]
    if not garments or not bodies:
        raise RuntimeError("Expected at least one CLOTH garment and one COLLISION body mesh")

    issues = []
    warnings = []
    cache_checks = []
    for garment in garments:
        for modifier in [m for m in garment.modifiers if m.type == "CLOTH"]:
            cache = modifier.point_cache
            is_baked = bool(cache.is_baked)
            cache_checks.append({
                "garment": garment.name, "modifier": modifier.name,
                "is_baked": is_baked, "frame_start": cache.frame_start,
                "frame_end": cache.frame_end
            })
            if not is_baked:
                issues.append("%s/%s: point cache is not baked" % (garment.name, modifier.name))

    action_names = inventory_actions(scene, armatures)
    normalized_names = " ".join(action_names).lower()
    pose_coverage = {
        label: any(term in normalized_names for term in terms)
        for label, terms in REQUIRED_POSE_TERMS.items()
    }
    for label, covered in pose_coverage.items():
        if not covered:
            warnings.append("No named %s action/strip found; supply and review this pose in the animation scene" % label)

    topology_baseline = {}
    frame_rows = []
    aggregate = {
        garment.name: {
            "body_inside_vertices": 0,
            "body_surface_triangle_pairs": 0,
            "self_intersection_triangle_pairs": 0,
            "sampled_frames": 0
        } for garment in garments
    }
    frames = list(range(scene.frame_start, scene.frame_end + 1, step))
    if frames[-1] != scene.frame_end:
        frames.append(scene.frame_end)

    for frame in frames:
        scene.frame_set(frame)
        depsgraph = bpy.context.evaluated_depsgraph_get()
        body_snapshots = [(body.name, world_mesh(body, depsgraph)) for body in bodies]
        for garment in garments:
            cloth = world_mesh(garment, depsgraph)
            row = {
                "frame": frame, "garment": garment.name,
                "vertices": cloth["vertex_count"], "edges": cloth["edge_count"],
                "polygons": cloth["polygon_count"], "finite": cloth["finite"],
                "bounds_world": cloth["bounds"],
                "body_inside_vertices": 0,
                "body_surface_triangle_pairs": 0,
                "self_intersection_triangle_pairs": 0
            }
            if not cloth["finite"] or not cloth["vertices"] or not cloth["polygons"]:
                issues.append("%s@%d: invalid or empty evaluated mesh" % (garment.name, frame))

            topology = (cloth["vertex_count"], cloth["edge_count"], cloth["polygon_count"])
            if garment.name not in topology_baseline:
                topology_baseline[garment.name] = topology
            elif topology != topology_baseline[garment.name]:
                issues.append("%s@%d: evaluated topology changed; possible mesh integrity failure" % (garment.name, frame))

            inside_count = 0
            surface_pairs = 0
            for _, body in body_snapshots:
                if body["bvh"] is None:
                    continue
                inside_count += sum(1 for point in cloth["vertices"] if inside_closed_mesh(point, body["bvh"]))
                surface_pairs += len(overlap_pairs(cloth, body, same_mesh=False))
            self_pairs = len(overlap_pairs(cloth, cloth, same_mesh=True))
            row["body_inside_vertices"] = inside_count
            row["body_surface_triangle_pairs"] = surface_pairs
            row["self_intersection_triangle_pairs"] = self_pairs
            aggregate[garment.name]["body_inside_vertices"] += inside_count
            aggregate[garment.name]["body_surface_triangle_pairs"] += surface_pairs
            aggregate[garment.name]["self_intersection_triangle_pairs"] += self_pairs
            aggregate[garment.name]["sampled_frames"] += 1
            if inside_count:
                issues.append("%s@%d: %d garment vertices inside body collision mesh(es)" % (garment.name, frame, inside_count))
            if surface_pairs:
                issues.append("%s@%d: %d garment/body triangle intersections" % (garment.name, frame, surface_pairs))
            if self_pairs:
                issues.append("%s@%d: %d non-adjacent garment triangle overlaps" % (garment.name, frame, self_pairs))
            frame_rows.append(row)

    pin_checks = []
    for garment in garments:
        cloth_modifiers = [m for m in garment.modifiers if m.type == "CLOTH"]
        for modifier in cloth_modifiers:
            group_name = modifier.settings.vertex_group_mass
            group = garment.vertex_groups.get(group_name) if group_name else None
            weights = []
            if group:
                for vertex in garment.data.vertices:
                    try:
                        weights.append(float(group.weight(vertex.index)))
                    except RuntimeError:
                        pass
                if not weights:
                    issues.append("%s: configured pin group has no weighted vertices" % garment.name)
                elif any(not math.isfinite(w) or w < 0.0 or w > 1.0 for w in weights):
                    issues.append("%s: pin weights outside finite [0,1] range" % garment.name)
            else:
                issues.append("%s: no pin group configured; pin-weight validation is required" % garment.name)
            pin_checks.append({
                "garment": garment.name, "group": group_name or None,
                "weighted_vertices": len(weights),
                "minimum": min(weights) if weights else None,
                "maximum": max(weights) if weights else None,
                "status": "range_validated" if weights else "not_configured"
            })

    status = "cloth_integrity_preflight_passed" if not issues else "cloth_integrity_issues_found"
    report = {
        "schema": "forge.cloth-integrity-report.v1",
        "status": status,
        "frame_range": [scene.frame_start, scene.frame_end],
        "sample_step": step,
        "sampled_frames": frames,
        "cache_checks": cache_checks,
        "pose_action_inventory": action_names,
        "named_pose_coverage": pose_coverage,
        "pose_coverage_complete": all(pose_coverage.values()),
        "garment_aggregate": aggregate,
        "frame_checks": frame_rows,
        "pin_weight_checks": pin_checks,
        "issues": issues,
        "warnings": warnings,
        "tearing_detection": {
            "topology_stability_checked": True,
            "topology_change_detected": any("topology changed" in issue for issue in issues),
            "physical_fabric_tear_solver_available": False,
            "note": "Topology stability catches mesh changes; Blender cloth does not physically tear fabric without a dedicated tear system."
        },
        "continuous_collision_detection": False,
        "collision_free_certified": False,
        "self_intersection_certified": False,
        "artist_review_required": True,
        "engine_certified": False,
        "limitations": [
            "Frame sampling cannot prove collision-free motion between sampled frames",
            "Ray parity assumes closed, consistently oriented body collision meshes",
            "Triangle overlap is a geometric candidate detector; inspect flagged frames visually",
            "Named action coverage does not prove pose quality or that all actions were simulated",
            "Physical cloth tearing requires authored tear topology/solver not provided by Blender cloth"
        ]
    }
    os.makedirs(os.path.dirname(report_path) or ".", exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    print("FORGE_CLOTH_INTEGRITY_QA " + json.dumps(report))
    if issues:
        raise SystemExit(1)

if __name__ == "__main__":
    main()
