"""Read-only exact raw geometry identity comparison; no Godot and no 27-grid rerun."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
import bpy
sys.path.insert(0,str(Path(__file__).parents[1]/'independent-face-check'))
import check_frozen_face as existing


def array_hash(value):
    value=np.ascontiguousarray(value)
    return hashlib.sha256(str((value.dtype.str,value.shape)).encode()+value.tobytes()).hexdigest()


def comparison(a,b):
    same_shape=a.shape==b.shape
    equal=bool(same_shape and np.array_equal(a,b))
    return {'equal_exact':equal,'old_shape':list(a.shape),'new_shape':list(b.shape),
            'old_hash':array_hash(a),'new_hash':array_hash(b),
            'maximum_numeric_difference':float(np.max(np.abs(a-b))) if same_shape and a.size else 0.0 if same_shape else None}


def source(path):
    bpy.ops.wm.open_mainfile(filepath=str(path),load_ui=False,use_scripts=False)
    dataset=existing.read_source()
    uvs={}
    for name in dataset:
        mesh=bpy.data.objects[name].data
        for layer in mesh.uv_layers:
            uv=np.empty((len(layer.data),2),np.float32)
            layer.data.foreach_get('uv',uv.ravel())
            uvs[name+'/'+layer.name]=uv
    return dataset,uvs


def oriented_faces(faces):
    # Cyclic rotation preserves winding; opposite winding is never accepted.
    return Counter(min((int(a),int(b),int(c)),(int(b),int(c),int(a)),(int(c),int(a),int(b))) for a,b,c in faces)


def main():
    p=argparse.ArgumentParser()
    for name in ('old_source','source','old_glb','glb','old_manifest','manifest','out'):
        p.add_argument('--'+name.replace('_','-'),type=Path,required=True)
    a=p.parse_args(sys.argv[sys.argv.index('--')+1:])
    paths={key:getattr(a,key) for key in ('old_source','source','old_glb','glb','old_manifest','manifest')}
    initial={key:existing.sha(path) for key,path in paths.items()}
    old,old_uv=source(a.old_source)
    new,new_uv=source(a.source)
    report={'scope':'Exact raw SOURCE geometry/morph/ROI and actual GLB canonical geometry identity against V8. UV and animation remain separate. Not a new 27-combination execution.',
            'blender':bpy.app.version_string,'paths':{key:str(value) for key,value in paths.items()},'initial_sha256':initial,
            'source_mesh_names_equal':set(old)==set(new),'source':{},'source_uv':{},'GLB':{}}
    for name in sorted(set(old)|set(new)):
        if name not in old or name not in new:
            report['source'][name]={'pass':False,'reason':'mesh missing'};continue
        x,y=old[name],new[name]
        checks={'basis':comparison(x['basis'],y['basis']),'triangles':comparison(x['faces'],y['faces'])}
        checks.update({'morph_'+key:comparison(x['morphs'][key],y['morphs'][key]) for key in set(x['morphs'])&set(y['morphs'])})
        checks.update({key:comparison(x['attrs'][key],y['attrs'][key]) for key in set(x['attrs'])&set(y['attrs'])})
        names_equal=set(x['morphs'])==set(y['morphs']) and set(x['attrs'])==set(y['attrs'])
        report['source'][name]={'pass':names_equal and all(check['equal_exact'] for check in checks.values()),'morph_and_ROI_attribute_names_equal':names_equal,'checks':checks}
        if name.startswith('NaifrogContinuousSkin'):
            patch=y['attrs']['NaiFrogFacialPatch']
            explicit=np.flatnonzero(patch>0)
            vertices=set(y['faces'][explicit].ravel().tolist())
            ids=np.array([i for i,face in enumerate(y['faces']) if patch[i]>0 or any(int(v) in vertices for v in face)],int)
            report['source'][name]['scope']={'explicit_ROI':len(explicit),'canonical_one_ring':len(ids)-len(explicit),'total_triangles':len(ids),'scoped_triangle_identity_hash':array_hash(y['faces'][ids])}
    for name in sorted(set(old_uv)|set(new_uv)):
        report['source_uv'][name]=comparison(old_uv[name],new_uv[name]) if name in old_uv and name in new_uv else {'equal_exact':False,'reason':'UV layer topology changed'}
    old_manifest=json.loads(a.old_manifest.read_text())
    new_manifest=json.loads(a.manifest.read_text())
    frame_keys=('side','frame_center','frame_u','frame_vertical','eye_normal','neutral_lid_rim_depth')
    old_frames=[{key:frame[key] for key in frame_keys} for frame in old_manifest['eye_envelopes']]
    new_frames=[{key:frame[key] for key in frame_keys} for frame in new_manifest['eye_envelopes']]
    report['eye_frame_exact_equal']=old_frames==new_frames
    parser=Path('/Users/lpz/Documents/Happy_Dash_Forward/tools/naifrog_inspect.py')
    for label,glb_path in [('V8',a.old_glb),('current',a.glb)]:
        data=existing.read_glb(glb_path,parser)
        report['GLB'][label]={}
        for name,mesh in data.items():
            reference=new[name]
            mapping=existing.bind_glb_roi(mesh,reference)
            counter_equal=oriented_faces(mesh['canonical_vertex_ids'][mesh['faces']])==oriented_faces(reference['faces'])
            report['GLB'][label][name]={'mapping':mapping,'oriented_canonical_triangle_multiset_exact_equal':counter_equal,
                                        'pass':mapping['complete_same_topology_mapping'] and mapping['max_basis_error_m']==0 and mapping['max_morph_delta_error_m']==0 and counter_equal}
    final={key:existing.sha(path) for key,path in paths.items()}
    report['final_sha256']=final
    report['input_bytes_unchanged']=initial==final
    report['reuse_v8_27_raw_geometry_results']=bool(report['input_bytes_unchanged'] and report['source_mesh_names_equal'] and report['eye_frame_exact_equal'] and all(item['pass'] for item in report['source'].values()) and all(item['pass'] for dataset in report['GLB'].values() for item in dataset.values()))
    report['uv_exact_equal']=all(item['equal_exact'] for item in report['source_uv'].values())
    report['reuse_limits']=['Applies only to V8 27 raw authored rest morph eye/mouth geometry result, whose checker does not inspect UV.',
                           'UV may differ; this comparison explicitly does not transfer texture/appearance acceptance.',
                           'Bone animation/support changed and must retain new native animation/sole verification.',
                           'Actual GLB vertices are mapped to unchanged SOURCE physical identities; raw export ordering/UV duplicates may differ.']
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'report':str(a.out),'reuse_v8_27_raw_geometry_results':report['reuse_v8_27_raw_geometry_results'],'uv_exact_equal':report['uv_exact_equal'],'input_bytes_unchanged':report['input_bytes_unchanged']}),flush=True)


if __name__=='__main__':
    main()
