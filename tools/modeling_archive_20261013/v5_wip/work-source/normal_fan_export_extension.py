"""A process-local standard glTF gather_mesh_hook, after normal extraction."""
class glTF2ExportUserExtension:
 def __init__(self):
  self.removed=[]
 def gather_mesh_hook(self,gltf_mesh,blender_mesh,blender_object,vertex_groups,modifiers,materials,export_settings):
  kept=[]
  for primitive in gltf_mesh.primitives:
   material=primitive.material
   if material is not None and material.name=='Eye transition normal fan alpha zero':
    self.removed.append({'mesh':gltf_mesh.name,'material':material.name,'target_count':len(primitive.targets or [])})
   else:kept.append(primitive)
  gltf_mesh.primitives=kept

def install():
 import bpy,io_scene_gltf2
 if 'io_scene_gltf2' not in bpy.context.preferences.addons:
  raise RuntimeError('Official exporter is not an enabled module; no preferences or plugin configuration will be changed.')
 old=getattr(io_scene_gltf2,'glTF2ExportUserExtensions',None)
 instance=glTF2ExportUserExtension()
 io_scene_gltf2.glTF2ExportUserExtensions=list(old or [])+[lambda:instance]
 def restore():
  if old is None:del io_scene_gltf2.glTF2ExportUserExtensions
  else:io_scene_gltf2.glTF2ExportUserExtensions=old
 return instance,restore
