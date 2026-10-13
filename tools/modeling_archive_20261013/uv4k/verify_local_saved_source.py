"""Independent reopen check of the editable UV source and packed real PNG."""
import bpy,numpy as np,json,hashlib,sys
from pathlib import Path
root=Path(__file__).resolve().parent;sys.path.insert(0,str(root))
from transfer_uv_corners import selected_atlas_path
proof=json.loads((root/'BODY_UV_LOCAL_ISLANDS_BAKE_PROOF.json').read_text())
skin=bpy.data.objects['NailongSkin_Reconstructed'];mesh=skin.data
sha=lambda a:hashlib.sha256(a).hexdigest()
def coords(key):
    value=np.empty(len(key.data)*3,np.float32);key.data.foreach_get('co',value);return value
loops=np.empty(len(mesh.loops),np.int32);mesh.loops.foreach_get('vertex_index',loops)
rgba=np.empty(len(mesh.color_attributes.active_color.data)*4,np.float32);mesh.color_attributes.active_color.data.foreach_get('color',rgba)
animations=[]
for action in bpy.data.actions:
    curves=[(f.data_path,f.array_index,[(tuple(k.co),k.interpolation) for k in f.keyframe_points]) for f in action.fcurves]
    animations.append((action.name,curves))
state={'vertices':len(mesh.vertices),'loops':len(mesh.loops),'polygons':len(mesh.polygons),'topology':sha(loops.tobytes()),'keys':{k.name:sha(coords(k).tobytes()) for k in mesh.shape_keys.key_blocks},'weights':sha(repr([(v.index,[(g.group,g.weight) for g in v.groups]) for v in mesh.vertices]).encode()),'original_corner_color':sha(rgba.tobytes()),'all_action_key_curves':sha(repr(animations).encode())}
assert state==proof['before']
uv=np.empty(len(mesh.loops)*2,np.float32);mesh.uv_layers['BodyUV4k'].data.foreach_get('uv',uv)
expected=np.load(selected_atlas_path(root))['corner_uv'];assert np.array_equal(uv.reshape(-1,2),expected)
material=mesh.materials[0];principled=material.node_tree.nodes.get('Principled BSDF')
links=[l for l in material.node_tree.links if l.to_node==principled and l.to_socket==principled.inputs['Base Color']];assert len(links)==1 and links[0].from_node.type=='TEX_IMAGE'
image=links[0].from_node.image;assert list(image.size)==[4096,4096] and image.colorspace_settings.name=='sRGB' and image.packed_file
packed_sha=sha(bytes(image.packed_file.data));assert packed_sha==proof['texture']['sha256']
report={'saved_source':bpy.data.filepath,'saved_source_sha256':sha(Path(bpy.data.filepath).read_bytes()),'original_geometry_keys_weights_corner_colors_action_curves_exact_after_save_reopen':True,'all5412459_uv_corners_match_selected_atlas_bit_exact':True,'actual_color_attribute_type':mesh.color_attributes.active_color.data_type,'actual_color_attribute_domain':mesh.color_attributes.active_color.domain,'material_base_color_is_real_image_only':True,'packed_png_sha256':packed_sha,'packed_png_matches_actual_written_texture_bytes':True,'real_image_size':list(image.size),'real_image_colorspace':image.colorspace_settings.name,'body_roughness':float(principled.inputs['Roughness'].default_value),'rig_bone_count':len(bpy.data.objects['NailongRig'].data.bones),'state':state,'scope':'Actual editable fullc3 source-copy reopen. Only Body UV/material changed; remaining face-source/UV work is not declared complete.'}
(root/'LOCAL_ISLANDS_SAVED_SOURCE_REOPEN_PROOF.json').write_text(json.dumps(report,indent=2)+'\n')
print('ACTUAL_SAVED_SOURCE_REOPEN_EXACT',packed_sha,flush=True)
