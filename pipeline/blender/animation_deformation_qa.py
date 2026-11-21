"""Sample every exported skeletal animation action and validate evaluated deformation.

This is geometry/animation QA, not self-intersection or target-engine certification.
"""
import bpy, json, math, os, sys
from mathutils import Vector

def main():
    args=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    if len(args)!=2: raise SystemExit("Usage: -- input.glb report.json")
    src,out=map(os.path.abspath,args)
    bpy.ops.object.select_all(action="SELECT"); bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=src)
    scene=bpy.context.scene
    rigs=[o for o in scene.objects if o.type=="ARMATURE"]
    meshes=[o for o in scene.objects if o.type=="MESH" and (o.vertex_groups or any(m.type=="ARMATURE" for m in o.modifiers))]
    issues=[]
    if len(rigs)!=1: issues.append("Expected exactly one armature")
    if not meshes: issues.append("No skinned meshes imported")
    if rigs:
        rig=rigs[0]
        if not rig.animation_data: rig.animation_data_create()
        animation_data=rig.animation_data
        tracks=list(animation_data.nla_tracks)
        for track in tracks: track.mute=True
        actions=[]
        seen=set()
        if animation_data.action:
            actions.append(animation_data.action); seen.add(animation_data.action.name)
        for track in tracks:
            for strip in track.strips:
                if strip.action and strip.action.name not in seen:
                    actions.append(strip.action); seen.add(strip.action.name)
        for action in bpy.data.actions:
            if action.name not in seen and any(fc.data_path.startswith('pose.bones["') for fc in action.fcurves):
                actions.append(action); seen.add(action.name)
        if not actions: issues.append("No skeletal animation actions found")
    else: actions=[]
    reports=[]
    for action in actions:
        animation_data.action=action
        frames={int(round(action.frame_range[0])),int(round(action.frame_range[1]))}
        for fc in action.fcurves:
            for key in fc.keyframe_points:
                frames.add(int(round(key.co.x)))
        frames=sorted(frames)
        if len(frames)>9:
            stride=max(1,(len(frames)-1)//8)
            frames=sorted(set(frames[::stride]+[frames[-1]]))
        baseline={}; moved=False; valid_frames=0; mesh_reports=[]
        for frame in frames:
            scene.frame_set(frame)
            depsgraph=bpy.context.evaluated_depsgraph_get()
            frame_meshes=[]
            for obj in meshes:
                evaluated=obj.evaluated_get(depsgraph)
                mesh=evaluated.to_mesh()
                coords=[evaluated.matrix_world @ vertex.co for vertex in mesh.vertices]
                finite=all(all(math.isfinite(float(v)) for v in p) for p in coords)
                if not finite: issues.append(f"{action.name}/{obj.name}@{frame}: non-finite vertex")
                if not coords: issues.append(f"{action.name}/{obj.name}@{frame}: empty mesh")
                if coords:
                    extent=[max(p[i] for p in coords)-min(p[i] for p in coords) for i in range(3)]
                    if max(extent)<=1e-7: issues.append(f"{action.name}/{obj.name}@{frame}: collapsed geometry")
                if obj.name not in baseline: baseline[obj.name]=coords
                elif len(coords)==len(baseline[obj.name]) and any((a-b).length>1e-5 for a,b in zip(coords,baseline[obj.name])):
                    moved=True
                mesh.calc_loop_triangles()
                frame_meshes.append({"mesh":obj.name,"vertices":len(coords),"triangles":len(mesh.loop_triangles),"finite":finite})
                evaluated.to_mesh_clear()
            valid_frames+=1
            mesh_reports.append({"frame":frame,"meshes":frame_meshes})
        if not moved: issues.append(f"{action.name}: no skinned mesh movement across sampled frames")
        reports.append({"action":action.name,"frame_range":[int(action.frame_range[0]),int(action.frame_range[1])],"sampled_frames":frames,"movement_detected":moved,"frames":mesh_reports})
    for track in tracks if rigs else []: track.mute=False
    report={"schema":"forge.animation-deformation-qa.v1","status":"pass" if not issues else "fail","source":src,"action_count":len(reports),"actions":reports,"issues":issues,"checks":["evaluated skinned mesh coordinates finite","no collapsed sampled mesh","per-action deformation movement"],"not_checked":["mesh self-intersection/clothing penetration","foot sliding/contact","joint-limit correctness","target-engine playback"],"artist_review_required":True,"engine_certified":False}
    os.makedirs(os.path.dirname(out) or ".",exist_ok=True)
    with open(out,"w",encoding="utf-8") as f: json.dump(report,f,indent=2)
    print("FORGE_ANIMATION_DEFORMATION_QA "+json.dumps({"status":report["status"],"action_count":len(reports),"actions":[r["action"] for r in reports],"issues":issues}))
    if issues: raise SystemExit(1)
if __name__=="__main__": main()
