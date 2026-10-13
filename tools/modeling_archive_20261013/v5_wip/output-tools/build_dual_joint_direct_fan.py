"""Isolated c3-to-two-eye builder; requires the independently fixed-eye PASS.

This file does not touch production tools/assets or the frozen v3 source.
Body vertices, original expression arrays, weights and all six actions survive.
Only measured front/back eye-region polygons are removed from the Body, and
the local patches retain real annular connectivity with a CDT bridge.
"""
from pathlib import Path
import bpy, bmesh, hashlib, importlib.util, json
import numpy as np

ROOT=Path(__file__).resolve().parent
WORK=ROOT.parents[1]/'work/nailong/face-topology-v5'
SOURCE=WORK/'source-v3-stable.blend'

def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

def coords(key):
    values=np.empty(len(key.data)*3,dtype=np.float32)
    key.data.foreach_get('co',values)
    return values.reshape(-1,3)

def inspect_side(skin,manifest,side):
    mesh=skin.data;points=coords(mesh.shape_keys.key_blocks['Basis'])
    loop=np.empty(len(mesh.loops),dtype=np.int32);mesh.loops.foreach_get('vertex_index',loop)
    faces=loop.reshape(-1,3)
    center=np.asarray(manifest['face_helper']['measured_eyes'][side]['center'])
    centroids=points[faces].mean(axis=1);dz=centroids[:,2]-center[2]
    q=((centroids[:,0]-center[0])/.275)**2+(dz/np.where(dz>=0,.24,.22))**2
    indices=np.flatnonzero((q<1)&(centroids[:,1]>.55));selected=faces[indices]
    parent=np.arange(len(indices))
    def find(index):
        while parent[index]!=index:
            parent[index]=parent[parent[index]];index=parent[index]
        return index
    edges=np.sort(np.concatenate([selected[:,[0,1]],selected[:,[1,2]],selected[:,[2,0]]]),axis=1)
    owners=np.tile(np.arange(len(indices)),3)
    codes=edges[:,0].astype(np.int64)*len(points)+edges[:,1];order=np.argsort(codes)
    for a,b in zip(order[:-1],order[1:]):
        if codes[a]==codes[b]:
            a,b=find(int(owners[a])),find(int(owners[b]))
            if a!=b:parent[b]=a
    components={}
    for i in range(len(indices)):components.setdefault(find(i),[]).append(i)
    reports=[]
    for label,members in components.items():
        tris=selected[members]
        edge=np.sort(np.concatenate([tris[:,[0,1]],tris[:,[1,2]],tris[:,[2,0]]]),axis=1)
        unique,count=np.unique(edge,axis=0,return_counts=True);boundary=unique[count==1]
        degree={}
        for a,b in boundary:
            degree[int(a)]=degree.get(int(a),0)+1;degree[int(b)]=degree.get(int(b),0)+1
        bad=[index for index,n in degree.items() if n!=2]
        loops=[] if bad else module.boundary_loops(tris)
        p=points[tris];normal=np.cross(p[:,1]-p[:,0],p[:,2]-p[:,0])
        reports.append({'label':int(label),'body_face_indices':indices[members].tolist(),
            'triangle_normal_y_median':float(np.median(normal[:,1]/np.maximum(np.linalg.norm(normal,axis=1),1e-30))),
            'boundary_loops':[{'source_vertex_ids':loop,'vertices':len(loop)} for loop in loops],
            'non_manifold_boundary_vertices':bad})
    reports.sort(key=lambda item:len(item['body_face_indices']),reverse=True)
    return {'side':side,'components':reports,'source_face_index_domain':'c3 post-mouth-cleanup Body'}

def original_contract(rig,skin):
    def actions(actor):
        result={}
        for block in [actor,getattr(actor.data,'shape_keys',None)]:
            if block is None or not block.animation_data:continue
            for track in block.animation_data.nla_tracks:
                for strip in track.strips:
                    result[(track.name,strip.action.name)]=[(f.data_path,f.array_index,
                        [(tuple(p.co),p.interpolation) for p in f.keyframe_points]) for f in strip.action.fcurves]
        return result
    return {'body_keys':{k.name:coords(k) for k in skin.data.shape_keys.key_blocks},
            'weights':[[tuple((g.group,g.weight)) for g in v.groups] for v in skin.data.vertices],
            'bone_rest':[(b.name,tuple(v for row in b.matrix_local for v in row)) for b in rig.data.bones],
            'rig_actions':actions(rig),'body_actions':actions(skin)}

def add_open_tracks(obj,body):
    keys=obj.data.shape_keys;reference=body.data.shape_keys.animation_data
    source={t.name:t.strips[0].action for t in reference.nla_tracks}
    for track in keys.animation_data.nla_tracks:
        action=track.strips[0].action;keys.animation_data.action=action
        curve=next(f for f in source[track.name].fcurves if 'key_blocks["Open"]' in f.data_path)
        grid_curve=next(f for f in action.fcurves if 'key_blocks[\"Open\"]' not in f.data_path)
        for point in grid_curve.keyframe_points:
            keys.key_blocks['Open'].value=float(curve.evaluate(float(point.co.x)))
            keys.key_blocks['Open'].keyframe_insert('value',frame=float(point.co.x))
        new=next(f for f in action.fcurves if 'key_blocks["Open"]' in f.data_path)
        for point in new.keyframe_points:point.interpolation='LINEAR'
        keys.animation_data.action=None

def main():
    receipt=json.loads((ROOT/'shared-cdt-fixed-review.json').read_text())
    if receipt.get('status')!='completed' or not receipt.get('PASS_conditions') or not all(receipt['PASS_conditions'].values()):
        raise RuntimeError('Fixed single-eye review must explicitly PASS before expansion: '+str(receipt.get('status')))
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE),load_ui=False)
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()=='c3f08b4b01489b5cc548aac7f23717338d24819fbb0e514706d59986bfa6be8c'
    rig=bpy.data.objects['NailongRig'];skin=bpy.data.objects['NailongSkin_Reconstructed'];mesh=skin.data
    manifest=json.loads((WORK/'V3_MODEL_MANIFEST.json').read_text())
    for actor in list(bpy.context.scene.objects):
        for block in [actor,getattr(actor.data,'shape_keys',None)]:
            if block is not None and block.animation_data:
                block.animation_data.action=None
                for track in block.animation_data.nla_tracks:track.mute=True
        if actor.type=='MESH' and actor.data.shape_keys:
            for key in actor.data.shape_keys.key_blocks:key.value=0
    for bone in rig.pose.bones:
        bone.location=(0,0,0);bone.rotation_quaternion=(1,0,0,0);bone.scale=(1,1,1)
    before=original_contract(rig,skin)
    loop=np.empty(len(mesh.loops),dtype=np.int32);mesh.loops.foreach_get('vertex_index',loop);old_faces=loop.reshape(-1,3)
    normals=np.empty(len(mesh.loops)*3,dtype=np.float32);mesh.corner_normals.foreach_get('vector',normals);normals=normals.reshape(-1,3)
    source_poly=mesh.attributes.new(name='V3SourcePolygonID',type='INT',domain='FACE');source_poly.data.foreach_set('value',np.arange(len(mesh.polygons),dtype=np.int32))
    inspections={side:inspect_side(skin,manifest,side) for side in ['left','right']}
    result={};patches=[];remove=np.zeros(len(old_faces),dtype=bool)
    for side in ['left','right']:
        obj,proof=module.build_eye_patch(rig,skin,manifest,inspections[side],side,final_joint=True)
        patches.append(obj);result[side]=proof
        remove[proof['selected_source_body_face_ids']]=True
        remove[proof['removed_background_source_body_face_ids']]=True
        remove[proof['body_normal_fan_ghost_source_face_ids']]=False
        module.h.lid_animations(obj);add_open_tracks(obj,skin)
    ghost_faces=sorted({i for proof in result.values() for i in proof['body_normal_fan_ghost_source_face_ids']})
    mesh.materials.append(module.normal_fan_material())
    ghost_material=len(mesh.materials)-1
    body_ghost=mesh.attributes.new(name='NormalFanGhost',type='BOOLEAN',domain='FACE')
    flags=np.zeros(len(mesh.polygons),dtype=bool);flags[ghost_faces]=True;body_ghost.data.foreach_set('value',flags)
    for i in ghost_faces:mesh.polygons[i].material_index=ghost_material
    # Both patches sample the same original source before this one cleanup.
    bm=bmesh.new();bm.from_mesh(mesh);bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm,geom=[bm.faces[int(i)] for i in np.flatnonzero(remove)],context='FACES_ONLY')
    bm.to_mesh(mesh);bm.free();mesh.update();mesh.normals_split_custom_set(normals[np.repeat(~remove,3)].tolist())
    for actor in list(bpy.context.scene.objects):
        if 'Eyelid_' in actor.name:bpy.data.objects.remove(actor,do_unlink=True)
    after=original_contract(rig,skin)
    preserved={name:before[name]==after[name] for name in ['weights','bone_rest','rig_actions','body_actions']}
    preserved['body_keys_bitwise_equal']=all(np.array_equal(points,after['body_keys'][name]) for name,points in before['body_keys'].items())
    assert all(preserved.values()),preserved
    newloop=np.empty(len(mesh.loops),dtype=np.int32);mesh.loops.foreach_get('vertex_index',newloop)
    assert np.array_equal(newloop.reshape(-1,3),old_faces[~remove])
    report={'status':'SOURCE_GENERATED_NOT_YET_GEOMETRY_OR_ART_PASS','source_before_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        'single_eye_prerequisite_sha256':receipt['prototype_sha256'],'original_contract_preserved':preserved,
        'body_removed_post_mouth_face_ids':np.flatnonzero(remove).tolist(),'body_retained_faces_exact':True,
        'local_eye_proofs':result,'aliases':['Blink','Focus'],'joint_name_format':'LidBxxxFxxx, length 11, F at position 7',
        'all_eye_meshes_use_original_six_clip_names':True,'CPU_only':True,'formal_assets_unchanged':True}
    bpy.context.preferences.filepaths.save_version=0
    target=WORK/'source-dual-eye-joint-direct-fan.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(target),compress=True)
    report['source_after_sha256']=hashlib.sha256(target.read_bytes()).hexdigest()
    (ROOT/'dual-eye-joint-direct-fan-source.json').write_text(json.dumps(report,indent=2)+'\n')
    print('DUAL_JOINT_SOURCE_COMPLETE',report['source_after_sha256'],flush=True)

module=load_module('dual_shared_eye',WORK/'dual_shared_eye_direct_fan.py')
if __name__=='__main__':main()
