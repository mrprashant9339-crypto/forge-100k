"""Create deterministic geometry fixtures for Phase 2 Blender worker integration tests.

Usage: blender -b --python pipeline/tests/blender_phase2_fixtures.py -- output_dir
"""
import bpy
import os
import sys

def args():
    argv=sys.argv
    return argv[argv.index("--")+1:] if "--" in argv else []

def reset():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

def material(name, color):
    mat=bpy.data.materials.new(name)
    mat.diffuse_color=(*color,1)
    mat.use_nodes=True
    mat.node_tree.nodes.get("Principled BSDF").inputs["Base Color"].default_value=(*color,1)
    return mat

def export(path, objects):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects: obj.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]
    bpy.ops.export_scene.gltf(filepath=path,export_format="GLB",use_selection=True,
        export_apply=True,export_texcoords=True,export_normals=True,
        export_materials="EXPORT",export_skins=True,export_animations=True,export_morph=True)

def main():
    a=args()
    if len(a)!=1: raise SystemExit("Usage: blender_phase2_fixtures.py -- output_dir")
    out=os.path.abspath(a[0]);os.makedirs(out,exist_ok=True)
    reset()
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=16,location=(0,0,1))
    body=bpy.context.object;body.name="BodyFixture";body.scale=(.45,.28,1.0)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    body.data.materials.append(material("BodyMat",(.3,.4,.6)))
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16,ring_count=12,location=(0,0,2.1))
    head=bpy.context.object;head.name="Head";head.scale=(.25,.22,.3)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    head.data.materials.append(body.data.materials[0])
    export(os.path.join(out,"body.glb"),[body,head])
    reset()
    # A manifold, quad-dominant torso garment shell. The previous 8-vertex
    # cube collapsed onto the body during shrinkwrap and was not a meaningful
    # cloth simulation mesh.
    segments = 32
    levels = [
        (0.50, 0.33, 0.48),
        (0.51, 0.34, 0.62),
        (0.52, 0.35, 0.78),
        (0.52, 0.35, 0.94),
        (0.51, 0.34, 1.10),
        (0.50, 0.33, 1.26),
        (0.49, 0.32, 1.42),
        (0.48, 0.31, 1.58),
        (0.47, 0.30, 1.72),
    ]
    vertices = []
    faces = []
    for rx, ry, z in levels:
        for index in range(segments):
            angle = 2.0 * 3.141592653589793 * index / segments
            vertices.append((rx * __import__("math").cos(angle),
                             ry * __import__("math").sin(angle), z))
    for ring in range(len(levels) - 1):
        for index in range(segments):
            a = ring * segments + index
            b = ring * segments + (index + 1) % segments
            c = (ring + 1) * segments + (index + 1) % segments
            d = (ring + 1) * segments + index
            faces.append((a, b, c, d))
    mesh = bpy.data.meshes.new("GarmentFixtureMesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    garment = bpy.data.objects.new("GarmentFixture", mesh)
    bpy.context.scene.collection.objects.link(garment)
    garment.data.materials.append(material("GarmentMat",(.6,.2,.1)))
    garment.data.uv_layers.new(name="UVMap")
    for polygon in garment.data.polygons:
        polygon.use_smooth = True
    export(os.path.join(out,"garment.glb"),[garment])
    reset()
    shared=material("SharedMaterial",(.2,.5,.3))
    for x in (-1,1):
        bpy.ops.mesh.primitive_cube_add(size=.5,location=(x*.4,0,1))
        bpy.context.object.name="StaticPart_"+str(x)
        bpy.context.object.data.materials.append(shared)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12,ring_count=8,location=(0,0,1))
    morph=bpy.context.object;morph.name="MorphProtected"
    morph.data.materials.append(bpy.data.objects["StaticPart_-1"].data.materials[0])
    morph.shape_key_add(name="Basis")
    key=morph.shape_key_add(name="ForgeBody_test")
    for v in key.data: v.co.z+=.1
    export(os.path.join(out,"merge-input.glb"),list(bpy.context.scene.objects))
    print("PHASE2_FIXTURES_CREATED "+out)

if __name__=="__main__": main()
