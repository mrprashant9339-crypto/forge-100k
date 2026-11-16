"""Generate reusable full-body animation actions and export them as glTF clips.

Usage: blender -b --python animation_library.py -- rigged.glb output.glb report.json
The clips are deterministic blockout motion, not motion-captured or combat-certified.
"""
import bpy, json, math, os, sys

CLIPS = {
 "Forge_Walk": (1, 25, 1.0),
 "Forge_Run": (31, 49, 1.65),
 "Forge_Jump": (55, 79, 1.0),
 "Forge_Combat_Ready": (85, 109, 1.0),
 "Forge_Idle_Interaction": (115, 145, 1.0),
 "Forge_Interact_Reach": (151, 181, 1.0),
}
def args():
    a=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    if len(a)!=3: raise SystemExit("Usage: -- input.glb output.glb report.json")
    return [os.path.abspath(x) for x in a]
def key(bone, frame, rot=None, loc=None):
    if bone is None: return
    if rot is not None:
        bone.rotation_mode="XYZ"; bone.rotation_euler=rot
        bone.keyframe_insert(data_path="rotation_euler",frame=frame)
    if loc is not None:
        bone.location=loc; bone.keyframe_insert(data_path="location",frame=frame)
def main():
    src,out,rpath=args()
    if not os.path.isfile(src): raise FileNotFoundError(src)
    bpy.ops.object.select_all(action="SELECT"); bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=src)
    arms=[o for o in bpy.context.scene.objects if o.type=="ARMATURE"]
    if len(arms)!=1: raise RuntimeError("Animation library requires one armature")
    arm=arms[0]; arm.animation_data_create()
    pb=arm.pose.bones
    required=("upper_leg_L","upper_leg_R","upper_arm_L","upper_arm_R","spine","head")
    missing=[n for n in required if pb.get(n) is None]
    if missing: raise RuntimeError("Humanoid animation bones missing: "+", ".join(missing))
    created=[]
    for name,(start,end,speed) in CLIPS.items():
        action=bpy.data.actions.new(name)
        arm.animation_data.action=action
        # Use symmetric cyclic phases for locomotion, distinct poses for action clips.
        if name in ("Forge_Walk","Forge_Run"):
            amplitude=0.42*speed
            for frame,phase in ((start,0),(start+6,math.pi/2),(start+12,math.pi),(start+18,3*math.pi/2),(end,2*math.pi)):
                t=phase
                key(pb.get("upper_leg_L"),frame,(amplitude*math.sin(t),0,0))
                key(pb.get("upper_leg_R"),frame,(-amplitude*math.sin(t),0,0))
                key(pb.get("upper_arm_L"),frame,(-amplitude*.72*math.sin(t),0,0))
                key(pb.get("upper_arm_R"),frame,(amplitude*.72*math.sin(t),0,0))
                key(pb.get("spine"),frame,(0.025*math.cos(t*2),0,0))
        elif name=="Forge_Jump":
            for frame,z,angle in ((start,0,0),(start+5,.25,-.25),(start+12,.65,-.5),(start+19,.25,-.2),(end,0,0)):
                key(pb.get("root"),frame,loc=(0,0,z))
                key(pb.get("upper_leg_L"),frame,(angle,0,0)); key(pb.get("upper_leg_R"),frame,(angle,0,0))
                key(pb.get("upper_arm_L"),frame,(-.8,0,0)); key(pb.get("upper_arm_R"),frame,(-.8,0,0))
        elif name=="Forge_Combat_Ready":
            for frame,arm_angle,spine_angle in ((start,0,0),(start+6,-.7,.12),(start+12,-.65,.10),(end,-.7,.12)):
                key(pb.get("upper_arm_L"),frame,(arm_angle,0,-.35))
                key(pb.get("upper_arm_R"),frame,(arm_angle,0,.35))
                key(pb.get("spine"),frame,(spine_angle,0,0))
                key(pb.get("head"),frame,(-.08,0,0))
        elif name=="Forge_Idle_Interaction":
            for frame,breath,head in ((start,0,0),(start+8,.025,.02),(start+16,0,-.02),(start+24,-.025,0),(end,0,0)):
                key(pb.get("spine"),frame,(breath,0,0)); key(pb.get("head"),frame,(head,0,0))
        else:
            for frame,reach in ((start,0),(start+8,-.25),(start+16,-.9),(start+24,-.9),(end,0)):
                key(pb.get("upper_arm_R"),frame,(reach,0,-.25))
                key(pb.get("lower_arm_R"),frame,(reach*.65,0,0))
                key(pb.get("head"),frame,(0,0,-.12 if reach else 0))
        for fc in action.fcurves:
            for kp in fc.keyframe_points: kp.interpolation="BEZIER"
        track=arm.animation_data.nla_tracks.new(); track.name=name
        track.strips.new(name,start,action)
        created.append({"name":name,"frame_start":start,"frame_end":end,
                        "duration_seconds":(end-start)/30.0,"loop":name in ("Forge_Walk","Forge_Run","Forge_Idle_Interaction")})
    arm.animation_data.action=None
    scene=bpy.context.scene; scene.render.fps=30
    scene.frame_start=1; scene.frame_end=max(v[1] for v in CLIPS.values()); scene.frame_set(1)
    bpy.ops.object.select_all(action="DESELECT"); arm.select_set(True)
    for obj in bpy.context.scene.objects:
        if obj.type in {"MESH","EMPTY"}: obj.select_set(True)
    bpy.context.view_layer.objects.active=arm
    os.makedirs(os.path.dirname(out) or ".",exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=out,export_format="GLB",use_selection=True,
        export_animations=True,export_animation_mode="NLA_TRACKS",export_skins=True,
        export_morph=True,export_texcoords=True,export_normals=True,export_materials="EXPORT",
        export_cameras=False,export_lights=False)
    report={"status":"animation_library_created","fps":30,"clips":created,
        "clip_count":len(created),"output":out,"artist_review_required":True,
        "engine_certified":False,"limitations":["Procedural keyframe blockouts; not motion capture",
        "No foot locking, root-motion retargeting, contact solving or combat choreography certification",
        "Review NLA clip names, loop seams and joint limits in target engine"]}
    os.makedirs(os.path.dirname(rpath) or ".",exist_ok=True)
    with open(rpath,"w",encoding="utf-8") as f: json.dump(report,f,indent=2)
    print("FORGE_ANIMATION_LIBRARY "+json.dumps(report))
if __name__=="__main__": main()
