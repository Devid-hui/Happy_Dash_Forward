"""Reproducible reference-specific NaiFrog, Blender 4.5 LTS.

Stage one: --stage shape --preview-dir PATH. No old Nailong mesh/topology loaded.
Blender Z up and +Y facing; Godot Y up and -Z facing after glTF export.
"""
import bpy
import bmesh
import math
import sys
import json
import hashlib
import numpy as np
from pathlib import Path
from mathutils import Vector

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
def argument(name, default):
    return ARGS[ARGS.index(name) + 1] if name in ARGS else default
ROOT = Path(argument('--repo', str(Path(__file__).resolve().parents[1]))).resolve()
STAGE = argument('--stage', 'shape')
PREVIEW = Path(argument('--preview-dir', str(ROOT / 'source_assets/naifrog/model/previews'))).resolve()
SOURCE = ROOT / 'source_assets/naifrog/model'
OUT = ROOT / 'assets/refined/naifrog'
for directory in (SOURCE, OUT, PREVIEW):
    directory.mkdir(parents=True, exist_ok=True)
(SOURCE / '.gdignore').touch()

# An independently authored small head and wide pear torso. Values are design
# targets, not measurements of three-dimensional distances in the user photo.
PROFILE = [(.75,.10,.10,-.04),(.88,.39,.30,-.03),(1.03,.64,.47,-.015),
           (1.27,.79,.59,.015),(1.50,.80,.585,.02),(1.73,.725,.51,.025),
           (1.94,.565,.415,.035),(2.12,.425,.340,.050),
           (2.27,.325,.275,.075),(2.40,.328,.270,.120),
           (2.53,.330,.265,.140),(2.64,.285,.220,.145),
           (2.71,.18,.130,.140),(2.735,.085,.050,.135),(2.742,.003,.003,.135)]
PROFILE=[(z,rx*(1-.08*max(0,min(1,(z-2.10)/.24))),ry,cy) for z,rx,ry,cy in PROFILE]
EYE_X = .127
EYE_Z = 2.626
EYE_RADIUS = .062
MOUTH_Z = 2.447
MOUTH_RX = .108
MOUTH_RZ = .006
MANIFEST = {'generator':'tools/build_naifrog_asset.py', 'blender':bpy.app.version_string,
    'reference':'User supplied naifrog-primary-reference.png; small head, wide pear belly, standing legs, olive hands and feet; no visible tail',
    'license':'Original authored meshes and maps; reference-character rights are not conferred by this file.',
    'coordinate_system':'Blender Z up +Y facing -> Godot Y up -Z facing',
    'stage':STAGE, 'clips':{}, 'validation':{'godot_run':False}}

def clear():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for action in list(bpy.data.actions):
        bpy.data.actions.remove(action)

def catmull(values, t):
    q=max(0,min(len(values)-1.000001,t*(len(values)-1)))
    i=int(q); f=q-i
    a=np.asarray(values[max(0,i-1)]); b=np.asarray(values[i])
    c=np.asarray(values[i+1]); d=np.asarray(values[min(i+2,len(values)-1)])
    return .5*((2*b)+(-a+c)*f+(2*a-5*b+4*c-d)*f*f+(-a+3*b-3*c+d)*f*f*f)

SAMPLES=np.asarray([catmull(PROFILE,t) for t in np.linspace(0,1,1200)])
def profile_at(z):
    return tuple(np.interp(z,SAMPLES[:,0],SAMPLES[:,i]) for i in (1,2,3))

def front_surface(x,z):
    rx,ry,cy=profile_at(z)
    sine=math.sqrt(max(0,1-(x/max(rx,.001))**2))
    return cy+ry*sine+face_sculpt(x,z)*sine**12

def eye_frame(cx,cz):
    step=.0005
    dx=(front_surface(cx+step,cz)-front_surface(cx-step,cz))/(2*step)
    dz=(front_surface(cx,cz+step)-front_surface(cx,cz-step))/(2*step)
    normal=Vector((-.55*dx,1,-.55*dz)).normalized()
    horizontal=Vector((1,.55*dx,0)).normalized()
    vertical=horizontal.cross(normal).normalized()
    return Vector((cx,front_surface(cx,cz),cz)),horizontal,vertical,normal

def face_sculpt(x,z):
    # Shallow rounded eyelid hoods emerge from the continuous head surface.
    hoods=sum(.026*math.exp(-((x-s*EYE_X)/.10)**2-((z-EYE_Z)/.10)**2) for s in (-1,1))
    muzzle=.014*math.exp(-(x/.19)**4-((z-MOUTH_Z)/.13)**2)
    smile=MOUTH_Z+.013*(x/MOUTH_RX)**2
    groove=.005*math.exp(-(x/MOUTH_RX)**8-((z-smile)/.009)**2)
    return hoods+muzzle-groove

def material(name,color,rough=.58,subsurface=0):
    m=bpy.data.materials.new(name); m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Roughness'].default_value=rough
    p.inputs['Specular IOR Level'].default_value=.25
    p.inputs['Subsurface Weight'].default_value=subsurface
    p.inputs['Subsurface Radius'].default_value=(.15,.11,.06)
    return m

def mesh_object(name,vertices,faces,mat):
    data=bpy.data.meshes.new(name)
    data.from_pydata(vertices,[],faces); data.update()
    obj=bpy.data.objects.new(name,data); bpy.context.collection.objects.link(obj)
    data.materials.append(mat)
    for p in data.polygons:p.use_smooth=True
    return obj

def trunk(mat,rings=290,sides=224):
    vs=[];fs=[]
    for i in range(rings):
        z,rx,ry,cy=catmull(PROFILE,i/(rings-1));rx=max(.002,rx);ry=max(.002,ry)
        for j in range(sides):
            a=math.tau*j/sides;x=rx*math.cos(a)
            y=cy+ry*math.sin(a)+max(0,math.sin(a))**12*face_sculpt(x,z)
            vs.append((x,y,z))
    for i in range(rings-1):
        for j in range(sides):
            fs.append((i*sides+j,i*sides+(j+1)%sides,(i+1)*sides+(j+1)%sides,(i+1)*sides+j))
    fs.append(tuple(reversed(range(sides))))
    fs.append(tuple((rings-1)*sides+j for j in range(sides)))
    return mesh_object('NaiFrog pear trunk and small head block',vs,fs,mat)

def sweep(name,controls,radii,mat,sides=72,steps=24,flatten=1):
    n=(len(controls)-1)*steps+1;vs=[];fs=[];normal=None
    for i in range(n):
        t=i/(n-1);center=Vector(catmull(controls,t));r=max(.001,float(catmull(radii,t)))
        tangent=(Vector(catmull(controls,min(1,t+.001)))-Vector(catmull(controls,max(0,t-.001)))).normalized()
        if normal is None:
            axis=Vector((0,0,1)) if abs(tangent.z)<.9 else Vector((1,0,0))
            normal=tangent.cross(axis).normalized()
        else:normal=(normal-tangent*normal.dot(tangent)).normalized()
        bitangent=tangent.cross(normal).normalized()
        for j in range(sides):
            a=math.tau*j/sides
            vs.append(tuple(center+r*(normal*math.cos(a)+bitangent*math.sin(a)*flatten)))
    for i in range(n-1):
        for j in range(sides):fs.append((i*sides+j,i*sides+(j+1)%sides,(i+1)*sides+(j+1)%sides,(i+1)*sides+j))
    fs.extend([tuple(reversed(range(sides))),tuple((n-1)*sides+j for j in range(sides))])
    return mesh_object(name,vs,fs,mat)

def continuous_skin(mat):
    parts=[trunk(mat)]
    for side,s in [('left',-1),('right',1)]:
        # Stand naturally: broad hip, genuine thigh/knee/calf, a small flat forefoot.
        leg=sweep('NaiFrog '+side+' standing leg',
            [(s*.295,-.01,1.16),(s*.43,.0,.82),(s*.465,-.014,.49),
             (s*.475,.005,.255),(s*.475,.064,.13),(s*.475,.195,.095),(s*.475,.30,.10)],
            [.257,.220,.150,.096,.098,.118,.008],mat,sides=96,steps=30)
        for v in leg.data.vertices:
            if v.co.z<.055:v.co.z=.014+.012*math.log1p(math.exp((v.co.z-.014)/.012))
        parts.append(leg)
        # Soft bent arms and mitten palms have one fused skin surface.
        arm=sweep('NaiFrog '+side+' lowered bent arm',
            [(s*.30,.015,1.86),(s*.645,.035,1.79),(s*.815,.10,1.60),
             (s*.825,.26,1.46),(s*.725,.435,1.34),(s*.665,.52,1.285),
             (s*.64,.552,1.24)],
            [.189,.184,.160,.139,.125,.133,.025],mat,sides=96,steps=28,flatten=.92)
        for v in arm.data.vertices:
            if abs(v.co.x)<.76 and v.co.z<1.42 and v.co.y>.25:
                v.co.y=max(v.co.y,front_surface(v.co.x,v.co.z)+.045)
        parts.append(arm)
        for digit in range(3):
            xx=s*(.58+digit*.055)
            parts.append(sweep(side+' short mitten finger '+str(digit),
                [(xx,.515,1.27),(xx,.566,1.245),(xx,.595,1.205)],
                [.052,.049,.006],mat,sides=40,steps=15,flatten=.88))
            tx=s*(.395+digit*.082)
            toe=sweep(side+' short olive forefoot toe '+str(digit),
                [(tx,.18,.095),(tx,.28,.087),(tx,.344,.083)],
                [.066,.060,.012],mat,sides=48,steps=16,flatten=.68)
            for v in toe.data.vertices:
                v.co.y=.06+(v.co.y-.06)*1.20
                v.co.z=.014+.012*math.log1p(math.exp((v.co.z-.014)/.012))
            parts.append(toe)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in parts:obj.select_set(True)
    skin=parts[0];bpy.context.view_layer.objects.active=skin;bpy.ops.object.join()
    rem=skin.modifiers.new('Continuous authored silhouette union','REMESH')
    rem.mode='VOXEL';rem.voxel_size=.007;rem.use_smooth_shade=True
    bpy.ops.object.modifier_apply(modifier=rem.name)
    smooth=skin.modifiers.new('Gentle junction relaxation','SMOOTH')
    smooth.factor=.55;smooth.iterations=14
    bpy.ops.object.modifier_apply(modifier=smooth.name)
    # Relax anatomical junctions rather than rounding away the whole silhouette.
    junction=skin.vertex_groups.new(name='NaiFrog shoulder and hip transition')
    for v in skin.data.vertices:
        x,y,z=v.co;ax=abs(x)
        shoulder=math.exp(-((ax-.55)/.24)**2-((z-1.90)/.25)**2)
        hip=math.exp(-((ax-.45)/.22)**2-((z-.99)/.22)**2)
        weight=max(shoulder,hip)
        if weight>.01:junction.add([v.index],weight,'REPLACE')
    soft=skin.modifiers.new('Continuous soft shoulder and hip fillets','SMOOTH')
    soft.factor=.65;soft.iterations=32;soft.vertex_group=junction.name
    bpy.ops.object.modifier_apply(modifier=soft.name)
    group=skin.vertex_groups.get('NaiFrog shoulder and hip transition')
    if group is not None:skin.vertex_groups.remove(group)
    # Native voxel unions can leave tiny enclosed zero-scale residual shells.
    # Keep the measured main skin component, not unrelated remesh residues.
    bm=bmesh.new();bm.from_mesh(skin.data);unseen=set(bm.verts);groups=[]
    while unseen:
        stack=[unseen.pop()];group=[]
        while stack:
            vertex=stack.pop();group.append(vertex)
            for edge in vertex.link_edges:
                other=edge.other_vert(vertex)
                if other in unseen:unseen.remove(other);stack.append(other)
        groups.append(group)
    main=max(groups,key=len)
    residues=[v for group in groups if group is not main for v in group]
    if residues:bmesh.ops.delete(bm,geom=residues,context='VERTS')
    bm.to_mesh(skin.data);bm.free();skin.data.update()
    skin.name='NaifrogContinuousSkin'
    for p in skin.data.polygons:p.use_smooth=True
    skin['authored_shape']='New continuous pear torso / small head / standing long legs; no visible tail'
    return skin

def color_field(coords):
    x,y,z=coords[:,0],coords[:,1],coords[:,2]
    d=(x/.70)**2+((z-1.49)/.64)**2
    belly=np.clip((1.045-d)/.095,0,1);belly=belly*belly*(3-2*belly)
    belly*=np.clip((y-.035)/.12,0,1)
    rx=np.interp(z,SAMPLES[:,0],SAMPLES[:,1]);ry=np.interp(z,SAMPLES[:,0],SAMPLES[:,2]);cy=np.interp(z,SAMPLES[:,0],SAMPLES[:,3])
    front=cy+ry*np.sqrt(np.maximum(0,1-(x/np.maximum(rx,.001))**2))
    belly*=1-smooth(.018,.045,y-front)
    hand=np.clip((np.abs(x)-.49)/.055,0,1)*smooth(.008,.025,y-front)*np.clip((1.445-z)/.070,0,1)*smooth(1.02,1.11,z)
    foot=np.clip((.18-z)/.055,0,1)*np.maximum(np.clip((y-.22)/.07,0,1),np.clip((.055-z)/.025,0,1))
    dark=np.maximum(hand,foot)
    gold=np.array([.94,.70,.016]);cream=np.array([.88,.79,.56]);olive=np.array([.052,.065,.019])
    color=gold[None,:]*(1-belly[:,None])+cream[None,:]*belly[:,None]
    color=color*(1-dark[:,None])+olive[None,:]*dark[:,None]
    return np.column_stack([color,np.ones(len(coords),np.float32)]).astype(np.float32)

def apply_preview_colors(skin):
    coords=np.empty(len(skin.data.vertices)*3,np.float32)
    skin.data.vertices.foreach_get('co',coords);coords=coords.reshape(-1,3)
    attr=skin.data.color_attributes.new(name='NaiFrog reference colors',type='FLOAT_COLOR',domain='POINT')
    attr.data.foreach_set('color',color_field(coords).ravel())
    m=skin.data.materials[0]
    node=m.node_tree.nodes.new('ShaderNodeVertexColor');node.layer_name=attr.name
    m.node_tree.links.new(node.outputs['Color'],m.node_tree.nodes.get('Principled BSDF').inputs['Base Color'])

def eye_disc(side,s,iris,pupil):
    vs=[];fs=[];materials=[];rings=18;sides=96
    cx=s*EYE_X
    center,u,v,normal=eye_frame(cx,EYE_Z)
    vs.append(tuple(center+normal*.034))
    for row in range(1,rings+1):
        r=EYE_RADIUS*row/rings
        for j in range(sides):
            a=math.tau*j/sides
            vs.append(tuple(center+u*(r*math.cos(a))+v*(r*math.sin(a))+normal*(.004+.030*(1-(r/EYE_RADIUS)**2))))
    for j in range(sides):fs.append((0,1+j,1+(j+1)%sides));materials.append(1)
    for row in range(1,rings):
        for j in range(sides):
            a=1+(row-1)*sides;b=1+row*sides
            fs.append((a+j,b+j,b+(j+1)%sides,a+(j+1)%sides))
            materials.append(1 if EYE_RADIUS*(row+.5)/rings<.047 else 0)
    obj=mesh_object('NaifrogEyes_'+side,vs,fs,iris);obj.data.materials.append(pupil)
    for poly,index in zip(obj.data.polygons,materials):poly.material_index=index
    obj['rig_bone']='eye_'+side
    return obj

def closed_mouth_preview(mat):
    controls=[]
    for i in range(15):
        x=MOUTH_RX*(2*i/14-1);z=MOUTH_Z+.013*(x/MOUTH_RX)**2
        controls.append((x,front_surface(x,z)+.002,z))
    obj=sweep('NaiFrog neutral mouth contour preview',controls,[.0015 if i in (0,14) else .0033 for i in range(15)],mat,sides=20,steps=4,flatten=.72)
    obj['stage_only']=True
    return obj

def topology_report(skin):
    bm=bmesh.new();bm.from_mesh(skin.data)
    components=0;unseen=set(bm.verts)
    while unseen:
        stack=[unseen.pop()];components+=1
        while stack:
            vertex=stack.pop()
            for edge in vertex.link_edges:
                other=edge.other_vert(vertex)
                if other in unseen:unseen.remove(other);stack.append(other)
    result={'vertices':len(bm.verts),'edges':len(bm.edges),'faces':len(bm.faces),
        'triangles':sum(len(p.vertices)-2 for p in skin.data.polygons),
        'boundary_edges':sum(e.is_boundary for e in bm.edges),
        'non_manifold_edges':sum(not e.is_manifold for e in bm.edges),'connected_components':components,
        'dimensions':list(skin.dimensions),'phase':'neutral continuous shape; binding/UV/actions not yet performed'}
    bm.free();return result

def preview_setup():
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU'
    scene.cycles.samples=32;scene.cycles.use_denoising=True
    scene.render.resolution_x=900;scene.render.resolution_y=900;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
    scene.view_settings.view_transform='Standard'
    scene.view_settings.exposure=-.80
    world=bpy.data.worlds.new('NaiFrog preview neutral world');scene.world=world;world.use_nodes=True
    world.node_tree.nodes['Background'].inputs['Color'].default_value=(.18,.195,.21,1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value=.35
    for name,loc,energy,size in [('Key',(-3,5,6),400,4),('Fill',(4,3,4),190,4),('Rim',(1,-3,5),300,3)]:
        data=bpy.data.lights.new(name,'AREA');data.energy=energy;data.shape='DISK';data.size=size
        obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj);obj.location=loc
        obj.rotation_euler=(Vector((0,0,1.4))-obj.location).to_track_quat('-Z','Y').to_euler()
    floor=material('NaiFrog preview floor',(.12,.135,.14),.83)
    bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,.0));bpy.context.object.data.materials.append(floor)
    bpy.context.object.name='PREVIEW_ONLY_floor'
    data=bpy.data.cameras.new('NaiFrog preview camera');cam=bpy.data.objects.new('NaiFrog preview camera',data)
    scene.collection.objects.link(cam);data.type='ORTHO';data.ortho_scale=3.25;scene.camera=cam
    return cam

def render_views():
    cam=preview_setup();scene=bpy.context.scene
    views={'front':(0,7,1.48),'three_quarter':(-4.6,7,2.18),'side':(-7,0,1.48),'back':(0,-7,1.48)}
    for name,position in views.items():
        cam.location=position;cam.rotation_euler=(Vector((0,0,1.40))-cam.location).to_track_quat('-Z','Y').to_euler()
        scene.render.filepath=str(PREVIEW/('naifrog_shape_'+name+'.png'))
        bpy.ops.render.render(write_still=True)

def build_shape():
    clear()
    skin_mat=material('Naifrog skin / cream belly / olive extremities',(.96,.635,.047),.60,.075)
    iris=material('Naifrog green iris',(.10,.19,.024),.32)
    pupil=material('Naifrog black pupil',(.0018,.0025,.0008),.10)
    pupil.node_tree.nodes.get('Principled BSDF').inputs['Specular IOR Level'].default_value=.48
    pupil.node_tree.nodes.get('Principled BSDF').inputs['Coat Weight'].default_value=.50
    pupil.node_tree.nodes.get('Principled BSDF').inputs['Coat Roughness'].default_value=.07
    mouth=material('Naifrog neutral mouth',(.095,.061,.015),.77)
    skin=continuous_skin(skin_mat);apply_preview_colors(skin)
    eyes=[eye_disc(side,s,iris,pupil) for side,s in [('left',-1),('right',1)]]
    closed_mouth_preview(mouth)
    MANIFEST['shape_geometry']=topology_report(skin)
    (PREVIEW/'shape-inspection.json').write_text(json.dumps(MANIFEST,indent=2,ensure_ascii=False))
    bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE/'naifrog_shape_master.blend'))
    render_views()
    print('NAIFROG_SHAPE_BUILT '+json.dumps(MANIFEST,ensure_ascii=False))

def array_coords(mesh):
    values=np.empty(len(mesh.vertices)*3,np.float32);mesh.vertices.foreach_get('co',values)
    return values.reshape(-1,3)

def close_eye_mesh(obj):
    # A closed, shallow convex eye volume, not a floating painted plane.
    bm=bmesh.new();bm.from_mesh(obj.data)
    border=[v for v in bm.verts if any(e.is_boundary for e in v.link_edges)]
    cx=(-1 if 'left' in obj.name else 1)*EYE_X
    center,u,vertical,normal=eye_frame(cx,EYE_Z)
    border.sort(key=lambda v:math.atan2((v.co-center).dot(vertical),(v.co-center).dot(u)))
    old=border
    for row in range(1,8):
        factor=1-row/8;ring=[]
        for v in border:
            relative=v.co-center
            ring.append(bm.verts.new(center+u*(relative.dot(u)*factor)+vertical*(relative.dot(vertical)*factor)-normal*(.020*(1-factor*factor))))
        for j in range(len(old)):
            f=bm.faces.new((old[j],old[(j+1)%len(old)],ring[(j+1)%len(old)],ring[j]));f.material_index=0
        old=ring
    pole=bm.verts.new(center-normal*.020)
    for j in range(len(old)):bm.faces.new((old[j],old[(j+1)%len(old)],pole))
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free()
    uv=obj.data.uv_layers.new(name='NaiFrog eye radial UV')
    for p in obj.data.polygons:
        for li in p.loop_indices:
            v=obj.data.vertices[obj.data.loops[li].vertex_index].co
            uv.data[li].uv=(.5+(v-center).dot(u)/(2*EYE_RADIUS),.5+(v-center).dot(vertical)/(2*EYE_RADIUS))

def facial_topology(skin,eyes):
    """Insert new connected eye openings and real oral cavity without booleans.

    Foremost lid rows stay beyond a measured eye envelope. Blink interpolates
    in the x/z plane; it cannot take a chord through the convex eye surface.
    Focus changes the outer hood only, leaving the opening's closure separate.
    """
    oral=material('Naifrog oral interior',(.024,.009,.007),.83)
    skin.data.materials.append(oral)
    bm=bmesh.new();bm.from_mesh(skin.data);bm.normal_update()
    deltas={};oral_vertices=set();facial_faces={};facial_sections={}
    def patch(cx,cz,rx,rz,kind,plane=None):
        frame=eye_frame(cx,cz) if kind=='eye' else None
        region=1 if kind=='eye' and cx<0 else 2 if kind=='eye' else 3
        cut_z=cz-.030 if kind=='mouth' else cz
        if frame:
            center,u,vertical,normal=frame
            cut=[f for f in bm.faces if f.normal.dot(normal)>.05 and
                (lambda q:q.dot(normal)>-.08 and (q.dot(u)/rx)**2+(q.dot(vertical)/rz)**2<1)(f.calc_center_median()-center)]
        else:
            cut=[f for f in bm.faces if f.normal.y>.05 and
                 (lambda c:c.y>.12 and ((c.x-cx)/rx)**2+((c.z-cut_z)/rz)**2<1)(f.calc_center_median())]
        if not cut:raise RuntimeError('Facial cut contains no faces: '+kind)
        bmesh.ops.delete(bm,geom=cut,context='FACES')
        edges=[e for e in bm.edges if e.is_boundary]
        if not edges:raise RuntimeError('Missing connected facial boundary: '+kind)
        links={}
        for e in edges:
            for a,b in (e.verts,list(reversed(e.verts))):links.setdefault(a,[]).append(b)
        if any(len(n)!=2 for n in links.values()):raise RuntimeError('Facial boundary is not a simple loop: '+kind)
        start=next(iter(links));loop=[start];previous=None;current=start
        while True:
            nxt=next(v for v in links[current] if v is not previous)
            if nxt==start:break
            loop.append(nxt);previous,current=current,nxt
            if len(loop)>len(links):raise RuntimeError('Invalid boundary traversal')
        if len(loop)!=len(links):raise RuntimeError('More than one facial cut boundary')
        # Grid-cut angular samples may reverse locally. Reparameterize by the
        # actual closed edge order so new radial rows never fold back.
        for _ in range(5):
            old_co=[v.co.copy() for v in loop]
            for i,v in enumerate(loop):v.co=(old_co[(i-1)%len(loop)]+2*old_co[i]+old_co[(i+1)%len(loop)])*.25
        projected=[((v.co-center).dot(u)/rx,(v.co-center).dot(vertical)/rz) if frame else ((v.co.x-cx)/rx,(v.co.z-cut_z)/rz) for v in loop]
        area=sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(projected,projected[1:]+projected[:1]))
        direction=1 if area>0 else -1;start_angle=math.atan2(projected[0][1],projected[0][0])
        angles=[start_angle+direction*math.tau*i/len(loop) for i in range(len(loop))]
        MANIFEST.setdefault('boundary_parameters',[]).append({'region':region,'vertex_count':len(loop),
            'angle_start':angles[0],'angle_step':direction*math.tau/len(loop),'monotone_no_reverse':all(direction*(b-a)>0 for a,b in zip(angles,angles[1:])),
            'method':'ordered edge loop, smoothed boundary, uniform monotone angular parameter'})
        outer=[v.co.copy() for v in loop];old=loop
        innerx=EYE_RADIUS if kind=='eye' else MOUTH_RX
        innerz=EYE_RADIUS if kind=='eye' else MOUTH_RZ
        for row in range(1,9):
            t=row/8;ring=[]
            for co,a in zip(outer,angles):
                target=Vector((cx+innerx*math.cos(a),0,cz+innerz*math.sin(a)))
                x=co.x*(1-t)+target.x*t;z=co.z*(1-t)+target.z*t
                if kind=='eye':
                    target=center+u*(innerx*math.cos(a))+vertical*(innerz*math.sin(a))
                    point=co*(1-t)+target*t
                    blend=min(1,t/.32);blend=blend*blend*(3-2*blend)
                    desired=(co-center).dot(normal)*(1-blend)+plane*blend
                    point+=normal*(desired-(point-center).dot(normal));x,y,z=point
                    blink_z=t*innerz*(-.94)*math.sin(a)
                    # Max radial derivative 4*.003=.012 stays below the
                    # measured outer-to-inner band, avoiding a reversed hood.
                    focus_z=-.003*max(0,math.sin(a))*4*t*(1-t)
                    local_z=(point-center).dot(vertical)
                    # The convex cap height is a concave quadratic in moving
                    # local z. Its tangent bounds every linear Blink/Focus
                    # interpolation from above; neutral rim stays flush.
                    blink=vertical*blink_z+normal*max(0,-.060*local_z*blink_z/(EYE_RADIUS**2))
                    focus=vertical*focus_z+normal*max(0,-.060*local_z*focus_z/(EYE_RADIUS**2))
                    opening=Vector((0,0,0))
                else:
                    y=co.y*(1-t)+(front_surface(target.x,target.z)+.002)*t
                    blink=focus=Vector((0,0,0))
                    opening=Vector((t*.016*math.cos(a),.004*t,t*(-.020+.066*math.sin(a))))
                v=bm.verts.new((x,y,z));ring.append(v);deltas[v]=(blink,focus,opening)
            for j in range(len(old)):
                f=bm.faces.new((old[j],old[(j+1)%len(old)],ring[(j+1)%len(old)],ring[j]))
                facial_faces[f]=region;facial_sections[f]=1
            old=ring
        front_ring=old
        for row in range(1,5):
            depth=(.13 if kind=='eye' else .115)*row/4;ring=[]
            for co,a in zip(front_ring,angles):
                factor=1 if row<4 else .66
                x=cx+innerx*factor*math.cos(a);z=cz+innerz*factor*math.sin(a)
                if frame:
                    point=center+u*(innerx*factor*math.cos(a))+vertical*(innerz*factor*math.sin(a))+normal*(plane-depth)
                else:point=Vector((x,front_surface(x,z)+.002-depth,z))
                v=bm.verts.new(point);ring.append(v)
                if kind=='mouth':oral_vertices.add(v)
                opening=Vector((.016*factor*math.cos(a),.004,-.020+.066*factor*math.sin(a))) if kind=='mouth' else Vector((0,0,0))
                deltas[v]=(Vector((0,0,0)),Vector((0,0,0)),opening)
            for j in range(len(old)):
                f=bm.faces.new((old[j],old[(j+1)%len(old)],ring[(j+1)%len(old)],ring[j]));f.material_index=1 if kind=='mouth' else 0
                facial_faces[f]=region;facial_sections[f]=2
            old=ring
        pole=bm.verts.new(center+normal*(plane-.13) if frame else (cx,front_surface(cx,cz)+.002-.115,cz))
        if kind=='mouth':oral_vertices.add(pole)
        deltas[pole]=(Vector((0,0,0)),Vector((0,0,0)),Vector((0,.004,-.020)) if kind=='mouth' else Vector((0,0,0)))
        for j in range(len(old)):
            f=bm.faces.new((old[j],old[(j+1)%len(old)],pole));f.material_index=1 if kind=='mouth' else 0
            facial_faces[f]=region;facial_sections[f]=2
    envelopes=[]
    for side,s,eye in [('left',-1,eyes[0]),('right',1,eyes[1])]:
        center,u,vertical,normal=eye_frame(s*EYE_X,EYE_Z)
        foremost=max((v.co-center).dot(normal) for v in eye.data.vertices)
        plane=.0071 # .004 cap edge + 3.1mm margin; measured polygon gap >3mm.
        patch(s*EYE_X,EYE_Z,.090,.085,'eye',plane)
        envelopes.append({'side':side,'frame_center':list(center),'frame_u':list(u),'frame_vertical':list(vertical),'eye_normal':list(normal),'foremost_eye_normal_depth':foremost,'neutral_lid_rim_depth':plane,'blink_focus_method':'flush neutral rim; cap quadratic tangent is a conservative bound for all linear joint values'})
    # Open=1 inner bounds are [-.092,+.052] around mouth center. This
    # asymmetric outer band is [-.128,+.068], so it cannot be overtaken.
    patch(0,MOUTH_Z,.150,.098,'mouth')
    bm.verts.index_update();bm.verts.ensure_lookup_table()
    data={name:np.zeros((len(bm.verts),3),np.float32) for name in ('Blink','Focus','Open')}
    oral_mask=np.zeros(len(bm.verts),np.float32)
    for v in oral_vertices:oral_mask[v.index]=1
    bm.faces.index_update();bm.faces.ensure_lookup_table()
    regions=np.zeros(len(bm.faces),np.int32);sections=np.zeros(len(bm.faces),np.int32)
    for face,region in facial_faces.items():regions[face.index]=region;sections[face.index]=facial_sections[face]
    for v,changes in deltas.items():
        for name,delta in zip(('Blink','Focus','Open'),changes):data[name][v.index]=delta
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(skin.data);bm.free();skin.data.update()
    for polygon in skin.data.polygons:polygon.use_smooth=True
    for name,values in data.items():
        attr=skin.data.attributes.new(name='NaiFrogDelta'+name,type='FLOAT_VECTOR',domain='POINT')
        attr.data.foreach_set('vector',values.ravel())
    attr=skin.data.attributes.new(name='NaiFrogOralWeight',type='FLOAT',domain='POINT')
    attr.data.foreach_set('value',oral_mask)
    for name,values in [('NaiFrogFacialPatch',regions),('NaiFrogFacialSection',sections)]:
        attr=skin.data.attributes.new(name=name,type='INT',domain='FACE');attr.data.foreach_set('value',values)
    MANIFEST['eye_envelopes']=envelopes
    MANIFEST['mouth_method']='New simple connected boundary, annulus and deep cavity; no Boolean cutter or old eyelid patch'

def add_morphs(obj):
    neutral=array_coords(obj.data);obj.shape_key_add(name='Basis')
    for name in ('Blink','Focus','Open'):
        attr=obj.data.attributes.get('NaiFrogDelta'+name)
        delta=np.zeros_like(neutral)
        if attr is None:raise RuntimeError('LOD lost authored deformation data: '+obj.name+'/'+name)
        attr.data.foreach_get('vector',delta.ravel())
        key=obj.shape_key_add(name=name);key.data.foreach_set('co',(neutral+delta).ravel())

def make_tongue():
    mat=material('Naifrog tongue',(.34,.09,.095),.62,.02)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48,ring_count=32,location=(0,front_surface(0,MOUTH_Z)-.063,MOUTH_Z-.021))
    obj=bpy.context.object;obj.name='NaifrogTongue';obj.scale=(.055,.037,.012)
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    obj.data.materials.append(mat);obj['rig_bone']='head'
    for p in obj.data.polygons:p.use_smooth=True
    neutral=array_coords(obj.data)
    for name in ('Blink','Focus','Open'):
        delta=np.zeros_like(neutral)
        if name=='Open':delta[:,1]=.012;delta[:,2]=-.038
        attr=obj.data.attributes.new(name='NaiFrogDelta'+name,type='FLOAT_VECTOR',domain='POINT');attr.data.foreach_set('vector',delta.ravel())
    return obj

def make_rig():
    data=bpy.data.armatures.new('NaiFrog editable anatomical skeleton');rig=bpy.data.objects.new('NaifrogRig',data);bpy.context.collection.objects.link(rig)
    bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig;bpy.ops.object.mode_set(mode='EDIT')
    bones=[('root',(0,0,0),(0,0,.30),None),('pelvis',(0,0,.79),(0,0,1.13),'root'),
        ('spine',(0,0,1.13),(0,0,1.92),'pelvis'),('belly',(0,.29,1.19),(0,.29,1.64),'spine'),
        ('neck',(0,.04,1.92),(0,.10,2.30),'spine'),('head',(0,.10,2.30),(0,.13,2.72),'neck'),
        ('jaw',(0,.30,2.46),(0,.39,2.42),'head'),('tail',(0,-.20,.96),(0,-.33,.96),'pelvis')]
    for side,s in [('left',-1),('right',1)]:
        bones.extend([(f'upper_arm_{side}',(s*.43,.035,1.90),(s*.82,.23,1.53),'spine'),
            (f'forearm_{side}',(s*.82,.23,1.53),(s*.665,.52,1.285),f'upper_arm_{side}'),
            (f'palm_{side}',(s*.665,.52,1.285),(s*.64,.57,1.22),f'forearm_{side}'),
            (f'thigh_{side}',(s*.43,0,.96),(s*.465,-.014,.54),'pelvis'),
            (f'shin_{side}',(s*.465,-.014,.54),(s*.475,.05,.155),f'thigh_{side}'),
            (f'foot_{side}',(s*.475,.05,.155),(s*.475,.31,.155),f'shin_{side}'),
            (f'eye_{side}',(s*EYE_X,.38,EYE_Z),(s*EYE_X,.38,EYE_Z+.08),'head'),
            (f'brow_{side}',(s*EYE_X,.35,EYE_Z+.070),(s*EYE_X,.35,EYE_Z+.110),'head')])
    for name,a,b,parent in bones:
        bone=data.edit_bones.new(name);bone.head=a;bone.tail=b
        if parent:bone.parent=data.edit_bones[parent]
    bpy.ops.object.mode_set(mode='OBJECT');rig.select_set(False)
    for p in rig.pose.bones:p.rotation_mode='XYZ'
    return rig

def author_uv_regions(skin):
    """Separate mutually occluding surfaces before actual UV projection."""
    from naifrog_materials import UV_REGION_NAMES
    mesh=skin.data;coords=array_coords(mesh)
    indices=np.empty(len(mesh.loops),np.int32);mesh.loops.foreach_get('vertex_index',indices)
    starts=np.empty(len(mesh.polygons),np.int32);mesh.polygons.foreach_get('loop_start',starts)
    totals=np.empty(len(mesh.polygons),np.int32);mesh.polygons.foreach_get('loop_total',totals)
    centers=np.add.reduceat(coords[indices],starts,axis=0)/totals[:,None]
    x,y,z=centers.T;ax=np.abs(x)
    rx=np.interp(z,SAMPLES[:,0],SAMPLES[:,1]);ry=np.interp(z,SAMPLES[:,0],SAMPLES[:,2]);cy=np.interp(z,SAMPLES[:,0],SAMPLES[:,3])
    front=cy+ry*np.sqrt(np.maximum(0,1-(x/np.maximum(rx,.001))**2))
    labels=np.zeros(len(mesh.polygons),np.int32)
    labels[z>2.10]=11
    arms=(ax>.50)&(z>1.10)&(z<2.02)&((y-front>.020)|(ax>rx*.90))
    labels[arms&(x<0)]=4;labels[arms&(x>=0)]=5
    # V8's 24 proven overlaps join the rear palm y=.448 with finger-front
    # y=.589 at z=1.207..1.212. Give the rear palm its own projection island.
    palm_rear=arms&(z<1.35)&(y<.52)
    labels[palm_rear&(x<0)]=12;labels[palm_rear&(x>=0)]=13
    legs=(z<1.14)&(ax>.08);labels[legs&(x<0)]=6;labels[legs&(x>=0)]=7
    patch=np.empty(len(mesh.polygons),np.int32);section=np.empty(len(mesh.polygons),np.int32)
    mesh.attributes['NaiFrogFacialPatch'].data.foreach_get('value',patch)
    mesh.attributes['NaiFrogFacialSection'].data.foreach_get('value',section)
    for region in (1,2,3):
        labels[(patch==region)&(section==1)]=region
        labels[(patch==region)&(section==2)]=region+7
    attr=mesh.attributes.new(name='NaiFrogUVRegion',type='INT',domain='FACE');attr.data.foreach_set('value',labels)
    if labels.min()<0 or labels.max()>=len(UV_REGION_NAMES):raise RuntimeError('Producer UV labels do not match the shared material helper schema')
    MANIFEST['uv_region_faces']={str(i):int((labels==i).sum()) for i in np.unique(labels)}
    MANIFEST['uv_region_schema']={str(i):name for i,name in enumerate(UV_REGION_NAMES)}

def smooth(a,b,value):
    t=np.clip((value-a)/(b-a),0,1);return t*t*(3-2*t)

def bind_skin(skin,rig):
    coords=array_coords(skin.data);x,y,z=coords.T;ax=np.abs(x)
    rx=np.interp(z,SAMPLES[:,0],SAMPLES[:,1]);ry=np.interp(z,SAMPLES[:,0],SAMPLES[:,2]);cy=np.interp(z,SAMPLES[:,0],SAMPLES[:,3])
    front=cy+ry*np.sqrt(np.maximum(0,1-(x/np.maximum(rx,.001))**2))
    head=smooth(2.05,2.30,z)
    arm=np.maximum(smooth(.56,.82,ax),smooth(.025,.095,y-front)*smooth(.48,.64,ax))*smooth(1.10,1.30,z)*(1-smooth(1.85,2.08,z))*(1-head)
    leg=smooth(.12,.35,ax)*(1-smooth(.93,1.15,z))*(1-head)*(1-arm)
    trunk=np.maximum(0,1-head-arm-leg);neck=smooth(1.93,2.18,z);spine=smooth(1.01,1.62,z)
    belly=.20*smooth(.20,.48,y)*(1-smooth(1.77,1.97,z))*smooth(1.09,1.27,z)
    fore=1-smooth(1.34,1.68,z);palm=smooth(.43,.535,y)*(1-smooth(1.26,1.43,z))
    foot=1-smooth(.135,.265,z);shin=smooth(.19,.33,z)*(1-smooth(.50,.70,z));thigh=np.maximum(0,1-foot-shin)
    fields={'head':head,'neck':trunk*neck,'pelvis':trunk*(1-spine)*(1-neck),
        'spine':trunk*(spine-belly)*(1-neck),'belly':trunk*belly*(1-neck)}
    for side,sign in [('left',-1),('right',1)]:
        mask=(x*sign>=0).astype(np.float32)
        fields.update({f'upper_arm_{side}':arm*(1-fore)*mask,f'forearm_{side}':arm*fore*(1-palm)*mask,
            f'palm_{side}':arm*fore*palm*mask,f'thigh_{side}':leg*thigh*mask,
            f'shin_{side}':leg*shin*mask,f'foot_{side}':leg*foot*mask})
    names=list(fields);values=np.maximum(0,np.stack([fields[n] for n in names],axis=1))
    selected=np.argsort(values,axis=1)[:,-4:];weight=np.take_along_axis(values,selected,axis=1)
    weight/=np.maximum(weight.sum(axis=1,keepdims=True),1e-12)
    for name in rig.data.bones.keys():skin.vertex_groups.new(name=name)
    for index in range(len(coords)):
        for column,w in zip(selected[index],weight[index]):
            if w>1e-7:skin.vertex_groups[names[column]].add([index],float(w),'REPLACE')
    skin.parent=rig;mod=skin.modifiers.new('NaiFrog independent anatomical skin','ARMATURE');mod.object=rig
    return coords

def bind_rigid(obj,rig):
    group=obj.vertex_groups.new(name=obj.get('rig_bone','head'));group.add(list(range(len(obj.data.vertices))),1,'REPLACE')
    obj.parent=rig;mod=obj.modifiers.new('NaiFrog independent attachment','ARMATURE');mod.object=rig

def sole_data(skin,rig):
    coords=array_coords(skin.data);result={}
    for side,s in [('left',-1),('right',1)]:
        indices=np.flatnonzero((coords[:,0]*s>0)&(coords[:,2]<.040))
        if len(indices)<20:raise RuntimeError('Missing actual sole vertices '+side)
        groups={g.index:g.name for g in skin.vertex_groups}
        influences=[]
        for i in indices:
            influences.append([(groups[g.group],g.weight) for g in skin.data.vertices[int(i)].groups if g.weight>1e-7])
        result[side]={'indices':indices,'coords':coords[indices],'influences':influences}
    return result

def skinned_sole(rig,sole):
    transforms={b.name:np.asarray(b.matrix@b.bone.matrix_local.inverted()) for b in rig.pose.bones}
    values=np.column_stack([sole['coords'],np.ones(len(sole['coords']))]);out=np.zeros((len(values),3),np.float64)
    for i,items in enumerate(sole['influences']):
        for bone,w in items:out[i]+=(transforms[bone]@values[i])[:3]*w
    return out

def animate(rig,objects,skin,label='high'):
    fps=30;scene=bpy.context.scene;scene.render.fps=fps
    clips={'idle':96,'walk':30,'chase':20,'warn':24,'charge':15,'recover':60}
    rig.animation_data_create()
    rig.animation_data.action=None
    for track in list(rig.animation_data.nla_tracks):rig.animation_data.nla_tracks.remove(track)
    soles=sole_data(skin,rig);samples=[]
    for name,frames in clips.items():
        duration=frames/fps;MANIFEST['clips'][name]={'duration':duration,'frames':frames,'root_motion':False}
        rig.animation_data_create();rig.animation_data.action=bpy.data.actions.new(name+' / NaiFrog skeleton')
        for track in rig.animation_data.nla_tracks:track.mute=True
        for frame in range(frames+1):
            t=frame/frames;p=math.tau*t
            for bone in rig.pose.bones:bone.location=(0,0,0);bone.rotation_euler=(0,0,0);bone.scale=(1,1,1)
            pelvis=rig.pose.bones['pelvis'];spine=rig.pose.bones['spine'];head=rig.pose.bones['head'];belly=rig.pose.bones['belly']
            belly.scale=(1+.011*math.sin(p),1+.016*math.sin(p),1+.010*math.sin(p))
            spine.rotation_euler.z=.010*math.sin(p);head.rotation_euler.z=-.011*math.sin(p)
            locomotion=name in ('walk','chase','charge')
            if locomotion:
                amplitude={'walk':.22,'chase':.31,'charge':.38}[name]
                pelvis.location.y=-.025+.012*math.cos(2*p)
                spine.rotation_euler.x={'walk':-.035,'chase':-.080,'charge':-.12}[name]
                for side,offset in [('left',0),('right',math.pi)]:
                    q=p+offset;th=rig.pose.bones['thigh_'+side];shin=rig.pose.bones['shin_'+side];foot=rig.pose.bones['foot_'+side]
                    th.rotation_euler.x=-amplitude*math.sin(q)
                    shin.rotation_euler.x=max(0,math.sin(q))*(.38 if name=='walk' else .56)
                    foot.rotation_euler.x=-th.rotation_euler.x-shin.rotation_euler.x
                    rig.pose.bones['upper_arm_'+side].rotation_euler.x=.13*math.sin(q)
                    rig.pose.bones['forearm_'+side].rotation_euler.x=-.03+.035*math.cos(q)
            elif name=='warn':
                anticipation=math.sin(t*math.pi/2);pelvis.location.y=-.055*anticipation
                spine.rotation_euler.x=-.09*anticipation;head.rotation_euler.x=.035*anticipation
                for side in ('left','right'):
                    rig.pose.bones['thigh_'+side].rotation_euler.x=.13*anticipation
                    rig.pose.bones['shin_'+side].rotation_euler.x=-.24*anticipation
                    rig.pose.bones['foot_'+side].rotation_euler.x=.11*anticipation
            elif name=='recover':
                spine.rotation_euler.x=-.03;head.rotation_euler.x=.025
                belly.scale=(1+.018*math.sin(p),1+.026*math.sin(p),1+.018*math.sin(p))
            bpy.context.view_layer.update()
            for side,offset in [('left',0),('right',math.pi)]:
                foot=rig.pose.bones['foot_'+side]
                target=.001+(max(0,math.sin(p+offset))*{'walk':.055,'chase':.080,'charge':.095}.get(name,0))
                for _ in range(2):
                    positions=skinned_sole(rig,soles[side]);floor=float(positions[:,2].min())
                    parent=foot.parent;basis=parent.matrix@parent.bone.matrix_local.inverted()@foot.bone.matrix_local
                    foot.location+=basis.to_3x3().inverted()@Vector((0,0,target-floor))
                    bpy.context.view_layer.update()
                positions=skinned_sole(rig,soles[side]);samples.append({'clip':name,'frame':frame+1,'side':side,'floor':float(positions[:,2].min()),'target':target,'support':not locomotion or math.sin(p+offset)<=1e-6})
            for bone in rig.pose.bones:
                bone.keyframe_insert('location',frame=frame+1);bone.keyframe_insert('rotation_euler',frame=frame+1);bone.keyframe_insert('scale',frame=frame+1)
        action=rig.animation_data.action
        for curve in action.fcurves:
            for key in curve.keyframe_points:key.interpolation='LINEAR'
        track=rig.animation_data.nla_tracks.new();track.name=name;track.strips.new(name,1,action);rig.animation_data.action=None
        for obj in objects:
            if obj.data.shape_keys is None:continue
            keys=obj.data.shape_keys;keys.animation_data_create()
            for track in keys.animation_data.nla_tracks:track.mute=True
            keys.animation_data.action=bpy.data.actions.new(name+' / '+obj.name+' expression')
            for frame in range(frames+1):
                t=frame/frames;p=math.tau*t
                blink=max(0,1-abs(t-(.56 if name=='idle' else .65))/.035) if name in ('idle','recover') else 0
                focus={'idle':0,'walk':.06,'chase':.20,'warn':.34,'charge':.25,'recover':.15}[name]
                opening={'idle':.035,'walk':.08,'chase':.14,'charge':.22,'recover':.09}.get(name,.85*math.sin(t*math.pi/2))
                for shape,value in [('Blink',blink),('Focus',focus),('Open',opening)]:
                    keys.key_blocks[shape].value=value;keys.key_blocks[shape].keyframe_insert('value',frame=frame+1)
            action=keys.animation_data.action
            for curve in action.fcurves:
                for key in curve.keyframe_points:key.interpolation='LINEAR'
            track=keys.animation_data.nla_tracks.new();track.name=name;track.strips.new(name,1,action);keys.animation_data.action=None
    for track in rig.animation_data.nla_tracks:track.mute=track.name!='idle'
    for obj in objects:
        if obj.data.shape_keys:
            for track in obj.data.shape_keys.animation_data.nla_tracks:track.mute=track.name!='idle'
    scene.frame_set(1)
    (PREVIEW/('actual-sole-keyframe-checks-'+label+'.json')).write_text(json.dumps(samples,indent=2))
    error=max(abs(s['floor']-s['target']) for s in samples)
    MANIFEST['sole_keyframe_error_max']=max(error,MANIFEST.get('sole_keyframe_error_max',0))
    MANIFEST.setdefault('sole_sets',{})[label]={side:{'rest_indices':sole['indices'].tolist(),'vertex_count':len(sole['indices']),'rest_z_threshold':.040} for side,sole in soles.items()}
    MANIFEST['support_definition']='locomotion sin(phase)<=0; right phase is left+pi; idle/warn/recover both feet; true rest sole vertices z<.040'

def reduce_mesh(obj,neutral,ratio):
    obj.data=neutral.copy();bpy.context.view_layer.objects.active=obj
    mod=obj.modifiers.new('Measured distance silhouette reduction','DECIMATE');mod.ratio=ratio
    bpy.ops.object.modifier_move_up(modifier=mod.name)
    bpy.ops.object.modifier_apply(modifier=mod.name)

def prune_weights(obj):
    """Decimation interpolates additional groups: match the GPU's four weights."""
    for vertex in obj.data.vertices:
        original=[(g.group,float(g.weight)) for g in vertex.groups]
        selected=sorted([(g,w) for g,w in original if w>1e-7],key=lambda item:item[1],reverse=True)[:4]
        total=sum(w for _,w in selected)
        if not total:raise RuntimeError('Runtime vertex lost skin weights: '+obj.name)
        selected_ids={g for g,_ in selected}
        for group,_ in original:
            if group not in selected_ids:obj.vertex_groups[group].remove([vertex.index])
        for group,w in selected:obj.vertex_groups[group].add([vertex.index],w/total,'REPLACE')

def full_build():
    sys.path.insert(0,str(Path(__file__).parent))
    from naifrog_materials import author_uv_and_maps
    clear()
    skin_mat=material('Naifrog skin / cream belly / olive extremities',(.94,.70,.016),.60,.055)
    iris=material('Naifrog green iris',(.10,.19,.024),.32)
    pupil=material('Naifrog black pupil',(.0018,.0025,.0008),.10)
    p=pupil.node_tree.nodes.get('Principled BSDF');p.inputs['Specular IOR Level'].default_value=.48;p.inputs['Coat Weight'].default_value=.50;p.inputs['Coat Roughness'].default_value=.07
    print('NAIFROG_STAGE continuous_shape',flush=True)
    skin=continuous_skin(skin_mat);eyes=[eye_disc(side,s,iris,pupil) for side,s in [('left',-1),('right',1)]]
    for eye in eyes:close_eye_mesh(eye)
    facial_topology(skin,eyes);tongue=make_tongue();objects=[skin]+eyes+[tongue]
    MANIFEST['high_skin_geometry']=topology_report(skin)
    print('NAIFROG_STAGE uv_and_maps',flush=True)
    author_uv_regions(skin)
    def current_oral_mask(coords):
        mesh=skin.data
        if not np.array_equal(array_coords(mesh),coords):raise RuntimeError('Baking callback did not receive current coordinate rows')
        mask=np.empty(len(mesh.vertices),np.float32);mesh.attributes['NaiFrogOralWeight'].data.foreach_get('value',mask)
        return mask
    def skin_color(coords):
        oral_mask=current_oral_mask(coords)
        colors=color_field(coords);colors[:,:3]=colors[:,:3]*(1-oral_mask[:,None])+np.array([.024,.009,.007])*oral_mask[:,None]
        return colors
    def roughness(coords):
        oral_mask=current_oral_mask(coords)
        rgba=color_field(coords);dark=(rgba[:,0]<.15).astype(np.float32);cream=((rgba[:,2]>.20)&(rgba[:,0]>.50)).astype(np.float32)
        return (.60+.08*dark+.01*cream)*(1-oral_mask)+.82*oral_mask
    maps=author_uv_and_maps(skin,OUT/'textures',skin_color,resolution=4096,roughness_field=roughness,blend_directory=SOURCE)
    MANIFEST['surface_maps']=maps['report']
    print('NAIFROG_STAGE rig_and_actual_sole_animation',flush=True)
    rig=make_rig();bind_skin(skin,rig)
    for obj in eyes+[tongue]:bind_rigid(obj,rig)
    neutral={obj.name:obj.data.copy() for obj in objects}
    add_morphs(skin);add_morphs(tongue);animate(rig,objects,skin)
    bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE/'naifrog_high_rig.blend'))
    MANIFEST['bones']=len(rig.data.bones)
    for level,ratio in [(0,1.0),(1,.16),(2,.045)]:
        print('NAIFROG_STAGE export_lod_'+str(level),flush=True)
        for obj in objects:
            old=obj.data;obj.data=neutral[obj.name].copy()
            if old.users==0 and old not in neutral.values():bpy.data.meshes.remove(old)
            reduction=ratio if obj==skin else (1 if level==0 else .55 if level==1 else .30)
            if reduction<1:reduce_mesh(obj,obj.data,reduction)
            # Keep glTF mesh names as stable as node names across every LOD.
            for stale in list(bpy.data.meshes):
                if stale!=obj.data and stale not in neutral.values() and stale.users==0 and stale.name==obj.name:
                    bpy.data.meshes.remove(stale)
            obj.data.name=obj.name
            prune_weights(obj)
            if obj in (skin,tongue):add_morphs(obj)
        # New data has new morph datablocks; regenerate exactly the six native tracks.
        animate(rig,objects,skin,'lod'+str(level))
        if level==0:bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE/'naifrog_game_rig.blend'))
        for track in rig.animation_data.nla_tracks:track.mute=False
        for obj in objects:
            if obj.data.shape_keys:
                for track in obj.data.shape_keys.animation_data.nla_tracks:track.mute=False
        bpy.ops.object.select_all(action='DESELECT')
        for obj in [rig]+objects:obj.hide_set(False);obj.select_set(True)
        bpy.context.view_layer.objects.active=rig
        filename=OUT/('naifrog_lod'+str(level)+'.glb')
        bpy.ops.export_scene.gltf(filepath=str(filename),export_format='GLB',use_selection=True,
            export_yup=True,export_apply=False,export_animations=True,export_animation_mode='NLA_TRACKS',
            export_nla_strips=True,export_merge_animation='NLA_TRACK',export_force_sampling=True,
            export_skins=True,export_normals=True,export_tangents=True,export_materials='EXPORT',
            export_vertex_color='NONE',export_all_vertex_colors=False,
            export_morph=True,export_morph_animation=True,export_cameras=False,export_lights=False)
        MANIFEST['lod'+str(level)+'_triangles']=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in objects)
        MANIFEST['lod'+str(level)+'_sha256']=hashlib.sha256(filename.read_bytes()).hexdigest()
    MANIFEST['parts']=[o.name for o in objects]
    MANIFEST['shape_names']={o.name:[s.name for s in o.data.shape_keys.key_blocks if s.name!='Basis'] for o in objects if o.data.shape_keys}
    (OUT/'MODEL_MANIFEST.json').write_text(json.dumps(MANIFEST,indent=2,ensure_ascii=False))
    print('NAIFROG_FULL_BUILT '+json.dumps({k:MANIFEST[k] for k in ('parts','bones','clips','lod0_triangles','lod1_triangles','lod2_triangles','sole_keyframe_error_max')},ensure_ascii=False),flush=True)

if __name__=='__main__':
    if STAGE=='shape':build_shape()
    elif STAGE=='full':full_build()
    else:raise RuntimeError('Unknown stage: '+STAGE)
