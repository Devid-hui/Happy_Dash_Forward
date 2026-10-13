"""Compare real exported Body/24-bone channels with frozen pre-UV c3 GLB."""
from pathlib import Path
import struct
import json
import hashlib
import numpy as np

root = Path(__file__).resolve().parent
trial = root.parents[1] / 'work/nailong/uv-pbr-trial'
reference = root.parents[1] / 'work/nailong/rig-candidate/face-tail-trial-v3/nailong_lod0.glb'
candidate = trial / 'body_uv_4k_local_islands_only.glb'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(reference) == 'c340395c197a44c2c22652a24458343ad0246dd966e575b1b6e67c5d872f55b1'


def read_glb(path):
    raw = path.read_bytes()
    assert raw[:4] == b'glTF' and struct.unpack_from('<I', raw, 4)[0] == 2
    size, kind = struct.unpack_from('<II', raw, 12)
    assert kind == 0x4e4f534a
    doc = json.loads(raw[20:20+size])
    bin_size, bin_kind = struct.unpack_from('<II', raw, 20+size)
    assert bin_kind == 0x004e4942
    binary = memoryview(raw)[28+size:28+size+bin_size]
    return doc, binary


def accessor(doc, binary, index):
    a = doc['accessors'][index]
    if 'sparse' in a:
        raise ValueError('Sparse animation accessor requires an explicit decoder')
    view = doc['bufferViews'][a['bufferView']]
    dtype = np.dtype({5120:'i1',5121:'u1',5122:'<i2',5123:'<u2',5125:'<u4',5126:'<f4'}[a['componentType']])
    columns = {'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}[a['type']]
    offset = view.get('byteOffset',0)+a.get('byteOffset',0)
    stride = view.get('byteStride',columns*dtype.itemsize)
    return np.ndarray((a['count'],columns),dtype=dtype,buffer=binary,
                      offset=offset,strides=(stride,dtype.itemsize))


def channels(path):
    doc, binary = read_glb(path)
    joints = {doc['nodes'][j]['name'] for j in doc['skins'][0]['joints']}
    assert len(joints) == 24
    records = {}
    for animation in doc['animations']:
        clip = animation['name']
        for channel in animation['channels']:
            target = channel['target']; node = doc['nodes'][target['node']]
            name = node.get('name',''); kind = target['path']
            if name not in joints and name != 'NailongSkin_Reconstructed':
                continue
            sampler = animation['samplers'][channel['sampler']]
            key = (clip,name,kind)
            if key in records:
                raise ValueError('Ambiguous duplicate animation channel '+repr(key))
            records[key] = {'time':accessor(doc,binary,sampler['input']),
                            'value':accessor(doc,binary,sampler['output']),
                            'interpolation':sampler.get('interpolation','LINEAR')}
    return doc, joints, records


old, old_joints, old_channels = channels(reference)
new, new_joints, new_channels = channels(candidate)
assert old_joints == new_joints
assert old_channels.keys() == new_channels.keys()
records = []
for key in sorted(old_channels):
    a,b = old_channels[key],new_channels[key]
    assert a['time'].shape == b['time'].shape and a['value'].shape == b['value'].shape
    assert a['interpolation'] == b['interpolation']
    assert np.isfinite(b['time']).all() and np.isfinite(b['value']).all()
    dt = float(np.abs(a['time'].astype(np.float64)-b['time']).max(initial=0))
    dv = float(np.abs(a['value'].astype(np.float64)-b['value']).max(initial=0))
    records.append({'clip':key[0],'node':key[1],'property':key[2],
                    'time_count':len(a['time']),'value_count':len(a['value']),
                    'interpolation':a['interpolation'],
                    'maximum_absolute_time_difference':dt,
                    'maximum_absolute_value_difference':dv})
body = [r for r in records if r['node']=='NailongSkin_Reconstructed']
bones = [r for r in records if r['node'] in old_joints]
assert len(body) == 6 and len(bones) == 432
body_nodes = [n for n in new['nodes'] if n.get('name')=='NailongSkin_Reconstructed']
assert len(body_nodes)==1
mesh = new['meshes'][body_nodes[0]['mesh']]
assert mesh.get('extras',{}).get('targetNames') == ['Open','Focus']
report = {'reference':str(reference),'reference_sha256':sha(reference),
          'candidate':str(candidate),'candidate_sha256':sha(candidate),
          'clips':sorted({r['clip'] for r in records}),'bone_count':len(new_joints),
          'bone_channels_compared':len(bones),'body_weight_channels_compared':len(body),
          'body_target_names':mesh['extras']['targetNames'],
          'maximum_absolute_bone_value_difference':max(r['maximum_absolute_value_difference'] for r in bones),
          'maximum_absolute_body_weight_difference':max(r['maximum_absolute_value_difference'] for r in body),
          'maximum_absolute_sampler_time_difference':max(r['maximum_absolute_time_difference'] for r in records),
          'all_channels_finite':True,'channels':records,
          'scope':'Real GLB sampler arrays for Body Open/Focus and all24 native bones; '
                  'body-only UV experiment, not face topology or graphical Godot acceptance'}
(root/'LOCAL_ISLANDS_ANIMATION_EXPORT_COMPARISON.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='channels'},indent=2))
