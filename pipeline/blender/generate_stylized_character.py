"""Forge 100K deterministic stylized humanoid generator.
Run: blender -b --python generate_stylized_character.py -- output_dir [asset_id] [seed]
"""
import bpy,os,sys,json,hashlib,random
from mathutils import Vector

def args():
 a=sys.argv; return a[a.index("--")+1:] if "--" in a else []
def clear():
 bpy.ops.object.select_all(action="SELECT"); bpy.ops.object.delete(use_global=False)
 for db in (bpy.data.meshes,bpy.data.armatures,bpy.data.actions,bpy.data.materials):
  for x in list(db):
   if x.users==0: db.remove(x)
def mat(n,c,r=.65,m=0):
 x=bpy.data.materials.new(n); x.diffuse_color=(*c,1); x.use_nodes=True
 p=x.node_tree.nodes.get("Principled BSDF")
 if p: p.inputs["Base Color"].default_value=(*c,1); p.inputs["Roughness"].default_value=r; p.inputs["Metallic"].default_value=m
 return x
def finish(o,bev=0):
 for f in o.data.polygons: f.use_smooth=True
 if bev:
  b=o.modifiers.new("Forge_Soft_Edges","BEVEL"); b.width=bev; b.segments=3
  o.modifiers.new("Forge_Weighted_Normals","WEIGHTED_NORMAL")
 return o
def uv(n,p,s,m,seg=32,rings=20):
 bpy.ops.mesh.primitive_uv_sphere_add(segments=seg,ring_count=rings,location=p)
 o=bpy.context.object; o.name=n; o.scale=s; bpy.ops.object.transform_apply(location=False,rotation=False,scale=True); o.data.materials.append(m); return finish(o)
def box(n,p,s,m,b=.025):
 bpy.ops.mesh.primitive_cube_add(size=1,location=p); o=bpy.context.object; o.name=n; o.dimensions=s
 bpy.ops.object.transform_apply(location=False,rotation=False,scale=True); o.data.materials.append(m); return finish(o,b)
def rod(n,a,b,r,m,r2=None):
 a=Vector(a); b=Vector(b); d=b-a
 bpy.ops.mesh.primitive_cone_add(vertices=20,radius1=r,radius2=r if r2 is None else r2,depth=d.length,location=(a+b)/2)
 o=bpy.context.object; o.name=n; o.rotation_mode="QUATERNION"; o.rotation_quaternion=d.to_track_quat("Z","Y"); o.data.materials.append(m); return finish(o)
def torus(n,p,major,minor,m):
 bpy.ops.mesh.primitive_torus_add(major_segments=32,minor_segments=10,major_radius=major,minor_radius=minor,location=p,rotation=(1.5708,0,0))
 o=bpy.context.object; o.name=n; o.data.materials.append(m); return finish(o)
def rig_create():
 data=bpy.data.armatures.new("Forge_Stylized_Humanoid_Rig"); rig=bpy.data.objects.new("Forge_Stylized_Humanoid_Rig",data); bpy.context.collection.objects.link(rig)
 bpy.context.view_layer.objects.active=rig; rig.select_set(True); bpy.ops.object.mode_set(mode="EDIT")
 def bone(n,h,t,p=None):
  b=data.edit_bones.new(n); b.head=h; b.tail=t
  if p: b.parent=data.edit_bones[p]
 bone("root",(0,0,.08),(0,0,.30)); bone("pelvis",(0,0,.82),(0,0,1.02),"root")
 bone("spine",(0,0,1.02),(0,0,1.42),"pelvis"); bone("chest",(0,0,1.42),(0,0,1.68),"spine")
 bone("neck",(0,0,1.68),(0,0,1.83),"chest"); bone("head",(0,0,1.83),(0,0,2.18),"neck")
 for s,L in [(-1,"L"),(1,"R")]:
  bone("clavicle_"+L,(0,0,1.62),(s*.28,0,1.61),"chest")
  bone("upper_arm_"+L,(s*.28,0,1.61),(s*.43,0,1.28),"clavicle_"+L)
  bone("lower_arm_"+L,(s*.43,0,1.28),(s*.46,-.01,1.02),"upper_arm_"+L)
  bone("hand_"+L,(s*.46,-.01,1.02),(s*.48,-.08,.94),"lower_arm_"+L)
  for i,n in enumerate(("thumb","index","middle","ring","pinky")):
   x=s*(.48+(i-2)*.025); bone(n+"_01_"+L,(s*.48,-.08,.94),(x,-.17,.91),"hand_"+L); bone(n+"_02_"+L,(x,-.17,.91),(x,-.23,.89),n+"_01_"+L)
  bone("upper_leg_"+L,(s*.13,0,.88),(s*.14,0,.49),"pelvis"); bone("lower_leg_"+L,(s*.14,0,.49),(s*.14,0,.13),"upper_leg_"+L); bone("foot_"+L,(s*.14,0,.13),(s*.14,-.23,.08),"lower_leg_"+L)
 bpy.ops.object.mode_set(mode="OBJECT"); rig.show_in_front=True; return rig
def segdist(p,a,b):
 d=b-a; t=max(0,min(1,(p-a).dot(d)/max(d.length_squared,1e-9))); return (p-(a+t*d)).length
def bind(o,rig):
 bones=[]
 for b in rig.data.bones:
  a=rig.matrix_world@b.head_local; z=rig.matrix_world@b.tail_local
  if (z-a).length>1e-6: bones.append((b.name,a,z))
 groups={n:o.vertex_groups.new(name=n) for n,_,_ in bones}
 for v in o.data.vertices:
  p=o.matrix_world@v.co; nearest=sorted((segdist(p,a,z),n) for n,a,z in bones)[:4]
  weights=[(1/max(d,.04)**2,n) for d,n in nearest]; total=sum(w for w,_ in weights)
  for w,n in weights: groups[n].add([v.index],w/total,"REPLACE")
 mod=o.modifiers.new("Forge_Skin","ARMATURE"); mod.object=rig; o.parent=rig
 o["forge_skinning"]="top4_normalized"
def animate(rig):
 scene=bpy.context.scene; scene.render.fps=30; scene.frame_start=1; scene.frame_end=25
 action=bpy.data.actions.new("Forge_Idle_Loop"); rig.animation_data_create(); rig.animation_data.action=action
 for n,a in {"spine":.025,"chest":.035,"head":.018,"upper_arm_L":.025,"upper_arm_R":-.025}.items():
  p=rig.pose.bones.get(n)
  if p:
   p.rotation_mode="XYZ"
   for f,v in ((1,-a),(13,a),(25,-a)):
    p.rotation_euler[1]=v; p.keyframe_insert(data_path="rotation_euler",frame=f,group=n)
 if action.fcurves:
  for fc in action.fcurves:
   for k in fc.keyframe_points: k.interpolation="BEZIER"
   fc.modifiers.new("CYCLES")
 scene.frame_set(1); rig["forge_animation"]="idle_loop_30fps"
def main():
 a=args()
 if not 1<=len(a)<=3: raise SystemExit("Usage: generate_stylized_character.py -- output_dir [asset_id] [seed]")
 out=os.path.abspath(a[0]); aid=a[1] if len(a)>1 else "FG-HUM-STYLIZED-000001"; seed=int(a[2]) if len(a)>2 else 100001
 if not aid or len(aid)>64: raise ValueError("Invalid asset_id")
 rng=random.Random(seed); os.makedirs(out,exist_ok=True); clear()
 skin=mat("M_Skin_Warm",(.55,.285,.19),.72); hi=mat("M_Skin_Highlight",(.72,.43,.31),.68); hair=mat("M_Hair_Deep",(.055,.035,.028),.48)
 teal=mat("M_Jacket_Teal",(.035,.24,.23),.76); pants=mat("M_Trousers_Charcoal",(.045,.075,.09),.82); lime=mat("M_Forge_Lime",(.55,.91,.24),.38,.12)
 brass=mat("M_Brushed_Brass",(.68,.39,.12),.3,.72); leather=mat("M_Boot_Leather",(.075,.045,.03),.55); white=mat("M_Eye_White",(.92,.94,.88),.22); iris=mat("M_Iris_Hazel",(.24,.12,.055),.3); pupil=mat("M_Pupil",(.008,.01,.012),.18); lip=mat("M_Lip",(.22,.075,.06),.62)
 meshes=[]
 def add(o): meshes.append(o); return o
 # Boots, shin guards, knee joints and tapered legs.
 for s,L in [(-1,"L"),(1,"R")]:
  x=s*.14
  add(box("Boot_Sole_"+L,(x,-.085,.095),(.22,.43,.09),leather,.035)); add(uv("Boot_Toe_"+L,(x,-.20,.17),(.115,.22,.13),leather))
  add(box("Boot_Cuff_"+L,(x,0,.285),(.18,.18,.13),brass)); add(uv("Shin_Guard_"+L,(x,-.035,.43),(.105,.13,.16),lime))
  add(rod("Lower_Leg_"+L,(x,0,.27),(x,0,.52),.085,pants,.105)); add(uv("Knee_"+L,(x,-.015,.53),(.105,.11,.105),brass))
  add(rod("Thigh_"+L,(x,0,.52),(x,0,.88),.115,pants,.15)); add(uv("Hip_Panel_"+L,(x,-.095,.88),(.14,.09,.16),teal))
  add(box("Thigh_Seam_"+L,(x,-.112,.69),(.018,.018,.26),lime,.008))
 # Torso and tailored jacket layers.
 add(uv("Pelvis_Core",(0,0,.91),(.245,.155,.19),pants)); add(uv("Torso_Base",(0,0,1.32),(.30,.17,.43),skin))
 add(uv("Jacket_Main",(0,-.012,1.34),(.34,.205,.43),teal)); add(box("Jacket_Hem",(0,-.02,1.00),(.62,.32,.10),pants,.04))
 add(box("Front_Placket",(0,-.207,1.34),(.075,.025,.57),brass,.012)); add(box("Chest_Panel",(0,-.218,1.47),(.28,.025,.22),pants,.025)); add(box("Chest_Insignia",(0,-.239,1.48),(.11,.014,.075),lime,.015))
 add(torus("Belt_Ring",(0,-.17,.93),.205,.024,brass)); add(box("Belt_Buckle",(0,-.196,.93),(.105,.035,.075),lime,.012))
 add(uv("Shoulder_L",(-.34,0,1.60),(.16,.19,.15),lime)); add(uv("Shoulder_R",(.34,0,1.60),(.16,.19,.15),lime))
 # Arms and clearly articulated five-finger hands.
 for s,L in [(-1,"L"),(1,"R")]:
  add(rod("Upper_Arm_"+L,(s*.30,0,1.57),(s*.42,0,1.27),.09,teal,.075)); add(uv("Elbow_"+L,(s*.42,0,1.27),(.075,.08,.075),brass))
  add(rod("Forearm_"+L,(s*.42,0,1.26),(s*.46,-.01,1.02),.072,skin,.06)); add(uv("Wrist_Guard_"+L,(s*.46,-.01,1.07),(.085,.09,.08),lime))
  add(uv("Hand_Palm_"+L,(s*.47,-.075,.95),(.075,.06,.09),hi))
  for i,n in enumerate(("Thumb","Index","Middle","Ring","Pinky")):
   dx=s*(.48+(i-2)*.027)
   a1=(s*.43,-.07,.97) if i==0 else (s*.47,-.10,.91); b=(s*.405,-.16,.93) if i==0 else (dx,-.20,.90)
   add(rod(n+"_Finger_"+L,a1,b,.018,hi,.014)); add(uv(n+"_Tip_"+L,b,(.017,.018,.018),hi,16,10))
 # Neck and readable face with hair silhouette.
 add(rod("Neck",(0,0,1.62),(0,0,1.86),.085,skin,.075)); add(uv("Head",(0,0,2.02),(.205,.18,.285),skin,40,28)); add(uv("Jaw",(0,-.045,1.90),(.16,.16,.13),hi))
 for s,L in [(-1,"L"),(1,"R")]:
  add(uv("Ear_"+L,(s*.205,0,2.02),(.045,.055,.075),skin)); add(uv("Ear_Inset_"+L,(s*.229,-.025,2.02),(.012,.028,.04),brass,16,10))
  add(uv("Eye_White_"+L,(s*.083,-.165,2.065),(.047,.025,.052),white,24,16)); add(uv("Iris_"+L,(s*.083,-.187,2.064),(.021,.012,.027),iris,20,12)); add(uv("Pupil_"+L,(s*.083,-.197,2.064),(.010,.007,.015),pupil,16,10))
  add(rod("Brow_"+L,(s*.045,-.169,2.135),(s*.125,-.155,2.125),.016,hair,.012)); add(uv("Cheek_"+L,(s*.12,-.145,1.985),(.045,.028,.035),hi,20,12))
 add(uv("Nose",(0,-.193,2.015),(.034,.052,.06),hi,24,16)); add(uv("Mouth",(0,-.174,1.945),(.048,.018,.012),lip,20,12))
 add(uv("Hair_Cap",(0,.005,2.205),(.215,.19,.13),hair,36,20))
 for i in range(7):
  x=-.17+i*.055; add(uv("Hair_Lock_%02d"%i,(x,-.095+rng.uniform(-.012,.012),2.19+rng.uniform(-.018,.018)),(.045,.095,.075),hair,20,12))
 # Explorer backpack, straps, side pouches.
 add(box("Backpack_Core",(0,.205,1.39),(.34,.20,.42),pants,.055)); add(box("Backpack_Flap",(0,.31,1.52),(.27,.025,.13),lime,.025))
 for s,L in [(-1,"L"),(1,"R")]:
  add(rod("Pack_Strap_"+L,(s*.23,-.15,1.60),(s*.16,-.19,1.08),.025,brass))
  add(box("Utility_Pouch_"+L,(s*.30,-.02,1.18),(.12,.12,.17),leather,.02))
 rig=rig_create()
 for o in meshes:
  bind(o,rig); o["forge_asset_id"]=aid; o["forge_seed"]=seed; o["forge_quality_tier"]="stylized_candidate_v1"
 rig["forge_asset_id"]=aid; rig["forge_quality_tier"]="stylized_candidate_v1"; animate(rig)
 scene=bpy.context.scene; # Rendering is not required for GLB export. Select an engine supported by this Blender build.
 engine_ids={item.identifier for item in scene.render.bl_rna.properties["engine"].enum_items}
 preferred=("BLENDER_EEVEE_NEXT","BLENDER_EEVEE","CYCLES")
 scene.render.engine=next((name for name in preferred if name in engine_ids),engine_ids.pop())
 scene.render.resolution_x=1024; scene.render.resolution_y=1024
 bpy.ops.object.select_all(action="DESELECT"); rig.select_set(True)
 for o in meshes: o.select_set(True)
 bpy.context.view_layer.objects.active=rig
 glb=os.path.join(out,aid+".glb")
 bpy.ops.export_scene.gltf(filepath=glb,export_format="GLB",use_selection=True,export_apply=False,export_animations=True,export_skins=True,export_morph=True,export_materials="EXPORT",export_texcoords=True,export_normals=True)
 blend=os.path.join(out,aid+".blend"); bpy.ops.wm.save_as_mainfile(filepath=blend)
 with open(glb,"rb") as f: digest=hashlib.sha256(f.read()).hexdigest()
 report={"schema":"forge.stylized-character.v1","asset_id":aid,"seed":seed,"status":"generated_candidate","quality_tier":"stylized_candidate_v1","artist_review_required":True,"engine_certified":False,
 "files":{"glb":os.path.basename(glb),"blend":os.path.basename(blend),"glb_sha256":digest},
 "geometry":{"mesh_objects":len(meshes),"vertices":sum(len(o.data.vertices) for o in meshes),"materials":len({m.name for o in meshes for m in o.data.materials if m})},
 "rig":{"name":rig.name,"bones":len(rig.data.bones),"skin_binding":"top4_normalized","animation":"Forge_Idle_Loop"},
 "features":["layered jacket","utility backpack","articulated hands","five fingers per hand","facial landmarks","hair locks","boots and shin guards","PBR materials"],
 "validation":{"uvs":"generated by Blender primitives","topology":"candidate; artist review required","deformation":"automated rig QA required"},
 "source":{"creator":"Forge 100K procedural generator","license":"CC0-1.0","source_url":None}}
 with open(os.path.join(out,aid+"-report.json"),"w",encoding="utf-8") as f: json.dump(report,f,indent=2)
 print(json.dumps(report,indent=2))
if __name__=="__main__": main()
