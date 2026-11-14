"""Deterministic GLB LOD builder.

Usage: blender -b --python pipeline/blender/build_lods.py -- input.glb output_dir
Creates independent LOD0/LOD1/LOD2 GLBs and a machine-readable triangle report.

Blender's Decimate modifier cannot be applied to meshes with shape keys. Such
meshes are intentionally kept at full topology in every LOD so facial/body
morph targets remain valid. Static meshes are decimated normally.
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
    depsgraph = bpy.context.evaluated_depsgraph_get()
    for obj in objects:
        if obj.type != "MESH":
            continue
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        try:
            total += sum(max(0, len(poly.vertices) - 2) for poly in mesh.polygons)
        finally:
            evaluated.to_mesh_clear()
    return total


def export_level(objects, output, ratio):
    bpy.ops.object.select_all(action="DESELECT")
    decimated = []
    preserved_morphs = []
    for obj in objects:
        if obj.type in {"MESH", "ARMATURE", "EMPTY"}:
            obj.select_set(True)
        if obj.type != "MESH" or ratio >= 1.0 or len(obj.data.polygons) <= 12:
            continue

        # Applying Decimate to a shape-key mesh raises a Blender RuntimeError.
        # Keep the original topology to preserve every morph target and its
        # vertex correspondence across exported LODs.
        if obj.data.shape_keys is not None:
            preserved_morphs.append(obj.name)
            continue

        modifier = obj.modifiers.new("ForgeLODDecimate", "DECIMATE")
        modifier.ratio = ratio
        modifier.use_collapse_triangulate = True
        bpy.context.view_layer.objects.active = obj
        try:
            bpy.ops.object.modifier_apply(modifier=modifier.name)
            decimated.append(obj.name)
        except Exception:
            # Do not silently export a broken/partially modified mesh.
            if obj.modifiers.get(modifier.name):
                obj.modifiers.remove(modifier)
            raise

    bpy.context.view_layer.objects.active = next(
        (obj for obj in objects if obj.type == "MESH"), None
    )
    os.makedirs(os.path.dirname(output), exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=output, export_format="GLB", use_selection=True,
        export_apply=True, export_texcoords=True, export_normals=True,
        export_materials="EXPORT", export_cameras=False, export_lights=False,
        export_morph=True, export_skins=True, export_animations=True
    )
    return {"decimated_meshes": decimated, "preserved_morph_meshes": preserved_morphs}


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
        objects = [
            obj for obj in bpy.context.scene.objects
            if obj.type in {"MESH", "ARMATURE", "EMPTY"}
        ]
        meshes = [obj for obj in objects if obj.type == "MESH"]
        if not meshes:
            raise RuntimeError("Input GLB contains no meshes")

        before = triangle_count(meshes)
        output = os.path.join(output_dir, "LOD" + str(level) + ".glb")
        mesh_report = export_level(objects, output, ratio)
        after = triangle_count(meshes)
        if not os.path.isfile(output) or os.path.getsize(output) <= 20:
            raise RuntimeError("LOD export missing or unexpectedly small: " + output)

        reports.append({
            "level": level,
            "target_ratio": ratio,
            "source_triangles": before,
            "result_triangles": after,
            "measured_ratio": after / before if before else 0,
            "file": output,
            "status": "pass",
            **mesh_report,
        })

    report_path = os.path.join(output_dir, "lod-report.json")
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump({
            "source": source,
            "levels": reports,
            "quality_note": (
                "Shape-key meshes retain full topology to preserve morph targets. "
                "Static meshes are decimated. Silhouette and deformation still "
                "require artist review."
            ),
        }, handle, indent=2)
    print("FORGE_LOD " + json.dumps(reports))


if __name__ == "__main__":
    main()
