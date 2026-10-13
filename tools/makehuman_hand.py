"""Extract and pose the CC0 MakeHuman hm08 hand, retaining its mature quad topology.

This is asset processing, not MakeHuman program code. Provenance is recorded next
to the unmodified upstream OBJ in source_assets/reference_cc0.
"""
import bpy, bmesh, math, numpy as np, json, hashlib
from mathutils import Vector, Matrix, Quaternion
from mathutils.bvhtree import BVHTree

HAND_SHAPE_WEIGHTS = {
    'mindfront_hand_thenar_eminence': .38,
    'mindfront_hand_hypothenar': .34,
    'jujube_knobby_knuckles': .28,
    'mindfront_hand_fingers_correction': .45,
}

def reference_hand(path, shape_weights=None):
    vertices=[];uv=[];faces=[];group=''
    for line in path.read_text().splitlines():
        s=line.split()
        if not s:continue
        if s[0]=='v':vertices.append(tuple(map(float,s[1:4])))
        elif s[0]=='vt':uv.append(tuple(map(float,s[1:3])))
        elif s[0]=='g':group=s[1]
        elif s[0]=='f':faces.append((group,[(int(c.split('/')[0])-1,int(c.split('/')[1])-1) for c in s[1:]]))
    vertices=np.asarray(vertices,dtype=np.float64)
    centers={}
    for g in set(g for g,_ in faces):
        if g.startswith('joint-r-'):
            ids=list(set(i for gg,f in faces if gg==g for i,_ in f));centers[g]=vertices[ids].mean(axis=0)
    origin=centers['joint-r-hand'];z=centers['joint-r-finger-3-1']-origin;z/=np.linalg.norm(z)
    x=centers['joint-r-finger-5-1']-centers['joint-r-finger-2-1'];x-=z*np.dot(x,z);x/=np.linalg.norm(x)
    y=np.cross(z,x);frame=np.stack((x,y,z))
    assert np.linalg.det(frame) > .999, 'source coordinate frame must preserve right-hand chirality'
    # The CC0 targets use the untouched hm08 indices. Apply them before
    # extraction; joint-marker helpers remain those of the source skeleton.
    if shape_weights:
        targets=path.parents[1]/'reference_hand_studies'/'hands01'/'targets'/'hands'
        for name,weight in shape_weights.items():
            assert 0 <= weight <= 1
            for line in (targets/(name+'.target')).read_text().splitlines():
                fields=line.split()
                if not fields or fields[0].startswith('#'):continue
                index=int(fields[0]);assert 0 <= index < len(vertices)
                vertices[index]+=np.asarray(fields[1:4],dtype=float)*weight
    local=np.stack([((vertices-origin)*axis).sum(1) for axis in frame],axis=1)*.1
    kept=[f for g,f in faces if g=='body' and all(vertices[i,0]<-3.8 and local[i,2]>-.025 for i,_ in f)]
    ids=sorted(set(i for f in kept for i,_ in f));remap={old:i for i,old in enumerate(ids)}
    joints={}
    for f in range(1,6):
        joints[f]=[]
        for j in range(1,5):
            delta=centers[f'joint-r-finger-{f}-{j}']-origin
            p=np.array([(delta*axis).sum() for axis in frame])*.1;joints[f].append(Vector(p))
    # Keep the source right hand and original winding. Only build_hand's
    # explicit left-hand mirror may reverse chirality.
    return local[ids],[[remap[i] for i,_ in f] for f in kept],[[uv[t] for _,t in f] for f in kept],joints,ids

def transverse_hinge(bone):
    """Finger flexion is orthogonal to the bone, in the source palm plane."""
    longitudinal=(bone.tail_local-bone.head_local).normalized()
    hinge=Vector((0,1,0)).cross(longitudinal).normalized()
    # The source and its sole left-hand mirror both flex toward palm-local +Y.
    if hinge.x < 0:hinge=-hinge
    local=(bone.matrix_local.to_3x3().inverted()@hinge).normalized()
    assert abs(local.y) < 1e-5, (bone.name,'axial finger flexion',local.y)
    return local

def thumb_hinge(bone,support,dorsal=None):
    """Thumb flexion follows its own opposed nail/volar plane, not the palm."""
    longitudinal=(bone.tail_local-bone.head_local).normalized()
    dorsal=Vector(dorsal) if dorsal is not None else Vector((.86 if support else -.86,-.50,0))
    volar=-dorsal+longitudinal*dorsal.dot(longitudinal)
    hinge=volar.normalized().cross(longitudinal).normalized()
    local=(bone.matrix_local.to_3x3().inverted()@hinge).normalized()
    assert abs(local.y)<1e-5
    return local

def cup_palm(vertices,joints,depth):
    """A shallow transverse palm arch, with the digit roots carried with it.

    The radial/index side remains the stable side; the ulnar metacarpals cup
    toward the held object. This source morph does not twist finger joints.
    """
    radial=float(joints[2][0].x);ulnar=float(joints[5][0].x)
    def amount(points):
        across=np.clip((points[:,0]-radial)/(ulnar-radial),0,1)
        across=np.clip((across-.22)/.78,0,1)
        along=np.clip((points[:,2]-.025)/.065,0,1);along=along*along*(3-2*along)
        return depth*across*across*along
    displacement=amount(vertices);vertices[:,1]+=displacement
    for chain in joints.values():
        offsets=amount(np.asarray(chain))
        for point,offset in zip(chain,offsets):point.y+=float(offset)
    return {'depth_m':depth,'maximum_applied_m':float(displacement.max()),'method':'ulnar transverse palm arch; matching joint-root displacement, wrist protected'}

def finger_skin_radii(obj,joints,name):
    """Measure the refined skin around each actual phalanx before posing."""
    coordinates=np.empty(len(obj.data.vertices)*3,dtype=np.float32)
    obj.data.vertices.foreach_get('co',coordinates);coordinates=coordinates.reshape(-1,3)
    rows=[]
    for digit,label in [(2,'Index'),(3,'Middle'),(4,'Ring'),(5,'Little')]:
        radii=[]
        for j in range(3):
            head=np.asarray(joints[digit][j]);direction=np.asarray(joints[digit][j+1])-head
            length=np.linalg.norm(direction);direction/=length
            distance=((coordinates-head)*direction).sum(axis=1)
            assert np.all(np.isfinite(distance)), 'non-finite source phalanx projection'
            group=obj.vertex_groups[name+label+str(j+1)].index
            selected=np.array([any(w.group==group and w.weight>.5 for w in v.groups) for v in obj.data.vertices])
            selected&=(distance>length*.20)&(distance<length*.85)
            radial=coordinates[selected]-head-distance[selected,None]*direction
            assert len(radial)>8,(name,label,j,'insufficient source skin cross section')
            radii.append(float(np.quantile(np.linalg.norm(radial,axis=1),.95)))
        rows.append(radii)
    return rows

class ContactSurface:
    """Signed distance to a union of verified closed mesh components."""
    def __init__(self,vertices,faces,components):
        self.tree=BVHTree.FromPolygons(vertices,faces)
        self.components=components
        self.ray=Vector((.7913,.3137,.5251)).normalized()
        self.lower=np.asarray([list(c[1]) for c in components])
        self.upper=np.asarray([list(c[2]) for c in components])
        self.cache={}

    def find_nearest(self,point):
        return self.tree.find_nearest(point)

    def signed_distance(self,point):
        key=tuple(point)
        if key in self.cache:return self.cache[key]
        distance=self.tree.find_nearest(point)[3]
        coordinates=np.asarray(key)
        for candidate in np.flatnonzero(np.all((coordinates>=self.lower-1e-8)&(coordinates<=self.upper+1e-8),axis=1)):
            tree=self.components[int(candidate)][0]
            cursor=Vector(point);crossings=0
            for _ in range(128):
                hit,_,_,_=tree.ray_cast(cursor,self.ray,10.0)
                if hit is None:break
                crossings+=1;cursor=hit+self.ray*.000002
            else:raise RuntimeError('closed contact component exceeded ray traversal bound')
            if crossings%2:distance=-distance;break
        if len(self.cache)>80000:self.cache.clear()
        self.cache[key]=distance
        return distance


def assembled_surface(parent, placement=None):
    """Closed, outward-oriented components of the actual contact geometry.

    Open reflectors and lettering cannot define an inside. Exclude those;
    inspect each closed component's oriented volume before signing distance.
    """
    bpy.context.view_layer.update();vertices=[];faces=[];components=[];receipt={'closed_components':0,'open_components_excluded':0,'orientation_corrections':0,'inside_test':'component AABB and ray parity; closest face normal is not used as an inside test'}
    placement=placement or Matrix.Identity(4)
    for part in parent.children_recursive:
        if part.type!='MESH':continue
        bm=bmesh.new();bm.from_mesh(part.data);bm.verts.ensure_lookup_table();bm.faces.ensure_lookup_table()
        seen=set();matrix=placement@part.matrix_world
        for seed in bm.faces:
            if seed in seen:continue
            component=[];todo=[seed];seen.add(seed)
            while todo:
                face=todo.pop();component.append(face)
                for edge in face.edges:
                    for neighbour in edge.link_faces:
                        if neighbour not in seen:seen.add(neighbour);todo.append(neighbour)
            if any(len(edge.link_faces)!=2 for face in component for edge in face.edges):
                receipt['open_components_excluded']+=1;continue
            component_vertices=list({v for face in component for v in face.verts})
            mapped={v:len(vertices)+i for i,v in enumerate(component_vertices)}
            transformed={v:matrix@v.co for v in component_vertices}
            origin=transformed[component_vertices[0]];volume=0.0
            for face in component:
                points=[transformed[v]-origin for v in face.verts]
                volume+=sum(points[0].dot(points[i].cross(points[i+1]))/6 for i in range(1,len(points)-1))
            if abs(volume)<1e-14:receipt['open_components_excluded']+=1;continue
            component_points=[transformed[v] for v in component_vertices]
            vertices.extend(component_points);component_faces=[];start_index=min(mapped.values())
            for face in component:
                polygon=tuple(mapped[v] for v in face.verts);polygon=tuple(reversed(polygon)) if volume<0 else polygon
                faces.append(polygon);component_faces.append(tuple(index-start_index for index in polygon))
            lower=Vector([min(v[i] for v in component_points) for i in range(3)]);upper=Vector([max(v[i] for v in component_points) for i in range(3)])
            components.append((BVHTree.FromPolygons(component_points,component_faces),lower,upper))
            receipt['closed_components']+=1;receipt['orientation_corrections']+=int(volume<0)
        bm.free()
    assert faces,(parent.name,'no closed contact surface')
    return ContactSurface(vertices,faces,components),receipt


def compress_contact_pads(mesh,obj,surface,loc,basis,digits=('Thumb','Index','Middle','Ring','Little')):
    """Bounded local flesh correction on confirmed inside contact pads.

    A 3 mm displacement cap cannot conceal deep intersections: vertices more
    than 3.5 mm inside are left for pose repair and reported separately.
    """
    inverse=basis.inverted();digit_groups={g.index for g in obj.vertex_groups if any(n in g.name for n in digits)}
    changed=0;too_deep=0;max_displacement=0.0;remaining=0.0
    for vertex in mesh.vertices:
        if sum(w.weight for w in vertex.groups if w.group in digit_groups)<=.5:continue
        point=loc+basis@vertex.co;signed=surface.signed_distance(point)
        if signed>=-.00002:continue
        if signed<-.0035:too_deep+=1;remaining=min(remaining,signed);continue
        nearest,_,_,_=surface.find_nearest(point);direction=(nearest-point).normalized()
        amount=min(.003,-signed+.00010);moved=point+direction*amount
        vertex.co=inverse@(moved-loc);changed+=1;max_displacement=max(max_displacement,amount)
        remaining=min(remaining,surface.signed_distance(moved))
    mesh.update()
    return {'method':'confirmed closed-volume finger-pad correction, no topology/UV/weight change','vertices_moved':changed,'maximum_displacement_m':max_displacement,'deep_pose_intersection_vertices_left_unmodified':too_deep,'remaining_inside_after_correction_m':remaining}

def weight_skin(obj,rig,bones,name):
    co=np.empty(len(obj.data.vertices)*3,dtype=np.float32);obj.data.vertices.foreach_get('co',co);co=co.reshape(-1,3)
    names=[b[0] for b in bones];ids={n:i for i,n in enumerate(names)};d=np.full((len(co),len(bones)),1e4,dtype=np.float32)
    for j,(_,a,b,_) in enumerate(bones):
        a=np.array(a);v=np.array(b)-a;t=np.clip(((co-a)*v).sum(1)/max(float((v*v).sum()),1e-8),0,1)
        d[:,j]=np.sqrt(((co-(a+t[:,None]*v))**2).sum(1))
    digit_names=['Index','Middle','Ring','Little','Thumb']
    chain_distance=np.stack([d[:,[ids[name+fn+str(j)] for j in range(1,4)]].min(1) for fn in digit_names],axis=1)
    nearest=chain_distance.argmin(1);allowed=np.zeros_like(d,dtype=bool)
    claimed=np.zeros(len(co),dtype=bool)
    for f,fn in enumerate(digit_names):
        head=np.array(bones[ids[name+fn+'1']][1]);axis=np.array(bones[ids[name+fn+'1']][2])-head;axis/=np.linalg.norm(axis)
        beyond=((co-head)*axis).sum(1)
        # The thumb has a long thenar transition; each other digit starts above
        # its metacarpal arch. Finger weights never reach a neighbouring finger.
        mask=(nearest==f)&(beyond>-.006)&(chain_distance[:,f]<(.026 if fn=='Thumb' else .016))
        for j in range(1,4):allowed[mask,ids[name+fn+str(j)]]=True
        allowed[mask&(beyond<(.025 if fn=='Thumb' else .011)),ids['palm']]=True;claimed|=mask
    allowed[~claimed,ids['palm']]=True;allowed[~claimed,ids['wrist']]=True
    d[~allowed]=1e4;near=np.argpartition(d,2,axis=1)[:,:2];dist=np.take_along_axis(d,near,axis=1)
    weights=1/np.maximum(dist,.0008)**2;weights/=weights.sum(1)[:,None];weights=np.round(weights*128)/128
    for j,bn in enumerate(names):
        vg=obj.vertex_groups.new(name=bn)
        for k in range(2):
            mask=near[:,k]==j
            for w in np.unique(weights[mask,k]):
                if w>0:vg.add(np.where(mask&(weights[:,k]==w))[0].tolist(),float(w),'REPLACE')
    mod=obj.modifiers.new('Per digit anatomical skin','ARMATURE');mod.object=rig

def transport_sleeve(lib,name,points,radii,material,parent,sides,steps):
    """A continuous sleeve frame: no cross-section flip at a world-axis threshold."""
    path=lib.sample_path(points,steps);vertices=[];faces=[];uv=[];previous_tangent=None;normal=None
    for i,p in enumerate(path):
        tangent=(path[min(i+1,len(path)-1)]-path[max(0,i-1)]).normalized()
        if previous_tangent is None:
            normal=tangent.cross(Vector((1,0,0))).normalized()
            if normal.length<.5:normal=tangent.cross(Vector((0,1,0))).normalized()
        else:
            normal=previous_tangent.rotation_difference(tangent)@normal
            normal=(normal-tangent*normal.dot(tangent)).normalized()
        bitangent=tangent.cross(normal).normalized();previous_tangent=tangent
        t=i/(len(path)-1);q=t*(len(radii)-1);k=min(len(radii)-2,int(q));r=radii[k]+(radii[k+1]-radii[k])*(q-k)
        for j in range(sides):
            a=math.tau*j/sides
            # Small longitudinal cloth fullness, never a changing arm silhouette.
            fold=.014*math.sin(7*a+t*38)*math.exp(-((t-.22)/.18)**2)
            wrist_fit=max(0,1-t/.24)
            normal_width=1-.22*wrist_fit;side_width=.9+.15*wrist_fit
            vertices.append(tuple(p+r*(1+fold)*(normal*math.cos(a)*normal_width+bitangent*math.sin(a)*side_width)))
            uv.append((j/sides,t))
    for i in range(len(path)-1):
        for j in range(sides):faces.append((i*sides+j,(i+1)*sides+j,(i+1)*sides+(j+1)%sides,i*sides+(j+1)%sides))
    # The cuff end stays open inside the skin wrist, avoiding a cloth disk through it.
    faces.append(tuple((len(path)-1)*sides+j for j in range(sides)))
    return lib.shaped_mesh(name,vertices,faces,material,parent,uv)

def articulated_sleeve(lib,name,wrist,elbow,shoulder,material,parent,rig,high):
    """Two straight limb sections with a short, local elbow transition."""
    wrist,elbow,shoulder=map(Vector,(wrist,elbow,shoulder))
    fore=(elbow-wrist).normalized();upper=(shoulder-elbow).normalized()
    corner=min(.055,.28*min((elbow-wrist).length,(shoulder-elbow).length))
    before=elbow-fore*corner;after=elbow+upper*corner
    straight=36 if high else 18;round_steps=18 if high else 10
    centers=[wrist.lerp(before,i/straight) for i in range(straight)]
    centers += [(1-t)**2*before+2*(1-t)*t*elbow+t*t*after for t in np.linspace(0,1,round_steps,endpoint=False).tolist()]
    centers += [after.lerp(shoulder,i/straight) for i in range(straight+1)]
    arc=[0.0]
    for a,b in zip(centers,centers[1:]):arc.append(arc[-1]+(b-a).length)
    elbow_arc=arc[straight+round_steps//2];length=arc[-1]
    from arm_sleeve_profile import make_sleeve_profile
    reference=json.loads((lib.SOURCE/'reference_cc0'/'HM08_ARM_SECTION_REFERENCE.json').read_text())
    cuff_radii=(.0235,.025) if parent.name=='LeftSupport' else (.026772179902526,.024454530578746)
    profile=make_sleeve_profile(reference,elbow_arc,length,cuff_radii=cuff_radii)
    blend_start,blend_end=arc[straight],arc[straight+round_steps]
    sides=112 if high else 48;vertices=[];faces=[];uv=[];previous=None;normal=None;ring_weights=[]
    for i,p in enumerate(centers):
        tangent=(centers[min(i+1,len(centers)-1)]-centers[max(0,i-1)]).normalized()
        if previous is None:normal=tangent.cross(Vector((0,1,0))).normalized()
        else:normal=previous.rotation_difference(tangent)@normal;normal=(normal-tangent*normal.dot(tangent)).normalized()
        bitangent=tangent.cross(normal).normalized();previous=tangent;s=arc[i]
        width_radius,depth_radius=profile.sample(s)
        wrist_weight=max(0.0,1.0-s/.018);wrist_weight=wrist_weight*wrist_weight*(3-2*wrist_weight)
        upper_weight=max(0.0,min(1.0,(s-blend_start)/(blend_end-blend_start)));upper_weight=upper_weight*upper_weight*(3-2*upper_weight)
        ring_weights.append((wrist_weight,(1-wrist_weight)*(1-upper_weight),(1-wrist_weight)*upper_weight))
        for j in range(sides):
            a=math.tau*j/sides
            fold=.0008*math.cos((s-elbow_arc)*230)*math.exp(-((s-elbow_arc)/.027)**2)*(0.45+0.55*math.sin(a)**2)
            vertices.append(tuple(p+normal*math.cos(a)*(width_radius+fold*.94)+bitangent*math.sin(a)*(depth_radius+fold)))
            uv.append((j/sides,s/length))
    for i in range(len(centers)-1):
        for j in range(sides):faces.append((i*sides+j,(i+1)*sides+j,(i+1)*sides+(j+1)%sides,i*sides+(j+1)%sides))
    faces.append(tuple((len(centers)-1)*sides+j for j in range(sides)))
    obj=lib.shaped_mesh(name,vertices,faces,material,parent,uv)
    groups=[obj.vertex_groups.new(name=n) for n in ['wrist',parent.name+'ForeArm',parent.name+'UpperArm']]
    for ring,weights in enumerate(ring_weights):
        indices=list(range(ring*sides,(ring+1)*sides))
        for group,value in zip(groups,weights):
            if value>0:group.add(indices,value,'REPLACE')
    modifier=obj.modifiers.new('Two segment anatomical arm reach','ARMATURE');modifier.object=rig;modifier.use_deform_preserve_volume=True
    obj['sleeve_structure_json']=json.dumps({'wrist_local':list(wrist),'wrist_section_center_local':list(wrist),'elbow_local':list(elbow),'shoulder_local':list(shoulder),'ring_centers_local':[list(p) for p in centers],'ring_weights':ring_weights,'vertices_per_ring':sides,'wrist_blend_length_m':.018,'elbow_blend_half_length_m':(blend_end-blend_start)*.5,'elbow_corner_length_m':corner,'cross_section_reference':'C1-smoothed CC0 hm08 width/depth plus 3 mm cloth, existing cuff retained'})
    obj['sleeve_profile_json']=json.dumps(profile.receipt())
    return obj


def build_hand(lib,name,support,skin,cloth,parent,high):
    root=lib.empty(name,parent)
    if not hasattr(lib,'HAND_POSE_CACHE'):lib.HAND_POSE_CACHE={}
    cached_pose=lib.HAND_POSE_CACHE.get(name) if not high else None
    verts,faces,uv,joints,original_ids=reference_hand(lib.SOURCE/'reference_cc0'/'makehuman-base.obj',HAND_SHAPE_WEIGHTS)
    root['palm_arch_json']=json.dumps(cup_palm(verts,joints,.0038 if support else .0028))
    targets=lib.SOURCE/'reference_hand_studies'/'hands01'/'targets'/'hands'
    root['hand_shape_targets_json']=json.dumps({key:{'weight':weight,'sha256':hashlib.sha256((targets/(key+'.target')).read_bytes()).hexdigest()} for key,weight in HAND_SHAPE_WEIGHTS.items()},sort_keys=True)
    if support:
        verts[:,0]*=-1;faces=[list(reversed(f)) for f in faces];uv=[list(reversed(f)) for f in uv]
        for points in joints.values():
            for p in points:p.x*=-1
    data=bpy.data.meshes.new(name+'CC0AnatomicalTopology');data.from_pydata(verts.tolist(),[],faces);data.update()
    obj=bpy.data.objects.new(name+'SkinnedHand',data);bpy.context.collection.objects.link(obj);obj.parent=root;data.materials.append(skin)
    layer=data.uv_layers.new(name='MakeHuman original atlas UV')
    for poly,coordinates in zip(data.polygons,uv):
        poly.use_smooth=True
        for loop,coord in zip(poly.loop_indices,coordinates):layer.data[loop].uv=coord
    # The exact upstream weights belong to this exact hm08 vertex order. Apply
    # them before subdivision so Blender interpolates the authored joint/web
    # gradients. Palm metacarpal weights collapse into the game's palm bone.
    upstream=json.loads((lib.SOURCE/'reference_cc0'/'makehuman-default_weights.mhw').read_text())['weights']
    original_to_local={old:i for i,old in enumerate(original_ids)};per_vertex=[{} for _ in original_ids]
    digit_map={1:'Thumb',2:'Index',3:'Middle',4:'Ring',5:'Little'}
    for bn,values in upstream.items():
        if not bn.endswith('.R'):continue
        if bn.startswith('finger'):
            digit,segment=bn[:-2].replace('finger','').split('-');target=name+digit_map[int(digit)]+segment
        elif bn.startswith('metacarpal'):target='palm'
        elif bn=='wrist.R':target='wrist'
        # This extraction ends inside the cuff. Its short skin wrist must
        # follow the wrist as a unit; the separately authored sleeve carries
        # forearm/elbow bending, so no arm weight may pull through this skin.
        elif bn.startswith('lowerarm'):target='wrist'
        else:continue
        for old,weight in values:
            if old in original_to_local:
                item=per_vertex[original_to_local[old]];item[target]=item.get(target,0)+weight
    # Spread CMC influence across the actual thenar web before subdivision.
    # A sharp wrist/palm -> thumb1 weight step pinches under thumb opposition.
    if not support:
        adjacency=[set() for _ in original_ids]
        for face in faces:
            for i,j in zip(face,face[1:]+face[:1]):adjacency[i].add(j);adjacency[j].add(i)
        cmc=np.array(joints[1][0]);web=cmc*.45+np.array(joints[2][0])*.55
        smooth_names=['wrist','palm',name+'Thumb1',name+'Index1']
        for iteration in range(9):
            previous=[dict(w) for w in per_vertex]
            for i,v in enumerate(verts):
                if not adjacency[i]:continue
                amount=max(.65*max(0,1-np.linalg.norm(v-cmc)/.045),.72*max(0,1-np.linalg.norm(v-web)/.032))
                if amount==0:continue
                total=sum(previous[i].get(n,0) for n in smooth_names)
                averages={n:sum(previous[j].get(n,0) for j in adjacency[i])/len(adjacency[i]) for n in smooth_names}
                avtotal=sum(averages.values())
                if total>.001 and avtotal>.001:
                    for n in smooth_names:per_vertex[i][n]=(1-amount)*previous[i].get(n,0)+amount*averages[n]*total/avtotal
    groups={bn:obj.vertex_groups.new(name=bn) for bn in sorted(set(bn for weights in per_vertex for bn in weights))}
    for i,weights in enumerate(per_vertex):
        total=sum(weights.values());assert total>.95,(name,'unweighted original hand vertex',original_ids[i],total)
        for bn,w in weights.items():groups[bn].add([i],w/total,'REPLACE')
    bpy.context.view_layer.objects.active=obj;obj.select_set(True)
    sub=obj.modifiers.new('Anatomical quad refinement','SUBSURF');sub.levels=3;sub.render_levels=3;bpy.ops.object.modifier_apply(modifier=sub.name)
    # Both authoring and runtime solve against the same un-decimated envelope.
    # Cover the later, strictly bounded 0.16 mm nail/surface refinement too.
    measured_radii=[[radius+.00016 for radius in row] for row in finger_skin_radii(obj,joints,name)]
    if not high:
        dec=obj.modifiers.new('Runtime silhouette preserved topology','DECIMATE');dec.ratio=.43;bpy.ops.object.modifier_apply(modifier=dec.name)
    from hand_surface_detail import refine_hand_surface
    root['hand_surface_detail_json']=json.dumps(refine_hand_surface(obj,joints,support,skin,high),sort_keys=True)
    obj.select_set(False)
    forward=Vector((1,0,0))
    base_basis=Matrix((Vector((-forward.y,forward.x,0)),Vector((0,0,1)),forward)).transposed() if support else Matrix((Vector((0,0,-1)),Vector((-1,0,0)),Vector((0,1,0)))).transposed()
    roll_degrees=-18 if support else 6
    palm_roll=Matrix.Rotation(math.radians(roll_degrees),3,'Y' if support else 'Z')
    roll_pivot=Vector((0,0,0)) if support else Vector((0,-.005,0))
    basis=palm_roll@base_basis
    baseline_loc=Vector((-.100,.109,-.062)) if support else Vector((.032,-.096,-.078))
    stance_delta=Vector((0,0,-.005)) if support else Vector((.006,.004,0))
    loc=roll_pivot+palm_roll@(baseline_loc+stance_delta-roll_pivot)
    fit_loc=loc.copy()
    # Start from the measured forward-thumb reference, then turn the whole
    # palm into a diagonal cradle. Fit skin against the final grip location.
    thumb_forward_shift=Vector((0,-.020,0)) if support else Vector((0,0,0))
    loc+=thumb_forward_shift
    old_support_basis=basis.copy()
    if support:
        cmc_anchor=loc+basis@joints[1][0]
        basis=Matrix.Rotation(math.radians(50),3,'Z')@Matrix.Rotation(math.radians(26),3,'Y')@basis
        loc=cmc_anchor-basis@joints[1][0]+Vector((.004,-.030,0))
        fit_loc=loc.copy()
    inv=basis.inverted();point=lambda p:tuple(inv@(Vector(p)-loc))
    # Aim the forearm through the wrist toward the metacarpals. The previous
    # anchors forced 66/75 degree wrist bends before any runtime animation.
    source_shoulder=Vector((-.430,-.250,-.355) if support else (.220,-.50,-.30))
    baseline_elbow=Vector((-.380,.005,-.170) if support else (.060,-.320,-.120))
    baseline_wrist=baseline_loc+base_basis@Vector((0,0,-.018));wanted_wrist=loc+basis@Vector((0,0,-.018))
    upper_length=(baseline_elbow-source_shoulder).length;fore_length=(baseline_wrist-baseline_elbow).length
    ray=wanted_wrist-source_shoulder;distance=ray.length;direction=ray.normalized()
    along=(upper_length**2-fore_length**2+distance**2)/(2*distance)
    hint=baseline_elbow-source_shoulder;bend=(hint-direction*hint.dot(direction)).normalized()
    source_elbow=source_shoulder+direction*along+bend*math.sqrt(max(0,upper_length**2-along**2))
    if support:
        palm_direction=basis@Vector((0,0,1));circle_radius=math.sqrt(max(0,upper_length**2-along**2))
        side=direction.cross(bend).normalized();candidates=[]
        for theta in np.linspace(0,math.tau,720,endpoint=False):
            candidate=source_shoulder+direction*along+(bend*math.cos(theta)+side*math.sin(theta))*circle_radius
            if candidate.z>wanted_wrist.z-.025:continue
            candidates.append(candidate)
        assert candidates,'reachable authored elbow below wrist'
        source_elbow=min(candidates,key=lambda e:(wanted_wrist-e).angle(palm_direction))
    shoulder=point(source_shoulder);elbow=point(source_elbow)
    root['grip_stance_adjustment_json']=json.dumps({'equipment_space_delta_m':list(loc-baseline_loc),'thumb_forward_axis_shift_m':list(thumb_forward_shift),'roll_degrees':8 if support else roll_degrees,'palm_yaw_degrees':50 if support else 0,'roll_axis':'equipment Y before yaw' if support else 'handle Z','upper_length_preserved_m':upper_length,'fore_length_preserved_m':fore_length,'source_shoulder_body_anchor':list(source_shoulder)})
    bones=[(name+'UpperArm',shoulder,elbow,None),(name+'ForeArm',elbow,(0,0,-.018),name+'UpperArm'),('wrist',(0,0,-.018),(0,0,.028),name+'ForeArm'),('palm',(0,0,.028),(0,0,.078),'wrist')]
    digits={2:'Index',3:'Middle',4:'Ring',5:'Little',1:'Thumb'}
    for f,fn in digits.items():
        previous='palm'
        for j in range(3):
            bn=name+fn+str(j+1);bones.append((bn,tuple(joints[f][j]),tuple(joints[f][j+1]),previous));previous=bn
    ad=bpy.data.armatures.new(name+'Skeleton');rig=bpy.data.objects.new(name+'Skeleton',ad);bpy.context.collection.objects.link(rig);rig.parent=root
    bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
    for bn,a,tail,pn in bones:
        b=ad.edit_bones.new(bn);b.head=a;b.tail=tail
        # Give every finger an anatomical flexion axis across the palm.
        if any(fn in bn for fn in digits.values()):b.align_roll(Vector((0,1,0)))
        if pn:b.parent=ad.edit_bones[pn]
    bpy.ops.object.mode_set(mode='OBJECT');rig.select_set(False)
    finger_axes={bone.name:transverse_hinge(bone) for bone in ad.bones if any(fn in bone.name for fn in ['Index','Middle','Ring','Little'])}
    # Flexion stays in the authored bone-local plane. The right reference
    # retains its existing baked rest; the left exports neutral skin bindings
    # and a default main pose through the supported glTF current-pose option.
    root['finger_flexion_axes_json']=json.dumps({key:list(value) for key,value in finger_axes.items()},sort_keys=True)
    mod=obj.modifiers.new('Upstream anatomical skin','ARMATURE');mod.object=rig;mod.use_deform_preserve_volume=not support
    angles=[(14,32,23),(16,34,24),(9,37,24),(8,30,18)] if support else [(30,36,22),(44,58,34),(42,54,34),(20,50,28)]
    # Fit every phalanx around the real housing/handle. Centreline samples
    # include measured source-skin thickness; a fingertip-only target permits
    # the middle phalanges to cut straight through the object.
    skin_radii=measured_radii
    skin_clouds={}
    if support:
        for digit in ['Index','Middle','Ring','Little']:
            for j in (1,2,3):
                b=ad.bones[name+digit+str(j)];group=obj.vertex_groups[b.name].index
                cloud=[]
                for v in obj.data.vertices:
                    if sum(g.weight for g in v.groups if g.group==group)<.55:continue
                    p=b.matrix_local.inverted()@v.co
                    if .2*b.length<p.y<.85*b.length:cloud.append((p.x,0,p.z))
                skin_clouds[b.name]=np.asarray(cloud)
                assert len(cloud)>8,(b.name,'skin direction samples')
    lamp_surface,surface_receipt=assembled_surface(bpy.data.objects['LampAssembly'])
    root['lamp_contact_surface_json']=json.dumps(surface_receipt)
    root['refined_finger_skin_radii_json']=json.dumps(skin_radii)
    print('REFINED_SKIN_RADII_MM',name,[[round(r*1000,3) for r in row] for row in skin_radii],flush=True)
    for f,fn in ([] if cached_pose else enumerate(['Index','Middle','Ring','Little'])):
        chain=[ad.bones[name+fn+str(j)] for j in range(1,4)]
        local_matrices=[b.parent.matrix_local.inverted()@b.matrix_local for b in chain]
        axes=[finger_axes[b.name] for b in chain]
        initial=-np.radians(angles[f]);a=initial.copy()
        def samples(a):
            transform=ad.bones['palm'].matrix_local.copy();values=[]
            for j,(b,local,axis) in enumerate(zip(chain,local_matrices,axes)):
                transform=transform@local@Quaternion(axis,float(a[j])).to_matrix().to_4x4()
                for t in np.linspace(.10,1,9):
                    p=fit_loc+basis@(transform@Vector((0,b.length*float(t),0)))
                    radius=skin_radii[f][j]
                    if support:
                        n=lamp_surface.find_nearest(p)[1]
                        local_direction=(basis@transform.to_3x3()).inverted()@(-n)
                        radial_projection=np.sum(skin_clouds[b.name]*np.asarray(local_direction),axis=1)
                        assert np.isfinite(radial_projection).all(),(b.name,'finite radial skin')
                        radius=float(np.quantile(radial_projection,.95))
                    values.append(lamp_surface.signed_distance(p)-radius)
            return np.array(values),fit_loc+basis@(transform@Vector((0,chain[-1].length,0)))
        def cost(a):
            d,tip=samples(a)
            claw=max(0.0,-a[2]+a[1]-.14)
            contact_weight=1.2 if support else .25
            return 300*float((np.minimum(d,0)**2).sum())+contact_weight*float(d[-1]**2)+.00012*float(((a-initial)**2).sum())+.0020*claw*claw
        candidates=[]
        for start in ([initial,np.radians([-35,-65,-35]),np.radians([-10,-85,-40])] if support else [initial]):
            a=start.copy()
            for step in np.radians([12,6,3,1,.25]):
                for iteration in range(50):
                    improved=False
                    for j in range(3):
                        for sign in [-1,1]:
                            lower=math.radians([-65,-100,-70][j]) if support else initial[j]-math.radians(22);upper=0 if support else min(0,initial[j]+math.radians(22))
                            trial=a.copy();trial[j]=np.clip(trial[j]+sign*step,lower,upper)
                            if cost(trial)<cost(a):a=trial;improved=True
                    if not improved:break
            candidates.append(a)
        a=min(candidates,key=cost)
        # Retain the accepted right middle-finger arc. The left four fingers
        # use the skin-aware solve in the final palm frame.
        contact_pose={('RightGrip','Middle'):(-25,-70,-20)}.get((name,fn))
        if contact_pose:a=np.radians(contact_pose)
        for j,(b,axis,angle) in enumerate(zip(chain,axes,a)):
            pb=rig.pose.bones[b.name];pb.rotation_mode='QUATERNION';pb.rotation_quaternion=Quaternion(axis,float(angle))
        clearance,tip=samples(a)
        print('FINGER_SHELL_CLEARANCE',name,fn,'angles_deg',np.degrees(a).tolist(),'min_mm',float(clearance.min()*1000),'tip_mm',float(clearance[-1]*1000),flush=True)
    # Thumb opposition is a separate CMC axis. Bending all three thumb joints
    # about the finger hinge had sent the pad through the lamp/onto the wrong side.
    thumb_names=[name+'Thumb'+str(j) for j in range(1,4)]
    thumb_bones=[ad.bones[n] for n in thumb_names]
    target_source=roll_pivot+palm_roll@(Vector((-.041,.133,.006) if support else (-.028,-.024,-.061))-roll_pivot)
    target=inv@(target_source-fit_loc)
    rest_parent=ad.bones['palm'].matrix_local.copy()
    local_rest=[];axes=[]
    for b in thumb_bones:
        local_rest.append(b.parent.matrix_local.inverted()@b.matrix_local)
        axes.append([b.matrix_local.to_3x3().inverted()@Vector(axis) for axis in [(1,0,0),(0,1,0),(0,0,1)]])
        if len(axes)>1:
            # Thumb IP/MCP flex across their own phalanx, not the other four
            # fingers' transverse axis; the thumb is oblique in the source hand.
            axes[-1][0]=thumb_hinge(b,support)
    root['thumb2_flexion_axis_local']=[float(v) for v in axes[1][0].normalized()]
    root['thumb_flexion_axes_json']=json.dumps({thumb_names[j]:list(axes[j][0]) for j in [1,2]})
    def thumb_rotations(a):
        return [Quaternion(axes[0][2],a[4])@Quaternion(axes[0][1],a[0])@Quaternion(axes[0][0],a[1]),Quaternion(axes[1][0],a[2]),Quaternion(axes[2][0],a[3])]
    def endpoint(a):
        transform=rest_parent.copy()
        for local,q in zip(local_rest,thumb_rotations(a)):transform=transform@local@q.to_matrix().to_4x4()
        return transform@Vector((0,thumb_bones[-1].length,0))
    initial=np.radians([-20,-23,-25,-18,10] if support else [18,0,-25,-18,-5]);a=initial.copy()
    windows=np.radians([12,12,10,8,10]);bounds=np.stack((initial-windows,initial+windows),axis=1)
    def error(a):
        transform=rest_parent.copy();collision=0.0;axial_limit=0.0
        for j,(b,local,q) in enumerate(zip(thumb_bones,local_rest,thumb_rotations(a))):
            transform=transform@local@q.to_matrix().to_4x4()
            for t in np.linspace(.10,1,9):
                p=fit_loc+basis@(transform@Vector((0,b.length*float(t),0)))
                skin_radius=([.018613,.014080,.009413] if support else [.012,.011,.009])[j]
                if support and j>0:axial_limit+=max(p.y-.150,0)**2
                radius=float(np.interp(p.z,[-.154,-.145,-.091,-.057,-.032,-.021],[.017,.018,.017,.017,.017,.015]))
                radial=math.hypot(p.x,p.y+.005)-radius
                cap=max(-.154-p.z,p.z+.021)
                signed=math.hypot(max(radial,0),max(cap,0))+min(max(radial,cap),0)-skin_radius
                collision+=min(signed,0)**2
                barrel_r=float(np.interp(p.y,[-.071,-.018,.030,.115,.151,.162],[.026,.033,.038,.041,.044,.039]))
                radial=math.hypot(p.x,p.z)-barrel_r;cap=max(-.071-p.y,p.y-.162)
                signed=math.hypot(max(radial,0),max(cap,0))+min(max(radial,cap),0)-skin_radius
                collision+=min(signed,0)**2
        return 200*collision+2000*axial_limit+.3*(endpoint(a)-target).length_squared+.00050*float(((a-initial)**2).sum())
    thumb_candidates=[]
    starts=[initial]
    if cached_pose:starts=[]
    for start in starts:
        a=np.clip(start,bounds[:,0],bounds[:,1])
        for step in np.radians([14,7,3,1,.3]):
            for iteration in range(45):
                improved=False
                for j in range(5):
                    for sign in [-1,1]:
                        trial=a.copy();trial[j]=np.clip(trial[j]+sign*step,*bounds[j])
                        if error(trial)<error(a):a=trial;improved=True
                if not improved:break
        thumb_candidates.append(a)
    a=np.asarray(cached_pose['thumb_angles']) if cached_pose else min(thumb_candidates,key=error)
    for bn,q in zip(thumb_names,thumb_rotations(a)):
        pb=rig.pose.bones[bn];pb.rotation_mode='QUATERNION';pb.rotation_quaternion=q
    thumb_tool_rest=None;thumb_tool_axes=None
    if support:
        # Preserve the old implement frame before correcting which side of
        # the thumb rests on the lamp. Opposition belongs at the CMC; MCP/IP
        # flex across the actual source nail/volar plane, without axial twist.
        bpy.context.view_layer.update()
        thumb_tool_rest={bn:rig.pose.bones[bn].matrix.copy() for bn in thumb_names}
        thumb_tool_axes={thumb_names[j]:list(axes[j][0]) for j in [1,2]}
        thumb_groups={obj.vertex_groups[bn].index for bn in thumb_names}
        thumb_ids={v.index for v in obj.data.vertices if sum(g.weight for g in v.groups if g.group in thumb_groups)>.5}
        nail_faces=[p for p in obj.data.polygons if 'keratin' in obj.data.materials[p.material_index].name and all(i in thumb_ids for i in p.vertices)]
        assert nail_faces, 'left thumb requires its actual source nail surface'
        actual_dorsal=sum((p.normal*p.area for p in nail_faces),Vector()).normalized()
        actual_hinges=[thumb_hinge(b,support,actual_dorsal) for b in thumb_bones[1:]]
        if cached_pose:actual_hinges=[Vector(v) for v in cached_pose['left_thumb_hinges']]
        cmc_axes=[(old_support_basis@thumb_bones[0].matrix_local.to_3x3()).inverted()@Vector(v) for v in [(1,0,0),(0,1,0),(0,0,1)]]
        cmc_degrees=(27.3,-5.7,82.4);flex_degrees=(-6.0,-6.0)
        cmc=Quaternion(cmc_axes[2],math.radians(cmc_degrees[2]))@Quaternion(cmc_axes[1],math.radians(cmc_degrees[1]))@Quaternion(cmc_axes[0],math.radians(cmc_degrees[0]))
        cmc=((basis@thumb_bones[0].matrix_local.to_3x3()).inverted()@(old_support_basis@thumb_bones[0].matrix_local.to_3x3()@cmc.to_matrix())).to_quaternion()
        selected=[cmc]+[Quaternion(axis,math.radians(deg)) for axis,deg in zip(actual_hinges,flex_degrees)]
        for bn,q in zip(thumb_names,selected):rig.pose.bones[bn].rotation_quaternion=q
        root['thumb2_flexion_axis_local']=list(actual_hinges[0])
        root['thumb_flexion_axes_json']=json.dumps({bn:list(axis) for bn,axis in zip(thumb_names[1:],actual_hinges)})
        root['thumb_direction_adjustment_json']=json.dumps({'method':'CMC opposition from neutral; actual source nail-derived MCP/IP volar hinges','actual_neutral_nail_normal':list(actual_dorsal),'forward_world_reference_euler_degrees':list(cmc_degrees),'cmc_quaternion_wxyz':list(cmc),'mcp_ip_flexion_degrees':list(flex_degrees),'nail_material_faces_measured':len(nail_faces)})
    if cached_pose:
        for bn,q in cached_pose['joint_rotations'].items():
            pb=rig.pose.bones[bn];pb.rotation_mode='QUATERNION';pb.rotation_quaternion=Quaternion(q)
        print('SHARED_HIGH_SOURCE_HAND_POSE',name,flush=True)
    else:
        lib.HAND_POSE_CACHE[name]={'thumb_angles':a.tolist(),'joint_rotations':{pb.name:list(pb.rotation_quaternion) for pb in rig.pose.bones}}
        if support:lib.HAND_POSE_CACHE[name]['left_thumb_hinges']=[list(v) for v in actual_hinges]
    if support:print('LEFT_THUMB_PAD_FACING',root['thumb_direction_adjustment_json'],flush=True)
    else:print('ANATOMICAL_THUMB_CONTACT',name,'angles',np.degrees(a).tolist(),'tip_error_m',(endpoint(a)-target).length,flush=True)
    # A local pose corrective relaxes the compressed index/thumb skin web.
    # It follows the corrected CMC and blended source weights; it changes the
    # real skin surface, not its shading or its visibility behind the handle.
    web_corrective=None
    if not support:
        web_center=Vector(joints[1][0])*.45+Vector(joints[2][0])*.55
        corrective_group=obj.vertex_groups.new(name='ThenarWebPoseCorrective')
        for v in obj.data.vertices:
            amount=max(0.0,1.0-(v.co-web_center).length/.034)
            if amount>0:corrective_group.add([v.index],amount*amount,'REPLACE')
        web_corrective=obj.modifiers.new('Local opposed-thumb web relaxation','SMOOTH')
        web_corrective.vertex_group=corrective_group.name;web_corrective.factor=.8;web_corrective.iterations=28
    if support:
        bpy.context.view_layer.update()
        main_rest={p.name:p.matrix.copy() for p in rig.pose.bones}
        root['contact_pad_corrective_json']=json.dumps({'method':'neutral skin retained; no contact compression; pose must fit the actual flesh'})
        root['neutral_bind_skin']=True
        root['authored_main_pose_quaternions_json']=json.dumps({p.name:list(p.rotation_quaternion) for p in rig.pose.bones})
        thumb_tool_rest={bn:ad.bones[bn].matrix_local.copy() for bn in thumb_names}
        thumb_tool_axes=json.loads(root['thumb_flexion_axes_json'])
    else:
        bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get();posed=bpy.data.meshes.new_from_object(obj.evaluated_get(dg),preserve_all_data_layers=True,depsgraph=dg)
        root['contact_pad_corrective_json']=json.dumps(compress_contact_pads(posed,obj,lamp_surface,loc,basis))
        bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='POSE');bpy.ops.pose.armature_apply(selected=False);bpy.ops.object.mode_set(mode='OBJECT');rig.select_set(False);obj.data=posed
    if web_corrective:obj.modifiers.remove(web_corrective)
    for polygon in obj.data.polygons:polygon.use_smooth=True
    sides=112 if high else 48
    # This measured section centre is offset from the joint marker to fit
    # the actual skin/cuff. Each arm is otherwise two straight limb sections.
    arm=articulated_sleeve(lib,name+'TailoredForearmSleeve',(0,.011,-.027),elbow,shoulder,cloth,root,rig,high)
    cuff=lib.turned(name+'TailoredWristCuff',[(-.035,.027),(-.029,.028),(-.014,.027),(-.010,.026),(-.018,.024),(-.034,.024),(-.035,.027)],cloth,root,'Z',sides=sides,steps=12 if high else 4,caps=False)
    for v in cuff.data.vertices:v.co.x*=1.06;v.co.y=v.co.y*.95+.011
    g=cuff.vertex_groups.new(name='wrist');g.add(list(range(len(cuff.data.vertices))),1,'REPLACE');mod=cuff.modifiers.new('Wrist cuff fit','ARMATURE');mod.object=rig
    if support:
        # Tool mounts share the actual palm frame, so a forearm/hand pose change
        # cannot leave an implement at an unrelated equipment-space coordinate.
        mount_basis=Matrix((Vector((0,0,1)),Vector((0,-1,0)),Vector((1,0,0)))).transposed()
        for kind,position in [('Luminol',(-.057,.020,.102)),('Salt',(-.041,.014,.107)),('Mud',(-.043,.025,.096))]:
            socket=lib.empty(kind+'GripSocket',root);socket.location=position;socket.rotation_euler=mount_basis.to_euler()
    if support:
        if cached_pose:
            for key,value in cached_pose['tool_metadata'].items():root[key]=value
            for socket in root.children:
                if socket.name in cached_pose['tool_sockets']:socket.location=cached_pose['tool_sockets'][socket.name]
        else:
            author_tool_poses(rig,root,name,thumb_tool_rest,thumb_tool_axes,main_rest,skin_clouds,obj)
            lib.HAND_POSE_CACHE[name]['tool_metadata']={key:root[key] for key in root.keys() if key.startswith('tool_grip_') or key.startswith('tool_absolute_') or key in ['luminol_contact_surface_json','salt_contact_surface_json','mud_contact_surface_json','salt_clearance_revision_json']}
            lib.HAND_POSE_CACHE[name]['tool_sockets']={socket.name:list(socket.location) for socket in root.children if socket.name.endswith('GripSocket')}
    root.location=loc;root.rotation_euler=basis.to_euler();root['anatomy_source']='MakeHuman hm08 CC0 hand, modified and independently posed';root['grip_role']='native left underside support' if support else 'right opposed pistol ring'
    return root


def author_tool_poses(rig,root,name,thumb_reference=None,thumb_reference_axes=None,main_rest=None,skin_clouds=None,neutral_skin=None):
    """Fit each implement from true neutral skin, then encode relative poses.

    Current main matrices become default glTF joint TRS while inverse binds
    stay neutral. Tool JSON uses xyzw relative to those default matrices.
    """
    ad=rig.data;all_poses={};contact_errors={};absolute_poses={}
    from skin_thumb_fit import ThumbSkinFit
    thumb_fit=ThumbSkinFit(neutral_skin,rig,name,json.loads(root['thumb_direction_adjustment_json'])['actual_neutral_nail_normal'])
    # Tool axes run across the palm (local X); dimensions match the builder.
    specs={'luminol':(-.057,.038,.085,.095,.021),'salt':(-.041,.032,.084,.069,.014),'mud':(-.043,.044,.080,.079,.026)}
    for kind,(x0,cy,cz,length,radius) in specs.items():
        socket=next(o for o in root.children if o.name=={'luminol':'Luminol','salt':'Salt','mud':'Mud'}[kind]+'GripSocket')
        socket.location.y=cy;socket.location.z=cz
        # Actual exported tool surfaces, including the narrow reagent shoulder
        # and rectangular packet, determine the thumb contact, not a cylinder.
        bpy.context.view_layer.update()
        tool=bpy.data.objects['Tool'+{'luminol':'Luminol','salt':'Salt','mud':'Mud'}[kind]]
        surface,receipt=assembled_surface(tool,socket.matrix_local@tool.matrix_world.inverted())
        root[kind+'_contact_surface_json']=json.dumps(receipt)
        pose={};errors={};absolute_pose={}
        for digit in ['Index','Middle','Ring','Little','Thumb']:
            chain=[ad.bones[name+digit+str(j)] for j in range(1,4)]
            solve_rest=[thumb_reference[b.name] if digit=='Thumb' and thumb_reference else b.matrix_local for b in chain]
            local=[(ad.bones['palm'].matrix_local if j==0 else solve_rest[j-1]).inverted()@m for j,m in enumerate(solve_rest)]
            if digit=='Thumb':
                # CMC opposition changes the approach plane. IP/MCP retain
                # independent transverse hinges, never rotate along the digit.
                world_axes=[Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1))]
                cmc_axes=[solve_rest[0].to_3x3().inverted()@v for v in world_axes]
                authored_thumb_axes=thumb_reference_axes or json.loads(root['thumb_flexion_axes_json'])
                hinges=[Vector(authored_thumb_axes[b.name]) for b in chain[1:]]
                target=Vector((x0+length+.010,cy,cz))
                contact,normal,_,_=surface.find_nearest(target)
                thumb_pad=.006 if kind=='salt' else .0035
                target=contact+normal*.0005
                def rotations(a):return [Quaternion(cmc_axes[2],float(a[2]))@Quaternion(cmc_axes[1],float(a[1]))@Quaternion(cmc_axes[0],float(a[0])),Quaternion(hinges[0],float(a[3])),Quaternion(hinges[1],float(a[4]))]
                initial=np.radians([0,0,0,-10,-10]);bounds=np.radians([[-30,60],[-60,45],[-70,60],[-70,65],[-65,65]])
                skin_radii=[.015,.012,thumb_pad]
            else:
                authored_axes=json.loads(root['finger_flexion_axes_json'])
                axes=[Vector(authored_axes[b.name]) for b in chain]
                target=Vector((max(x0+.007,min(x0+length-.007,chain[-1].tail_local.x)),cy+radius+.007,cz+.002))
                def rotations(a):return [Quaternion(axis,float(v)) for axis,v in zip(axes,a)]
                initial=np.radians([-20,-50,-30]);bounds=np.radians([[-75,15],[-110,0],[-80,0]])
                skin_radii=json.loads(root['refined_finger_skin_radii_json'])[['Index','Middle','Ring','Little'].index(digit)]
            def evaluate(a):
                matrix=ad.bones['palm'].matrix_local.copy();collision=0.0;pose_matrices={}
                for j,(b,m,q) in enumerate(zip(chain,local,rotations(a))):
                    matrix=matrix@m@q.to_matrix().to_4x4();pose_matrices[b.name]=matrix.copy()
                    for t in [.10,.22,.35,.50,.65,.80,1.0]:
                        v=matrix@Vector((0,b.length*t,0))
                        skin_radius=skin_radii[j]
                        if skin_clouds and b.name in skin_clouds:
                            normal=surface.find_nearest(v)[1];toward=matrix.to_3x3().inverted()@(-normal)
                            values=np.sum(skin_clouds[b.name]*np.asarray(toward),axis=1)
                            assert np.isfinite(values).all()
                            skin_radius=float(np.quantile(values,.95))
                        signed=surface.signed_distance(v)-skin_radius
                        collision+=min(signed,0)**2
                tip=matrix@Vector((0,chain[-1].length,0))
                closest,normal,_,_=surface.find_nearest(tip)
                if digit=='Thumb':
                    desired=target
                    actual_pad,actual_nail,actual_skin=thumb_fit.evaluate(pose_matrices);tip=Vector(actual_pad);posed_dorsal=Vector(actual_nail)
                    near,target_normal,_,_=surface.find_nearest(tip)
                    desired=near+target_normal*.0006
                    collision=sum(min(surface.signed_distance(Vector(v))+.0002,0)**2 for v in actual_skin)
                    orientation=.0003*(1-posed_dorsal.dot(target_normal))**2+.4*(tip-target).length_squared
                else:
                    desired=closest+normal*(.0035 if digit=='Little' else .0045)
                    local_volar=chain[-1].matrix_local.to_3x3().inverted()@Vector((0,1,0))
                    posed_volar=(matrix.to_3x3()@local_volar).normalized()
                    orientation=.00010*(1-posed_volar.dot(-normal))**2
                return (tip-desired).length_squared*8+collision*240+orientation+.000015*float(((a-initial)**2).sum()),tip
            candidates=[]
            for start in [initial,np.zeros(len(initial))]:
                a=start.copy()
                for step in np.radians([14,7,3,1,.3]):
                    for iteration in range(36):
                        improved=False
                        for j in range(len(a)):
                            for sign in [-1,1]:
                                trial=a.copy();trial[j]=np.clip(trial[j]+sign*step,*bounds[j])
                                if evaluate(trial)[0]<evaluate(a)[0]:a=trial;improved=True
                        if not improved:break
                candidates.append(a)
            a=min(candidates,key=lambda x:evaluate(x)[0]);final_tip=evaluate(a)[1]
            if digit!='Thumb':
                near,normal,_,_=surface.find_nearest(final_tip);target=near+normal*(.0035 if digit=='Little' else .0045)
            if digit=='Thumb':
                near,normal,_,_=surface.find_nearest(final_tip);target=near+normal*.0006
            errors[digit]=float((final_tip-target).length)
            for j,(bone,q) in enumerate(zip(chain,rotations(a))):
                absolute_pose[bone.name]=[float(q.x),float(q.y),float(q.z),float(q.w)]
                if main_rest:
                    # Convert all relative frames: the main grip now has both
                    # CMC opposition and true volar MCP/IP bending.
                    current_local=main_rest[bone.parent.name].inverted()@main_rest[bone.name]
                    q=(current_local.inverted()@local[j]).to_quaternion()@q
                pose[bone.name]=[float(q.x),float(q.y),float(q.z),float(q.w)]
            print('TOOL_POSE_CONTACT',kind,digit,'tip_target_error_mm',errors[digit]*1000,'angles',np.degrees(a).tolist(),flush=True)
        if kind=='salt':
            # The independent full-surface check found Index/Thumb crossings,
            # plus a small CMC/palm fold. Give the index its normal MCP side
            # clearance and open the CMC slightly; keep the other joint arcs.
            for digit,degrees in [('Index',-12.0),('Thumb',2.0)]:
                bone=ad.bones[name+digit+'1']
                axis=bone.matrix_local.to_3x3().inverted()@Vector((0,1,0))
                q=absolute_pose[bone.name]
                corrected=Quaternion(axis,math.radians(degrees))@Quaternion((q[3],q[0],q[1],q[2]))
                absolute_pose[bone.name]=[corrected.x,corrected.y,corrected.z,corrected.w]
                current_local=main_rest[bone.parent.name].inverted()@main_rest[bone.name]
                neutral_local=bone.parent.matrix_local.inverted()@bone.matrix_local
                relative=(current_local.inverted()@neutral_local).to_quaternion()@corrected
                pose[bone.name]=[relative.x,relative.y,relative.z,relative.w]
            socket.location.x=x0+.002
            root['salt_clearance_revision_json']=json.dumps({'index_mcp_source_palm_Y_splay_degrees':-12,'thumb_cmc_source_Y_opening_delta_degrees':2,'socket_source_X_shift_m':.002,'reason':'independent full-surface Index/Thumb crossing and CMC/palm fold; main and other implements retained'})
            bpy.context.view_layer.update()
            revised_surface,_=assembled_surface(tool,socket.matrix_local@tool.matrix_world.inverted())
            for digit in ['Index','Thumb']:
                matrix=ad.bones['palm'].matrix_local.copy();matrices={}
                for j in (1,2,3):
                    bone=ad.bones[name+digit+str(j)];local=bone.parent.matrix_local.inverted()@bone.matrix_local;q=absolute_pose[bone.name]
                    matrix=matrix@local@Quaternion((q[3],q[0],q[1],q[2])).to_matrix().to_4x4();matrices[bone.name]=matrix.copy()
                point=Vector(thumb_fit.evaluate(matrices)[0]) if digit=='Thumb' else matrix@Vector((0,bone.length,0))
                near,normal,_,_=revised_surface.find_nearest(point);padding=.0006 if digit=='Thumb' else .0045
                errors[digit]=(point-near-normal*padding).length
        all_poses[kind]=pose;contact_errors[kind]=errors;absolute_poses[kind]=absolute_pose
    root['tool_grip_poses_json']=json.dumps(all_poses,separators=(',',':'))
    root['tool_absolute_neutral_poses_json']=json.dumps(absolute_poses,separators=(',',':'))
    root['tool_grip_target_errors_json']=json.dumps(contact_errors,separators=(',',':'))
