"""CPU-only actual candidate inspection; no production imports or Godot."""
import bpy, json, math, sys, importlib.util, os
import numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parent
TRIAL=ROOT.parents[1]/'work/nailong/face-topology-v5'
spec=importlib.util.spec_from_file_location('face_candidate_v3',TRIAL/'face_v3_frozen.py')
helper=importlib.util.module_from_spec(spec);spec.loader.exec_module(helper)
manifest=json.loads((TRIAL/'V3_MODEL_MANIFEST.json').read_text())
out=ROOT/'dual-joint-direct-fan-visible-previews';out.mkdir(exist_ok=True)
scene=bpy.context.scene
rig=bpy.data.objects['NailongRig'];skin=bpy.data.objects['NailongSkin_Reconstructed']
actors=[obj for obj in scene.objects if obj.type=='MESH']
for obj in [rig,*actors]:
 for block in [obj, getattr(obj.data,'shape_keys',None)]:
  if block is not None and block.animation_data:
   block.animation_data.action=None
   for track in block.animation_data.nla_tracks:track.mute=True
for bone in rig.pose.bones:
 bone.location=(0,0,0);bone.rotation_quaternion=(1,0,0,0);bone.scale=(1,1,1)
for key in skin.data.shape_keys.key_blocks:key.value=0
for actor in actors:
 if actor.data.shape_keys:
  for key in actor.data.shape_keys.key_blocks:key.value=0
report={'blender':bpy.app.version_string,'candidate_file':bpy.data.filepath,'cpu_only':True,'samples':[], 'bone_count':len(rig.data.bones), 'source_body_counts':{'vertices':len(skin.data.vertices),'polygons':len(skin.data.polygons)}}
globes={obj.name:np.array([v.co[:] for v in obj.data.vertices]) for obj in actors if 'Sclera' in obj.name}
lids=[obj for obj in actors if 'Eyelid' in obj.name]
measure=manifest['face_helper']['measured_eyes']

def values(blink,focus,face_focus=None):
 if face_focus is None:face_focus=focus
 for lid in lids:
  for name,v in helper.lid_weights(blink,focus,face_focus).items():lid.data.shape_keys.key_blocks[name].value=v
 skin.data.shape_keys.key_blocks['Focus'].value=face_focus
 for actor in actors:
  if actor.name.startswith('ReconstructedOralLining'):
   actor.data.shape_keys.key_blocks['Focus'].value=face_focus
 bpy.context.view_layer.update()

def audit(blink,focus,face_focus=None):
 values(blink,focus,face_focus); record={'blink':blink,'focus':focus,'face_focus':face_focus if face_focus is not None else focus,'lids':{},'globes':{}}
 for globe,baseline in globes.items():
  actual=np.array([v.co[:] for v in bpy.data.objects[globe].data.vertices]);record['globes'][globe]={'local_geometry_max_delta_m':float(np.max(np.abs(actual-baseline))),'scale':list(bpy.data.objects[globe].scale)}
 for lid in lids:
  side='left' if 'left' in lid.name else 'right';c=np.array(measure[side]['center']);r=np.array(measure[side]['radii'])
  obj=lid.evaluated_get(bpy.context.evaluated_depsgraph_get());mesh=obj.to_mesh();pts=np.array([v.co[:] for v in mesh.vertices]);obj.to_mesh_clear()
  normalized=(pts-c)/r;radial=np.linalg.norm(normalized,axis=1)
  projected=normalized[:,0]**2+normalized[:,2]**2
  sel=(projected<=.90**2)&(normalized[:,1]>=0)
  # The actual cornea uses the same ellipsoid + a 6.8mm front offset.
  clearance=pts[sel,1]-c[1]-r[1]*np.sqrt(1-projected[sel])-.0068
  record['lids'][lid.name]={'finite':bool(np.isfinite(pts).all()),'minimum_ellipsoid_radius':float(radial.min()),'front_cornea_clearance_min_m':float(clearance.min()) if len(clearance) else None,'front_cornea_samples':int(sel.sum())}
 report['samples'].append(record)
 return record

scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=8;scene.cycles.use_denoising=True
scene.render.threads_mode='FIXED';scene.render.threads=2
scene.render.resolution_x=640;scene.render.resolution_y=640;scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('CPU candidate inspection world');scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.08,.10,.13,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.45
scene.view_settings.view_transform='AgX'
for name,pos,power,size in [('Key',(-3,4,5),1100,3),('Fill',(4,4,3),700,4),('Rim',(1,-4,4),900,3)]:
 data=bpy.data.lights.new(name,'AREA');data.energy=power;data.size=size
 obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj);obj.location=pos
 obj.rotation_euler=(Vector((0,.1,1.6))-obj.location).to_track_quat('-Z','Y').to_euler()
data=bpy.data.cameras.new('CPU reference candidate camera');data.type='ORTHO'
camera=bpy.data.objects.new('CPU reference candidate camera',data);scene.collection.objects.link(camera);scene.camera=camera
def render(name,deg,close=True):
 center=Vector((0,.40,2.08)) if close else Vector((0,-.1,1.38));data.ortho_scale=1.45 if close else 3.5
 theta=math.radians(deg);camera.location=center+Vector((math.sin(theta)*6,math.cos(theta)*6,.12 if close else .4))
 camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(out/name)
 bpy.ops.render.render(write_still=True)



import importlib.util,hashlib
spec=importlib.util.spec_from_file_location('adapter_v3_actual_clips',ROOT.parent/'nailong-face-candidate-v3/adapter-final.py')
binder=importlib.util.module_from_spec(spec);spec.loader.exec_module(binder)
evidence={'source':bpy.data.filepath,'source_sha256':hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),'source_Focus_alias_displacement':{},'clip_samples':[],'CPU_only':True,'not_expression_art_pass':True}
for obj in lids:
 basis=helper.oral_coordinates(obj.data.shape_keys.key_blocks['Basis']);focus=helper.oral_coordinates(obj.data.shape_keys.key_blocks['Focus']);length=np.linalg.norm(focus-basis,axis=1)
 evidence['source_Focus_alias_displacement'][obj.name]={'max_m':float(length.max()),'median_m':float(np.median(length)),'p95_m':float(np.percentile(length,95)),'changed_vertices_above_1mm':int((length>.001).sum())}
snap_spec=importlib.util.spec_from_file_location('visible_normal_snapshot',TRIAL/'render_visible_normal_snapshot.py')
snapshot=importlib.util.module_from_spec(snap_spec);snap_spec.loader.exec_module(snapshot)
source_render=render
def render(*args,**kwargs):
 pairs=snapshot.snapshots(actors)
 try:source_render(*args,**kwargs)
 finally:snapshot.restore(pairs)
values(.2,0);render('blink020-front.png',0)
values(0,1);render('focus100-front.png',0)
for clip,seconds in [('warn',.78),('charge',.25),('idle',1.792)]:
 binder.activate_clip(rig,skin,clip,seconds,actors)
 for deg,suffix in [(0,'front'),(65,'right-near')]:render(clip+'-'+suffix+'.png',deg)
 evidence['clip_samples'].append({'clip':clip,'seconds':seconds,'BodyFocus':float(skin.data.shape_keys.key_blocks['Focus'].value),'BodyOpen':float(skin.data.shape_keys.key_blocks['Open'].value)})
(ROOT/'dual-joint-direct-fan-visible-visual-evidence.json').write_text(json.dumps(evidence,indent=2)+'\n')
print('DUAL_JOINT_NATIVE_CLIP_CPU_PREVIEWS_COMPLETE')
