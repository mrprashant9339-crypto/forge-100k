"""Bake high-detail source meshes onto UV-mapped low-poly targets.
Usage: blender -b --python bake_pbr_textures.py -- high.glb low.glb output_dir [resolution]
Requires matching mesh object names and valid UVs on low-poly meshes.
"""
import bpy, json, os, sys

def cli():
    a=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    if len(a) not in (3,4): raise SystemExit("Usage: -- high.glb low.glb output_dir [resolution]")
    return [os.path.abspath(x) for x in a[:3]] + [int(a[3]) if len(a)==4 else 1024]

def clear():
    bpy.ops.object.select_all(action="SELECT); bpy.ops.object.delete(use_global=False)

def save_image(name, size, path, colorspace="Non-Color"):
    img=bpy.data.images.new(name,width=size,height=size,alpha=True,float_buffer=False)
    img.generated_color=(0.0,0.0,0.0,0.0)
    img.colorspace_settings.name=colorspace
    img.file_format="PNG"; img.filepath_raw=path
    return img

def bake_pass(low, high_objects, image, bake_type, directory, margin):
    for obj in bpy.context.scene.objects:
        obj.select_set(False)
    for obj in high_objects: obj.select_set(True)
    low.select_set(True)
    bpy.context.view_layer.objects.active=low
    mat=low.active_material
    if mat is None:
        mat=bpy.data.materials.new(low.name+"_BakeMaterial"); low.data.materials.append(mat)
    mat.use_nodes=True
    nodes=mat.node_tree.nodes
    target=nodes.new("ShaderNodeTexImage"); target.name="FORGE_BAKE_TARGET"; target.image=image
    for node in nodes: node.select=False
    target.select=True; nodes.active=target
    bpy.context.scene.render.bake.margin=margin
    bpy.context.scene.render.bake.use_selected_to_active=True
    bpy.context.scene.render.bake.use_clear=True
    bpy.context.scene.render.bake.normal_space="TANGENT"
    bpy.ops.object.bake(type=bake_type)
    image.filepath_raw=os.path.join(directory,bake_type.lower()+".png")
    image.file_format="PNG"; image.save()
    nodes.remove(target)
    return image.filepath_raw

def main():
    high_path,low_path,out,size=cli()
    if size<64 or size>4096 or size&(size-1): raise ValueError("resolution must be power of two 64..4096")
    os.makedirs(out,exist_ok=True); clear()
    bpy.ops.import_scene.gltf(filepath=high_path)
    high={o.name:o for o in bpy.context.scene.objects if o.type=="MESH"}
    bpy.ops.import_scene.gltf(filepath=low_path)
    low={o.name:o for o in bpy.context.scene.objects if o.type=="MESH" and o.name in high}
    if not low: raise RuntimeError("No matching high/low mesh object names")
    report={"status":"baked","resolution":[size,size],"meshes":[],"maps":{},"limitations":[]}
    scene=bpy.context.scene; scene.render.engine="CYCLES"; scene.cycles.samples=16
    scene.render.bake.use_pass_color=True
    scene.render.bake.use_pass_direct=False; scene.render.bake.use_pass_indirect=False
    for name,target in sorted(low.items()):
        if not target.data.uv_layers: raise RuntimeError("Low mesh has no UV map: "+name)
        src=high[name]
        if len(src.data.polygons)==0 or len(target.data.polygons)==0: raise RuntimeError("Empty mesh: "+name)
        high_obj=[src]
        entry={"mesh":name,"low_vertices":len(target.data.vertices),"high_vertices":len(src.data.vertices),"uv_layer":target.data.uv_layers.active.name}
        for bake_type in ("DIFFUSE","NORMAL","AO"):
            img=save_image("Forge_"+name+"_"+bake_type,size,os.path.join(out,bake_type.lower()+".png"),"sRGB" if bake_type=="DIFFUSE" else "Non-Color")
            if bake_type=="DIFFUSE":
                scene.render.bake.use_pass_color=True
            path=bake_pass(target,high_obj,img,bake_type,out,16)
            entry[bake_type.lower()]=path
            report["maps"].setdefault(bake_type.lower(),[]).append(path)
        report["meshes"].append(entry)
    report["channel_packing"]={"metallic_roughness":"Not synthesized from high-poly geometry; retain authored material factors or supply a dedicated packed source map","normal":"Tangent-space","ao":"Ambient occlusion"}
    report["limitations"]=["High/low correspondence is name-based; inspect cage distances and skewing","Diffuse bake uses Blender diffuse color pass; metallic/roughness are not inferred from sculpt geometry","Artist must inspect UV seams, cage intersections, tangent basis, mipmaps and engine appearance","This worker does not perform automatic retopology"]
    report["artist_review_required"]=True; report["engine_certified"]=False
    with open(os.path.join(out,"bake-report.json"),"w",encoding="utf-8") as f: json.dump(report,f,indent=2)
    print("FORGE_BAKE "+json.dumps(report))
if __name__=="__main__": main()
