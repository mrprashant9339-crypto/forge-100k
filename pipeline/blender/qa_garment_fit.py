"""Post-fit garment geometry and metadata QA for Forge 100K.

Usage:
  blender -b --python pipeline/blender/qa_garment_fit.py -- fitted.glb fit-report.json qa.json

This validates exported geometry and semantic fit metadata. It does not claim
cloth simulation, collision-free posing, or production body-intersection proof.
"""
import bpy
import json
import math
import os
import sys

def args_after_separator():
    argv = sys.argv
    return argv[argv.index("--") + 1:] if "--" in argv else []

def main():
    args = args_after_separator()
    if len(args) != 3:
        raise SystemExit("Usage: qa_garment_fit.py -- fitted.glb fit-report.json qa.json")
    glb_path, fit_path, output_path = map(os.path.abspath, args)
    for path in (glb_path, fit_path):
        if not os.path.isfile(path):
            raise FileNotFoundError(path)
    with open(fit_path, encoding="utf-8") as handle:
        fit = json.load(handle)
    expected = fit.get("garments", [])
    if fit.get("status") != "proxy_fit_complete" or not expected:
        raise ValueError("Input fit report is not a completed garment fit")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=glb_path)
    meshes = {obj.name: obj for obj in bpy.context.scene.objects if obj.type == "MESH"}
    records = []
    failures = []
    for item in expected:
        name = item.get("mesh")
        obj = meshes.get(name)
        issues = []
        if obj is None:
            failures.append({"mesh": name, "issues": ["mesh_missing_after_export"]})
            continue
        mesh = obj.data
        if len(mesh.vertices) < 3 or len(mesh.polygons) < 1:
            issues.append("empty_or_degenerate_mesh")
        coords = [obj.matrix_world @ vertex.co for vertex in mesh.vertices]
        if any(not all(math.isfinite(float(axis)) for axis in co) for co in coords):
            issues.append("non_finite_vertex_coordinate")
        if coords:
            bounds = {
                "min": [min(float(v[i]) for v in coords) for i in range(3)],
                "max": [max(float(v[i]) for v in coords) for i in range(3)]
            }
            if any(bounds["max"][i] - bounds["min"][i] <= 1e-6 for i in range(3)):
                issues.append("collapsed_bounds_axis")
        else:
            bounds = None
        mesh.calc_loop_triangles()
        degenerate = 0
        for tri in mesh.loop_triangles:
            a, b, c = (mesh.vertices[index].co for index in tri.vertices)
            if (b - a).cross(c - a).length <= 1e-10:
                degenerate += 1
        if degenerate:
            issues.append("degenerate_triangles")
        # glTF 2.0 does not preserve Blender vertex-group definitions as
        # editable groups. Validate semantic zones against the fit-report
        # sidecar, which is authoritative for this prototype stage.
        body_zones = item.get("body_zones", {})
        if not isinstance(body_zones, dict) or not body_zones:
            issues.append("missing_semantic_body_zone_metadata")
        if not mesh.materials:
            issues.append("missing_material_slots")
        if item.get("fit_method") != "nearest_surface_shrinkwrap":
            issues.append("unexpected_fit_method")
        record = {
            "mesh": name,
            "vertex_count": len(mesh.vertices),
            "polygon_count": len(mesh.polygons),
            "triangle_count": len(mesh.loop_triangles),
            "degenerate_triangle_count": degenerate,
            "bounds_world": bounds,
            "body_zones": body_zones,
            "material_slot_count": len(mesh.materials),
            "issues": issues,
            "status": "failed" if issues else "geometry_validated"
        }
        records.append(record)
        if issues:
            failures.append({"mesh": name, "issues": issues})
    report = {
        "schema_version": "1.0",
        "status": "failed" if failures else "geometry_qa_passed",
        "input": glb_path,
        "fit_report": fit_path,
        "garment_count": len(expected),
        "validated_count": len(records),
        "garments": records,
        "failures": failures,
        "collision_free_pose_certified": False,
        "cloth_simulation_certified": False,
        "artist_review_required": True,
        "limitations": [
            "Static exported geometry only; no pose-space collision sampling",
            "No cloth simulation or runtime physics validation",
            "No certified self-intersection or body-clipping test",
            "Requires artist review in target DCC and engine"
        ]
    }
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    print("FORGE_GARMENT_QA " + json.dumps(report))
    if failures:
        raise SystemExit("Garment fit QA failed")

if __name__ == "__main__":
    main()
