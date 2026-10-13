"""Small, anatomical surface refinements on the existing CC0 hand topology.

Called on the neutral hand after refinement/decimation and before skin posing.
Coordinates are metres: +Z follows the fingers, +Y faces the palm.  The left
hand is an X mirror.  No topology, UV, vertex-group, or object/rig changes occur.
The original MakeHuman nail beds remain the supporting geometry; they are not
replaced by floating fingernail meshes or a coating over the entire fingertip.
"""
import hashlib
import struct

import bpy
import numpy as np


def _unit(v):
    value = np.asarray(v, dtype=np.float64)
    return value / max(float(np.linalg.norm(value)), 1e-12)


def _smooth(value):
    value = np.clip(value, 0.0, 1.0)
    return value * value * (3.0 - 2.0 * value)


def _integrity(obj):
    """The complete UV and weight streams, including original vertex indices."""
    digest = hashlib.sha256()
    mesh = obj.data
    for group in obj.vertex_groups:
        digest.update(group.name.encode('utf8') + b'\0')
    for vertex in mesh.vertices:
        for item in vertex.groups:
            digest.update(struct.pack('<IIf', vertex.index, item.group, item.weight))
    for layer in mesh.uv_layers:
        values = np.empty(len(layer.data) * 2, dtype=np.float32)
        layer.data.foreach_get('uv', values)
        digest.update(values.tobytes())
    for poly in mesh.polygons:
        digest.update(np.asarray(poly.vertices, dtype=np.int32).tobytes())
    return digest.hexdigest()


def _material(name, color, roughness):
    material = bpy.data.materials.get(name)
    if material is None:
        material = bpy.data.materials.new(name)
        material.use_nodes = True
    material.diffuse_color = (*color, 1.0)
    shader = material.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*color, 1.0)
    shader.inputs['Roughness'].default_value = roughness
    shader.inputs['Metallic'].default_value = 0.0
    shader.inputs['IOR'].default_value = 1.46
    # These simple Principled values survive the existing glTF export route.
    return material


def _nail_frame(points, digit, support):
    root = np.asarray(points[2], dtype=np.float64)
    axis = _unit(np.asarray(points[3]) - root)
    # The CC0 thumb is opposed in the neutral pose. Its nail faces outward,
    # not toward the four fingers' common dorsal plane.
    outward = np.array((.86 if support else -.86, -.50, 0.0)) if digit == 1 else np.array((0.0, -1.0, 0.0))
    dorsal = _unit(outward - axis * np.dot(outward, axis))
    across = _unit(np.cross(axis, dorsal))
    length = float(np.linalg.norm(np.asarray(points[3]) - root))
    return root, axis, dorsal, across, length


def _nail_coordinates(co, root, axis, dorsal, across, length, half_width):
    delta = co - root
    longitudinal = np.sum(delta * axis, axis=1) / length
    lateral = np.sum(delta * across, axis=1)
    outward = np.sum(delta * dorsal, axis=1)
    # The rounded rectangle sits within the existing nail-bed area. The root
    # ends distally of the IP/DIP joint; no whole phalanx receives nail material.
    x = lateral / half_width
    y = (longitudinal - .704) / .257
    rounded = np.abs(x) ** 2.8 + np.abs(y) ** 2.8
    return longitudinal, lateral, outward, rounded


def _curve_distance(points, curve):
    """Distance to a sampled neutral-palm curve in the transverse/long axis."""
    result = np.full(len(points), np.inf)
    for a, b in zip(curve, curve[1:]):
        direction = b - a
        t = np.clip((np.sum((points - a) * direction, axis=1)) / max(np.sum(direction * direction), 1e-12), 0, 1)
        distance = np.linalg.norm(points - a - t[:, None] * direction, axis=1)
        result = np.minimum(result, distance)
    return result


def _bezier(control):
    t = np.linspace(0, 1, 48)[:, None]
    a, b, c, d = np.asarray(control, dtype=np.float64)
    return (1-t)**3*a + 3*(1-t)**2*t*b + 3*(1-t)*t*t*c + t**3*d


def refine_hand_surface(obj, joints, support, skin, high):
    """Refine existing nail beds and shallow creases; return a measured receipt."""
    mesh = obj.data
    integrity = _integrity(obj)
    co = np.empty(len(mesh.vertices) * 3, dtype=np.float64)
    normals = np.empty_like(co)
    mesh.vertices.foreach_get('co', co)
    mesh.vertices.foreach_get('normal', normals)
    co = co.reshape(-1, 3)
    normals = normals.reshape(-1, 3)
    displacement = np.zeros_like(co)
    centroids = np.empty(len(mesh.polygons) * 3, dtype=np.float64)
    polygon_normals = np.empty_like(centroids)
    mesh.polygons.foreach_get('center', centroids)
    mesh.polygons.foreach_get('normal', polygon_normals)
    centroids = centroids.reshape(-1, 3)
    polygon_normals = polygon_normals.reshape(-1, 3)
    polygon_areas = np.empty(len(mesh.polygons), dtype=np.float64)
    mesh.polygons.foreach_get('area', polygon_areas)
    # Restrained warm keratin: close to the existing skin hue, never white tips.
    plate = _material('Natural thin keratin nail plate', (.435, .276, .212), .42)
    edge = _material('Short warm nail free edge', (.50, .385, .295), .49)
    slots = []
    for material in (plate, edge):
        if material.name not in mesh.materials:
            mesh.materials.append(material)
        slots.append(mesh.materials.find(material.name))
    assignments = np.array([p.material_index for p in mesh.polygons], dtype=np.int32)
    nail_receipts = []
    left_tone = np.ones_like(co) * .5 if support else None
    nail_protection = np.zeros(len(co), dtype=bool)
    widths = {1: .0050, 2: .0045, 3: .0049, 4: .0044, 5: .0032}
    for digit in range(1, 6):
        frame = _nail_frame(joints[digit], digit, support)
        root, axis, dorsal, across, length = frame
        t, side, distance, shape = _nail_coordinates(co, *frame, widths[digit])
        facing = _smooth((np.sum(normals * dorsal, axis=1) - .24) / .50)
        front = _smooth((distance - .0015) / .002)
        mask = _smooth((1.0 - shape) / .22) * facing * front
        # The CC0 bed already has curvature. A very small central thickness
        # preserves it while blending continuously into the cuticle/side walls.
        lift = .00016 * mask * np.clip(1.0 - shape * .40, 0.0, 1.0)
        displacement += dorsal[None, :] * lift[:, None]
        nail_protection |= (shape < 1.24) & (distance > .001)
        ft, fs, fd, fshape = _nail_coordinates(centroids, *frame, widths[digit])
        select = (fshape < .91) & (fd > .002) & (np.sum(polygon_normals * dorsal, axis=1) > .32)
        # At most a 0.55 mm distal band, clipped to the nail plate itself.
        free = select & (ft > .94 - .00055 / length)
        if support:
            short_edge = mask * _smooth((t - (.94 - .00055 / length)) / (.0012 / length))
            plate_ratio = np.asarray((.435/.42, .276/.25, .212/.16))
            edge_ratio = np.asarray((.50/.42, .385/.25, .295/.16))
            left_tone += .5 * (mask[:,None] * (plate_ratio - 1)[None,:] + short_edge[:,None] * (edge_ratio - plate_ratio)[None,:])
        assignments[select] = slots[0]
        assignments[free] = slots[1]
        nail_receipts.append({
            'digit': digit,
            'plate_faces': int(np.count_nonzero(select & ~free)),
            'free_edge_faces': int(np.count_nonzero(free)),
            'lift_vertices': int(np.count_nonzero(lift > 1e-7)),
            'maximum_lift_mm': float(lift.max() * 1000),
            'dorsal_normal': dorsal.tolist(),
            'half_width_mm': widths[digit] * 1000,
            'plate_and_edge_area_mm2': float(np.sum(polygon_areas[select]) * 1e6),
        })

    crease_depth = np.zeros(len(co), dtype=np.float64)
    # Existing joint pads are retained. Fine surface creases are slightly
    # proximal to the marker and fade before the sides rather than carving a
    # circumferential groove through the finger.
    for digit in range(1, 6):
        points = [np.asarray(p, dtype=np.float64) for p in joints[digit]]
        for joint in (1, 2):
            axis = _unit(points[joint + 1] - points[joint - 1])
            palm = _unit(np.array((0, 1, 0)) - axis * axis[1])
            cross = _unit(np.cross(axis, palm))
            delta = co - points[joint]
            side = np.sum(delta * cross, axis=1)
            along = np.sum(delta * axis, axis=1)
            outward = np.sum(delta * palm, axis=1)
            radius = {1: .009, 2: .009, 3: .010, 4: .009, 5: .007}[digit]
            width_gate = _smooth((1 - np.abs(side) / radius) / .26)
            face_gate = _smooth((np.sum(normals * palm, axis=1) - .26) / .54) * _smooth((outward - .001) / .003)
            line = -.0013 + .0015 * (side / radius)**2
            depth = .00007 * np.exp(-((along - line) / .00075)**2) * width_gate * face_gate
            if digit == 1:
                depth *= .6
            crease_depth = np.maximum(crease_depth, depth)
    # Two principal palmar folds and the thenar fold. They are surface marks,
    # not substitutes for the metacarpal skeleton or the Hands01 volume targets.
    mirror = -1.0 if support else 1.0
    local = co[:, (0, 2)].copy()
    local[:, 0] *= mirror
    palm_gate = _smooth((normals[:, 1] - .32) / .54) * _smooth((co[:, 1] - .001) / .006)
    curves = [
        [(-.026,.080),(-.004,.073),(.017,.074),(.034,.073)],
        [(-.030,.068),(-.004,.063),(.011,.048),(.030,.044)],
        [(-.029,.069),(-.011,.062),(-.007,.036),(-.018,.023)],
    ]
    for control in curves:
        curve = _bezier(control)
        dist = _curve_distance(local, curve)
        # Gently tapered ends prevent puncture-like dots at the endpoints.
        taper = _smooth(np.linalg.norm(local-curve[0],axis=1)/.004) * _smooth(np.linalg.norm(local-curve[-1],axis=1)/.004)
        crease_depth = np.maximum(crease_depth, .000065 * np.exp(-(dist/.00065)**2) * palm_gate * taper)
    crease_depth[nail_protection] = 0
    displacement -= normals * crease_depth[:, None]
    assert np.isfinite(displacement).all(), 'non-finite hand surface displacement'
    amount = np.linalg.norm(displacement, axis=1)
    assert float(amount.max()) <= .00030, 'hand surface refinement exceeded 0.30 mm'
    mesh.vertices.foreach_set('co', (co + displacement).reshape(-1))
    mesh.polygons.foreach_set('material_index', assignments)
    mesh.update()
    if support:
        _left_continuous_nail_tone(obj, skin, left_tone)
    after = _integrity(obj)
    assert integrity == after, 'surface refinement changed topology, UVs, or weights'
    assert all(n['plate_faces'] > 0 for n in nail_receipts), 'a nail bed was not found'
    receipt = {
        'version': 1,
        'side': 'left' if support else 'right',
        'source_resolution': 'high' if high else 'runtime',
        'vertex_count_unchanged': len(mesh.vertices),
        'polygon_count_unchanged': len(mesh.polygons),
        'uv_topology_weights_sha256_before': integrity,
        'uv_topology_weights_sha256_after': after,
        'maximum_surface_displacement_mm': float(amount.max() * 1000),
        'maximum_crease_depth_mm': float(crease_depth.max() * 1000),
        'modified_vertices': int(np.count_nonzero(amount > 1e-7)),
        'nails': nail_receipts,
        'scope': 'neutral surface only; pose and in-engine appearance need separate inspection',
    }
    obj['hand_surface_detail_version'] = 1
    return receipt


def _left_continuous_nail_tone(obj, skin, coefficients):
    """Standard glTF COLOR_0 times a compensated diffuse map, left hand only.

    Material tags and nail-bed polygons stay intact for geometric inspection.
    All left-hand slots share the continuous pigment shader, avoiding hard
    polygon colour edges. The original right-hand materials are untouched.
    """
    import subprocess, shutil
    from pathlib import Path
    nodes = skin.node_tree.nodes
    shader = nodes.get('Principled BSDF')
    image_node = shader.inputs['Base Color'].links[0].from_node
    source = Path(bpy.path.abspath(image_node.image.filepath))
    destination = source.with_name(source.stem + '_left_nail_blend.png')
    if not destination.exists():
        runtime = shutil.which('ffmpeg')
        if not runtime:
            raise RuntimeError('ffmpeg is required only to regenerate the cached left nail diffuse map')
        linear = "(2*if(lte(val/255,0.04045),val/255/12.92,pow((val/255+0.055)/1.055,2.4)))"
        encoded = "(255*if(lte("+linear+",0.0031308),12.92*"+linear+",1.055*pow("+linear+",1/2.4)-0.055))"
        lookup = "lutrgb=r='"+encoded+"':g='"+encoded+"':b='"+encoded+"'"
        subprocess.run([runtime,'-hide_banner','-loglevel','error','-i',str(source),'-vf',lookup,'-frames:v','1','-update','1',str(destination)],check=True)
    diffuse = bpy.data.images.load(str(destination),check_existing=True)
    diffuse.colorspace_settings.name = 'sRGB'
    layer = obj.data.color_attributes.new(name='LeftNailBlend',type='FLOAT_COLOR',domain='CORNER')
    assert np.isfinite(coefficients).all() and coefficients.min()>=0 and coefficients.max()<=1
    loop_vertices = np.asarray([l.vertex_index for l in obj.data.loops],dtype=np.int32)
    values = np.ones((len(loop_vertices),4),dtype=np.float32)
    values[:,:3] = coefficients[loop_vertices]
    layer.data.foreach_set('color',values.reshape(-1))
    old = list(obj.data.materials)
    for slot, tag in enumerate(old):
        material = skin.copy()
        material.name = tag.name + ' left continuous pigment'
        tree = material.node_tree
        p = tree.nodes.get('Principled BSDF')
        base = p.inputs['Base Color'].links[0].from_node
        base.image = diffuse
        attribute = tree.nodes.new('ShaderNodeVertexColor')
        attribute.layer_name = layer.name
        multiply = tree.nodes.new('ShaderNodeMix')
        multiply.data_type = 'RGBA';multiply.blend_type = 'MULTIPLY'
        multiply.inputs[0].default_value = 1.0
        tree.links.new(base.outputs['Color'],multiply.inputs[6])
        tree.links.new(attribute.outputs['Color'],multiply.inputs[7])
        tree.links.new(multiply.outputs[2],p.inputs['Base Color'])
        obj.data.materials[slot] = material
    obj['left_nail_colour_transition'] = 'continuous neutral-vertex pigment including a 1.2 mm free-edge fade; glTF COLOR_0 multiplied with linearly compensated original diffuse; original nail polygons and normals preserved'
