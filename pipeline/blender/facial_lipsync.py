"""Create timestamp-driven lip-sync curves from phoneme/viseme cue JSON.

Usage: blender -b --python facial_lipsync.py -- input.glb timeline.json output.glb report.json
Timeline format: {"fps":30,"cues":[{"start":0.0,"duration":0.12,"viseme":"MBP"}]}
This maps externally supplied phoneme timing; it does not infer speech from raw audio.
"""
import bpy, json, os, sys

def args():
    a=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    if len(a)!=4: raise SystemExit("Usage: -- input.glb timeline.json output.glb report.json")
    return [os.path.abspath(x) for x in a]
def main():
    src,timeline_path,out,report_path=args()
    for p in (src,timeline_path):
        if not os.path.isfile(p): raise FileNotFoundError(p)
    with open(timeline_path,encoding="utf-8") as f: timeline=json.load(f)
    fps=int(timeline.get("fps",30)); cues=timeline.get("cues",[])
    if fps<1 or fps>120 or not cues: raise ValueError("Timeline requires fps 1..120 and non-empty cues")
    bpy.ops.object.select_all(action="SELECT"); bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=src)
    meshes=[o for o in bpy.context.scene.objects if o.type=="MESH" and o.data.shape_keys]
    if not meshes: raise RuntimeError("Input GLB has no facial shape-key mesh")
    available={}
    for obj in meshes:
        for key in obj.data.shape_keys.key_blocks:
            if key.name.startswith("ForgeViseme_"): available.setdefault(key.name.replace("ForgeViseme_",""),[]).append((obj,key))
    if not available: raise RuntimeError("No ForgeViseme targets found")
    normalized=[]; last_end=-1.0
    for cue in cues:
        viseme=str(cue.get("viseme","")).upper()
        start=float(cue.get("start",-1)); duration=float(cue.get("duration",0))
        if viseme not in available: raise ValueError("Unsupported or missing viseme: "+viseme)
        if start<0 or duration<=0 or start<last_end: raise ValueError("Cues must be positive-duration and ordered without overlap")
        normalized.append({"viseme":viseme,"start":start,"duration":duration})
        last_end=start+duration
    # Set every available viseme to neutral around each cue, then animate its
    # own envelope with a short 10 ms attack/release to avoid hard pops.
    frame_end=1
    for cue in normalized:
        start=round(cue["start"]*fps)+1
        end=max(start+2,round((cue["start"]+cue["duration"])*fps)+1)
        attack=max(start+1,round(start+fps*0.01))
        release=max(attack+1,end-1)
        for meshes_for_key in available.values():
            for obj,key in meshes_for_key:
                key.value=0.0; key.keyframe_insert(data_path="value",frame=start-1,group="Forge_LipSync")
                key.value=0.0; key.keyframe_insert(data_path="value",frame=start,group="Forge_LipSync")
        for obj,key in available[cue["viseme"]]:
            key.value=1.0; key.keyframe_insert(data_path="value",frame=attack,group="Forge_LipSync")
            key.value=0.0; key.keyframe_insert(data_path="value",frame=release,group="Forge_LipSync")
            key.value=0.0; key.keyframe_insert(data_path="value",frame=end,group="Forge_LipSync")
        frame_end=max(frame_end,end)
    scene=bpy.context.scene; scene.render.fps=fps; scene.frame_start=1; scene.frame_end=frame_end; scene.frame_set(1)
    for obj in bpy.context.scene.objects:
        if obj.type in {"MESH","ARMATURE","EMPTY"}: obj.select_set(True)
    if meshes: bpy.context.view_layer.objects.active=meshes[0]
    os.makedirs(os.path.dirname(out) or ".",exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=out,export_format="GLB",use_selection=True,
        export_animations=True,export_skins=True,export_morph=True,
        export_texcoords=True,export_normals=True,export_materials="EXPORT",
        export_cameras=False,export_lights=False)
    report={"status":"timestamped_lipsync_created","input":src,"timeline":timeline_path,
        "output":out,"fps":fps,"cue_count":len(normalized),"cues":normalized,
        "available_visemes":sorted(available),"frame_end":frame_end,
        "audio_analysis_performed":False,"artist_review_required":True,"engine_certified":False,
        "limitations":["Requires externally authored phoneme/viseme timestamps",
        "Does not perform speech recognition or raw-audio phoneme extraction",
        "Review coarticulation, jaw motion and audio alignment in target engine"]}
    os.makedirs(os.path.dirname(report_path) or ".",exist_ok=True)
    with open(report_path,"w",encoding="utf-8") as f: json.dump(report,f,indent=2)
    print("FORGE_LIPSYNC "+json.dumps(report))
if __name__=="__main__": main()
