"""Bind actual completed atlas corners to the frozen c3 source identity."""
from pathlib import Path
import hashlib
import json
import numpy as np
from transfer_uv_corners import load_actual_mapping, retained_corner_uv, self_test, selected_atlas_path

root = Path(__file__).resolve().parent
source_receipt = json.loads((root / 'SOURCE_AND_API.json').read_text())
source_path = Path(source_receipt['source'])
expected_source = 'c3f08b4b01489b5cc548aac7f23717338d24819fbb0e514706d59986bfa6be8c'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(source_path) == source_receipt['source_sha256'] == expected_source
faces, uv = load_actual_mapping(root)
polygon_ids = np.arange(len(faces), dtype=np.int32)
mapped, retained = retained_corner_uv(faces, uv, polygon_ids, faces)
assert retained.all() and np.array_equal(mapped.reshape(-1, 2), uv)
path = root / 'body-source-corner-uv-transfer.npz'
np.savez(path, source_polygon_id=polygon_ids,
         original_corner_vertex_id=faces,
         source_corner_uv=uv.reshape(-1, 3, 2))
report = {'source': str(source_path), 'source_sha256': expected_source,
          'body_object': 'NailongSkin_Reconstructed',
          'source_polygon_count': len(faces),
          'source_corner_count': int(faces.size),
          'polygon_identity': 'Row is c3 post-mouth-cleanup SourcePolygonID; '
                              'not a raw pre-cleanup polygon index',
          'corner_identity': 'Original vertex index matched within that original '
                             'triangle, preserving UV seams and any corner order',
          'exact_full_source_roundtrip': True,
          'new_topology_policy': 'SourcePolygonID=-1 returns NaN; the face owner '
                                 'must parameterize these triangles separately',
          'bundle': str(path), 'bundle_sha256': sha(path),
          'atlas_path': str(selected_atlas_path(root)),
          'atlas_sha256': sha(selected_atlas_path(root)),
          'source_geometry_sha256': sha(root / 'source-body-geometry.npz'),
          'transfer_function': str(root / 'transfer_uv_corners.py'),
          'transfer_function_sha256': sha(root / 'transfer_uv_corners.py'),
          'synthetic_seam_and_corner_tests': self_test()}
(root / 'UV_CORNER_TRANSFER_RECEIPT.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2))
