"""Generate deterministic procedural PBR starter maps with Blender.
Usage: blender -b --python generate_pbr_textures.py -- output_dir [resolution]
This authors texture maps; it is not a UV bake from a production mesh.
"""
import bpy, json, math, os, sys
from mathutils import noise

def args():
    values=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    if len(values) not in (1,2): raise SystemExit("Usage: -- output_dir [resolution]")
    return os.path.abspath(values[0]), int(values[1]) if len(values)==2 else 512

def image(name, size, pixels, color_space, output):
    img=bpy.data.images.new(name,width=size,height=size,alpha=False,float_buffer=False)
    img.pixels.foreach_set(pixels)
    img.colorspace_settings.name=color_space
    img.file_format="PNG"
    img.filepath_raw=output
    img.save()
    bpy.data.images.remove(img)
    return output

def main():
    out,size=args()
    if size<64 or size>2048 or size & (size-1): raise ValueError("resolution must be a power of two from 64 to 2048")
    os.makedirs(out,exist_ok=True)
    base=[]; mr=[]; normal=[]; ao=[]
    for y in range(size):
        v=y/(size-1)
        for x in range(size):
            u=x/(size-1)
            n=noise.fractal((u*18.0,v*18.0,0.37),1.0,2.0,3)
            grain=noise.noise_vector((u*95.0,v*95.0,0.13)).x
            tone=max(0.0,min(1.0,0.62+0.055*n+0.012*grain))
            base.extend((0.62*tone,0.34*tone,0.19*tone,1.0))
            rough=max(0.0,min(1.0,0.82+0.035*n))
            metal=0.0
            mr.extend((0.0,rough,metal,1.0))
            # Tangent-space normal map with subtle, bounded procedural perturbation.
            nx=max(-0.12,min(0.12,grain*0.08)); ny=max(-0.12,min(0.12,n*0.04))
            nz=math.sqrt(max(0.0,1.0-nx*nx-ny*ny))
            normal.extend((0.5+nx*0.5,0.5+ny*0.5,0.5+nz*0.5,1.0))
            oc=max(0.0,min(1.0,0.96+0.025*n))
            ao.extend((oc,oc,oc,1.0))
    files={
      "base_color":image("Forge_BaseColor",size,base,"sRGB",os.path.join(out,"basecolor.png")),
      "metallic_roughness":image("Forge_MetallicRoughness",size,mr,"Non-Color",os.path.join(out,"metallic_roughness.png")),
      "normal":image("Forge_Normal",size,normal,"Non-Color",os.path.join(out,"normal.png")),
      "occlusion":image("Forge_Occlusion",size,ao,"Non-Color",os.path.join(out,"occlusion.png"))
    }
    report={"status":"generated","resolution":[size,size],"format":"PNG","maps":files,
      "channel_packing":{"metallic_roughness":{"R":"unused","G":"roughness","B":"metallic","A":"opaque"},"normal":{"R":"tangent normal X","G":"tangent normal Y","B":"tangent normal Z"},"occlusion":{"RGB":"grayscale ambient occlusion"}},
      "method":"deterministic procedural image authoring; not mesh UV baking",
      "artist_review_required":True,"game_ready":False}
    with open(os.path.join(out,"pbr-texture-report.json"),"w",encoding="utf-8") as f: json.dump(report,f,indent=2)
    print("FORGE_PBR_TEXTURES "+json.dumps(report))
if __name__=="__main__": main()
