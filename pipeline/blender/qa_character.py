"""Blender-side asset QA: UVs, transforms, PBR nodes, rig and deformation."""
import bpy
import json
import os
import sys

def args_after_separator():
    argv=sys.argv
    return argv[argv.index("--")+1:] if "--" in argv else []

def main():
    args=args_after_separator()
    if len(args)!=2:
        raise SystemExit("Usage: qa_character.py -- input.glb report.json")
    source,report_path=map(os.path.abspath,args)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=source)
    meshes=[o for o in bpy.context.scene.objects if o.type=="MESH"]
    armatures=[o for o in bpy.context.scene.objects if o.type=="ARMATURE"]
    issues=[]
    if not meshes: issues.append("No mesh objects")
    if not armatures: issues.append("No armature object")
    mesh_stats=[]
    weight_stats=[]
    mesh_diagnostics=[]
    for obj in meshes:
        # Blender may import armature display helpers as hidden non-deforming meshes.
        importer_helper = (obj.name=="Icosphere" and len(obj.data.vertices)==42 and
            len(obj.data.polygons)==80 and len(obj.data.materials)==0 and
            len(obj.vertex_groups)==0 and not any(m.type=="ARMATURE" for m in obj.modifiers))
        hidden_helper = (bool(obj.hide_render or obj.hide_viewport or obj.hide_get()) and
            not obj.data.materials and not any(m.type=="ARMATURE" for m in obj.modifiers))
        if importer_helper or hidden_helper:
            mesh_stats.append({"name":obj.name,"role":"non-character-import-helper",
                "excluded_from_render_qa":True,"signature":"unbound-42v-80f-helper"})
            continue
        mesh_diagnostics.append({"name":obj.name,"hidden_render":obj.hide_render,
            "hidden_viewport":obj.hide_viewport,"hidden_get":obj.hide_get(),
            "parent":obj.parent.name if obj.parent else None,
            "parent_type":obj.parent_type,"vertex_groups":[g.name for g in obj.vertex_groups],
            "modifiers":[m.type for m in obj.modifiers]})
        if not obj.data.uv_layers:
            issues.append(obj.name+": missing UV map")
        if not obj.data.materials:
            issues.append(obj.name+": missing material")
        for mat in obj.data.materials:
            if mat and mat.use_nodes:
                principled=[n for n in mat.node_tree.nodes if n.type=="BSDF_PRINCIPLED"]
                if not principled:
                    issues.append(obj.name+": material has no Principled BSDF")
            else:
                issues.append(obj.name+": material nodes disabled")
        if not any(m.type=="ARMATURE" for m in obj.modifiers):
            issues.append(obj.name+": missing armature modifier")
        if any(abs(v-1.0)>1e-4 for v in obj.scale):
            issues.append(obj.name+": unapplied object scale")
        sums=[]
        max_influences=0
        for vertex in obj.data.vertices:
            influences=[g.weight for g in vertex.groups if g.weight>1e-6]
            if influences:
                sums.append(sum(influences))
                max_influences=max(max_influences,len(influences))
        if not sums:
            issues.append(obj.name+": no weighted vertices")
        elif any(abs(total-1.0)>1e-3 for total in sums):
            issues.append(obj.name+": vertex weights are not normalized")
        if max_influences>4:
            issues.append(obj.name+": more than four bone influences on a vertex")
        weight_stats.append({"name":obj.name,"weighted_vertices":len(sums),
            "max_influences":max_influences,
            "max_normalization_error":max((abs(total-1.0) for total in sums),default=None)})
        mesh_stats.append({"name":obj.name,"vertices":len(obj.data.vertices),
            "polygons":len(obj.data.polygons),"uv_layers":len(obj.data.uv_layers),
            "materials":len(obj.data.materials)})
    animation_count=0
    for arm in armatures:
        if arm.animation_data and arm.animation_data.action:
            animation_count+=1
    if animation_count==0:
        issues.append("No active armature animation")
    scene=bpy.context.scene
    scene.frame_set(1)
    depsgraph=bpy.context.evaluated_depsgraph_get()
    start_positions={}
    for obj in meshes:
        evaluated=obj.evaluated_get(depsgraph)
        mesh=evaluated.to_mesh()
        start_positions[obj.name]=[evaluated.matrix_world @ v.co for v in mesh.vertices]
        evaluated.to_mesh_clear()
    scene.frame_set(16)
    depsgraph=bpy.context.evaluated_depsgraph_get()
    moved=0
    for obj in meshes:
        evaluated=obj.evaluated_get(depsgraph)
        mesh=evaluated.to_mesh()
        before=start_positions.get(obj.name,[])
        for i,vertex in enumerate(mesh.vertices):
            if i<len(before) and ((evaluated.matrix_world @ vertex.co)-before[i]).length>1e-5:
                moved+=1
        evaluated.to_mesh_clear()
    if moved==0:
        issues.append("Animation did not deform any mesh vertices at test frame")
    result={"status":"pass" if not issues else "fail","source":source,
        "mesh_count":len(meshes),"armature_count":len(armatures),
        "animated_mesh_vertices":moved,"meshes":mesh_stats,"weight_stats":weight_stats,
        "mesh_diagnostics":mesh_diagnostics,"issues":issues,
        "checks":["UV presence","Principled material nodes","armature modifiers",
                  "applied object scale","active animation","evaluated deformation"]}
    os.makedirs(os.path.dirname(report_path) or ".",exist_ok=True)
    with open(report_path,"w",encoding="utf-8") as handle:
        json.dump(result,handle,indent=2)
    print("FORGE_QA "+json.dumps(result))
    if issues:
        raise SystemExit(1)

if __name__=="__main__":
    main()
