"""Assign real atlas corners; bake original linear color to a usable sRGB map."""
import bpy,numpy as np,json,hashlib,struct,importlib.util,math
from pathlib import Path
from mathutils import Vector
import sys
root=Path(__file__).resolve().parent;trial=root.parents[1]/'work/nailong/uv-pbr-trial';trial.mkdir(exist_ok=True)
sys.path.insert(0,str(root))
from transfer_uv_corners import selected_atlas_path
skin=bpy.data.objects['NailongSkin_Reconstructed'];mesh=skin.data;rig=bpy.data.objects['NailongRig'];source=Path(bpy.data.filepath)
def sha(a):return hashlib.sha256(a).hexdigest()
def coords(key):
    output=np.empty(len(key.data)*3,np.float32);key.data.foreach_get('co',output);return output
def state():
    groups=sha(repr([(v.index,[(g.group,g.weight) for g in v.groups]) for v in mesh.vertices]).encode())
    loops=np.empty(len(mesh.loops),np.int32);mesh.loops.foreach_get('vertex_index',loops)
    rgba=np.empty(len(mesh.color_attributes.active_color.data)*4,np.float32);mesh.color_attributes.active_color.data.foreach_get('color',rgba)
    animations=[]
    for action in bpy.data.actions:
        curves=[(f.data_path,f.array_index,[(tuple(k.co),k.interpolation) for k in f.keyframe_points]) for f in action.fcurves]
        animations.append((action.name,curves))
    return {'vertices':len(mesh.vertices),'loops':len(mesh.loops),'polygons':len(mesh.polygons),'topology':sha(loops.tobytes()),'keys':{k.name:sha(coords(k).tobytes()) for k in mesh.shape_keys.key_blocks},'weights':groups,'original_corner_color':sha(rgba.tobytes()),'all_action_key_curves':sha(repr(animations).encode())}
before=state();atlas_path=selected_atlas_path(root);atlas=np.load(atlas_path);uv_data=atlas['corner_uv'];assert len(uv_data)==len(mesh.loops)
color_name=str(mesh.color_attributes.active_color.name);uv_name='BodyUV4k'
uv=mesh.uv_layers.new(name=uv_name);uv.data.foreach_set('uv',uv_data.ravel());mesh.uv_layers.active=mesh.uv_layers[uv_name];mesh.uv_layers[uv_name].active_render=True;mesh.update()
after_uv=state();assert before==after_uv
original_materials=list(mesh.materials)
image=bpy.data.images.new('Nailong body original colour 4K',width=4096,height=4096,alpha=True,float_buffer=False);image.colorspace_settings.name='sRGB'
bake_mat=bpy.data.materials.new('Body isolated unlit colour transfer');bake_mat.use_nodes=True;bake_mat.node_tree.nodes.clear()
output=bake_mat.node_tree.nodes.new('ShaderNodeOutputMaterial');emit=bake_mat.node_tree.nodes.new('ShaderNodeEmission');vertex=bake_mat.node_tree.nodes.new('ShaderNodeVertexColor');vertex.layer_name=color_name
bake_mat.node_tree.links.new(vertex.outputs['Color'],emit.inputs['Color']);bake_mat.node_tree.links.new(emit.outputs[0],output.inputs['Surface'])
target=bake_mat.node_tree.nodes.new('ShaderNodeTexImage');target.image=image;bake_mat.node_tree.nodes.active=target
for i in range(len(mesh.materials)):mesh.materials[i]=bake_mat
bpy.ops.object.select_all(action='DESELECT');skin.select_set(True);bpy.context.view_layer.objects.active=skin
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=1
scene.render.threads_mode='FIXED';scene.render.threads=2
print('ACTUAL_4K_EMISSION_COLOUR_BAKE_BEGIN',flush=True)
bpy.ops.object.bake(type='EMIT',target='IMAGE_TEXTURES',margin=2,margin_type='ADJACENT_FACES',use_clear=True,uv_layer=uv_name)
png_path=trial/'nailong_body_basecolor_4k_local_islands.png'
image.file_format='PNG';image.filepath_raw=str(png_path);image.save()
pixels=np.empty(4096*4096*4,np.float32);image.pixels.foreach_get(pixels);pixels=pixels.reshape(4096,4096,4)
for i,mat in enumerate(original_materials):mesh.materials[i]=mat
textured_material=original_materials[0].copy();textured_material.name='Nailong body 4K original colour PBR'
principled=textured_material.node_tree.nodes.get('Principled BSDF')
for link in list(textured_material.node_tree.links):
    if link.to_node==principled and link.to_socket==principled.inputs['Base Color']:textured_material.node_tree.links.remove(link)
texture=textured_material.node_tree.nodes.new('ShaderNodeTexImage');texture.image=image;texture.label='Baked original colour, sRGB; do not multiply original vertex colour'
uv_node=textured_material.node_tree.nodes.new('ShaderNodeUVMap');uv_node.uv_map=uv_name
textured_material.node_tree.links.new(uv_node.outputs['UV'],texture.inputs['Vector']);textured_material.node_tree.links.new(texture.outputs['Color'],principled.inputs['Base Color'])
mesh.materials[0]=textured_material
after=state();assert before==after
image.pack()
candidate=trial/'body_uv_4k_local_islands_candidate.blend';bpy.ops.wm.save_as_mainfile(filepath=str(candidate),compress=True)
spec=importlib.util.spec_from_file_location('existing_binding','/Users/lpz/Documents/Happy_Dash_Forward/tools/bind_reconstructed_nailong.py');binding=importlib.util.module_from_spec(spec);spec.loader.exec_module(binding)
# Same original six NLA clips; explicit UV and no dormant original color
# multiplier. Active color attributes remain editable in the saved .blend.
for actor in [rig,skin]:
    for block in binding.animation_data_blocks(actor):
        for track in block.nla_tracks:track.mute=False
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);skin.select_set(True);bpy.context.view_layer.objects.active=rig
glb=trial/'body_uv_4k_local_islands_only.glb'
bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,export_yup=True,export_apply=False,export_animations=True,export_animation_mode='ACTIONS',export_merge_animation='NLA_TRACK',export_force_sampling=False,export_nla_strips=True,export_skins=True,export_normals=True,export_tangents=False,export_texcoords=True,export_materials='EXPORT',export_vertex_color='MATERIAL',export_all_vertex_colors=False)
glb_audit=binding.audit_export(glb)
raw=glb.read_bytes();size=struct.unpack_from('<I',raw,12)[0];doc=json.loads(raw[20:20+size]);primitive=doc['meshes'][0]['primitives'][0];material=doc['materials'][primitive['material']]
assert 'TEXCOORD_0' in primitive['attributes'] and 'COLOR_0' not in primitive['attributes'] and 'baseColorTexture' in material['pbrMetallicRoughness']
report={'source':str(source),'source_sha256':sha(source.read_bytes()),'before':before,'after':after,'all_original_geometry_keys_weights_colors_and_action_curves_exact':before==after,'uv_layer':uv_name,'uv_corner_count':len(uv_data),'texture':{'path':str(png_path),'size':[4096,4096],'source':'Actual original linear vertex colour, unlit emission bake; no invented detail','colorspace':'sRGB','byte_image_pixels_are_srgb_encoded':True,'alpha_covered_or_extended_pixels':int((pixels[:,:,3]>.5).sum()),'nonconstant_rgb_std':pixels[:,:,:3].std(axis=(0,1)).tolist(),'sha256':sha(png_path.read_bytes())},'candidate':str(candidate),'candidate_sha256':sha(candidate.read_bytes()),'export':glb_audit,'actual_gltf_body_attributes':primitive['attributes'],'actual_gltf_material':material,'normal_or_roughness_texture_fabricated':False,'roughness_preserved':float(principled.inputs['Roughness'].default_value),'body_only_prototype':True}
(root/'BODY_UV_LOCAL_ISLANDS_BAKE_PROOF.json').write_text(json.dumps(report,indent=2)+'\n')
print('REAL_BODY_UV_4K_AND_MATERIAL_EXPORT_COMPLETE',glb_audit['sha256'],flush=True)
