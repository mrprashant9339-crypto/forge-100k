"""Build a small deterministic cloth mesh with an authored tear seam for CI.

Usage: blender -b --python blender_authored_tear_fixture.py -- output.blend
"""
import bpy
import os
import sys


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if len(args) != 1:
        raise SystemExit("Usage: -- output.blend")
    output = os.path.abspath(args[0])
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    nx, ny = 9, 7
    verts = [((x / (nx - 1)) - 0.5, 0.0, (y / (ny - 1)) + 0.5)
             for y in range(ny) for x in range(nx)]
    faces = []
    for y in range(ny - 1):
        for x in range(nx - 1):
            a = y * nx + x
            faces.append((a, a + 1, a + 1 + nx, a + nx))
    mesh = bpy.data.meshes.new("AuthoredTearFixtureMesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    garment = bpy.data.objects.new("GarmentTearFixture", mesh)
    bpy.context.scene.collection.objects.link(garment)
    garment.data.uv_layers.new(name="UVMap")
    cloth = garment.modifiers.new("Forge_Cloth_Simulation", "CLOTH")
    cloth.settings.quality = 5
    pin = garment.vertex_groups.new(name="Forge_Cloth_Pin")
    pin.add([v.index for v in mesh.vertices], 0.85, "REPLACE")
    cloth.settings.vertex_group_mass = pin.name
    seam = garment.vertex_groups.new(name="Forge_Tear_Seam")
    seam_indices = [y * nx + (nx // 2) for y in range(ny)]
    seam.add(seam_indices, 1.0, "REPLACE")

    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = 1, 12
    os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=output)
    print("FORGE_AUTHORED_TEAR_FIXTURE_CREATED " + output)


if __name__ == "__main__":
    main()
