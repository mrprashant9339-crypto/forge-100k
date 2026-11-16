"""Pose-driven garment/body and garment self-intersection QA.

Usage:
  blender --background scene.blend --python pipeline/blender/pose_cloth_qa.py -- report.json [--require-clean]

The worker evaluates actual skeletal Actions on the imported armature(s). It is
a sampled geometric preflight; it is not continuous collision detection.
"""
import bpy
import json
import math
import os
import sys

from cloth_integrity_qa import world_mesh, inside_closed_mesh, overlap_pairs

REQUIRED = {
    "walking": ("walk",),
    "running": ("run",),
    "jumping": ("jump",),
    "combat": ("combat", "fight", "attack"),
}


def cli():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    require_clean = "--require-clean" in argv
    values = [value for value in argv if value != "--require-clean"]
    if len(values) != 1:
        raise SystemExit("Usage: pose_cloth_qa.py -- report.json [--require-clean]")
    return os.path.abspath(values[0]), require_clean


def is_garment(obj):
    return bool(obj.get("forge_fit_stage")) or obj.name.lower().startswith(
        ("garment", "cloth", "outfit")
    )


def finite_bounds(snapshot):
    return snapshot["finite"] and snapshot["vertex_count"] > 0 and snapshot["polygon_count"] > 0


def main():
    report_path, require_clean = cli()
    scene = bpy.context.scene
    armatures = [obj for obj in scene.objects if obj.type == "ARMATURE"]
    meshes = [obj for obj in scene.objects if obj.type == "MESH"]
    garments = [obj for obj in meshes if is_garment(obj)]
    bodies = [obj for obj in meshes if obj not in garments]
    if not armatures or not garments or not bodies:
        raise RuntimeError("Pose QA requires an armature, garment mesh and body collider mesh")

    actions = list(bpy.data.actions)
    action_by_kind = {}
    for kind, terms in REQUIRED.items():
        candidates = [action for action in actions
                      if any(term in action.name.lower() for term in terms)]
        action_by_kind[kind] = sorted(candidates, key=lambda action: action.name)[0] if candidates else None

    issues = []
    clips = []
    aggregate = {
        "sampled_pose_frames": 0,
        "body_inside_vertices": 0,
        "body_surface_triangle_pairs": 0,
        "self_intersection_triangle_pairs": 0,
    }
    armature = armatures[0]
    armature.animation_data_create()

    for kind, action in action_by_kind.items():
        if action is None:
            issues.append("missing_%s_action" % kind)
            clips.append({"kind": kind, "status": "missing_action", "frames_sampled": 0})
            continue
        armature.animation_data.action = action
        start = max(scene.frame_start, int(math.floor(action.frame_range[0])))
        end = min(scene.frame_end, int(math.ceil(action.frame_range[1])))
        if end < start:
            start, end = int(math.floor(action.frame_range[0])), int(math.ceil(action.frame_range[1]))
        clip_counts = {
            "body_inside_vertices": 0,
            "body_surface_triangle_pairs": 0,
            "self_intersection_triangle_pairs": 0,
        }
        frame_records = []
        for frame in range(start, end + 1):
            scene.frame_set(frame)
            depsgraph = bpy.context.evaluated_depsgraph_get()
            body_snaps = [(obj.name, world_mesh(obj, depsgraph)) for obj in bodies]
            garment_snaps = [(obj.name, world_mesh(obj, depsgraph)) for obj in garments]
            body_snaps = [(name, snap) for name, snap in body_snaps if finite_bounds(snap)]
            garment_snaps = [(name, snap) for name, snap in garment_snaps if finite_bounds(snap)]
            if len(body_snaps) != len(bodies) or len(garment_snaps) != len(garments):
                issues.append("%s@%d: invalid evaluated mesh geometry" % (kind, frame))
                continue
            body_inside = 0
            body_pairs = 0
            self_pairs = 0
            for garment_name, garment_snap in garment_snaps:
                for _, body_snap in body_snaps:
                    body_inside += sum(
                        1 for point in garment_snap["vertices"]
                        if inside_closed_mesh(point, body_snap["bvh"])
                    )
                    body_pairs += len(overlap_pairs(garment_snap, body_snap))
                self_pairs += len(overlap_pairs(garment_snap, garment_snap, same_mesh=True))
            clip_counts["body_inside_vertices"] += body_inside
            clip_counts["body_surface_triangle_pairs"] += body_pairs
            clip_counts["self_intersection_triangle_pairs"] += self_pairs
            aggregate["sampled_pose_frames"] += 1
            aggregate["body_inside_vertices"] += body_inside
            aggregate["body_surface_triangle_pairs"] += body_pairs
            aggregate["self_intersection_triangle_pairs"] += self_pairs
            frame_records.append({
                "frame": frame,
                "body_inside_vertices": body_inside,
                "body_surface_triangle_pairs": body_pairs,
                "self_intersection_triangle_pairs": self_pairs,
            })
        clip_issues = []
        for key, label in (
            ("body_inside_vertices", "body_penetration"),
            ("body_surface_triangle_pairs", "garment_body_triangle_intersection"),
            ("self_intersection_triangle_pairs", "garment_self_intersection"),
        ):
            if clip_counts[key]:
                clip_issues.append(label)
        if not frame_records:
            clip_issues.append("no_pose_frames_evaluated")
        if clip_issues:
            issues.extend("%s: %s" % (kind, label) for label in clip_issues)
        clips.append({
            "kind": kind,
            "action": action.name,
            "frame_range": [start, end],
            "frames_sampled": len(frame_records),
            "aggregate": clip_counts,
            "issues": clip_issues,
            "status": "sampled_clear" if not clip_issues else "findings",
            "frame_checks": frame_records,
        })

    coverage = {kind: action is not None for kind, action in action_by_kind.items()}
    report = {
        "schema": "forge.pose-cloth-qa.v1",
        "status": "pose_cloth_qa_passed" if not issues else "pose_cloth_qa_findings",
        "pose_coverage": coverage,
        "pose_coverage_complete": all(coverage.values()),
        "armature": armature.name,
        "garments": [obj.name for obj in garments],
        "body_colliders": [obj.name for obj in bodies],
        "clips": clips,
        "aggregate": aggregate,
        "issues": issues,
        "sampled_skeletal_actions": True,
        "continuous_collision_detection": False,
        "collision_free_certified": False,
        "artist_review_required": True,
        "engine_certified": False,
        "limitations": [
            "Only named skeletal actions and integer frames are sampled",
            "Body-inside parity requires closed, consistently oriented body collider meshes",
            "Sampled pose QA does not replace baked cloth-cache QA or continuous collision detection",
            "Visual fit, cloth drape, tearing and target-engine behavior still require artist review",
        ],
    }
    os.makedirs(os.path.dirname(report_path) or ".", exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    print("FORGE_POSE_CLOTH_QA " + json.dumps(report))
    if require_clean and issues:
        raise SystemExit("Pose cloth QA release gate failed: " + "; ".join(issues))


if __name__ == "__main__":
    main()
