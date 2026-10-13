"""Read-only CPU previews of the saved NaiFrog rig; never export/import Godot."""
import bpy
import sys
import json
import importlib.util
from pathlib import Path
from mathutils import Vector

args=sys.argv[sys.argv.index('--')+1:]
out=Path(args[0]).resolve();out.mkdir(parents=True,exist_ok=True)
spec=importlib.util.spec_from_file_location('nfbuild','/Users/lpz/Documents/Happy_Dash_Forward/tools/build_naifrog_asset.py')
nf=importlib.util.module_from_spec(spec);spec.loader.exec_module(nf)
nf.PREVIEW=out
rig=bpy.data.objects['NaifrogRig']
objects=[o for o in bpy.data.objects if o.type=='MESH']
for track in rig.animation_data.nla_tracks:track.mute=track.name!='idle'
for obj in objects:
    if obj.data.shape_keys:
        for track in obj.data.shape_keys.animation_data.nla_tracks:track.mute=track.name!='idle'
bpy.context.scene.frame_set(1)
nf.render_views()
scene=bpy.context.scene;cam=scene.camera;cam.data.ortho_scale=.85
cam.location=(0,6,2.53);cam.rotation_euler=(Vector((0,.30,2.51))-cam.location).to_track_quat('-Z','Y').to_euler()
for track in rig.animation_data.nla_tracks:track.mute=True
for obj in objects:
    if obj.data.shape_keys:
        for track in obj.data.shape_keys.animation_data.nla_tracks:track.mute=True
for b in rig.pose.bones:b.location=(0,0,0);b.rotation_euler=(0,0,0);b.scale=(1,1,1)
for blink,focus,opening,label in [(0,0,0,'neutral'),(.5,0,0,'blink_half'),(1,0,0,'blink_closed'),(.5,.5,0,'joint_half'),(1,1,0,'joint_closed'),(0,.34,.85,'warn_open')]:
    for obj in objects:
        if not obj.data.shape_keys:continue
        for name,value in [('Blink',blink),('Focus',focus),('Open',opening)]:obj.data.shape_keys.key_blocks[name].value=value
    bpy.context.view_layer.update();scene.render.filepath=str(out/('face_'+label+'.png'));bpy.ops.render.render(write_still=True)
print('NAIFROG_RIG_CPU_PREVIEW_COMPLETE',str(out))
