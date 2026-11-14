"""Humanoid rigging worker with proximity-based smooth skin weights.

This is a production-pipeline prototype for the stylized modular blockout.
It creates a reusable skeleton, top-4 normalized vertex influences and a
looping idle clip. It does not certify game-ready deformation.
"""
import bpy
import json
import os
import sys
from mathutils import Vector

def args_after_separator():
    argv=sys.argv
    return argv[argv.index("--")+1:] if "--" in argv else []

def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

def make_bone(arm_data,name,head,tail,parent=None):
    bone=arm_data.edit_bones.new(name)
    bone.head=head
    bone.tail=tail
    if parent:
        bone.parent=arm_data.edit_bones[parent]
    return bone

def build_armature():
    data=bpy.data.armatures.new("ForgeHumanoidRig")
    arm=bpy.data.objects.new("ForgeHumanoidRig",data)
    bpy.context.collection.objects.link(arm)
    bpy.context.view_layer.objects.active=arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    make_bone(data,"root",(0,0,0),(0,0,0.25))
    make_bone(data,"pelvis",(0,0,0.82),(0,0,1.08),"root")
    make_bone(data,"spine",(0,0,1.08),(0,0,1.55),"pelvis")
    make_bone(data,"chest",(0,0,1.55),(0,0,1.85),"spine")
    make_bone(data,"neck",(0,0,1.85),(0,0,2.02),"chest")
    make_bone(data,"head",(0,0,2.02),(0,0,2.42),"neck")
    for side,label in [(-1,"L"),(1,"R")]:
        x=side
        make_bone(data,"upper_arm_"+label,(x*.35,0,1.78),(x*.66,0,1.48),"chest")
        make_bone(data,"lower_arm_"+label,(x*.66,0,1.48),(x*.68,0,1.10),"upper_arm_"+label)
        make_bone(data,"hand_"+label,(x*.68,0,1.10),(x*.68,-.02,.98),"lower_arm_"+label)
        make_bone(data,"upper_leg_"+label,(x*.20,0,.94),(x*.22,0,.52),"pelvis")
        make_bone(data,"lower_leg_"+label,(x*.22,0,.52),(x*.22,0,.16),"upper_leg_"+label)
        make_bone(data,"foot_"+label,(x*.22,0,.16),(x*.22,-.32,.08),"lower_leg_"+label)
    bpy.ops.object.mode_set(mode="OBJECT")
    arm.show_in_front=True
    return arm

def point_segment_distance(point,a,b):
    ab=b-a
    denom=ab.length_squared
    if denom < 1e-12:
        return (point-a).length
    t=max(0.0,min(1.0,(point-a).dot(ab)/denom))
    return (point-(a+t*ab)).length

def bind_smooth_weights(arm):
    bone_segments=[]
    for bone in arm.data.bones:
        a=arm.matrix_world @ bone.head_local
        b=arm.matrix_world @ bone.tail_local
        bone_segments.append((bone.name,a,b))
    mesh_count=0
    weighted_vertices=0
    for obj in [o for o in bpy.context.scene.objects if o.type=="MESH"]:
        if not obj.data.vertices:
            continue
        groups={name:obj.vertex_groups.get(name) or obj.vertex_groups.new(name=name)
                for name,_,_ in bone_segments}
        inv_arm=arm.matrix_world.inverted()
        for vertex in obj.data.vertices:
            world=obj.matrix_world @ vertex.co
            point=inv_arm @ world
            distances=sorted(
                (point_segment_distance(point,arm.data.bones[name].head_local,
                     arm.data.bones[name].tail_local),name)
                for name,_,_ in bone_segments
            )[:4]
            raw=[(1.0/max(distance,0.035)**2,name) for distance,name in distances]
            total=sum(weight for weight,_ in raw)
            for weight,name in raw:
                groups[name].add([vertex.index],weight/total,"REPLACE")
            weighted_vertices+=1
        mod=obj.modifiers.new("ForgeArmature","ARMATURE")
        mod.object=arm
        world_matrix=obj.matrix_world.copy()
        obj.parent=arm
        obj.matrix_world=world_matrix
        mesh_count+=1
    return mesh_count,weighted_vertices

def add_idle_animation(arm):
    bpy.context.view_layer.objects.active=arm
    bpy.ops.object.mode_set(mode="POSE")
    for bone_name,angles in {
        "chest":[(1,-.025),(16,.025),(31,-.025)],
        "head":[(1,0.0),(16,.018),(31,0.0)],
        "upper_arm_L":[(1,-.01),(16,.01),(31,-.01)],
        "upper_arm_R":[(1,.01),(16,-.01),(31,.01)]
    }.items():
        bone=arm.pose.bones.get(bone_name)
        if bone:
            bone.rotation_mode="XYZ"
            for frame,angle in angles:
                bone.rotation_euler[1]=angle
                bone.keyframe_insert(data_path="rotation_euler",frame=frame,group="Idle")
    bpy.ops.object.mode_set(mode="OBJECT")
    action=arm.animation_data.action if arm.animation_data else None
    if action:
        action.name="Forge_Idle_Loop"
        for curve in action.fcurves:
            for key in curve.keyframe_points:
                key.interpolation="BEZIER"
            curve.modifiers.new("CYCLES")
    scene=bpy.context.scene
    scene.frame_start=1
    scene.frame_end=30
    scene.frame_set(1)

def main():
    args=args_after_separator()
    if len(args)!=2:
        raise SystemExit("Usage: rig_character.py -- input.glb output.glb")
    source,output=map(os.path.abspath,args)
    if not os.path.isfile(source):
        raise FileNotFoundError(source)
    clear_scene()
    bpy.ops.import_scene.gltf(filepath=source)
    arm=build_armature()
    mesh_count,vertex_count=bind_smooth_weights(arm)
    add_idle_animation(arm)
    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True)
    for obj in bpy.context.scene.objects:
        if obj.type=="MESH":
            obj.select_set(True)
    bpy.context.view_layer.objects.active=arm
    os.makedirs(os.path.dirname(output) or ".",exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=output,export_format="GLB",use_selection=True,
        export_animations=True,export_skins=True,export_texcoords=True,export_normals=True,
        export_materials="EXPORT",export_cameras=False,export_lights=False)
    report={"input":source,"output":output,"mesh_count":mesh_count,
        "weighted_vertices":vertex_count,"rig":"ForgeHumanoidRig",
        "skin_weights":"top-4 inverse-distance normalized",
        "animation":"Forge_Idle_Loop","quality_tier":"prototype_smooth_rig",
        "game_ready":False,"notes":"Requires deformation QA, retargeting and artist approval."}
    with open(output+".rig-report.json","w",encoding="utf-8") as handle:
        json.dump(report,handle,indent=2)
    print("FORGE_RIGGED "+json.dumps(report))

if __name__=="__main__":
    main()
