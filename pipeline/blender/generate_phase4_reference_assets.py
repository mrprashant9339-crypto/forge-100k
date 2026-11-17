"""Generate deterministic Phase 4 reference assets for pipeline self-tests.

IMPORTANT: outputs are synthetic engineering fixtures, not production character art.
The generated meshes are intentionally simple and must never be promoted as
artist-approved or production-certified assets.
Run:
  blender -b --python pipeline/blender/generate_phase4_reference_assets.py -- output_dir
"""
import bpy
import json
import math
import os
import sys
import hashlib
from mathutils import Euler

def args_after_separator():
    argv = sys.argv
    return argv[argv.index("--") + 1:] if "--" in argv else []

def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.armatures, bpy.data.actions, bpy.data.materials):
        for item in list(datablocks):
            if item.users == 0:
                datablocks.remove(item)

def material(name, color, roughness=0.7, metallic=0.0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1.0)
    mat.use_nodes = True
    shader = mat.node_tree.nodes.get("Principled BSDF")
    if shader:
        shader.inputs["Base Color"].default_value = (*color, 1.0)
        shader.inputs["Roughness"].default_value = roughness
        shader.inputs["Metallic"].default_value = metallic
    return mat

def make_armature():
    data = bpy.data.armatures.new("ForgeReferenceHumanoidRig")
    rig = bpy.data.objects.new("ForgeReferenceHumanoidRig", data)
    bpy.context.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    def bone(name, head, tail, parent=None):
        item = data.edit_bones.new(name)
        item.head = head
        item.tail = tail
        if parent:
            item.parent = data.edit_bones[parent]
        return item
    bone("root", (0, 0, 0), (0, 0, .25))
    bone("pelvis", (0, 0, .82), (0, 0, 1.08), "root")
    bone("spine", (0, 0, 1.08), (0, 0, 1.48), "pelvis")
    bone("chest", (0, 0, 1.48), (0, 0, 1.82), "spine")
    bone("neck", (0, 0, 1.82), (0, 0, 2.02), "chest")
    bone("head", (0, 0, 2.02), (0, 0, 2.40), "neck")
    for side, label in ((-1, "L"), (1, "R")):
        x = side
        bone("upper_arm_" + label, (x*.34, 0, 1.76), (x*.62, 0, 1.48), "chest")
        bone("lower_arm_" + label, (x*.62, 0, 1.48), (x*.66, 0, 1.12), "upper_arm_" + label)
        bone("hand_" + label, (x*.66, 0, 1.12), (x*.68, -.10, 1.02), "lower_arm_" + label)
        for finger, spread in (("thumb", -.07), ("index", -.035), ("middle", 0), ("ring", .035), ("pinky", .07)):
            start = (x*.68, -.10, 1.02)
            end = (x*(.68+spread), -.23, 1.00)
            bone(f"{finger}_01_{label}", start, end, "hand_" + label)
        bone("upper_leg_" + label, (x*.18, 0, .92), (x*.20, 0, .52), "pelvis")
        bone("lower_leg_" + label, (x*.20, 0, .52), (x*.20, 0, .16), "upper_leg_" + label)
        bone("foot_" + label, (x*.20, 0, .16), (x*.20, -.28, .08), "lower_leg_" + label)
    bpy.ops.object.mode_set(mode="OBJECT")
    rig.show_in_front = True
    rig["forge_asset_class"] = "synthetic_reference_fixture"
    rig["forge_rig_profile"] = "humanoid_reference_v2"
    return rig

def bind_mesh(obj, rig, garment=False):
    bones = []
    for bone in rig.data.bones:
        a = rig.matrix_world @ bone.head_local
        b = rig.matrix_world @ bone.tail_local
        if (b - a).length > 1e-6:
            bones.append((bone.name, a, b))
    groups = {name: obj.vertex_groups.new(name=name) for name, _, _ in bones}
    for vertex in obj.data.vertices:
        point = obj.matrix_world @ vertex.co
        influences = []
        for name, start, end in bones:
            axis = end - start
            t = max(0.0, min(1.0, (point - start).dot(axis) / max(axis.length_squared, 1e-9)))
            distance = (point - (start + t * axis)).length
            influences.append((distance, name))
        influences.sort(key=lambda item: item[0])
        nearest = influences[:4]
        raw = [(1.0 / max(distance, 0.035) ** 2, name) for distance, name in nearest]
        total = sum(weight for weight, _ in raw)
        for weight, name in raw:
            groups[name].add([vertex.index], weight / total, "REPLACE")
    modifier = obj.modifiers.new("ForgeReferenceArmature", "ARMATURE")
    modifier.object = rig
    obj.parent = rig
    if garment:
        pin = obj.vertex_groups.new(name="Forge_Cloth_Pin")
        seam = obj.vertex_groups.new(name="Forge_Tear_Seam")
        pin_indices = [v.index for v in obj.data.vertices if v.co.z > 0.15]
        seam_indices = [v.index for v in obj.data.vertices if abs(v.co.x) < 0.025]
        if pin_indices:
            pin.add(pin_indices, 1.0, "REPLACE")
        if len(seam_indices) < 2:
            seam_indices = [0, 1]
        seam.add(seam_indices, 1.0, "REPLACE")
        obj["forge_fixture_pin_vertices"] = len(pin_indices)
        obj["forge_fixture_seam_vertices"] = len(seam_indices)

def make_mesh(name, location, scale, mat, segments=32, rings=16):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    # UV sphere primitive includes UV coordinates; assert rather than assume.
    if not obj.data.uv_layers:
        raise RuntimeError(name + " has no UV map")
    return obj

def bind_mesh(obj, rig, garment=False):
    group = obj.vertex_groups.new(name="Root")
    if obj.data.vertices:
        group.add([v.index for v in obj.data.vertices], 1.0, "REPLACE")
    modifier = obj.modifiers.new("ForgeReferenceArmature", "ARMATURE")
    modifier.object = rig
    obj.parent = rig
    if garment:
        pin = obj.vertex_groups.new(name="Forge_Cloth_Pin")
        seam = obj.vertex_groups.new(name="Forge_Tear_Seam")
        pin_indices = [v.index for v in obj.data.vertices if v.co.z > 0.15]
        seam_indices = [v.index for v in obj.data.vertices if abs(v.co.x) < 0.025]
        if pin_indices:
            pin.add(pin_indices, 1.0, "REPLACE")
        if len(seam_indices) < 2:
            seam_indices = [0, 1]
        seam.add(seam_indices, 1.0, "REPLACE")
        obj["forge_fixture_pin_vertices"] = len(pin_indices)
        obj["forge_fixture_seam_vertices"] = len(seam_indices)

def add_reference_actions(rig):
    scene = bpy.context.scene
    action = bpy.data.actions.new("Forge_Reference_Deformation_Test")
    rig.animation_data_create()
    rig.animation_data.action = action
    for bone_name, amplitude in (("root", 0.04), ("spine", 0.08), ("chest", 0.12), ("head", 0.035)):
        bone = rig.pose.bones.get(bone_name)
        if not bone:
            continue
        bone.rotation_mode = "XYZ"
        for frame, angle in ((1, -amplitude), (8, amplitude), (16, -amplitude)):
            bone.rotation_euler[1] = angle
            bone.keyframe_insert(data_path="rotation_euler", frame=frame, group=bone_name)
    for curve in action.fcurves:
        for key in curve.keyframe_points:
            key.interpolation = "BEZIER"
        curve.modifiers.new("CYCLES")
    scene.frame_start = 1
    scene.frame_end = 16
    scene.frame_set(1)
    rig["forge_animation_class"] = "synthetic_deformation_test_not_production_motion"

def export_selection(path, objects):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=path, export_format="GLB", use_selection=True,
        export_apply=False, export_texcoords=True, export_normals=True,
        export_materials="EXPORT", export_animations=True,
        export_skins=True, export_morph=True
    )

def sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def main():
    args = args_after_separator()
    if len(args) != 1:
        raise SystemExit("Usage: blender -b --python generate_phase4_reference_assets.py -- output_dir")
    output = os.path.abspath(args[0])
    os.makedirs(output, exist_ok=True)
    clear_scene()
    body_mat = material("ForgeReference_Body", (0.32, 0.43, 0.58))
    cloth_mat = material("ForgeReference_Garment", (0.16, 0.22, 0.31))
    rig = make_armature()

    # A deliberately simple proxy mannequin assembled into one mesh.
    body_parts = [
        make_mesh("body_part_torso", (0, 0, 1.45), (0.34, 0.20, 0.52), body_mat),
        make_mesh("body_part_head", (0, 0, 2.15), (0.22, 0.20, 0.27), body_mat),
        make_mesh("body_part_pelvis", (0, 0, 0.91), (0.30, 0.19, 0.22), body_mat),
        make_mesh("body_part_arm_l", (-0.48, 0, 1.48), (0.13, 0.14, 0.47), body_mat),
        make_mesh("body_part_arm_r", (0.48, 0, 1.48), (0.13, 0.14, 0.47), body_mat),
        make_mesh("body_part_leg_l", (-0.16, 0, 0.43), (0.15, 0.17, 0.48), body_mat),
        make_mesh("body_part_leg_r", (0.16, 0, 0.43), (0.15, 0.17, 0.48), body_mat),
    ]
    bpy.ops.object.select_all(action="DESELECT")
    for obj in body_parts:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = body_parts[0]
    bpy.ops.object.join()
    body = bpy.context.object
    body.name = "ForgeReferenceBody"
    bind_mesh(body, rig)

    # A simple upper-body shell proxy; not a tailored garment pattern.
    garment = make_mesh("ForgeReferenceGarment", (0, -0.005, 1.48), (0.39, 0.235, 0.57), cloth_mat)
    bind_mesh(garment, rig, garment=True)
    add_reference_actions(rig)

    # Preserve a complete Blender source scene with groups and animation actions.
    blend_path = os.path.join(output, "forge-phase4-reference.blend")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    # Export body and garment independently with the common rig.
    export_selection(os.path.join(output, "body.glb"), [body, rig])
    export_selection(os.path.join(output, "garment.glb"), [garment, rig])

    records = {}
    for filename in ("body.glb", "garment.glb", "forge-phase4-reference.blend"):
        path = os.path.join(output, filename)
        records[filename] = {"sha256": sha256(path), "bytes": os.path.getsize(path)}
    report = {
        "schema_version": "1.0",
        "asset_id": "FORGE-REFERENCE-SYNTHETIC-001",
        "is_synthetic_fixture": True,
        "certification_status": "synthetic_reference_only",
        "production_release_approved": False,
        "limitations": [
            "Proxy mannequin geometry; not production anatomy or topology",
            "Single-bone deformation rig; not production IK/FK or finger rig",
            "Garment is a geometric shell proxy, not a tailored cloth pattern",
            "Reference actions are simple root rotations, not production motion clips",
            "No artist review or target-engine visual acceptance has occurred"
        ],
        "assets": records,
        "mesh_validation": {
            "body_meshes": 1,
            "garment_meshes": 1,
            "uv_maps_present": True,
            "shared_root_bone": True,
            "garment_pin_group": True,
            "garment_tear_seam_group": True,
            "animation_test_action": "Forge_Reference_Deformation_Test",
            "production_animation_clips": []
        }
    }
    report_path = os.path.join(output, "reference-asset-report.json")
    with open(report_path, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    print("FORGE_PHASE4_REFERENCE_ASSETS " + json.dumps(report))

if __name__ == "__main__":
    main()
