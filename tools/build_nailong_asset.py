"""Author and export the rainfield pursuer, using Blender 4.5 LTS.

Rebuild: Blender --background --python tools/build_nailong_asset.py -- --repo REPO
The official character picture is an anatomical reference, never a texture/source mesh.
All meshes, UVs, surface maps, skinning and six animation clips are authored here.
Blender coordinates: Z up, +Y facing; glTF exports to Godot Y up, -Z facing.
"""
import bpy, math, json, sys, numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ARGS = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
ROOT = Path(ARGS[ARGS.index('--repo') + 1]) if '--repo' in ARGS else Path(__file__).resolve().parents[1]
CANDIDATE = '--candidate' in ARGS
OUT = ROOT / 'assets/refined/nailong' / ('reference_candidate' if CANDIDATE else '')
SOURCE = ROOT / 'source_assets/nailong' / ('reference_candidate' if CANDIDATE else '')
OUT.mkdir(parents=True, exist_ok=True)
SOURCE.mkdir(parents=True, exist_ok=True)
(SOURCE / '.gdignore').touch()
TEX = OUT / 'textures'; TEX.mkdir(exist_ok=True)
HI = '--high-only' in ARGS
bpy.context.preferences.filepaths.save_version = 0
MANIFEST = {'generator': 'tools/build_nailong_asset.py', 'blender': bpy.app.version_string,
            'reference': 'User supplied reference-1.png to reference-4.png, green-eyed common form only', 'coordinate_system': 'Godot Y up, -Z facing',
            'license': 'Original authored mesh and maps; character IP belongs to its owner.', 'clips': {}}

def clear():
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    for a in list(bpy.data.actions): bpy.data.actions.remove(a)

def material(name, color, rough=.5, subsurface=0):
    m=bpy.data.materials.new(name); m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF'); p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Roughness'].default_value=rough; p.inputs['Subsurface Weight'].default_value=subsurface
    p.inputs['Subsurface Radius'].default_value=(.24,.13,.06)
    return m

def image_save(name, array, noncolor=False):
    h,w,_=array.shape; im=bpy.data.images.new(name,width=w,height=h,alpha=True)
    im.pixels.foreach_set(array.astype(np.float32).reshape(-1)); im.filepath_raw=str(TEX/(name+'.png'))
    im.file_format='PNG'; im.save()
    if noncolor: im.colorspace_settings.name='Non-Color'
    return im

def skin_material():
    m=material('Soft warm yellow skin / cream belly',(.88,.63,.035),.61,.15)
    size=4096; yy,xx=np.mgrid[:size,:size].astype(np.float32); u=xx/size;v=yy/size
    # Cylindrical original UV: front theta=pi/2. Rounded cream belly is part of the skin map.
    radius=np.interp(v[:,0]*2.8,[.30,.43,.65,.92,1.17,1.39,1.53,1.64,1.82,2.08,2.35,2.56,2.72,2.8],
        [.15,.54,.72,.75,.70,.59,.48,.65,.76,.74,.65,.50,.29,.005])[:,None]
    projected_x=radius*np.cos(u*math.tau)
    d=(projected_x/.44)**2+((v*2.8-1.02)/.46)**2
    belly=np.clip((1.027-d)/.055,0,1);belly=belly*belly*(3-2*belly)*(np.sin(u*math.tau)>.25)
    rng=np.random.default_rng(6501);grain=rng.normal(0,.0045,(size,size)).astype(np.float32)
    cloudy=.004*np.sin(u*47+np.sin(v*21))+.005*np.sin(v*31+u*8)
    tone=1+grain*.26+cloudy
    gold=np.array([.88,.63,.035]);cream=np.array([.98,.86,.49])
    data=np.ones((size,size,4),np.float32)
    data[:,:,:3]=(gold[None,None,:]*(1-belly[:,:,None])+cream[None,None,:]*belly[:,:,None])*tone[:,:,None]
    albedo=image_save('nailong_skin_basecolor',np.clip(data,0,1))
    data[:,:,:3]=np.clip(.61+grain*.35+cloudy*.6-.02*belly,.53,.67)[:,:,None]
    rough=image_save('nailong_skin_roughness',data,True)
    # Restrained micro-surface: no visible reptile scales or pixel-noise pores.
    data[:,:,0]=.5+(np.roll(grain,1,axis=1)-grain)*.25
    data[:,:,1]=.5+(np.roll(grain,1,axis=0)-grain)*.25;data[:,:,2]=.999
    normal=image_save('nailong_skin_normal',data,True)
    n=m.node_tree.nodes;l=m.node_tree.links;p=n.get('Principled BSDF')
    for name,im in [('Base Color',albedo),('Roughness',rough),('Normal',normal)]:
        tex=n.new('ShaderNodeTexImage');tex.image=im
        if name=='Normal':
            norm=n.new('ShaderNodeNormalMap');norm.inputs['Strength'].default_value=.10
            l.new(tex.outputs['Color'],norm.inputs['Color']);l.new(norm.outputs['Normal'],p.inputs[name])
        else:l.new(tex.outputs['Color'],p.inputs[name])
    return m

def iris_material():
    m=material('Layered olive green iris',(.16,.35,.018),.21)
    size=1024; yy,xx=np.mgrid[:size,:size].astype(np.float32);x=(xx-size/2)/(size/2);z=(yy-size/2)/(size/2)
    r=np.sqrt(x*x+z*z);a=np.arctan2(z,x)
    fibres=(np.sin(a*117+np.sin(r*32))*np.sin(a*43-r*18)+np.sin(a*181+r*27))*.5
    limbus=np.clip((1-r)/.10,0,1);ring=np.exp(-((r-.43)/.16)**2)
    base=np.stack([.21+.065*fibres+.07*ring,.52+.11*fibres+.08*ring,.025+.018*fibres],axis=2)
    data=np.ones((size,size,4),np.float32);data[:,:,:3]=np.clip(base*(.21+.79*limbus[:,:,None]),0,1)
    tex=m.node_tree.nodes.new('ShaderNodeTexImage');tex.image=image_save('nailong_iris_basecolor',data)
    m.node_tree.links.new(tex.outputs['Color'],m.node_tree.nodes.get('Principled BSDF').inputs['Base Color'])
    return m

def create_mesh(name, verts, faces, mat=None, uv=None):
    data=bpy.data.meshes.new(name);data.from_pydata(verts,[],faces);data.update()
    obj=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(obj)
    if mat:data.materials.append(mat)
    for p in data.polygons:p.use_smooth=True
    if uv is not None:
        layer=data.uv_layers.new(name='AuthoredUV');indices=np.empty(len(data.loops),np.int32)
        data.loops.foreach_get('vertex_index',indices);layer.data.foreach_set('uv',np.asarray(uv,np.float32)[indices].ravel())
    return obj

def catmull(values, t):
    q=max(0,min(len(values)-1.000001,t*(len(values)-1)));i=int(q);f=q-i
    a=np.asarray(values[max(0,i-1)]);b=np.asarray(values[i]);c=np.asarray(values[i+1]);d=np.asarray(values[min(i+2,len(values)-1)])
    return .5*((2*b)+(-a+c)*f+(2*a-5*b+4*c-d)*f*f+(-a+3*b-3*c+d)*f*f*f)

BODY_PROFILE=[(.30,.15,.11,0),(.43,.54,.39,-.03),(.65,.72,.54,-.02),(.92,.75,.56,.02),
    (1.17,.70,.51,.015),(1.39,.625,.45,.006),(1.48,.575,.39,.008),(1.62,.655,.445,.03),
    (1.82,.735,.51,.065),(2.08,.74,.49,.065),(2.35,.695,.47,.025),
    (2.56,.54,.38,.006),(2.72,.32,.23,0),(2.80,.006,.006,0)]
EYE_X=.345;EYE_Z=2.235;EYE_R=.093;MOUTH_Z=1.91;MOUTH_RX=.195;MOUTH_RZ=.050
PROFILE_SAMPLES=np.array([catmull(BODY_PROFILE,t) for t in np.linspace(0,1,500)])

def profile_at(z):
    samples=PROFILE_SAMPLES
    return tuple(np.interp(z,samples[:,0],samples[:,i]) for i in [1,2,3])

def facial_volume(x,z):
    cheeks=.080*(math.exp(-((x-.39)/.26)**2-((z-1.955)/.24)**2)+math.exp(-((x+.39)/.26)**2-((z-1.955)/.24)**2))
    muzzle=.110*math.exp(-(x/.38)**4-((z-1.995)/.21)**2)
    chin=.075*math.exp(-(x/.40)**4-((z-1.71)/.15)**2)
    eye=0.0
    for s in [-1,1]:
        r=math.sqrt(((x-s*EYE_X)/.112)**2+((z-EYE_Z)/.115)**2)
        eye+=.022*math.exp(-((r-1.05)/.32)**2)-.020*math.exp(-(r/.8)**2)
    return cheeks+muzzle+chin+eye

def front_surface(x,z):
    rx,ry,cy=profile_at(z)
    sine=math.sqrt(max(0,1-(x/max(rx,.01))**2))
    return cy+ry*sine+sine**12*facial_volume(x,z)

EYE_Y=front_surface(EYE_X,EYE_Z)+.017

def anatomical_torso(mat):
    # One authored continuous form: broad rounded head, hidden short neck, pear belly and hips.
    profile=BODY_PROFILE
    rings=300;sides=256;vs=[];fs=[]
    for i in range(rings):
        z,rx,ry,cy=catmull(profile,i/(rings-1));rx=max(.005,rx);ry=max(.005,ry)
        if z>2.30:
            cap=max(.004,.705*math.sqrt(max(0,1-((z-2.105)/.695)**2)))
            blend=max(0,min(1,(z-2.30)/.20));blend=blend*blend*(3-2*blend)
            rx=rx*(1-blend)+cap*blend;ry=ry*(1-blend)+cap*.71*blend
        for j in range(sides):
            a=math.tau*j/sides;x=rx*math.cos(a);y=cy+ry*math.sin(a)
            front=max(0,math.sin(a))**12
            # Sculpted cheeks, chin, nose bridge and orbital recesses are actual surface geometry.
            y+=front*facial_volume(x,z)
            vs.append((x,y,z))
    for i in range(rings-1):
        for j in range(sides):fs.append((i*sides+j,i*sides+(j+1)%sides,(i+1)*sides+(j+1)%sides,(i+1)*sides+j))
    fs.extend([tuple(reversed(range(sides))),tuple((rings-1)*sides+j for j in range(sides))])
    return create_mesh('Anatomically sculpted trunk and head',vs,fs,mat)

def limb(name, controls, radii, mat, flatten=1, sides=80, steps=20):
    # Deformed section sweep, with anatomically varying forearm/thigh/heel cross sections.
    n=(len(controls)-1)*steps+1;vs=[];fs=[];previous_normal=None
    for i in range(n):
        t=i/(n-1);p=Vector(catmull(controls,t));r=float(catmull(radii,t))
        p0=Vector(catmull(controls,max(0,t-.001)));p1=Vector(catmull(controls,min(1,t+.001)))
        tangent=(p1-p0).normalized()
        if previous_normal is None:
            axis=Vector((0,0,1)) if abs(tangent.z)<.9 else Vector((1,0,0))
            normal=tangent.cross(axis).normalized()
        else:
            normal=(previous_normal-tangent*previous_normal.dot(tangent)).normalized()
        bitangent=tangent.cross(normal).normalized();previous_normal=normal
        for j in range(sides):
            a=math.tau*j/sides;section=normal*math.cos(a)+bitangent*math.sin(a)*flatten
            vs.append(tuple(p+section*max(.001,r)))
    for i in range(n-1):
        for j in range(sides):fs.append((i*sides+j,i*sides+(j+1)%sides,(i+1)*sides+(j+1)%sides,(i+1)*sides+j))
    fs.extend([tuple(reversed(range(sides))),tuple((n-1)*sides+j for j in range(sides))])
    return create_mesh(name,vs,fs,mat)

def ellipsoid(name, center, radii, mat, bone=None, segments=96, rings=64):
    vs=[];fs=[];uv=[]
    for i in range(rings+1):
        p=-math.pi/2+math.pi*i/rings
        for j in range(segments):
            a=math.tau*j/segments
            vs.append((center[0]+radii[0]*math.cos(p)*math.cos(a),center[1]+radii[1]*math.cos(p)*math.sin(a),center[2]+radii[2]*math.sin(p)))
            uv.append((j/segments,i/rings))
    for i in range(rings):
        for j in range(segments):fs.append((i*segments+j,i*segments+(j+1)%segments,(i+1)*segments+(j+1)%segments,(i+1)*segments+j))
    o=create_mesh(name,vs,fs,mat,uv);o['rig_bone']=bone or 'head';return o

def join_remesh(objects, voxel):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:o.select_set(True)
    bpy.context.view_layer.objects.active=objects[0];bpy.ops.object.join();o=objects[0]
    rem=o.modifiers.new('Continuous sculpt voxel union','REMESH');rem.mode='VOXEL';rem.voxel_size=voxel;rem.use_smooth_shade=True
    bpy.ops.object.modifier_apply(modifier=rem.name)
    fusion=o.vertex_groups.new(name='Soft anatomical fusion zones')
    for v in o.data.vertices:
        x,y,z=v.co;ax=abs(x)
        neck=math.exp(-((z-1.55)/.24)**2)*.9
        shoulder=math.exp(-((ax-.57)/.22)**2-((z-1.37)/.23)**2)
        hip=math.exp(-((ax-.43)/.26)**2-((z-.62)/.25)**2)*.85
        ankle=math.exp(-((ax-.41)/.24)**2-((z-.20)/.19)**2)*.75
        tail=math.exp(-((y+.48)/.33)**2-((z-.60)/.24)**2)*.75
        w=min(1,max(neck,shoulder,hip,ankle,tail))
        if w>.002:fusion.add([v.index],w,'REPLACE')
    smooth=o.modifiers.new('Sculpt soft shoulder neck hip and ankle transitions','SMOOTH');smooth.factor=.80;smooth.iterations=280;smooth.vertex_group=fusion.name
    bpy.ops.object.modifier_apply(modifier=smooth.name)
    o.vertex_groups.remove(o.vertex_groups.get('Soft anatomical fusion zones'))
    o.name='NailongContinuousSkin';return o

def skin_uv(o):
    # The boolean cutter has its own UV. Do not leave that layer active on skin.
    for old in list(o.data.uv_layers):o.data.uv_layers.remove(old)
    coords=np.empty(len(o.data.vertices)*3,np.float32);o.data.vertices.foreach_get('co',coords);coords=coords.reshape(-1,3)
    uv=np.stack([np.mod(np.arctan2(coords[:,1],coords[:,0])/math.tau,1),np.clip(coords[:,2]/2.8,0,1)],axis=1)
    layer=o.data.uv_layers.new(name='AuthoredCylindricalUV');idx=np.empty(len(o.data.loops),np.int32);o.data.loops.foreach_get('vertex_index',idx)
    # Keep each triangle on a single side of the seam; no streak across the back.
    values=uv[idx].copy()
    for p in o.data.polygons:
        sl=slice(p.loop_start,p.loop_start+p.loop_total);u=values[sl,0]
        if np.ptp(u)>.5:values[sl,0]=np.where(u<.5,u+1,u)
    layer.data.foreach_set('uv',values.ravel())

def iris_cap(name,cx,mat,radius,depth,bone,segments=128,rings=36):
    vs=[];fs=[];uv=[]
    for i in range(rings+1):
        r=radius*i/rings
        for j in range(segments):
            a=math.tau*j/segments
            vs.append((cx+r*math.cos(a),EYE_Y+.044+depth*(1-(r/.105)**2),EYE_Z+r*math.sin(a)))
            uv.append((.5+r*math.cos(a)/(radius*2),.5+r*math.sin(a)/(radius*2)))
    for i in range(rings):
        for j in range(segments):fs.append((i*segments+j,i*segments+(j+1)%segments,(i+1)*segments+(j+1)%segments,(i+1)*segments+j))
    o=create_mesh(name,vs,fs,mat,uv);o['rig_bone']=bone;return o

def mouth_mesh(name,mat,kind='cavity'):
    # Smooth closed smile cavity and small enamel strip, with actual inward depth.
    n=128;vs=[];fs=[];uv=[]
    for ring in range(13):
        t=ring/12
        for j in range(n):
            a=math.tau*j/n
            w=.23 if kind=='cavity' else .196
            height=.026 if kind=='cavity' else .014
            x=w*t*math.cos(a);z=1.963+height*t*math.sin(a)+.035*(x/w)**2
            y=.553 if kind=='cavity' else .557
            y+=.016*(1-t*t)-.023*(x/w)**2
            vs.append((x,y,z));uv.append((.5+.5*t*math.cos(a),.5+.5*t*math.sin(a)))
    for ring in range(12):
        for j in range(n):fs.append((ring*n+j,ring*n+(j+1)%n,(ring+1)*n+(j+1)%n,(ring+1)*n+j))
    if kind=='teeth':
        count=len(vs);front_faces=list(fs)
        vs.extend((x,y-.008,z) for x,y,z in list(vs));uv.extend(list(uv))
        fs.extend(tuple(count+index for index in reversed(face)) for face in front_faces)
        outer=12*n
        for j in range(n):
            a=outer+j;b=outer+(j+1)%n;fs.append((a,a+count,b+count,b))
    o=create_mesh(name,vs,fs,mat,uv);o['rig_bone']='jaw'
    o.shape_key_add(name='Basis');focus=o.shape_key_add(name='Focus')
    for vertex in focus.data:
        vertex.co.z-=.031*(vertex.co.x/w)**2
        if kind=='teeth':vertex.co.y-=.020;vertex.co.z-=.008
    return o

def anatomical_upper_lid(side,s,skin):
    cx=s*EYE_X;columns=64;rows=10;vs=[];fs=[];uv=[];states={'Basis':[],'Blink':[],'Focus':[]}
    def point(x,top,bottom,row):
        z=bottom+(top-bottom)*row
        globe=EYE_Y+.046*math.sqrt(max(0,1-(x/.095)**2-(z/.101)**2))
        lens=EYE_Y+.044+.028*(1-(x*x+z*z)/.011025) if x*x+z*z<.088*.088 else -.5
        return (cx+x,max(globe,lens)+.002,EYE_Z+z)
    for i in range(rows+1):
        row=i/rows
        for j in range(columns+1):
            x=-.095+.190*j/columns;top=.103*math.sqrt(max(0,1-(x/.095)**2))
            base=point(x,top,min(top,.091),row);vs.append(base)
            states['Blink'].append(point(x,top,-top,row));states['Focus'].append(point(x,top,min(top,.055),row))
            uv.append((math.atan2(base[1],base[0])/math.tau,base[2]/2.8))
    for i in range(rows):
        for j in range(columns):
            k=i*(columns+1)+j;fs.append((k,k+columns+1,k+columns+2,k+1))
    o=create_mesh(side+' anatomical upper lid',vs,fs,skin,uv);o['rig_bone']='head'
    o.shape_key_add(name='Basis')
    for name in ['Blink','Focus']:
        key=o.shape_key_add(name=name)
        for v,co in zip(key.data,states[name]):v.co=co
    return o

def cut_real_oral_aperture(skin):
    # An actual hole in the primary skin; the cavity is behind this opening.
    center=front_surface(0,MOUTH_Z)-.18
    cutter=ellipsoid('Temporary oral volume cutter',(0,center,MOUTH_Z),(.213,.40,.061),None,segments=128,rings=72)
    bpy.context.view_layer.objects.active=skin
    mod=skin.modifiers.new('Actual mouth aperture with manifold inner wall','BOOLEAN');mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter,do_unlink=True)

ORAL_RIM=[]
SKIN_BVH=None
def measure_oral_rim(skin,samples=96):
    global ORAL_RIM,SKIN_BVH
    bvh=BVHTree.FromPolygons([v.co for v in skin.data.vertices],[p.vertices[:] for p in skin.data.polygons])
    SKIN_BVH=bvh
    ORAL_RIM=[]
    for j in range(samples):
        a=math.tau*j/samples;low=.60;high=1.50
        def hit(scale):
            x=.213*scale*math.cos(a);z=MOUTH_Z+.061*scale*math.sin(a)
            location,normal,index,distance=bvh.ray_cast(Vector((x,1.5,z)),Vector((0,-1,0)),2.5)
            return location, location is not None and location.y>front_surface(x,z)-.040
        for k in range(15):
            mid=(low+high)*.5;point,outside=hit(mid)
            if outside:high=mid
            else:low=mid
        point,outside=hit(high+.0001)
        if point is None:raise RuntimeError('Cannot locate authored skin aperture')
        ORAL_RIM.append(tuple(point))

def oral_open_vector(v):
    x,y,z=v;u=x/MOUTH_RX;h=(z-MOUTH_Z)/MOUTH_RZ;r=math.sqrt(u*u+h*h)
    front=max(0,min(1,(y-.23)/.22));band=math.exp(-((r-1)/1.08)**2)
    return Vector((x*(1+.11*band*front),y+.009*band*front,z+(z-MOUTH_Z)*1.62*band*front))

def oral_closed_vector(v):
    x,y,z=v;r=math.sqrt((x/MOUTH_RX)**2+((z-MOUTH_Z)/MOUTH_RZ)**2)
    front=max(0,min(1,(y-.23)/.22));band=math.exp(-((r-1)/1.08)**2)
    return Vector((x,y,z-(z-MOUTH_Z)*.92*band*front))

def add_skin_oral_morph(skin):
    original=[v.co.copy() for v in skin.data.vertices]
    skin.shape_key_add(name='Basis');key=skin.shape_key_add(name='Open')
    for vertex,co in zip(key.data,original):vertex.co=oral_open_vector(co)
    for vertex,co in zip(skin.data.shape_keys.key_blocks['Basis'].data,original):vertex.co=oral_closed_vector(co)

def oral_component(name,material,kind='cavity'):
    n=96;rows=24;vs=[];fs=[];uv=[]
    for row in range(rows+1):
        t=row/rows
        for j in range(n):
            a=math.tau*j/n
            rim=Vector(ORAL_RIM[j])
            if kind=='cavity':
                scale=.30+.70*t;x=rim.x*scale;z=MOUTH_Z+(rim.z-MOUTH_Z)*scale
                y=rim.y-.205*(1-t)+.001
            else:
                # Upper/lower lip are one soft tissue annulus contacting the real opening.
                scale=.994+.075*t;x=rim.x*scale;z=MOUTH_Z+(rim.z-MOUTH_Z)*scale
                y=rim.y+.002*math.sin(math.pi*t)+.0006
            vs.append((x,y,z));uv.append((j/n,t) if kind=='cavity' else (math.atan2(y,x)/math.tau,z/2.8))
    for row in range(rows):
        for j in range(n):fs.append((row*n+j,row*n+(j+1)%n,(row+1)*n+(j+1)%n,(row+1)*n+j))
    if kind=='cavity':
        center=len(vs);vs.append((0,sum(p[1] for p in ORAL_RIM)/n-.215,MOUTH_Z));uv.append((.5,0))
        for j in range(n):fs.append((center,(j+1)%n,j))
    o=create_mesh(name,vs,fs,material,uv);o['rig_bone']='head'
    original=[v.co.copy() for v in o.data.vertices]
    o.shape_key_add(name='Basis');key=o.shape_key_add(name='Open')
    for vertex,co in zip(key.data,original):vertex.co=oral_open_vector(co)
    for vertex,co in zip(o.data.shape_keys.key_blocks['Basis'].data,original):vertex.co=oral_closed_vector(co)
    return o

def animate_shapes(objects,clips,fps=30):
    for obj in objects:
        keys=obj.data.shape_keys
        if keys is None:continue
        keys.animation_data_create()
        for old in list(keys.animation_data.nla_tracks):keys.animation_data.nla_tracks.remove(old)
        for name,duration in clips.items():
            for track in keys.animation_data.nla_tracks:track.mute=True
            action=bpy.data.actions.new(name+' / '+obj.name+' facial');keys.animation_data.action=action
            frames=max(2,round(duration*fps))
            for frame in range(frames+1):
                t=frame/frames;p=math.tau*t
                blink=max(0,1-abs(t-(.56 if name=='idle' else .65))/.035) if name in ['idle','recover'] else 0
                focus=0 if name=='idle' else .07 if name=='walk' else .23 if name=='chase' else .36*math.sin(t*math.pi/2) if name=='warn' else .30 if name=='charge' else .16
                opening=.20+.10*math.sin(p) if name=='idle' else .25 if name=='walk' else .32 if name=='chase' else .82*math.sin(t*math.pi/2) if name=='warn' else .56+.10*math.sin(2*p) if name=='charge' else .47+.13*math.sin(p)
                for key in keys.key_blocks:
                    if key.name=='Basis':continue
                    key.value=blink if key.name=='Blink' else focus if key.name=='Focus' else max(0,opening)
                    key.keyframe_insert('value',frame=frame+1)
            track=keys.animation_data.nla_tracks.new();track.name=name;strip=track.strips.new(name,1,action);strip.name=name
            keys.animation_data.action=None
        for track in keys.animation_data.nla_tracks:track.mute=False

def make_rig():
    data=bpy.data.armatures.new('Nailong anatomical skeleton');rig=bpy.data.objects.new('NailongRig',data);bpy.context.collection.objects.link(rig)
    bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
    bones=[('root',(0,0,0),(0,0,.30),None),('pelvis',(0,0,.43),(0,0,.88),'root'),
           ('spine',(0,0,.88),(0,0,1.40),'pelvis'),('belly',(0,.23,.93),(0,.23,1.23),'spine'),
           ('neck',(0,0,1.40),(0,0,1.69),'spine'),('head',(0,0,1.69),(0,0,2.5),'neck'),
           ('jaw',(0,.39,1.99),(0,.51,1.925),'head'),('tail',(0,-.30,.65),(0,-.66,.51),'pelvis')]
    for side,s in [('left',-1),('right',1)]:
        bones.extend([(f'upper_arm_{side}',(s*.45,.01,1.49),(s*.68,.055,1.22),'spine'),
                      (f'forearm_{side}',(s*.68,.055,1.22),(s*.75,.23,1.10),f'upper_arm_{side}'),
                      (f'palm_{side}',(s*.75,.23,1.10),(s*.75,.31,1.01),f'forearm_{side}'),
                      (f'thigh_{side}',(s*.37,0,.68),(s*.39,.015,.35),'pelvis'),
                      (f'shin_{side}',(s*.39,.015,.35),(s*.40,.08,.14),f'thigh_{side}'),
                      (f'foot_{side}',(s*.40,.08,.14),(s*.40,.26,.14),f'shin_{side}'),
                      (f'eye_{side}',(s*EYE_X,EYE_Y,EYE_Z),(s*EYE_X,EYE_Y,EYE_Z+.12),'head'),
                      (f'brow_{side}',(s*EYE_X,EYE_Y-.02,EYE_Z+.13),(s*EYE_X,EYE_Y-.02,EYE_Z+.19),'head')])
    for name,a,b,parent in bones:
        bone=data.edit_bones.new(name);bone.head=a;bone.tail=b
        if parent:bone.parent=data.edit_bones[parent]
    bpy.ops.object.mode_set(mode='OBJECT');rig.select_set(False)
    for p in rig.pose.bones:p.rotation_mode='XYZ'
    return rig,bones

def bind(o,rig,weight=None):
    if weight is None:
        bone=o.get('rig_bone','head');vg=o.vertex_groups.new(name=bone);vg.add(list(range(len(o.data.vertices))),1,'REPLACE')
    else:
        groups={name:o.vertex_groups.new(name=name) for name in rig.data.bones.keys()}
        for i,v in enumerate(o.data.vertices):
            weights=weight(v.co);total=sum(weights.values())
            for name,w in weights.items():
                if w>.0001:groups[name].add([i],w/total,'REPLACE')
    mod=o.modifiers.new('Skin / independent per-instance bones','ARMATURE');mod.object=rig;o.parent=rig

def continuous_weights(v):
    x,y,z=v;s=-1 if x<0 else 1;side='left' if s<0 else 'right';ax=abs(x)
    def smooth(a,b,value):
        t=max(0,min(1,(value-a)/(b-a)));return t*t*(3-2*t)
    # Continuous partitions of unity, including the lower belly between the legs.
    # Abrupt region tests would split neighbouring vertices when a thigh swings.
    head=smooth(1.51,1.82,z)
    arm=smooth(.49,.71,ax)*smooth(.76,1.04,z)*(1-smooth(1.43,1.72,z))*(1-head)
    tail=smooth(.37,.65,-y)*(1-smooth(.76,.99,z))*(1-head)*(1-arm)
    sole_blend=1-smooth(.16,.32,z)
    leg_side=smooth(.15,.37,ax)*(1-sole_blend)+smooth(.03,.16,ax)*sole_blend
    leg=leg_side*(1-smooth(.52,.85,z))*(1-head)*(1-arm)*(1-tail)
    trunk=max(0,1-head-arm-tail-leg)
    spine=smooth(.69,1.13,z);neck=smooth(1.36,1.60,z)
    belly=max(0,min(.16,(y-.13)*.28))*(1-smooth(1.18,1.43,z))*spine
    fore=1-smooth(1.15,1.42,z);palm=1-smooth(1.02,1.15,z)
    foot=1-smooth(.13,.285,z);shin=smooth(.135,.32,z)*(1-smooth(.31,.53,z));thigh=max(0,1-foot-shin)
    result={'head':head,'neck':trunk*neck,'pelvis':trunk*(1-spine)*(1-neck),
        'spine':trunk*(spine-belly)*(1-neck),'belly':trunk*belly*(1-neck),'tail':tail,
        f'upper_arm_{side}':arm*(1-fore),f'forearm_{side}':arm*fore*(1-palm),f'palm_{side}':arm*fore*palm,
        f'thigh_{side}':leg*thigh,f'shin_{side}':leg*shin,f'foot_{side}':leg*foot}
    # Four native influences, normalized in bind(), agree with the actual GLB GPU path.
    return dict(sorted(result.items(),key=lambda item:item[1],reverse=True)[:4])

def animations(rig,shape_objects):
    clips={'idle':3.2,'walk':1.0,'chase':.68,'warn':.8,'charge':.50,'recover':2.0}
    fps=30;scene=bpy.context.scene;scene.render.fps=fps
    for name,duration in clips.items():
        rig.animation_data_create();rig.animation_data.action=bpy.data.actions.new(name)
        for track in rig.animation_data.nla_tracks:track.mute=True
        frames=max(2,round(duration*fps));MANIFEST['clips'][name]={'duration':duration,'frames':frames,'root_motion':False}
        for frame in range(frames+1):
            t=frame/frames;p=math.tau*t
            for bone in rig.pose.bones:
                bone.location=(0,0,0);bone.rotation_euler=(0,0,0);bone.scale=(1,1,1)
            pelvis=rig.pose.bones['pelvis'];spine=rig.pose.bones['spine'];head=rig.pose.bones['head'];belly=rig.pose.bones['belly'];jaw=rig.pose.bones['jaw']
            breathe=math.sin(p);belly.scale=(1+.012*breathe,1+.018*breathe,1+.012*breathe)
            rig.pose.bones['tail'].rotation_euler[2]=.07*math.sin(p+.3)
            # Root stays fixed. Pose offsets only, so gameplay navigation and collision are authoritative.
            if name=='idle':
                spine.rotation_euler[2]=.011*math.sin(p);head.rotation_euler[2]=-.014*math.sin(p)
                blink=max(0,1-abs(t-.56)/.025);gaze=.015*math.sin(p)
            elif name in ['walk','chase','charge']:
                amp={'walk':.32,'chase':.52,'charge':.67}[name]
                spine.rotation_euler[0]=-.055 if name=='walk' else -.12 if name=='chase' else -.19
                pelvis.location.y=.024*math.cos(2*p) # bone local Y is world height.
                pelvis.rotation_euler[2]=.035*math.sin(p);spine.rotation_euler[2]=-.025*math.sin(p)
                head.rotation_euler[0]=.025;head.rotation_euler[2]=-.021*math.sin(p)
                for side,offset in [('left',0),('right',math.pi)]:
                    q=p+offset;th=rig.pose.bones['thigh_'+side];shin=rig.pose.bones['shin_'+side];foot=rig.pose.bones['foot_'+side]
                    th.rotation_euler[0]=-amp*math.sin(q);shin.rotation_euler[0]=max(0,math.sin(q))*(.45 if name=='walk' else .70)
                    foot.rotation_euler[0]=-th.rotation_euler[0]-shin.rotation_euler[0]
                    foot.location.y=max(0,math.sin(q))*(.02 if name=='walk' else .038)
                    rig.pose.bones['upper_arm_'+side].rotation_euler[0]=.31*math.sin(q)
                    rig.pose.bones['forearm_'+side].rotation_euler[0]=-.16+(.06*math.cos(q))
                    rig.pose.bones['eye_'+side].scale.y=1.0
                    rig.pose.bones['brow_'+side].rotation_euler[2]=(-1 if side=='left' else 1)*(.1 if name=='walk' else .19)
                belly.scale=(1+.014*math.sin(2*p-.4),1+.010*math.sin(2*p-.4),1+.014*math.sin(2*p-.4));blink=0;gaze=0
                jaw.rotation_euler[0]=-.025 if name=='walk' else -.055
            elif name=='warn':
                anticipation=math.sin(t*math.pi/2);pelvis.location.y=-.065*anticipation
                spine.rotation_euler[0]=-.15*anticipation;head.rotation_euler[0]=.06*anticipation
                for side,s in [('left',-1),('right',1)]:
                    rig.pose.bones['thigh_'+side].rotation_euler[0]=.18*anticipation
                    rig.pose.bones['shin_'+side].rotation_euler[0]=-.32*anticipation
                    rig.pose.bones['foot_'+side].rotation_euler[0]=.14*anticipation
                    rig.pose.bones['upper_arm_'+side].rotation_euler[0]=-.26*anticipation
                    rig.pose.bones['brow_'+side].rotation_euler[2]=s*.24*anticipation
                    rig.pose.bones['eye_'+side].scale.y=1.0
                jaw.rotation_euler[0]=-.06*anticipation;blink=0;gaze=0
            else:
                spine.rotation_euler[0]=-.065;head.rotation_euler[0]=.045
                belly.scale=(1+.025*breathe,1+.029*breathe,1+.025*breathe)
                for side in ['left','right']:
                    rig.pose.bones['upper_arm_'+side].rotation_euler[0]=-.12
                    rig.pose.bones['eye_'+side].scale.y=1.0
                blink=max(0,1-abs(t-.65)/.035);gaze=.008*math.sin(p);jaw.rotation_euler[0]=-.025-.014*breathe
            if name in ['idle','recover']:
                for side in ['left','right']:
                    eye=rig.pose.bones['eye_'+side];eye.rotation_euler[2]=gaze
            bpy.context.view_layer.update()
            if name in ['walk','chase','charge','warn']:
                for side,s,offset in [('left',-1,0),('right',1,math.pi)]:
                    foot=rig.pose.bones['foot_'+side]
                    deform=foot.matrix @ foot.bone.matrix_local.inverted()
                    probes=[Vector((s*.40,-.07,.018)),Vector((s*.40,.31,.018)),Vector((s*.58,.13,.018)),Vector((s*.23,.13,.018))]
                    floor=min((deform @ v).z for v in probes)
                    lift=0 if name=='warn' else max(0,math.sin(p+offset))*({'walk':.055,'chase':.085,'charge':.105}[name])
                    parent=foot.parent
                    basis=parent.matrix @ parent.bone.matrix_local.inverted() @ foot.bone.matrix_local
                    correction=basis.to_3x3().inverted() @ Vector((0,0,.018+lift-floor))
                    foot.location+=correction
            for bone in rig.pose.bones:
                bone.keyframe_insert('location',frame=frame+1);bone.keyframe_insert('rotation_euler',frame=frame+1);bone.keyframe_insert('scale',frame=frame+1)
        action=rig.animation_data.action
        for curve in action.fcurves:
            for k in curve.keyframe_points:k.interpolation='BEZIER'
        track=rig.animation_data.nla_tracks.new();track.name=name;strip=track.strips.new(name,1,action);strip.name=name
        rig.animation_data.action=None
    for track in rig.animation_data.nla_tracks:track.mute=False
    animate_shapes(shape_objects,clips,fps)
    scene.frame_set(1)

def build():
    clear();skin=skin_material();claw=material('Warm small nail keratin',(.25,.115,.025),.44)
    white=material('Ivory sclera',(.95,.92,.77),.23);iris=iris_material();pupil=material('Deep black pupil',(.004,.006,.0015),.12)
    cornea=material('Corneal wet surface',(.96,.98,.95),.045);p=cornea.node_tree.nodes.get('Principled BSDF')
    p.inputs['Transmission Weight'].default_value=1.0;p.inputs['IOR'].default_value=1.38
    mouth=material('Deep burgundy oral mucosa',(.016,.0018,.004),.91)
    mouth.node_tree.nodes.get('Principled BSDF').inputs['Specular IOR Level'].default_value=.10
    pink=material('Soft pink palm and plantar cushion',(.80,.28,.32),.64,.12)
    tongue_material=material('Warm pink living tongue',(.43,.10,.13),.56,.10)
    trunk=anatomical_torso(skin);flesh=[trunk];attachments=[]
    for side,s in [('left',-1),('right',1)]:
        arm=limb('Soft stubby '+side+' arm',[(s*.45,.025,1.44),(s*.64,.065,1.32),(s*.73,.17,1.17),(s*.74,.29,1.08),(s*.71,.35,1.055)],[.255,.247,.232,.182,.055],skin,flatten=.94)
        leg=limb('Continuous '+side+' leg heel and forefoot',[(s*.37,-.015,.71),(s*.395,0,.48),
            (s*.405,.015,.27),(s*.405,.11,.135),(s*.405,.29,.12),(s*.405,.355,.12)],
            [.27,.26,.23,.195,.163,.012],skin,flatten=1.0,sides=96,steps=22)
        for v in leg.data.vertices:
            if v.co.z<.17:v.co.z=.012+.018*math.log1p(math.exp((v.co.z-.012)/.018))
        flesh.extend([arm,leg])
        for digit in range(3):
            xx=s*(.27+digit*.13);toe=limb(side+' toe pad '+str(digit),[(xx,.23,.125),(xx,.32,.12),(xx,.387,.113)],[.087,.085,.025],skin,flatten=1,sides=40,steps=12)
            for v in toe.data.vertices:v.co.z=.115+(v.co.z-.115)*.65
            flesh.append(toe)
            nail=limb(side+' small brown toe claw '+str(digit),[(xx,.348,.13),(xx,.375,.12),(xx,.410,.093),(xx,.420,.084)],[.029,.025,.012,.003],claw,sides=40,steps=12)
            nail['rig_bone']='foot_'+side;attachments.append(nail)
            handx=s*(.635+digit*.078)
            finger=limb(side+' soft distal finger '+str(digit),[(handx,.315,1.063),(handx,.355,1.045),(handx,.395,1.024)],[.043,.045,.005],skin,sides=48,steps=16)
            flesh.append(finger)
            nail=limb(side+' small brown hand claw '+str(digit),[(handx,.379,1.037),(handx,.406,1.030),(handx,.426,1.013),(handx,.433,1.006)],[.020,.017,.009,.002],claw,sides=32,steps=10)
            nail['rig_bone']='palm_'+side;attachments.append(nail)
        attachments.append(ellipsoid(side+' pink plantar cushion',(s*.405,.130,.013),(.133,.147,.008),pink,'foot_'+side,96,64))
        eye='eye_'+side;cx=s*EYE_X
        attachments.append(ellipsoid(side+' small crescent sclera',(cx,EYE_Y,EYE_Z),(.095,.046,.101),white,eye,96,56))
        attachments.append(iris_cap(side+' thin green iris',cx,iris,.080,.014,eye,96,32))
        attachments.append(iris_cap(side+' dominant black pupil',cx,pupil,.071,.017,eye,96,24))
        # Cornea retains a proper clear domed layer and real specular response.
        attachments.append(iris_cap(side+' corneal lens',cx,cornea,.088,.028,eye,96,24))
        attachments.append(anatomical_upper_lid(side,s,skin))
        # The orbital ridge is sculpted into the face; no external pipe eye rim/brow.
    tail=limb('Short plump upcurved tail',[(0,-.34,.61),(0,-.51,.52),(0,-.69,.54),(0,-.77,.65),(0,-.80,.72)],[.26,.22,.15,.082,.004],skin,flatten=.92)
    flesh.append(tail)
    source=join_remesh(flesh,.0045);cut_real_oral_aperture(source);measure_oral_rim(source);skin_uv(source)
    for side,s in [('left',-1),('right',1)]:
        hit,normal,index,distance=SKIN_BVH.ray_cast(Vector((s*.715,1.5,1.130)),Vector((0,-1,0)),2.5)
        if hit is None:raise RuntimeError('Palm cushion must attach to real flesh')
        attachments.append(ellipsoid(side+' embedded soft palm cushion',(s*.715,hit.y-.008,1.130),(.090,.032,.093),pink,'palm_'+side,96,56))
    MANIFEST['source_skin_triangles']=sum(len(p.vertices)-2 for p in source.data.polygons)
    source.name='NailongHighSculpt';source['authored_detail']='Continuous remeshed anatomical sculpt, UV-mapped soft skin'
    # Save recoverable high master separately. Runtime is a geometric reduction of this authored sculpt.
    bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE/'nailong_high_sculpt.blend'))
    bpy.ops.file.make_paths_relative()
    bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE/'nailong_high_sculpt.blend'))
    dec=source.modifiers.new('Game surface reduction retaining silhouette','DECIMATE');dec.ratio=.09
    bpy.context.view_layer.objects.active=source;bpy.ops.object.modifier_apply(modifier=dec.name);source.name='NailongSkin_LOD0'
    rig,bones=make_rig();bind(source,rig,continuous_weights)
    neutral_skin_data=source.data.copy()
    add_skin_oral_morph(source)
    for a in attachments:bind(a,rig)
    cavity=oral_component('Deep actual oral cavity',mouth)
    lips=oral_component('Soft integrated upper and lower lips',skin,'lips')
    tongue=ellipsoid('Soft volumetric tongue',(0,front_surface(0,MOUTH_Z)-.135,MOUTH_Z-.030),(.124,.087,.027),tongue_material,'head',64,40)
    tongue.shape_key_add(name='Basis');key=tongue.shape_key_add(name='Open')
    for vertex in key.data:vertex.co.z-=.043;vertex.co.y+=.024
    for vertex in tongue.data.shape_keys.key_blocks['Basis'].data:vertex.co.z-=.015;vertex.co.y-=.05
    for obj in [cavity,lips,tongue]:bind(obj,rig)
    objects=[source]+attachments+[cavity,lips,tongue]
    shape_objects=[o for o in objects if o.data.shape_keys]
    animations(rig,shape_objects)
    MANIFEST['bones']=len(bones);MANIFEST['lod0_triangles']=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in objects)
    MANIFEST['bounds_rest_blender']={'min':[-1.03,-1.01,-.025],'max':[1.03,.66,2.83]}
    MANIFEST['bounds_animation_godot']={'position':[-1.25,-.2,-1.32],'size':[2.5,3.22,2.55]}
    MANIFEST['reference_metrics']={'eye_diameter_head_width':.125,'pupil_iris_radius':.8875,'body_mouth_aperture':True,'pink_palm_sole_pads':True}
    # Runtime asset includes UV originals, independent bones and native animation tracks.
    for track in rig.animation_data.nla_tracks:track.mute=track.name!='idle'
    for obj in shape_objects:
        for track in obj.data.shape_keys.animation_data.nla_tracks:track.mute=track.name!='idle'
    bpy.context.scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE/'nailong_game_rig.blend'))
    for track in rig.animation_data.nla_tracks:track.mute=False
    for obj in shape_objects:
        for track in obj.data.shape_keys.animation_data.nla_tracks:track.mute=False
    export_objects=[rig]+objects
    def export(filename):
        bpy.ops.object.select_all(action='DESELECT')
        for o in export_objects:o.select_set(True)
        bpy.context.view_layer.objects.active=rig
        bpy.ops.export_scene.gltf(filepath=str(OUT/filename),export_format='GLB',use_selection=True,
            export_yup=True,export_apply=False,export_animations=True,export_animation_mode='NLA_TRACKS',
            export_nla_strips=True,export_skins=True,export_normals=True,export_tangents=True,
            export_materials='EXPORT',export_cameras=False,export_lights=False)
    export('nailong_lod0.glb')
    for level,ratio in [(1,.28),(2,.22)]:
        for o in objects:
            if o.data.shape_keys and o!=source:continue # Preserve small facial morph topology.
            if o==source:o.data=neutral_skin_data
            bpy.context.view_layer.objects.active=o
            # Apply reduction before armature; preserve inherited vertex skin weights.
            mod=o.modifiers.new('Distance geometry reduction','DECIMATE');mod.ratio=ratio
            bpy.ops.object.modifier_move_up(modifier=mod.name)
            bpy.ops.object.modifier_apply(modifier=mod.name)
            if o==source:
                neutral_skin_data=o.data.copy()
                add_skin_oral_morph(o)
                animate_shapes([o],{name:clip['duration'] for name,clip in MANIFEST['clips'].items()})
        MANIFEST['lod'+str(level)+'_triangles']=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in objects)
        export('nailong_lod'+str(level)+'.glb')
    (OUT/'MODEL_MANIFEST.json').write_text(json.dumps(MANIFEST,ensure_ascii=False,indent=2)+'\n')
    print('NAILONG_ASSET_BUILT '+json.dumps(MANIFEST))

if __name__=='__main__':build()
