"""Bounded, read-only triangle geometry checks; metre coordinates, fixed tolerances."""
import itertools
import math
import numpy as np

LENGTH_EPS = 1e-8
AREA_EPS = 1e-12
BARY_EPS = 1e-7


def barycentric(point, triangle):
    a, b, c = triangle
    v0, v1, v2 = b-a, c-a, point-a
    aa, ab, bb = np.dot(v0, v0), np.dot(v0, v1), np.dot(v1, v1)
    den = aa*bb-ab*ab
    if den <= AREA_EPS**2:
        return np.array([-math.inf]*3)
    ac, bc = np.dot(v0, v2), np.dot(v1, v2)
    v = (bb*ac-ab*bc)/den
    w = (aa*bc-ab*ac)/den
    return np.array([1-v-w, v, w])


def clip_polygon(subject, triangle, eps=LENGTH_EPS):
    """Intersect a convex 2D polygon with a triangle, preserving its orientation."""
    subject = [np.asarray(p, dtype=float) for p in subject]
    triangle = np.asarray(triangle)
    area = np.cross(triangle[1]-triangle[0], triangle[2]-triangle[0])
    sign = 1 if area >= 0 else -1
    for a, b in zip(triangle, np.roll(triangle, -1, axis=0)):
        if not subject:
            break
        def distance(p):
            return float(sign*np.cross(b-a, p-a))
        old, subject = subject, []
        previous, dp = old[-1], distance(old[-1])
        for current in old:
            dc = distance(current)
            if (dp >= -eps) != (dc >= -eps):
                subject.append(previous+(current-previous)*(dp/(dp-dc)))
            if dc >= -eps:
                subject.append(current)
            previous, dp = current, dc
    return np.asarray(subject)


def polygon_area(poly):
    if len(poly) < 3:
        return 0.0
    return abs(float(sum(np.cross(a, b) for a, b in zip(poly, np.roll(poly, -1, axis=0)))))*.5


def plane_segment(triangle, distances):
    points = []
    for i in range(3):
        j = (i+1) % 3
        if abs(distances[i]) <= LENGTH_EPS:
            points.append(triangle[i])
        if distances[i]*distances[j] < 0 and abs(distances[i]) > LENGTH_EPS and abs(distances[j]) > LENGTH_EPS:
            points.append(triangle[i]+(triangle[j]-triangle[i])*(distances[i]/(distances[i]-distances[j])))
    if len(points) < 2:
        return None
    return np.asarray(points)


def strict_crossing(a, b):
    """Return strict noncoplanar crossing/coplanar area overlap; boundary contact is none.

    The noncoplanar intersection segment must have positive length and a point
    strictly inside both triangles. Shared topology must be excluded by caller.
    """
    a, b = np.asarray(a, float), np.asarray(b, float)
    na, nb = np.cross(a[1]-a[0], a[2]-a[0]), np.cross(b[1]-b[0], b[2]-b[0])
    ma, mb = np.linalg.norm(na), np.linalg.norm(nb)
    if ma*.5 <= AREA_EPS or mb*.5 <= AREA_EPS:
        return None
    na, nb = na/ma, nb/mb
    da, db = (a-b[0])@nb, (b-a[0])@na
    if np.all(da > LENGTH_EPS) or np.all(da < -LENGTH_EPS) or np.all(db > LENGTH_EPS) or np.all(db < -LENGTH_EPS):
        return None
    line = np.cross(na, nb)
    line_length = np.linalg.norm(line)
    if line_length <= 1e-10:
        if np.max(np.abs(da)) > LENGTH_EPS:
            return None
        axes = [i for i in range(3) if i != int(np.argmax(np.abs(na)))]
        overlap = clip_polygon(a[:, axes], b[:, axes], eps=AREA_EPS)
        return "coplanar_area_overlap" if polygon_area(overlap) > AREA_EPS else None
    line /= line_length
    sa, sb = plane_segment(a, da), plane_segment(b, db)
    if sa is None or sb is None:
        return None
    ia, ib = sa@line, sb@line
    low, high = max(ia.min(), ib.min()), min(ia.max(), ib.max())
    if high-low <= LENGTH_EPS:
        return None
    mid = (low+high)*.5
    point = sa[0]+line*(mid-float(sa[0]@line))
    if np.min(barycentric(point, a)) > BARY_EPS and np.min(barycentric(point, b)) > BARY_EPS:
        return "strict_noncoplanar_crossing"
    return None


def candidate_pairs(triangles, cell_size=.015):
    """Exact AABB broad phase via a uniform hash. No candidate is filtered by distance."""
    triangles = np.asarray(triangles)
    low, high = triangles.min(axis=1), triangles.max(axis=1)
    cells = {}
    for i, (lo, hi) in enumerate(zip(low, high)):
        begin, end = np.floor(lo/cell_size).astype(int), np.floor(hi/cell_size).astype(int)
        for key in itertools.product(*(range(a, b+1) for a, b in zip(begin, end))):
            cells.setdefault(key, []).append(i)
    pairs = set()
    for ids in cells.values():
        for i, j in itertools.combinations(ids, 2):
            if np.all(high[i]+LENGTH_EPS >= low[j]) and np.all(high[j]+LENGTH_EPS >= low[i]):
                pairs.add((i, j))
    return sorted(pairs)


def self_crossings(vertices, faces, face_ids=None):
    faces = np.asarray(faces, dtype=int)
    if face_ids is None:
        face_ids = np.arange(len(faces))
    triangles = np.asarray(vertices)[faces]
    adjacent, checked, failures = 0, 0, []
    for i, j in candidate_pairs(triangles):
        if np.intersect1d(faces[i], faces[j]).size:
            adjacent += 1
            continue
        checked += 1
        kind = strict_crossing(triangles[i], triangles[j])
        if kind:
            failures.append({"face_a": int(face_ids[i]), "face_b": int(face_ids[j]), "kind": kind})
    return {"candidate_nonneighbor_pairs": checked, "adjacent_pairs_excluded": adjacent,
            "strict_intersections": len(failures), "examples": failures[:30]}


def synthetic():
    a = np.array([[-1., -1., 0.], [1., -1., 0.], [0., 1., 0.]])
    cases = [
        ("proper_interior_crossing", a, np.array([[0., -.5, -1.], [0., -.5, 1.], [0., .5, 0.]]), "strict_noncoplanar_crossing"),
        ("separated_parallel", a, a+np.array([0, 0, .01]), None),
        ("shared_edge_only", a, np.array([[-1., -1., 0.], [1., -1., 0.], [0., -2., 1.]]), None),
        ("point_touch_only", a, np.array([[0., 1., 0.], [-.5, 2., 1.], [.5, 2., 1.]]), None),
        ("strict_coplanar_overlap", a, a*.5, "coplanar_area_overlap"),
        ("coplanar_edge_touch", a, np.array([[-1., -1., 0.], [1., -1., 0.], [0., -2., 0.]]), None),
        ("degenerate_triangle", a, np.zeros((3, 3)), None),
    ]
    result = [{"name": name, "expected": expected, "actual": strict_crossing(left, right)} for name, left, right, expected in cases]
    for item in result:
        item["pass"] = item["actual"] == item["expected"]
    # Scale, translate, reverse windings: the crossing classification is invariant.
    left, right = cases[0][1], cases[0][2]
    for scale in (.01, .1, 2.):
        actual = strict_crossing((left*scale+[.03, .1, 2.6])[::-1], (right*scale+[.03, .1, 2.6])[::-1])
        result.append({"name": f"translated_reversed_scale_{scale}", "expected": "strict_noncoplanar_crossing", "actual": actual, "pass": actual == "strict_noncoplanar_crossing"})
    return {"pass": all(item["pass"] for item in result), "cases": result,
            "tolerances": {"length_m": LENGTH_EPS, "degenerate_area_m2": AREA_EPS, "strict_barycentric_margin": BARY_EPS}}
