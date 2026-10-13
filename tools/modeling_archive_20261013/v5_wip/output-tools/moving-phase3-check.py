"""Actual source NLA walk/chase comparison, with only a legacy Body Focus override."""
import bpy, json, hashlib, math, traceback
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parent
namespace = {'__file__': str(ROOT / 'review-direct-fan.py')}
text = (ROOT / 'review-direct-fan.py').read_text()
exec(text[:text.index('def main():')], namespace)
for name in ['sha', 'float_coordinates', 'loop_ids', 'point_ids', 'world_points', 'transform_normals', 'topology', 'body_boundary_pairs', 'sample_clearance', 'visible_polygons', 'summary', 'angle']:
    globals()[name] = namespace[name]
from mathutils.bvhtree import BVHTree
from mathutils import Quaternion
WORK = ROOT.parents[1] / 'work/nailong/face-topology-v5'
SOURCE = WORK / 'source-dual-eye-joint-direct-fan-linear.blend'
EXPECTED = '2b8016d6929bba31b0e5f04df4a8e975b45698dbe0fdbfbc40c899506c95b1f4'
REPORT = {'status': 'started', 'source': str(SOURCE), 'CPU_only': True, 'Godot_launched': False, 'cases': []}


def activate(block, clip):
    if block is None or block.animation_data is None: return
    block.animation_data.action = None
    for track in block.animation_data.nla_tracks: track.mute = track.name != clip


def posed_target(obj):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get()); mesh = evaluated.to_mesh(); mesh.calc_loop_triangles()
    points = world_points(obj, mesh); tri = np.asarray([t.vertices[:] for t in mesh.loop_triangles], dtype=np.int64)
    result = {'object': obj.name, 'tree': BVHTree.FromPolygons(points.tolist(), tri.tolist(), all_triangles=True),
              'minimum': points.min(axis=0), 'maximum': points.max(axis=0), 'triangles': tri}
    evaluated.to_mesh_clear(); return result


try:
    REPORT['source_sha256_before'] = sha(SOURCE)
    if REPORT['source_sha256_before'] != EXPECTED: raise RuntimeError('Moving probe source identity differs')
    actor_path = Path('/Users/lpz/Documents/Happy_Dash_Forward/scripts/enemies/hunter_visual.gd')
    actor_source = actor_path.read_text(); REPORT['actor_source_sha256'] = sha(actor_path)
    REPORT['latest_source_has_shared_face_guard'] = 'if _has_shared_eyelid_faces:' in actor_source
    REPORT['scope'] = 'Actual Blender source NLA walk/chase, actual armature evaluation and posed ocular BVHs. Forced Body .22 is the requested pre-fix moving-phase3 regression simulation. Latest actor source has a shared-Face guard. No Godot playback or GLB NORMAL claim.'
    for clip, seconds, authored_focus in [('walk', .23, .12), ('chase', .16, .27)]:
        for legacy_force in [False, True]:
            bpy.ops.wm.open_mainfile(filepath=str(SOURCE), load_ui=False)
            body = bpy.data.objects['NailongSkin_Reconstructed']; rig = bpy.data.objects['NailongRig']
            patches = {s: bpy.data.objects['SharedEyelidFace_' + s] for s in ['left', 'right']}
            actors = [o for o in bpy.context.scene.objects if o.type in {'MESH', 'ARMATURE'}]
            for obj in actors:
                activate(obj, clip); activate(getattr(obj.data, 'shape_keys', None), clip)
            fps = bpy.context.scene.render.fps / bpy.context.scene.render.fps_base; frame = seconds * fps
            bpy.context.scene.frame_set(int(frame), subframe=frame - math.floor(frame)); bpy.context.view_layer.update()
            authored_body_values = {k.name: float(k.value) for k in body.data.shape_keys.key_blocks}
            face_values = {s: {k.name: float(k.value) for k in o.data.shape_keys.key_blocks if abs(k.value) > 1e-8} for s, o in patches.items()}
            # Freeze the actual NLA-evaluated rig pose and Body values before
            # applying the additional common-head moving-recovery rotation.
            rig.animation_data.action = None
            for track in rig.animation_data.nla_tracks: track.mute = True
            body.data.shape_keys.animation_data_clear()
            for key in body.data.shape_keys.key_blocks: key.value = authored_body_values[key.name]
            body.data.shape_keys.key_blocks['Focus'].value = .22 if legacy_force else authored_focus
            head = rig.pose.bones.get('head')
            if head:
                head.rotation_mode = 'QUATERNION'; head.rotation_quaternion = head.rotation_quaternion @ Quaternion((1, 0, 0), .035 + .010 * math.sin(seconds * 3.4))
            bpy.context.view_layer.update()
            with bpy.data.libraries.load(str(WORK / 'source-v3-stable.blend'), link=False) as (available, loaded): loaded.objects = ['NailongSkin_Reconstructed']
            original = loaded.objects[0]; original_faces = loop_ids(original.data).reshape(-1, 3); source_points = float_coordinates(original.data.shape_keys.key_blocks['Basis']).astype(np.float64)
            manifest = json.loads((WORK / 'V3_MODEL_MANIFEST.json').read_text())
            body_eval = body.evaluated_get(bpy.context.evaluated_depsgraph_get()); bm = body_eval.to_mesh(); bp = world_points(body, bm)
            entry = {'clip': clip, 'seconds': seconds, 'scene_fps': fps, 'actual_NLA_frame': frame, 'legacy_force_Body_Focus_022': legacy_force,
                     'authored_Face_Focus': authored_focus, 'Body_Focus_applied': .22 if legacy_force else authored_focus,
                     'actual_authored_Body_key_values': authored_body_values, 'actual_active_Face_NLA_weights': face_values, 'eyes': {}}
            for side, obj in patches.items():
                _, topo = topology(obj, original_faces, source_points, manifest['face_helper']['measured_eyes'][side]); pairs = body_boundary_pairs(body, obj, topo)
                evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get()); mesh = evaluated.to_mesh(); points = world_points(obj, mesh)
                body_normals = transform_normals(body, np.asarray([bm.corner_normals[int(i)].vector[:] for i in pairs[:, 3]], dtype=np.float64))
                face_normals = transform_normals(obj, np.asarray([mesh.corner_normals[int(i)].vector[:] for i in pairs[:, 2]], dtype=np.float64))
                mesh.calc_loop_triangles(); tri = np.asarray([t.vertices[:] for t in mesh.loop_triangles], dtype=np.int64); poly = np.asarray([t.polygon_index for t in mesh.loop_triangles], dtype=np.int64)
                mask = np.isin(poly, list(topo['visible_polygons'])); tri = tri[mask]; poly = poly[mask]
                difference = np.linalg.norm(points[pairs[:, 0]] - bp[pairs[:, 1]], axis=1); corner_angle = angle(face_normals, body_normals)
                worst = int(np.argmax(difference))
                targets = [posed_target(bpy.data.objects['ReconstructedSclera_' + side]), posed_target(bpy.data.objects['ReconstructedCorneal_' + side])]
                entry['eyes'][side] = {'boundary_world_position_difference_m': summary(difference), 'actual_corner_normal_difference_degrees': summary(corner_angle),
                    'worst_boundary_original_source_vertex': int(pairs[worst, 1]), 'Face_world_xyz_m': points[pairs[worst, 0]].tolist(), 'Body_world_xyz_m': bp[pairs[worst, 1]].tolist(),
                    'actual_posed_ocular_sample_clearance': {t['object']: sample_clearance(points, tri, poly, t, topo['visible_vertices']) for t in targets}}
                evaluated.to_mesh_clear()
            body_eval.to_mesh_clear(); REPORT['cases'].append(entry)
            print('MOVING_PHASE3_CASE', clip, legacy_force, {s: e['boundary_world_position_difference_m']['max'] for s, e in entry['eyes'].items()}, flush=True)
    REPORT['source_sha256_after'] = sha(SOURCE)
    if REPORT['source_sha256_after'] != EXPECTED: raise RuntimeError('Immutable moving probe source changed')
    REPORT['status'] = 'completed'
except Exception as exc:
    REPORT['status'] = 'failed'; REPORT['error'] = repr(exc); REPORT['traceback'] = traceback.format_exc()
finally:
    REPORT['probe_script_sha256'] = sha(__file__)
    (ROOT / 'moving-phase3-check.json').write_text(json.dumps(REPORT, indent=2, ensure_ascii=False) + '\n')
    print('MOVING_PHASE3_CHECK', REPORT['status'], REPORT.get('error'), flush=True)
