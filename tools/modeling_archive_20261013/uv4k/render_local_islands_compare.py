"""Same candidate geometry, camera, light and seed: VC versus real UV image."""
import bpy,math,json,hashlib,numpy as np
from pathlib import Path
from mathutils import Vector
root=Path(__file__).resolve().parent;source=root.parents[1]/'work/nailong/rig-candidate/face-tail-trial-v3/source/nailong_reconstructed_rig.blend'
skin=bpy.data.objects['NailongSkin_Reconstructed'];bag=bpy.data.objects['ReconstructedOralLining'];rig=bpy.data.objects['NailongRig'];texture_mat=skin.data.materials[0]
with bpy.data.libraries.load(str(source),link=False) as (data_from,data_to):data_to.materials=['Nailong_GS_linear_color']
vertex_mat=data_to.materials[0]
for obj in bpy.data.objects:
    for block in [obj,getattr(obj.data,'shape_keys',None)]:
        if block and block.animation_data:
            block.animation_data.action=None
            for t in block.animation_data.nla_tracks:t.mute=True
    if obj.type=='ARMATURE':
        for b in obj.pose.bones:b.location=(0,0,0);b.rotation_quaternion=(1,0,0,0);b.scale=(1,1,1)
    if obj.type=='MESH' and obj.data.shape_keys:
        for k in obj.data.shape_keys.key_blocks:k.value=0
scene=bpy.context.scene
for obj in list(scene.objects):
    if obj.type in ['LIGHT','CAMERA']:bpy.data.objects.remove(obj,do_unlink=True)
scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=16;scene.cycles.use_denoising=True;scene.cycles.seed=0
scene.render.threads_mode='FIXED';scene.render.threads=2
scene.render.resolution_x=640;scene.render.resolution_y=640;scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('UV colour compare world');scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.08,.10,.13,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.45
scene.view_settings.view_transform='AgX'
for name,pos,power,size in [('Key',(-3,4,5),1100,3),('Fill',(4,4,3),700,4),('Rim',(1,-4,4),900,3)]:
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.size=size
    obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj);obj.location=pos
    obj.rotation_euler=(Vector((0,.1,1.6))-obj.location).to_track_quat('-Z','Y').to_euler()
data=bpy.data.cameras.new('Same source UV compare');data.type='ORTHO'
camera=bpy.data.objects.new('Same source UV compare',data);scene.collection.objects.link(camera);scene.camera=camera
views=[('body-front',0,False,0),('body-oblique',35,False,0),('body-back',180,False,0),('face-front',0,True,0),('face-65deg',65,True,0),('mouth-open',35,True,.82)]
records=[]
for mode,material in [('before-vcol',vertex_mat),('after-texture',texture_mat)]:
    skin.data.materials[0]=material;folder=root/'compare-local-islands'/mode;folder.mkdir(parents=True,exist_ok=True)
    for name,angle,close,opening in views:
        skin.data.shape_keys.key_blocks['Open'].value=opening;bag.data.shape_keys.key_blocks['Open'].value=opening
        center=Vector((0,.40,2.08)) if close else Vector((0,-.1,1.38));data.ortho_scale=1.45 if close else 3.5
        theta=math.radians(angle);camera.location=center+Vector((math.sin(theta)*6,math.cos(theta)*6,.12 if close else .4));camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
        path=folder/(name+'.png');scene.render.filepath=str(path);bpy.context.view_layer.update();bpy.ops.render.render(write_still=True)
        records.append({'mode':mode,'view':name,'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
(root/'LOCAL_ISLANDS_SAME_SOURCE_CPU_COMPARE.json').write_text(json.dumps({'candidate':bpy.data.filepath,'same_geometry_lights_camera_seed_and_pose':True,'difference':'Only primary body Base Color source; other BRDF parameters unchanged','cpu_samples':16,'images':records},indent=2)+'\n');print('UV_BODY_CPU_COMPARE_DONE')
