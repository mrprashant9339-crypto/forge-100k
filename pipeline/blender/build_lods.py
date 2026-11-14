"""Deterministic GLB LOD builder.

Usage: blender -b --python pipeline/blender/build_lods.py -- input.glb output_dir
Creates independent LOD0/LOD1/LOD2 GLBs and a machine-readable triangle report.
This is a geometric decimation stage; it does not replace artist review.
"""
import bpy
import json
import os
import sys

RATIOS = (1.0, 0.5, 0.2)

def arguments():
    argv = sys.argv
    return argv[argv.index("--") + 1:] if "--" in argv else []

def reset():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

def triangle_count(objects):
    total = 0
    for obj in objects:
        if obj.type != "MESH":
            continue
        evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        mesh = evaluated.to_mesh()
        total += sum(max(0, len(poly.vertices) - 2) for poly in mesh.polygons)
        evaluated.to_mesh_clear()
    return total

def export_level(objects, output, level, ratio):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        if obj.type in {"MESH", "ARMATURE", "EMPTY"}:
            obj.select_set(True)
        if obj.type == "MESH":
            if ratio < 1.0 and len(obj.data.polygons) > 12:
                modifier = obj.modifiers.new("ForgeLODDecimate", "DECIMATE")
                modifier.ratio = ratio
                modifier.use_collapse_triangulate = True
                bpy.context.view_layer.objects.active = obj
                bpy.ops.object.modifier_apply(modifier=modifier.name)
    bpy.context.view_layer.objects.active = next((o for o in objects if o.type == "MESH"), None)
    os.makedirs(os.path.dirname(output), exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=output, export_format="GLB", use_selection=True,
        export_apply=True, export_texcoords=True, export_normals=True,
        export_materials="EXPORT", export_cameras=False, export_lights=False,
        export_morph=True, export_skins=True, export_animations=True
    )

def main():
    args = arguments()
    if len(args) != 2:
        raise SystemExit("Usage: build_lods.py -- input.glb output_dir")
    source, output_dir = map(os.path.abspath, args)
    if not os.path.isfile(source):
        raise FileNotFoundError(source)
    os.makedirs(output_dir, exist_ok=True)
    reports = []
    for level, ratio in enumerate(RATIOS):
        reset()
        bpy.ops.import_scene.gltf(filepath=source)
        objects = [o for o in bpy.context.scene.objects if o.type in {"MESH", "ARMATURE", "EMPTY"}]
        meshes = [o for o in objects if o.type == "MESH"]
        if not meshes:
            raise RuntimeError("Input GLB contains no meshes")
        before = triangle_count(meshes)
        # LOD levels are generated from the same source to avoid cumulative loss.
        out = os.path.join(output_dir, "LOD" + str(level) + ".glb")
        export_level(objects, out, level, ratio)
        after = triangle_count(meshes)
        reports.append({
            "level": level, "target_ratio": ratio, "source_triangles": before,
            "result_triangles": after, "measured_ratio": after / before if before else 0,
            "file": out, "status": "pass" if os.path.isfile(out) and os.path.getsize(out) > 20 else "fail"
        })
    if any(item["status"] != "pass" for item in reports):
        raise RuntimeError("One or more LOD exports failed")
    report_path = os.path.join(output_dir, "lod-report.json")
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump({"source": source, "levels": reports,
                   "quality_note": "Decimation is automated; silhouette and deformation require artist review."},
                  handle, indent=2)
    print("FORGE_LOD " + json.dumps(reports))

if __name__ == "__main__":
    main()
