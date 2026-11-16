"""Add humanoid IK/FK controls, finger chains and facial joints to a rigged GLB.

Usage: blender -b --python advanced_rig_controls.py -- input.glb output.glb report.json
Controls are DCC rig controls; exported GLB contains deform skeleton and baked
starter constraints only where the glTF exporter supports them.
"""
import bpy, json, math, os, sys
from mathutils import Vector

def args():
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if len(a) != 3: raise SystemExit("Usage: -- input.glb output.glb report.json")
    return [os.path.abspath(x) for x in a]

def main():
    src, out, report_path = args()
    if not os.path.isfile(src): raise FileNotFoundError(src)
    bpy.ops.object.select_all(action="SELECT"); bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=src)
    arms = [o for o in bpy.context.scene.objects if o.type == "ARMATURE"]
    if len(arms) != 1: raise RuntimeError("Expected exactly one armature")
    arm = arms[0]
    names = set(arm.data.bones.keys())
    if not {"root", "head", "chest"}.issubset(names):
        raise RuntimeError("Advanced humanoid controls require root, chest and head bones")
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm.data.edit_bones
    def add(name, head, tail, parent, deform=False):
        if name in eb: return eb[name]
        bone = eb.new(name); bone.head = head; bone.tail = tail
        bone.parent = eb.get(parent) if parent else None
        bone.use_deform = deform
        return bone
    # Finger chains are deform bones parented to each hand.
    finger_names = ("thumb", "index", "middle", "ring", "pinky")
    for side, sign in (("L", -1.0), ("R", 1.0)):
        hand = eb.get("hand_" + side)
        if hand is None: continue
        base_x = hand.tail.x
        for fi, finger in enumerate(finger_names):
            spread = (fi - 2) * 0.035
            start = Vector((base_x + sign * (0.025 + fi * 0.008), hand.tail.y, hand.tail.z - 0.015))
            parent = "hand_" + side
            for segment in range(1, 4):
                end = start + Vector((sign * 0.018, -0.025, -0.012 + spread * 0.08))
                name = "finger_%s_%s_%d" % (finger, side, segment)
                add(name, start, end, parent, True)
                start = end; parent = name
        # IK target and pole controls are non-deforming bones.
        upper = eb.get("upper_arm_" + side); lower = eb.get("lower_arm_" + side)
        if upper and lower:
            add("CTRL_hand_IK_" + side, lower.tail, lower.tail + Vector((0, -0.12, 0)), "root")
            add("CTRL_elbow_pole_" + side, Vector((sign * 0.9, -0.25, 1.45)),
                Vector((sign * 0.9, -0.25, 1.55)), "root")
        thigh = eb.get("upper_leg_" + side); shin = eb.get("lower_leg_" + side)
        if thigh and shin:
            add("CTRL_foot_IK_" + side, shin.tail, shin.tail + Vector((0, -0.12, 0)), "root")
            add("CTRL_knee_pole_" + side, Vector((sign * 0.65, -0.45, 0.5)),
                Vector((sign * 0.65, -0.45, 0.6)), "root")
        # Facial joints: eye aim and jaw hinge.
        head = eb["head"]
        add("FAC_eye_" + side, (sign * 0.105, -0.19, 2.15),
            (sign * 0.105, -0.29, 2.15), "head", True)
    add("FAC_jaw", (0, -0.16, 2.00), (0, -0.22, 1.91), "head", True)
    add("FAC_eye_target", (0, -1.0, 2.15), (0, -1.1, 2.15), "root", False)
    bpy.ops.object.mode_set(mode="OBJECT")
    # IK constraints and switch property. The original deform chain remains the FK path.
    arm["forge_ik_fk_switch"] = 1.0
    arm["forge_ik_fk_switch_description"] = "0=FK, 1=IK; animate this property in Blender"
    ik_count = 0
    ik_pole_targets = 0
    for side in ("L", "R"):
        for lower_name, target_name, pole_name, chain in (
            ("lower_arm_" + side, "CTRL_hand_IK_" + side, "CTRL_elbow_pole_" + side, 2),
            ("lower_leg_" + side, "CTRL_foot_IK_" + side, "CTRL_knee_pole_" + side, 2)):
            pose = arm.pose.bones.get(lower_name)
            if pose and arm.pose.bones.get(target_name) and arm.pose.bones.get(pole_name):
                con = pose.constraints.new("IK"); con.name = "Forge_IK_" + side + "_" + lower_name
                con.target = arm; con.subtarget = target_name; con.chain_count = chain
                con.pole_target = arm; con.pole_subtarget = pole_name
                con.pole_angle = 0.0
                con.use_stretch = False
                ik_pole_targets += 1
                driver = con.driver_add("influence").driver
                var = driver.variables.new(); var.name = "ik"
                var.type = "SINGLE_PROP"
                var.targets[0].id = arm
                var.targets[0].data_path = '["forge_ik_fk_switch"]'
                driver.expression = "min(1.0,max(0.0,ik))"
                ik_count += 1
    # Eye aim controls: move CTRL/FAC_eye_target in Blender to drive both eyes.
    eye_tracking_constraints = 0
    for side in ("L", "R"):
        eye = arm.pose.bones.get("FAC_eye_" + side)
        if eye:
            constraint = eye.constraints.new("DAMPED_TRACK")
            constraint.name = "Forge_Eye_Gaze_" + side
            constraint.target = arm
            constraint.subtarget = "FAC_eye_target"
            constraint.track_axis = "TRACK_NEGATIVE_Y"
            eye_tracking_constraints += 1
    # Facial groups bias existing head mesh vertices toward the new facial joints.
    face_meshes = [o for o in bpy.context.scene.objects if o.type == "MESH" and o.name.lower().startswith("head")]
    assigned = 0
    for mesh in face_meshes:
        for side, sign in (("L", -1.0), ("R", 1.0)):
            group = mesh.vertex_groups.get("FAC_eye_" + side) or mesh.vertex_groups.new(name="FAC_eye_" + side)
            for v in mesh.data.vertices:
                p = mesh.matrix_world @ v.co
                d = ((p.x - sign * 0.105) ** 2 + (p.y + 0.19) ** 2 + (p.z - 2.15) ** 2) ** 0.5
                if d < 0.11: group.add([v.index], max(0.05, 1.0 - d / 0.11), "REPLACE"); assigned += 1
        jaw = mesh.vertex_groups.get("FAC_jaw") or mesh.vertex_groups.new(name="FAC_jaw")
        for v in mesh.data.vertices:
            p = mesh.matrix_world @ v.co
            d = ((p.x) ** 2 + (p.y + 0.16) ** 2 + (p.z - 1.98) ** 2) ** 0.5
            if d < 0.15: jaw.add([v.index], max(0.05, 1.0 - d / 0.15), "REPLACE"); assigned += 1
    # Re-normalize all skin weights and enforce the glTF four-influence limit
    # after adding facial groups. This avoids invalid >4 influence vertices.
    for mesh in [o for o in bpy.context.scene.objects if o.type == "MESH"]:
        group_by_index = {g.index: g for g in mesh.vertex_groups}
        for vertex in mesh.data.vertices:
            memberships = sorted(
                [(float(item.weight), item.group) for item in vertex.groups if item.weight > 1e-8],
                reverse=True
            )
            keep = memberships[:4]
            keep_ids = {group_id for _, group_id in keep}
            for _, group_id in memberships[4:]:
                group_by_index[group_id].remove([vertex.index])
            total = sum(weight for weight, _ in keep)
            if total > 1e-8:
                for weight, group_id in keep:
                    group_by_index[group_id].add([vertex.index], weight / total, "REPLACE")
    # Preserve existing armature modifiers; new facial groups are supplemental.
    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True)
    for obj in bpy.context.scene.objects:
        if obj.type in {"MESH", "EMPTY"}: obj.select_set(True)
    bpy.context.view_layer.objects.active = arm
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=out, export_format="GLB", use_selection=True,
        export_animations=True, export_skins=True, export_morph=True,
        export_texcoords=True, export_normals=True, export_materials="EXPORT",
        export_cameras=False, export_lights=False, export_extras=True)
    report = {"status":"advanced_rig_controls_added","input":src,"output":out,
        "bone_count":len(arm.data.bones),"finger_bones":sum(1 for b in arm.data.bones if b.name.startswith("finger_")),
        "facial_bones":[n for n in arm.data.bones.keys() if n.startswith("FAC_")],
        "ik_constraints":ik_count,"ik_pole_targets":ik_pole_targets,"eye_tracking_constraints":eye_tracking_constraints,"ik_fk_switch_property":"forge_ik_fk_switch",
        "facial_group_vertex_assignments":assigned,"artist_review_required":True,
        "engine_certified":False,"limitations":["IK/FK switching and pole placement require animator calibration",
        "Facial bone weights are proximity-seeded and require sculpt/weight-paint review",
        "glTF does not preserve Blender custom control widgets or constraint UI; bake constraints for runtime export"]}
    os.makedirs(os.path.dirname(report_path) or ".",exist_ok=True)
    with open(report_path,"w",encoding="utf-8") as f: json.dump(report,f,indent=2)
    print("FORGE_ADVANCED_RIG "+json.dumps(report))
if __name__ == "__main__": main()
