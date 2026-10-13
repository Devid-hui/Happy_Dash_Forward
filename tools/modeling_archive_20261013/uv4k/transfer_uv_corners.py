"""Transfer only retained source triangles; new topology needs its own UV.

This is intentionally face-corner based: a source vertex can have several UV
coordinates at a seam. No production or face-owner file is edited here.
"""
from pathlib import Path
import numpy as np


def retained_corner_uv(source_faces, source_corner_uv, target_polygon_ids,
                       target_original_vertex_ids):
    source_faces = np.asarray(source_faces, dtype=np.int64)
    source_corner_uv = np.asarray(source_corner_uv).reshape(-1, 3, 2)
    polygon_ids = np.asarray(target_polygon_ids, dtype=np.int64)
    vertex_ids = np.asarray(target_original_vertex_ids, dtype=np.int64)
    if source_faces.ndim != 2 or source_faces.shape[1] != 3:
        raise ValueError('Expected the original triangulated source')
    if source_corner_uv.shape != (len(source_faces), 3, 2):
        raise ValueError('UV/source face count mismatch')
    if polygon_ids.ndim != 1 or vertex_ids.shape != (len(polygon_ids), 3):
        raise ValueError('Target polygons and corner IDs must describe triangles')
    if np.any(polygon_ids < -1) or np.any(polygon_ids >= len(source_faces)):
        raise ValueError('Unknown SourcePolygonID; only -1 declares new topology')
    retained = polygon_ids >= 0
    result = np.full((len(polygon_ids), 3, 2), np.nan,
                     dtype=source_corner_uv.dtype)
    original = source_faces[polygon_ids[retained]]
    target = vertex_ids[retained]
    correspondence = target[:, :, None] == original[:, None, :]
    if np.any(correspondence.sum(axis=2) != 1):
        raise ValueError('Retained face has ambiguous or changed original corners')
    if np.any(correspondence.sum(axis=1) != 1):
        raise ValueError('Target repeats or omits an original source corner')
    order = correspondence.argmax(axis=2)
    retained_uv = source_corner_uv[polygon_ids[retained]]
    result[retained] = np.take_along_axis(retained_uv, order[:, :, None], axis=1)
    # New triangles deliberately stay NaN. A Blender caller must supply their
    # own actual UV, rather than exporting an empty or arbitrary zero layer.
    return result, retained


def load_actual_mapping(evidence_directory=None):
    root = Path(evidence_directory or Path(__file__).resolve().parent)
    source = np.load(root / 'source-body-geometry.npz')
    atlas = np.load(selected_atlas_path(root))
    if not np.array_equal(atlas['source_vertex_index'][atlas['uv_vertex_indices']],
                          source['faces']):
        raise ValueError('Atlas source face/corner identity failed')
    return source['faces'], atlas['corner_uv']


def selected_atlas_path(evidence_directory=None):
    import json, hashlib
    root = Path(evidence_directory or Path(__file__).resolve().parent)
    selection = json.loads((root / 'SELECTED_ATLAS.json').read_text())
    path = Path(selection['atlas_path'])
    if hashlib.sha256(path.read_bytes()).hexdigest() != selection['atlas_sha256']:
        raise ValueError('Selected atlas bytes changed')
    return path


def retained_loop_uv(source_corner_uv, target_polygon_ids, target_loop_ids):
    """Use explicit c3 post-mouth loop IDs from the face owner's sidecar.

    c3 Body is all triangles, so each retained SourcePolygonID owns loops
    [3*p, 3*p+1, 3*p+2]. Validate this identity before direct indexing.
    """
    source_uv = np.asarray(source_corner_uv).reshape(-1, 2)
    polygon_ids = np.asarray(target_polygon_ids, dtype=np.int64)
    loop_ids = np.asarray(target_loop_ids, dtype=np.int64)
    if len(source_uv) % 3 or loop_ids.shape != (len(polygon_ids), 3):
        raise ValueError('Source/target must describe actual triangular corners')
    if np.any(polygon_ids < -1) or np.any(polygon_ids >= len(source_uv)//3):
        raise ValueError('Unknown c3 post-mouth source polygon')
    retained = polygon_ids >= 0
    retained_loops = loop_ids[retained]
    if np.any(retained_loops < 0) or np.any(retained_loops >= len(source_uv)):
        raise ValueError('Retained face has an invalid source loop')
    if np.any(retained_loops//3 != polygon_ids[retained, None]):
        raise ValueError('Loop IDs do not belong to the declared source triangle')
    sorted_loops = np.sort(retained_loops, axis=1)
    expected = polygon_ids[retained, None]*3+np.arange(3)
    if not np.array_equal(sorted_loops, expected):
        raise ValueError('Retained face repeats or omits an original corner')
    result = np.full((len(polygon_ids), 3, 2), np.nan, dtype=source_uv.dtype)
    result[retained] = source_uv[retained_loops]
    return result, retained


def self_test():
    # The shared original vertex 0 has distinct UVs in the two source faces.
    # Choosing one UV per vertex would erase this deliberate seam.
    faces = np.array([[0, 1, 2], [0, 2, 3]])
    uv = np.array([[[.1, .1], [.2, .1], [.1, .2]],
                   [[.7, .7], [.8, .7], [.7, .8]]], dtype=np.float32)
    polygon_ids = np.array([1, 0, -1])
    target = np.array([[3, 2, 0], [1, 2, 0], [-1, -1, -1]])
    mapped, mask = retained_corner_uv(faces, uv, polygon_ids, target)
    assert np.array_equal(mapped[0], uv[1, [2, 1, 0]])
    assert np.array_equal(mapped[1], uv[0, [1, 2, 0]])
    assert mask.tolist() == [True, True, False]
    assert np.isnan(mapped[2]).all()
    rejected = False
    try:
        retained_corner_uv(faces, uv, [0], [[0, 1, 1]])
    except ValueError:
        rejected = True
    assert rejected
    by_loop, loop_mask = retained_loop_uv(uv, polygon_ids,
                                         [[5, 4, 3], [1, 2, 0], [-1, -1, -1]])
    assert np.array_equal(by_loop[loop_mask], mapped[mask])
    return {'seam_vertex_keeps_face_specific_uv': True,
            'cyclic_and_reversed_corners_preserved': True,
            'undeclared_changed_triangle_rejected': True,
            'new_topology_explicitly_unmapped': True,
            'explicit_post_mouth_loop_mapping_matches_vertex_corner_mapping': True}


if __name__ == '__main__':
    import json
    print(json.dumps(self_test(), indent=2))
