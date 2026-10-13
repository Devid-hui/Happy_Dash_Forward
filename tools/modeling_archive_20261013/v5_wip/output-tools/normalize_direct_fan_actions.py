from pathlib import Path
import bpy,json,hashlib,numpy as np
root=Path(__file__).resolve().parent;work=root.parents[1]/'work/nailong/face-topology-v5'
before=bpy.data.filepath;changed=[]
for obj in bpy.context.scene.objects:
 if not obj.name.startswith('SharedEyelidFace_'):continue
 for track in obj.data.shape_keys.animation_data.nla_tracks:
  for curve in track.strips[0].action.fcurves:
   for point in curve.keyframe_points:
    if point.interpolation!='LINEAR':changed.append([obj.name,track.name,curve.data_path,float(point.co.x),point.interpolation])
    point.interpolation='LINEAR'
target=work/'source-dual-eye-joint-direct-fan-linear.blend'
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(target),compress=True)
record={'before':before,'before_sha256':hashlib.sha256(Path(before).read_bytes()).hexdigest(),'changed_interpolations':changed,'source':str(target),'source_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'scope':'Only local Face animation interpolation tags standardized to LINEAR; coordinates, original Body/rig/actions and normal-fan geometry unchanged.'}
(root/'direct-fan-linear-source.json').write_text(json.dumps(record,indent=2)+'\n')
print('DIRECT_FAN_LINEAR_SOURCE',record['source_sha256'],len(changed),flush=True)
