"""Prototype garment fitting stage for Forge 100K.

Usage:
  blender -b --python pipeline/blender/fit_garment.py -- body.glb garment.glb output.glb report.json

The worker fits garment meshes to a combined body proxy. Cloth simulation,
production collision resolution and artist review remain required.
"""
import bpy
import json
from mathutils.bvhtree import BVHTree
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
    for scene in list(bpy.data.scenes):
        if scene.name != bpy.context.scene.name:
            bpy.data.scenes.remove(scene)


def import_into_scene(path, scene_name):
    scene = bpy.data.scenes.new(scene_name)
    bpy.context.window.scene = scene
    bpy.ops.import_scene.gltf(filepath=path)
    meshes = [obj for obj in scene.objects if obj.type == "MESH"]
    if not meshes:
        raise RuntimeError(f"{scene_name} GLB contains no mesh objects")
    return scene, meshes


def world_z_bounds(obj):
    values = [(obj.matrix_world @ vertex.co).z for vertex in obj.data.vertices]
    return (min(values), max(values)) if values else (0.0, 0.0)


def assign_zone_groups(obj):
    low, high = world_z_bounds(obj)
    groups = {}
    for zone, (z0, z1) in ZONES.items():
        if high < z0 or low > z1:
            continue
        group = obj.vertex_groups.new(name="ForgeZone_" + zone)
        indices = [vertex.index for vertex in obj.data.vertices
                   if z0 <= (obj.matrix_world @ vertex.co).z <= z1]
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
    body_scene, body_meshes = import_into_scene(body_path, "ForgeBodyImport")
    garment_scene, garment_meshes = import_into_scene(garment_path, "ForgeGarmentImport")

    # Keep both imports in separate scenes because Blender's glTF importer may
    # replace objects in its active scene. Build a combined world-space proxy.
    proxy_vertices = []
    proxy_faces = []
    for body_obj in body_meshes:
        offset = len(proxy_vertices)
        proxy_vertices.extend([tuple(body_obj.matrix_world @ vertex.co)
                               for vertex in body_obj.data.vertices])
        proxy_faces.extend([tuple(offset + index for index in polygon.vertices)
                            for polygon in body_obj.data.polygons if len(polygon.vertices) >= 3])
    proxy_mesh = bpy.data.meshes.new("ForgeBodyFitProxyMesh")
    proxy_mesh.from_pydata(proxy_vertices, [], proxy_faces)
    proxy_mesh.update()
    fit_scene = bpy.data.scenes.new("ForgeGarmentFit")
    bpy.context.window.scene = fit_scene
    proxy_obj = bpy.data.objects.new("ForgeBodyFitProxy", proxy_mesh)
    fit_scene.collection.objects.link(proxy_obj)
    if not proxy_mesh.polygons:
        raise RuntimeError("Combined body fit proxy contains no polygons")

    # Link imported objects into the output scene without invalidating their
    # source-scene datablocks.
    for obj in body_meshes + garment_meshes:
        fit_scene.collection.objects.link(obj)

    records = []
    depsgraph = bpy.context.evaluated_depsgraph_get()
    body_bvh = BVHTree.FromObject(proxy_obj, depsgraph, epsilon=0.0)
    if body_bvh is None:
        raise RuntimeError("Could not build BVH for combined body fit proxy")
    for garment in garment_meshes:
        zones = assign_zone_groups(garment)
        inverse_world = garment.matrix_world.inverted_safe()
        for vertex in garment.data.vertices:
            world_position = garment.matrix_world @ vertex.co
            nearest = body_bvh.find_nearest(world_position)
            if nearest is None or nearest[0] is None or nearest[1] is None:
                raise RuntimeError("No nearest body surface found for garment vertex")
            # Imported fixtures can contain overlapping body parts with
            # inconsistent face winding. Orient the offset away from the source
            # garment point rather than trusting the BVH triangle normal alone.
            outward = world_position - nearest[0]
            normal = nearest[1].normalized()
            if outward.length > 1e-8 and normal.dot(outward) < 0.0:
                normal.negate()
            fitted_world = nearest[0] + normal * 0.012
            vertex.co = inverse_world @ fitted_world
        garment.data.update()
        garment["forge_fit_stage"] = "shrinkwrap_proxy_v1"
        garment["forge_fit_target"] = proxy_obj.name
        records.append({"mesh": garment.name, "body_zones": zones,
                        "fit_method": "nearest_surface_shrinkwrap",
                        "offset_m": 0.012, "body_target_mesh_count": len(body_meshes),
                        "status": "proxy_fit_applied"})

    bpy.ops.object.select_all(action="DESELECT")
    for obj in body_meshes + garment_meshes:
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
