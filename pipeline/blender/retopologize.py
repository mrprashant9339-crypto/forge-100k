"""Create a retopology candidate from a high-resolution source using Blender Quadriflow.

Usage:
  blender -b --python retopologize.py -- source.glb output.glb [target_faces]

This is an automated retopology draft. It preserves the source file, creates UVs,
and reports topology metrics. It is NOT artist-approved production topology.
"""
import bpy, bmesh, json, os, sys

def cli():
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if len(a) not in (2, 3):
        raise SystemExit("Usage: -- source.glb output.glb [target_faces]")
    return os.path.abspath(a[0]), os.path.abspath(a[1]), int(a[2]) if len(a) == 3 else 12000

def mesh_stats(obj):
    mesh = obj.data
    bm = bmesh.new()\n    bm.from_mesh(mesh)\n    non_manifold = sum(1 for e in bm.edges if not e.is_manifold)\n    bm.free()
    return {
        "vertices": len(mesh.vertices),
        "edges": len(mesh.edges),
        "faces": len(mesh.polygons),
        "non_manifold_edges": non_manifold,
        "uv_layers": [uv.name for uv in mesh.uv_layers],
        "materials": [m.name if m else None for m in mesh.materials],
    }

def main():
    source, output, target_faces = cli()
    if target_faces < 100 or target_faces > 200000:
        raise ValueError("target_faces must be between 100 and 200000")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=source)
    sources = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    if not sources:
        raise RuntimeError("Source GLB contains no mesh objects")
    os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
    report = {"source": source, "output": output, "target_faces": target_faces, "meshes": [], "method": "Blender Quadriflow", "artist_review_required": True, "engine_certified": False}
    exported = []
    for index, src in enumerate(sources):
        before = mesh_stats(src)
        low = src.copy()
        low.data = src.data.copy()
        low.name = src.name + "_Retopo"
        bpy.context.collection.objects.link(low)
        low.matrix_world = src.matrix_world.copy()
        bpy.ops.object.select_all(action="DESELECT")
        low.select_set(True)
        bpy.context.view_layer.objects.active = low
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
        # Quadriflow operator options vary slightly between Blender versions.
        props = bpy.ops.object.quadriflow_remesh.get_rna_type().properties
        kwargs = {"target_faces": max(100, target_faces // len(sources))}
        for key, value in (("use_mesh_symmetry", False), ("use_preserve_sharp", True), ("use_preserve_boundary", True), ("smooth_normals", True)):
            if key in props:
                kwargs[key] = value
        result = bpy.ops.object.quadriflow_remesh(**kwargs)
        if "FINISHED" not in result:
            raise RuntimeError("Quadriflow remesh did not finish for " + src.name)
        low = bpy.context.view_layer.objects.active
        if low is None or low.type != "MESH":
            raise RuntimeError("Quadriflow did not return an active mesh for " + src.name)
        low.name = src.name + "_Retopo"
        low.data.name = low.name + "_Mesh"
        # Preserve object transform from the imported source and generate a usable UV set.
        if not low.data.uv_layers:
            low.data.uv_layers.new(name="UVMap")
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.smart_project(island_margin=0.02)
        bpy.ops.mesh.select_all(action="DESELECT")
        bpy.ops.object.mode_set(mode="OBJECT")
        low.data.update()
        after = mesh_stats(low)
        if after["faces"] < 1 or not after["uv_layers"]:
            raise RuntimeError("Retopology output failed basic mesh/UV checks: " + src.name)
        report["meshes"].append({"name": src.name, "before": before, "after": after, "face_ratio": round(after["faces"] / max(1, before["faces"]), 4)})
        exported.append(low)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in exported:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = exported[0]
    bpy.ops.export_scene.gltf(filepath=output, export_format="GLB", use_selection=True, export_apply=False, export_texcoords=True, export_normals=True, export_materials="EXPORT", export_cameras=False, export_lights=False)
    report["status"] = "retopology_candidate_created"
    report["limitations"] = [
        "Quadriflow is an automated draft, not artist-authored deformation topology",
        "Inspect facial loops, elbows, knees, shoulders, fingers and silhouette manually",
        "UVs are Smart UV Project islands and require production packing/texel-density review",
        "No sculpt detail transfer is performed here; run the high-to-low bake worker next",
        "No rig deformation, engine import or performance certification is implied"
    ]
    with open(output + ".retopo.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print("FORGE_RETOPO " + json.dumps(report))

if __name__ == "__main__":
    main()
