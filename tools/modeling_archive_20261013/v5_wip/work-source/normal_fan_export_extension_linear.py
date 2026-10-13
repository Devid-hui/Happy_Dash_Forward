"""Standard post-extraction hook: runtime normals use the same Body linear law."""
import copy,numpy as np
from pathlib import Path
import json
class glTF2ExportUserExtension:
 def __init__(self):
  self.removed=[];self.fixed=[];self.body=None
  root=Path(__file__).parents[3]/'outputs/nailong-face-topology-v5'
  self.mapping=json.loads((root/'visible-boundary-export-map.json').read_text())['eyes']
 @staticmethod
 def array(accessor):
  width=3;count=accessor.count
  if accessor.buffer_view is None:out=np.zeros((count,width),dtype=np.float32)
  else:out=np.frombuffer(accessor.buffer_view.data,dtype='<f4',count=count*width,offset=accessor.byte_offset or 0).reshape(-1,width).copy()
  if accessor.sparse:
   sparse=accessor.sparse;indices=sparse.indices;values=sparse.values
   dtype={5121:'u1',5123:'<u2',5125:'<u4'}[indices.component_type]
   ids=np.frombuffer(indices.buffer_view.data,dtype=dtype,count=sparse.count,offset=indices.byte_offset or 0)
   out[ids]=np.frombuffer(values.buffer_view.data,dtype='<f4',count=sparse.count*width,offset=values.byte_offset or 0).reshape(-1,width)
  return out
 @staticmethod
 def accessor(original,array):
  from io_scene_gltf2.io.exp.binary_data import BinaryData
  result=copy.copy(original)
  result.buffer_view=BinaryData(np.asarray(array,dtype='<f4').tobytes())
  result.byte_offset=None;result.sparse=None;result.min=None;result.max=None
  return result
 def gather_mesh_hook(self,gltf_mesh,blender_mesh,blender_object,vertex_groups,modifiers,materials,export_settings):
  kept=[]
  for primitive in gltf_mesh.primitives:
   if primitive.material is not None and primitive.material.name=='Eye transition normal fan alpha zero':
    self.removed.append({'mesh':gltf_mesh.name,'material':primitive.material.name,'target_count':len(primitive.targets or [])})
   else:kept.append(primitive)
  gltf_mesh.primitives=kept
  if blender_object is None:return
  if blender_object.name=='NailongSkin_Reconstructed':
   assert len(kept)==1
   p=kept[0];positions=self.array(p.attributes['POSITION']);normals=self.array(p.attributes['NORMAL'])
   names=gltf_mesh.extras['targetNames']
   targets={n:self.array(t['NORMAL']) for n,t in zip(names,p.targets)}
   self.body=(positions,normals,targets)
  elif blender_object.name.startswith('SharedEyelidFace_'):
   if self.body is None:raise RuntimeError('Body normal law must be gathered before local Face')
   side='left' if blender_object.name.endswith('left') else 'right'
   p=kept[0];positions=self.array(p.attributes['POSITION']);normals=self.array(p.attributes['NORMAL']);names=gltf_mesh.extras['targetNames']
   targets=self.mapping[side]['outer_basis_xyz_blender']
   xyz=np.asarray(targets)[:,[0,2,1]]*np.array([1,1,-1])
   bp,bn,bt=self.body
   bounds=(xyz.min(axis=0)-1e-5,xyz.max(axis=0)+1e-5)
   candidates=np.flatnonzero(np.all((bp>=bounds[0])&(bp<=bounds[1]),axis=1))
   body_table={}
   for i in candidates:body_table.setdefault(tuple(np.round(bp[i].astype(np.float64)*1e6).astype(np.int64)),[]).append(int(i))
   face_table={}
   for i,point in enumerate(positions):face_table.setdefault(tuple(np.round(np.asarray(point,dtype=np.float64)*1e6).astype(np.int64)),[]).append(i)
   indices=[];body_indices=[]
   for point in xyz:
    key=tuple(np.round(np.asarray(point,dtype=np.float64)*1e6).astype(np.int64))
    for face in face_table[key]:
     options=body_table[key]
     choice=options[int(np.argmin(np.linalg.norm(bn[options]-normals[face],axis=1)))]
     indices.append(face);body_indices.append(choice)
   indices=np.asarray(indices);body_indices=np.asarray(body_indices)
   normals[indices]=bn[body_indices]
   p.attributes['NORMAL']=self.accessor(p.attributes['NORMAL'],normals)
   for name,target in zip(names,p.targets):
    values=self.array(target['NORMAL'])
    coefficient=1 if name=='Focus' else 0 if name in ['Blink','Open'] else int(name[8:11])/100
    values[indices]=bt['Open'][body_indices] if name=='Open' else coefficient*bt['Focus'][body_indices]
    target['NORMAL']=self.accessor(target['NORMAL'],values)
   self.fixed.append({'mesh':gltf_mesh.name,'side':side,'actual_export_boundary_vertices':len(indices),'same_Body_linear_Normal_law_for_all_targets':True})
def install():
 import bpy,io_scene_gltf2
 if 'io_scene_gltf2' not in bpy.context.preferences.addons:raise RuntimeError('No exporter module enabled; preferences will not be changed.')
 old=getattr(io_scene_gltf2,'glTF2ExportUserExtensions',None);instance=glTF2ExportUserExtension()
 io_scene_gltf2.glTF2ExportUserExtensions=list(old or [])+[lambda:instance]
 def restore():
  if old is None:del io_scene_gltf2.glTF2ExportUserExtensions
  else:io_scene_gltf2.glTF2ExportUserExtensions=old
 return instance,restore
