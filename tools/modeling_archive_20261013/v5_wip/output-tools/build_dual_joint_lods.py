"""Three isolated LOD candidates, each rebuilt at its actual Body boundary."""
from pathlib import Path
import bpy,bmesh,hashlib,importlib.util,json,sys
import numpy as np

ROOT=Path(__file__).resolve().parent
WORK=ROOT.parents[1]/'work/nailong/face-topology-v5'
V3=ROOT.parents[1]/'work/nailong/rig-candidate/face-tail-trial-v3'
DEST=WORK/'lod-candidates';DEST.mkdir(exist_ok=True)

def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result)
    return result

builder=module('dual_source_builder',ROOT/'build_dual_joint_source.py')
binder=module('v3_frozen_adapter',ROOT.parent/'nailong-face-candidate-v3/adapter-final.py')

def curves(strip):
    # The actual Blender 4.5 glTF importer creates one action with separate
    # channelbags for armature and mesh slots; legacy Action.fcurves reads only
    # its first slot, which is not the Body's morph data.
    from io_scene_gltf2.blender.com.data_path import get_channelbag_for_slot
    return get_channelbag_for_slot(strip.action,strip.action_slot).fcurves

def imported_contract(rig,body):
    contract=builder.original_contract(rig,body)
    for key,block in [('rig_actions',rig),('body_actions',body.data.shape_keys)]:
        contract[key]={t.name:[(f.data_path,f.array_index,[(tuple(p.co),p.interpolation) for p in f.keyframe_points])
            for f in curves(t.strips[0])] for t in block.animation_data.nla_tracks}
    return contract

def add_imported_open_tracks(obj,body):
    keys=obj.data.shape_keys
    source={t.name:t.strips[0] for t in body.data.shape_keys.animation_data.nla_tracks}
    for track in keys.animation_data.nla_tracks:
        action=track.strips[0].action;keys.animation_data.action=action
        source_strip=source[track.name]
        reference=next(f for f in curves(source_strip) if 'key_blocks["Open"]' in f.data_path)
        grid_curve=next(f for f in action.fcurves if 'key_blocks["Open"]' not in f.data_path)
        for grid_point in grid_curve.keyframe_points:
            frame=float(grid_point.co.x)
            # Keep every joint channel on the exact same floating grid. The
            # glTF exporter otherwise bakes differing channel key counts at
            # integer frames, despite export_force_sampling=False.
            global_frame=frame+(source_strip.frame_start-1)
            source_frame=source_strip.action_frame_start+(global_frame-source_strip.frame_start)/source_strip.scale
            keys.key_blocks['Open'].value=float(reference.evaluate(source_frame))
            keys.key_blocks['Open'].keyframe_insert('value',frame=frame)
        new=next(f for f in action.fcurves if 'key_blocks["Open"]' in f.data_path)
        for point in new.keyframe_points:point.interpolation='LINEAR'
        keys.animation_data.action=None

def main():
    manifest=json.loads((WORK/'V3_MODEL_MANIFEST.json').read_text())
    result=[]
    levels=[int(v) for v in sys.argv[sys.argv.index('--')+1:]] if '--' in sys.argv else [0,1,2]
    for level in levels:
        path=V3/('nailong_lod%d.glb'%level)
        expected=manifest['lods'][level]['sha256']
        assert hashlib.sha256(path.read_bytes()).hexdigest()==expected
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.context.scene.render.fps=30
        bpy.ops.import_scene.gltf(filepath=str(path),merge_vertices=True)
        actors=[o for o in bpy.context.scene.objects if o.type=='MESH' and any(m.type=='ARMATURE' for m in o.modifiers)]
        skin=max([o for o in actors if o.data.shape_keys and 'Open' in o.data.shape_keys.key_blocks and 'Blink' not in o.data.shape_keys.key_blocks],key=lambda o:len(o.data.vertices))
        rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
        skin.name='NailongSkin_Reconstructed';rig.name='NailongRig'
        for actor in [rig,*actors]:
            for block in [actor,getattr(actor.data,'shape_keys',None)]:
                if block is not None and block.animation_data:
                    block.animation_data.action=None
                    for track in block.animation_data.nla_tracks:track.mute=True
            if actor.type=='MESH' and actor.data.shape_keys:
                for key in actor.data.shape_keys.key_blocks:key.value=0
        for bone in rig.pose.bones:
            bone.location=(0,0,0);bone.rotation_quaternion=(1,0,0,0);bone.scale=(1,1,1)
        before=imported_contract(rig,skin)
        mesh=skin.data;loop=np.empty(len(mesh.loops),dtype=np.int32);mesh.loops.foreach_get('vertex_index',loop);old_faces=loop.reshape(-1,3)
        normals=np.empty(len(mesh.loops)*3,dtype=np.float32);mesh.corner_normals.foreach_get('vector',normals);normals=normals.reshape(-1,3)
        source_poly=mesh.attributes.new(name='LODInputSourcePolygonID',type='INT',domain='FACE');source_poly.data.foreach_set('value',np.arange(len(mesh.polygons),dtype=np.int32))
        inspections={side:builder.inspect_side(skin,manifest,side) for side in ['left','right']}
        proof={};patches=[];remove=np.zeros(len(old_faces),dtype=bool)
        for side in ['left','right']:
            obj,record=builder.module.build_eye_patch(rig,skin,manifest,inspections[side],side,final_joint=True)
            patches.append(obj);proof[side]=record
            remove[record['selected_source_body_face_ids']]=True
            remove[record['removed_background_source_body_face_ids']]=True
            builder.module.h.lid_animations(obj)
            add_imported_open_tracks(obj,skin)
            # Match the actual NLA timeline, not the imported action's frame 0.
            original_strips={t.name:t.strips[0] for t in skin.data.shape_keys.animation_data.nla_tracks}
            for track in obj.data.shape_keys.animation_data.nla_tracks:
                strip=track.strips[0]
                reference=original_strips[track.name]
                shift=reference.frame_start-1
                for curve in strip.action.fcurves:
                    if 'key_blocks["Open"]' in curve.data_path:continue
                    for point in curve.keyframe_points:
                        point.co.x+=shift;point.handle_left.x+=shift;point.handle_right.x+=shift
                strip.action_frame_start=reference.frame_start
                strip.action_frame_end=reference.frame_end
                strip.frame_start=reference.frame_start;strip.frame_end=reference.frame_end
        bm=bmesh.new();bm.from_mesh(mesh);bm.faces.ensure_lookup_table()
        bmesh.ops.delete(bm,geom=[bm.faces[int(i)] for i in np.flatnonzero(remove)],context='FACES_ONLY')
        bm.to_mesh(mesh);bm.free();mesh.update();mesh.normals_split_custom_set(normals[np.repeat(~remove,3)].tolist())
        for actor in list(bpy.context.scene.objects):
            if actor.type=='MESH' and actor.data.shape_keys and 'Blink' in actor.data.shape_keys.key_blocks and actor not in patches:
                bpy.data.objects.remove(actor,do_unlink=True)
        extras=[o for o in bpy.context.scene.objects if o.type=='MESH' and o!=skin and any(m.type=='ARMATURE' for m in o.modifiers)]
        after=imported_contract(rig,skin)
        kept={key:before[key]==after[key] for key in ['weights','bone_rest','rig_actions','body_actions']}
        kept['body_keys_bitwise_equal']=all(np.array_equal(p,after['body_keys'][key]) for key,p in before['body_keys'].items())
        assert all(kept.values()),kept
        newloop=np.empty(len(mesh.loops),dtype=np.int32);mesh.loops.foreach_get('vertex_index',newloop)
        assert np.array_equal(newloop.reshape(-1,3),old_faces[~remove])
        for actor in [rig,skin,*extras]:
            for block in binder.animation_data_blocks(actor):
                for track in block.nla_tracks:track.mute=False
        source=DEST/('source-lod%d.blend'%level)
        bpy.context.preferences.filepaths.save_version=0
        bpy.ops.wm.save_as_mainfile(filepath=str(source),compress=True)
        target=DEST/('nailong_lod%d.glb'%level)
        binder.export(rig,skin,target,extras,force_sampling=False)
        actual=binder.audit_export(target)
        record={'level':level,'baseline_glb':str(path),'baseline_glb_sha256':expected,'source':str(source),
            'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'file':str(target),'sha256':actual['sha256'],
            'original_imported_contract_preserved':kept,'body_retained_faces_exact':True,'body_removed_input_face_ids':np.flatnonzero(remove).tolist(),
            'face_helper':{'measured_eyes':manifest['face_helper']['measured_eyes'],'Blink':True,'Focus':True,'joint_key_grid':True,'source_proofs':proof},
            'export_audit':actual,'status':'EXPORTED_CANDIDATE_PENDING_CONTINUOUS_GEOMETRY_AND_ART_REVIEW'}
        (ROOT/('dual-joint-lod%d.json'%level)).write_text(json.dumps(record,indent=2)+'\n')
        result.append(record)
        print('DUAL_JOINT_LOD_EXPORTED',level,actual['sha256'],actual['triangles'],flush=True)
    (ROOT/'dual-joint-lod-generation.json').write_text(json.dumps({'lods':result,'formal_assets_unchanged':True,'CPU_only':True},indent=2)+'\n')

if __name__=='__main__':main()
