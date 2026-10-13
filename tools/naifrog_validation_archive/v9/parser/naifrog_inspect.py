"""Read-only Blender 4.5 / GLB inspection for the authored Naifrog asset.

Blender --background --disable-autoexec model.blend --python tools/naifrog_inspect.py \
    -- --blend-report report.json --expected-json expected.json
python3 tools/naifrog_inspect.py --glb lod0.glb lod1.glb lod2.glb --out report.json \
    --expected-json expected.json

Expected JSON may contain mesh_names, material_names, shape_names (a mapping from
mesh name to ordered non-Basis keys), connected_components (a mesh-name mapping),
clip_durations, duration_tolerance, and lod_mesh_names (for a combined GLB).
The fixed 24 bone and six clip names are checked even in inventory mode. Names
that have not yet been frozen are not guessed: contract_complete remains false.

Blender RNA properties were queried on the local Blender 4.5.14 LTS runtime.
GLB layout/accessors follow https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html.
This does not evaluate animated skin deformation, sole contact, or appearance.
"""

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import struct
import sys


BONE_NAMES = ["root", "pelvis", "spine", "belly", "neck", "head", "jaw", "tail"] + [
    f"{part}_{side}"
    for side in ("left", "right")
    for part in ("upper_arm", "forearm", "palm", "thigh", "shin", "foot", "eye", "brow")
]
CLIP_NAMES = ["idle", "walk", "chase", "warn", "charge", "recover"]
WEIGHT_TOLERANCE = 1e-4


def _check(report, name, passed, detail=None):
    report["checks"][name] = {"pass": bool(passed)}
    if detail is not None:
        report["checks"][name]["detail"] = detail


def _report(kind, source):
    return {
        "schema": "naifrog-inspection-v1", "kind": kind, "source": str(source),
        "checked_at": datetime.now(timezone.utc).isoformat(), "checks": {},
        "limitations": ["No animated deformation, foot contact, visual, or Godot acceptance."],
    }


def _finish(report, expected):
    required = ["mesh_names", "material_names", "shape_names"]
    report["unconfigured_contract_fields"] = [key for key in required if key not in expected]
    report["contract_complete"] = not report["unconfigured_contract_fields"]
    report["data_checks_pass"] = all(item["pass"] for item in report["checks"].values())
    report["ok"] = report["data_checks_pass"] and report["contract_complete"]
    report["status"] = "fail" if not report["data_checks_pass"] else "pass" if report["ok"] else "inventory"
    return report


def _names_check(report, expected, key, actual):
    if key in expected:
        _check(report, key, Counter(actual) == Counter(expected[key]), {"expected": expected[key], "actual": actual})


def _topology(vertex_count, edges, faces):
    """Count components and closed two-manifold edge/vertex fans on raw mesh data."""
    parent = list(range(vertex_count))

    def find(vertex):
        while parent[vertex] != vertex:
            parent[vertex] = parent[parent[vertex]]
            vertex = parent[vertex]
        return vertex

    def union(a, b):
        parent[find(a)] = find(b)

    edge_faces = defaultdict(list)
    vertex_faces = defaultdict(set)
    invalid_faces = 0
    face_counts = Counter()
    for face_index, face in enumerate(faces):
        if len(face) < 3 or len(set(face)) != len(face) or any(v < 0 or v >= vertex_count for v in face):
            invalid_faces += 1
            continue
        for vertex in face:
            vertex_faces[vertex].add(face_index)
        face_counts[tuple(sorted(face))] += 1
        for a, b in zip(face, face[1:] + face[:1]):
            edge_faces[tuple(sorted((a, b)))].append(face_index)
            union(a, b)
    raw_edges = Counter(tuple(sorted(edge)) for edge in edges)
    for a, b in raw_edges:
        union(a, b)
    component_sizes = sorted(Counter(find(v) for v in range(vertex_count)).values(), reverse=True)
    loose = [edge for edge in raw_edges if edge not in edge_faces]
    boundary = [edge for edge, adjacent in edge_faces.items() if len(adjacent) == 1]
    overused = [edge for edge, adjacent in edge_faces.items() if len(adjacent) > 2]
    fan_links = defaultdict(lambda: defaultdict(set))
    for (a, b), adjacent in edge_faces.items():
        if len(adjacent) == 2:
            left, right = adjacent
            for vertex in (a, b):
                fan_links[vertex][left].add(right)
                fan_links[vertex][right].add(left)
    bad_fans = 0
    isolated = 0
    for vertex in range(vertex_count):
        incident = vertex_faces[vertex]
        if not incident:
            isolated += 1
            continue
        pending = [next(iter(incident))]
        seen = set()
        while pending:
            face = pending.pop()
            if face not in seen:
                seen.add(face)
                pending.extend(fan_links[vertex][face] - seen)
        if seen != incident:
            bad_fans += 1
    duplicate_edges = sum(v - 1 for v in raw_edges.values())
    duplicate_faces = sum(v - 1 for v in face_counts.values())
    return {
        "vertices": vertex_count, "edges": len(edges), "faces": len(faces),
        "components": len(component_sizes), "component_vertex_counts": component_sizes,
        "boundary_edges": len(boundary), "edges_with_more_than_two_faces": len(overused),
        "loose_edges": len(loose), "duplicate_edges": duplicate_edges, "duplicate_faces": duplicate_faces,
        "isolated_vertices": isolated, "disconnected_vertex_fans": bad_fans,
        "invalid_faces": invalid_faces,
        "closed_manifold": bool(faces) and not any((boundary, overused, loose, isolated, bad_fans, invalid_faces, duplicate_edges, duplicate_faces)),
    }


def _tail_action_check(action, strip):
    curves = []
    for layer in action.layers:
        for keyframe_strip in layer.strips:
            for bag in keyframe_strip.channelbags:
                if bag.slot_handle == strip.action_slot_handle:
                    curves.extend(bag.fcurves)
    if not action.layers:
        curves = list(action.fcurves)
    failures = []
    for curve in curves:
        if not curve.data_path.startswith('pose.bones["tail"].'):
            continue
        prop = curve.data_path.rsplit(".", 1)[-1]
        neutral = 1.0 if prop == "scale" or (prop == "rotation_quaternion" and curve.array_index == 0) else 0.0
        for key in curve.keyframe_points:
            values = (key.co.y, key.handle_left.y, key.handle_right.y)
            if any(not math.isfinite(value) or abs(value - neutral) > 1e-6 for value in values):
                failures.append({"path": curve.data_path, "index": curve.array_index})
                break
    return failures


def inspect_blend(expected=None):
    import bpy  # Deliberately import only when running inside Blender.

    expected = expected or {}
    report = _report("blend", bpy.data.filepath)
    report["blender_version"] = bpy.app.version_string
    report["autoexec_disabled"] = not bpy.context.preferences.filepaths.use_scripts_auto_execute
    armatures = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    report["armatures"] = []
    all_bones = set()
    clips = []
    for rig in armatures:
        names = [bone.name for bone in rig.data.bones]
        all_bones.update(names)
        report["armatures"].append({"name": rig.name, "bone_names": names, "bone_count": len(names)})
        _check(report, f"bones:{rig.name}", len(names) == 24 and set(names) == set(BONE_NAMES), names)
        if rig.animation_data:
            for track in rig.animation_data.nla_tracks:
                for strip in track.strips:
                    action = strip.action
                    if action is None:
                        continue
                    actual_start, actual_end = map(float, action.curve_frame_range)
                    fps = bpy.context.scene.render.fps / bpy.context.scene.render.fps_base
                    clips.append({
                        "name": track.name, "strip_name": strip.name, "action": action.name,
                        "rig": rig.name, "action_frame_range": [actual_start, actual_end],
                        "action_duration": (actual_end - actual_start) / fps,
                        "nla_frame_range": [float(strip.frame_start), float(strip.frame_end)],
                        "nla_duration": float(strip.frame_end - strip.frame_start) / fps,
                        "muted": bool(track.mute), "fps": fps,
                    })
                    tail_failures = _tail_action_check(action, strip)
                    _check(report, f"tail_neutral_animation:{track.name}", not tail_failures, tail_failures)
    report["clips"] = clips
    _check(report, "armature_present", bool(armatures))
    _check(report, "six_clip_names", Counter(clip["name"] for clip in clips) == Counter(CLIP_NAMES))
    _duration_checks(report, expected, clips, "action_duration")
    report["meshes"] = []
    material_names = set()
    for obj in meshes:
        mesh = obj.data
        topology = _topology(len(mesh.vertices), [tuple(edge.vertices) for edge in mesh.edges],
                             [list(poly.vertices) for poly in mesh.polygons])
        uv_layers = []
        for layer in mesh.uv_layers:
            coords = [tuple(item.uv) for item in layer.data]
            uv_layers.append({"name": layer.name, "loop_count": len(coords),
                              "finite": all(math.isfinite(value) for uv in coords for value in uv)})
        bad_weights = 0
        max_influences = 0
        max_sum_error = 0.0
        tail_sum = 0.0
        unknown_groups = set()
        group_names = {group.index: group.name for group in obj.vertex_groups}
        for vertex in mesh.vertices:
            all_weights = [(group_names.get(group.group, "<missing>"), float(group.weight)) for group in vertex.groups]
            weights = [(name, weight) for name, weight in all_weights if weight > 0]
            maximum = len(weights)
            total = sum(weight for _, weight in weights)
            error = abs(total - 1.0)
            max_influences = max(max_influences, maximum)
            max_sum_error = max(max_sum_error, error)
            unknown_groups.update(name for name, _ in weights if name not in all_bones)
            tail_sum += sum(weight for name, weight in all_weights if name == "tail")
            if maximum > 4 or error > WEIGHT_TOLERANCE or not all(math.isfinite(w) and 0 <= w <= 1 for _, w in all_weights):
                bad_weights += 1
        shape_names = [key.name for key in mesh.shape_keys.key_blocks] if mesh.shape_keys else []
        mats = [material.name if material else None for material in mesh.materials]
        material_names.update(name for name in mats if name is not None)
        item = {
            "name": obj.name, "mesh_data_name": mesh.name, "topology": topology,
            "uv_layers": uv_layers, "material_names": mats, "shape_names": shape_names,
            "weights": {"bad_vertices": bad_weights, "max_influences": max_influences,
                        "max_sum_error": max_sum_error, "tail_weight_sum": tail_sum,
                        "unknown_positive_weight_groups": sorted(unknown_groups)},
        }
        report["meshes"].append(item)
        _check(report, f"closed_manifold:{obj.name}", topology["closed_manifold"])
        _check(report, f"finite_vertices:{obj.name}", all(math.isfinite(value) for vertex in mesh.vertices for value in vertex.co))
        target_components = expected.get("connected_components", {}).get(
            obj.name, 1 if obj.name.startswith("NaifrogContinuousSkin") else None)
        if target_components is not None:
            _check(report, f"components:{obj.name}", topology["components"] == target_components)
        _check(report, f"uv:{obj.name}", bool(uv_layers) and all(
            layer["finite"] and layer["loop_count"] == len(mesh.loops) for layer in uv_layers))
        _check(report, f"weights:{obj.name}", bad_weights == 0 and not unknown_groups)
        _check(report, f"tail_zero_weight:{obj.name}", tail_sum == 0.0)
        if obj.name in expected.get("shape_names", {}):
            wanted = expected["shape_names"][obj.name]
            _check(report, f"shape_order:{obj.name}", shape_names == ["Basis"] + wanted if wanted else shape_names in ([], ["Basis"]), shape_names)
    report["material_names"] = sorted(material_names)
    _check(report, "meshes_present", bool(meshes))
    _names_check(report, expected, "mesh_names", [obj.name for obj in meshes])
    _names_check(report, expected, "material_names", sorted(material_names))
    _check_shape_coverage(report, expected, [obj.name for obj in meshes])
    return _finish(report, expected)


def _duration_checks(report, expected, clips, field):
    tolerance = float(expected.get("duration_tolerance", 1e-4))
    for clip in clips:
        duration = clip[field]
        _check(report, f"positive_duration:{clip['name']}", math.isfinite(duration) and duration > 0, duration)
        if clip["name"] in expected.get("clip_durations", {}):
            target = float(expected["clip_durations"][clip["name"]])
            _check(report, f"duration:{clip['name']}", abs(duration - target) <= tolerance,
                   {"actual": duration, "expected": target, "tolerance": tolerance})


def _check_shape_coverage(report, expected, mesh_names):
    if "shape_names" in expected:
        missing = set(expected["shape_names"]) - set(mesh_names)
        uncovered = set(mesh_names) - set(expected["shape_names"])
        _check(report, "shape_contract_covers_all_meshes", not missing and not uncovered,
               {"missing_meshes": sorted(missing), "uncovered_meshes": sorted(uncovered)})


def _read_glb(path):
    raw = Path(path).read_bytes()
    if len(raw) < 20:
        raise ValueError("GLB is shorter than the header and first chunk")
    magic, version, length = struct.unpack_from("<4sII", raw)
    if magic != b"glTF" or version != 2 or length != len(raw):
        raise ValueError("GLB magic, version, or declared file length is invalid")
    chunks = []
    offset = 12
    while offset < len(raw):
        if offset + 8 > len(raw):
            raise ValueError("Truncated GLB chunk header")
        size, kind = struct.unpack_from("<II", raw, offset)
        offset += 8
        if size % 4 or offset + size > len(raw):
            raise ValueError("Unaligned or truncated GLB chunk")
        chunks.append((kind, raw[offset:offset + size]))
        offset += size
    if not chunks or chunks[0][0] != 0x4E4F534A:
        raise ValueError("The first GLB chunk must be JSON")
    if sum(kind == 0x4E4F534A for kind, _ in chunks) != 1 or sum(kind == 0x004E4942 for kind, _ in chunks) > 1:
        raise ValueError("Duplicate JSON or BIN chunk")
    document = json.loads(chunks[0][1].decode("utf-8"))
    binary = next((data for kind, data in chunks if kind == 0x004E4942), b"")
    return document, binary, hashlib.sha256(raw).hexdigest()


def _accessor(document, binary, index):
    accessor = document["accessors"][index]
    formats = {5120: ("b", 1), 5121: ("B", 1), 5122: ("h", 2), 5123: ("H", 2), 5125: ("I", 4), 5126: ("f", 4)}
    widths = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}
    code, size = formats[accessor["componentType"]]
    width = widths[accessor["type"]]
    count = accessor["count"]

    def rows(view_index, local_offset, row_count, row_code, row_size, row_width, allow_stride=True):
        view = document["bufferViews"][view_index]
        if view.get("buffer", 0) != 0:
            raise ValueError("Only the embedded GLB buffer is supported")
        element_size = row_size * row_width
        stride = view.get("byteStride", element_size) if allow_stride else element_size
        start = view.get("byteOffset", 0) + local_offset
        end = start if not row_count else start + (row_count - 1) * stride + element_size
        view_end = view.get("byteOffset", 0) + view["byteLength"]
        if stride < element_size or local_offset < 0 or end > view_end or end > len(binary):
            raise ValueError("Accessor exceeds its buffer view or BIN chunk")
        return [struct.unpack_from("<" + row_code * row_width, binary, start + row * stride) for row in range(row_count)]

    values = rows(accessor["bufferView"], accessor.get("byteOffset", 0), count, code, size, width) if "bufferView" in accessor else [(0,) * width for _ in range(count)]
    if "sparse" in accessor:
        sparse = accessor["sparse"]
        indices = sparse["indices"]
        index_code, index_size = formats[indices["componentType"]]
        locations = rows(indices["bufferView"], indices.get("byteOffset", 0), sparse["count"], index_code, index_size, 1, False)
        updates = rows(sparse["values"]["bufferView"], sparse["values"].get("byteOffset", 0), sparse["count"], code, size, width, False)
        last = -1
        for (location,), update in zip(locations, updates):
            if not last < location < count:
                raise ValueError("Sparse accessor indices are not strictly increasing and in range")
            values[location] = update
            last = location
    if accessor.get("normalized") and accessor["componentType"] != 5126:
        maximum = {5120: 127, 5121: 255, 5122: 32767, 5123: 65535, 5125: 4294967295}[accessor["componentType"]]
        values = [tuple(max(-1.0, value / maximum) for value in row) for row in values]
    return values


def _glb_weights(document, binary, attributes, skin_names):
    sets = sorted(key for key in attributes if key.startswith("WEIGHTS_"))
    if not sets or not skin_names:
        return {"valid": False, "reason": "Missing skin binding or weight attributes"}
    weighted_rows = []
    for key in sets:
        joint_key = "JOINTS_" + key.split("_", 1)[1]
        if joint_key not in attributes:
            return {"valid": False, "reason": f"Missing {joint_key}"}
        weights = _accessor(document, binary, attributes[key])
        joints = _accessor(document, binary, attributes[joint_key])
        if len(weights) != len(joints) or any(len(row) != 4 for row in weights + joints):
            return {"valid": False, "reason": "Weights and joints must be matching VEC4 rows"}
        weighted_rows.append((weights, joints))
    vertex_count = document["accessors"][attributes["POSITION"]]["count"]
    if any(len(weights) != vertex_count for weights, _ in weighted_rows):
        return {"valid": False, "reason": "Weight vertex count differs from POSITION"}
    bad = 0
    maximum = 0
    max_error = 0.0
    tail_sum = 0.0
    for vertex in range(vertex_count):
        pairs = [(weight, joint) for weights, joints in weighted_rows for weight, joint in zip(weights[vertex], joints[vertex])]
        positive = [(weight, joint) for weight, joint in pairs if weight > 0]
        maximum = max(maximum, len(positive))
        error = abs(sum(weight for weight, _ in pairs) - 1.0)
        max_error = max(max_error, error)
        valid = all(math.isfinite(weight) and 0 <= weight <= 1 and isinstance(joint, int)
                    and 0 <= joint < len(skin_names) for weight, joint in pairs)
        if not valid or len(positive) > 4 or error > WEIGHT_TOLERANCE:
            bad += 1
        if valid:
            tail_sum += sum(weight for weight, joint in pairs if skin_names[joint] == "tail")
    return {"valid": bad == 0 and tail_sum == 0.0, "bad_vertices": bad,
            "max_influences": maximum, "max_sum_error": max_error, "tail_weight_sum": tail_sum}


def inspect_glb(path, expected=None):
    expected = expected or {}
    report = _report("glb", Path(path).resolve())
    document, binary, report["sha256"] = _read_glb(path)
    nodes = document.get("nodes", [])
    meshes = document.get("meshes", [])
    animations = document.get("animations", [])
    report["asset"] = document.get("asset", {})
    report["node_names"] = [node.get("name") for node in nodes]
    report["material_names"] = [material.get("name") for material in document.get("materials", [])]
    report["extensions_used"] = document.get("extensionsUsed", [])
    _check(report, "gltf_version", document.get("asset", {}).get("version") == "2.0")
    _check(report, "readable_mesh_attributes", not any(
        name in document.get("extensionsRequired", []) for name in ("KHR_draco_mesh_compression", "EXT_meshopt_compression")))
    report["skins"] = []
    for index, skin in enumerate(document.get("skins", [])):
        joints = skin.get("joints", [])
        names = [nodes[joint].get("name") for joint in joints]
        report["skins"].append({"name": skin.get("name"), "joint_count": len(joints), "bone_names": names})
        _check(report, f"skin_24_bones:{index}", len(joints) == 24 and len(set(joints)) == 24 and set(names) == set(BONE_NAMES))
    _check(report, "skin_present", bool(report["skins"]))
    buffers = document.get("buffers", [])
    _check(report, "embedded_buffers", len(buffers) == 1 and "uri" not in buffers[0]
           and 0 <= len(binary) - buffers[0].get("byteLength", 0) <= 3)
    report["images"] = []
    for index, image in enumerate(document.get("images", [])):
        embedded = "bufferView" in image or image.get("uri", "").startswith("data:")
        valid_view = True
        if "bufferView" in image:
            view = document["bufferViews"][image["bufferView"]]
            valid_view = view.get("buffer", 0) == 0 and view.get("byteOffset", 0) + view["byteLength"] <= len(binary)
        report["images"].append({"name": image.get("name"), "mime_type": image.get("mimeType"), "embedded": embedded})
        _check(report, f"embedded_image:{index}", embedded and valid_view)
    report["meshes"] = []
    for mesh_index, mesh in enumerate(meshes):
        primitives = []
        target_names = mesh.get("extras", {}).get("targetNames", [])
        for primitive_index, primitive in enumerate(mesh.get("primitives", [])):
            attributes = primitive.get("attributes", {})
            position_count = document["accessors"][attributes["POSITION"]]["count"]
            count = document["accessors"][primitive["indices"]]["count"] if "indices" in primitive else position_count
            mode = primitive.get("mode", 4)
            triangles = count // 3 if mode == 4 else max(0, count - 2) if mode in (5, 6) else 0
            target_count = len(primitive.get("targets", []))
            prefix = f"mesh:{mesh_index}:primitive:{primitive_index}"
            _check(report, prefix + ":triangles", mode == 4 and count % 3 == 0 and count > 0)
            _check(report, prefix + ":morph_order", len(target_names) == target_count, {"names": target_names, "count": target_count})
            _check(report, prefix + ":morph_vertex_counts", all(
                document["accessors"][accessor]["count"] == position_count
                for target in primitive.get("targets", []) for accessor in target.values()))
            has_uv = "TEXCOORD_0" in attributes
            _check(report, prefix + ":uv", has_uv)
            if has_uv:
                uv = _accessor(document, binary, attributes["TEXCOORD_0"])
                _check(report, prefix + ":finite_uv", len(uv) == position_count and all(math.isfinite(x) for row in uv for x in row))
            bindings = {node["skin"] for node in nodes if node.get("mesh") == mesh_index and "skin" in node}
            weights = [_glb_weights(document, binary, attributes, report["skins"][skin]["bone_names"]) for skin in sorted(bindings)]
            _check(report, prefix + ":weights", bool(weights) and all(item["valid"] for item in weights), weights)
            primitives.append({"triangles": triangles, "vertices": position_count,
                               "material": report["material_names"][primitive["material"]] if "material" in primitive else None,
                               "morph_count": target_count, "attribute_names": sorted(attributes), "weights": weights})
        name = mesh.get("name")
        report["meshes"].append({"name": name, "shape_names": target_names,
                                "triangles": sum(item["triangles"] for item in primitives), "primitives": primitives})
        if name in expected.get("shape_names", {}):
            _check(report, f"shape_order:{name}", target_names == expected["shape_names"][name], target_names)
    _check(report, "meshes_present", bool(meshes))
    report["triangle_count"] = sum(mesh["triangles"] for mesh in report["meshes"])
    report["clips"] = []
    for animation in animations:
        seen = set()
        duplicates = []
        time_bounds = []
        morph_channels = 0
        for channel in animation.get("channels", []):
            target = channel["target"]
            identity = (target.get("node"), target.get("path"))
            if identity in seen:
                duplicates.append(identity)
            seen.add(identity)
            sampler = animation["samplers"][channel["sampler"]]
            times = [row[0] for row in _accessor(document, binary, sampler["input"])]
            if not times or not all(math.isfinite(t) for t in times) or any(a >= b for a, b in zip(times, times[1:])):
                raise ValueError("Animation times must be finite and strictly increasing")
            time_bounds.append((min(times), max(times)))
            node_index = target.get("node")
            if node_index is not None and nodes[node_index].get("name") == "tail" and target.get("path") in ("translation", "rotation", "scale"):
                values = _accessor(document, binary, sampler["output"])
                neutral_tangents = True
                if sampler.get("interpolation") == "CUBICSPLINE":
                    neutral_tangents = all(abs(component) <= 1e-6 for row in values[0::3] + values[2::3] for component in row)
                    values = values[1::3]
                static = neutral_tangents and bool(values) and all(all(abs(a - b) <= 1e-6 for a, b in zip(values[0], value)) for value in values)
                _check(report, f"tail_static_animation:{animation.get('name')}:{target['path']}", static)
            if target.get("path") == "weights":
                morph_channels += 1
                mesh_index = nodes[target["node"]]["mesh"]
                target_count = len(meshes[mesh_index].get("primitives", [{}])[0].get("targets", []))
                output_count = document["accessors"][sampler["output"]]["count"]
                multiplier = 3 if sampler.get("interpolation") == "CUBICSPLINE" else 1
                _check(report, f"morph_output_count:{animation.get('name')}:{target['node']}", output_count == len(times) * target_count * multiplier
                       and document["accessors"][sampler["output"]]["type"] == "SCALAR")
        start = min((bounds[0] for bounds in time_bounds), default=0.0)
        end = max((bounds[1] for bounds in time_bounds), default=0.0)
        name = animation.get("name")
        report["clips"].append({"name": name, "start": start, "end": end, "duration": end - start,
                                "channel_count": len(seen), "morph_channels": morph_channels,
                                "duplicate_target_paths": duplicates})
        _check(report, f"unique_target_paths:{name}", not duplicates, duplicates)
    _check(report, "six_clip_names", Counter(clip["name"] for clip in report["clips"]) == Counter(CLIP_NAMES))
    _duration_checks(report, expected, report["clips"], "duration")
    actual_mesh_names = [mesh.get("name") for mesh in meshes]
    _names_check(report, expected, "mesh_names", actual_mesh_names)
    _names_check(report, expected, "material_names", report["material_names"])
    _check_shape_coverage(report, expected, actual_mesh_names)
    if "lod_mesh_names" in expected:
        lods = expected["lod_mesh_names"]
        _check(report, "three_lod_groups", len(lods) == 3)
        _check(report, "lod_mesh_names", Counter(name for names in lods.values() for name in names) == Counter(actual_mesh_names))
        report["lod_triangle_counts"] = {lod: sum(mesh["triangles"] for mesh in report["meshes"] if mesh["name"] in names) for lod, names in lods.items()}
    return _finish(report, expected)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--blend-report", type=Path, help="Inspect the already opened Blender scene and write JSON")
    mode.add_argument("--glb", type=Path, nargs="+", help="Inspect one GLB, or the three separate LOD GLBs")
    parser.add_argument("--out", type=Path, help="JSON output for --glb")
    parser.add_argument("--expected-json", type=Path, help="Explicit frozen naming / shape / duration contract")
    args = parser.parse_args(argv)
    if args.glb and args.out is None:
        parser.error("--glb requires --out")
    output = args.blend_report or args.out
    try:
        expected = json.loads(args.expected_json.read_text()) if args.expected_json else {}
        if args.blend_report:
            report = inspect_blend(expected)
        elif len(args.glb) == 1:
            report = inspect_glb(args.glb[0], expected)
        else:
            reports = [inspect_glb(path, expected) for path in args.glb]
            report = _report("glb_lod_set", [str(path) for path in args.glb])
            report["lod_reports"] = reports
            report["triangle_counts"] = [item["triangle_count"] for item in reports]
            _check(report, "three_lod_files", len(reports) == 3)
            _check(report, "distinct_lod_files", len({path.resolve() for path in args.glb}) == len(args.glb))
            _check(report, "individual_data_checks", all(item["data_checks_pass"] for item in reports))
            _check(report, "same_part_names", all(Counter(mesh["name"] for mesh in item["meshes"]) == Counter(mesh["name"] for mesh in reports[0]["meshes"]) for item in reports[1:]))
            _check(report, "same_shape_order", all({mesh["name"]: mesh["shape_names"] for mesh in item["meshes"]} == {mesh["name"]: mesh["shape_names"] for mesh in reports[0]["meshes"]} for item in reports[1:]))
            _check(report, "same_material_names", all(Counter(item["material_names"]) == Counter(reports[0]["material_names"]) for item in reports[1:]))
            report = _finish(report, expected)
    except Exception as exc:
        report = _report("error", args.glb or "opened Blender scene")
        report.update({"ok": False, "data_checks_pass": False, "contract_complete": False, "status": "error",
                       "error_type": type(exc).__name__, "error": str(exc)})
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n")
    print(json.dumps({"report": str(output.resolve()), "status": report["status"], "ok": report["ok"]}))
    return 1 if not report["data_checks_pass"] else 0


if __name__ == "__main__":
    arguments = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    raise SystemExit(main(arguments))
