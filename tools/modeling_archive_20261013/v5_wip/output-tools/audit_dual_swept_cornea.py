"""Whole-triangle, whole-time separation certificates for actual GLB samplers.

On a LINEAR weight interval each vertex follows a straight segment. Every
triangle at every time is inside the convex hull of its six endpoint vertices.
A separating plane for that hull and the normalized unit ellipsoid therefore
certifies the complete triangle/time interval. Uncertified hulls are subdivided
in time; sampled points are not reported as proof of whole-face separation.
"""
from pathlib import Path
import json,hashlib,sys
import numpy as np
from glb_arrays import arrays,xyz_to_blender
ROOT=Path(__file__).resolve().parent
WORK=ROOT.parents[1]/'work/nailong/face-topology-v5'
MANIFEST=json.loads((WORK/'V3_MODEL_MANIFEST.json').read_text())

def hull_certificate(vertices,iterations=40):
    """Certified lower bound on distance of each 6-point hull to the origin."""
    n=len(vertices);p=vertices[np.arange(n),np.argmin(np.sum(vertices*vertices,axis=2),axis=1)]
    certified=np.zeros(n,dtype=bool);bound=np.zeros(n);active=np.arange(n)
    for iteration in range(iterations):
        if not len(active):break
        v=vertices[active];q=p[active];length=np.linalg.norm(q,axis=1)
        dots=np.einsum('nij,nj->ni',v,q);choice=np.argmin(dots,axis=1)
        lower=dots[np.arange(len(active)),choice]/np.maximum(length,1e-30)
        good=lower>=1+1e-9
        certified[active[good]]=True;bound[active[good]]=lower[good]
        remaining=active[~good]
        if not len(remaining):break
        target=v[~good,choice[~good]];q=q[~good];direction=target-q
        alpha=np.clip(-np.einsum('ij,ij->i',q,direction)/np.maximum(np.einsum('ij,ij->i',direction,direction),1e-30),0,1)
        p[remaining]=q+alpha[:,None]*direction
        active=remaining
    return certified,bound

def swept(p0,p1,center,radii,depth=0):
    vertices=np.concatenate([p0,p1],axis=1)
    normalized=(vertices-center)/radii
    good,bound=hull_certificate(normalized)
    unresolved=np.flatnonzero(~good)
    lower=float(bound[good].min()) if good.any() else float('inf')
    subdivisions=0;failures=[]
    if len(unresolved):
        if depth>=12:
            failures=unresolved.tolist()
        else:
            a,b=p0[unresolved],p1[unresolved];middle=(a+b)*.5
            left=swept(a,middle,center,radii,depth+1)
            right=swept(middle,b,center,radii,depth+1)
            lower=min(lower,left['radius_lower_bound'],right['radius_lower_bound'])
            failures=sorted(set(unresolved[left['uncertified_indices']].tolist()+unresolved[right['uncertified_indices']].tolist()))
            subdivisions=len(unresolved)+left['subdivisions']+right['subdivisions']
    return {'radius_lower_bound':lower,'uncertified_indices':failures,'subdivisions':subdivisions}

def reference_cases():
    triangle=np.array([[-.1,1.2,-.1],[.1,1.2,-.1],[0,1.2,.1]])[None]
    clear=swept(triangle,triangle+.01,np.zeros(3),np.ones(3))
    crossing=swept(triangle*np.array([1,-1,1]),triangle,np.zeros(3),np.ones(3),depth=12)
    assert not clear['uncertified_indices'] and crossing['uncertified_indices']
    return {'static_outside_and_small_motion_certified':True,'swept_across_sphere_not_falsely_certified':True,
        'clear_radius_lower_bound':clear['radius_lower_bound'],'algorithm_scope':'convex swept endpoint hull separation; all surface points and continuous time'}

def audit(level):
    path=WORK/'lod-candidates'/('nailong_lod%d.glb'%level);doc,access=arrays(path)
    result={'level':level,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'meshes':[]}
    bone_names=[doc['nodes'][i]['name'] for i in doc['skins'][0]['joints']]
    head=bone_names.index('head')
    for mesh_index,mesh in enumerate(doc['meshes']):
        if 'Shared' not in mesh['name'] or 'eyelid' not in mesh['name']:continue
        side='left' if 'left' in mesh['name'] else 'right'
        frame=MANIFEST['face_helper']['measured_eyes'][side]
        center=np.asarray(frame['center']);radii=np.asarray(frame['radii'])
        record={'mesh':mesh['name'],'intervals':0,'whole_triangle_interval_pairs':0,'uncertified_pairs':[],
            'subdivisions':0,'minimum_certified_normalized_radius':float('inf'),'all_vertices_rigid_head_bound':True}
        nodes={i for i,node in enumerate(doc['nodes']) if node.get('mesh')==mesh_index}
        for primitive in mesh['primitives']:
            attr=primitive['attributes'];joints=access[attr['JOINTS_0']];weights=access[attr['WEIGHTS_0']]
            head_weight=np.sum(np.where(joints==head,weights,0),axis=1)
            assert np.all(head_weight>=1-1e-6),(mesh['name'],float(head_weight.min()))
            base=xyz_to_blender(access[attr['POSITION']]);faces=access[primitive['indices']].reshape(-1,3)
            tensor=np.stack([xyz_to_blender(access[target['POSITION']]) for target in primitive['targets']])
            names=mesh['extras']['targetNames']
            for animation in doc['animations']:
                for channel in animation['channels']:
                    if channel['target'].get('node') not in nodes or channel['target']['path']!='weights':continue
                    sampler=animation['samplers'][channel['sampler']];assert sampler.get('interpolation','LINEAR')=='LINEAR'
                    times=access[sampler['input']].ravel();morph=access[sampler['output']].reshape(-1,len(names))
                    previous=base+np.einsum('k,kij->ij',morph[0],tensor)
                    for i in range(len(times)-1):
                        following=base+np.einsum('k,kij->ij',morph[i+1],tensor)
                        # Both the true sclera and the conservative ellipsoid
                        # enclosing its front corneal cap are tested.
                        for offset in [0,.0068]:
                            c=center+np.array([0,offset,0])
                            proof=swept(previous[faces],following[faces],c,radii)
                            record['minimum_certified_normalized_radius']=min(record['minimum_certified_normalized_radius'],proof['radius_lower_bound'])
                            record['subdivisions']+=proof['subdivisions']
                            if proof['uncertified_indices']:
                                record['uncertified_pairs'].append({'clip':animation['name'],'interval':i,'offset_m':offset,'faces':proof['uncertified_indices'][:20]})
                        record['intervals']+=1;record['whole_triangle_interval_pairs']+=len(faces)
                        previous=following
                    print('SWEPT_CLIP',level,side,animation['name'],record['intervals'],len(record['uncertified_pairs']),flush=True)
        record['rest_space_distance_lower_bound_m']=(record['minimum_certified_normalized_radius']-1)*float(radii.min())
        record['whole_face_and_time_separation_certified']=not record['uncertified_pairs']
        result['meshes'].append(record)
    assert len(result['meshes'])==2
    result['all_actual_samplers_whole_triangles_clear']=all(x['whole_face_and_time_separation_certified'] for x in result['meshes'])
    return result

if __name__=='__main__':
    levels=[int(x) for x in sys.argv[1:]] or [0,1,2]
    report={'reference_cases':reference_cases(),'files':[audit(i) for i in levels],
        'scope':'Actual LINEAR GLB weight intervals, every entire local eye triangle, rigid-head coordinates. Separating swept-hull planes certify continuous time and triangle interior. Uncertified hulls are reported as unresolved, not asserted penetrations. Geometry self-intersections, inter-object face/body joins, native shading, and independently moving eye bones are outside this certificate.'}
    (ROOT/'dual-glb-swept-cornea.json').write_text(json.dumps(report,indent=2)+'\n')
    print('SWEPT_AUDIT_DONE',all(x['all_actual_samplers_whole_triangles_clear'] for x in report['files']),flush=True)
