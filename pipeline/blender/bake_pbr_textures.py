"""Bake high-detail source meshes onto UV-mapped low-poly targets.

Usage:
  blender -b --python bake_pbr_textures.py -- high.glb low.glb output_dir [resolution]

High and low objects must have matching names (Blender numeric suffixes are ignored).
The low mesh must have UVs. This worker bakes diffuse color, tangent normals and AO.
Metallic/roughness values remain authored material data; they are not sculpt-derived.
"""
import bpy, json, os, re, sys
from array import array

def cli():
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if len(a) not in (3, 4):
        raise SystemExit("Usage: -- high.glb low.glb output_dir [resolution]")
    return [os.path.abspath(x) for x in a[:3]] + [int(a[3]) if len(a) == 4 else 1024]

def clear():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

def base_name(value):
    return re.sub(r"\.\d{3}$", "", value)

def safe_name(value):
    return re.sub(r"[^A-Za-z0-9_-]+", "_", value)

def save_image(name, size, path, colorspace):
    img = bpy.data.images.new(name, width=size, height=size, alpha=False, float_buffer=False)
    img.generated_color = (0.0, 0.0, 0.0, 1.0)
    img.colorspace_settings.name = colorspace
    img.file_format = "PNG"
    img.filepath_raw = path
    return img

def bake_pass(low, high_objects, image, bake_type, directory, margin, cage_extrusion, max_ray_distance):
    for obj in bpy.context.scene.objects:
        obj.select_set(False)
    for obj in high_objects:
        obj.select_set(True)
    low.select_set(True)
    bpy.context.view_layer.objects.active = low
    mat = low.active_material
    if mat is None:
        mat = bpy.data.materials.new(low.name + "_BakeMaterial")
        low.data.materials.append(mat)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    target = nodes.new("ShaderNodeTexImage")
    target.name = "FORGE_BAKE_TARGET"
    target.image = image
    for node in nodes:
        node.select = False
    target.select = True
    nodes.active = target
    bake = bpy.context.scene.render.bake
    bake.margin = margin
    bake.use_selected_to_active = True
    bake.use_clear = True
    bake.normal_space = "TANGENT"
    if hasattr(bake, "use_cage"):
        bake.use_cage = False
    if hasattr(bake, "cage_extrusion"):
        bake.cage_extrusion = cage_extrusion
    if hasattr(bake, "max_ray_distance"):
        bake.max_ray_distance = max_ray_distance
    bpy.ops.object.bake(type=bake_type)
    path = os.path.join(directory, safe_name(low.name) + "_" + bake_type.lower() + ".png")
    image.filepath_raw = path
    image.file_format = "PNG"
    image.save()
    nodes.remove(target)
    return path

def bake_metallic_roughness(target, directory, size):
    """Write glTF metallic-roughness texture: G=roughness, B=metallic."""
    material = target.active_material
    metallic, roughness = 0.0, 0.5
    if material and material.use_nodes and material.node_tree:
        shader = next((node for node in material.node_tree.nodes
                       if node.type == "BSDF_PRINCIPLED"), None)
        if shader:
            metallic = float(shader.inputs["Metallic"].default_value)
            roughness = float(shader.inputs["Roughness"].default_value)
    image = bpy.data.images.new("Forge_" + safe_name(target.name) + "_METALLIC_ROUGHNESS",
                                width=size, height=size, alpha=False, float_buffer=False)
    image.colorspace_settings.name = "Non-Color"
    pixel = (0.0, roughness, metallic, 1.0)
    pixel_buffer = array("f", pixel) * (size * size)
    image.pixels.foreach_set(pixel_buffer)
    del pixel_buffer
    path = os.path.join(directory, safe_name(target.name) + "_metallic_roughness.png")
    image.filepath_raw = path
    image.file_format = "PNG"
    image.save()
    bpy.data.images.remove(image)
    return path, metallic, roughness


def main():
    high_path, low_path, out, size = cli()
    if size < 64 or size > 4096 or size & (size - 1):
        raise ValueError("resolution must be power of two 64..4096")
    os.makedirs(out, exist_ok=True)
    clear()
    bpy.ops.import_scene.gltf(filepath=high_path)
    high = {base_name(o.name): o for o in bpy.context.scene.objects if o.type == "MESH"}
    bpy.ops.import_scene.gltf(filepath=low_path)
    low = {}
    for obj in bpy.context.scene.objects:
        key = base_name(obj.name)
        if obj.type == "MESH" and key in high and obj is not high[key]:
            if key in low:
                raise RuntimeError("Ambiguous low-poly mesh name: " + key)
            low[key] = obj
    if not low:
        raise RuntimeError("No matching high/low mesh object names; use matching source object names")
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 32
    scene.render.bake.use_pass_color = True
    scene.render.bake.use_pass_direct = False
    scene.render.bake.use_pass_indirect = False
    report = {
        "status": "baked", "resolution": [size, size], "meshes": [], "maps": {},
        "settings": {"engine": "Cycles", "samples": 32, "margin_px": 16, "cage_extrusion": 0.02, "max_ray_distance": 0.1},
        "artist_review_required": True, "engine_certified": False
    }
    for name, target in sorted(low.items()):
        if not target.data.uv_layers:
            raise RuntimeError("Low mesh has no UV map: " + name)
        src = high[name]
        if not src.data.polygons or not target.data.polygons:
            raise RuntimeError("Empty mesh: " + name)
        entry = {
            "mesh": name, "low_vertices": len(target.data.vertices),
            "high_vertices": len(src.data.vertices), "low_faces": len(target.data.polygons),
            "high_faces": len(src.data.polygons), "uv_layer": target.data.uv_layers.active.name
        }
        for bake_type in ("DIFFUSE", "NORMAL", "AO"):
            color_space = "sRGB" if bake_type == "DIFFUSE" else "Non-Color"
            img = save_image("Forge_" + safe_name(name) + "_" + bake_type, size, os.path.join(out, "tmp.png"), color_space)
            path = bake_pass(target, [src], img, bake_type, out, 16, 0.02, 0.1)
            bpy.data.images.remove(img)
            entry[bake_type.lower()] = path
            report["maps"].setdefault(bake_type.lower(), []).append(path)
        mr_path, metallic, roughness = bake_metallic_roughness(target, out, size)
        entry["metallic_roughness"] = mr_path
        entry["metallic_factor"] = metallic
        entry["roughness_factor"] = roughness
        report["maps"].setdefault("metallic_roughness", []).append(mr_path)
        report["meshes"].append(entry)
    report["channel_packing"] = {
        "metallic_roughness": "Authored Principled BSDF factors packed into glTF channels: G=roughness, B=metallic; not inferred from sculpt geometry",
        "normal": "Tangent-space normal bake",
        "ao": "Ambient occlusion bake",
        "diffuse": "Diffuse color-only bake (direct and indirect lighting disabled)"
    }
    report["limitations"] = [
        "High/low correspondence is name-based; verify transforms and object alignment",
        "Cage extrusion and ray distance are defaults; tune per asset to avoid projection misses/skew",
        "Inspect UV seams, cage intersections, tangent basis, mipmaps and target-engine appearance",
        "Metallic/roughness texture is generated from authored low-poly material factors, not inferred from sculpt geometry",
        "This worker does not perform retopology"
    ]
    with open(os.path.join(out, "bake-report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print("FORGE_BAKE " + json.dumps(report))

if __name__ == "__main__":
    main()
