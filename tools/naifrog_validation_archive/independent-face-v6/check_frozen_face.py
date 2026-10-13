"""Read-only bounded SOURCE/GLB eye and mouth morph verification.

Run with Blender 4.5.14 --background --disable-autoexec --python-exit-code 1
SOURCE.blend --python this.py -- --manifest MANIFEST --glb GLB --out DIR.
Uses raw authored rest geometry, not skinned animation, lighting or rendering.
"""
import argparse
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import sys
import time
import numpy as np
import bpy

sys.path.insert(0, str(Path(__file__).parent))
from strict_triangles import AREA_EPS, LENGTH_EPS, clip_polygon, polygon_area, self_crossings, synthetic

YUP = np.array([[1.,0,0], [0,0,1.], [0,-1.,0]])
KEYS = ('Blink', 'Focus', 'Open')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def transform(points, matrix, vector=False):
    matrix = np.asarray(matrix)
    return np.einsum('ij,kj->ik',np.asarray(points),matrix[:3,:3]) + (0 if vector else matrix[:3,3])


def read_source():
    result = {}
    for obj in bpy.context.scene.objects:
        if obj.type != 'MESH' or not (obj.name.startswith('NaifrogContinuousSkin') or obj.name.startswith('NaifrogEyes_')):
            continue
        mesh = obj.data
        mesh.calc_loop_triangles()
        coords = np.empty((len(mesh.vertices), 3), dtype=np.float64)
        mesh.vertices.foreach_get('co', coords.ravel())
        basis = coords.copy()
        morphs = {}
        if mesh.shape_keys:
            mesh.shape_keys.key_blocks['Basis'].data.foreach_get('co', basis.ravel())
            for name in KEYS:
                if name in mesh.shape_keys.key_blocks:
                    key = np.empty_like(coords)
                    mesh.shape_keys.key_blocks[name].data.foreach_get('co', key.ravel())
                    morphs[name] = key-basis
        world = np.asarray(obj.matrix_world, dtype=float)
        basis = np.einsum('ij,kj->ik',transform(basis,world),YUP)
        morphs = {name:np.einsum('ij,kj->ik',transform(delta,world,vector=True),YUP) for name,delta in morphs.items()}
        if not np.all(np.isfinite(basis)) or not all(np.all(np.isfinite(delta)) for delta in morphs.values()):
            raise ValueError(f'{obj.name}: nonfinite source geometry')
        faces = np.asarray([tuple(tri.vertices) for tri in mesh.loop_triangles], dtype=int)
        poly = np.asarray([tri.polygon_index for tri in mesh.loop_triangles], dtype=int)
        attrs = {}
        for attr_name in ('NaiFrogFacialPatch', 'NaiFrogFacialSection'):
            attr = mesh.attributes.get(attr_name)
            if attr:
                if attr.domain != 'FACE' or attr.data_type != 'INT':
                    raise ValueError(f'{obj.name}/{attr_name} must be FACE INT')
                values = np.empty(len(mesh.polygons), dtype=np.int32)
                attr.data.foreach_get('value', values)
                attrs[attr_name] = values[poly]
        result[obj.name] = {'basis':basis, 'morphs':morphs, 'faces':faces, 'attrs':attrs,
                            'source_polygon_ids':poly, 'canonical_vertex_ids':np.arange(len(basis)),
                            'object':obj.name, 'space':'glTF global metres'}
    return result


def gltf_matrix(node):
    if 'matrix' in node:
        return np.asarray(node['matrix']).reshape(4,4).T
    x,y,z,w = node.get('rotation', [0,0,0,1])
    rot = np.array([[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
                    [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
                    [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]])
    matrix = np.eye(4)
    matrix[:3,:3] = rot@np.diag(node.get('scale',[1,1,1]))
    matrix[:3,3] = node.get('translation', [0,0,0])
    return matrix


def read_glb(path, parser_path):
    spec = importlib.util.spec_from_file_location('actual_naifrog_parser', parser_path)
    parser = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(parser)
    doc,binary,file_sha = parser._read_glb(path)
    parents = {child:i for i,node in enumerate(doc['nodes']) for child in node.get('children',[])}
    matrices = {}
    def world(i):
        if i not in matrices:
            matrices[i] = (world(parents[i]) if i in parents else np.eye(4))@gltf_matrix(doc['nodes'][i])
        return matrices[i]
    result = {}
    for i,node in enumerate(doc['nodes']):
        if 'mesh' not in node:
            continue
        name = node.get('name','')
        if not (name.startswith('NaifrogContinuousSkin') or name.startswith('NaifrogEyes_')):
            continue
        mesh = doc['meshes'][node['mesh']]
        names = mesh.get('extras',{}).get('targetNames',[])
        points,faces = [],[]
        morph_lists = {key:[] for key in KEYS}
        offset = 0
        for primitive in mesh['primitives']:
            if primitive.get('mode',4) != 4:
                raise ValueError('Only actual triangle primitives supported')
            basis = np.asarray(parser._accessor(doc,binary,primitive['attributes']['POSITION']))
            ids = np.asarray(parser._accessor(doc,binary,primitive['indices']),dtype=int).reshape(-1,3)
            points.append(transform(basis, world(i)))
            faces.append(ids+offset)
            for key in KEYS:
                if key in names:
                    target = primitive['targets'][names.index(key)]
                    delta = np.asarray(parser._accessor(doc,binary,target['POSITION'])) if 'POSITION' in target else np.zeros_like(basis)
                else:
                    delta = np.zeros_like(basis)
                morph_lists[key].append(transform(delta,world(i),vector=True))
            offset += len(basis)
        result[name] = {'basis':np.concatenate(points), 'faces':np.concatenate(faces),
                        'morphs':{key:np.concatenate(values) for key,values in morph_lists.items()},
                        'attrs':{}, 'object':name, 'space':'glTF global metres', 'sha256':file_sha}
    return result


def bind_glb_roi(glb, source):
    """Match export vertices to source coordinates/morphs, weld only true export duplicates."""
    scale = 1e-5
    buckets = {}
    for i,point in enumerate(source['basis']):
        buckets.setdefault(tuple(np.floor(point/scale).astype(int)),[]).append(i)
    ids = np.full(len(glb['basis']),-1,dtype=int)
    max_basis_error, max_delta_error = 0.,0.
    ambiguous_vertices=0
    source_deltas={key:source['morphs'].get(key) for key in KEYS}
    glb_deltas={key:glb['morphs'].get(key) for key in KEYS}
    for i,point in enumerate(glb['basis']):
        cell = np.floor(point/scale).astype(int)
        candidates = [v for delta in itertools.product((-1,0,1),repeat=3)
                        for v in buckets.get(tuple(cell+delta),[])]
        if not candidates:
            continue
        errors = np.linalg.norm(source['basis'][candidates]-point,axis=1)
        viable=[]
        for candidate,error in zip(candidates,errors):
            if error>1e-6:
                continue
            delta_error=max(float(np.linalg.norm((glb_deltas[key][i] if glb_deltas[key] is not None else 0)-(source_deltas[key][candidate] if source_deltas[key] is not None else 0))) for key in KEYS)
            if delta_error<=1e-6:
                viable.append((float(error),delta_error,candidate))
        if viable:
            if len(viable)>1:
                ambiguous_vertices+=1
            error,delta_error,best=min(viable)
            ids[i] = best
            max_basis_error=max(max_basis_error,error)
            max_delta_error=max(max_delta_error,delta_error)
    source_faces = {tuple(sorted(face)):i for i,face in enumerate(source['faces'])}
    face_source = np.array([source_faces.get(tuple(sorted(ids[face])),-1) if np.all(ids[face]>=0) else -1 for face in glb['faces']])
    for attr,values in source['attrs'].items():
        mapped = np.zeros(len(face_source), dtype=int)
        valid = face_source >= 0
        mapped[valid] = values[face_source[valid]]
        glb['attrs'][attr] = mapped
    # IDs remain unique for unmatched export vertices, so unrelated vertices are never made adjacent.
    ids[ids<0] = np.arange(len(ids))[ids<0]+len(source['basis'])
    glb['canonical_vertex_ids'] = ids
    report = {'matching_tolerance_m':1e-6, 'vertices':len(ids), 'matched_vertices':int(np.sum(ids<len(source['basis']))),
              'triangles':len(face_source), 'matched_triangles':int(np.sum(face_source>=0)),
              'max_basis_error_m':max_basis_error, 'max_morph_delta_error_m':max_delta_error,
              'ambiguous_source_identity_export_vertices':ambiguous_vertices,
              'ROI_source_triangles':int(np.sum(source['attrs'].get('NaiFrogFacialPatch',np.zeros(len(source['faces'])))>0)),
              'ROI_matched_export_triangles':int(np.sum(glb['attrs'].get('NaiFrogFacialPatch',np.zeros(len(face_source)))>0))}
    report['complete_same_topology_mapping'] = not ambiguous_vertices and report['matched_triangles'] == report['triangles'] and report['ROI_source_triangles'] == report['ROI_matched_export_triangles']
    return report


def areas_normals(vertices, faces):
    triangles=vertices[faces]
    cross=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0])
    areas=np.linalg.norm(cross,axis=1)*.5
    normals=cross/np.maximum(areas[:,None]*2,1e-30)
    return areas,normals


def cap_clearance(body_vertices, body_faces, cap_vertices, cap_faces, frame):
    """Minimum signed front gap over exact projected triangle intersections.

    Each planar height difference is affine, so its minimum occurs at a vertex
    of the projected overlap polygon. Socket backseal is excluded explicitly.
    Only actual front cap faces are included; no analytic ideal eye replaces it.
    """
    center=np.asarray(frame['center'])@YUP.T
    axes=np.asarray([frame['u'],frame['vertical'],frame['normal']])@YUP.T
    body=np.einsum('ij,kj->ik',body_vertices-center,axes)
    cap=np.einsum('ij,kj->ik',cap_vertices-center,axes)
    btris,ctris=body[body_faces],cap[cap_faces]
    # Front cap is an explicit closed-mesh subset: every corner at/forward of .004 m.
    cap_projected_area=np.abs(np.cross(ctris[:,1,:2]-ctris[:,0,:2],ctris[:,2,:2]-ctris[:,0,:2]))*.5
    cap_mask=np.all(ctris[:,:,2] >= .004-1e-6,axis=1)&(cap_projected_area>AREA_EPS)
    ctris=ctris[cap_mask]
    if not len(ctris):
        return {'status':'unconfigured','reason':'No actual cap triangles at/forward of .004m'}
    clo,chi=ctris[:,:,:2].min(axis=1),ctris[:,:,:2].max(axis=1)
    cs=[]
    for ct in ctris:
        mat=np.column_stack([ct[:,:2],np.ones(3)])
        cs.append(np.linalg.solve(mat,ct[:,2]))
    cs=np.asarray(cs)
    minimum=float('inf'); overlaps=0; negative=0; example=None
    for i,bt in enumerate(btris):
        mat=np.column_stack([bt[:,:2],np.ones(3)])
        if abs(np.linalg.det(mat)) <= AREA_EPS:
            continue
        bs=np.linalg.solve(mat,bt[:,2])
        lo,hi=bt[:,:2].min(axis=0),bt[:,:2].max(axis=0)
        candidates=np.flatnonzero(np.all(chi+LENGTH_EPS>=lo,axis=1)&np.all(clo-LENGTH_EPS<=hi,axis=1))
        for j in candidates:
            overlap=clip_polygon(bt[:,:2],ctris[j,:,:2],eps=AREA_EPS)
            if polygon_area(overlap) <= AREA_EPS:
                continue
            overlaps+=1
            p=np.column_stack([overlap,np.ones(len(overlap))])
            gap=float(np.min(p@(bs-cs[j])))
            if gap < -LENGTH_EPS: negative+=1
            if gap < minimum:
                minimum=gap; example={'body_subset_triangle':i,'cap_subset_triangle':int(j)}
    return {'status':'pass' if overlaps and minimum>=-LENGTH_EPS else 'fail' if overlaps else 'no_projected_area_overlap',
            'cap_triangles':len(ctris),'projected_overlap_triangle_pairs':overlaps,
            'minimum_signed_normal_gap_m':minimum if overlaps else None,'negative_gap_pairs':negative,
            'nonpenetrating_with_numeric_tolerance':bool(not overlaps or minimum>=-LENGTH_EPS),
            'nominal_3mm_margin_met':bool(overlaps and minimum>=.003-LENGTH_EPS),
            'minimum_example':example,'method':'exact affine height difference over projected polygon overlap; actual cap only; front annulus only'}


def check_dataset(dataset, frames):
    body_names=[name for name in dataset if name.startswith('NaifrogContinuousSkin')]
    if len(body_names)!=1:
        raise ValueError(f'Expected one Body, got {body_names}')
    body=dataset[body_names[0]]
    patch=body['attrs'].get('NaiFrogFacialPatch')
    section=body['attrs'].get('NaiFrogFacialSection')
    if patch is None:
        raise ValueError('Actual FACE INT NaiFrogFacialPatch required; no guessed spatial ROI')
    explicit_ids=np.flatnonzero(patch>0)
    explicit_vertices=set(body['faces'][explicit_ids].ravel().tolist())
    # Include the join's actual one-ring skin, where reparameterized outer vertices moved.
    roi_ids=np.array([i for i,face in enumerate(body['faces']) if patch[i]>0 or any(int(v) in explicit_vertices for v in face)],dtype=int)
    roi_faces=body['faces'][roi_ids]
    canonical_faces=body['canonical_vertex_ids'][roi_faces]
    # Canonical IDs affect adjacency only; keep exported positions for all computations.
    _,basis_normals=areas_normals(body['basis'],roi_faces)
    edge_faces={}
    for face_i,face in enumerate(canonical_faces):
        for a,b in zip(face,np.roll(face,-1)):
            edge_faces.setdefault(tuple(sorted((int(a),int(b)))),[]).append(face_i)
    normal_pairs=np.array([adj for adj in edge_faces.values() if len(adj)==2],dtype=int)
    basis_edge_angles=np.degrees(np.arccos(np.clip(np.einsum('ij,ij->i',basis_normals[normal_pairs[:,0]],basis_normals[normal_pairs[:,1]]),-1,1)))
    results=[]
    started=time.time()
    for blink,focus,opening in itertools.product((0.,.5,1.),repeat=3):
        values=dict(zip(KEYS,(blink,focus,opening)))
        vertices=body['basis'].copy()
        for key,value in values.items():
            if key in body['morphs']:
                vertices+=body['morphs'][key]*value
        areas,normals=areas_normals(vertices,roi_faces)
        dots=np.einsum('ij,ij->i',normals,basis_normals)
        edge_angles=np.degrees(np.arccos(np.clip(np.einsum('ij,ij->i',normals[normal_pairs[:,0]],normals[normal_pairs[:,1]]),-1,1)))
        added_sharp=(edge_angles>90)&((edge_angles-basis_edge_angles)>45)
        # Reindex geometry to canonical source ids for precise exported adjacency.
        from strict_triangles import candidate_pairs, strict_crossing
        triangles=vertices[roi_faces]
        adjacent,checked,failures=0,0,[]
        for i,j in candidate_pairs(triangles):
            if np.intersect1d(canonical_faces[i],canonical_faces[j]).size:
                adjacent+=1;continue
            checked+=1
            kind=strict_crossing(triangles[i],triangles[j])
            if kind:failures.append({'face_a':int(roi_ids[i]),'face_b':int(roi_ids[j]),'kind':kind,'patch_a':int(patch[roi_ids[i]]),'patch_b':int(patch[roi_ids[j]])})
        item={'values':values,'ROI_triangles':len(roi_ids),'candidate_nonneighbor_pairs':checked,'adjacent_pairs_excluded':adjacent,
              'strict_intersections':len(failures),'intersection_examples':failures[:30],
              'degenerate_triangles':int(np.sum(areas<=AREA_EPS)),'minimum_triangle_area_m2':float(areas.min()),
              'basis_normal_dot_min':float(dots.min()),'basis_normal_dot_negative_triangles':int(np.sum(dots<0)),
              'basis_normal_negative_examples':roi_ids[dots<0][:30].tolist(),'cap_clearance':{}}
        item['edge_normal_change']={'shared_edges':len(normal_pairs),'maximum_dihedral_degrees':float(edge_angles.max()),
                                    'basis_maximum_dihedral_degrees':float(basis_edge_angles.max()),
                                    'maximum_added_dihedral_degrees':float((edge_angles-basis_edge_angles).max()),
                                    'new_over_90deg_edges_added_over_45deg':int(np.sum(added_sharp)),
                                    'examples':roi_ids[normal_pairs[added_sharp]][:20].tolist(),
                                    'diagnostic_thresholds_only':'90 degree edge dihedral and 45 degree increase; reports, never filters crossing'}
        for side,patch_id in [('left',1),('right',2)]:
            eye_names=[name for name in dataset if name.startswith('NaifrogEyes_'+side)]
            if section is None or side not in frames or len(eye_names)!=1:
                item['cap_clearance'][side]={'status':'unconfigured','reason':'Need explicit front section, actual eye and frozen actual frame'}
                continue
            front_ids=np.flatnonzero((patch==patch_id)&(section==1))
            eye=dataset[eye_names[0]]
            item['cap_clearance'][side]=cap_clearance(vertices,body['faces'][front_ids],eye['basis'],eye['faces'],frames[side])
        item['strict_intersection_and_degeneracy_pass']=not failures and item['degenerate_triangles']==0
        results.append(item)
        print(json.dumps({'dataset':body_names[0],'state':values,'crossings':len(failures),'degenerate':item['degenerate_triangles'],'normal_flips':item['basis_normal_dot_negative_triangles'],'cap_status':{side:r['status'] for side,r in item['cap_clearance'].items()} }),flush=True)
    return {'body_object':body_names[0],'ROI_patch_labels':{'1':'left eye annulus plus backseal','2':'right eye annulus plus backseal','3':'mouth annulus plus oral cavity'},
            'ROI_triangle_count':len(roi_ids),'explicit_ROI_triangles':len(explicit_ids),'surrounding_one_ring_triangles':len(roi_ids)-len(explicit_ids),
            'ROI_patch_triangle_counts':{str(i):int(np.sum(patch==i)) for i in (1,2,3)},
            'state_grid':[0.,.5,1.],'states':results,'elapsed_seconds':time.time()-started,
            'strict_intersection_and_degeneracy_pass':all(item['strict_intersection_and_degeneracy_pass'] for item in results),
            'cap_clearance_pass':all(all(r.get('nonpenetrating_with_numeric_tolerance',False) for r in item['cap_clearance'].values()) for item in results)}


def main():
    args=sys.argv[sys.argv.index('--')+1:]
    p=argparse.ArgumentParser()
    p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--glb',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--parser',type=Path,default=Path('/Users/lpz/Documents/Happy_Dash_Forward/tools/naifrog_inspect.py'))
    a=p.parse_args(args)
    a.out.mkdir(parents=True,exist_ok=True)
    source_path=Path(bpy.data.filepath)
    initial={'source':sha(source_path),'glb':sha(a.glb),'manifest':sha(a.manifest),'parser':sha(a.parser)}
    manifest=json.loads(a.manifest.read_text())
    frames={item['side']:item for item in manifest['eye_envelopes']}
    aliases={'center':'frame_center','u':'frame_u','vertical':'frame_vertical','normal':'eye_normal'}
    frames={side:{**frame,**{key:frame[key] if key in frame else frame[alias] for key,alias in aliases.items()}} for side,frame in frames.items()}
    required=('center','u','vertical','normal')
    for side,frame in frames.items():
        if not all(key in frame for key in required):
            raise ValueError(f'Frozen manifest missing actual eye frame {side}/{required}')
    report={'schema':'naifrog-independent-face-geometry-v1','blender':bpy.app.version_string,
            'source':str(source_path),'glb':str(a.glb),'manifest':str(a.manifest),'initial_sha256':initial,
            'synthetic':synthetic(),'limits':['27 static raw authored Blink/Focus/Open combinations only; no skin/bone animation or continuous-time proof',
            'Only explicit FACE ROI; no global whole-character self-intersection proof',
            'Normals are geometric triangle normals relative to Basis; normal reversal is reported for manual interpretation',
            'Eye clearance is signed along frozen actual eye normal over projected actual front-cap/front-annulus triangle overlaps; not Euclidean margin']}
    if not report['synthetic']['pass']:
        raise AssertionError('Strict crossing synthetic must pass before reading model')
    source=read_source()
    glb=read_glb(a.glb,a.parser)
    body=[obj for name,obj in source.items() if name.startswith('NaifrogContinuousSkin')][0]
    report['GLB_ROI_mapping']={}
    for name,obj in glb.items():
        if name.startswith('NaifrogContinuousSkin'):
            report['GLB_ROI_mapping'][name]=bind_glb_roi(obj,body)
    report['SOURCE']=check_dataset(source,frames)
    report['GLB']=check_dataset(glb,frames)
    final={'source':sha(source_path),'glb':sha(a.glb),'manifest':sha(a.manifest),'parser':sha(a.parser)}
    report['final_sha256']=final
    report['frozen_input_bytes_unchanged']=initial==final
    report['strict_geometry_pass']=report['frozen_input_bytes_unchanged'] and report['SOURCE']['strict_intersection_and_degeneracy_pass'] and report['GLB']['strict_intersection_and_degeneracy_pass'] and all(r['complete_same_topology_mapping'] for r in report['GLB_ROI_mapping'].values())
    report['cap_clearance_pass']=report['SOURCE']['cap_clearance_pass'] and report['GLB']['cap_clearance_pass']
    output=a.out/'report.json'
    output.write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
    print(json.dumps({'report':str(output),'strict_geometry_pass':report['strict_geometry_pass'],'cap_clearance_pass':report['cap_clearance_pass']}),flush=True)


if __name__=='__main__':
    main()
