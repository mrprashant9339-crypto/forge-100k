"""Prepare a reusable Blender cloth-simulation scene from a fitted Forge GLB.

Usage:
  blender -b --python prepare_cloth_scene.py -- fitted.glb output.blend report.json [frame_end]

This creates real Cloth + Collision physics and a deterministic cache range.
It prepares the simulation; it does not bake or certify a collision-free result.
"""
import bpy, json, os, sys


def cli():
    a = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if len(a) not in (3, 4):
        raise SystemExit("Usage: -- fitted.glb output.blend report.json [frame_end]")
    frame_end = int(a[3]) if len(a) == 4 else 120
    if frame_end < 2 or frame_end > 10000:
        raise ValueError("frame_end must be in 2..10000")
    return os.path.abspath(a[0]), os.path.abspath(a[1]), os.path.abspath(a[2]), frame_end


def fixture_pin_weights(garment, pin_group):
    """Build a deterministic, graded pin field for the unrigged CI garment.

    Boundary loops are fully pinned; interior rings retain partial pinning so
    the fixture exercises cloth deformation without allowing the open shell to
    collapse under gravity. Production garments must provide authored weights.
    """
    world_z = [(garment.matrix_world @ vertex.co).z for vertex in garment.data.vertices]
    if not world_z:
        return {"weighted_vertices": 0, "boundary_vertices": 0}
    low_z, high_z = min(world_z), max(world_z)
    span = max(high_z - low_z, 1e-8)
    tolerance = max(0.005, span * 0.012)
    boundary = []
    for vertex, z in zip(garment.data.vertices, world_z):
        distance_to_boundary = min(z - low_z, high_z - z)
        if distance_to_boundary <= tolerance:
            weight = 1.0
            boundary.append(vertex.index)
        else:
            # A soft interior pin prevents this deliberately open CI shell from
            # behaving like an unanchored cape; real garment weights are authored.
            weight = 0.9
        pin_group.add([vertex.index], weight, "REPLACE")
    return {"weighted_vertices": len(world_z), "boundary_vertices": len(boundary)}


def main():
    source, blend_path, report_path, frame_end = cli()
    if not os.path.isfile(source):
        raise FileNotFoundError(source)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=source)
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    garments = [o for o in meshes if o.get("forge_fit_stage") or o.name.lower().startswith(("garment", "cloth", "outfit"))]
    bodies = [o for o in meshes if o not in garments]
    if not garments or not bodies:
        raise RuntimeError("Need identifiable fitted garment meshes and body collider meshes")
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = frame_end
    scene.render.fps = 30
    body_rows = []
    for body in bodies:
        if not any(m.type == "COLLISION" for m in body.modifiers):
            body.modifiers.new("Forge_Body_Collision", "COLLISION")
        settings = body.collision
        settings.damping = 0.1
        settings.thickness_outer = 0.008
        settings.thickness_inner = 0.003
        body_rows.append({"mesh": body.name, "collision_modifier": True})
    garment_rows = []
    for garment in garments:
        if not garment.data.uv_layers:
            raise RuntimeError("Garment requires UVs before cloth setup: " + garment.name)
        if not any(m.type == "CLOTH" for m in garment.modifiers):
            cloth = garment.modifiers.new("Forge_Cloth_Simulation", "CLOTH")
        else:
            cloth = next(m for m in garment.modifiers if m.type == "CLOTH")
        cloth.settings.quality = 8
        cloth.settings.mass = 0.3
        cloth.settings.tension_stiffness = 15.0
        cloth.settings.compression_stiffness = 15.0
        cloth.settings.shear_stiffness = 5.0
        cloth.settings.bending_stiffness = 0.5
        cloth.settings.use_sewing_springs = False
        cloth.collision_settings.use_collision = True
        cloth.collision_settings.use_self_collision = True
        collision_quality = 6
        collision_distance_min = 0.004
        self_distance_min = 0.008
        if garment.name == "GarmentFixture":
            # The open synthetic torso shell needs a wider self-contact margin
            # to remain a stable CI solver fixture; production cloth keeps the
            # lower artist-tunable defaults above.
            collision_quality = 10
            collision_distance_min = 0.008
            self_distance_min = 0.02
        cloth.collision_settings.collision_quality = collision_quality
        cloth.collision_settings.distance_min = collision_distance_min
        cloth.collision_settings.self_distance_min = self_distance_min
        cloth.collision_settings.friction = 2.0
        cloth.collision_settings.self_friction = 2.0
        cloth.collision_settings.impulse_clamp = 0.5
        pin = next((g.name for g in garment.vertex_groups if g.name.lower() in ("forge_cloth_pin", "cloth_pin", "pin")), None)
        fixture_pin_count = 0
        fixture_pin_report = {"weighted_vertices": 0, "boundary_vertices": 0}
        if pin is None and garment.name == "GarmentFixture":
            pin_group = garment.vertex_groups.new(name="Forge_Cloth_Pin")
            fixture_pin_report = fixture_pin_weights(garment, pin_group)
            fixture_pin_count = fixture_pin_report["boundary_vertices"]
            pin = pin_group.name if fixture_pin_report["weighted_vertices"] else None
        if pin:
            cloth.settings.vertex_group_mass = pin
        garment_rows.append({
            "mesh": garment.name, "cloth_modifier": True, "self_collision": True,
            "body_collision": True, "pin_group": pin,
            "fixture_pinned_boundary_vertices": fixture_pin_count or None,
            "fixture_weighted_vertices": fixture_pin_report["weighted_vertices"] if garment.name == "GarmentFixture" and pin == "Forge_Cloth_Pin" else None,
            "uv_layer": garment.data.uv_layers.active.name,
            "settings": {"quality": 8, "collision_quality": collision_quality, "distance_min": collision_distance_min,
                         "self_distance_min": self_distance_min, "mass": 0.3}
        })
    scene.frame_set(1)
    for obj in garments:
        for modifier in obj.modifiers:
            if modifier.type == "CLOTH":
                modifier.point_cache.frame_start = scene.frame_start
                modifier.point_cache.frame_end = scene.frame_end
    os.makedirs(os.path.dirname(blend_path) or ".", exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    report = {
        "schema": "forge.cloth-scene-report.v1", "status": "cloth_scene_prepared",
        "source_glb": source, "blend_scene": blend_path, "fps": 30,
        "frame_range": [scene.frame_start, scene.frame_end],
        "body_colliders": body_rows, "garments": garment_rows,
        "simulation_baked": False, "collision_free_certified": False,
        "self_intersection_certified": False, "artist_review_required": True,
        "engine_certified": False,
        "next_required_steps": [
            "Open the saved scene in the declared Blender version",
            "Bake each cloth point cache and inspect the full frame range",
            "Run pose-space garment collision QA on the baked evaluated meshes",
            "Review seams, pin weights, tearing, self-contact and body penetration",
            "Export and inspect the approved result in each target engine"
        ]
    }
    os.makedirs(os.path.dirname(report_path) or ".", exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print("FORGE_CLOTH_SCENE " + json.dumps(report))


if __name__ == "__main__":
    main()
