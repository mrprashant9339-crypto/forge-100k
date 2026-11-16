"""Measure retopology density, edge flow and deformation-sensitive topology.

Usage: blender -b --python retopo_quality_qa.py -- retopo.glb report.json
This is a geometric preflight, not artist approval of edge-loop placement.
"""
import bpy, bmesh, json, math, os, sys, statistics
def args():
    a=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    if len(a)!=2: raise SystemExit("Usage: -- retopo.glb report.json")
    return [os.path.abspath(x) for x in a]
def main():
    src,out=args()
    if not os.path.isfile(src): raise FileNotFoundError(src)
    bpy.ops.object.select_all(action="SELECT"); bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=src)
    meshes=[o for o in bpy.context.scene.objects if o.type=="MESH"]
    if not meshes: raise RuntimeError("Retopo GLB contains no meshes")
    records=[]; failures=[]
    for obj in meshes:
        bm=bmesh.new(); bm.from_mesh(obj.data); bm.verts.ensure_lookup_table(); bm.edges.ensure_lookup_table(); bm.faces.ensure_lookup_table()
        edge_lengths=[e.calc_length() for e in bm.edges]
        valence=[len(v.link_edges) for v in bm.verts]
        boundary=sum(1 for e in bm.edges if e.is_boundary)
        nonmanifold=sum(1 for e in bm.edges if not e.is_manifold)
        tri=sum(1 for f in bm.faces if len(f.verts)==3)
        quad=sum(1 for f in bm.faces if len(f.verts)==4)
        ngon=sum(1 for f in bm.faces if len(f.verts)>4)
        poles=sum(1 for v in bm.verts if len(v.link_edges) not in (4,)) 
        lengths_sorted=sorted(edge_lengths)
        mean=statistics.fmean(edge_lengths) if edge_lengths else 0.0
        cv=(statistics.pstdev(edge_lengths)/mean) if mean>1e-12 and len(edge_lengths)>1 else 0.0
        uv=bool(obj.data.uv_layers)
        issues=[]
        if not uv: issues.append("missing_uv_layer")
        if not bm.faces: issues.append("no_faces")
        if nonmanifold: issues.append("non_manifold_edges")
        if boundary: issues.append("open_boundary_edges")
        if cv>1.5: issues.append("high_edge_length_variance")
        if ngon: issues.append("ngon_faces_require_review")
        record={"mesh":obj.name,"vertices":len(bm.verts),"edges":len(bm.edges),"faces":len(bm.faces),
            "triangles":tri,"quads":quad,"ngons":ngon,"quad_ratio":quad/max(1,len(bm.faces)),
            "boundary_edges":boundary,"non_manifold_edges":nonmanifold,
            "vertex_valence_histogram":{str(n):valence.count(n) for n in sorted(set(valence))},
            "non_four_valence_vertices":poles,"edge_length":{"min":min(edge_lengths) if edge_lengths else 0,
            "median":statistics.median(edge_lengths) if edge_lengths else 0,"max":max(edge_lengths) if edge_lengths else 0,
            "coefficient_of_variation":cv},"uv_layer_count":len(obj.data.uv_layers),
            "deformation_regions_to_review":["shoulders","elbows","wrists","hips","knees","ankles","neck","face"],
            "issues":issues,"status":"review_required" if issues or poles else "topology_preflight_passed"}
        records.append(record)
        if nonmanifold or boundary or not uv or not bm.faces: failures.append(obj.name)
        bm.free()
    report={"status":"failed" if failures else "topology_preflight_passed","source":src,
        "mesh_count":len(records),"meshes":records,"hard_failures":failures,
        "artist_edge_flow_approval":False,"engine_certified":False,
        "limitations":["Valence and edge-length metrics cannot infer anatomically correct edge-loop flow",
        "Joint deformation requires sculpted pose tests and human topology review",
        "UV texel density and seam quality require dedicated inspection"]}
    os.makedirs(os.path.dirname(out) or ".",exist_ok=True)
    with open(out,"w",encoding="utf-8") as f: json.dump(report,f,indent=2)
    print("FORGE_RETOPO_QUALITY "+json.dumps(report))
    if failures: raise SystemExit("Retopology topology preflight failed")
if __name__=="__main__": main()
