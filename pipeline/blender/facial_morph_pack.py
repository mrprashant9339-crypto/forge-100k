"""Author a deterministic facial expression and viseme morph-target pack.

Usage:
  blender -b --python facial_morph_pack.py -- input.glb output.glb report.json

This creates editable morph targets on an original stylized head mesh. It is
not an ARKit 52 mapping, facial rig, performance-captured animation, or
artist-certified production face.
"""
import bpy
import json
import math
import os
import sys

EXPRESSIONS = {
    "smile": "ForgeExpr_smile",
    "frown": "ForgeExpr_frown",
    "brow_raise": "ForgeExpr_brow_raise",
    "jaw_open": "ForgeExpr_jaw_open",
    "cheek_puff": "ForgeExpr_cheek_puff",
    "squint": "ForgeExpr_squint",
}
VISEME = {name: "ForgeViseme_" + name for name in ("A", "E", "I", "O", "U")}

def arguments():
    argv=sys.argv
    values=argv[argv.index("--")+1:] if "--" in argv else []
    if len(values)!=3:
        raise SystemExit("Usage: facial_morph_pack.py -- input.glb output.glb report.json")
    return [os.path.abspath(v) for v in values]

def gaussian(x, center, width):
    return math.exp(-((x-center)/width)**2)

def face_weight(p):
    # The starter character faces -Y. Weight only the front facial surface.
    return max(0.0,min(1.0,(-p.y-0.025)/0.12))

def delta(name, p):
    front=face_weight(p)
    mouth=gaussian(p.z,-0.105,0.075)*gaussian(p.x,0.0,0.16)*front
    corners=gaussian(abs(p.x),0.17,0.075)*gaussian(p.z,-0.105,0.07)*front
    brow=gaussian(abs(p.x),0.13,0.09)*gaussian(p.z,0.19,0.055)*front
    cheeks=gaussian(abs(p.x),0.19,0.075)*gaussian(p.z,-0.005,0.09)*front
    lower=gaussian(p.z,-0.19,0.12)*front
    if name=="ForgeExpr_smile":
        return (0.0,-0.025*mouth,0.055*corners)
    if name=="ForgeExpr_frown":
        return (0.0,-0.018*mouth,-0.045*corners)
    if name=="ForgeExpr_brow_raise":
        return (0.0,-0.018*brow,0.045*brow)
    if name=="ForgeExpr_jaw_open":
        return (0.0,-0.035*mouth,-0.11*lower)
    if name=="ForgeExpr_cheek_puff":
        return (0.0,-0.055*cheeks,0.008*cheeks)
    if name=="ForgeExpr_squint":
        eyes=gaussian(abs(p.x),0.13,0.085)*gaussian(p.z,0.105,0.055)*front
        return (0.0,-0.012*eyes,-0.035*eyes)
    if name=="ForgeViseme_A":
        return (0.0,-0.045*mouth,-0.085*lower)
    if name=="ForgeViseme_E":
        return (0.0,-0.035*mouth,0.018*corners)
    if name=="ForgeViseme_I":
        return (0.0,-0.025*mouth,0.035*corners)
    if name=="ForgeViseme_O":
        return (0.0,-0.075*mouth,-0.035*lower)
    if name=="ForgeViseme_U":
        return (0.0,-0.06*mouth,-0.018*lower)
    raise ValueError("Unknown facial target: "+name)

def main():
    source,output,report_path=arguments()
    if not os.path.isfile(source): raise FileNotFoundError(source)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=source)
    heads=[o for o in bpy.context.scene.objects if o.type=="MESH" and o.name.lower().startswith("head")]
    if not heads: raise RuntimeError("Facial morph pack requires a mesh named Head or Head*")
    head=heads[0]
    if len(head.data.vertices)<16: raise RuntimeError("Head mesh needs at least 16 vertices")
    if not head.data.shape_keys: head.shape_key_add(name="Basis",from_mix=False)
    basis=head.data.shape_keys.key_blocks["Basis"]
    targets=list(EXPRESSIONS.values())+list(VISEME.values())
    created=[]
    for target in targets:
        if head.data.shape_keys.key_blocks.get(target):
            raise RuntimeError("Refusing to overwrite existing morph target: "+target)
        block=head.shape_key_add(name=target,from_mix=False)
        for index,vertex in enumerate(basis.data):
            p=vertex.co
            dx,dy,dz=delta(target,p)
            block.data[index].co=(p.x+dx,p.y+dy,p.z+dz)
        block.value=0.0
        created.append(target)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in bpy.context.scene.objects:
        if obj.type in {"MESH","ARMATURE","EMPTY"}: obj.select_set(True)
    bpy.context.view_layer.objects.active=head
    os.makedirs(os.path.dirname(output) or ".",exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=output,export_format="GLB",use_selection=True,
        export_apply=True,export_texcoords=True,export_normals=True,
        export_materials="EXPORT",export_skins=True,export_animations=True,
        export_morph=True,export_cameras=False,export_lights=False)
    report={
        "status":"facial_morph_pack_created","input":source,"output":output,
        "head_mesh":head.name,"vertex_count":len(head.data.vertices),
        "expression_targets":list(EXPRESSIONS.values()),
        "viseme_targets":list(VISEME.values()),"target_count":len(created),
        "standard":"Forge facial morph pack v1",
        "game_ready":False,
        "limitations":[
            "Procedural starter morphs require sculpt and phoneme review",
            "Not an ARKit 52 blendshape mapping",
            "No timed facial animation clips or performance capture included",
            "Eye blink and gaze controls require a dedicated eye rig",
            "Not validated against a production basemesh or target engine"
        ]
    }
    os.makedirs(os.path.dirname(report_path) or ".",exist_ok=True)
    with open(report_path,"w",encoding="utf-8") as f: json.dump(report,f,indent=2)
    print("FORGE_FACIAL_MORPHS "+json.dumps(report))

if __name__=="__main__": main()
