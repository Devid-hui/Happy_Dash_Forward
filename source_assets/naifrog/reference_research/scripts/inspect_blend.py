"""Read-only data inspection of downloaded Blend files; run with --disable-autoexec."""
import bpy
import bmesh
import json
import os
import sys
from pathlib import Path

args = sys.argv[sys.argv.index('--') + 1:]
out = Path(args[0])
report = {
    'blender_version': bpy.app.version_string,
    'source_file': bpy.data.filepath,
    'inspection': 'data inventory only; no imported script executed; no source saved',
    'scene': {'fps': bpy.context.scene.render.fps,
              'frame_start': bpy.context.scene.frame_start,
              'frame_end': bpy.context.scene.frame_end},
    'objects': [], 'actions': [], 'materials': [], 'images': [], 'text_blocks': [],
}
for obj in bpy.data.objects:
    item = {'name': obj.name, 'type': obj.type,
            'parent': obj.parent.name if obj.parent else None,
            'location': list(obj.location), 'rotation': list(obj.rotation_euler),
            'scale': list(obj.scale), 'dimensions': list(obj.dimensions),
            'hidden_render': obj.hide_render,
            'modifiers': [{'name': m.name, 'type': m.type,
                           'object': m.object.name if hasattr(m, 'object') and m.object else None}
                          for m in obj.modifiers],
            'animation_data': None}
    if obj.animation_data:
        ad = obj.animation_data
        item['animation_data'] = {
            'action': ad.action.name if ad.action else None,
            'nla_tracks': [{'name': t.name, 'strips': [
                {'name': s.name, 'action': s.action.name if s.action else None,
                 'frame_start': s.frame_start, 'frame_end': s.frame_end}
                for s in t.strips]} for t in ad.nla_tracks],
            'drivers': [{'path': f.data_path, 'type': f.driver.type,
                         'expression': f.driver.expression} for f in ad.drivers]}
    if obj.type == 'MESH':
        mesh = obj.data
        mesh.calc_loop_triangles()
        bm = bmesh.new(); bm.from_mesh(mesh)
        weighted = []; unweighted = 0; badsum = 0; max_influences = 0
        for v in mesh.vertices:
            weights = [g.weight for g in v.groups if g.weight > 0]
            if not weights: unweighted += 1
            if weights and abs(sum(weights) - 1) > 1e-4: badsum += 1
            max_influences = max(max_influences, len(weights))
        item['mesh'] = {
            'vertices': len(mesh.vertices), 'edges': len(mesh.edges),
            'polygons': len(mesh.polygons), 'triangles': len(mesh.loop_triangles),
            'polygon_sizes': {str(n): sum(len(p.vertices) == n for p in mesh.polygons)
                              for n in sorted({len(p.vertices) for p in mesh.polygons})},
            'boundary_edges': sum(e.is_boundary for e in bm.edges),
            'non_manifold_edges': sum(not e.is_manifold for e in bm.edges),
            'loose_vertices': sum(not v.link_edges for v in bm.verts),
            'uv_layers': [{'name': uv.name, 'loops': len(uv.data),
                           'min': [min((d.uv[i] for d in uv.data), default=0) for i in (0, 1)],
                           'max': [max((d.uv[i] for d in uv.data), default=0) for i in (0, 1)]}
                          for uv in mesh.uv_layers],
            'materials': [m.name if m else None for m in mesh.materials],
            'vertex_groups': [g.name for g in obj.vertex_groups],
            'weight_summary': {'unweighted_vertices': unweighted,
                               'non_normalized_weight_vertices': badsum,
                               'max_influences': max_influences},
            'shape_keys': [k.name for k in mesh.shape_keys.key_blocks] if mesh.shape_keys else [],
        }
        bm.free()
    if obj.type == 'ARMATURE':
        item['armature'] = {'bones': len(obj.data.bones),
             'deform_bones': sum(b.use_deform for b in obj.data.bones),
             'bone_list': [{'name': b.name, 'parent': b.parent.name if b.parent else None,
                            'deform': b.use_deform, 'head_local': list(b.head_local),
                            'tail_local': list(b.tail_local)} for b in obj.data.bones],
             'constraints': [{'bone': b.name, 'constraints': [
                 {'name': c.name, 'type': c.type, 'target':
                    c.target.name if hasattr(c, 'target') and c.target else None,
                  'subtarget': c.subtarget if hasattr(c, 'subtarget') else None}
                 for c in b.constraints]} for b in obj.pose.bones if b.constraints]}
    report['objects'].append(item)
for action in bpy.data.actions:
    curves = []
    if hasattr(action, 'fcurves'):
        curves = list(action.fcurves)
    else:
        for layer in action.layers:
            for strip in layer.strips:
                for slot in action.slots:
                    bag = strip.channelbag(slot, ensure=False)
                    if bag: curves.extend(bag.fcurves)
    report['actions'].append({'name': action.name, 'frame_range': list(action.frame_range),
          'users': action.users, 'fake_user': action.use_fake_user,
          'curve_count': len(curves), 'keyframe_count': sum(len(f.keyframe_points) for f in curves),
          'animated_paths': sorted({f.data_path for f in curves})})
for material in bpy.data.materials:
    report['materials'].append({'name': material.name, 'use_nodes': material.use_nodes,
          'nodes': [{'name': n.name, 'type': n.type,
                     'image': n.image.name if n.type == 'TEX_IMAGE' and n.image else None}
                    for n in material.node_tree.nodes] if material.node_tree else []})
for img in bpy.data.images:
    path = bpy.path.abspath(img.filepath)
    report['images'].append({'name': img.name, 'size': list(img.size), 'source': img.source,
         'filepath': img.filepath, 'resolved_filepath': path,
         'packed': bool(img.packed_file), 'exists': os.path.exists(path)})
for txt in bpy.data.texts:
    report['text_blocks'].append({'name': txt.name, 'use_module': txt.use_module,
                                 'characters': len(txt.as_string())})
out.write_text(json.dumps(report, indent=2, ensure_ascii=False))
print(json.dumps({'written': str(out), 'meshes': sum(o.type == 'MESH' for o in bpy.data.objects),
                  'armatures': sum(o.type == 'ARMATURE' for o in bpy.data.objects),
                  'actions': [a.name for a in bpy.data.actions]}))
