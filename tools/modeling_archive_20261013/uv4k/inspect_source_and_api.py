"""Actual source UV/material and installed Blender API capability inspection."""
import bpy,numpy as np,json,hashlib
from pathlib import Path
root=Path(__file__).resolve().parent
source=Path(bpy.data.filepath);skin=bpy.data.objects['NailongSkin_Reconstructed'];mesh=skin.data
report={'source':str(source),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'blender':bpy.app.version_string,'objects':{},'installed_operator_capabilities':{}}
for obj in bpy.data.objects:
    if obj.type!='MESH':continue
    m=obj.data;uvs=[]
    for uv in m.uv_layers:
        coords=np.empty(len(uv.data)*2,dtype=np.float32);uv.data.foreach_get('uv',coords);coords=coords.reshape(-1,2)
        uvs.append({'name':uv.name,'loops':len(uv.data),'finite':bool(np.isfinite(coords).all()),'min':coords.min(axis=0).tolist(),'max':coords.max(axis=0).tolist(),'not_empty':bool(np.ptp(coords,axis=0).max()>1e-8)})
    materials=[]
    for mat in m.materials:
        nodes=[]
        if mat.use_nodes:
            for n in mat.node_tree.nodes:
                item={'name':n.name,'type':n.bl_idname}
                if n.type=='VERTEX_COLOR':item['layer_name']=n.layer_name
                if n.type=='TEX_IMAGE':item['image']=n.image.name if n.image else None;item['colorspace']=n.image.colorspace_settings.name if n.image else None
                if n.type=='BSDF_PRINCIPLED':item['roughness']=n.inputs['Roughness'].default_value;item['metallic']=n.inputs['Metallic'].default_value
                nodes.append(item)
        materials.append({'name':mat.name,'nodes':nodes,'links':[{'from':[l.from_node.name,l.from_socket.name],'to':[l.to_node.name,l.to_socket.name]} for l in mat.node_tree.links] if mat.use_nodes else []})
    report['objects'][obj.name]={'vertices':len(m.vertices),'polygons':len(m.polygons),'uv_layers':uvs,'color_attributes':[{'name':c.name,'domain':c.domain,'type':c.data_type} for c in m.color_attributes],'materials':materials,'modifiers':[{'name':mod.name,'type':mod.type} for mod in obj.modifiers]}
for key,op in [('unwrap',bpy.ops.uv.unwrap),('smart_project',bpy.ops.uv.smart_project),('bake',bpy.ops.object.bake),('export_gltf',bpy.ops.export_scene.gltf)]:
    rna=op.get_rna_type();properties={}
    for p in rna.properties:
        if p.identifier=='rna_type':continue
        if key=='export_gltf' and p.identifier not in ['export_texcoords','export_vertex_color','export_all_vertex_colors','export_active_vertex_color_when_no_material','export_tangents','export_materials','export_force_sampling','export_animation_mode','export_merge_animation']:continue
        properties[p.identifier]={'type':p.type,'default':str(getattr(p,'default',None)),'description':p.description,'enum':[i.identifier for i in p.enum_items] if p.type=='ENUM' else None}
    report['installed_operator_capabilities'][key]=properties
vertices=np.empty(len(mesh.vertices)*3,dtype=np.float32);mesh.shape_keys.key_blocks['Basis'].data.foreach_get('co',vertices);vertices=vertices.reshape(-1,3)
loops=np.empty(len(mesh.loops),dtype=np.int32);mesh.loops.foreach_get('vertex_index',loops);faces=loops.reshape(-1,3)
col=mesh.color_attributes.active_color;rgba=np.empty(len(col.data)*4,dtype=np.float32);col.data.foreach_get('color',rgba);rgba=rgba.reshape(-1,4)
np.savez(root/'source-body-geometry.npz',vertices=vertices,faces=faces,corner_rgba=rgba,source_vertex_id=np.arange(len(vertices),dtype=np.int32))
(root/'SOURCE_AND_API.json').write_text(json.dumps(report,indent=2)+'\n')
print('SOURCE_BODY_UV_REAL',report['objects'][skin.name]['uv_layers'])
print('SOURCE_BODY_MATERIAL',report['objects'][skin.name]['materials'])
print('API_PROPERTIES',[(k,len(v)) for k,v in report['installed_operator_capabilities'].items()])
