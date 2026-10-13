from pathlib import Path
import bpy,json,hashlib,importlib.util,re,numpy as np
root=Path(__file__).resolve().parent;work=root.parents[1]/'work/nailong/face-topology-v5'
spec=importlib.util.spec_from_file_location('frozen_joint_weights',work/'face_v3_frozen.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)
body=bpy.data.objects['NailongSkin_Reconstructed'];source={t.name:t.strips[0] for t in body.data.shape_keys.animation_data.nla_tracks}
def keyname(curve):return re.search(r'key_blocks\["([^"]+)"\]',curve.data_path).group(1)
def b_value(name):return 1 if name=='Blink' else 0 if name in ['Focus','Open'] else int(name[4:7])/100
record={'before':bpy.data.filepath,'before_sha256':hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),'faces':{}}
for obj in bpy.context.scene.objects:
 if not obj.name.startswith('SharedEyelidFace_'):continue
 changes={}
 for track in obj.data.shape_keys.animation_data.nla_tracks:
  strip=track.strips[0];curves={keyname(f):f for f in strip.action.fcurves};reference=source[track.name]
  focus_curve=next(f for f in reference.action.fcurves if keyname(f)=='Focus')
  times=[float(p.co.x) for p in curves['Blink'].keyframe_points]
  before_times={name:[float(p.co.x) for p in f.keyframe_points] for name,f in curves.items()}
  maximum=0
  for index,frame in enumerate(times):
   blink=sum(b_value(name)*float(curve.keyframe_points[index].co.y) for name,curve in curves.items() if name!='Open')
   global_frame=strip.frame_start+(frame-strip.action_frame_start)*strip.scale
   reference_frame=reference.action_frame_start+(global_frame-reference.frame_start)/reference.scale
   focus=float(focus_curve.evaluate(reference_frame))
   weights=h.lid_weights(blink,focus,focus)
   for name,value in weights.items():
    point=curves[name].keyframe_points[index];maximum=max(maximum,abs(float(point.co.y)-value));point.co.y=value;point.interpolation='LINEAR'
  for name,curve in curves.items():
   assert before_times[name]==[float(p.co.x) for p in curve.keyframe_points],(obj.name,track.name,name)
  changes[track.name]={'same_key_count_and_floating_times':True,'maximum_weight_change':maximum,'Body_focus_reference_used':True}
 record['faces'][obj.name]=changes
target=work/'source-dual-eye-joint-direct-fan-body-synced.blend'
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(target),compress=True)
record['source']=str(target);record['sha256']=hashlib.sha256(target.read_bytes()).hexdigest();record['scope']='Only joint weight values aligned to original Body Focus curve at existing float key times; no geometry, original Body/rig action, or extra samples changed.'
(root/'body-focus-synced-source.json').write_text(json.dumps(record,indent=2)+'\n');print('BODY_FOCUS_SYNCED_SOURCE',record['sha256'],flush=True)
