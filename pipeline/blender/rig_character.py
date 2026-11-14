"""Rigging stage for Forge 100K starter blockouts.

Run:
 blender --background --python pipeline/blender/rig_character.py -- input.glb output.glb

Creates a humanoid skeleton, rigid per-part skin weights, and a looping
starter idle animation. This is a pipeline integration rig, not deformable
production skinning. Human QA and deformation tests remain required.
"""
import bpy
import json
import os
import sys
from mathutils import Euler

def args_after_separator():
    argv=sys.argv
    return argv[argv.index("--")+1:] if "--" in argv else []

def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

def make_bone(arm_data,name,head,tail,parent=None,connected=False):
    bone=arm_data.edit_bones.new(name)
    bone.head=head
    bone.tail=tail
    if parent:
        bone.parent=arm_data.edit_bones[parent]
        bone.use_connect=connected
    return bone

def build_armature():
    arm_data=bpy.data.armatures.new("ForgeHumanoidRig")
    arm=bpy.data.objects.new("ForgeHumanoidRig",arm_data)
    bpy.context.collection.objects.link(arm)
    bpy.context.view_layer.objects.active=arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    make_bone(arm_data,"root",(0,0,0),(0,0,0.25))
    make_bone(arm_data,"pelvis",(0,0,0.82),(0,0,1.08),"root")
    make_bone(arm_data,"spine",(0,0,1.08),(0,0,1.55),"pelvis")
    make_bone(arm_data,"chest",(0,0,1.55),(0,0,1.85),"spine")
    make_bone(arm_data,"neck",(0,0,1.85),(0,0,2.02),"chest")
    make_bone(arm_data,"head",(0,0,2.02),(0,0,2.42),"neck")
    for side,label in [(-1,"L"),(1,"R")]:
        x=side
        make_bone(arm_data,"upper_arm_"+label,(x*0.35,0,1.78),(x*0.66,0,1.48),"chest")
        make_bone(arm_data,"lower_arm_"+label,(x*0.66,0,1.48),(x*0.68,0,1.10),"upper_arm_"+label)
        make_bone(arm_data,"hand_"+label,(x*0.68,0,1.10),(x*0.68,-0.02,0.98),"lower_arm_"+label)
        make_bone(arm_data,"upper_leg_"+label,(x*0.20,0,0.94),(x*0.22,0,0.52),"pelvis")
        make_bone(arm_data,"lower_leg_"+label,(x*0.22,0,0.52),(x*0.22,0,0.16),"upper_leg_"+label)
        make_bone(arm_data,"foot_"+label,(x*0.22,0,0.16),(x*0.22,-0.32,0.08),"lower_leg_"+label)
    bpy.ops.object.mode_set(mode="OBJECT")
    arm.show_in_front=True
    return arm

def choose_bone(obj):
    n=obj.name.lower()
    if "head" in n or "eye" in n: return "head"
    if "torso" in n or "chestplate" in n or "shoulder" in n: return "chest"
    if "pelvis" in n: return "pelvis"
    if "boot" in n: return "foot_"+("L" if n.endswith("_l") else "R")
    if "leg" in n: return "lower_leg_"+("L" if n.endswith("_l") else "R")
    if "arm" in n: return "upper_arm_"+("L" if n.endswith("_l") else "R")
    return "spine"

def bind_rigid_parts(arm):
    mesh_count=0
    for obj in [o for o in bpy.context.scene.objects if o.type=="MESH"]:
        bone=choose_bone(obj)
        group=obj.vertex_groups.get(bone) or obj.vertex_groups.new(name=bone)
        if obj.data.vertices:
            group.add([v.index for v in obj.data.vertices],1.0,"REPLACE")
        mod=obj.modifiers.new("ForgeArmature","ARMATURE")
        mod.object=arm
        world=obj.matrix_world.copy()
        obj.parent=arm
        obj.matrix_world=world
        mesh_count+=1
    return mesh_count

def add_idle_animation(arm):
    bpy.context.view_layer.objects.active=arm
    bpy.ops.object.mode_set(mode="POSE")
    chest=arm.pose.bones.get("chest")
    if chest:
        chest.rotation_mode="XYZ"
        for frame,angle in [(1,-0.025),(16,0.025),(31,-0.025)]:
            chest.rotation_euler[1]=angle
            chest.keyframe_insert(data_path="rotation_euler",frame=frame,group="Idle")
    head=arm.pose.bones.get("head")
    if head:
        head.rotation_mode="XYZ"
        for frame,angle in [(1,0.0),(16,0.018),(31,0.0)]:
            head.rotation_euler[1]=angle
            head.keyframe_insert(data_path="rotation_euler",frame=frame,group="Idle")
    bpy.ops.object.mode_set(mode="OBJECT")
    action=arm.animation_data.action if arm.animation_data else None
    if action:
        action.name="Forge_Idle_Loop"
        for fc in action.fcurves:
            for key in fc.keyframe_points:
                key.interpolation="BEZIER"
            fc.modifiers.new("CYCLES")
    scene=bpy.context.scene
    scene.frame_start=1
    scene.frame_end=30
    scene.frame_set(1)

def main():
    args=args_after_separator()
    if len(args)!=2:
        raise SystemExit("Usage: rig_character.py -- input.glb output.glb")
    source=os.path.abspath(args[0])
    output=os.path.abspath(args[1])
    if not os.path.isfile(source):
        raise FileNotFoundError(source)
    clear_scene()
    bpy.ops.import_scene.gltf(filepath=source)
    arm=build_armature()
    mesh_count=bind_rigid_parts(arm)
    add_idle_animation(arm)
    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True)
    for obj in bpy.context.scene.objects:
        if obj.type=="MESH": obj.select_set(True)
    bpy.context.view_layer.objects.active=arm
    os.makedirs(os.path.dirname(output) or ".",exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=output,export_format="GLB",use_selection=True,
        export_animations=True,export_skins=True,export_texcoords=True,export_normals=True,
        export_materials="EXPORT",export_cameras=False,export_lights=False)
    report={"input":source,"output":output,"mesh_count":mesh_count,
        "rig":"ForgeHumanoidRig","skin_weights":"rigid-per-part",
        "animation":"Forge_Idle_Loop","quality_tier":"prototype_rig",
        "game_ready":False,"notes":"Requires deforming skin weights, retargeting and QA."}
    with open(output+".rig-report.json","w",encoding="utf-8") as f:
        json.dump(report,f,indent=2)
    print("FORGE_RIGGED "+json.dumps(report))

if __name__=="__main__":
    main()
