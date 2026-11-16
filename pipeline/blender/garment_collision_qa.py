"""Run static and pose-sampled garment/body clearance checks on a fitted GLB.

Usage: blender -b --python garment_collision_qa.py -- fitted.glb fit-report.json output.json
This detects sampled body penetration candidates and non-adjacent triangle overlaps;
it is not a cloth solver or a substitute for production physics validation.
"""
import bpy, bmesh, json, math, os, sys
from mathutils import Vector
from mathutils.bvhtree import BVHTree

def args():
    a=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    if len(a)!=3: raise SystemExit("Usage: -- fitted.glb fit-report.json output.json")
    return [os.path.abspath(x) for x in a]
def ray_parity(tree, point):
    direction=Vector((1.0,0.000173,0.000319)).normalized()
    origin=point.copy(); hits=0
    for _ in range(64):
        loc,normal,index,distance=tree.ray_cast(origin,direction,1.0e4)
        if loc is None: break
        hits+=1; origin=loc+direction*1.0e-4
    return hits % 2 == 1
def main():
    src,fit_path,out=args()
    for p in (src,fit_path):
        if not os.path.isfile(p): raise FileNotFoundError(p)
    with open(fit_path,encoding="utf-8") as f: fit=json.load(f)
    if fit.get("status")!="proxy_fit_complete": raise ValueError("Fit report not complete")
    bpy.ops.object.select_all(action="SELECT"); bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=src)
    all_meshes=[o for o in bpy.context.scene.objects if o.type=="MESH"]
    garment_names={x.get("mesh") for x in fit.get("garments",[])}
    body_names=set(fit.get("body_meshes",[]))
    garments=[o for o in all_meshes if o.name in garment_names]
    bodies=[o for o in all_meshes if o.name in body_names] if body_names else [o for o in all_meshes if o.name not in garment_names]
    if not garments or not bodies: raise RuntimeError("Need body and garment meshes in fitted GLB")
    # Keep body parts as independent BVHs. A parity test against one merged
    # BVH incorrectly cancels intersections where body parts overlap.
    depsgraph=bpy.context.evaluated_depsgraph_get()
    body_trees=[]
    for body in bodies:
        tree=BVHTree.FromObject(body,depsgraph,epsilon=0.0)
        if tree is not None: body_trees.append((body.name,tree))
    if not body_trees: raise RuntimeError("Could not build per-part body BVHs")
    def inside_any(point):
        return any(ray_parity(tree,point) for _,tree in body_trees)
    results=[]; hard_failures=[]; review_meshes=[]
    for garment in garments:
        coords=[garment.matrix_world@v.co for v in garment.data.vertices]
        # Rest-pose signed-inside test with parity ray casting.
        inside=[i for i,p in enumerate(coords) if inside_any(p)]
        distances=[]
        for p in coords:
            nearest_hits=[tree.find_nearest(p) for _,tree in body_trees]
            nearest_hits=[hit for hit in nearest_hits if hit and hit[0] is not None]
            if nearest_hits: distances.append(min(float(hit[3]) for hit in nearest_hits))
        # Sample simple shoulder/hip articulation transforms without changing source data.
        pose_samples=[]
        original=garment.matrix_world.copy()
        center=sum(coords,Vector())/max(1,len(coords))
        for angle in (-0.25,0.0,0.25):
            from mathutils import Matrix
            rot=Matrix.Translation(center) @ Matrix.Rotation(angle,4,'X') @ Matrix.Translation(-center)
            transformed=[rot@p for p in coords]
            penetrations=sum(1 for p in transformed if inside_any(p))
            pose_samples.append({"rotation_x_radians":angle,"inside_body_vertices":penetrations})
        # BVH self-overlap candidates; exclude face pairs sharing vertices.
        bm=bmesh.new(); bm.from_mesh(garment.data); bm.verts.ensure_lookup_table(); bm.faces.ensure_lookup_table()
        self_pairs=[]
        if bm.faces:
            local_tree=BVHTree.FromBMesh(bm)
            for a,b in local_tree.overlap(local_tree):
                if a>=b: continue
                if set(v.index for v in bm.faces[a].verts).isdisjoint(v.index for v in bm.faces[b].verts):
                    self_pairs.append([a,b])
        bm.free()
        issue=[]
        blocking=[]
        if inside:
            issue.append("rest_pose_body_penetration_candidates")
            blocking.append("rest_pose_body_penetration_candidates")
        if any(x["inside_body_vertices"] for x in pose_samples):
            issue.append("synthetic_garment_only_rotation_candidates")
        if self_pairs:
            issue.append("bvh_self_overlap_candidates")
        row={"mesh":garment.name,"vertex_count":len(coords),"rest_inside_body_vertices":len(inside),
            "minimum_body_surface_distance":min(distances) if distances else None,
            "pose_samples":pose_samples,"self_intersection_triangle_pairs":len(self_pairs),
            "self_intersection_pairs_sample":self_pairs[:100],"issues":issue,
            "blocking_issues":blocking,
            "status":"blocking_rest_penetration" if blocking else ("review_candidates_found" if issue else "sampled_clearance_preflight_passed")}
        results.append(row)
        if issue: review_meshes.append(garment.name)
        if blocking: hard_failures.append(garment.name)
    report={"status":"blocking_rest_penetration" if hard_failures else ("review_candidates_found" if review_meshes else "sampled_clearance_preflight_passed"),
        "input":src,"garment_count":len(garments),"results":results,"failed_meshes":hard_failures,
        "review_required_meshes":review_meshes,
        "body_parts_tested":[name for name,_ in body_trees],"pose_sampling":"synthetic garment-only rigid X-axis rotations -0.25, 0, +0.25 rad; diagnostic only, not articulated body poses",
        "candidate_policy":"Only rest-pose body-inside vertices block this fixture preflight. Synthetic garment-only rotations and BVH AABB overlap pairs are review candidates, not exact triangle-intersection proofs.",
        "collision_free_pose_certified":False,"cloth_simulation_certified":False,
        "artist_review_required":True,"engine_certified":False,
        "limitations":["Pose samples move the garment without a skeletal body rig and are diagnostic only",
        "Parity tests are approximate for open/non-manifold body meshes",
        "BVH overlap flags are conservative candidates and require visual confirmation",
        "No cloth simulation, continuous collision detection or runtime physics test"]}
    os.makedirs(os.path.dirname(out) or ".",exist_ok=True)
    with open(out,"w",encoding="utf-8") as f: json.dump(report,f,indent=2)
    print("FORGE_GARMENT_COLLISION_QA "+json.dumps(report))
    if hard_failures: raise SystemExit("Rest-pose garment/body penetration candidates detected")
if __name__=="__main__": main()
