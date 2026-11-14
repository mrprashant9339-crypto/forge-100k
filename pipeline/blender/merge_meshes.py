"""Material-preserving mesh merge stage for Forge 100K.

Usage:
  blender -b --python pipeline/blender/merge_meshes.py -- input.glb output.glb report.json

Meshes are joined by compatible material set; UVs and material slots are kept.
This is NOT a texture atlas baker. Shape-key meshes are isolated so morph target
vertex correspondence is not destroyed.
"""
import bpy
import json
import os
import sys

def args_after_separator():
    argv = sys.argv
    return argv[argv.index("--") + 1:] if "--" in argv else []

def material_signature(obj):
    return tuple(sorted((m.name if m else "__none__") for m in obj.data.materials))

def main():
    args = args_after_separator()
    if len(args) != 3:
        raise SystemExit("Usage: merge_meshes.py -- input.glb output.glb report.json")
    source, output, report_path = map(os.path.abspath, args)
    if not os.path.isfile(source):
        raise FileNotFoundError(source)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=source)
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    if not meshes:
        raise RuntimeError("Input GLB contains no meshes")
    buckets = {}
    protected = []
    for obj in meshes:
        if obj.data.shape_keys is not None:
            protected.append(obj.name)
            continue
        buckets.setdefault(material_signature(obj), []).append(obj)
    merged = []
    for index, group in enumerate(buckets.values()):
        if len(group) < 2:
            continue
        names = [obj.name for obj in group]
        bpy.ops.object.select_all(action="DESELECT")
        for obj in group:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = group[0]
        bpy.ops.object.join()
        group[0].name = "ForgeMerged_" + str(index).zfill(3)
        merged.append({"output_mesh": group[0].name, "source_meshes": names})
    bpy.ops.object.select_all(action="DESELECT")
    export_objects = [o for o in bpy.context.scene.objects
                      if o.type in {"MESH", "ARMATURE", "EMPTY"}]
    for obj in export_objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = next(
        (o for o in export_objects if o.type == "MESH"), None)
    os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=output, export_format="GLB",
        use_selection=True, export_apply=True, export_texcoords=True,
        export_normals=True, export_materials="EXPORT", export_skins=True,
        export_animations=True, export_morph=True, export_cameras=False,
        export_lights=False)
    report = {
        "status": "mesh_merge_complete", "input": source, "output": output,
        "merged_groups": merged, "shape_key_meshes_preserved": protected,
        "texture_atlas_baked": False, "game_ready": False,
        "note": "Material-preserving mesh merge only; texture atlas baking is a separate stage."
    }
    os.makedirs(os.path.dirname(report_path) or ".", exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    print("FORGE_MESH_MERGE " + json.dumps(report))

if __name__ == "__main__":
    main()
