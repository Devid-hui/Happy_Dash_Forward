"""Read-only positive-area UV overlap verification for the high-detail skin.

Blender --background --disable-autoexec SOURCE.blend --python tools/naifrog_uv_verify.py \
    -- --out REPORT.json

Default scope is NaifrogContinuousSkin; --mesh can select another object.
Candidate pairs use a 2D AABB grid and convex Sutherland-Hodgman intersection.
Shared edges/vertices alone have zero area. Default area epsilon is exactly 0.
Budgets are explicit: a bounded run never claims full-atlas clearance.
No geometry, UVs, material, animation or file in the opened scene is edited.
"""

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from fractions import Fraction
from functools import lru_cache
import hashlib
import json
import math
from pathlib import Path
import sys
import time


REGION_ATTRIBUTE = "NaiFrogUVRegion"


def _cross(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _clip_polygon(subject, clip):
    winding = _cross(clip[0], clip[1], clip[2])
    if winding == 0:
        return []
    sign = 1 if winding > 0 else -1
    polygon = list(subject)
    for a, b in zip(clip, clip[1:] + clip[:1]):
        if not polygon:
            break
        result = []
        previous = polygon[-1]
        previous_side = sign * _cross(a, b, previous)
        for current in polygon:
            current_side = sign * _cross(a, b, current)
            previous_inside, current_inside = previous_side >= 0, current_side >= 0
            if previous_inside != current_inside:
                ratio = previous_side / (previous_side - current_side)
                result.append((previous[0] + ratio * (current[0] - previous[0]),
                               previous[1] + ratio * (current[1] - previous[1])))
            if current_inside:
                result.append(current)
            previous, previous_side = current, current_side
        polygon = result
    return polygon


def _integer_points(*triangles):
    ratios = [[tuple(float(value).as_integer_ratio() for value in point) for point in triangle]
              for triangle in triangles]
    power = max(denominator.bit_length() - 1 for triangle in ratios for point in triangle for _, denominator in point)
    return [[tuple(numerator << (power - (denominator.bit_length() - 1)) for numerator, denominator in point)
             for point in triangle] for triangle in ratios]


def _interiors_overlap(a, b):
    """Exact integer SAT: touching projection intervals have no positive area."""
    for triangle, other in ((a, b), (b, a)):
        winding = _cross(*triangle)
        if winding == 0:
            return False
        sign = 1 if winding > 0 else -1
        for index in range(3):
            edge_a, edge_b, opposite = triangle[index], triangle[(index + 1) % 3], triangle[(index + 2) % 3]
            near = [sign * _cross(edge_a, edge_b, point) for point in other]
            far = [sign * ((edge_b[0] - edge_a[0]) * (point[1] - opposite[1])
                          - (edge_b[1] - edge_a[1]) * (point[0] - opposite[0])) for point in other]
            if max(near) <= 0 or min(far) >= 0:
                return False
    return True


def polygon_area(polygon):
    if len(polygon) < 3:
        return 0.0
    # A local origin avoids cancellation from subtracting large global UV sums.
    origin = polygon[0]
    return abs(math.fsum(_cross(origin, polygon[index], polygon[index + 1])
                         for index in range(1, len(polygon) - 1))) * .5


def triangle_intersection_area(a, b):
    return _intersection_measure(a, b)[0]


def _intersection_measure(a, b, integer_a=None, integer_b=None):
    a = [tuple(float(value) for value in point) for point in a]
    b = [tuple(float(value) for value in point) for point in b]
    if integer_a is None:
        integer_a, integer_b = _integer_points(a, b)
    if not _interiors_overlap(integer_a, integer_b):
        return 0.0, []
    polygon = _clip_polygon(a, b)
    area = polygon_area(polygon)
    if area == 0:
        exact_a = [tuple(Fraction(value) for value in point) for point in a]
        exact_b = [tuple(Fraction(value) for value in point) for point in b]
        exact = _clip_polygon(exact_a, exact_b)
        exact_area = abs(sum((_cross(exact[0], exact[index], exact[index + 1])
                              for index in range(1, len(exact) - 1)), Fraction(0))) / 2
        area = float(exact_area)
        polygon = [tuple(float(value) for value in point) for point in exact]
    return area, polygon


def intersection_polygon(a, b):
    return _intersection_measure(a, b)[1]


def verify_triangles(triangles, *, polygons=None, regions=None, grid_size=512,
                     max_seconds=60.0, max_candidates=2000000,
                     max_reported_pairs=1000, area_epsilon=0.0, progress=False):
    import numpy as np

    started = time.monotonic()
    input_dtype = np.asarray(triangles).dtype
    triangles = np.asarray(triangles, dtype=np.float64)
    if triangles.ndim != 3 or triangles.shape[1:] != (3, 2) or not len(triangles):
        raise ValueError("Expected nonempty Nx3x2 UV triangles")
    if not np.isfinite(triangles).all():
        raise ValueError("UV triangles contain nonfinite values")
    if not 1 <= grid_size <= 2048 or not math.isfinite(max_seconds) or max_seconds < 0 or max_candidates < 0 or max_reported_pairs < 0 or not math.isfinite(area_epsilon) or area_epsilon < 0:
        raise ValueError("Invalid spatial grid, budget, report limit, or area epsilon")
    count = len(triangles)
    polygons = np.arange(count, dtype=np.int64) if polygons is None else np.asarray(polygons, dtype=np.int64)
    regions = np.full(count, -1, dtype=np.int32) if regions is None else np.asarray(regions, dtype=np.int32)
    if polygons.shape != (count,) or regions.shape != (count,):
        raise ValueError("Polygon indices and region labels must match the triangle count")
    a, b, c = triangles[:, 0], triangles[:, 1], triangles[:, 2]
    ab, ac = b - a, c - a
    areas = np.abs(ab[:, 0] * ac[:, 1] - ab[:, 1] * ac[:, 0]) * .5
    low, high = triangles.min(axis=1), triangles.max(axis=1)
    origin, extent = low.min(axis=0), high.max(axis=0) - low.min(axis=0)
    step = np.where(extent > 0, extent / grid_size, 1.0)
    cell_low = np.clip(np.floor((low - origin) / step).astype(np.int32), 0, grid_size - 1)
    cell_high = np.clip(np.floor((high - origin) / step).astype(np.int32), 0, grid_size - 1)
    large = np.prod(cell_high - cell_low + 1, axis=1) > 64
    valid = areas > 0
    nonzero = np.abs(triangles[triangles != 0])
    precision = 24 if input_dtype == np.dtype(np.float32) else 53
    power = max(0, precision - int(np.frexp(nonzero.min())[1])) if len(nonzero) else 0
    scale = math.ldexp(1.0, power) if power <= 1023 else None
    buckets = defaultdict(list)
    large_indices = []
    indexed = 0
    processed_cells = 0
    processed_large = 0
    examined = 0
    positive = 0
    pairs = []
    kinds = Counter()
    region_counts = Counter()
    stop_reason = None
    last_progress = started

    def expired():
        return bool(max_seconds and time.monotonic() - started >= max_seconds)

    def announce(stage):
        nonlocal last_progress
        now = time.monotonic()
        if progress and now - last_progress >= 5:
            print("UV_VERIFY_PROGRESS=" + json.dumps({"stage": stage, "indexed_triangles": indexed,
                  "processed_cells": processed_cells, "candidate_pairs_examined": examined,
                  "positive_pairs": positive, "elapsed_seconds": round(now - started, 2)}), flush=True)
            last_progress = now

    for index in range(count):
        if index % 1024 == 0:
            announce("index")
            if expired():
                stop_reason = "time_budget_during_indexing"
                break
        indexed += 1
        if not valid[index]:
            continue
        if large[index]:
            large_indices.append(index)
            continue
        x0, y0 = cell_low[index]
        x1, y1 = cell_high[index]
        for x in range(int(x0), int(x1) + 1):
            for y in range(int(y0), int(y1) + 1):
                buckets[(x, y)].append(index)

    @lru_cache(maxsize=65536)
    def points(index):
        values = triangles[index].tolist()
        if scale is not None:
            integer = [tuple(int(value * scale) for value in point) for point in values]
        else:
            integer = [tuple(numerator << (power - (denominator.bit_length() - 1))
                             for numerator, denominator in (value.as_integer_ratio() for value in point)) for point in values]
        return values, integer

    def examine(left, right):
        nonlocal examined, positive, stop_reason
        for i, j in zip(left.tolist(), right.tolist()):
            if (max_candidates and examined >= max_candidates) or expired():
                stop_reason = "candidate_budget" if max_candidates and examined >= max_candidates else "time_budget_during_pairs"
                return False
            examined += 1
            a, integer_a = points(i)
            b, integer_b = points(j)
            area, polygon = _intersection_measure(a, b, integer_a, integer_b)
            if area <= area_epsilon:
                continue
            positive += 1
            ra, rb = int(regions[i]), int(regions[j])
            kind = "unlabelled" if ra < 0 or rb < 0 else "within_region" if ra == rb else "cross_region"
            kinds[kind] += 1
            region_counts[tuple(sorted((ra, rb)))] += 1
            if len(pairs) < max_reported_pairs:
                pairs.append({"triangle_a": i, "triangle_b": j,
                              "polygon_a": int(polygons[i]), "polygon_b": int(polygons[j]),
                              "region_a": ra, "region_b": rb, "classification": kind,
                              "intersection_area": area,
                              "intersection_fraction_of_smaller_triangle": area / min(areas[i], areas[j]),
                              "sample_uv": [math.fsum(p[axis] for p in polygon) / len(polygon) for axis in (0, 1)]})
        return True

    def aabb_pairs(left, right, owner=None):
        mask = np.all(np.minimum(high[left], high[right]) > np.maximum(low[left], low[right]), axis=1)
        if owner is not None:
            mask &= np.all(np.maximum(cell_low[left], cell_low[right]) == owner, axis=1)
        return left[mask], right[mask]

    def cell_batches(ids):
        ids = np.asarray(ids, dtype=np.int64)
        if len(ids) <= 256:
            row, column = np.triu_indices(len(ids), k=1)
            yield ids[row], ids[column]
        else:
            for row in range(len(ids) - 1):
                for start in range(row + 1, len(ids), 8192):
                    right = ids[start:start + 8192]
                    yield np.full(len(right), ids[row], dtype=np.int64), right

    if stop_reason is None:
        for owner, ids in sorted(buckets.items()):
            announce("grid_pairs")
            if expired():
                stop_reason = "time_budget_during_grid_cells"
                break
            finished = True
            for left, right in cell_batches(ids):
                left, right = aabb_pairs(left, right, np.asarray(owner))
                if not examine(left, right):
                    finished = False
                    break
            if not finished:
                break
            processed_cells += 1
    if stop_reason is None:
        for index in large_indices:
            announce("large_triangle_pairs")
            finished = True
            for start in range(0, count, 8192):
                if expired():
                    stop_reason = "time_budget_during_large_triangles"
                    finished = False
                    break
                right = np.arange(start, min(count, start + 8192), dtype=np.int64)
                # Large-vs-small pairs are absent from the grid. Large-vs-large
                # pairs have exactly one owner, the smaller triangle index.
                mask = valid[right] & (right != index) & (~large[right] | (right > index))
                right = right[mask]
                left = np.full(len(right), index, dtype=np.int64)
                left, right = aabb_pairs(left, right)
                if not examine(left, right):
                    finished = False
                    break
            if not finished:
                break
            processed_large += 1
    complete = stop_reason is None and indexed == count and processed_cells == len(buckets) and processed_large == len(large_indices)
    zero_area = int(np.count_nonzero(~valid))
    return {
        "method": "2D triangle AABB grid, exact dyadic-integer SAT contacts, Sutherland-Hodgman area",
        "arithmetic": "Exact integer separating-axis classification on represented UVs; float64 intersection area, rational fallback for collapsed positive area.",
        "input_uv_dtype": str(input_dtype), "dyadic_scale_power": power,
        "area_epsilon": area_epsilon, "positive_criterion": "intersection_area > area_epsilon",
        "uv_triangle_count": count, "zero_area_triangles": zero_area,
        "uv_range_min": origin.tolist(), "uv_range_max": high.max(axis=0).tolist(),
        "summed_triangle_area": float(areas.sum()), "positive_overlap_pairs": positive,
        "cross_region_pairs": kinds["cross_region"], "within_region_pairs": kinds["within_region"],
        "unlabelled_pairs": kinds["unlabelled"],
        "region_pair_counts": [{"regions": list(key), "pairs": value} for key, value in sorted(region_counts.items())],
        "pairs": pairs, "reported_pairs_truncated": positive > len(pairs),
        "coverage": {"complete": complete, "stop_reason": stop_reason,
                     "indexed_triangles": indexed, "total_triangles": count,
                     "processed_grid_cells": processed_cells, "total_nonempty_grid_cells": len(buckets),
                     "processed_large_triangles": processed_large, "total_large_triangles": len(large_indices),
                     "candidate_pairs_examined": examined,
                     "note": "Complete requires indexing and exhausting every owned AABB candidate; bounded zero findings are not clearance."},
        "configuration": {"grid_size": grid_size, "large_triangle_cell_limit": 64,
                          "max_seconds": max_seconds, "max_candidates": max_candidates,
                          "max_reported_pairs": max_reported_pairs},
        "elapsed_seconds": time.monotonic() - started,
        "ok": complete and zero_area == 0 and positive == 0,
        "status": "overlap" if positive else "bounded" if not complete else "invalid_uv" if zero_area else "clear",
    }


def inspect_mesh(obj, uv_layer=None, **options):
    import numpy as np

    if obj.type != "MESH" or obj.mode != "OBJECT":
        raise ValueError("UV verification needs an Object Mode mesh")
    mesh = obj.data
    name = uv_layer or (mesh.uv_layers.active.name if mesh.uv_layers.active else None)
    if name is None:
        raise ValueError(f"{obj.name} has no active UV layer")
    mesh.calc_loop_triangles()
    layer = mesh.uv_layers.get(name)
    if layer is None:
        raise ValueError(f"{obj.name} has no UV layer {name}")
    if len(layer.data) != len(mesh.loops):
        raise ValueError("UV data length does not match mesh corners")
    uvs = np.empty(len(layer.data) * 2, dtype=np.float32)
    layer.data.foreach_get("uv", uvs)
    uvs = uvs.reshape(-1, 2)
    if not np.isfinite(uvs).all():
        raise ValueError("Nonfinite UV corner values")
    loops = np.empty(len(mesh.loop_triangles) * 3, dtype=np.int32)
    mesh.loop_triangles.foreach_get("loops", loops)
    polygons = np.empty(len(mesh.loop_triangles), dtype=np.int32)
    mesh.loop_triangles.foreach_get("polygon_index", polygons)
    region_attribute = mesh.attributes.get(REGION_ATTRIBUTE)
    labels = None
    if region_attribute is not None:
        if region_attribute.domain != "FACE" or region_attribute.data_type != "INT":
            raise ValueError(f"{REGION_ATTRIBUTE} must be FACE INT")
        face_labels = np.empty(len(mesh.polygons), dtype=np.int32)
        region_attribute.data.foreach_get("value", face_labels)
        labels = face_labels[polygons]
    report = verify_triangles(uvs[loops.reshape(-1, 3)], polygons=polygons, regions=labels, **options)
    report.update({"object": obj.name, "mesh_data": mesh.name, "uv_layer": name,
                   "uv_corner_count": len(uvs), "finite_corner_values": True,
                   "region_attribute": REGION_ATTRIBUTE if region_attribute else None,
                   "region_triangle_counts": [{"region": int(key), "triangles": int(value)}
                                              for key, value in sorted(Counter(labels.tolist()).items())] if labels is not None else []})
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--mesh", action="append", help="Object name; repeat to inspect meshes separately")
    parser.add_argument("--uv-layer")
    parser.add_argument("--grid-size", type=int, default=512)
    parser.add_argument("--max-seconds", type=float, default=60.0, help="Per-mesh pair-check budget; 0 means unlimited")
    parser.add_argument("--max-candidates", type=int, default=2000000, help="Per-mesh clipping budget; 0 means unlimited")
    parser.add_argument("--max-reported-pairs", type=int, default=1000)
    parser.add_argument("--area-epsilon", type=float, default=0.0)
    args = parser.parse_args(argv)
    report = {"schema": "naifrog-uv-overlap-v1", "checked_at": datetime.now(timezone.utc).isoformat(),
              "checker_path": str(Path(__file__).resolve()), "checker_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "scope": "Within each selected raw mesh UV atlas; meshes and LODs are not compared to one another.",
              "limitations": ["No geometric self-intersection, animated skinning, image fidelity, or Godot verification.",
                              "Area magnitudes are float64 estimates; strict contact classification uses exact represented-coordinate integer predicates."]}
    try:
        import bpy
        report["source"] = bpy.data.filepath
        report["blender"] = bpy.app.version_string
        report["meshes"] = []
        for name in args.mesh or ["NaifrogContinuousSkin"]:
            obj = bpy.data.objects.get(name)
            if obj is None:
                raise ValueError(f"Mesh object does not exist: {name}")
            report["meshes"].append(inspect_mesh(obj, args.uv_layer, grid_size=args.grid_size,
                max_seconds=args.max_seconds, max_candidates=args.max_candidates,
                max_reported_pairs=args.max_reported_pairs, area_epsilon=args.area_epsilon, progress=True))
        report["complete"] = all(mesh["coverage"]["complete"] for mesh in report["meshes"])
        report["ok"] = all(mesh["ok"] for mesh in report["meshes"])
        report["status"] = "overlap" if any(mesh["positive_overlap_pairs"] for mesh in report["meshes"]) else "bounded" if not report["complete"] else "clear" if report["ok"] else "invalid_uv"
    except Exception as exc:
        report.update({"status": "error", "ok": False, "complete": False,
                       "error_type": type(exc).__name__, "error": str(exc)})
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    print("UV_VERIFY_RESULT=" + json.dumps({"report": str(args.out.resolve()), "status": report["status"],
                                         "complete": report["complete"], "ok": report["ok"]}), flush=True)
    return 0 if report["ok"] else 2 if report["status"] == "bounded" else 1


if __name__ == "__main__":
    arguments = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    raise SystemExit(main(arguments))
