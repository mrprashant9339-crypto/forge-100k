"""Create deterministic high/low GLB fixtures for Phase 3 retopo and bake CI."""
import bpy, os, sys

def main():
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if len(a) != 1:
        raise SystemExit("Usage: -- output_dir")
    out = os.path.abspath(a[0])
    os.makedirs(out, exist_ok=True)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=4, radius=1.0)
    high = bpy.context.object
    high.name = "BakeFixture"
    mat = bpy.data.materials.new("FixtureRed")
    mat.diffuse_color = (0.7, 0.12, 0.08, 1.0)
    high.data.materials.append(mat)
    bpy.ops.object.select_all(action="DESELECT")
    high.select_set(True)
    bpy.context.view_layer.objects.active = high
    bpy.ops.export_scene.gltf(filepath=os.path.join(out, "high.glb"), export_format="GLB", use_selection=True)
    bpy.ops.object.select_all(action="DESELECT")
    high.select_set(True)
    bpy.context.view_layer.objects.active = high
    bpy.ops.object.duplicate()
    low = bpy.context.object
    low.name = "BakeFixture"
    low.data = low.data.copy()
    low.modifiers.new("FixtureDecimate", "DECIMATE").ratio = 0.12
    bpy.context.view_layer.objects.active = low
    bpy.ops.object.modifier_apply(modifier="FixtureDecimate")
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(island_margin=0.02)
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.ops.object.select_all(action="DESELECT")
    low.select_set(True)
    bpy.context.view_layer.objects.active = low
    bpy.ops.export_scene.gltf(filepath=os.path.join(out, "low.glb"), export_format="GLB", use_selection=True, export_texcoords=True)
    print("FORGE_PHASE3_FIXTURES " + out)

if __name__ == "__main__":
    main()
