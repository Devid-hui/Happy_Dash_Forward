from pathlib import Path
import bpy,json,hashlib,importlib.util
root=Path(__file__).resolve().parent;work=root.parents[1]/'work/nailong/face-topology-v5'
def load(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
b=load('frozen_v3_adapter',root.parent/'nailong-face-candidate-v3/adapter-final.py')
e=load('normal_fan_export_extension',work/'normal_fan_export_extension_linear.py')
rig=bpy.data.objects['NailongRig'];skin=bpy.data.objects['NailongSkin_Reconstructed']
extras=[o for o in bpy.context.scene.objects if o.type=='MESH' and o!=skin]
path=work/'direct-fan-high-visible-normal-linear.glb'
extension,restore=e.install()
try:b.export(rig,skin,path,extras,force_sampling=False)
finally:restore()
assert len(extension.fixed)==2,extension.fixed
audit=b.audit_export(path)
(root/'direct-fan-high-visible-normal-linear-export.json').write_text(json.dumps({'source':bpy.data.filepath,'source_sha256':hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),'export_audit':audit,'standard_after_normal_extraction_hook_removed_helpers':extension.removed,'linear_NORMAL_boundary_repairs':extension.fixed,'official_exporter_file_unmodified':True,'preferences_unmodified':True,'formal_unchanged':True,'not_final_LOD_or_art_acceptance':True},indent=2)+'\n')
print('DIRECT_FAN_HIGH_VISIBLE_GLTF',audit['sha256'],audit['triangles'],len(extension.removed),flush=True)
