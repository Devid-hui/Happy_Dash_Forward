"""Read-only CPU Blender audit of the saved single-eye shared-edge prototype."""
import bpy
import hashlib
import json
import math
import traceback
from pathlib import Path
import numpy as np
from mathutils.bvhtree import BVHTree

ROOT = Path(__file__).resolve().parent
WORK = ROOT.parents[1] / 'work/nailong/face-topology-v5'
PROTO = WORK / 'source-single-eye-cdt-corner-fixed.blend'
BASELINE = WORK / 'source-v3-stable.blend'
REPORT = {'status': 'started', 'cpu_only': True, 'rendered': False,
          'graph_evidence': 'Parent Verify generation 2026-10-13T01:14:30Z ready 1651/4337; new directory outside_project; explicit source fallback.',
          'prototype': str(PROTO), 'baseline': str(BASELINE), 'prototype_stage': 'cdt-corner-fixed'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def get_coords(data):
    points = data.data if hasattr(data, 'data') else data.vertices
    out = np.empty(len(points) * 3, dtype=np.float32)
    points.foreach_get('co', out)
    return out.reshape(-1, 3).astype(np.float64)


def get_normals(mesh):
    out = np.empty(len(mesh.loops) * 3, dtype=np.float32)
    mesh.corner_normals.foreach_get('vector', out)
    return out.reshape(-1, 3).astype(np.float64)


def unit(a):
    return a / np.maximum(np.linalg.norm(a, axis=-1, keepdims=True), 1e-30)


def angle(a, b):
    return np.degrees(np.arccos(np.clip(np.sum(unit(a) * unit(b), axis=-1), -1, 1)))


def summary(a):
    a = np.asarray(a)
    if not len(a): return {'count': 0}
    return {'count': len(a), 'min': float(a.min()), 'median': float(np.median(a)),
            'p95': float(np.percentile(a, 95)), 'max': float(a.max())}


def point_ids(mesh):
    attr = mesh.attributes.get('OriginalSourceVertexID')
    if attr is None: raise RuntimeError('Actual prototype has no OriginalSourceVertexID attribute')
    out = np.empty(len(mesh.vertices), dtype=np.int32)
    attr.data.foreach_get('value', out)
    return out


def loop_ids(mesh):
    out = np.empty(len(mesh.loops), dtype=np.int32)
    mesh.loops.foreach_get('vertex_index', out)
    return out


def cross2(a, b):
    return a[..., 0] * b[..., 1] - a[..., 1] * b[..., 0]


def proper_crossing(a, b, c, d):
    return (cross2(b - a, c - a) * cross2(b - a, d - a) < -1e-20) & (cross2(d - c, a - c) * cross2(d - c, b - c) < -1e-20)


def strict_non_neighbor_intersections(points, triangles, polygon_ids):
    """Actual 3D strict penetrations; shared-vertex neighbors and touch excluded.

    AABB candidates are refined with segment/plane and barycentric tests.
    Coplanar overlaps use projected proper edge crossings/strict point-inside.
    This is scoped to the local Face mesh, not other character objects.
    """
    tolerance = 1e-8
    # Blender BVHTree.overlap omits coplanar containment (verified by the
    # reference case), so use an explicit sweep of bounding-box intervals.
    tp = points[triangles]
    minimum = tp.min(axis=1) - tolerance
    maximum = tp.max(axis=1) + tolerance
    axis = int(np.argmax(np.ptp((minimum + maximum) * .5, axis=0) / np.maximum(np.mean(maximum - minimum, axis=0), 1e-12)))
    order = np.argsort(minimum[:, axis])
    start = minimum[order, axis]
    upper = np.searchsorted(start, maximum[order, axis], side='right')
    length = np.maximum(0, upper - np.arange(len(order)) - 1)
    total = int(length.sum())
    if not total: return {'strict_non_neighbor_triangle_pairs': 0, 'candidate_pairs': 0, 'first_pairs': []}
    row = np.repeat(np.arange(len(order), dtype=np.int32), length)
    col = np.arange(total, dtype=np.int64) - np.repeat(np.cumsum(length) - length, length) + row + 1
    first, second = order[row], order[col]
    intersects = np.all((minimum[first] <= maximum[second]) & (minimum[second] <= maximum[first]), axis=1)
    pairs = np.stack((first[intersects], second[intersects]), axis=1)
    del row, col, first, second, intersects
    if not len(pairs): return {'strict_non_neighbor_triangle_pairs': 0, 'candidate_pairs': 0, 'first_pairs': []}
    ia, ib = triangles[pairs[:, 0]], triangles[pairs[:, 1]]
    shared = np.any(ia[:, :, None] == ib[:, None, :], axis=(1, 2))
    pairs = pairs[~shared]
    if not len(pairs): return {'strict_non_neighbor_triangle_pairs': 0, 'candidate_pairs': 0, 'first_pairs': []}
    aa, bb = points[triangles[pairs[:, 0]]], points[triangles[pairs[:, 1]]]
    na = unit(np.cross(aa[:, 1] - aa[:, 0], aa[:, 2] - aa[:, 0]))
    nb = unit(np.cross(bb[:, 1] - bb[:, 0], bb[:, 2] - bb[:, 0]))
    da = np.sum((aa - bb[:, 0, None, :]) * nb[:, None, :], axis=2)
    db = np.sum((bb - aa[:, 0, None, :]) * na[:, None, :], axis=2)
    transverse = (da.min(axis=1) < -tolerance) & (da.max(axis=1) > tolerance) & (db.min(axis=1) < -tolerance) & (db.max(axis=1) > tolerance)
    coplanar = (np.abs(da).max(axis=1) < tolerance) & (np.abs(db).max(axis=1) < tolerance)
    hit = np.zeros(len(pairs), dtype=bool)
    # Both orientations catch an intersection segment whose endpoint lies on
    # one triangle edge and strictly inside the other triangle.
    for first, second, distances in [(aa, bb, da), (bb, aa, db)]:
        v0 = second[:, 1] - second[:, 0]
        v1 = second[:, 2] - second[:, 0]
        d00 = np.sum(v0 * v0, axis=1); d01 = np.sum(v0 * v1, axis=1); d11 = np.sum(v1 * v1, axis=1)
        denominator = d00 * d11 - d01 * d01
        for corner in range(3):
            nxt = (corner + 1) % 3
            crosses = transverse & (distances[:, corner] * distances[:, nxt] < -tolerance ** 2)
            ratio = distances[:, corner] / np.where(np.abs(distances[:, corner] - distances[:, nxt]) > 1e-30, distances[:, corner] - distances[:, nxt], 1)
            point = first[:, corner] + ratio[:, None] * (first[:, nxt] - first[:, corner])
            v2 = point - second[:, 0]
            d20 = np.sum(v2 * v0, axis=1); d21 = np.sum(v2 * v1, axis=1)
            safe = np.where(np.abs(denominator) > 1e-30, denominator, 1)
            u = (d11 * d20 - d01 * d21) / safe
            v = (d00 * d21 - d01 * d20) / safe
            hit |= crosses & (u > 1e-7) & (v > 1e-7) & (u + v < 1 - 1e-7)
    for axis in range(3):
        ids = np.flatnonzero(coplanar & (np.argmax(np.abs(na), axis=1) == axis))
        if not len(ids): continue
        axes = [i for i in range(3) if i != axis]
        ap = aa[ids][:, :, axes]; bp = bb[ids][:, :, axes]
        coplanar_hit = np.zeros(len(ids), dtype=bool)
        for ai in range(3):
            for bi in range(3):
                coplanar_hit |= proper_crossing(ap[:, ai], ap[:, (ai + 1) % 3], bp[:, bi], bp[:, (bi + 1) % 3])
        def inside(vertices, other):
            orientation = cross2(other[:, 1] - other[:, 0], other[:, 2] - other[:, 0])
            found = np.zeros(len(vertices), dtype=bool)
            for vertex in range(3):
                signs = np.stack([cross2(other[:, (edge + 1) % 3] - other[:, edge], vertices[:, vertex] - other[:, edge]) for edge in range(3)], axis=1)
                found |= np.all(signs * np.sign(orientation)[:, None] > 1e-14, axis=1)
            return found
        coplanar_hit |= inside(ap, bp) | inside(bp, ap)
        distances = np.linalg.norm(aa[ids][:, :, None, :] - bb[ids][:, None, :, :], axis=3)
        duplicate_area = np.all(distances.min(axis=2) < tolerance, axis=1)
        coplanar_hit |= duplicate_area
        hit[ids] |= coplanar_hit
    selected = pairs[hit]
    return {'candidate_pairs': len(pairs), 'strict_non_neighbor_triangle_pairs': len(selected),
            'first_pairs': [{'triangle_indices': [int(a), int(b)], 'polygon_ids': [int(polygon_ids[a]), int(polygon_ids[b])],
                             'local_vertex_ids': [triangles[a].tolist(), triangles[b].tolist()]} for a, b in selected[:20]]}


from mathutils import Vector
import time

SOURCE = WORK / 'source-dual-eye-joint-candidate.blend'
SOURCE_EXPECTED = '56f36c9b1042e4f6788f791c713d69433296597d7a44c69ca7a41efee2cd2691'
REPORT = {'status': 'started', 'CPU_only': True, 'rendered': False,
          'graph_evidence': 'Supported CLI 0.11 Verify: happy-dash-forward-audit-20261012 ready 1654/4342 generation 2026-10-13T01:19:59Z. Both exact helper paths and V5 scope outside_project/unavailable; both complete helper sources read.',
          'source': str(SOURCE), 'coverage': {'quick_grid_requested_per_eye': 121, 'full_joint_requested_per_eye': 2121, 'full_joint_evaluated_per_eye': 0}, 'eyes': {}}


def key_name(b, f):
    if b == 0 and f == 0: return 'Basis'
    if b == 10 and f == 0: return 'Blink'
    if b == 0 and f == 10: return 'Focus'
    return 'LidB%03dF%03d' % (b * 10, f * 10)


def float_coordinates(key):
    values = np.empty(len(key.data) * 3, dtype=np.float32)
    key.data.foreach_get('co', values)
    return values.reshape(-1, 3)


def mesh_signature(mesh):
    points = np.empty(len(mesh.vertices) * 3, dtype=np.float32); mesh.vertices.foreach_get('co', points)
    loops = loop_ids(mesh)
    totals = np.empty(len(mesh.polygons), dtype=np.int32); mesh.polygons.foreach_get('loop_total', totals)
    return {'vertices': len(mesh.vertices), 'polygons': len(mesh.polygons), 'coordinate_sha256': hashlib.sha256(points.tobytes()).hexdigest(),
            'loop_sha256': hashlib.sha256(loops.tobytes()).hexdigest(), 'polygon_total_sha256': hashlib.sha256(totals.tobytes()).hexdigest()}


def world_points(obj, mesh):
    points = get_coords(mesh)
    matrix = np.asarray(obj.matrix_world, dtype=np.float64)
    return points @ matrix[:3, :3].T + matrix[:3, 3]


def transform_normals(obj, values):
    return unit(values @ np.linalg.inv(np.asarray(obj.matrix_world, dtype=np.float64)[:3, :3]))


def read_faces(mesh):
    return [np.array(p.vertices, dtype=np.int64) for p in mesh.polygons]


def topology(obj, original_faces, source_points, frame):
    mesh = obj.data; faces = read_faces(mesh); source_ids = point_ids(mesh); c = np.asarray(frame['center'])
    candidates = np.flatnonzero(np.all(np.isin(original_faces, source_ids[source_ids >= 0]), axis=1))
    center = source_points[original_faces[candidates]].mean(axis=1); dz = center[:, 2] - c[2]
    q = ((center[:, 0] - c[0]) / .20) ** 2 + (dz / np.where(dz >= 0, .185, .165)) ** 2
    lookup = {tuple(sorted(original_faces[i].tolist())) for i in candidates[q >= 1]}
    ann = {i for i, f in enumerate(faces) if len(f) == 3 and np.all(source_ids[f] >= 0) and tuple(sorted(source_ids[f].tolist())) in lookup}
    initial_cdt = {i for i, f in enumerate(faces) if len(f) == 3 and i not in ann and np.any(source_ids[f] >= 0)}
    regular = {int(v) for i in initial_cdt for v in faces[i] if source_ids[v] < 0}
    radial = {i for i, f in enumerate(faces) if len(f) == 4 or len(f) == 3 and np.all(source_ids[f] < 0) and all(int(v) not in regular for v in f)}
    cdt = set(range(len(faces))) - ann - radial
    edge_faces = {}; directions = {}
    for p, face in enumerate(faces):
        for a, b in zip(face, np.roll(face, -1)):
            edge = tuple(sorted((int(a), int(b)))); edge_faces.setdefault(edge, []).append(p); directions.setdefault(edge, []).append((int(a), int(b)))
    first = {e for e, pp in edge_faces.items() if len(pp) == 2 and any(p in ann for p in pp) and any(p in cdt for p in pp)}
    second = {e for e, pp in edge_faces.items() if len(pp) == 2 and any(p in cdt for p in pp) and any(p in radial for p in pp)}
    outer = {e for e, pp in edge_faces.items() if len(pp) == 1 and np.all(source_ids[list(e)] >= 0)}
    outer_vertices = sorted({v for e in outer for v in e})
    neighbors = sorted({v for e in edge_faces if any(x in outer_vertices for x in e) for v in e if v not in outer_vertices})
    expected = {key_name(b, f) for b in range(11) for f in range(11)} | {'Open'}
    actual = {k.name for k in mesh.shape_keys.key_blocks}
    report = {'vertices': len(mesh.vertices), 'polygons': len(faces), 'source_annular_vertices': int(np.count_nonzero(source_ids >= 0)),
              'ANN_triangles': len(ann), 'CDT_triangles': len(cdt), 'radial_polygons': len(radial), 'regular_vertices': len(regular),
              'ANN_CDT_actual_shared_edges': len(first), 'CDT_radial_actual_shared_edges': len(second),
              'both_common_edge_incidence_exactly_two': all(len(edge_faces[e]) == 2 for e in first | second),
              'both_common_edge_winding_opposite': all(directions[e][0] != directions[e][1] for e in first | second),
              'outer_boundary_edges': len(outer), 'outer_vertices': len(outer_vertices), 'outer_one_ring_neighbors': len(neighbors),
              'nonmanifold_edge_count': sum(len(pp) > 2 for pp in edge_faces.values()), 'joint_grid_key_names_exact': expected == actual,
              'joint_grid_states': 121, 'key_count_including_Open': len(actual), 'missing_keys': sorted(expected - actual), 'unexpected_keys': sorted(actual - expected)}
    if len(regular) != 128 or not report['joint_grid_key_names_exact']: raise RuntimeError('Actual regular ring/key schema differs')
    return report, {'faces': faces, 'source_ids': source_ids, 'ann': ann, 'cdt': cdt, 'radial': radial, 'outer': outer,
                    'outer_vertices': outer_vertices, 'neighbors': neighbors, 'edge_faces': edge_faces}


def target_tree(obj):
    mesh = obj.data; mesh.calc_loop_triangles(); points = world_points(obj, mesh)
    tri = np.array([t.vertices[:] for t in mesh.loop_triangles], dtype=np.int64)
    return {'object': obj.name, 'tree': BVHTree.FromPolygons(points.tolist(), tri.tolist(), all_triangles=True),
            'minimum': points.min(axis=0), 'maximum': points.max(axis=0), 'triangles': tri}


def sample_clearance(points, triangles, polygon_ids, target):
    # Every actual vertex, every actual triangle centroid, and all three edge
    # midpoints are sampled. Exact actual-mesh ray hits, then exact nearest
    # point at the minimum-front-gap sample; no analytic replacement sphere.
    xyz = points[triangles]
    samples = np.concatenate([points, xyz.mean(axis=1), (xyz[:, 0] + xyz[:, 1]) * .5,
                              (xyz[:, 1] + xyz[:, 2]) * .5, (xyz[:, 2] + xyz[:, 0]) * .5])
    candidate = np.flatnonzero((samples[:, 0] >= target['minimum'][0] - 1e-8) & (samples[:, 0] <= target['maximum'][0] + 1e-8)
                              & (samples[:, 2] >= target['minimum'][2] - 1e-8) & (samples[:, 2] <= target['maximum'][2] + 1e-8))
    best = None; hits = 0; below = 0; minima_by_type = {}
    source_tri_count = len(triangles)
    for sample_index in candidate:
        point = samples[sample_index]
        hit, normal, target_triangle, distance = target['tree'].ray_cast(Vector((float(point[0]), 3, float(point[2]))), Vector((0, -1, 0)), 5)
        if hit is None: continue
        gap = float(point[1] - hit.y); hits += 1; below += int(gap < -1e-8)
        if sample_index < len(points):
            kind = 'vertex'; primitive_index = int(sample_index); poly = None; source_vertices = [int(sample_index)]
        else:
            block, primitive_index = divmod(int(sample_index) - len(points), source_tri_count)
            kind = ['triangle_centroid', 'edge_midpoint_01', 'edge_midpoint_12', 'edge_midpoint_20'][block]
            poly = int(polygon_ids[primitive_index])
            source_vertices = triangles[primitive_index].tolist() if block == 0 else triangles[primitive_index][[[0, 1], [1, 2], [2, 0]][block - 1]].tolist()
        minima_by_type[kind] = min(minima_by_type.get(kind, math.inf), gap)
        if best is None or gap < best['front_Y_gap_m']:
            nearest, nearest_normal, nearest_triangle, nearest_distance = target['tree'].find_nearest(Vector(tuple(point)))
            best = {'front_Y_gap_m': gap, 'sample_type': kind, 'sample_index': int(sample_index), 'polygon_id': poly,
                    'source_vertex_ids': source_vertices, 'sample_xyz_m': point.tolist(), 'actual_target_hit_xyz_m': list(hit),
                    'target_triangle_index': int(target_triangle), 'exact_nearest_distance_at_this_sample_m': float(nearest_distance),
                    'signed_nearest_distance_at_this_sample_m': float(nearest_distance) * (-1 if gap < 0 else 1)}
    if best is not None and best['sample_type'] == 'vertex':
        vertex = best['source_vertex_ids'][0]
        best['incident_actual_polygon_ids'] = sorted(set(polygon_ids[np.any(triangles == vertex, axis=1)].tolist()))
    return {'sample_count_total': len(samples), 'actual_front_ray_hits': hits, 'below_actual_front_sample_count_at_1e_minus_8_m': below,
            'minimum_front_Y_gap_by_sample_type_m': minima_by_type, 'worst_front_sample': best,
            'nearest_distance_scope': 'Exact nearest distance is at the actual minimum front-Y-gap sample; full all-sample Euclidean minimum is not claimed.'}


def body_boundary_pairs(body, patch, topo):
    body_loops = loop_ids(body.data); body_faces = body_loops.reshape(-1, 3); source_ids = topo['source_ids']
    boundary_source_ids = source_ids[topo['outer_vertices']]
    near = np.flatnonzero(np.any(np.isin(body_faces, boundary_source_ids), axis=1)); matches = {}
    target_edges = {tuple(sorted((int(source_ids[a]), int(source_ids[b])))): (a, b, topo['edge_faces'][(a, b)][0]) for a, b in topo['outer']}
    for polygon in near:
        f = body_faces[polygon]
        for corner in range(3):
            edge = tuple(sorted((int(f[corner]), int(f[(corner + 1) % 3]))))
            if edge in target_edges:
                matches[edge] = (int(polygon), f)
    pairs = []
    for edge, (a, b, patch_polygon) in target_edges.items():
        if edge not in matches: raise RuntimeError('Retained Body does not share an actual boundary source edge')
        body_polygon, bf = matches[edge]; pf = topo['faces'][patch_polygon]
        for vertex in [a, b]:
            sid = int(source_ids[vertex]); body_corner = int(np.flatnonzero(bf == sid)[0]); local_corner = int(np.flatnonzero(pf == vertex)[0])
            pairs.append((vertex, sid, int(patch.data.polygons[patch_polygon].loop_start + local_corner), body_polygon * 3 + body_corner))
    return np.asarray(pairs, dtype=np.int64)


def main():
    started = time.time(); bpy.ops.wm.open_mainfile(filepath=str(SOURCE), load_ui=False)
    REPORT['source_sha256_before'] = sha(SOURCE)
    if REPORT['source_sha256_before'] != SOURCE_EXPECTED: raise RuntimeError('Dual source identity differs')
    body = bpy.data.objects['NailongSkin_Reconstructed']; patches = {s: bpy.data.objects['SharedEyelidFace_' + s] for s in ['left', 'right']}
    ocular_names = ['Reconstructed' + kind + '_' + side for side in ['left', 'right'] for kind in ['Sclera', 'Iris', 'Pupil', 'Corneal']]
    with bpy.data.libraries.load(str(BASELINE), link=False) as (available, loaded): loaded.objects = ['NailongSkin_Reconstructed'] + ocular_names
    refs = dict(zip(['NailongSkin_Reconstructed'] + ocular_names, loaded.objects)); original = refs['NailongSkin_Reconstructed']
    original_faces = loop_ids(original.data).reshape(-1, 3); source_points = float_coordinates(original.data.shape_keys.key_blocks['Basis']).astype(np.float64)
    REPORT['ocular_mesh_bitwise_preserved'] = {name: mesh_signature(bpy.data.objects[name].data) == mesh_signature(refs[name].data) for name in ocular_names}
    if not all(REPORT['ocular_mesh_bitwise_preserved'].values()): raise RuntimeError('An original ocular mesh changed')
    REPORT['body_shape_keys_bitwise_preserved'] = {key.name: bool(np.array_equal(float_coordinates(key).view(np.uint32), float_coordinates(original.data.shape_keys.key_blocks[key.name]).view(np.uint32))) for key in body.data.shape_keys.key_blocks}
    source_attr = body.data.attributes.get('V3SourcePolygonID'); retained_ids = np.empty(len(body.data.polygons), dtype=np.int32); source_attr.data.foreach_get('value', retained_ids)
    REPORT['body_retained_triangles_exact'] = bool(np.array_equal(loop_ids(body.data).reshape(-1, 3), original_faces[retained_ids]))
    with bpy.data.libraries.load(str(WORK / 'source-single-eye-cdt-corner-fixed.blend'), link=False) as (available, loaded): loaded.objects = ['SharedLeftEyeFacePrototype']
    single = loaded.objects[0]
    REPORT['F0_single_eye_reference_sha256'] = sha(WORK / 'source-single-eye-cdt-corner-fixed.blend')
    if REPORT['F0_single_eye_reference_sha256'] != '737f13ca0af9a7becf75a9d2401f765c04c4ff24f7508be2cb8a9dd964d0bb62': raise RuntimeError('Approved single-eye reference changed')
    prior_anchor = [float_coordinates(single.data.shape_keys.key_blocks[n]) for n in ['Basis', 'Half', 'Closed']]
    f0 = {}
    for b in range(11):
        blink = b / 10; expected = prior_anchor[0] * (1 - 2 * blink) + prior_anchor[1] * (2 * blink) if blink <= .5 else prior_anchor[1] * (2 - 2 * blink) + prior_anchor[2] * (2 * blink - 1)
        actual = float_coordinates(patches['left'].data.shape_keys.key_blocks[key_name(b, 0)])
        f0[key_name(b, 0)] = bool(np.array_equal(expected.astype(np.float32).view(np.uint32), actual.view(np.uint32)))
    REPORT['left_F0_raw_joint_keys_bitwise_match_approved_three_anchor_interpolation'] = f0
    REPORT['right_F0_reference_limitation'] = 'The approved 737f single-eye source is left-only (6957 vertices); right has its own original-source topology and cannot be compared bitwise to left coordinates.'
    for actor in [body] + list(patches.values()) + [bpy.data.objects[name] for name in ocular_names]:
        if actor.data.shape_keys:
            actor.data.shape_keys.animation_data_clear()
            for key in actor.data.shape_keys.key_blocks: key.value = 0
        for modifier in actor.modifiers: modifier.show_viewport = False
    manifest = json.loads((WORK / 'V3_MODEL_MANIFEST.json').read_text()); topologies = {}; edge_pairs = {}
    for side, obj in patches.items():
        info, topologies[side] = topology(obj, original_faces, source_points, manifest['face_helper']['measured_eyes'][side])
        edge_pairs[side] = body_boundary_pairs(body, obj, topologies[side])
        REPORT['eyes'][side] = {'actual_topology': info, 'quick_grid_states': []}
    targets = {side: [target_tree(bpy.data.objects['ReconstructedSclera_' + side]), target_tree(bpy.data.objects['ReconstructedCorneal_' + side])] for side in patches}
    first_fail_reported = False
    for f in range(11):
        focus = f / 10
        for key in body.data.shape_keys.key_blocks: key.value = focus if key.name == 'Focus' else 0
        bpy.context.view_layer.update(); body_eval = body.evaluated_get(bpy.context.evaluated_depsgraph_get()); bm = body_eval.to_mesh()
        bp = world_points(body, bm); boundary_normals = {}
        for side in patches:
            ids = edge_pairs[side][:, 3]; boundary_normals[side] = transform_normals(body, np.asarray([bm.corner_normals[int(i)].vector[:] for i in ids], dtype=np.float64))
        for b in range(11):
            blink = b / 10
            for side, obj in patches.items():
                for key in obj.data.shape_keys.key_blocks: key.value = 1 if key.name == key_name(b, f) and (b or f) else 0
                bpy.context.view_layer.update(); evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get()); mesh = evaluated.to_mesh()
                points = world_points(obj, mesh); mesh.calc_loop_triangles(); tri = np.array([t.vertices[:] for t in mesh.loop_triangles], dtype=np.int64); poly = np.array([t.polygon_index for t in mesh.loop_triangles], dtype=np.int64)
                cross = np.cross(points[tri[:, 1]] - points[tri[:, 0]], points[tri[:, 2]] - points[tri[:, 0]]); areas = np.linalg.norm(cross, axis=1) * .5; normals = unit(cross)
                negative = normals[:, 1] < -1e-8; topo = topologies[side]; pairs = edge_pairs[side]
                corner = transform_normals(obj, np.asarray([mesh.corner_normals[int(i)].vector[:] for i in pairs[:, 2]], dtype=np.float64))
                gap = np.linalg.norm(points[pairs[:, 0]] - bp[pairs[:, 1]], axis=1); corner_angle = angle(corner, boundary_normals[side])
                clearance = {target['object']: sample_clearance(points, tri, poly, target) for target in targets[side]}
                state = {'blink': blink, 'focus': focus, 'key': key_name(b, f), 'finite': bool(np.isfinite(points).all() and np.isfinite(normals).all() and np.isfinite(corner).all()),
                         'minimum_triangle_area_m2': float(areas.min()), 'degenerate_triangles_lt_1e_minus_12_m2': int(np.count_nonzero(areas < 1e-12)),
                         'negative_Y_triangle_count': int(negative.sum()), 'negative_Y_polygon_ids': sorted(set(poly[negative].tolist())),
                         'outer_actual_position_vs_BodyFocus_m': summary(gap), 'outer_actual_corner_vs_retained_BodyFocus_degrees': summary(corner_angle), 'actual_ocular_sample_clearance': clearance}
                worst_corner = int(np.argmax(corner_angle)); pair = pairs[worst_corner]
                local_polygon = int(np.searchsorted(np.array([p.loop_start for p in mesh.polygons]), pair[2], side='right') - 1)
                state['worst_actual_boundary_corner'] = {'angle_degrees': float(corner_angle[worst_corner]), 'local_vertex': int(pair[0]),
                    'original_source_vertex': int(pair[1]), 'local_loop': int(pair[2]), 'local_polygon': local_polygon,
                    'retained_Body_loop': int(pair[3]), 'retained_Body_polygon': int(pair[3] // 3),
                    'local_corner_normal_world': corner[worst_corner].tolist(), 'retained_Body_corner_normal_world': boundary_normals[side][worst_corner].tolist()}
                REPORT['eyes'][side]['quick_grid_states'].append(state)
                failures = [name for name, value in clearance.items() if value['below_actual_front_sample_count_at_1e_minus_8_m']]
                if (failures or negative.any() or areas.min() < 1e-12 or corner_angle.max() >= .05 or gap.max() > 1e-6) and not first_fail_reported:
                    REPORT['first_quick_failure'] = {'side': side, 'state': state}; first_fail_reported = True
                    print('DUAL_JOINT_FIRST_FAILURE ' + json.dumps(REPORT['first_quick_failure']), flush=True)
                evaluated.to_mesh_clear()
        body_eval.to_mesh_clear()
        print('DUAL_JOINT_QUICK_FOCUS_COMPLETE', f, 'seconds', round(time.time() - started, 2), flush=True)
        (ROOT / 'dual-joint-review.json').write_text(json.dumps(REPORT, indent=2, ensure_ascii=False) + '\n')
    REPORT['source_sha256_after'] = sha(SOURCE)
    if REPORT['source_sha256_after'] != SOURCE_EXPECTED: raise RuntimeError('Dual source changed during audit')
    REPORT['coverage']['quick_grid_evaluated_per_eye'] = {side: len(value['quick_grid_states']) for side, value in REPORT['eyes'].items()}
    REPORT['status'] = 'quick_121_grid_failed' if first_fail_reported else 'quick_121_grid_completed'
    REPORT['elapsed_seconds'] = time.time() - started
    REPORT['remaining_scope'] = ['Full 2121 evaluated states per eye with strict 3D/XZ intersections', 'Global minimum Euclidean clearance over all samples', 'Pose/clips/LOD/GLB/art acceptance remain outside this local review']
    REPORT['quick_grid_summary'] = {}
    for side, data in REPORT['eyes'].items():
        states = data['quick_grid_states']; corner = max(states, key=lambda s: s['outer_actual_corner_vs_retained_BodyFocus_degrees']['max'])
        summary_data = {'evaluated_nodes': len(states), 'all_finite': all(s['finite'] for s in states),
            'negative_Y_triangles_across_grid': sum(s['negative_Y_triangle_count'] for s in states),
            'degenerate_triangles_across_grid': sum(s['degenerate_triangles_lt_1e_minus_12_m2'] for s in states),
            'maximum_outer_position_vs_BodyFocus_m': max(s['outer_actual_position_vs_BodyFocus_m']['max'] for s in states),
            'worst_boundary_corner_state': {'blink': corner['blink'], 'focus': corner['focus'], **corner['worst_actual_boundary_corner']}, 'ocular': {}}
        for target in targets[side]:
            name = target['object']; records = [(s, s['actual_ocular_sample_clearance'][name]) for s in states]
            valid = [(s, r) for s, r in records if r['worst_front_sample'] is not None]
            state, result = min(valid, key=lambda pair: pair[1]['worst_front_sample']['front_Y_gap_m'])
            by_type = {}
            for _, record in records:
                for kind, value in record['minimum_front_Y_gap_by_sample_type_m'].items(): by_type[kind] = min(by_type.get(kind, math.inf), value)
            summary_data['ocular'][name] = {'worst_blink': state['blink'], 'worst_focus': state['focus'], **result['worst_front_sample'],
                'minimum_front_Y_gap_by_sample_type_m_over_121_grid': by_type,
                'grid_nodes_with_samples_below_actual_front': sum(r['below_actual_front_sample_count_at_1e_minus_8_m'] > 0 for _, r in records)}
        REPORT['quick_grid_summary'][side] = summary_data
    REPORT['full_scan_deferred_reason'] = 'The actual 121-grid preflight already fails cornea and Focus boundary-normal constraints; parent is preparing a separate revision. No 2121-state acceptance is claimed for this failing immutable source.' if first_fail_reported else None


try:
    main()
except Exception as exc:
    REPORT['status'] = 'failed'; REPORT['error'] = repr(exc); REPORT['traceback'] = traceback.format_exc()
finally:
    REPORT['review_script_sha256'] = sha(__file__)
    (ROOT / 'dual-joint-review.json').write_text(json.dumps(REPORT, indent=2, ensure_ascii=False) + '\n')
    print('DUAL_JOINT_QUICK_REVIEW ' + json.dumps({'status': REPORT['status'], 'error': REPORT.get('error'), 'coverage': REPORT['coverage']}, ensure_ascii=False), flush=True)


