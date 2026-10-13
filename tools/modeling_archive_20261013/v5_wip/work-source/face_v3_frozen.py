"""Separate, articulated eyes on the measured reconstructed face.

All coordinates are the adapter's Blender +Y forward, Z-up world. Original body
vertices, morph deltas and weights are retained; an optional bounded oral repair
removes the recorded broken interior faces. Eyes use separate native parts.
"""
import math, importlib.util
from pathlib import Path
import bmesh
import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

CLIPS = {'idle':3.2, 'walk':1.0, 'chase':.68, 'warn':.8, 'charge':.50, 'recover':2.0}


def material(name, color, roughness=.5):
    result=bpy.data.materials.new(name); result.use_nodes=True
    shader=result.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value=(*color,1)
    shader.inputs['Roughness'].default_value=roughness
    shader.inputs['Specular IOR Level'].default_value=.28
    return result


def mesh_object(name, vertices, faces, mat):
    mesh=bpy.data.meshes.new(name); mesh.from_pydata(vertices, [], faces); mesh.update()
    obj=bpy.data.objects.new(name,mesh); bpy.context.collection.objects.link(obj)
    mesh.materials.append(mat)
    for polygon in mesh.polygons: polygon.use_smooth=True
    return obj


def rigid_bind(obj, rig, bone):
    group=obj.vertex_groups.new(name=bone)
    group.add(list(range(len(obj.data.vertices))),1.0,'REPLACE')
    modifier=obj.modifiers.new('Native independent eye skin','ARMATURE'); modifier.object=rig
    obj.parent=rig


def colors_of(skin):
    attr=skin.data.color_attributes.active_color
    if attr is None: raise RuntimeError('Measured reconstructed face requires original linear vertex colors')
    colors=np.empty(len(attr.data)*4,dtype=np.float32); attr.data.foreach_get('color',colors); colors=colors.reshape(-1,4)
    if attr.domain=='POINT': return colors,attr
    if attr.domain!='CORNER': raise RuntimeError('Unsupported reconstructed color domain')
    loop_vertices=np.empty(len(skin.data.loops),dtype=np.int32); skin.data.loops.foreach_get('vertex_index',loop_vertices)
    averaged=np.zeros((len(skin.data.vertices),4),dtype=np.float32)
    np.add.at(averaged,loop_vertices,colors)
    averaged/=np.maximum(np.bincount(loop_vertices,minlength=len(averaged))[:,None],1)
    return averaged,attr


def eye_surface(center, radii, x, z, offset=0):
    normalized=(x/radii[0])**2+(z/radii[2])**2
    return (center[0]+x,center[1]+radii[1]*math.sqrt(max(.015,1-normalized))+offset,center[2]+z)


def cap(name, center, radii, extent, offset, mat, segments, rings, iris=False):
    vertices=[eye_surface(center,radii,0,0,offset)]; colors=[(.018,.048,.006,1)]
    for row in range(1,rings+1):
        t=row/rings
        for column in range(segments):
            theta=math.tau*column/segments
            vertices.append(eye_surface(center,radii,extent[0]*t*math.cos(theta),extent[1]*t*math.sin(theta),offset))
            fiber=.5+.23*math.sin(theta*67+.7*math.sin(t*14))+.15*math.sin(theta*103+t*9)
            ring=max(0,min(1,(1-t)/.13))
            colors.append((.013+.045*fiber*ring,.037+(.10+.11*fiber)*ring,.004+.011*ring,1))
    faces=[]
    for col in range(segments): faces.append((0,1+(col+1)%segments,1+col))
    for row in range(rings-1):
        first=1+row*segments; following=first+segments
        for col in range(segments):
            nxt=(col+1)%segments
            faces.append((first+col,first+nxt,following+nxt,following+col))
    obj=mesh_object(name,vertices,faces,mat)
    if iris:
        attr=obj.data.color_attributes.new(name='IrisFiberColor',type='FLOAT_COLOR',domain='POINT')
        attr.data.foreach_set('color',np.asarray(colors,dtype=np.float32).ravel())
        obj.data.color_attributes.active_color=attr
    return obj


class FaceSurface:
    """Read the actual reconstructed face, not an assumed spherical head."""
    def __init__(self, skin, vertices, colors):
        counts=np.empty(len(skin.data.polygons),dtype=np.int32)
        skin.data.polygons.foreach_get('loop_total',counts)
        if not np.all(counts==3): raise RuntimeError('Reconstructed face expects the actual triangulated source')
        loops=np.empty(len(skin.data.loops),dtype=np.int32); skin.data.loops.foreach_get('vertex_index',loops)
        triangles=loops.reshape(-1,3)
        mask=(np.abs(vertices[:,0])<.67)&(vertices[:,2]>1.75)&(vertices[:,2]<2.55)&(vertices[:,1]>.48)
        self.faces=triangles[np.all(mask[triangles],axis=1)]
        if not len(self.faces): raise RuntimeError('Cannot measure reconstructed eye surroundings')
        unique,inverse=np.unique(self.faces,return_inverse=True)
        self.vertices=vertices; self.colors=colors
        self.bvh=BVHTree.FromPolygons(vertices[unique].tolist(),inverse.reshape(-1,3).tolist(),all_triangles=True)
        self.material=skin.data.materials[0]
        self.color_layer=skin.data.color_attributes.active_color.name
        self.focus_delta=np.zeros_like(vertices)
        if skin.data.shape_keys and 'Focus' in skin.data.shape_keys.key_blocks:
            basis=np.empty(len(vertices)*3,dtype=np.float32); focus=np.empty_like(basis)
            skin.data.shape_keys.key_blocks['Basis'].data.foreach_get('co',basis)
            skin.data.shape_keys.key_blocks['Focus'].data.foreach_get('co',focus)
            self.focus_delta=(focus-basis).reshape(-1,3)
        self.probes={}
        self.missing_rays=0

    def sample(self, x, z):
        key=(round(x,8),round(z,8))
        if key in self.probes: return self.probes[key][:2]
        hit,normal,face,distance=self.bvh.ray_cast(Vector((x,3,z)),Vector((0,-1,0)),4)
        if hit is None:
            self.missing_rays+=1
            hit,normal,face,distance=self.bvh.find_nearest(Vector((x,.8,z)))
        if hit is None: raise RuntimeError('Face surface probe failed')
        indices=self.faces[face]; a,b,c=self.vertices[indices]
        v0=b-a; v1=c-a; v2=np.asarray(hit)-a
        d00=float(v0@v0); d01=float(v0@v1); d11=float(v1@v1); d20=float(v2@v0); d21=float(v2@v1)
        denominator=d00*d11-d01*d01
        if abs(denominator)<1e-18: weights=np.array([1/3,1/3,1/3])
        else:
            w1=(d11*d20-d01*d21)/denominator; w2=(d00*d21-d01*d20)/denominator
            weights=np.clip([1-w1-w2,w1,w2],0,1); weights/=weights.sum()
        self.probes[key]=(float(hit.y),weights@self.colors[indices,:3],weights@self.focus_delta[indices])
        return self.probes[key][:2]

    def focus_at(self, x, z):
        self.sample(x,z)
        return self.probes[(round(x,8),round(z,8))][2]


def lid_key(blink_index, focus_index):
    if blink_index==10 and focus_index==0: return 'Blink'
    if blink_index==0 and focus_index==10: return 'Focus'
    return 'LidB%03dF%03d'%(blink_index*10,focus_index*10)


def lid_weights(blink, focus, face_focus):
    # The same face expression drives body and lids. Independent additive
    # blink/focus deltas are invalid on a curved, continuous facial surface.
    result={lid_key(b,f):0.0 for b in range(11) for f in range(11) if b or f}
    b=max(0,min(1,float(blink)))*10; f=max(0,min(1,float(face_focus)))*10
    bi=min(9,int(b)); fi=min(9,int(f)); bt=b-bi; ft=f-fi
    for db,wb in [(0,1-bt),(1,bt)]:
        for df,wf in [(0,1-ft),(1,ft)]:
            if bi+db or fi+df: result[lid_key(bi+db,fi+df)]+=wb*wf
    return result


def conform_over_globe(points, center, radii, lip):
    projected=((points[:,0]-center[0])/radii[0])**2+((points[:,2]-center[2])/radii[2])**2
    signed=1-projected
    # A hard q<1 cutoff creates the circular step of a pasted spherical cap.
    # Continue the globe envelope smoothly into the actual facial surface.
    depth=np.sqrt((signed+np.sqrt(signed*signed+.05**2))*.5)
    safety=center[1]+radii[1]*depth+.0068+.0035+lip
    taper=np.clip((projected-1)/.8,0,1);taper=taper*taper*(3-2*taper)
    envelope=safety*(1-taper)+points[:,1]*taper
    epsilon=.006*(1-taper)
    points[:,1]=(points[:,1]+envelope+np.sqrt((points[:,1]-envelope)**2+epsilon*epsilon))*.5
    return points


def eyelid(name, center, radii, upper, skin_color, segments, rows, surface, landmarks):
    # The moving margin belongs to a facial patch that reaches the real head.
    # Closing changes a thin arc inside that patch, never the globe's size.
    center=np.asarray(center); radii=np.asarray(radii)
    u=np.linspace(-1,1,segments+1)
    v=np.concatenate(([0,.006,.022],np.linspace(.095,1,rows-2)))
    uu,vv=np.meshgrid(u,v); uu=uu.ravel(); vv=vv.ravel()
    arc=np.sqrt(np.maximum(0,1-uu*uu))
    edge_x=.98*radii[0]*uu
    outer_x=.20*uu
    outer_z=(.185 if upper else -.165)*arc
    xx=center[0]+edge_x*(1-vv)+outer_x*vv
    blend=vv*vv*(3-2*vv)
    body_cache={}
    body_follow=None
    def sample_body(xs,zs):
        ys=[]; rgb=[]
        for x,z in zip(xs,zs):
            key=(round(float(x),8),round(float(z),8))
            if key not in body_cache: body_cache[key]=surface.sample(float(x),float(z))
            y,color=body_cache[key]; ys.append(y); rgb.append(color)
        return np.asarray(ys),np.asarray(rgb)
    def shape(blink=0.0, focus=0.0):
        opening=(.94+(.36-.94)*focus) if upper else (-.92+(-.86+.92)*focus)
        edge_z=radii[2]*opening*arc
        # Like the inspected Rain control, the upper lid supplies most closure.
        # A high seam forces the lower cheek into an unnatural raised bag.
        closed=-.30*radii[2]*(1-uu*uu)
        closed+=(-.0005 if upper else .0005)*(1-uu*uu)
        edge_z=edge_z*(1-blink)+closed*blink
        zz=center[2]+edge_z*(1-vv)+outer_z*vv
        by,color=sample_body(xx,zz)
        reference=by.copy()
        side='left' if name.endswith('_left') else 'right'
        frame_info=landmarks.get('face_eye_frames',{}).get(side,{})
        if frame_info.get('head_surface_fit'):
            local=(xx-center[0])/radii[0]; vertical=(zz-center[2])/radii[2]
            ref_basis=np.column_stack((np.ones(len(xx)),local,vertical,local*local,local*vertical,vertical*vertical))
            fitted=np.einsum('ij,j->i',ref_basis,np.asarray(frame_info['head_surface_fit']))
            reference=fitted*(1-blend)+by*blend
        projected=((xx-center[0])/radii[0])**2+((zz-center[2])/radii[2])**2
        globe_front=center[1]+radii[1]*np.sqrt(np.maximum(0,1-projected))
        lip=(.0012 if upper else 0)*(1-uu*uu)*np.exp(-vv/.045)
        minimum=globe_front+.0068+.0035+lip
        ey=center[1]+radii[1]*np.sqrt(np.maximum(0,1-(edge_x/radii[0])**2-(edge_z/radii[2])**2))+.0103
        yy=ey*(1-blend)+by*blend
        yy=yy*(1-blink)+(reference+.00035)*blink
        join=np.clip((vv-.55)/.25,0,1);join=join*join*(3-2*join)
        yy=yy*(1-join)+(by+.00002)*join
        # Smooth the junction into the globe envelope instead of leaving a
        # curvature break that outlines a spherical button under closed skin.
        output=np.column_stack((xx,yy,zz))
        if body_follow is not None:
            output+=focus*body_follow
        output=conform_over_globe(output,center,radii,lip)
        return output,color
    faces=[]
    for row in range(rows):
        for col in range(segments):
            a=row*(segments+1)+col; b=a+segments+1
            face=(a,b,b+1,a+1)
            faces.append(face if upper else tuple(reversed(face)))
    neutral,colors=shape(); neutral=neutral.astype(np.float32)
    outer_follow=(vv*vv*(3-2*vv))[:,None]
    body_follow=np.asarray([surface.focus_at(float(point[0]),float(point[2])) for point in neutral])*outer_follow
    # Keep the original face's complete BRDF. A different specular/roughness
    # response makes even a geometrically continuous patch look pasted on.
    mat=surface.material.copy(); mat.name=name+' original facial BRDF'
    obj=mesh_object(name,neutral.tolist(),faces,mat)
    # A narrow native colored lip plus depth offset makes a visible closure
    # crease; the full patch follows sampled facial color at its outer edge.
    tint=np.ones_like(vv)
    tint[vv==0]=((.12 if upper else .65)+.25*uu[vv==0]**2)
    tint[vv==.006]=((.55 if upper else .90)+.10*uu[vv==.006]**2)
    attr=obj.data.color_attributes.new(name=surface.color_layer,type='FLOAT_COLOR',domain='POINT')
    attr.data.foreach_set('color',np.column_stack((colors*tint[:,None],np.ones(len(colors)))).astype(np.float32).ravel())
    obj.data.color_attributes.active_color=attr
    obj.shape_key_add(name='Basis')
    shapes=[(lid_key(b,f),shape(blink=b/10,focus=f/10)[0]) for b in range(11) for f in range(11) if b or f]
    for key_name,coordinates in shapes:
        key=obj.shape_key_add(name=key_name); key.data.foreach_set('co',np.asarray(coordinates,dtype=np.float32).ravel())
    return obj


def lid_animations(obj):
    keys=obj.data.shape_keys; keys.animation_data_create()
    for clip,duration in CLIPS.items():
        for track in keys.animation_data.nla_tracks: track.mute=True
        action=bpy.data.actions.new(clip+' / eyelid closure'); keys.animation_data.action=action
        count=round(duration*30)
        peak=.56 if clip=='idle' else .65
        samples={frame/count for frame in range(count+1)}
        if clip in ['idle','recover']:
            samples.add(peak)
            for value in np.arange(.1,1,.1):
                offset=.032*math.sqrt(-math.log(float(value)))
                samples.update([peak-offset,peak+offset])
        if clip=='warn':
            for value in np.arange(.1,.75,.1): samples.add(math.asin(float(value)/.75)*2/math.pi)
        for t in sorted(samples):
            frame=t*count
            blink=math.exp(-((t-peak)/.032)**2) if clip in ['idle','recover'] else 0.0
            focus={'idle':0,'walk':.10,'chase':.35,'warn':.72*math.sin(t*math.pi/2),'charge':.60,'recover':.17}[clip]
            focus*=1-blink
            face_focus=0 if clip=='idle' else .12 if clip=='walk' else .27 if clip=='chase' else .75*math.sin(t*math.pi/2) if clip=='warn' else .60 if clip=='charge' else .18
            for name,value in lid_weights(blink,focus,face_focus).items():
                keys.key_blocks[name].value=value; keys.key_blocks[name].keyframe_insert('value',frame=frame+1)
        for curve in action.fcurves:
            for key in curve.keyframe_points: key.interpolation='LINEAR'
        track=keys.animation_data.nla_tracks.new(); track.name=clip
        strip=track.strips.new(clip,1,action); strip.name=clip
        keys.animation_data.action=None
    for track in keys.animation_data.nla_tracks: track.mute=False


def attach_face(rig, skin, landmarks):
    level=int(landmarks.get('_lod_level',0)); segments=[96,64,32][max(0,min(2,level))]
    rings=[32,24,12][max(0,min(2,level))]
    vertices=np.empty(len(skin.data.vertices)*3,dtype=np.float32); skin.data.vertices.foreach_get('co',vertices); vertices=vertices.reshape(-1,3)
    colors,attribute=colors_of(skin); original_colors=colors.copy()
    mouth_recolored=0
    if landmarks.get('mouth_backwall_recolor',False):
        mouth=landmarks['mouth']
        mouth_ellipse=((vertices[:,0]-mouth[0])/.23)**2+((vertices[:,2]-mouth[2])/.14)**2
        recessed=(mouth_ellipse<.75)&(vertices[:,1]>.55)&(vertices[:,1]<.82)
        yellow=recessed&(colors[:,0]>.16)&(colors[:,1]>.055)&(colors[:,2]<.13)&(colors[:,0]>colors[:,1]*1.25)&(colors[:,1]>colors[:,2]*1.6)
        dark=recessed&(colors[:,0]<.2)&(colors[:,1]<.04)&(colors[:,2]<.03)
        tone=np.median(colors[dark,:3],axis=0) if dark.sum()>20 else np.array([.028,.007,.003])
        tone=np.clip(tone,[.02,.004,.001],[.10,.018,.008])
        colors[yellow,:3]=tone
        mouth_recolored=int(yellow.sum())
    socket_delta=np.zeros_like(vertices)
    objects=[]; animated=[]; measurements={}
    for side,sign in [('left',-1),('right',1)]:
        region=(vertices[:,0]*sign>.10)&(vertices[:,0]*sign<.60)&(vertices[:,2]>1.90)&(vertices[:,2]<2.40)&(vertices[:,1]>.55)
        green=region&(colors[:,1]>colors[:,0]*1.20)&(colors[:,1]>colors[:,2]*1.65)&(colors[:,1]>.05)
        if green.sum()<20: raise RuntimeError('Cannot locate measured green iris: '+side)
        points=vertices[green]; center=points.mean(axis=0).astype(float)
        white=region&(np.abs(vertices[:,0]-center[0])<.20)&(np.abs(vertices[:,2]-center[2])<.21)&(colors[:,2]>.50)&(np.abs(colors[:,0]-colors[:,2])<.17)
        if white.sum()>20:
            bounds=np.percentile(vertices[white],[2,98],axis=0)
            rx=float(np.clip((bounds[1,0]-bounds[0,0])*.55,.096,.122))
            rz=float(np.clip((bounds[1,2]-bounds[0,2])*.55,.110,.132))
        else: rx,rz=.105,.12
        center[1]=float(np.percentile(points[:,1],98))-.052
        # A reviewed frame can keep both anatomical eye sizes and their socket
        # positions identical across LODs; decimation must not refit the gaze.
        eye_frame=landmarks.get('face_eye_frames',{}).get(side)
        if eye_frame:
            center=np.asarray(eye_frame['center'],dtype=float)
            rx,depth,rz=eye_frame['radii']
        else: depth=.069
        radii=(rx,depth,rz)
        ellipse=((vertices[:,0]-center[0])/rx)**2+((vertices[:,2]-center[2])/rz)**2
        nearby=region&(ellipse>1.5)&(ellipse<4.0)&(colors[:,0]>colors[:,1]*1.10)&(colors[:,1]>colors[:,2]*1.35)
        skin_color=np.median(colors[nearby,:3],axis=0) if nearby.sum()>20 else np.array([.72,.46,.09])
        mask=region&(ellipse<3.0)&(vertices[:,1]>center[1]-.17)
        # Reconstruct the local yellow gradient from the surrounding original
        # surface. A constant median creates an obvious circular painted patch.
        dx=(vertices[:,0]-center[0])/rx; dz=(vertices[:,2]-center[2])/rz
        basis=np.column_stack((np.ones(len(vertices)),dx,dz,dx*dx,dx*dz,dz*dz))
        if nearby.sum()>20:
            fitted=np.linalg.lstsq(basis[nearby],colors[nearby,:3],rcond=None)[0]
            replacement=np.einsum('ij,jk->ik',basis[mask],fitted)
            replacement=np.clip(replacement,np.percentile(colors[nearby,:3],1,axis=0),np.percentile(colors[nearby,:3],99,axis=0))
            skin_color=np.clip(fitted[0],0,1)
        else: replacement=np.broadcast_to(skin_color,(int(mask.sum()),3))
        blend=np.clip((3.0-ellipse[mask])/(3.0-1.65),0,1)
        blend=blend*blend*(3-2*blend)
        original_eye_paint=(green|white|((colors[:,0]<.08)&(colors[:,1]<.08)&(colors[:,2]<.08)))
        blend[original_eye_paint[mask]]=1
        colors[mask,:3]=colors[mask,:3]*(1-blend[:,None])+replacement*blend[:,None]
        if landmarks.get('preserve_eye_head_surface',False):
            pass
        elif eye_frame and eye_frame.get('head_surface_fit'):
            local=(vertices[:,0]-center[0])/rx; vertical=(vertices[:,2]-center[2])/rz
            frame_basis=np.column_stack((np.ones(len(vertices)),local,vertical,local*local,local*vertical,vertical*vertical))
            fitted_y=np.einsum('ij,j->i',frame_basis,np.asarray(eye_frame['head_surface_fit']))
            transition=np.clip((3.5-ellipse)/1.5,0,1);transition=transition*transition*(3-2*transition)
            blend=region&(ellipse<3.5)
            socket_delta[blend,1]+=np.clip(fitted_y[blend]-vertices[blend,1],-.04,.04)*transition[blend]
        else:
            socket=region&(ellipse<1.75)&(vertices[:,1]>center[1]-.13)
            socket_delta[socket,1]-=.080*np.maximum(0,1-ellipse[socket]/1.75)**2
        if landmarks.get('clear_eye_aperture',False):
            aperture=region&(ellipse<1.2)&(vertices[:,1]>center[1]-.13)
            q=ellipse[aperture];signed=1-q
            depth=np.sqrt((signed+np.sqrt(signed*signed+.05**2))*.5)
            behind_globe=center[1]+radii[1]*depth-.010
            taper=np.clip((q-.65)/.55,0,1);taper=taper*taper*(3-2*taper)
            current=vertices[aperture,1]+socket_delta[aperture,1]
            target=behind_globe*(1-taper)+current*taper
            epsilon=.001*(1-taper)
            lowered=(current+target-np.sqrt((current-target)**2+epsilon*epsilon))*.5
            socket_delta[aperture,1]=lowered-vertices[aperture,1]
        sclera_mat=material('Reconstructed '+side+' sclera',(.81,.86,.81),.28)
        bpy.ops.mesh.primitive_uv_sphere_add(segments=segments,ring_count=rings,location=center)
        globe=bpy.context.object; globe.name='ReconstructedSclera_'+side; globe.scale=radii
        bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
        # Mesh vertices are world-space like the body and all other attachments.
        bpy.ops.object.transform_apply(location=True,rotation=False,scale=False)
        globe.data.materials.append(sclera_mat)
        for polygon in globe.data.polygons: polygon.use_smooth=True
        iris_mat=material('Reconstructed '+side+' layered green iris',(.05,.18,.01),.31)
        node=iris_mat.node_tree.nodes.new('ShaderNodeVertexColor'); node.layer_name='IrisFiberColor'
        iris_mat.node_tree.links.new(node.outputs['Color'],iris_mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
        iris=cap('ReconstructedIris_'+side,center,radii,(rx*.76,rz*.76),.0022,iris_mat,segments,rings,True)
        pupil=cap('ReconstructedPupil_'+side,center,radii,(rx*.53,rz*.53),.0042,material('Reconstructed '+side+' pupil',(.0007,.001,.0005),.22),segments,max(8,rings//2))
        cornea_mat=material('Reconstructed transparent cornea '+side,(1.0,1.0,1.0),.025)
        principled=cornea_mat.node_tree.nodes['Principled BSDF']; principled.inputs['Transmission Weight'].default_value=1; principled.inputs['IOR'].default_value=1.376
        cornea=cap('ReconstructedCorneal_'+side,center,radii,(rx*.90,rz*.90),.0068,cornea_mat,segments,rings)
        for obj in [globe,iris,pupil,cornea]:
            rigid_bind(obj,rig,'eye_'+side); objects.append(obj)
        # Eyelid closure returns to the actual facial reference, not the open
        # eye socket that was recessed to reveal the iris.
        surface=FaceSurface(skin,vertices,colors)
        for upper in [True,False]:
            lid=eyelid(('Upper' if upper else 'Lower')+'Eyelid_'+side,center,radii,upper,skin_color,max(64,segments),max(32,rings),surface,landmarks)
            rigid_bind(lid,rig,'head'); lid_animations(lid); objects.append(lid); animated.append(lid)
        measurements[side]={'center':list(center),'radii':list(radii),'explicit_lod_stable_frame':bool(eye_frame),'iris_source_vertices':int(green.sum()),'repainted_body_vertices':int(mask.sum()),'lid_skin_linear_rgb':skin_color.tolist()}
    if attribute.domain=='POINT': attribute.data.foreach_set('color',colors.ravel())
    else:
        loop_vertices=np.empty(len(skin.data.loops),dtype=np.int32); skin.data.loops.foreach_get('vertex_index',loop_vertices)
        attribute.data.foreach_set('color',colors[loop_vertices].ravel())
    # Inset the former fused eye bulge behind the independent globe. Every body
    # shape key receives the same offset so its actual expression deltas survive.
    adjusted=vertices+socket_delta
    key_arrays=[]
    if skin.data.shape_keys:
        for key in skin.data.shape_keys.key_blocks:
            points=np.empty(len(key.data)*3,dtype=np.float32); key.data.foreach_get('co',points)
            key_arrays.append((key,points.reshape(-1,3)+socket_delta))
    skin.data.vertices.foreach_set('co',adjusted.ravel())
    for key,points in key_arrays: key.data.foreach_set('co',points.ravel())
    skin.data.update()
    oral_manifest=None
    if landmarks.get('measured_oral_bag',False):
        bag,oral_manifest=measured_oral_bag(rig,skin,landmarks,max(64,segments),max(24,rings))
        oral_manifest['inner_surface_cleanup']=remove_broken_inner_faces(skin)
        objects.append(bag);animated.append(bag)
    return {'objects':objects,'animated_objects':animated,
            'manifest':{'Blink':True,'Focus':True,'independent_globes':True,'eyeball_squashing':False,
                        'measured_eyes':measurements,'objects':len(objects),'source_body_topology_unchanged':oral_manifest is None,
                        'source_body_vertices_morphs_weights_preserved':True,'oral_bag':oral_manifest,
                        'former_eye_bulge_inset_max_m':float(np.abs(socket_delta[:,1]).max()),
                        'continuous_facial_lids':True,'closure_seam_lower_than_eye_center':True,
                        'recessed_mouth_recolored_vertices':mouth_recolored,
                        'repaint_max_linear_delta':float(np.max(np.abs(colors-original_colors)))}}


def oral_coordinates(key_or_mesh):
    data=key_or_mesh.data if hasattr(key_or_mesh,'data') else key_or_mesh.vertices
    output=np.empty(len(data)*3,dtype=np.float32);data.foreach_get('co',output)
    return output.reshape(-1,3)


def measured_oral_bag(rig,skin,landmarks,segments=96,rows=32):
    source=oral_coordinates(skin.data.shape_keys.key_blocks['Basis'])
    loops=np.empty(len(skin.data.loops),dtype=np.int32);skin.data.loops.foreach_get('vertex_index',loops)
    faces=loops.reshape(-1,3)
    region=(np.abs(source[:,0])<.48)&(source[:,2]>1.54)&(source[:,2]<2.02)&(source[:,1]>.36)
    candidates=faces[np.all(region[faces],axis=1)]
    ids,inverse=np.unique(candidates,return_inverse=True)
    bvh=BVHTree.FromPolygons(source[ids].tolist(),inverse.reshape(-1,3).tolist(),all_triangles=True)
    center=np.array([landmarks['mouth'][0],.61,landmarks['mouth'][2]+.061])
    source_open=oral_coordinates(skin.data.shape_keys.key_blocks['Open'])
    source_delta=source_open-source
    rim=[];rim_delta=[]
    for index in range(segments):
        theta=math.tau*index/segments
        x=center[0]+.203*math.cos(theta);z=center[2]+.119*math.sin(theta)
        hit,normal,face,distance=bvh.ray_cast(Vector((x,3,z)),Vector((0,-1,0)),4)
        if hit is None:raise RuntimeError('Actual reconstructed mouth rim ray missed')
        rim.append((x,float(hit.y)-.003,z))
        ids=candidates[face];a,b,c=source[ids]
        v0=b-a;v1=c-a;v2=np.asarray(hit)-a
        denominator=float((v0@v0)*(v1@v1)-(v0@v1)**2)
        w1=float(((v1@v1)*(v2@v0)-(v0@v1)*(v2@v1))/denominator)
        w2=float(((v0@v0)*(v2@v1)-(v0@v1)*(v2@v0))/denominator)
        rim_delta.append(np.array([1-w1-w2,w1,w2])@source_delta[ids])
    rim=np.asarray(rim)
    rim_delta=np.asarray(rim_delta);center_delta=rim_delta.mean(axis=0)
    vertices=[center.tolist()];open_delta=[center_delta]
    for row in range(1,rows+1):
        t=row/rows
        for index,endpoint in enumerate(rim):
            p=center+(endpoint-center)*t
            p[1]=center[1]+(endpoint[1]-center[1])*t**3
            vertices.append(p.tolist())
            # Extend the actual lip motion through the recessed bag. Applying
            # the external skin's depth mask to a deep wall makes it buckle.
            open_delta.append(center_delta*(1-t)+rim_delta[index]*t)
    faces=[]
    for col in range(segments):faces.append((0,1+(col+1)%segments,1+col))
    for row in range(rows-1):
        a=1+row*segments;b=a+segments
        for col in range(segments):
            nxt=(col+1)%segments;faces.append((a+col,a+nxt,b+nxt,b+col))
    mesh=bpy.data.meshes.new('Measured recessed oral bag')
    mesh.from_pydata(vertices,[],faces);mesh.update()
    obj=bpy.data.objects.new('ReconstructedOralLining',mesh);bpy.context.collection.objects.link(obj)
    mat=bpy.data.materials.new('Measured dark oral interior');mat.use_nodes=True
    shader=mat.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value=(.026,.0025,.0013,1)
    shader.inputs['Roughness'].default_value=.78
    shader.inputs['Specular IOR Level'].default_value=.18
    pigment=mesh.color_attributes.new(name='Measured oral mucosa',type='FLOAT_COLOR',domain='POINT')
    points=np.asarray(vertices,dtype=np.float32)
    lower=np.clip(((center[2]-points[:,2])/.119-.30)/.65,0,1)
    lower=lower*lower*(3-2*lower)
    pigment.data.foreach_set('color',np.column_stack((np.array([.026,.0025,.0013])[None,:]*(1-lower[:,None])+np.array([.42,.115,.13])[None,:]*lower[:,None],np.ones(len(points)))).astype(np.float32).ravel())
    mesh.color_attributes.active_color=pigment
    vertex=mat.node_tree.nodes.new('ShaderNodeVertexColor');vertex.layer_name=pigment.name
    mat.node_tree.links.new(vertex.outputs['Color'],shader.inputs['Base Color'])
    mesh.materials.append(mat)
    for p in mesh.polygons:p.use_smooth=True
    # Use exactly the same source morph recipe and native four-weight skinning.
    spec=importlib.util.spec_from_file_location('reconstructed_binding_for_oral_bag',Path('/Users/lpz/Documents/Happy_Dash_Forward/tools/bind_reconstructed_nailong.py'))
    binder=importlib.util.module_from_spec(spec);spec.loader.exec_module(binder)
    binder.bind(obj,rig)
    binder.add_facial_morphs(obj,landmarks)
    corrected_open=np.asarray(vertices,dtype=np.float32)+np.asarray(open_delta,dtype=np.float32)
    obj.data.shape_keys.key_blocks['Open'].data.foreach_set('co',corrected_open.ravel())
    binder.facial_tracks(obj)
    return obj,{'vertices':len(vertices),'polygons':len(faces),'rim_range_m':[rim.min(axis=0).tolist(),rim.max(axis=0).tolist()],'source_body_modified':False,'oral_bag_open_actual_lip_boundary_corrective':True,'open_rim_barycentric_delta':rim_delta.tolist(),'open_center_delta':center_delta.tolist(),'oral_bag_same_six_clips':True,'uses_original_four_influence_weight_recipe':True}


def remove_broken_inner_faces(skin):
    """Remove tangential, recessed oral patches; retain original vertex IDs.

    The front facing exterior is outside the bounded normal/depth mask.
    Original source keys and group weights stay on every original vertex.
    """
    mesh=skin.data;vertices=oral_coordinates(mesh.shape_keys.key_blocks['Basis'])
    loops=np.empty(len(mesh.loops),dtype=np.int32);mesh.loops.foreach_get('vertex_index',loops)
    faces=loops.reshape(-1,3)
    colors=mesh.color_attributes.active_color
    rgba=np.empty(len(colors.data)*4,dtype=np.float32);colors.data.foreach_get('color',rgba);rgba=rgba.reshape(-1,4)
    face_colors=rgba.reshape(-1,3,4).mean(axis=1) if colors.domain=='CORNER' else rgba[faces].mean(axis=1)
    ellipse=(vertices[:,0]/.200)**2+((vertices[:,2]-1.811)/.118)**2
    internal=(ellipse<1.0)&(vertices[:,1]>.35)&(vertices[:,1]<1.055)
    triangles=vertices[faces]
    normals=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0])
    normals/=np.maximum(np.linalg.norm(normals,axis=1)[:,None],1e-15)
    # The real exterior faces toward +Y. The broken roof, throat and tongue
    # fragments lie along inward, tangential surfaces behind the outer lip.
    inside_surface=(normals[:,1]<.62)|(np.max(triangles[:,:,1],axis=1)<.94)
    remove=np.all(internal[faces],axis=1)&inside_surface
    deleted=np.flatnonzero(remove)
    if not len(deleted):
        return {'deleted_original_polygon_ids':[],'deleted_original_polygons':0,'original_vertex_ids_preserved':True,'retained_triangles_exact':True,'retained_corner_colors_exact':True,'front_facing_exterior_scope_excluded':True}
    expected_faces=faces[~remove]
    expected_colors=rgba[np.repeat(~remove,3)] if colors.domain=='CORNER' else rgba.copy()
    original_ids=mesh.attributes.new(name='MouthRepairOriginalVertexID',type='INT',domain='POINT')
    original_ids.data.foreach_set('value',np.arange(len(vertices),dtype=np.int32))
    bm=bmesh.new();bm.from_mesh(mesh);bm.faces.ensure_lookup_table()
    bmesh.ops.delete(bm,geom=[bm.faces[int(i)] for i in deleted],context='FACES_ONLY')
    bm.to_mesh(mesh);bm.free();mesh.update()
    actual_ids=np.empty(len(mesh.vertices),dtype=np.int32);mesh.attributes['MouthRepairOriginalVertexID'].data.foreach_get('value',actual_ids)
    actual_loops=np.empty(len(mesh.loops),dtype=np.int32);mesh.loops.foreach_get('vertex_index',actual_loops)
    actual_colors=np.empty(len(mesh.color_attributes.active_color.data)*4,dtype=np.float32);mesh.color_attributes.active_color.data.foreach_get('color',actual_colors);actual_colors=actual_colors.reshape(-1,4)
    if not np.array_equal(actual_ids,np.arange(len(vertices))):raise RuntimeError('Face-only repair changed original vertex correspondence')
    if not np.array_equal(actual_loops.reshape(-1,3),expected_faces):raise RuntimeError('Face-only repair changed a retained triangle')
    if not np.array_equal(actual_colors,expected_colors):raise RuntimeError('Face-only repair changed a retained color')
    return {'deleted_original_polygon_ids':deleted.tolist(),'deleted_original_polygons':int(len(deleted)),'deleted_vertex_coordinate_bounds':[vertices[faces[remove]].min(axis=(0,1)).tolist(),vertices[faces[remove]].max(axis=(0,1)).tolist()],'original_vertex_ids_preserved':True,'retained_triangles_exact':True,'retained_corner_colors_exact':True,'front_facing_exterior_scope_excluded':True}
