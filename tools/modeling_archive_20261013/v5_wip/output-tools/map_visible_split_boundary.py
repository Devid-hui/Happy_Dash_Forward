from pathlib import Path
import bpy,json,numpy as np,hashlib
root=Path(__file__).resolve().parent;work=root.parents[1]/'work/nailong/face-topology-v5'
manifest=json.loads((work/'V3_MODEL_MANIFEST.json').read_text());record={'source':bpy.data.filepath,'source_sha256':hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),'eyes':{}}
for side in ['left','right']:
 obj=bpy.data.objects['SharedEyelidFace_'+side];m=obj.data
 flags=np.empty(len(m.polygons),dtype=bool);m.attributes['NormalFanGhost'].data.foreach_get('value',flags)
 counts={}
 for p in m.polygons:
  if flags[p.index]:continue
  for edge in p.edge_keys:
   key=tuple(sorted(edge));counts[key]=counts.get(key,0)+1
 edges=[edge for edge,n in counts.items() if n==1];adj={}
 for a,b in edges:adj.setdefault(a,[]).append(b);adj.setdefault(b,[]).append(a)
 remain=set(adj);components=[]
 while remain:
  pending=[next(iter(remain))];component=set(pending)
  while pending:
   a=pending.pop()
   for b in adj[a]:
    if b not in component:component.add(b);pending.append(b)
  remain-=component;components.append(sorted(component))
 basis=np.empty(len(m.vertices)*3,dtype=np.float32);m.shape_keys.key_blocks['Basis'].data.foreach_get('co',basis);basis=basis.reshape(-1,3)
 center=np.asarray(manifest['face_helper']['measured_eyes'][side]['center']);r=np.asarray(manifest['face_helper']['measured_eyes'][side]['radii'])
 outer=max(components,key=lambda ids:np.median(((basis[ids,0]-center[0])/r[0])**2+((basis[ids,2]-center[2])/r[2])**2))
 source=np.empty(len(m.vertices),dtype=np.int32);m.attributes['OriginalSourceVertexID'].data.foreach_get('value',source)
 record['eyes'][side]={'outer_local_vertex_ids':outer,'outer_original_source_vertex_ids':source[outer].tolist(),'outer_basis_xyz_blender':basis[outer].tolist(),'actual_visible_boundary_components':[len(ids) for ids in components]}
(root/'visible-boundary-export-map.json').write_text(json.dumps(record,indent=2)+'\n');print('VISIBLE_BOUNDARY_MAP',[(s,len(x['outer_local_vertex_ids'])) for s,x in record['eyes'].items()])
