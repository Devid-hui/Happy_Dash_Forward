"""Bind a supplied, genuinely reconstructed Nailong surface without replacing its shape.

Blender 4.5: --background --threads 4 --python tools/bind_reconstructed_nailong.py --
    --input /absolute/final-surface.glb --repo /absolute/Happy_Dash_Forward

The source is Z-up and faces -Y after Blender's glTF import. This adapter rotates
the actual imported surface to +Y, scales its measured height, and keeps its
vertex appearance. It does not construct a replacement character from primitives.
The imported open mouth has an actual geometry morph. This version deliberately
does not advertise Blink: a painted, fused eye cannot blink anatomically until
there is a separate conforming eyelid. See the generated manifest's limitations.
"""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import struct
import sys
import time

import bpy
import numpy as np
from mathutils import Vector, Quaternion


def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True, type=Path)
    parser.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output', type=Path)
    parser.add_argument('--source-output', type=Path)
    parser.add_argument('--height', type=float, default=2.75)
    parser.add_argument('--body-center-y', type=float, default=-.13)
    parser.add_argument('--tail-length-scale', type=float, default=1.0,
                        help='Monotone short-tail compression in original source coordinates; 1 keeps source intact')
    parser.add_argument('--config', type=Path)
    parser.add_argument('--preview-output', type=Path)
    parser.add_argument('--skip-previews', action='store_true')
    parser.add_argument('--only-lod0', action='store_true')
    parser.add_argument('--no-force-sampling', action='store_true',
                        help='Opt out of forced animation sampling for an explicitly reviewed candidate; default remains forced')
    parser.add_argument('--lod-ratios', type=float, nargs=3, default=(.45, .12, .035),
                        help='Runtime ratios; full supplied surface remains in the saved source blend')
    parser.add_argument('--face-helper', type=Path,
                        help='Optional local module exposing attach_face(rig, skin, landmarks)')
    return parser.parse_args(sys.argv[sys.argv.index('--') + 1:])


CLIPS = {'idle': 3.2, 'walk': 1.0, 'chase': .68, 'warn': .8, 'charge': .50, 'recover': 2.0}
FPS = 30


def smooth(a, b, value):
    t = np.clip((value - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def mesh_vertices(mesh):
    vertices = np.empty(len(mesh.vertices) * 3, dtype=np.float64)
    mesh.vertices.foreach_get('co', vertices)
    return vertices.reshape((-1, 3))


def triangles(obj):
    return sum(len(poly.vertices) - 2 for poly in obj.data.polygons)


def attach_face(args, rig, obj, landmarks, lod_level=-1):
    if not args.face_helper:
        return {'objects': [], 'animated_objects': [], 'manifest': {'Blink': False}}
    specification = importlib.util.spec_from_file_location('reconstructed_nailong_face', args.face_helper)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    helper_landmarks = dict(landmarks)
    helper_landmarks['_lod_level'] = lod_level
    result = module.attach_face(rig, obj, helper_landmarks)
    if not isinstance(result, dict) or 'objects' not in result:
        raise RuntimeError('Face helper must return a dictionary with explicit objects')
    result.setdefault('animated_objects', [])
    result.setdefault('manifest', {})
    return result


def animation_data_blocks(obj):
    blocks = []
    if obj.animation_data:
        blocks.append(obj.animation_data)
    if obj.type == 'MESH' and obj.data.shape_keys and obj.data.shape_keys.animation_data:
        blocks.append(obj.data.shape_keys.animation_data)
    return blocks


def import_surface(args):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.import_scene.gltf(filepath=str(args.input))
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
    if not meshes:
        raise RuntimeError('Input contains no real mesh')
    bpy.ops.object.select_all(action='DESELECT')
    for obj in meshes:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.join()
    obj = bpy.context.object
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    obj.name = 'NailongSkin_Reconstructed'
    original = mesh_vertices(obj.data)
    if not np.isfinite(original).all():
        raise RuntimeError('Source geometry contains non-finite coordinates')
    source_min, source_max = original.min(axis=0), original.max(axis=0)
    source_height = source_max[2] - source_min[2]
    if source_height <= 0:
        raise RuntimeError('Input has zero measured height')
    scale = args.height / source_height
    vertices = original.copy()
    tail_ratio = args.tail_length_scale
    if not 0 < tail_ratio <= 1:
        raise ValueError('--tail-length-scale must be greater than zero and at most one')
    tail_root, tail_ramp = .09, .08
    tail_mask = vertices[:, 1] > tail_root
    tail_before = vertices[tail_mask].copy()
    if tail_ratio != 1:
        t = vertices[tail_mask, 1] - tail_root
        vertices[tail_mask, 1] = tail_root + tail_ratio * t + (1 - tail_ratio) * tail_ramp * (1 - np.exp(-t / tail_ramp))
    tail_after = vertices[tail_mask].copy()
    vertices[:, 0] *= -scale
    vertices[:, 1] = -(vertices[:, 1] - args.body_center_y) * scale
    vertices[:, 2] = (vertices[:, 2] - source_min[2]) * scale + .008
    obj.data.vertices.foreach_set('co', vertices.ravel())
    for poly in obj.data.polygons:
        poly.use_smooth = True
    obj.data.update()
    tail_tip = vertices[np.argmin(vertices[:, 1])].copy()
    tail_tip[0] = 0
    return obj, {'source_blender_bounds': [source_min.tolist(), source_max.tolist()],
                 'source_body_center_y': args.body_center_y, 'scale': scale,
                 'height_m': args.height, 'ground_clearance_m': .008,
                 'rotation_z_degrees': 180, 'rest_bounds_blender': [vertices.min(axis=0).tolist(), vertices.max(axis=0).tolist()],
                 'tail_compression': {'enabled': tail_ratio != 1, 'length_scale': tail_ratio,
                     'source_root_y': tail_root, 'source_ramp': tail_ramp, 'affected_vertices': int(tail_mask.sum()),
                     'formula': 'root + ratio*t + (1-ratio)*ramp*(1-exp(-t/ramp)); t=source_y-root; only t>0',
                     'derivative_range': [tail_ratio, 1.0], 'source_x_and_z_unchanged': True,
                     'source_tail_bounds_before': [tail_before.min(axis=0).tolist(), tail_before.max(axis=0).tolist()] if len(tail_before) else None,
                     'source_tail_bounds_after': [tail_after.min(axis=0).tolist(), tail_after.max(axis=0).tolist()] if len(tail_after) else None,
                     'measured_tail_tip_blender': tail_tip.tolist()}}


def default_landmarks():
    # Measured against the reconstructed neutral A-pose, not the previous model.
    return {
        'pelvis': [0, -.01, .49], 'spine': [0, -.02, .92],
        'neck': [0, .04, 1.48], 'head': [0, .17, 1.70],
        'head_tip': [0, .17, 2.53], 'mouth': [0, .84, 1.75],
        'shoulder': [.56, -.015, 1.42], 'elbow': [.83, .015, 1.22],
        'wrist': [1.03, .05, 1.15], 'palm_tip': [1.15, .09, 1.09],
        'hip': [.40, -.01, .49], 'knee': [.49, .015, .29],
        'ankle': [.51, .05, .14], 'toe': [.51, .25, .14],
        'tail_start': [0, -.49, .56], 'tail_tip': [0, -1.74, .55],
        'eye': [.36, .80, 2.16],
    }


def make_rig(landmarks):
    data = bpy.data.armatures.new('Reconstructed Nailong anatomical skeleton')
    rig = bpy.data.objects.new('NailongRig', data)
    bpy.context.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.select_all(action='DESELECT')
    rig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    lm = landmarks
    bones = [('root', (0, 0, 0), (0, 0, .23), None),
             ('pelvis', lm['pelvis'], lm['spine'], 'root'),
             ('spine', lm['spine'], lm['neck'], 'pelvis'),
             ('belly', (0, .22, .83), (0, .22, 1.16), 'spine'),
             ('neck', lm['neck'], lm['head'], 'spine'),
             ('head', lm['head'], lm['head_tip'], 'neck'),
             ('jaw', (0, .47, 1.70), (0, .86, 1.62), 'head'),
             ('tail', lm['tail_start'], lm['tail_tip'], 'pelvis')]
    for side, sign in [('left', -1), ('right', 1)]:
        def sided(name):
            x, y, z = lm[name]
            return (sign * x, y, z)
        eye = sided('eye')
        bones.extend([
            ('upper_arm_' + side, sided('shoulder'), sided('elbow'), 'spine'),
            ('forearm_' + side, sided('elbow'), sided('wrist'), 'upper_arm_' + side),
            ('palm_' + side, sided('wrist'), sided('palm_tip'), 'forearm_' + side),
            ('thigh_' + side, sided('hip'), sided('knee'), 'pelvis'),
            ('shin_' + side, sided('knee'), sided('ankle'), 'thigh_' + side),
            ('foot_' + side, sided('ankle'), sided('toe'), 'shin_' + side),
            ('eye_' + side, eye, (eye[0], eye[1], eye[2] + .09), 'head'),
            ('brow_' + side, (eye[0], eye[1], eye[2] + .11), (eye[0], eye[1], eye[2] + .17), 'head'),
        ])
    for name, start, end, parent in bones:
        bone = data.edit_bones.new(name)
        bone.head, bone.tail = start, end
        if parent:
            bone.parent = data.edit_bones[parent]
    bpy.ops.object.mode_set(mode='OBJECT')
    rig.select_set(False)
    for bone in rig.pose.bones:
        bone.rotation_mode = 'QUATERNION'
    return rig, bones


def skin_weights(vertices, names):
    x, y, z = vertices.T
    ax = np.abs(x)
    head = smooth(1.47, 1.77, z)
    arm = smooth(.57, .84, ax) * smooth(.73, 1.00, z) * (1 - smooth(1.43, 1.66, z)) * (1 - head)
    tail = smooth(.44, .80, -y) * (1 - smooth(.82, 1.02, z)) * (1 - head) * (1 - arm)
    # This character's short thighs end below the hanging belly. Giving its
    # lower belly the same leg weights produces a traveling crease across the
    # abdomen even with modest steps. Keep the central/upper underside pelvic.
    leg = smooth(.25, .43, ax) * (1 - smooth(.36, .61, z)) * (1 - head) * (1 - arm) * (1 - tail)
    trunk = np.maximum(0, 1 - head - arm - tail - leg)
    spine = smooth(.62, 1.02, z)
    neck = smooth(1.34, 1.58, z)
    belly = np.clip((y - .06) * .30, 0, .18) * (1 - smooth(1.26, 1.46, z)) * spine
    forearm = smooth(.76, 1.00, ax)
    palm = smooth(.97, 1.12, ax)
    foot = 1 - smooth(.18, .30, z)
    shin = smooth(.18, .30, z) * (1 - smooth(.30, .47, z))
    thigh = np.maximum(0, 1 - foot - shin)
    weights = np.zeros((len(vertices), len(names)), dtype=np.float32)
    base = {'head': head, 'neck': trunk * neck, 'pelvis': trunk * (1 - spine) * (1 - neck),
            'spine': trunk * (spine - belly) * (1 - neck), 'belly': trunk * belly * (1 - neck), 'tail': tail}
    for side, mask in [('left', x < 0), ('right', x >= 0)]:
        base.update({
            'upper_arm_' + side: arm * (1 - forearm) * mask,
            'forearm_' + side: arm * forearm * (1 - palm) * mask,
            'palm_' + side: arm * forearm * palm * mask,
            'thigh_' + side: leg * thigh * mask,
            'shin_' + side: leg * shin * mask,
            'foot_' + side: leg * foot * mask,
        })
    for name, value in base.items():
        weights[:, names.index(name)] = value
    # Match native glTF's four-influence path, not Blender-only extra weights.
    strongest = np.argpartition(weights, -4, axis=1)[:, -4:]
    result = np.zeros_like(weights)
    rows = np.arange(len(vertices))[:, None]
    result[rows, strongest] = weights[rows, strongest]
    result /= np.maximum(result.sum(axis=1, keepdims=True), 1e-12)
    assert np.all(np.isfinite(result)) and np.max(np.abs(result.sum(axis=1) - 1)) < 1e-5
    return result


def bind(obj, rig):
    names = list(rig.data.bones.keys())
    vertices = mesh_vertices(obj.data)
    weights = skin_weights(vertices, names)
    for column, name in enumerate(names):
        group = obj.vertex_groups.new(name=name)
        # Quantization permits bulk assignments and is normalized by the exporter.
        quantized = np.rint(weights[:, column] * 4096).astype(np.int32)
        indices = np.flatnonzero(quantized)
        ordered = indices[np.argsort(quantized[indices], kind='stable')]
        values, starts = np.unique(quantized[ordered], return_index=True)
        for value, members in zip(values, np.split(ordered, starts[1:])):
            group.add(members.tolist(), float(value) / 4096, 'REPLACE')
    modifier = obj.modifiers.new('Independent native skeleton', 'ARMATURE')
    modifier.object = rig
    modifier.use_deform_preserve_volume = False  # The exported runtime uses linear blend skinning.
    obj.parent = rig
    return weights


def add_facial_morphs(obj, landmarks):
    vertices = mesh_vertices(obj.data)
    obj.shape_key_add(name='Basis')
    mouth = np.array(landmarks['mouth'])
    x, y, z = vertices.T
    region = np.exp(-((x - mouth[0]) / .285) ** 4) * np.exp(-((z - mouth[2]) / .255) ** 6) * smooth(.58, .78, y)
    opened = vertices.copy()
    lower = (1 - smooth(mouth[2] - .045, mouth[2] + .015, z))
    upper = smooth(mouth[2] + .015, mouth[2] + .105, z)
    opened[:, 2] += region * (-.105 * lower + .024 * upper)
    opened[:, 1] += region * .012 * lower
    key = obj.shape_key_add(name='Open')
    key.data.foreach_set('co', opened.ravel())
    # Eyeballs/painted iris stay rigid. Only forehead skin above them moves.
    focus = vertices.copy()
    for sign in [-1, 1]:
        eye = np.array(landmarks['eye']) * np.array([sign, 1, 1])
        brow = np.exp(-((x - eye[0]) / .20) ** 4) * np.exp(-((z - (eye[2] + .165)) / .070) ** 4) * smooth(.58, .74, y)
        focus[:, 2] -= .038 * brow
        focus[:, 1] += .006 * brow
    key = obj.shape_key_add(name='Focus')
    key.data.foreach_set('co', focus.ravel())
    return {'Open': float(np.max(np.linalg.norm(opened - vertices, axis=1))),
            'Focus': float(np.max(np.linalg.norm(focus - vertices, axis=1))),
            'Blink': None, 'eyeball_squashing': False}


def rotate_world(bone, axis, angle):
    local_axis = bone.bone.matrix_local.to_3x3().inverted() @ Vector(axis)
    bone.rotation_quaternion = Quaternion(local_axis.normalized(), angle)


def pose_frame(rig, clip, fraction):
    phase = math.tau * fraction
    for bone in rig.pose.bones:
        bone.location = (0, 0, 0)
        bone.rotation_quaternion = (1, 0, 0, 0)
        bone.scale = (1, 1, 1)
    bones = rig.pose.bones
    belly_breath = math.sin(phase)
    bones['belly'].scale = (1 + .009 * belly_breath, 1 + .012 * belly_breath, 1 + .009 * belly_breath)
    rotate_world(bones['tail'], (0, 0, 1), .035 * math.sin(phase + .3))
    if clip == 'idle':
        rotate_world(bones['head'], (0, 0, 1), -.011 * math.sin(phase))
        rotate_world(bones['spine'], (0, 0, 1), .009 * math.sin(phase))
    elif clip in ['walk', 'chase', 'charge']:
        amplitude = {'walk': .20, 'chase': .31, 'charge': .39}[clip]
        lean = {'walk': .035, 'chase': .075, 'charge': .115}[clip]
        rotate_world(bones['spine'], (1, 0, 0), -lean)
        rotate_world(bones['head'], (1, 0, 0), lean * .45)
        for side, offset in [('left', 0), ('right', math.pi)]:
            swing = math.sin(phase + offset)
            thigh = amplitude * swing
            shin = -max(0, swing) * amplitude * .65
            rotate_world(bones['thigh_' + side], (1, 0, 0), thigh)
            rotate_world(bones['shin_' + side], (1, 0, 0), shin)
            rotate_world(bones['foot_' + side], (1, 0, 0), -thigh - shin)
            rotate_world(bones['upper_arm_' + side], (1, 0, 0), -.27 * swing)
            rotate_world(bones['forearm_' + side], (1, 0, 0), -.045 - .025 * swing)
    elif clip == 'warn':
        anticipation = math.sin(fraction * math.pi / 2)
        rotate_world(bones['spine'], (1, 0, 0), -.09 * anticipation)
        rotate_world(bones['head'], (1, 0, 0), .055 * anticipation)
        for side, sign in [('left', -1), ('right', 1)]:
            rotate_world(bones['upper_arm_' + side], (0, 1, 0), sign * .08 * anticipation)
            rotate_world(bones['forearm_' + side], (1, 0, 0), -.12 * anticipation)
            # The short reconstructed legs cannot support a humanoid deep squat
            # without folding the lower belly. Warning uses upper-body intent.
    else:
        rotate_world(bones['spine'], (1, 0, 0), -.04)
        rotate_world(bones['head'], (1, 0, 0), .025 + .007 * math.sin(phase))
        bones['belly'].scale = (1 + .017 * belly_breath, 1 + .022 * belly_breath, 1 + .017 * belly_breath)
        for side in ['left', 'right']:
            rotate_world(bones['upper_arm_' + side], (1, 0, 0), -.07)


def deform_vertices(rig, vertices, weights):
    bpy.context.view_layer.update()
    result = np.zeros_like(vertices)
    for column, bone in enumerate(rig.pose.bones):
        indices = np.flatnonzero(weights[:, column] > 1e-7)
        if not len(indices):
            continue
        transform = np.array(bone.matrix @ bone.bone.matrix_local.inverted())
        points = np.einsum('ij,kj->ki', transform[:3, :3], vertices[indices]) + transform[:3, 3]
        result[indices] += points * weights[indices, column, None]
    if not np.isfinite(result).all():
        raise RuntimeError('Skin deformation contains non-finite coordinates')
    return result


def animation_tracks(rig, obj, weights):
    vertices = mesh_vertices(obj.data)
    # Floor measurement uses the actual low foot surface from the source, not old
    # coordinates. Full-pose verification below additionally checks every vertex.
    foot_indices = np.flatnonzero(vertices[:, 2] < .20)
    feet, foot_weights = vertices[foot_indices], weights[foot_indices]
    manifest = {}
    for clip, duration in CLIPS.items():
        rig.animation_data_create()
        for track in rig.animation_data.nla_tracks:
            track.mute = True
        action = bpy.data.actions.new(clip)
        rig.animation_data.action = action
        frame_count = max(2, round(duration * FPS))
        corrections = []
        for frame in range(frame_count + 1):
            pose_frame(rig, clip, frame / frame_count)
            posed = deform_vertices(rig, feet, foot_weights)
            correction = .008 - float(posed[:, 2].min())
            # A small pelvis displacement preserves root/physics authority and
            # moves all child bones together; no ankle-only dislocation.
            bones = rig.pose.bones
            world_offset = Vector((0, 0, correction))
            bones['pelvis'].location = bones['pelvis'].bone.matrix_local.to_3x3().inverted() @ world_offset
            corrections.append(correction)
            for bone in bones:
                bone.keyframe_insert('location', frame=frame + 1)
                bone.keyframe_insert('rotation_quaternion', frame=frame + 1)
                bone.keyframe_insert('scale', frame=frame + 1)
        for curve in action.fcurves:
            for key in curve.keyframe_points:
                key.interpolation = 'LINEAR'
        track = rig.animation_data.nla_tracks.new()
        track.name = clip
        strip = track.strips.new(clip, 1, action)
        strip.name = clip
        rig.animation_data.action = None
        manifest[clip] = {'duration': duration, 'frames': frame_count, 'root_motion': False,
                          'floor_probe_count': len(foot_indices),
                          'pelvis_floor_correction_range_m': [min(corrections), max(corrections)]}
    for track in rig.animation_data.nla_tracks:
        track.mute = False
    return manifest


def facial_tracks(obj):
    keys = obj.data.shape_keys
    keys.animation_data_create()
    for clip, duration in CLIPS.items():
        for track in keys.animation_data.nla_tracks:
            track.mute = True
        action = bpy.data.actions.new(clip + ' / actual surface expression')
        keys.animation_data.action = action
        frame_count = max(2, round(duration * FPS))
        for frame in range(frame_count + 1):
            t = frame / frame_count
            opening = .06 + .025 * math.sin(math.tau * t) if clip == 'idle' else .14 if clip == 'walk' else .28 if clip == 'chase' else .82 * math.sin(t * math.pi / 2) if clip == 'warn' else .48 if clip == 'charge' else .16 + .04 * math.sin(math.tau * t)
            focus = 0 if clip == 'idle' else .12 if clip == 'walk' else .27 if clip == 'chase' else .75 * math.sin(t * math.pi / 2) if clip == 'warn' else .60 if clip == 'charge' else .18
            for name, value in [('Open', opening), ('Focus', focus)]:
                keys.key_blocks[name].value = value
                keys.key_blocks[name].keyframe_insert('value', frame=frame + 1)
        for curve in action.fcurves:
            for key in curve.keyframe_points:
                key.interpolation = 'LINEAR'
        track = keys.animation_data.nla_tracks.new()
        track.name = clip
        strip = track.strips.new(clip, 1, action)
        strip.name = clip
        keys.animation_data.action = None
    for track in keys.animation_data.nla_tracks:
        track.mute = False


def activate_clip(rig, obj, clip, seconds, extra_objects=()):
    for actor in [rig, obj, *extra_objects]:
        for animation in animation_data_blocks(actor):
            for track in animation.nla_tracks:
                track.mute = track.name != clip
    frame = 1 + seconds * FPS
    bpy.context.scene.frame_set(int(frame), subframe=frame - int(frame))
    bpy.context.view_layer.update()


def measured_pose_bounds(rig, obj, extra_objects=()):
    samples = []
    overall_min = np.array([np.inf] * 3)
    overall_max = np.array([-np.inf] * 3)
    for clip, duration in CLIPS.items():
        for fraction in [0, .125, .23, .375, .49, .625, .74, .875, .96, 1]:
            activate_clip(rig, obj, clip, duration * fraction, extra_objects)
            low, high = np.full(3, np.inf), np.full(3, -np.inf)
            for actor in [obj, *extra_objects]:
                if actor.type != 'MESH':
                    continue
                evaluated = actor.evaluated_get(bpy.context.evaluated_depsgraph_get())
                mesh = evaluated.to_mesh()
                matrix = np.array(evaluated.matrix_world)
                local = mesh_vertices(mesh)
                points = np.einsum('ij,kj->ki', matrix[:3, :3], local) + matrix[:3, 3]
                if not np.isfinite(points).all():
                    raise RuntimeError('Evaluated pose contains non-finite coordinates: ' + clip + ' / ' + actor.name)
                low, high = np.minimum(low, points.min(axis=0)), np.maximum(high, points.max(axis=0))
                evaluated.to_mesh_clear()
            overall_min = np.minimum(overall_min, low)
            overall_max = np.maximum(overall_max, high)
            samples.append({'clip': clip, 'fraction': fraction, 'min': low.tolist(), 'max': high.tolist()})
    # glTF maps Blender (x, y, z) -> Godot (x, z, -y).
    godot_min = [overall_min[0] - .08, overall_min[2] - .08, -overall_max[1] - .08]
    godot_max = [overall_max[0] + .08, overall_max[2] + .08, -overall_min[1] + .08]
    return {'sample_count': len(samples), 'all_vertices_measured': True,
            'min_blender': overall_min.tolist(), 'max_blender': overall_max.tolist(),
            'recommended_godot_aabb': {'position': godot_min, 'size': (np.array(godot_max) - godot_min).tolist()},
            'minimum_floor_m': float(overall_min[2]), 'samples': samples}


def export(rig, obj, path, extra_objects=(), force_sampling=True):
    for actor in [rig, obj, *extra_objects]:
        for animation in animation_data_blocks(actor):
            for track in animation.nla_tracks:
                track.mute = False
    bpy.ops.object.select_all(action='DESELECT')
    rig.select_set(True)
    obj.select_set(True)
    for actor in extra_objects:
        actor.select_set(True)
    bpy.context.view_layer.objects.active = rig
    animation_options={'export_animation_mode':'NLA_TRACKS'} if force_sampling else {
        'export_animation_mode':'ACTIONS','export_merge_animation':'NLA_TRACK'}
    bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB', use_selection=True,
        export_yup=True, export_apply=False, export_animations=True, **animation_options,
        export_force_sampling=force_sampling,
        export_nla_strips=True, export_skins=True, export_normals=True, export_tangents=False,
        export_materials='EXPORT', export_cameras=False, export_lights=False)


def audit_export(path):
    """Check actual exported bytes, including all animation/morph/skin floats."""
    blob = path.read_bytes()
    if struct.unpack_from('<4sII', blob) != (b'glTF', 2, len(blob)):
        raise RuntimeError('Invalid GLB header: ' + str(path))
    document, binary, offset = None, None, 12
    while offset < len(blob):
        length, kind = struct.unpack_from('<II', blob, offset)
        chunk = blob[offset + 8:offset + 8 + length]
        if kind == 0x4E4F534A:
            document = json.loads(chunk)
        elif kind == 0x004E4942:
            binary = chunk
        offset += length + 8
    dimensions = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}
    dtypes = {5121: np.uint8, 5123: np.dtype('<u2'), 5125: np.dtype('<u4'), 5126: np.dtype('<f4')}
    values = []
    float_count = 0
    for number, accessor in enumerate(document.get('accessors', [])):
        dtype = np.dtype(dtypes[accessor['componentType']])
        width = dimensions[accessor['type']]
        if 'bufferView' in accessor:
            view = document['bufferViews'][accessor['bufferView']]
            start = view.get('byteOffset', 0) + accessor.get('byteOffset', 0)
            array = np.ndarray((accessor['count'], width), dtype=dtype, buffer=binary,
                               offset=start, strides=(view.get('byteStride', width * dtype.itemsize), dtype.itemsize))
        else:
            array = np.zeros((accessor['count'], width), dtype=dtype)
        if 'sparse' in accessor:
            sparse = accessor['sparse']
            index_spec, value_spec = sparse['indices'], sparse['values']
            index_view = document['bufferViews'][index_spec['bufferView']]
            value_view = document['bufferViews'][value_spec['bufferView']]
            indices = np.frombuffer(binary, dtype=dtypes[index_spec['componentType']], count=sparse['count'],
                                    offset=index_view.get('byteOffset', 0) + index_spec.get('byteOffset', 0))
            replacements = np.frombuffer(binary, dtype=dtype, count=sparse['count'] * width,
                                         offset=value_view.get('byteOffset', 0) + value_spec.get('byteOffset', 0)).reshape((-1, width))
            if len(indices) and (int(indices[-1]) >= len(array) or np.any(indices[1:] <= indices[:-1])):
                raise RuntimeError('Invalid sparse accessor indices: ' + str(number))
            array = array.copy()
            array[indices] = replacements
        if accessor['componentType'] == 5126:
            if not np.isfinite(array).all():
                raise RuntimeError('Non-finite values in exported accessor %d' % number)
            float_count += array.size
        values.append(array)
    export_triangles = 0
    export_vertices = 0
    color_attributes = []
    for mesh in document['meshes']:
        for primitive in mesh['primitives']:
            attrs = primitive['attributes']
            export_vertices += len(values[attrs['POSITION']])
            if 'WEIGHTS_0' in attrs:
                weight = values[attrs['WEIGHTS_0']]
                if np.min(weight) < 0 or np.max(np.abs(weight.sum(axis=1) - 1)) > 1e-4:
                    raise RuntimeError('Exported skin weights are not normalized')
            if 'COLOR_0' in attrs:
                color = values[attrs['COLOR_0']]
                color_attributes.append({'type': document['accessors'][attrs['COLOR_0']]['componentType'],
                                         'min': float(color.min()), 'max': float(color.max())})
            export_triangles += len(values[primitive['indices']]) // 3
    clips = [animation['name'] for animation in document.get('animations', [])]
    if sorted(clips) != sorted(CLIPS):
        raise RuntimeError('Exported native clips differ from the required six: ' + repr(clips))
    joint_counts = [len(skin['joints']) for skin in document.get('skins', [])]
    if not joint_counts or any(count != 24 for count in joint_counts):
        raise RuntimeError('Exported skin lost its 24-bone skeleton: ' + repr(joint_counts))
    return {'float_accessor_values_checked': int(float_count), 'all_float_accessors_finite': True,
            'native_animation_names': clips, 'joint_counts': joint_counts,
            'triangles': export_triangles, 'exported_vertices': export_vertices,
            'mesh_count': len(document['meshes']), 'color_attributes': color_attributes,
            'sha256': hashlib.sha256(blob).hexdigest(), 'bytes': len(blob)}


def previews(rig, obj, output, bounds, extra_objects=()):
    output.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 16
    scene.cycles.use_denoising = True
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = 4
    scene.render.resolution_x = 768
    scene.render.resolution_y = 768
    scene.render.resolution_percentage = 100
    scene.world = bpy.data.worlds.new('Inspection studio')
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.10, .12, .14, 1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value = .45
    scene.view_settings.view_transform = 'AgX'
    center = Vector((0, -.18, 1.39))
    for name, offset, power, size in [('Key', (-3, 4, 5), 1150, 4), ('Fill', (4, 3, 2), 680, 4), ('Rim', (1, -4, 4), 900, 3)]:
        light = bpy.data.lights.new(name, 'AREA')
        light.energy, light.shape, light.size = power, 'DISK', size
        actor = bpy.data.objects.new(name, light)
        scene.collection.objects.link(actor)
        actor.location = center + Vector(offset)
        actor.rotation_euler = (center - actor.location).to_track_quat('-Z', 'Y').to_euler()
    camera_data = bpy.data.cameras.new('Actual mesh and actual rig inspection')
    camera_data.type, camera_data.ortho_scale = 'ORTHO', 3.5
    camera = bpy.data.objects.new('Inspection camera', camera_data)
    scene.collection.objects.link(camera)
    scene.camera = camera
    shots = [(clip, seconds, degrees, clip + '-%03d.png' % degrees) for clip, seconds, degrees in [('idle', 0, 0), ('idle', 0, 45), ('idle', 0, 90), ('walk', .23, 0), ('chase', .16, 45), ('warn', .75, 0), ('charge', .125, 45), ('recover', .45, 0)]]
    if any('Eyelid' in actor.name for actor in extra_objects):
        shots += [('idle', 1.792, 0, 'idle-blink-front.png'), ('idle', 1.792, 45, 'idle-blink-three-quarter.png'),
                  ('idle', 1.76, 0, 'idle-blink-middle-front.png'), ('idle', 1.76, 45, 'idle-blink-middle-three-quarter.png')]
    for clip, seconds, degrees, filename in shots:
        activate_clip(rig, obj, clip, seconds, extra_objects)
        angle = math.radians(degrees)
        camera.location = center + Vector((math.sin(angle) * 6, math.cos(angle) * 6, .50))
        camera.rotation_euler = (center - camera.location).to_track_quat('-Z', 'Y').to_euler()
        scene.render.filepath = str(output / filename)
        bpy.ops.render.render(write_still=True)


def main():
    started = time.monotonic()
    args = arguments()
    output = args.output or args.repo / 'assets/refined/nailong/reconstructed_candidate'
    source_output = args.source_output or args.repo / 'source_assets/nailong/reconstructed_candidate'
    output.mkdir(parents=True, exist_ok=True)
    source_output.mkdir(parents=True, exist_ok=True)
    (source_output / '.gdignore').touch()
    obj, transform = import_surface(args)
    neutral_mesh = obj.data.copy()
    landmarks = default_landmarks()
    if args.tail_length_scale != 1:
        landmarks['tail_tip'] = transform['tail_compression']['measured_tail_tip_blender']
    if args.config:
        landmarks.update(json.loads(args.config.read_text()).get('landmarks', {}))
    rig, bones = make_rig(landmarks)
    bpy.context.scene.render.fps = FPS
    weights = bind(obj, rig)
    facial = add_facial_morphs(obj, landmarks)
    clips = animation_tracks(rig, obj, weights)
    facial_tracks(obj)
    face = attach_face(args, rig, obj, landmarks)
    source_face_manifest = dict(face['manifest'])
    bounds = measured_pose_bounds(rig, obj, face['objects'])
    if bounds['minimum_floor_m'] < -.015:
        raise RuntimeError('Actual posed surface penetrates the floor: ' + str(bounds['minimum_floor_m']))
    activate_clip(rig, obj, 'idle', 0, face['objects'])
    bpy.ops.wm.save_as_mainfile(filepath=str(source_output / 'nailong_reconstructed_rig.blend'), compress=True)
    lods = []
    source_triangles, source_vertices = triangles(obj), len(obj.data.vertices)
    source_total_triangles = source_triangles + sum(triangles(actor) for actor in face['objects'] if actor.type == 'MESH')
    for level, ratio in enumerate(args.lod_ratios):
        if level and args.only_lod0:
            break
        if level or ratio != 1:
            for actor in face['objects']:
                bpy.data.objects.remove(actor, do_unlink=True)
            for group in list(obj.vertex_groups):
                obj.vertex_groups.remove(group)
            for mod in list(obj.modifiers):
                obj.modifiers.remove(mod)
            obj.data = neutral_mesh.copy()
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            mod = obj.modifiers.new('Explicit distance surface simplification', 'DECIMATE')
            mod.ratio = ratio
            bpy.ops.object.modifier_apply(modifier=mod.name)
            bind(obj, rig)
            add_facial_morphs(obj, landmarks)
            facial_tracks(obj)
            face = attach_face(args, rig, obj, landmarks, level)
        filename = 'nailong_lod%d.glb' % level
        lod_bounds = measured_pose_bounds(rig, obj, face['objects'])
        if lod_bounds['minimum_floor_m'] < -.015:
            raise RuntimeError('LOD %d penetrates floor' % level)
        export(rig, obj, output / filename, face['objects'], force_sampling=not args.no_force_sampling)
        actual_export = audit_export(output / filename)
        lods.append({'level': level, 'file': filename, 'vertices': len(obj.data.vertices),
                     'triangles': actual_export['triangles'], 'body_triangles': triangles(obj), 'source_ratio': ratio,
                     'pose_bounds': lod_bounds,
                     'face_helper': face['manifest'], 'export_audit': actual_export, 'sha256': actual_export['sha256']})
        print('EXPORTED_VERIFIED_LOD ' + json.dumps({'level': level, 'triangles': triangles(obj), 'minimum_floor_m': lod_bounds['minimum_floor_m'], 'all_float_accessors_finite': True}), flush=True)
    manifest = {'generator': 'tools/bind_reconstructed_nailong.py', 'blender': bpy.app.version_string,
        'source': str(args.input), 'source_sha256': hashlib.sha256(args.input.read_bytes()).hexdigest(),
        'source_geometry_replaced': False, 'candidate_only': True,
        'not_visual_acceptance': True, 'coordinate_system': 'Godot Y-up, -Z-facing',
        'transform': transform, 'landmarks_blender': landmarks, 'bones': len(bones),
        'bone_names': [b[0] for b in bones], 'clips': clips, 'facial_morphs': facial,
        'source_triangles': source_triangles, 'source_vertices': source_vertices, 'source_total_triangles': source_total_triangles,
        'lods': lods, 'pose_bounds': bounds, 'face_helper': source_face_manifest,
        'limitations': ([] if face['manifest'].get('Blink') else ['Blink has not been authored. Eyes are fused into the colored reconstructed surface; squeezing them would be anatomically wrong.',
                        'Eye and brow named bones reserve the runtime contract but fused eyes currently follow head skin weights.',
                       ]) + ['No claim of final commercial art acceptance; preview and in-engine integration still require review.'],
        'elapsed_seconds_before_previews': time.monotonic() - started}
    (output / 'MODEL_MANIFEST.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    (source_output / 'RIG_BINDING.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    if not args.skip_previews:
        bpy.ops.wm.open_mainfile(filepath=str(source_output / 'nailong_reconstructed_rig.blend'))
        rig = bpy.data.objects['NailongRig']
        obj = bpy.data.objects['NailongSkin_Reconstructed']
        extra_objects = [actor for actor in bpy.context.scene.objects if actor.type == 'MESH' and actor != obj]
        previews(rig, obj, args.preview_output or output / 'previews', bounds, extra_objects)
    print('RECONSTRUCTED_NAILONG_RIG_CANDIDATE ' + json.dumps({'lods': [{k: lod[k] for k in ['level', 'file', 'triangles', 'vertices', 'sha256']} for lod in lods], 'bones': len(bones), 'clips': list(clips), 'minimum_floor_m': bounds['minimum_floor_m'], 'elapsed_seconds': time.monotonic() - started}))


if __name__ == '__main__':
    main()
