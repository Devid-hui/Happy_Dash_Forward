"""Read actual GLB bytes, compare six original clips and float lid times."""
import hashlib,json
from pathlib import Path
import numpy as np
from glb_arrays import arrays
ROOT=Path(__file__).resolve().parent
WORK=ROOT.parents[1]/'work/nailong/face-topology-v5/lod-candidates'
V3=ROOT.parents[1]/'work/nailong/rig-candidate/face-tail-trial-v3'

def curves(doc,access):
    joints=set(doc['skins'][0]['joints']);result={}
    for animation in doc['animations']:
        channels={}
        for channel in animation['channels']:
            node=channel['target'].get('node');path=channel['target']['path']
            if node not in joints:continue
            sampler=animation['samplers'][channel['sampler']]
            channels[(doc['nodes'][node]['name'],path)]=(access[sampler['input']].ravel(),access[sampler['output']],sampler.get('interpolation','LINEAR'))
        result[animation['name']]=channels
    return result

def interpolate(time,values,samples):
    if len(time)==1:return np.repeat(values[:1],len(samples),axis=0)
    return np.column_stack([np.interp(samples,time,values[:,i]) for i in range(values.shape[1])])

def audit(level):
    baseline=V3/('nailong_lod%d.glb'%level);path=WORK/('nailong_lod%d.glb'%level)
    old,oa=arrays(baseline);doc,a=arrays(path)
    before,after=curves(old,oa),curves(doc,a)
    assert sorted(before)==sorted(after)==['charge','chase','idle','recover','walk','warn']
    assert len(doc['skins'])==1 and len(doc['skins'][0]['joints'])==24
    clips={}
    for name in before:
        assert set(before[name])==set(after[name]),name
        maximum=0.;identical_time_arrays=True
        for key,(t,v,kind) in before[name].items():
            nt,nv,nkind=after[name][key];assert kind==nkind=='LINEAR',(name,key,kind,nkind)
            times=np.union1d(t,nt);reference=interpolate(t,v,times);actual=interpolate(nt,nv,times)
            if key[1]=='rotation':
                error=np.minimum(np.linalg.norm(reference-actual,axis=1),np.linalg.norm(reference+actual,axis=1)).max()
            else:error=np.abs(reference-actual).max()
            maximum=max(maximum,float(error));identical_time_arrays &= np.array_equal(t,nt)
        assert maximum<=1e-5,(name,maximum)
        old_animation=next(x for x in old['animations'] if x['name']==name)
        animation=next(x for x in doc['animations'] if x['name']==name)
        duration=max(float(a[s['input']].max()) for s in animation['samplers'])
        prior_duration=max(float(oa[s['input']].max()) for s in old_animation['samplers'])
        assert abs(duration-prior_duration)<1e-6,(name,duration,prior_duration)
        clips[name]={'bone_channels':len(before[name]),'bone_value_max_difference':maximum,'all_bone_time_arrays_bitwise_equal':identical_time_arrays,'duration_s':duration,'original_duration_s':prior_duration}
    lids=[]
    for mesh_index,mesh in enumerate(doc['meshes']):
        if 'Shared' not in mesh['name'] or 'eyelid' not in mesh['name']:continue
        names=mesh['extras']['targetNames']
        assert len(names)==121 and names.count('Blink')==1 and names.count('Focus')==1 and names.count('Open')==1
        assert all(n in ['Blink','Focus','Open'] or (len(n)==11 and n.startswith('LidB') and n[7]=='F') for n in names)
        nodes={i for i,node in enumerate(doc['nodes']) if node.get('mesh')==mesh_index}
        samples=[]
        for animation in doc['animations']:
            for channel in animation['channels']:
                if channel['target'].get('node') not in nodes or channel['target']['path']!='weights':continue
                sampler=animation['samplers'][channel['sampler']]
                times=a[sampler['input']].ravel();weights=a[sampler['output']].reshape(-1,len(names))
                noninteger=int((np.abs(times*30-np.round(times*30))>1e-5).sum())
                if animation['name'] in ['idle','recover']:assert noninteger>0,(mesh['name'],animation['name'])
                assert sampler.get('interpolation','LINEAR')=='LINEAR'
                assert np.isfinite(weights).all()
                samples.append({'clip':animation['name'],'keys':len(times),'actual_noninteger_frame_times':noninteger,'Blink_peak':float(weights[:,names.index('Blink')].max())})
        lids.append({'mesh':mesh['name'],'targets':len(names),'actual_weight_samplers':samples})
    assert len(lids)==2,len(lids)
    return {'level':level,'file':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'baseline_sha256':hashlib.sha256(baseline.read_bytes()).hexdigest(),'clips':clips,'joint_lid_semantics':lids,'status':'CLIP_AND_FLOAT_SAMPLER_CONTRACT_PASS_NOT_GEOMETRY_OR_ART_PASS'}

if __name__=='__main__':
    import sys
    levels=[int(x) for x in sys.argv[1:]] or [0,1,2]
    report={'files':[audit(level) for level in levels]}
    (ROOT/'dual-glb-clip-contract.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
