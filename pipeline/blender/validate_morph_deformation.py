"""Run Blender evaluated-geometry QA at both extremes of every morph target.

Usage: blender -b --python validate_morph_deformation.py -- model.glb report.json
"""
import bpy
import json
import math
import os
import sys


def args():
    argv = sys.argv
    return argv[argv.index("--") + 1:] if "--" in argv else []


def evaluated_metrics(obj, depsgraph):
    evaluated = obj.evaluated_get(depsgraph)
    mesh = evaluated.to_mesh()
    try:
        if not mesh.vertices or not mesh.polygons:
            raise RuntimeError("evaluated mesh is empty: " + obj.name)
        coordinates = [tuple(vertex.co) for vertex in mesh.vertices]
        if any(not math.isfinite(value) for point in coordinates for value in point):
            raise RuntimeError("non-finite vertex coordinate: " + obj.name)
        mesh.calc_loop_triangles()
        areas = [triangle.area for triangle in mesh.loop_triangles]
        degenerate = sum(1 for area in areas if not math.isfinite(area) or area <= 1e-12)
        if degenerate:
            raise RuntimeError("degenerate evaluated triangles on " + obj.name + ": " + str(degenerate))
        bounds = [[min(point[axis] for point in coordinates),
                   max(point[axis] for point in coordinates)] for axis in range(3)]
        if any((hi - lo) <= 1e-8 for lo, hi in bounds):
            raise RuntimeError("evaluated mesh collapsed on an axis: " + obj.name)
        return {"vertices": len(mesh.vertices), "triangles": len(mesh.loop_triangles),
                "bounds": bounds, "degenerate_triangles": degenerate}
    finally:
        evaluated.to_mesh_clear()


def main():
    argv = args()
    if len(argv) != 2:
        raise SystemExit("Usage: validate_morph_deformation.py -- model.glb report.json")
    source, report_path = map(os.path.abspath, argv)
    if not os.path.isfile(source):
        raise FileNotFoundError(source)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=source)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    records = []
    total_targets = 0
    for obj in (item for item in bpy.context.scene.objects if item.type == "MESH" and item.data.shape_keys):
        blocks = obj.data.shape_keys.key_blocks
        original = {block.name: block.value for block in blocks}
        targets = [block for block in blocks if block.name != "Basis"]
        for target in targets:
            for block in targets:
                block.value = 0.0
            samples = []
            for value in (0.0, 1.0):
                target.value = value
                bpy.context.view_layer.update()
                metrics = evaluated_metrics(obj, depsgraph)
                samples.append({"value": value, **metrics})
            records.append({"mesh": obj.name, "target": target.name, "extremes": samples})
            total_targets += 1
        for block in blocks:
            block.value = original[block.name]
    if total_targets == 0:
        raise RuntimeError("GLB contains no morph targets")
    os.makedirs(os.path.dirname(report_path) or ".", exist_ok=True)
    report = {"status": "morph_deformation_preflight_passed", "source": source,
              "morph_targets_checked": total_targets, "samples_checked": total_targets * 2,
              "artist_review_required": True, "engine_certified": False, "targets": records}
    with open(report_path, "w", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2)
    print("FORGE_MORPH_QA " + json.dumps({"status": report["status"],
          "morph_targets_checked": total_targets, "samples_checked": total_targets * 2}))


if __name__ == "__main__":
    main()
