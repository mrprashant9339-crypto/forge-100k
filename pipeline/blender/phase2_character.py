"""Phase 2 Blender worker: facial shape keys and modular equipment.
Usage: blender -b --python phase2_character.py -- input.glb job.json output.glb
ForgeFace controls are procedural sliders, not ARKit-certified expressions.
"""
import bpy,json,math,os,sys
from mathutils import Vector
def args():
 a=sys.argv
 return a[a.index("--")+1:] if "--" in a else []
def mat(n,c,metal=0,rough=.55):
 m=bpy.data.materials.new(n);m.diffuse_color=(*c,1);m.use_nodes=True
 p=m.node_tree.nodes.get("Principled BSDF")
 if p:p.inputs["Base Color"].default_value=(*c,1);p.inputs["Metallic"].default_value=metal;p.inputs["Roughness"].default_value=rough
 return m
def add_face_keys(head,controls):
 funcs={
 "jaw_width":lambda p:Vector((p.x*.18,0,0))*math.exp(-((p.z+.12)/.18)**2),
 "jaw_height":lambda p:Vector((0,0,p.z*.12))*math.exp(-((p.z+.12)/.2)**2),
 "cheek_fullness":lambda p:Vector((0,-.045,0))*math.exp(-((abs(p.x)-.19)/.10)**2-((p.z-.02)/.10)**2),
 "eye_scale":lambda p:Vector((0,-.025,0))*math.exp(-((abs(p.x)-.12)/.07)**2-((p.z-.09)/.055)**2),
 "eye_spacing":lambda p:Vector((p.x*.12,0,0))*math.exp(-((abs(p.x)-.12)/.08)**2-((p.z-.09)/.08)**2),
 "nose_width":lambda p:Vector((p.x*.20,0,0))*math.exp(-(p.x/.07)**2-((p.z)/.11)**2),
 "nose_length":lambda p:Vector((0,-.035,0))*math.exp(-(p.x/.06)**2-(p.z/.13)**2),
 "mouth_width":lambda p:Vector((p.x*.18,0,0))*math.exp(-(p.x/.12)**2-((p.z+.11)/.045)**2),
 "brow_depth":lambda p:Vector((0,-.035,0))*math.exp(-((abs(p.x)-.12)/.08)**2-((p.z-.17)/.04)**2),
 "chin_projection":lambda p:Vector((0,-.04,0))*math.exp(-(p.x/.12)**2-((p.z+.22)/.06)**2)}
 if not head.data.shape_keys:head.shape_key_add(name="Basis",from_mix=False)
 basis=head.data.shape_keys.key_blocks["Basis"]
 for name,fn in funcs.items():
  block=head.shape_key_add(name="ForgeFace_"+name,from_mix=False);amount=float(controls.get(name,0))
  for i,v in enumerate(head.data.vertices):
   local=basis.data[i].co.copy();world=head.matrix_world@local;p=world-Vector((0,0,2.15))
   block.data[i].co=local+head.matrix_world.inverted().to_3x3()@(fn(p)*amount)
 return ["ForgeFace_"+k for k in funcs]
def part(name,loc,dim,material,sphere=False):
 if sphere:bpy.ops.mesh.primitive_uv_sphere_add(segments=24,ring_count=12,location=loc)
 else:bpy.ops.mesh.primitive_cube_add(size=1,location=loc)
 o=bpy.context.object;o.name=name;o.dimensions=dim;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);o.data.materials.append(material)
 b=o.modifiers.new("ForgeSoftEdges","BEVEL");b.width=.035;b.segments=2;o["forge_module"]=name;return o
def add_body_keys(objects,profile):
 controls={
  "height":float(profile.get("height",1.0)),
  "shoulder_width":float(profile.get("shoulder_width",1.0)),
  "torso_ratio":float(profile.get("torso_ratio",1.0)),
  "arm_length":float(profile.get("arm_length",1.0)),
  "leg_length":float(profile.get("leg_length",1.0)),
  "muscle":float(profile.get("muscle",.5)),
  "mass":float(profile.get("mass",.5))}
 mapping={
  "height":lambda n:(1,1,controls["height"]),
  "shoulder_width":lambda n:((controls["shoulder_width"] if n in ("Torso","ChestPlate","Shoulder_L","Shoulder_R","Arm_L","Arm_R") else 1),1,1),
  "torso_ratio":lambda n:((controls["torso_ratio"] if n in ("Torso","Pelvis","ChestPlate") else 1),1,(1+(controls["torso_ratio"]-1)*.5 if n in ("Torso","Pelvis") else 1)),
  "arm_length":lambda n:(1,1,controls["arm_length"] if n.startswith("Arm_") else 1),
  "leg_length":lambda n:(1,1,controls["leg_length"] if n.startswith(("Leg_","Boot_")) else 1),
  "muscle":lambda n:((1+(controls["muscle"]-.5)*.28 if n.startswith(("Arm_","Leg_")) else 1),(1+(controls["muscle"]-.5)*.28 if n.startswith(("Arm_","Leg_")) else 1),1),
  "mass":lambda n:((1+(controls["mass"]-.5)*.32 if n in ("Torso","Pelvis") else 1),(1+(controls["mass"]-.5)*.24 if n in ("Torso","Pelvis") else 1),1)}
 made=[]
 for obj in objects:
  if obj.type!="MESH" or obj.name.startswith("Module_"):continue
  if not obj.data.shape_keys:obj.shape_key_add(name="Basis",from_mix=False)
  basis=obj.data.shape_keys.key_blocks["Basis"]
  for key,fn in mapping.items():
   block=obj.shape_key_add(name="ForgeBody_"+key,from_mix=False)
   sx,sy,sz=fn(obj.name)
   for i,v in enumerate(basis.data):
    block.data[i].co=(v.co.x*sx,v.co.y*sy,v.co.z*sz)
   block.value=1.0
   made.append(block.name)
 return sorted(set(made))

def build_module(mid):
 steel=mat("M_Module_Steel",(.12,.19,.28),.72,.32);cloth=mat("M_Module_Cloth",(.18,.25,.31),.05,.78);gold=mat("M_Module_Accent",(.78,.52,.16),.65,.28)
 spec={
 "hair_short":("Module_Hair_Short",(0,0,2.43),(.66,.64,.30),cloth,True),
 "helmet_scout":("Module_Helmet_Scout",(0,0,2.46),(.78,.72,.38),steel,True),
 "backpack_field":("Module_Backpack_Field",(0,.34,1.48),(.58,.34,.68),cloth,False),
 "armor_chest":("Module_Armor_Chest",(0,-.29,1.48),(.68,.12,.55),steel,False),
 "shoulder_guard":("Module_Shoulder_Guard",(.65,0,1.86),(.34,.38,.28),gold,True),
 "boots_combat":("Module_Boots_Combat",(0,-.13,.08),(.78,.60,.20),steel,False)}
 if mid not in spec:raise ValueError("Unsupported module "+mid)
 n,l,d,m,s=spec[mid];o=part(n,l,d,m,s);o["forge_module_id"]=mid;o["forge_license"]="CC0-1.0";return o
def main():
 a=args()
 if len(a)!=3:raise SystemExit("Usage: phase2_character.py -- input.glb job.json output.glb")
 src,jp,out=map(os.path.abspath,a);job_data=json.load(open(jp,encoding="utf-8"))
 job=job_data["jobs"][0] if isinstance(job_data,dict) and "jobs" in job_data else job_data
 bpy.ops.object.select_all(action="SELECT");bpy.ops.object.delete(use_global=False);bpy.ops.import_scene.gltf(filepath=src)
 heads=[o for o in bpy.context.scene.objects if o.type=="MESH" and o.name.startswith("Head")]
 if job.get("species")=="human" and not heads:raise RuntimeError("Human asset missing Head mesh")
 face=add_face_keys(heads[0],job.get("face_profile",{})) if heads else []
 body=add_body_keys([o for o in bpy.context.scene.objects if o.type=="MESH"],job.get("body_profile",{}))
 mods=[build_module(x) for x in job.get("modules",[])]
 bpy.ops.object.select_all(action="DESELECT")
 for o in bpy.context.scene.objects:
  if o.type in {"MESH","EMPTY"}:o.select_set(True)
 os.makedirs(os.path.dirname(out) or ".",exist_ok=True)
 bpy.ops.export_scene.gltf(filepath=out,export_format="GLB",use_selection=True,export_apply=True,export_texcoords=True,export_normals=True,export_morph=True,export_materials="EXPORT",export_cameras=False,export_lights=False)
 report={"asset_id":job["asset_id"],"output":out,"face_morph_targets":face,"face_profile":job.get("face_profile",{}),"body_morph_targets":body,"body_profile":job.get("body_profile",{}),"modules":job.get("modules",[]),"module_count":len(mods),"morph_standard":"Forge procedural controls v1 (not ARKit)","status":"phase2_generated","license":"CC0-1.0","artist_review_required":True}
 json.dump(report,open(out+".phase2.json","w",encoding="utf-8"),indent=2);print("FORGE_PHASE2 "+json.dumps(report))
if __name__=="__main__":main()
