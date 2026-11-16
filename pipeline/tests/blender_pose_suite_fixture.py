"""Create a deterministic rigged garment pose-suite fixture for Phase 4.1.

Usage: blender --background --python blender_pose_suite_fixture.py -- output.blend
"""
import bpy
import math
import os
import sys


def args():
    values = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if len(values) != 1:
        raise SystemExit("Usage: -- output.blend")
    return os.path.abspath(values[0])


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)


def make_rig():
    data = bpy.data.armatures.new("ForgePoseRig")
    rig = bpy.data.objects.new("ForgePoseRig", data)
    bpy.context.scene.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    bones = {
        "root": ((0, 0, 0), (0, 0, 1.0), None),
        "spine": ((0, 0, 1.0), (0, 0, 1.75), "root"),
        "upper_arm.L": ((0, 0, 1.58), (-0.62, 0, 1.48), "spine"),
        "upper_arm.R": ((0, 0, 1.58), (0.62, 0, 1.48), "spine"),
        "thigh.L": ((0, 0, 0.95), (-0.18, 0, 0.25), "root"),
        "thigh.R": ((0, 0, 0.95), (0.18, 0, 0.25), "root"),
    }
    for name, (head, tail, parent) in bones.items():
        bone = data.edit_bones.new(name)
        bone.head, bone.tail = head, tail
        if parent:
            bone.parent = data.edit_bones[parent]
            bone.use_connect = False
    bpy.ops.object.mode_set(mode="OBJECT")
    rig.select_set(False)
    return rig


def add_weights(obj, rig, group_name):
    group = obj.vertex_groups.new(name=group_name)
    group.add([v.index for v in obj.data.vertices], 1.0, "REPLACE")
    modifier = obj.modifiers.new("Forge_Armature", "ARMATURE")
    modifier.object = rig
    obj.parent = rig
    return group


def create_actions(rig):
    poses = {
        "Forge_Walk": {
            "spine": (0.04, 0.0, 0.0), "upper_arm.L": (0.10, 0.0, 0.0),
            "upper_arm.R": (-0.10, 0.0, 0.0), "thigh.L": (-0.08, 0.0, 0.0),
            "thigh.R": (0.08, 0.0, 0.0),
        },
        "Forge_Run": {
            "spine": (0.08, 0.0, 0.0), "upper_arm.L": (0.22, 0.0, 0.0),
            "upper_arm.R": (-0.22, 0.0, 0.0), "thigh.L": (-0.18, 0.0, 0.0),
            "thigh.R": (0.18, 0.0, 0.0),
        },
        "Forge_Jump": {
            "spine": (-0.10, 0.0, 0.0), "upper_arm.L": (-0.20, 0.0, 0.0),
            "upper_arm.R": (-0.20, 0.0, 0.0), "thigh.L": (0.10, 0.0, 0.0),
            "thigh.R": (0.10, 0.0, 0.0),
        },
        "Forge_Combat": {
            "spine": (0.12, 0.0, 0.05), "upper_arm.L": (-0.25, 0.0, 0.0),
            "upper_arm.R": (0.28, 0.0, 0.0), "thigh.L": (-0.10, 0.0, 0.0),
            "thigh.R": (0.10, 0.0, 0.0),
        },
    }
    for action_name, pose in poses.items():
        action = bpy.data.actions.new(action_name)
        rig.animation_data_create()
        rig.animation_data.action = action
        for bone_name, rotation in pose.items():
            bone = rig.pose.bones[bone_name]
            bone.rotation_mode = "XYZ"
            for frame, multiplier in ((1, 0.0), (8, 1.0), (16, 0.0)):
                bone.rotation_euler = tuple(value * multiplier for value in rotation)
                bone.keyframe_insert(data_path="rotation_euler", frame=frame, group=bone_name)
        action.use_fake_user = True
    rig.animation_data.action = bpy.data.actions.get("Forge_Walk")


def main():
    output = args()
    clear_scene()
    rig = make_rig()

    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=20, location=(0, 0, 1.0))
    body = bpy.context.object
    body.name = "BodyPoseFixture"
    body.scale = (0.44, 0.29, 0.90)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    add_weights(body, rig, "spine")

    segments = 32
    levels = [
        (0.50, 0.35, 0.48), (0.51, 0.36, 0.62), (0.52, 0.37, 0.78),
        (0.52, 0.37, 0.94), (0.51, 0.36, 1.10), (0.50, 0.35, 1.26),
        (0.49, 0.34, 1.42), (0.48, 0.33, 1.58), (0.47, 0.32, 1.72),
    ]
    vertices, faces = [], []
    for rx, ry, z in levels:
        for index in range(segments):
            angle = 2.0 * math.pi * index / segments
            vertices.append((rx * math.cos(angle), ry * math.sin(angle), z))
    for ring in range(len(levels) - 1):
        for index in range(segments):
            a = ring * segments + index
            b = ring * segments + (index + 1) % segments
            c = (ring + 1) * segments + (index + 1) % segments
            d = (ring + 1) * segments + index
            faces.append((a, b, c, d))
    mesh = bpy.data.meshes.new("GarmentPoseFixtureMesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    garment = bpy.data.objects.new("GarmentPoseFixture", mesh)
    bpy.context.scene.collection.objects.link(garment)
    garment.data.uv_layers.new(name="UVMap")
    add_weights(garment, rig, "spine")
    garment["forge_body_collider"] = body.name

    # Add real Blender body collision and garment cloth/self-collision physics.
    body_collision = body.modifiers.new("Forge_Body_Collision", "COLLISION")
    body.collision.damping = 0.1
    body.collision.thickness_outer = 0.008
    body.collision.thickness_inner = 0.003

    cloth = garment.modifiers.new("Forge_Cloth_Simulation", "CLOTH")
    cloth.settings.quality = 8
    cloth.settings.mass = 0.3
    cloth.settings.tension_stiffness = 15.0
    cloth.settings.compression_stiffness = 15.0
    cloth.settings.shear_stiffness = 5.0
    cloth.settings.bending_stiffness = 0.5
    cloth.collision_settings.use_collision = True
    cloth.collision_settings.use_self_collision = True
    cloth.collision_settings.collision_quality = 10
    cloth.collision_settings.distance_min = 0.008
    cloth.collision_settings.self_distance_min = 0.02
    cloth.collision_settings.friction = 2.0
    cloth.collision_settings.self_friction = 2.0

    pin = garment.vertex_groups.new(name="Forge_Cloth_Pin")
    z_values = [vertex.co.z for vertex in garment.data.vertices]
    low_z, high_z = min(z_values), max(z_values)
    tolerance = max(0.005, (high_z - low_z) * 0.012)
    for vertex in garment.data.vertices:
        boundary_distance = min(vertex.co.z - low_z, high_z - vertex.co.z)
        pin.add([vertex.index], 1.0 if boundary_distance <= tolerance else 0.9, "REPLACE")
    cloth.settings.vertex_group_mass = pin.name

    # Mark one continuous vertical seam for the authored tear workflow.
    tear_seam = garment.vertex_groups.new(name="Forge_Tear_Seam")
    tear_seam.add([ring * segments for ring in range(len(levels))], 1.0, "REPLACE")

    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = 1, 16
    create_actions(rig)
    bpy.context.view_layer.update()
    os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=output)
    print("FORGE_POSE_FIXTURE_CREATED " + output)


if __name__ == "__main__":
    main()
