"""Prototype garment fitting stage for Forge 100K.

Usage:
  blender -b --python pipeline/blender/fit_garment.py -- body.glb garment.glb output.glb report.json

The worker fits garment meshes to the imported body with a bounded Shrinkwrap
offset and assigns semantic body-zone groups. It is a proxy workflow: cloth
simulation, production collision resolution and artist review remain required.
"""
import bpy
import json
import os
import sys

ZONES = {
    "head": (1.95, 3.0),
    "torso": (1.05, 1.95),
    "arms": (1.0, 2.05),
    "legs": (0.0, 1.1),
    "feet": (0.0, 0.22),
}

def args_after_separator():
    argv = sys.argv
    return argv[argv.index("--") + 1:] if "--" in argv else []

def reset_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

def world_z_bounds(obj):
    values = [(obj.matrix_world @ v.co).z for v in obj.data.vertices]
    return (min(values), max(values)) if values else (0.0, 0.0)

def assign_zone_groups(obj):
    low, high = world_z_bounds(obj)
    groups = {}
    for zone, (z0, z1) in ZONES.items():
        if high < z0 or low > z1:
            continue
        group = obj.vertex_groups.new(name="ForgeZone_" + zone)
        indices = [v.index for v in obj.data.vertices
                   if z0 <= (obj.matrix_world @ v.co).z <= z1]
        if indices:
            group.add(indices, 1.0, "REPLACE")
            groups[zone] = len(indices)
    obj["forge_body_zone_groups"] = json.dumps(groups, sort_keys=True)
    return groups

def main():
    args = args_after_separator()
    if len(args) != 4:
        raise SystemExit("Usage: fit_garment.py -- body.glb garment.glb output.glb report.json")
    body_path, garment_path, output_path, report_path = map(os.path.abspath, args)
    for path in (body_path, garment_path):
        if not os.path.isfile(path):
            raise FileNotFoundError(path)
    reset_scene()
    bpy.ops.import_scene.gltf(filepath=body_path)
    body_meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    if not body_meshes:
        raise RuntimeError("Body GLB contains no mesh objects")
    body_objects = list(body_meshes)
    # Build one world-space proxy from every body mesh. Using only body_meshes[0]
    # silently misses separate head/limb meshes during garment fitting.
    proxy_vertices = []
    proxy_faces = []
    for body_obj in body_objects:
        offset = len(proxy_vertices)
        proxy_vertices.extend([tuple(body_obj.matrix_world @ vertex.co)
                               for vertex in body_obj.data.vertices])
        proxy_faces.extend([tuple(offset + index for index in polygon.vertices)
                            for polygon in body_obj.data.polygons if len(polygon.vertices) >= 3])
    proxy_mesh = bpy.data.meshes.new("ForgeBodyFitProxyMesh")
    proxy_mesh.from_pydata(proxy_vertices, [], proxy_faces)
    proxy_mesh.update()
    proxy_obj = bpy.data.objects.new("ForgeBodyFitProxy", proxy_mesh)
    bpy.context.collection.objects.link(proxy_obj)
    proxy_obj.matrix_world.identity()
    if len(proxy_mesh.polygons) == 0:
        raise RuntimeError("Combined body fit proxy contains no polygons")
    bpy.ops.import_scene.gltf(filepath=garment_path)
    garment_meshes = [o for o in bpy.context.scene.objects
                      if o.type == "MESH" and o not in body_objects]
    if not garment_meshes:
        raise RuntimeError("Garment GLB contains no mesh objects")
    records = []
    for garment in garment_meshes:
        zones = assign_zone_groups(garment)
        modifier = garment.modifiers.new("ForgeGarmentProxyFit", "SHRINKWRAP")
        modifier.target = proxy_obj
        modifier.wrap_method = "NEAREST_SURFACEPOINT"
        modifier.offset = 0.012
        bpy.context.view_layer.objects.active = garment
        bpy.ops.object.modifier_apply(modifier=modifier.name)
        garment["forge_fit_stage"] = "shrinkwrap_proxy_v1"
        garment["forge_fit_target"] = proxy_obj.name
        records.append({"mesh": garment.name, "body_zones": zones,
                        "fit_method": "nearest_surface_shrinkwrap",
                        "offset_m": 0.012, "body_target_mesh_count": len(body_objects),
                        "status": "proxy_fit_applied"})
    bpy.data.objects.remove(proxy_obj, do_unlink=True)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in body_objects + garment_meshes:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = garment_meshes[0]
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=output_path, export_format="GLB",
        use_selection=True, export_apply=True, export_texcoords=True,
        export_normals=True, export_materials="EXPORT", export_skins=True,
        export_animations=True, export_morph=True, export_cameras=False,
        export_lights=False)
    report = {
        "status": "proxy_fit_complete", "body": body_path,
        "garment": garment_path, "output": output_path,
        "garments": records, "game_ready": False,
        "limitations": [
            "No cloth simulation or fabric solver is performed",
            "No certified self-intersection or body-clipping test is performed",
            "Body-zone groups are semantic metadata, not runtime occlusion masks",
            "Requires pose-space fit tests and artist approval"
        ]
    }
    os.makedirs(os.path.dirname(report_path) or ".", exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    print("FORGE_GARMENT_FIT " + json.dumps(report))

if __name__ == "__main__":
    main()
