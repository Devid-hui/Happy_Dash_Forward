"""Author UVs and two image maps on the high-detail continuous Naifrog skin.

Call before making LOD copies/decimating. Mesh copies keep the UV corner data;
reuse the returned material and images rather than copying those data-blocks.
color_field(Nx3 local coordinates) returns Nx4 linear RGBA. An optional
roughness_field returns N scalar values using the builder's existing masks.
No shape, palette, light, noise, normal map, or LOD is authored here.

The UV, EMIT bake, image save/pack and node APIs were checked against local
Blender 4.5.14 LTS RNA and the Blender 4.5 official manual:
https://docs.blender.org/manual/en/4.5/modeling/meshes/editing/uv.html
https://docs.blender.org/manual/en/4.5/render/cycles/baking.html
https://docs.blender.org/api/4.5/bpy.types.Image.html
"""

import hashlib
import math
from pathlib import Path
import struct


MATERIAL_NAME = "Naifrog skin / cream belly / olive extremities"
UV_NAME = "NaifrogUV"
UV_REGION_ATTRIBUTE = "NaiFrogUVRegion"
UV_REGION_NAMES = ("torso", "left eye front annulus", "right eye front annulus",
                   "mouth front annulus", "left arm", "right arm", "left leg", "right leg",
                   "left eye interior", "right eye interior", "mouth interior", "head_and_neck",
                   "left palm rear surface", "right palm rear surface")


def _field_values(coords, color_field, roughness_field):
    import numpy as np

    colors = np.asarray(color_field(coords), dtype=np.float32)
    if colors.shape != (len(coords), 4):
        raise ValueError("color_field must return Nx4 linear RGBA")
    if not np.isfinite(colors).all() or np.any(colors < 0) or np.any(colors > 1):
        raise ValueError("PNG base colors must be finite linear RGBA in [0, 1]")
    if not np.allclose(colors[:, 3], 1.0, atol=1e-6, rtol=0):
        raise ValueError("Continuous skin is opaque; color_field alpha must be 1")
    rough = np.full(len(coords), .60, dtype=np.float32) if roughness_field is None else np.asarray(roughness_field(coords), dtype=np.float32)
    if rough.shape != (len(coords),) or not np.isfinite(rough).all() or np.any(rough < 0) or np.any(rough > 1):
        raise ValueError("roughness_field must return N finite scalar values in [0, 1]")
    rough_rgba = np.column_stack((rough, rough, rough, np.ones(len(coords), dtype=np.float32)))
    return colors, rough, rough_rgba


def _uv_array_stats(uvs, triangles, epsilon=1e-14):
    import numpy as np

    uvs = np.asarray(uvs, dtype=np.float64)
    triangles = np.asarray(triangles, dtype=np.int32)
    if uvs.ndim != 2 or uvs.shape[1] != 2 or triangles.ndim != 2 or triangles.shape[1] != 3:
        raise ValueError("UV coordinates and triangle loop indices must be Nx2 and Mx3")
    if not len(uvs) or not len(triangles) or not np.isfinite(uvs).all():
        raise ValueError("UVs must be nonempty and finite")
    if np.any(triangles < 0) or np.any(triangles >= len(uvs)):
        raise ValueError("UV triangle contains an invalid corner index")
    a, b, c = (uvs[triangles[:, index]] for index in range(3))
    ab, ac = b - a, c - a
    signed = (ab[:, 0] * ac[:, 1] - ab[:, 1] * ac[:, 0]) * .5
    areas = np.abs(signed)
    low, high = uvs.min(axis=0), uvs.max(axis=0)
    return {
        "corner_count": int(len(uvs)), "triangle_count": int(len(triangles)),
        "finite": True, "range_min": low.tolist(), "range_max": high.tolist(),
        "in_unit_square": bool(np.all(low >= -1e-6) and np.all(high <= 1 + 1e-6)),
        "summed_triangle_area": float(areas.sum()), "min_triangle_area": float(areas.min()),
        "max_triangle_area": float(areas.max()), "zero_area_triangles": int(np.count_nonzero(areas <= epsilon)),
        "negative_orientation_triangles": int(np.count_nonzero(signed < -epsilon)),
        "area_epsilon": epsilon,
        "area_note": "Sum of UV triangle areas; does not certify island overlap or texture coverage.",
    }


def uv_stats(mesh, layer=None):
    """Read actual per-corner UVs and tessellated UV triangle areas."""
    import numpy as np

    layer_name = layer if isinstance(layer, str) else layer.name if layer is not None else mesh.uv_layers.active.name if mesh.uv_layers.active else None
    if layer_name is None:
        raise ValueError("Mesh has no UV layer")
    mesh.calc_loop_triangles()
    layer = mesh.uv_layers.get(layer_name)
    if layer is None:
        raise ValueError(f"Mesh has no UV layer named {layer_name}")
    uvs = np.empty(len(layer.data) * 2, dtype=np.float32)
    layer.data.foreach_get("uv", uvs)
    loops = np.empty(len(mesh.loop_triangles) * 3, dtype=np.int32)
    mesh.loop_triangles.foreach_get("loops", loops)
    report = _uv_array_stats(uvs.reshape(-1, 2), loops.reshape(-1, 3))
    report["layer"] = layer.name
    report["matches_mesh_corners"] = len(layer.data) == len(mesh.loops)
    return report


def _native_uv_atlas(bpy, skin, uv_name, has_regions, resolution, margin):
    """Operate in Edit Mode; separate tagged face regions before native packing."""
    import bmesh

    smart_options = {"angle_limit": math.radians(66), "margin_method": "FRACTION",
                     "island_margin": 2 * margin / resolution, "area_weight": 0.0,
                     "correct_aspect": True, "scale_to_bounds": True}
    if not has_regions:
        bpy.ops.mesh.select_all(action="SELECT")
        return bpy.ops.uv.smart_project(**smart_options), {"method": "single native Smart UV", "groups": []}
    bm = bmesh.from_edit_mesh(skin.data)
    region_layer = bm.faces.layers.int.get(UV_REGION_ATTRIBUTE)
    if region_layer is None:
        raise RuntimeError("FACE INT UV region layer did not survive Edit Mode entry")
    counts = {region: 0 for region in range(len(UV_REGION_NAMES))}
    for face in bm.faces:
        region = face[region_layer]
        if region not in counts:
            raise ValueError(f"Unsupported {UV_REGION_ATTRIBUTE} label: {region}")
        counts[region] += 1
    groups = []
    bpy.context.scene.tool_settings.mesh_select_mode = (False, False, True)
    bpy.context.scene.tool_settings.use_uv_select_sync = False
    for region, name in enumerate(UV_REGION_NAMES):
        groups.append({"id": region, "name": name, "face_count": counts[region],
                       "temporary_offset": [float(region * 3), 0.0]})
        if not counts[region]:
            continue
        bpy.ops.mesh.select_all(action="DESELECT")
        bm = bmesh.from_edit_mesh(skin.data)
        region_layer = bm.faces.layers.int.get(UV_REGION_ATTRIBUTE)
        for face in bm.faces:
            if face[region_layer] == region:
                face.select_set(True)
        bmesh.update_edit_mesh(skin.data, loop_triangles=False, destructive=False)
        result = bpy.ops.uv.smart_project(**smart_options)
        if "FINISHED" not in result:
            raise RuntimeError(f"Native Smart UV failed for region {region}: {result}")
        bm = bmesh.from_edit_mesh(skin.data)
        region_layer = bm.faces.layers.int.get(UV_REGION_ATTRIBUTE)
        uv_layer = bm.loops.layers.uv.get(uv_name)
        if uv_layer is None:
            raise RuntimeError(f"UV layer disappeared while authoring region {region}")
        for face in bm.faces:
            if face[region_layer] == region:
                for loop in face.loops:
                    loop[uv_layer].uv.x += region * 3.0
        bmesh.update_edit_mesh(skin.data, loop_triangles=False, destructive=False)
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.select_all(action="SELECT")
    # ACTIVE_UDIM targets the single 0..1 atlas instead of the temporary tiles.
    # AABB packs conservative island bounds; never merge overlapping islands.
    pack_options = {"udim_source": "ACTIVE_UDIM", "rotate": True, "rotate_method": "CARDINAL",
                    "scale": True, "merge_overlap": False, "margin_method": "FRACTION",
                    "margin": 2 * margin / resolution, "pin": False, "shape_method": "AABB"}
    result = bpy.ops.uv.pack_islands(**pack_options)
    return result, {"method": "region Smart UV, separated temporary offsets, native AABB pack",
                    "region_attribute": UV_REGION_ATTRIBUTE, "groups": groups, "pack_options": pack_options}


def _region_uv_stats(mesh, uv_name, atlas):
    import numpy as np

    if not atlas["groups"]:
        return
    regions = mesh.attributes.get(UV_REGION_ATTRIBUTE)
    if regions is None:
        raise RuntimeError("UV face region attribute disappeared after Object Mode return")
    labels = np.empty(len(mesh.polygons), dtype=np.int32)
    regions.data.foreach_get("value", labels)
    polygon_indices = np.empty(len(mesh.loop_triangles), dtype=np.int32)
    mesh.loop_triangles.foreach_get("polygon_index", polygon_indices)
    loops = np.empty(len(mesh.loop_triangles) * 3, dtype=np.int32)
    mesh.loop_triangles.foreach_get("loops", loops)
    loops = loops.reshape(-1, 3)
    layer = mesh.uv_layers.get(uv_name)
    uvs = np.empty(len(layer.data) * 2, dtype=np.float32)
    layer.data.foreach_get("uv", uvs)
    uvs = uvs.reshape(-1, 2)
    for group in atlas["groups"]:
        count = int(np.count_nonzero(labels == group["id"]))
        if count != group["face_count"]:
            raise RuntimeError(f"UV face count changed for region {group['id']}: {group['face_count']} -> {count}")
        selected = labels[polygon_indices] == group["id"]
        if not np.any(selected):
            group["uv_stats"] = None
            continue
        group_uvs = uvs[loops[selected]].reshape(-1, 2)
        indices = np.arange(len(group_uvs), dtype=np.int32).reshape(-1, 3)
        stats = _uv_array_stats(group_uvs, indices)
        stats["triangle_corner_count"] = stats.pop("corner_count")
        group["uv_stats"] = stats


def _png_receipt(path, resolution):
    data = path.read_bytes()
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise RuntimeError(f"Image save did not produce a PNG: {path}")
    width, height = struct.unpack_from(">II", data, 16)
    if (width, height) != (resolution, resolution):
        raise RuntimeError(f"Saved PNG has unexpected dimensions: {width}x{height}")
    return {"path": str(path), "width": width, "height": height, "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest()}


def _image_map(bpy, skin, bake_material, field, name, path, resolution, margin, blend_directory):
    mesh = skin.data
    attribute = mesh.color_attributes.new(name=f"Naifrog temporary {name}", type="FLOAT_COLOR", domain="POINT")
    attribute_name = attribute.name
    attribute.data.foreach_set("color", field.ravel())
    image = bpy.data.images.new(name=f"Naifrog {name}", width=resolution, height=resolution,
                                alpha=True, float_buffer=False, is_data=name == "roughness")
    image.colorspace_settings.name = "Non-Color" if name == "roughness" else "sRGB"
    temporary_path = path.with_name(f".{path.stem}.bake-tmp.png")
    try:
        nodes = bake_material.node_tree.nodes
        nodes.clear()
        source = nodes.new("ShaderNodeVertexColor")
        source.layer_name = attribute_name
        emission = nodes.new("ShaderNodeEmission")
        emission.inputs["Strength"].default_value = 1.0
        output = nodes.new("ShaderNodeOutputMaterial")
        target = nodes.new("ShaderNodeTexImage")
        target.image = image
        bake_material.node_tree.links.new(source.outputs["Color"], emission.inputs["Color"])
        bake_material.node_tree.links.new(emission.outputs["Emission"], output.inputs["Surface"])
        for node in nodes:
            node.select = False
        target.select = True
        nodes.active = target
        result = bpy.ops.object.bake(type="EMIT", target="IMAGE_TEXTURES", use_clear=True,
                                     use_selected_to_active=False, margin=margin, margin_type="EXTEND",
                                     save_mode="INTERNAL", uv_layer=mesh.uv_layers.active.name)
        if "FINISHED" not in result:
            raise RuntimeError(f"Cycles EMIT bake did not finish for {name}: {result}")
        image.file_format = "PNG"
        image.filepath_raw = str(temporary_path)
        image.save()
        receipt = _png_receipt(temporary_path, resolution)
        temporary_path.replace(path)
        receipt["path"] = str(path)
        image.filepath_raw = str(path)
        image.pack()
        if image.packed_file is None:
            raise RuntimeError(f"PNG was not packed: {path}")
        image.filepath_raw = bpy.path.relpath(str(path), start=str(blend_directory))
        receipt.update({"relative_path": image.filepath_raw, "packed": True,
                        "color_space": image.colorspace_settings.name, "bake": "Cycles CPU EMIT"})
        return image, receipt
    except Exception:
        bpy.data.images.remove(image)
        raise
    finally:
        attribute = skin.data.color_attributes.get(attribute_name)
        if attribute is not None:
            skin.data.color_attributes.remove(attribute)
        if temporary_path.exists():
            temporary_path.unlink()


def _final_material(bpy, uv_name, basecolor, roughness):
    material = bpy.data.materials.get(MATERIAL_NAME) or bpy.data.materials.new(MATERIAL_NAME)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    nodes.clear()
    uv = nodes.new("ShaderNodeUVMap")
    uv.uv_map = uv_name
    base = nodes.new("ShaderNodeTexImage")
    base.name = "Naifrog Base Color"
    base.image = basecolor
    rough = nodes.new("ShaderNodeTexImage")
    rough.name = "Naifrog Roughness"
    rough.image = roughness
    principled = nodes.new("ShaderNodeBsdfPrincipled")
    output = nodes.new("ShaderNodeOutputMaterial")
    material.node_tree.links.new(uv.outputs["UV"], base.inputs["Vector"])
    material.node_tree.links.new(uv.outputs["UV"], rough.inputs["Vector"])
    material.node_tree.links.new(base.outputs["Color"], principled.inputs["Base Color"])
    material.node_tree.links.new(rough.outputs["Color"], principled.inputs["Roughness"])
    material.node_tree.links.new(principled.outputs["BSDF"], output.inputs["Surface"])
    return material


def author_uv_and_maps(skin, texture_directory, color_field, resolution=4096, *,
                       roughness_field=None, blend_directory=None):
    """Return live material/images plus a JSON-safe report after native UV/bakes.

    blend_directory is required for an unsaved scene, and must be the final
    source .blend parent directory. A saved scene defaults to its current parent.
    Local coordinates passed to both fields are identical; caller-owned masks
    determine color and roughness. On failure, restore material slots/selection
    and remove the new UV layer. Successful final skin exports no COLOR_0.
    The returned report is an authoring receipt, not model acceptance.
    """
    import bpy
    import numpy as np

    if skin.type != "MESH" or skin.mode != "OBJECT" or not len(skin.data.polygons):
        raise ValueError("skin must be a nonempty mesh in Object Mode")
    active = bpy.context.view_layer.objects.active
    if active is not None and active.mode != "OBJECT":
        raise ValueError("UV authoring requires the active object to start in Object Mode")
    if not isinstance(resolution, int) or not 64 <= resolution <= 16384:
        raise ValueError("resolution must be an integer from 64 to 16384")
    if blend_directory is None:
        if not bpy.data.filepath:
            raise ValueError("Unsaved scene requires the final blend_directory for relative image paths")
        blend_directory = Path(bpy.data.filepath).parent
    blend_directory = Path(blend_directory).expanduser().resolve()
    texture_directory = Path(texture_directory).expanduser().resolve()
    mesh = skin.data
    region_attribute = mesh.attributes.get(UV_REGION_ATTRIBUTE)
    has_regions = region_attribute is not None
    if has_regions and (region_attribute.domain != "FACE" or region_attribute.data_type != "INT"):
        raise ValueError(f"{UV_REGION_ATTRIBUTE} must be FACE INT")
    pre_vertex_count = len(mesh.vertices)
    coords = np.empty(len(mesh.vertices) * 3, dtype=np.float32)
    mesh.vertices.foreach_get("co", coords)
    coords = coords.reshape(-1, 3)
    if not np.isfinite(coords).all():
        raise ValueError("Skin vertices contain nonfinite coordinates")
    pre_coords = coords.copy()
    colors, rough_values, rough_rgba = _field_values(coords, color_field, roughness_field)
    texture_directory.mkdir(parents=True, exist_ok=True)
    scene = bpy.context.scene
    old_selection = list(bpy.context.selected_objects)
    old_materials = list(mesh.materials)
    old_material_indices = np.empty(len(mesh.polygons), dtype=np.int32)
    mesh.polygons.foreach_get("material_index", old_material_indices)
    old_uv_name = mesh.uv_layers.active.name if mesh.uv_layers.active else None
    old_mesh_select_mode = tuple(scene.tool_settings.mesh_select_mode)
    old_uv_select_sync = scene.tool_settings.use_uv_select_sync
    old_engine, old_device, old_samples = scene.render.engine, scene.cycles.device, scene.cycles.samples
    bake_material = bpy.data.materials.new("Naifrog temporary EMIT bake")
    bake_material.use_nodes = True
    new_uv_name = None
    images = {}
    committed = False
    try:
        for obj in old_selection:
            obj.select_set(False)
        skin.select_set(True)
        bpy.context.view_layer.objects.active = skin
        new_uv = mesh.uv_layers.new(name=UV_NAME)
        new_uv_name = new_uv.name
        mesh.uv_layers.active = new_uv
        new_uv.active_render = True
        bpy.ops.object.mode_set(mode="EDIT")
        margin = max(2, round(resolution / 256))
        result, atlas = _native_uv_atlas(bpy, skin, new_uv_name, has_regions, resolution, margin)
        bpy.ops.object.mode_set(mode="OBJECT")
        # Edit-mode exit rebuilds Mesh CustomData; layer RNA pointers from before
        # the mode switch are invalid even if their Python wrappers still exist.
        mesh = skin.data
        new_uv = mesh.uv_layers.get(new_uv_name)
        if new_uv is None:
            raise RuntimeError(f"Native UV layer disappeared after mode switch: {new_uv_name}")
        mesh.uv_layers.active = new_uv
        new_uv.active_render = True
        if "FINISHED" not in result:
            raise RuntimeError(f"Native Smart UV did not finish: {result}")
        post_vertex_count = len(mesh.vertices)
        if post_vertex_count != pre_vertex_count:
            raise RuntimeError(f"Native UV changed vertex count: {pre_vertex_count} -> {post_vertex_count}")
        coords = np.empty(post_vertex_count * 3, dtype=np.float32)
        mesh.vertices.foreach_get("co", coords)
        coords = coords.reshape(-1, 3)
        if not np.isfinite(coords).all():
            raise ValueError("Skin vertices contain nonfinite coordinates after UV authoring")
        coordinate_rows_identical = bool(np.array_equal(pre_coords, coords))
        max_coordinate_row_difference = float(np.max(np.abs(pre_coords - coords)))
        # Bake fields must follow the current Mesh point order, not the order
        # captured before Edit Mode rebuilt the mesh and its point attributes.
        colors, rough_values, rough_rgba = _field_values(coords, color_field, roughness_field)
        stats = uv_stats(mesh, new_uv_name)
        if not stats["matches_mesh_corners"] or not stats["in_unit_square"] or stats["zero_area_triangles"]:
            raise RuntimeError(f"Native UV failed nondegenerate/finite/corner/range checks: {stats}")
        _region_uv_stats(mesh, new_uv_name, atlas)
        mesh.materials.clear()
        mesh.materials.append(bake_material)
        mesh.polygons.foreach_set("material_index", np.zeros(len(mesh.polygons), dtype=np.int32))
        scene.render.engine = "CYCLES"
        scene.cycles.device = "CPU"
        scene.cycles.samples = 1
        receipts = {}
        for name, field in (("basecolor", colors), ("roughness", rough_rgba)):
            images[name], receipts[name] = _image_map(bpy, skin, bake_material, field, name,
                texture_directory / f"naifrog_{name}.png", resolution, margin, blend_directory)
        for layer_name in [layer.name for layer in mesh.uv_layers]:
            if layer_name != new_uv_name:
                mesh.uv_layers.remove(mesh.uv_layers.get(layer_name))
        new_uv = mesh.uv_layers.get(new_uv_name)
        new_uv.name = UV_NAME
        new_uv_name = new_uv.name
        new_uv.active_render = True
        material = _final_material(bpy, new_uv_name, images["basecolor"], images["roughness"])
        mesh.materials.clear()
        mesh.materials.append(material)
        removed_colors = [attribute.name for attribute in mesh.color_attributes]
        for attribute_name in removed_colors:
            mesh.color_attributes.remove(mesh.color_attributes.get(attribute_name))
        committed = True
        stats["layer"] = new_uv_name
        report = {
            "method": "Native Smart UV followed by Cycles CPU EMIT", "blender": bpy.app.version_string,
            "uv": stats, "atlas": atlas, "resolution": resolution, "bake_margin_pixels": margin, "maps": receipts,
            "point_order_check": {"pre_vertices": pre_vertex_count, "post_vertices": post_vertex_count,
                                  "coordinate_rows_identical": coordinate_rows_identical,
                                  "max_abs_coordinate_row_difference": max_coordinate_row_difference,
                                  "bake_field_source": "Re-read coordinates and re-evaluated callbacks after Object Mode return"},
            "material_name": material.name, "removed_color_attributes": removed_colors,
            "roughness_min": float(rough_values.min()), "roughness_max": float(rough_values.max()),
            "roughness_source": "caller semantic field" if roughness_field is not None else "constant .60; no regional field supplied",
            "normal_map": None, "normal_map_reason": "Omitted in this stage; actual mesh normals remain, with no noise-derived detail.",
            "lod_rule": "Create/decimate LODs after UV authoring; share these material/image data-blocks.",
            "acceptance": "Authoring receipt only; not a model, texture fidelity, LOD, or Godot acceptance.",
        }
        return {"material": material, "images": images,
                "maps": {name: receipt["path"] for name, receipt in receipts.items()},
                "uv_stats": stats, "report": report}
    finally:
        if skin.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        mesh = skin.data
        if not committed:
            mesh.materials.clear()
            for material in old_materials:
                mesh.materials.append(material)
            mesh.polygons.foreach_set("material_index", old_material_indices)
            new_uv = mesh.uv_layers.get(new_uv_name) if new_uv_name else None
            if new_uv is not None:
                mesh.uv_layers.remove(new_uv)
            old_uv = mesh.uv_layers.get(old_uv_name) if old_uv_name else None
            if old_uv is not None:
                mesh.uv_layers.active = old_uv
            for image in images.values():
                bpy.data.images.remove(image)
        bpy.data.materials.remove(bake_material)
        scene.render.engine, scene.cycles.device, scene.cycles.samples = old_engine, old_device, old_samples
        scene.tool_settings.mesh_select_mode = old_mesh_select_mode
        scene.tool_settings.use_uv_select_sync = old_uv_select_sync
        skin.select_set(False)
        for obj in old_selection:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = active
