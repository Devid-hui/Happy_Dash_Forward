from pathlib import Path
import json,numpy as np,hashlib
from glb_arrays import arrays,xyz_to_blender
root=Path(__file__).resolve().parent;work=root.parents[1]/'work/nailong/face-topology-v5'
raw,ra=arrays(work/'direct-fan-high-probe.glb');doc,a=arrays(work/'direct-fan-high-visible.glb')
mapping=json.loads((root/'visible-boundary-export-map.json').read_text())
def normalized(x):return x/np.maximum(np.linalg.norm(x,axis=1)[:,None],1e-30)
def angles(x,y):return np.degrees(np.arccos(np.clip(np.sum(normalized(x)*normalized(y),axis=1),-1,1)))
def primitive(name):
 mesh=next(m for m in doc['meshes'] if m['name']==name);assert len(mesh['primitives'])==1
 return mesh,mesh['primitives'][0]
body,bp=primitive('MLS surface before voxel resampling')
pos=xyz_to_blender(a[bp['attributes']['POSITION']]);bn=a[bp['attributes']['NORMAL']]
bt={name:a[target['NORMAL']] for name,target in zip(body['extras']['targetNames'],bp['targets'])}
report={'source_sha256':mapping['source_sha256'],'visible_glb_sha256':hashlib.sha256((work/'direct-fan-high-visible.glb').read_bytes()).hexdigest(),'normal_arrays_unchanged_by_standard_helper_drop':True,'eyes':{},'runtime_helper_material_references':[]}
for mesh in doc['meshes']:
 old=next(m for m in raw['meshes'] if m['name']==mesh['name']);op=old['primitives'][0];p=mesh['primitives'][0]
 for field in ['POSITION','NORMAL']:
  assert np.array_equal(ra[op['attributes'][field]],a[p['attributes'][field]]),(mesh['name'],field)
 for before,after in zip(op.get('targets',[]),p.get('targets',[])):
  for field in ['POSITION','NORMAL']:
   assert np.array_equal(ra[before[field]],a[after[field]]),(mesh['name'],field)
 for p in mesh['primitives']:
  if 'normal fan' in doc['materials'][p['material']].get('name',''):report['runtime_helper_material_references'].append(mesh['name'])
assert not report['runtime_helper_material_references']
for side,proof in mapping['eyes'].items():
 mesh,p=primitive('Shared '+side+' face and eyelid joint patch')
 fp=xyz_to_blender(a[p['attributes']['POSITION']]);fn=a[p['attributes']['NORMAL']]
 ft={name:a[target['NORMAL']] for name,target in zip(mesh['extras']['targetNames'],p['targets'])}
 targets=np.asarray(proof['outer_basis_xyz_blender']);low=targets.min(axis=0)-1e-5;high=targets.max(axis=0)+1e-5
 candidate=np.flatnonzero(np.all((pos>=low)&(pos<=high),axis=1))
 table={}
 for i in candidate:table.setdefault(tuple(np.round(pos[i]*1e6).astype(np.int64)),[]).append(int(i))
 ftable={}
 for i,point in enumerate(fp):ftable.setdefault(tuple(np.round(point*1e6).astype(np.int64)),[]).append(i)
 bind=[];face=[]
 for point in targets:
  key=tuple(np.round(point*1e6).astype(np.int64));f=ftable[key][0]
  possibilities=table[key];best=possibilities[int(np.argmin(angles(bn[possibilities],np.repeat(fn[f:f+1],len(possibilities),axis=0))))]
  bind.append(best);face.append(f)
 bind=np.asarray(bind);face=np.asarray(face)
 states=[]
 for b in np.linspace(0,1,11):
  for f in np.linspace(0,1,21):
   bi=min(9,int(b*10));fi=min(9,int(f*10));bw=b*10-bi;fw=f*10-fi
   normal=fn[face].copy()
   for db,wb in [(0,1-bw),(1,bw)]:
    for df,wf in [(0,1-fw),(1,fw)]:
     bb,ff=bi+db,fi+df
     if not (bb or ff):continue
     key='Blink' if (bb,ff)==(10,0) else 'Focus' if (bb,ff)==(0,10) else 'LidB%03dF%03d'%(bb*10,ff*10)
     normal+=wb*wf*ft[key][face]
   body_normal=bn[bind]+f*bt['Focus'][bind]
   err=angles(normal,body_normal)
   states.append({'B':float(b),'F':float(f),'max_degrees':float(err.max())})
 worst=max(states,key=lambda x:x['max_degrees'])
 report['eyes'][side]={'mapped_boundary_vertices':len(bind),'grid_and_mid_F_states':len(states),'actual_LINEAR_NORMAL_mix_worst':worst,'pass_original_0_05_degree_threshold':worst['max_degrees']<.05}
report['all_actual_normal_mix_boundaries_pass']=all(x['pass_original_0_05_degree_threshold'] for x in report['eyes'].values())
(root/'visible-glb-normal-mix-audit.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
