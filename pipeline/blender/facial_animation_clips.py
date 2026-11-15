"""Author timed facial morph clips on an existing GLB.
Usage: blender -b --python facial_animation_clips.py -- input.glb output.glb report.json
"""
import bpy,json,os,sys

CLIPS={
 "ForgeExpr_smile":[(1,0.0),(8,0.8),(18,0.8),(26,0.0)],
 "ForgeExpr_brow_raise":[(1,0.0),(7,0.7),(15,0.7),(22,0.0)],
 "ForgeExpr_jaw_open":[(1,0.0),(6,0.65),(14,0.65),(20,0.0)],
 "ForgeExpr_blink":[(1,0.0),(4,1.0),(7,0.0),(24,0.0),(27,1.0),(30,0.0)],
 "ForgeViseme_A":[(1,0.0),(3,1.0),(7,0.0)],
 "ForgeViseme_E":[(1,0.0),(9,1.0),(13,0.0)],
 "ForgeViseme_I":[(1,0.0),(15,1.0),(19,0.0)],
 "ForgeViseme_O":[(1,0.0),(21,1.0),(25,0.0)],
 "ForgeViseme_U":[(1,0.0),(27,1.0),(31,0.0)]
}
def args():
 a=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
 if len(a)!=3: raise SystemExit("Usage: -- input.glb output.glb report.json")
 return [os.path.abspath(x) for x in a]
def main():
 src,out,report_path=args(); bpy.ops.object.select_all(action="SELECT");bpy.ops.object.delete(use_global=False)
 bpy.ops.import_scene.gltf(filepath=src)
 meshes=[o for o in bpy.context.scene.objects if o.type=="MESH" and o.data.shape_keys]
 if not meshes: raise RuntimeError("Input has no shape-key meshes")
 found={}
 for obj in meshes:
  keys=obj.data.shape_keys
  for clip,frames in CLIPS.items():
   block=keys.key_blocks.get(clip)
   if block:
    found.setdefault(clip,[]).append(obj.name)
    for f,v in frames:
     block.value=v;block.keyframe_insert(data_path="value",frame=f,group=clip)
 if not found: raise RuntimeError("No supported Forge expression/viseme shape keys found")
 actions=[]
 for obj in meshes:
  keys=obj.data.shape_keys
  if keys.animation_data and keys.animation_data.action:
   action=keys.animation_data.action
   action.name="Forge_Facial_Timed_Clips_"+obj.name
   for fc in action.fcurves:
    for kp in fc.keyframe_points: kp.interpolation="BEZIER"
   actions.append(action.name)
 scene=bpy.context.scene;scene.frame_start=1;scene.frame_end=31;scene.render.fps=30;scene.frame_set(1)
 bpy.ops.object.select_all(action="DESELECT")
 for obj in bpy.context.scene.objects:
  if obj.type in {"MESH","ARMATURE","EMPTY"}: obj.select_set(True)
 bpy.context.view_layer.objects.active=meshes[0]
 os.makedirs(os.path.dirname(out) or ".",exist_ok=True)
 bpy.ops.export_scene.gltf(filepath=out,export_format="GLB",use_selection=True,export_animations=True,export_skins=True,export_morph=True,export_texcoords=True,export_normals=True,export_materials="EXPORT",export_cameras=False,export_lights=False)
 data={"status":"timed_clips_authored","fps":30,"frame_range":[1,31],"duration_seconds":31/30,"clips":{k:{"keyframes":v,"meshes":found.get(k,[])} for k,v in CLIPS.items() if k in found},"actions":actions,"limitations":["Starter procedural curves only; phoneme timing must be synchronized to audio","No ARKit 52 mapping, gaze rig, performance capture or artist facial review; blink is a starter head-surface morph","Review interpolation and neutral pose in each target engine"],"artist_review_required":True,"engine_certified":False}
 with open(report_path,"w",encoding="utf-8") as f:json.dump(data,f,indent=2)
 print("FORGE_FACIAL_CLIPS "+json.dumps(data))
if __name__=="__main__":main()
