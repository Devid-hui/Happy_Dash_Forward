"""High resolution masters and independently authored runtime LODs for field assets.
Blender 4.5 LTS. Original meshes/material maps only. Keeps 17-bone hand interfaces.
Source detail is generated from actual curved anatomy, hardware and manufactured parts.
Run: Blender --background --python tools/build_commercial_assets.py -- --output-root REPO --asset equipment|car|all
"""
import bpy, bmesh, numpy as np, math, json, sys, importlib.util, time, types
from pathlib import Path
from mathutils import Vector

base=types.ModuleType('field_base');base.__file__=str(Path(__file__).with_name('build_field_assets.py'))
source=Path(base.__file__).read_text().split('\nfield_equipment();car();tower();book()')[0]
exec(compile(source,base.__file__,'exec'),base.__dict__)
ROOT=base.ROOT;OUT=base.OUT;SOURCE=base.SOURCE;TEXTURES=OUT/'textures';TEXTURES.mkdir(exist_ok=True)
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
ASSET=args[args.index('--asset')+1] if '--asset' in args else 'all'
HI=False
COUNTS=json.loads((SOURCE/'COMMERCIAL_MODEL_MANIFEST.json').read_text()).get('assets',{}) if (SOURCE/'COMMERCIAL_MODEL_MANIFEST.json').exists() else {}
empty=base.empty;box=base.box;mesh=base.mesh;mat=base.mat;uv_sphere=base.uv_sphere;join=base.join_group;beam=base.beam;label=base.label

def uv_assign(obj,coords=None):
    if obj.data.uv_layers:return
    layer=obj.data.uv_layers.new(name='Authored UV')
    if coords is None:
        vertices=np.empty(len(obj.data.vertices)*3,dtype=np.float32);obj.data.vertices.foreach_get('co',vertices);vertices=vertices.reshape(-1,3)
        dims=np.ptp(vertices,axis=0);order=np.argsort(dims)[-2:];coords=vertices[:,order]
        coords=(coords-coords.min(axis=0))/np.maximum(np.ptp(coords,axis=0),.001)
    ids=np.empty(len(obj.data.loops),dtype=np.int32);obj.data.loops.foreach_get('vertex_index',ids)
    layer.data.foreach_set('uv',np.asarray(coords,dtype=np.float32)[ids].reshape(-1))

def shaped_mesh(name,verts,faces,m,parent=None,uv=None,smooth=True):
    o=mesh(name,verts,faces,m,parent,0,smooth);uv_assign(o,uv);return o

def sample_path(points,steps):
    points=[Vector(p) for p in points];result=[]
    for i in range(len(points)-1):
        for j in range(steps):
            t=j/steps;p0=points[max(0,i-1)];p1=points[i];p2=points[i+1];p3=points[min(len(points)-1,i+2)]
            p=.5*((2*p1)+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t*t*t)
            result.append(p)
    result.append(points[-1]);return result

def sweep(name,points,radii,m,parent=None,sides=None,steps=None,ellipse=1.0,fold=0):
    sides=sides or (64 if HI else 20);steps=steps or (20 if HI else 6)
    controls=[Vector(p) for p in points];pts=sample_path(points,steps);verts=[];faces=[];uv=[]
    for i,p in enumerate(pts):
        t=i/(len(pts)-1);q=t*(len(radii)-1);k=min(len(radii)-2,int(q));r=radii[k]+(radii[k+1]-radii[k])*(q-k)
        tangent=(pts[min(i+1,len(pts)-1)]-pts[max(0,i-1)]).normalized();axis=Vector((0,0,1))
        if abs(tangent.dot(axis))>.96:axis=Vector((1,0,0))
        n=tangent.cross(axis).normalized();b=tangent.cross(n).normalized()
        for j in range(sides):
            a=math.tau*j/sides;wrinkle=fold*math.sin(a*7+t*42)*math.exp(-((t-.17)/.16)**2)+fold*.5*math.sin(a*5+t*29)
            rr=r*(1+wrinkle);verts.append(tuple(p+rr*(n*math.cos(a)+b*math.sin(a)*ellipse)));uv.append((j/sides,t))
    for i in range(len(pts)-1):
        for j in range(sides):faces.append((i*sides+j,(i+1)*sides+j,(i+1)*sides+(j+1)%sides,i*sides+(j+1)%sides))
    faces.extend([tuple(reversed(range(sides))),tuple((len(pts)-1)*sides+j for j in range(sides))])
    return shaped_mesh(name,verts,faces,m,parent,uv)

def turned(name,profile,m,parent=None,axis='Y',loc=(0,0,0),sides=None,steps=None,ripple=0,caps=True):
    sides=sides or (192 if HI else 64);steps=steps or (8 if HI else 3)
    # Sample an actual designed section, retain separate sealing shoulders and lens curvatures.
    verts=[];faces=[];uv=[];pro=[]
    for k in range(len(profile)-1):
        for j in range(steps):
            t=j/steps;pro.append((profile[k][0]*(1-t)+profile[k+1][0]*t,profile[k][1]*(1-t)+profile[k+1][1]*t))
    pro.append(profile[-1])
    for k,(z,r) in enumerate(pro):
        for j in range(sides):
            a=j*math.tau/sides;rr=r+ripple*math.sin(80*a)*math.sin(k*.71)
            v=(rr*math.cos(a),rr*math.sin(a),z)
            if axis=='Y':v=(v[0],v[2],v[1])
            elif axis=='X':v=(v[2],v[0],v[1])
            verts.append(tuple(v[i]+loc[i] for i in range(3)));uv.append((j/sides,k/(len(pro)-1)))
    for k in range(len(pro)-1):
        for j in range(sides):faces.append((k*sides+j,k*sides+(j+1)%sides,(k+1)*sides+(j+1)%sides,(k+1)*sides+j))
    if caps: faces.extend([tuple(reversed(range(sides))),tuple((len(pro)-1)*sides+j for j in range(sides))])
    return shaped_mesh(name,verts,faces,m,parent,uv)

def seal(name,loc,major,minor,m,parent=None,axis='Y',rings=None,tube_sides=None):
    rings=rings or (192 if HI else 64);tube_sides=tube_sides or (24 if HI else 8)
    verts=[];faces=[];uv=[]
    for i in range(rings):
        a=i*math.tau/rings
        for j in range(tube_sides):
            b=j*math.tau/tube_sides;r=major+minor*math.cos(b);v=(r*math.cos(a),r*math.sin(a),minor*math.sin(b))
            if axis=='Y':v=(v[0],v[2],v[1])
            elif axis=='X':v=(v[2],v[0],v[1])
            verts.append(tuple(v[k]+loc[k] for k in range(3)));uv.append((i/rings,j/tube_sides))
    for i in range(rings):
        for j in range(tube_sides):faces.append((i*tube_sides+j,((i+1)%rings)*tube_sides+j,((i+1)%rings)*tube_sides+(j+1)%tube_sides,i*tube_sides+(j+1)%tube_sides))
    return shaped_mesh(name,verts,faces,m,parent,uv)

def texture_material(name,color,kind='metal',size=4096,metal=.3,rough=.4):
    # Compact original 4K maps preserve surface variation in native glTF, without unexported procedural nodes.
    safe=name.lower().replace(' ','_');files={k:TEXTURES/(safe+'_'+k+'.png') for k in ['basecolor','roughness','normal']}
    if not all(p.exists() for p in files.values()):
        rng=np.random.default_rng(731+sum(map(ord,name)));y,x=np.mgrid[:size,:size].astype(np.float32);u=x/size;v=y/size
        grain=rng.integers(-4,5,(size,size),dtype=np.int8).astype(np.float32)/255
        cloudy=(np.sin(u*21+np.sin(v*13))*np.sin(v*29+u*8))*.032
        if kind=='skin':
            pores=grain*.19
            tone=1+cloudy*.25+grain*.35
            rough_map=np.clip(rough+grain*.7+cloudy*.25,.2,.9)
            hx=(np.roll(grain,1,axis=1)-grain)*.55;hy=(np.roll(grain,1,axis=0)-grain)*.55
        elif kind=='cloth':
            weave=np.sin(u*math.tau*501)*np.sin(v*math.tau*499);tone=1+cloudy*.7+grain*.55+weave*.034
            rough_map=np.clip(rough+weave*.024+grain,.2,.98);hx=np.cos(u*math.tau*501)*.023;hy=np.sin(v*math.tau*499)*.023
        elif kind=='car':
            water=np.maximum(0,np.sin(u*137+v*19))**16*np.maximum(0,np.sin(v*131-u*7))**16
            chips=np.maximum(0,(np.sin(u*61+np.sin(v*41))*np.cos(v*59+u*7)-.72))**2
            tone=1+cloudy+grain*.5;rough_map=np.clip(rough+cloudy*2+chips*2-water*.16,.17,.91)
            hx=np.cos(u*math.tau*251)*.012+water*.023;hy=np.sin(v*math.tau*243)*.012
        else:
            scratches=np.maximum(0,np.sin(u*1003+v*15))**64*.014
            tone=1+cloudy*.35+grain*.22-scratches
            rough_map=np.clip(rough+cloudy*.9+grain*.4-scratches,.14,.88);hx=np.cos(u*719)*.012;hy=np.sin(v*731)*.009
        arr=np.ones((size,size,4),dtype=np.float32)
        for c in range(3):linear=np.clip(color[c]*tone,0,1);arr[:,:,c]=np.where(linear<=.0031308,linear*12.92,1.055*linear**(1/2.4)-.055)
        def save(k,data):
            im=bpy.data.images.new(safe+' '+k,width=size,height=size,alpha=True);im.pixels.foreach_set(data.reshape(-1));im.filepath_raw=str(files[k]);im.file_format='PNG';im.save();bpy.data.images.remove(im)
        save('basecolor',arr);arr[:,:,:3]=rough_map[:,:,None];save('roughness',arr)
        arr[:,:,0]=.5+hx;arr[:,:,1]=.5+hy;arr[:,:,2]=.998;save('normal',arr)
        del arr,x,y,u,v,grain,rough_map
    m=mat(name,color,rough,metal);nodes=m.node_tree.nodes;links=m.node_tree.links;p=nodes.get('Principled BSDF')
    for kind,path in files.items():
        tex=nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(path),check_existing=True)
        if kind!='basecolor':tex.image.colorspace_settings.name='Non-Color'
        if kind=='basecolor':links.new(tex.outputs['Color'],p.inputs['Base Color'])
        elif kind=='roughness':links.new(tex.outputs['Color'],p.inputs['Roughness'])
        else:
            normal=nodes.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=.24;links.new(tex.outputs['Color'],normal.inputs['Color']);links.new(normal.outputs['Normal'],p.inputs['Normal'])
    return m

def screw(name,pos,m,parent=None,axis='Z',radius=.0045):
    # Actual torx recess is formed by a raised six-lobed annular head with an open central socket.
    profile=[(0,radius*.75),(.001,radius),(.0023,radius),(.0028,radius*.85),(.0028,radius*.36),(.0017,radius*.30)]
    return turned(name,profile,m,parent,axis,pos,sides=48 if HI else 20,steps=3 if HI else 1)

def skin_bind(name,palm,finger_data,nails,bones,root):
    # Volume-fuse the metacarpal / thumb / finger bases, then recreate smooth skin weights.
    union=join(name+'SkinnedHand',[palm]+[f[0] for f in finger_data],root)
    bpy.context.view_layer.objects.active=union
    remesh=union.modifiers.new('Continuous anatomical volume','REMESH');remesh.mode='VOXEL';remesh.voxel_size=.00058 if HI else .00088;remesh.use_smooth_shade=True
    bpy.ops.object.modifier_apply(modifier=remesh.name)
    smooth=union.modifiers.new('Skin transition relaxation','SMOOTH');smooth.factor=.62;smooth.iterations=5
    bpy.ops.object.modifier_apply(modifier=smooth.name)
    if not HI:
        count=sum(len(p.vertices)-2 for p in union.data.polygons)
        if count>70000:
            lod=union.modifiers.new('Runtime anatomical topology budget','DECIMATE');lod.ratio=70000/count
            bpy.ops.object.modifier_apply(modifier=lod.name)
    uv_assign(union)
    data=bpy.data.armatures.new(name+'Skeleton');rig=bpy.data.objects.new(name+'Skeleton',data);bpy.context.collection.objects.link(rig);rig.parent=root
    bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
    for bn,a,b,pn in bones:
        bone=data.edit_bones.new(bn);bone.head=a;bone.tail=b
        if pn:bone.parent=data.edit_bones[pn]
    bpy.ops.object.mode_set(mode='OBJECT');rig.select_set(False)
    coordinates=np.empty(len(union.data.vertices)*3,dtype=np.float32);union.data.vertices.foreach_get('co',coordinates);coordinates=coordinates.reshape(-1,3)
    distance=np.empty((len(coordinates),len(bones)),dtype=np.float32)
    for j,(_,a,b,_) in enumerate(bones):
        a=np.asarray(a,dtype=np.float32);d=np.asarray(b,dtype=np.float32)-a
        t=np.clip(((coordinates-a)*d).sum(axis=1)/max(float((d*d).sum()),1e-9),0,1)
        distance[:,j]=np.sqrt(((coordinates-(a+t[:,None]*d))**2).sum(axis=1))
    closest=np.argpartition(distance,2,axis=1)[:,:2]
    ds=np.take_along_axis(distance,closest,axis=1);weights=np.clip(ds[:,::-1]/np.maximum(ds.sum(axis=1)[:,None],1e-8),.03,.97)
    weights=np.round(weights*32)/32
    for j,(bn,_,_,_) in enumerate(bones):
        group=union.vertex_groups.new(name=bn)
        for slot in range(2):
            mask=closest[:,slot]==j
            for quant in np.unique(weights[mask,slot]):
                ids=np.where(mask & (weights[:,slot]==quant))[0]
                if len(ids):group.add(ids.tolist(),float(quant),'REPLACE')
    mod=union.modifiers.new('Anatomical articulated grip','ARMATURE');mod.object=rig
    nailobjects=[]
    for obj,group_specs in nails:
        groups={}
        for index,bn,weight in group_specs:
            if bn not in groups:groups[bn]=obj.vertex_groups.new(name=bn)
            groups[bn].add([index],weight,'REPLACE')
        mod=obj.modifiers.new('Distal nail attachment','ARMATURE');mod.object=rig;nailobjects.append(obj)
    join(name+'ThinNailPlates',nailobjects,root)
    return rig

def anatomical_hand(name,side,skin,cloth,root):
    s=side;hand=empty(name,root);n=128 if HI else 64;rings=78 if HI else 42
    profile=[(-.329,.029,.024),(-.301,.039,.027),(-.263,.050,.032),(-.224,.059,.035),(-.192,.058,.030),(-.177,.048,.025),(-.164,.007,.007)]
    verts=[];faces=[];uv=[]
    for k in range(rings):
        t=k/(rings-1);z=profile[0][0]+t*(profile[-1][0]-profile[0][0]);q=0
        while q<len(profile)-2 and z>profile[q+1][0]:q+=1
        f=(z-profile[q][0])/(profile[q+1][0]-profile[q][0]);rx=profile[q][1]*(1-f)+profile[q+1][1]*f;ry=profile[q][2]*(1-f)+profile[q+1][2]*f
        for j in range(n):
            a=math.tau*j/n;back=max(0,-math.sin(a))
            x=s*.047+rx*math.cos(a)*(1-.11*math.sin(a))
            tendon=.0023*sum(math.exp(-((x-s*tx)/.010)**2) for tx in [.020,.047,.074])*math.exp(-((z+.220)/.065)**2)*back
            y=-.035+(ry+tendon)*math.sin(a)+.004*math.sin(t*math.pi)
            verts.append((x,y,z));uv.append((j/n,t))
    for k in range(rings-1):
        for j in range(n):faces.append((k*n+j,(k+1)*n+j,(k+1)*n+(j+1)%n,k*n+(j+1)%n))
    faces.extend([tuple(reversed(range(n))),tuple((rings-1)*n+j for j in range(n))]);palm=shaped_mesh(name+'AnatomicalPalm',verts,faces,skin,hand,uv)
    bones=[('wrist',(s*.047,-.035,-.325),(s*.047,-.035,-.266),None),('palm',(s*.047,-.035,-.266),(s*.047,-.035,-.167),'wrist')]
    fingers=[];nails=[];pieces=[palm]
    nailmat=mat('Natural translucent nail',(.48,.31,.22),.42)
    names=['Index','Middle','Ring','Little','Thumb']
    for f,fn in enumerate(names):
        z=-.174-f*.031
        if fn=='Thumb':pts=[(s*.058,-.041,-.235),(s*.074,-.061,-.193),(s*.040,-.078,-.157),(-s*.014,-.060,-.171)];rs=[.024,.020,.012,.0087]
        else:
            pts=[(s*.084,-.033,z),(s*.057,.000,z+.001),(s*.019,.003,z-.005),(-s*.036,-.021,z-.012)]
            rad=[.0115,.0120,.0114,.0098][f];rs=[rad*1.08,rad,rad*.87,rad*.64]
        obj=sweep(name+fn+'Phalanges',pts,rs,skin,hand,sides=96 if HI else 40,steps=35 if HI else 15,ellipse=.89,fold=.035)
        pieces.append(obj);prev='palm';specs=[]
        for j in range(3):bn=name+fn+str(j+1);bones.append((bn,pts[j],pts[j+1],prev));prev=bn
        fingers.append((obj,specs))
        tip=Vector(pts[-1]);tangent=(Vector(pts[-1])-Vector(pts[-2])).normalized();normal=Vector((0,-.35,.94)).normalized()
        across=tangent.cross(normal).normalized();rings_n=15 if HI else 7;around=96 if HI else 36
        center=tip+normal*rs[-1]*.70-tangent*.005;nv=[];nf=[];nuv=[]
        for rr in range(rings_n):
            r=(rr+1)/rings_n
            for k in range(around):
                a=k*math.tau/around
                pos=center+across*(.007*r*math.cos(a))+tangent*(.012*r*math.sin(a))+normal*(.0012*(1-r*r))
                nv.append(tuple(pos));nuv.append((.5+.5*r*math.cos(a),.5+.5*r*math.sin(a)))
        for rr in range(rings_n-1):
            for k in range(around):nf.append((rr*around+k,rr*around+(k+1)%around,(rr+1)*around+(k+1)%around,(rr+1)*around+k))
        nf.append(tuple(reversed(range(around))))
        nail=shaped_mesh(name+fn+'ThinNailPlate',nv,nf,nailmat,hand,nuv)
        nails.append((nail,[(i,prev,1.0) for i in range(len(nail.data.vertices))]))
    # Thenar volume bridges the thumb metacarpal into wrist and palm before the volume union.
    thenar=sweep(name+'ThenarMuscle',[(s*.042,-.043,-.282),(s*.064,-.048,-.244),(s*.076,-.052,-.202)],[.021,.032,.024],skin,hand,sides=96 if HI else 40,steps=32 if HI else 12,ellipse=.81)
    fingers.append((thenar,[]))
    rig=skin_bind(name,palm,fingers,nails,bones,hand)
    # Tailored cloth volume includes compressed wrist folds, seam piping and individual stitch loops.
    arm_side=1 if name=='RightGrip' else -1
    sleeve=sweep(name+'TailoredSleeve',[(s*.047,-.035,-.335),(arm_side*.06,-.19,-.395),(arm_side*.15,-.44,-.49),(arm_side*.23,-.68,-.57)],[.044,.064,.080,.089],cloth,hand,sides=128 if HI else 44,steps=55 if HI else 14,ellipse=.86,fold=.095)
    cuff=turned(name+'DoubleCuff',[(-.346,.047),(-.335,.048),(-.304,.044),(-.294,.042),(-.299,.029),(-.339,.028)],cloth,hand,'Z',(s*.047,-.035,0),sides=128 if HI else 44,steps=12 if HI else 3)
    textile=[sleeve,cuff]
    seamMat=mat('Rainwear seam thread',(.075,.095,.08),.82)
    for edge in [-1,1]:
        pts=[(s*.047+edge*.026,-.075,-.333),(arm_side*.06+edge*.039,-.235,-.395),(arm_side*.15+edge*.049,-.49,-.49),(arm_side*.23+edge*.06,-.73,-.57)]
        textile.append(sweep(name+'BoundSeam',pts,[.00125]*4,seamMat,hand,sides=12 if HI else 6,steps=40 if HI else 10))
        line=sample_path(pts,35 if HI else 15)
        for i in range(0,len(line),2):
            p=line[i];textile.append(sweep(name+'LockStitch',[p+Vector((-.0014,0,0)),p+Vector((0,-.0013,0)),p+Vector((.0014,0,0))],[.00048]*3,seamMat,hand,sides=6 if HI else 4,steps=2 if HI else 1))
    join(name+'SleeveTextile',textile,hand)
    return hand

def equipment():
    base.clear();root=empty('FieldEquipmentAsset');lamp=empty('LampAssembly',root)
    enamel=texture_material('Field graphite coated metal',(.062,.088,.076),'metal',metal=.45,rough=.42)
    metal=texture_material('Machined aluminium',(.35,.37,.34),'metal',metal=.85,rough=.30)
    rubber=texture_material('Grip vulcanised rubber',(.021,.028,.021),'cloth',size=2048,metal=.0,rough=.68)
    brass=mat('Optical retaining brass',(.34,.23,.08),.31,.82);ivory=mat('Thermal ceramic cells',(.46,.47,.39),.45,.0);black=mat('Nitrile seals',(.015,.019,.014),.79)
    lensmat=mat('Coated optical glass',(.025,.135,.17),.085,.08);p=lensmat.node_tree.nodes.get('Principled BSDF');p.inputs['Alpha'].default_value=.075
    lensmat.diffuse_color=(.025,.135,.17,.075);lensmat.surface_render_method='DITHERED';p.inputs['IOR'].default_value=1.46
    glow=mat('Optical emission core',(.09,.56,.39),.23,.14,emission=(.10,.52,.33));white=mat('Laser etched legend',(.61,.67,.55),.49)
    parts=[];rings=[];hardware=[]
    parts.append(turned('PrecisionOpticalBarrel',[(-.178,.073),(-.164,.081),(-.151,.087),(-.141,.087),(-.132,.098),(-.117,.104),(-.067,.104),(-.046,.111),(.08,.116),(.11,.123),(.188,.123),(.205,.117),(.211,.108),(.211,.100),(.15,.106),(.04,.102),(-.14,.075),(-.178,.068)],enamel,lamp,steps=14 if HI else 4))
    # A reflector and nested lens stack sit physically inside an open front aperture.
    parts.append(turned('ParabolicReflector',[(.106,.022),(.114,.046),(.126,.064),(.148,.081),(.17,.094),(.195,.103)],metal,lamp,caps=False))
    for i in range(3):
        y=.177+i*.015
        turned('OpticalLensLayer'+str(i),[(y,.098-i*.006),(y+.006,.096-i*.006),(y+.011,.075-i*.004),(y+.014,.032),(y+.0145,.001)],lensmat,lamp,steps=12 if HI else 4)
    turned('CoatedOpticalLens',[(.214,.106),(.222,.100),(.229,.078),(.233,.034),(.234,.001)],lensmat,lamp,steps=18 if HI else 5)
    turned('OpticalEmitter',[(.116,.025),(.119,.031),(.125,.027)],glow,lamp,sides=128 if HI else 48,steps=8 if HI else 2)
    for y,r in [(-.139,.091),(-.118,.105),(-.054,.112),(.09,.121),(.176,.124),(.207,.117)]:rings.append(seal('LensRetainingRing',(0,y,0),r,.0028,metal,lamp))
    for y,r in [(-.131,.099),(.197,.118)]:rings.append(seal('PressureSeal',(0,y,0),r,.0036,black,lamp))
    # Real helical external thread / grip knurl changes geometry, not only normal-map frequency.
    thread=[]
    for helix in range(2):
        pts=[]
        for k in range(420 if HI else 160):
            t=k/(419 if HI else 159);a=t*math.tau*7+helix*math.pi;pts.append((.1048*math.cos(a),-.123+t*.064,.1048*math.sin(a)))
        thread.append(sweep('MachinedHelicalThread',pts,[.0014]*len(pts),metal,lamp,sides=12 if HI else 6,steps=1))
    for i in range(72 if HI else 48):
        a=i*math.tau/(72 if HI else 48)
        pts=[(.125*math.cos(a),.116,.125*math.sin(a)),(.126*math.cos(a+.021),.172,.126*math.sin(a+.021))]
        thread.append(sweep('GripCollarKnurl',pts,[.0015,.0015],metal,lamp,sides=10 if HI else 6,steps=12 if HI else 4))
    join('MachinedThreadsAndKnurl',thread,lamp)
    storage=turned('ContourStorageShell',[(-.274,.078),(-.264,.083),(-.247,.088),(-.215,.092),(-.177,.091),(-.148,.077),(-.128,.065)],enamel,lamp,loc=(0,0,-.025),steps=14 if HI else 5)
    for v in storage.data.vertices:v.co.z=-.025+(v.co.z+.025)*.72
    parts.append(storage)
    parts.append(box('StorageServiceLid',(.009,.149,.110),(.093,-.178,-.022),metal,lamp,.009))
    for sx in [-1,1]:
        parts.append(sweep('OpticsImpactBridge',[(sx*.096,-.12,.040),(sx*.128,-.050,.084),(sx*.131,.075,.087),(sx*.111,.18,.049)],[.007,.008,.008,.007],metal,lamp,sides=48 if HI else 20,steps=20 if HI else 6))
    parts.append(box('GripShoulder',(.071,.077,.055),(0,-.035,-.118),enamel,lamp,.018))
    parts.append(turned('ErgonomicPistolGrip',[(-.317,.032),(-.301,.038),(-.279,.035),(-.252,.033),(-.222,.032),(-.195,.033),(-.170,.035),(-.145,.025)],rubber,lamp,'Z',(0,-.035,0),sides=160 if HI else 48,steps=12 if HI else 4))
    gripdetails=[]
    for ring in range(19):
        z=-.292+ring*.0073
        # Grip ribs and diamond crossing cuts create readable contact detail under the hand.
        gripdetails.append(seal('GripTractionRib',(0,-.035,z),.034,.0010,rubber,lamp,'Z',rings=96 if HI else 40,tube_sides=10 if HI else 5))
    join('GripTraction',gripdetails,lamp)
    parts.append(box('GripHeel',(.075,.086,.023),(0,-.035,-.320),enamel,lamp,.010))
    parts.append(sweep('ContinuousTriggerGuard',[(.040,-.009,-.125),(.045,.072,-.130),(.046,.093,-.211),(.041,.043,-.277),(.038,-.027,-.275)],[.0057]*5,metal,lamp,sides=48 if HI else 16,steps=22 if HI else 7))
    parts.append(box('InsetModeSwitch',(.025,.022,.007),(-.025,-.064,-.152),ivory,lamp,.004))
    parts.append(box('TriggerLever',(.008,.023,.037),(.036,.009,-.170),brass,lamp,.005))
    cells=[]
    for i,x in enumerate([-.053,0,.053]):
        cells.append(turned('ElectrochemicalCell'+str(i),[(-.237,.018),(-.228,.023),(-.196,.023),(-.161,.023),(-.148,.020)],ivory,lamp,'Y',(x,0,-.100),sides=160 if HI else 56,steps=14 if HI else 4))
        for y in [-.228,-.16]:cells.append(seal('CapacitorMetalFerrule',(x,y,-.100),.0232,.0018,metal,lamp))
        cells.append(box('CellChargeIndicator',(.007,.053,.004),(x,-.192,-.074),glow,lamp,.002))
        cells.append(sweep('CellBusContact',[(x,-.143,-.100),(x,-.123,-.083),(x,-.120,-.041)],[.003]*3,brass,lamp,sides=24 if HI else 12,steps=8 if HI else 3))
    join('StorageCellsAndBusBars',cells,lamp)
    for y in [-.230,-.13]:
        for z in [-.061,.022]:hardware.append(screw('CaptiveTorxFastener',(.099,y,z),metal,lamp,'X',.0049))
    for x in [-.048,.048]:
        hardware.append(screw('RearPressureBolt',(x,-.278,.014),metal,lamp,'Y',.0052))
    join('SealedHousing',parts,lamp);join('PrecisionRetainingRings',rings,lamp);join('CaptiveFasteners',hardware,lamp)
    label('DeviceIdentification','SPECTRA 03',(0,-.2757,-.014),.0118,white,lamp,(math.pi/2,0,0))
    scale_plate=label('CalibratedScale','400  |  550  |  700 nm',(0,-.112,.1043),.0056,white,lamp)
    for vertex in scale_plate.data.vertices:vertex.co.z+=math.sqrt(max(.001,.104**2-vertex.co.x**2))-.104
    sensor=empty('SensorModules',lamp)
    sv=[]
    for zz in [0,1]:
        for xx,yy in [(.012,-.170),(.075,-.170),(.075,-.128),(.012,-.128)]:
            bottom=math.sqrt(max(.0001,.091**2-xx**2));sv.append((xx,yy,.105 if zz else bottom-.0006))
    shaped_mesh('ConformingSensorModule',sv,[(0,3,2,1),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)],enamel,sensor)
    box('SensorScreen',(.044,.023,.003),(.043,-.146,.108),glow,sensor,.003)
    for xx in [.020,.067]:screw('ModuleFastener',(xx,-.148,.1055),metal,sensor,'Z',.003)
    label('SerialStamp','RAINFIELD / OPTICS',(0,-.2757,-.039),.0056,white,lamp,(math.pi/2,0,0))
    cloth=texture_material('Tailored storm shell',(.041,.075,.065),'cloth',size=4096,metal=0,rough=.79)
    skin=texture_material('Anatomical warm skin',(.42,.25,.16),'skin',size=4096,metal=0,rough=.58)
    right=anatomical_hand('RightGrip',-1,skin,cloth,root)
    left=anatomical_hand('LeftSupport',-1,skin,cloth,root);left.location=(-.067,.125,.073);left.rotation_euler.y=.13
    props=empty('SkillTools',root)
    reagent=empty('ToolLuminol',props);reagent.location=(-.25,.03,-.22)
    turned('LaboratoryGlassBottle',[(0,.027),(.009,.029),(.065,.029),(.090,.026),(.110,.017),(.139,.017)],lensmat,reagent,'Z',sides=128 if HI else 40,steps=10 if HI else 3)
    turned('ReagentDropper',[(.13,.020),(.144,.020),(.154,.017),(.167,.008)],rubber,reagent,'Z',sides=128 if HI else 40,steps=8 if HI else 3)
    for z in [.136,.145,.151]:seal('DropperKnurl',(0,0,z),.020,.001,rubber,reagent,'Z')
    label('ReagentCalibration','LUM / 20 mL',(0,-.030,.064),.009,white,reagent,(math.pi/2,0,0))
    salt=empty('ToolSalt',props);salt.location=(-.25,.03,-.22)
    # A gusseted flexible pouch, curled corners and compressed seal, not an opaque box.
    pouch=sweep('FlexibleSaltPouch',[(0,0,.00),(0,0,.022),(0,.002,.072),(0,0,.121)],[.022,.038,.039,.026],ivory,salt,sides=96 if HI else 32,steps=22 if HI else 8,ellipse=.51,fold=.075)
    box('HeatSealedPouchRim',(.064,.020,.008),(0,0,.124),metal,salt,.002)
    label('SaltFormula','NaCl',(0,-.023,.095),.014,brass,salt,(math.pi/2,0,0))
    mud=empty('ToolMud',props);mud.location=(-.25,.03,-.22)
    turned('MudSamplingCanister',[(0,.037),(.008,.042),(.105,.042),(.114,.04),(.12,.038)],enamel,mud,'Z',sides=128 if HI else 40,steps=12 if HI else 4)
    turned('SealedSampleLid',[(.115,.043),(.128,.044),(.137,.041)],metal,mud,'Z',sides=128 if HI else 40,steps=12 if HI else 4)
    seal('SampleLidGasket',(0,0,.119),.0425,.0018,black,mud,'Z')
    label('SampleScientificMark','SiO2 / FIELD',(0,-.043,.070),.009,white,mud,(math.pi/2,0,0))
    root['quality_status']='High-resolution candidate: requires native-rendered human acceptance'
    return root

def tris():return sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in bpy.context.scene.objects if o.type=='MESH')

def save_master(name):
    for o in bpy.context.scene.objects:
        if o.type=='MESH':uv_assign(o)
    bpy.ops.file.pack_all()
    path=SOURCE/(name+'.blend');bpy.ops.wm.save_as_mainfile(filepath=str(path),compress=True)
    n=tris();COUNTS[name]={'source_triangles':n,'source':str(path.relative_to(ROOT))};print('HIGH_MASTER_SAVED',name,n,flush=True)

def save_runtime(name,suffix='',rest_position_armature=True):
    for o in bpy.context.scene.objects:
        if o.type=='MESH':uv_assign(o)
    n=tris();path=OUT/(name+suffix+'.glb')
    bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',export_yup=True,export_apply=True,export_animations=False,export_extras=True,export_cameras=False,export_lights=False,export_rest_position_armature=rest_position_armature)
    COUNTS.setdefault(name,{})['runtime'+suffix+'_triangles']=n
    print('HIGH_RUNTIME_EXPORTED',name+suffix,n,flush=True)
    if not suffix and name in ['field_equipment','abandoned_car']:
        for level,ratio in [(1,.43),(2,.40)]:
            pose_states=[]
            if not rest_position_armature:
                for obj in bpy.context.scene.objects:
                    if obj.type=='ARMATURE':
                        pose_states.append((obj.data,obj.data.pose_position))
                        obj.data.pose_position='REST'
                bpy.context.view_layer.update()
            try:
                for obj in bpy.context.scene.objects:
                    if obj.type=='MESH' and len(obj.data.polygons)>300:
                        bpy.context.view_layer.objects.active=obj
                        dec=obj.modifiers.new('Native runtime LOD '+str(level),'DECIMATE');dec.ratio=ratio
                        bpy.ops.object.modifier_apply(modifier=dec.name)
            finally:
                for data,position in pose_states:data.pose_position=position
                if pose_states:bpy.context.view_layer.update()
            lod_tri=tris();lodpath=OUT/(name+'_lod'+str(level)+'.glb')
            bpy.ops.export_scene.gltf(filepath=str(lodpath),export_format='GLB',export_yup=True,export_apply=True,export_animations=False,export_extras=True,export_cameras=False,export_lights=False,export_rest_position_armature=rest_position_armature)
            COUNTS[name]['runtime_lod'+str(level)+'_triangles']=lod_tri
            print('HIGH_RUNTIME_LOD_EXPORTED',name,level,lod_tri,flush=True)

def car_surface(name,points_u,points_v,func,m,parent):
    verts=[];faces=[];uv=[]
    for i in range(points_u):
        u=i/(points_u-1)
        for j in range(points_v):
            v=j/(points_v-1);verts.append(func(u,v));uv.append((u,v))
    for i in range(points_u-1):
        for j in range(points_v-1):
            a=i*points_v+j;faces.append((a,a+1,a+points_v+1,a+points_v))
    # Exterior normals must follow the actual manufactured face, not a generic UV order.
    flip=name in ['StampedHood','RearDeckPanel','CrownedRoofPanel','FrontWindshield']
    if name in ['OuterDoorPanel','SideWindow'] and verts[0][0]>0:flip=True
    if flip:faces=[tuple(reversed(f)) for f in faces]
    obj=shaped_mesh(name,verts,faces,m,parent,uv)
    if name in ['StampedHood','RearDeckPanel','CrownedRoofPanel','OuterDoorPanel']:
        shell=obj.modifiers.new('Actual sheet-metal thickness','SOLIDIFY');shell.thickness=.0022;shell.offset=-1
        bpy.context.view_layer.objects.active=obj;bpy.ops.object.modifier_apply(modifier=shell.name)
    return obj

def rounded_seat(name,center,dims,m,parent):
    nu=192 if HI else 48;nv=128 if HI else 28;verts=[];faces=[];uv=[]
    for i in range(1,nv):
        t=math.pi*i/nv
        for j in range(nu):
            a=math.tau*j/nu
            def power(x,p):return math.copysign(abs(x)**p,x)
            xx=power(math.sin(t)*math.cos(a),.52)*dims[0]*.5
            yy=power(math.sin(t)*math.sin(a),.55)*dims[1]*.5
            zz=power(math.cos(t),.53)*dims[2]*.5
            # Pressure depression and stitched upholstery channeling change actual cushion form.
            zz-=.007*max(0,math.cos(t))*math.exp(-(xx/(dims[0]*.36))**2-(yy/(dims[1]*.38))**2)
            verts.append((center[0]+xx,center[1]+yy,center[2]+zz));uv.append((j/nu,i/nv))
    for i in range(nv-2):
        for j in range(nu):faces.append((i*nu+j,i*nu+(j+1)%nu,(i+1)*nu+(j+1)%nu,(i+1)*nu+j))
    faces.extend([tuple(reversed(range(nu))),tuple((nv-2)*nu+j for j in range(nu))])
    obj=shaped_mesh(name,verts,faces,m,parent,uv)
    for vertex in obj.data.vertices:vertex.co-=Vector(center)
    obj.location=center
    return obj

def detailed_car():
    from mathutils import Matrix
    base.clear();root=empty('RefinedCar')
    paint=texture_material('Aged olive automotive lacquer',(.13,.16,.10),'car',metal=.38,rough=.39)
    steel=texture_material('Oxidised automotive steel',(.23,.245,.22),'metal',metal=.78,rough=.36)
    tyre=texture_material('Weathered tyre compound',(.019,.022,.018),'cloth',size=4096,metal=0,rough=.73)
    trim=mat('Weatherstripping black rubber',(.016,.020,.016),.78);rust=texture_material('Exposed chassis corrosion',(.19,.078,.025),'car',metal=.15,rough=.79)
    upholstery=texture_material('Worn textile upholstery',(.071,.054,.034),'cloth',size=4096,metal=0,rough=.86)
    glass=mat('Thin automotive safety glazing',(.025,.040,.035),.095,.08);p=glass.node_tree.nodes.get('Principled BSDF');p.inputs['Alpha'].default_value=.22;glass.diffuse_color=(.025,.040,.035,.22);glass.surface_render_method='DITHERED'
    headglass=mat('Ribbed headlamp glass',(.45,.43,.33),.13,.04);dark=mat('Dashboard vinyl',(.032,.030,.022),.66);white=mat('Faded instrument lettering',(.49,.50,.39),.65)
    profile=[(-2.08,.97,.76,.22),(-1.88,1.035,.79,.255),(-1.45,1.04,.80,.26),(-.88,1.04,.82,.27),(-.32,1.06,.83,.265),(.55,1.06,.83,.265),(1.15,1.025,.79,.25),(1.74,1.02,.755,.235),(2.08,.93,.71,.20)]
    lengthsteps=240 if HI else 112;around=224 if HI else 96;verts=[];faces=[];uv=[]
    for i in range(lengthsteps):
        y=-2.08+4.16*i/(lengthsteps-1);k=0
        while k<len(profile)-2 and y>profile[k+1][0]:k+=1
        t=(y-profile[k][0])/(profile[k+1][0]-profile[k][0]);w=profile[k][1]*(1-t)+profile[k+1][1]*t;mid=profile[k][2]*(1-t)+profile[k+1][2]*t;h=profile[k][3]*(1-t)+profile[k+1][3]*t
        for j in range(around):
            a=math.tau*j/around;xx=w*math.copysign(abs(math.cos(a))**.59,math.cos(a));zz=mid+h*math.copysign(abs(math.sin(a))**.52,math.sin(a))
            bulge=.055*(math.exp(-((y+1.35)/.37)**2)+math.exp(-((y-1.35)/.38)**2))*abs(math.cos(a))**8
            xx+=math.copysign(bulge,xx)
            dent=.036*math.exp(-((y+1.65)/.27)**2-((zz-.89)/.12)**2)*(1 if xx<0 else 0)
            xx+=dent;zz-=.021*math.exp(-((y+1.83)/.26)**2)*max(0,-math.cos(a))**3
            verts.append((xx,y,zz));uv.append((j/around,i/(lengthsteps-1)))
    for i in range(lengthsteps-1):
        for j in range(around):faces.append((i*around+j,i*around+(j+1)%around,(i+1)*around+(j+1)%around,(i+1)*around+j))
    faces.extend([tuple(reversed(range(around))),tuple((lengthsteps-1)*around+j for j in range(around))])
    body=shaped_mesh('Body',verts,faces,paint,root,uv)
    for y in [-1.35,1.36]:
        bpy.ops.mesh.primitive_cylinder_add(vertices=128 if HI else 64,radius=.485,depth=2.8,location=(0,y,.43),rotation=(0,math.pi/2,0));cutter=bpy.context.object
        mod=body.modifiers.new('Open formed wheel arch','BOOLEAN');mod.object=cutter;mod.operation='DIFFERENCE';bpy.context.view_layer.objects.active=body;bpy.ops.object.modifier_apply(modifier=mod.name);bpy.data.objects.remove(cutter,do_unlink=True)
    # Rolled front / rear panel skins and hood crown, with a deformed damaged corner.
    car_surface('StampedHood',96 if HI else 40,112 if HI else 48,lambda u,v:((-1+2*u)*.96,-1.98+1.08*v,1.054+.028*(1-(2*u-1)**2)+.018*v+.048*math.exp(-((u-.10)/.18)**2-((v-.16)/.23)**2)),paint,root)
    car_surface('RearDeckPanel',96 if HI else 36,96 if HI else 36,lambda u,v:((-1+2*u)*.92,1.03+1.00*v,.974+.038*(1-(2*u-1)**2)-.095*v),paint,root)
    car_surface('CrownedRoofPanel',128 if HI else 48,160 if HI else 52,lambda u,v:((-1+2*u)*.79,-.55+1.25*v,1.668+.046*(1-(2*u-1)**2)+.016*math.sin(v*math.pi)),paint,root)
    pillars=[];seals=[];seams=[]
    for side in [-1,1]:
        for pts in [[(side*.94,-.89,1.07),(side*.89,-.77,1.33),(side*.79,-.55,1.668)],[(side*.94,.99,1.07),(side*.88,.87,1.36),(side*.79,.70,1.668)],[(side*1.01,.04,1.07),(side*.9,.035,1.36),(side*.8,.03,1.681)]]:
            pillars.append(sweep('FormedWindowPillar',pts,[.045,.041,.036],paint,root,sides=64 if HI else 28,steps=24 if HI else 8,ellipse=.36))
        for start,end in [(-.82,.00),(.07,.91)]:
            width=end-start
            def door_point(u,v,sgn=side,a=start,b=end):
                y=a+(b-a)*u;z=.665+.398*v;x=sgn*(1.064+.012*math.sin(u*math.pi)*math.sin(v*math.pi)-.010*(1-v))
                x+=(-sgn)*.026*math.exp(-((u-.7)/.23)**2-((v-.20)/.13)**2)
                return (x,y,z)
            car_surface('OuterDoorPanel',88 if HI else 34,80 if HI else 26,door_point,paint,root)
            outline=[(side*1.059,start,.68),(side*1.077,start,1.052),(side*1.075,end,1.052),(side*1.052,end,.68),(side*1.059,start,.68)]
            seams.append(sweep('DoorPanelGap',outline,[.0036]*len(outline),trim,root,sides=12 if HI else 6,steps=16 if HI else 5))
            handle=box('RecessedDoorHandle',(.024,.178,.038),(side*1.083,end-.16,.981),steel,root,.010)
            # Inner door cards and arm rests provide real structure behind the glazing.
            rounded_seat('DoorInnerCard',(side*.935,(start+end)/2,.93),(.063,width*.87,.36),upholstery,root)
            rounded_seat('DoorArmrest',(side*.892,(start+end)/2,.94),(.090,width*.72,.073),dark,root)
        for y0,y1 in [(-.82,.01),(.06,.93)]:
            def side_glass(u,v,sgn=side,aa=y0,bb=y1):
                z=1.112+.515*v;x=sgn*(.966-.161*v);y=aa+(bb-aa)*u
                if aa<0:y+=.23*v*(1-u)
                else:y-=.21*v*u
                return (x,y,z)
            pane=car_surface('SideWindow',96 if HI else 30,80 if HI else 26,side_glass,glass,root)
            edge=[side_glass(0,0),side_glass(1,0),side_glass(1,1),side_glass(0,1),side_glass(0,0)]
            seals.append(sweep('WindowWeatherSeal',edge,[.008]*len(edge),trim,root,sides=24 if HI else 10,steps=18 if HI else 5))
    join('CabinPillarFrames',pillars,root);join('GlazingWeatherSeals',seals,root);join('DoorSeamLines',seams,root)
    def front_glass(u,v):return ((2*u-1)*(.885-.13*v),-.922+.337*v,1.100+.535*v+.018*(1-(2*u-1)**2))
    car_surface('FrontWindshield',128 if HI else 44,100 if HI else 36,front_glass,glass,root)
    car_surface('RearWindshield',128 if HI else 44,96 if HI else 32,lambda u,v:((2*u-1)*(.89-.13*v),1.019-.284*v,1.098+.53*v+.012*(1-(2*u-1)**2)),glass,root)
    cracks=[]
    center=Vector(front_glass(.27,.44))+Vector((0,-.008,0))
    for u,v in [(.05,.11),(.13,.84),(.35,.91),(.62,.7),(.60,.19),(.3,.02)]:
        target=Vector(front_glass(u,v))+Vector((0,-.008,0));cracks.append(sweep('SafetyGlazingFracture',[center,center.lerp(target,.43)+Vector((.012,0,.003)),target],[.0019,.0014,.0003],white,root,sides=8 if HI else 4,steps=12 if HI else 4))
    join('CrackedWindshield',cracks,root)
    wipers=[]
    for offset in [-.39,.39]:
        wipers.append(sweep('WiperDriveArm',[(offset,-.953,1.116),(offset-.09,-.84,1.31),(offset-.18,-.712,1.48)],[.0048,.0045,.0036],steel,root,sides=20 if HI else 8,steps=12 if HI else 4))
        wipers.append(sweep('PressureWiperBlade',[(offset-.32,-.744,1.43),(offset-.19,-.688,1.52),(offset+.01,-.626,1.58)],[.009,.009,.006],trim,root,sides=24 if HI else 10,steps=16 if HI else 5))
    join('WindshieldWipers',wipers,root)
    # Complete interior uses actual cushion, backrest, headrest, belt, dash and driving controls.
    interior=[];stitches=[]
    for row,y in enumerate([-.09,.64]):
        for side in [-1,1]:
            x=side*.46
            interior.append(rounded_seat('SeatCushion',(x,y,.814),(.63,.64,.17),upholstery,root))
            back=rounded_seat('ContouredSeatBack',(x,y+.27,1.133),(.61,.155,.60),upholstery,root);back.rotation_euler.x=-.08;interior.append(back)
            interior.append(rounded_seat('PaddedHeadrest',(x,y+.315,1.48),(.30,.13,.18),upholstery,root))
            for seamx in [-.22,.22]:
                stitches.append(sweep('UpholsteryPiping',[(x+seamx,y-.24,.87),(x+seamx,y+.24,.875),(x+seamx,y+.20,1.35)],[.0028]*3,rust,root,sides=12 if HI else 6,steps=32 if HI else 8))
            interior.append(sweep('SeatBeltWebbing',[(x+side*.24,y+.34,1.45),(x,y+.30,1.15),(x-side*.19,y+.15,.86)],[.013,.013,.010],trim,root,sides=24 if HI else 8,steps=24 if HI else 8,ellipse=.16))
    join('CompleteSeatsAndBelts',interior,root);join('UpholsterySeams',stitches,root)
    dash=rounded_seat('CurvedDashboard',(0,-.663,1.18),(1.76,.30,.19),dark,root)
    gauges=[]
    for x in [-.58,-.40,-.22]:
        gauges.append(turned('GaugeBezel',[(0,.065),(.009,.068),(.016,.060)],steel,root,'Y',(x,-.496,1.20),sides=128 if HI else 48,steps=8 if HI else 2))
        gauges.append(turned('GaugeFace',[(.016,.057),(.0165,.057)],trim,root,'Y',(x,-.496,1.20),sides=128 if HI else 48,steps=4 if HI else 1))
        for k in range(16):
            a=k*math.tau/16;gauges.append(beam('GaugeCalibration',(x+.044*math.cos(a),-.477,1.20+.044*math.sin(a)),(x+.052*math.cos(a),-.477,1.20+.052*math.sin(a)),.0016,white,root))
        gauges.append(beam('GaugeNeedle',(x,-.474,1.2),(x+.030,-.474,1.229),.002,white,root))
    join('AnalogInstrumentCluster',gauges,root)
    vents=[]
    for x in [.29,.66]:
        box('DashboardVentFrame',(.29,.032,.075),(x,-.493,1.2),steel,root,.008)
        for j in range(9):vents.append(box('VentLouvre',(.021,.029,.060),(x-.106+j*.026,-.469,1.20),trim,root,.004))
    join('VentLouvres',vents,root)
    center=Vector((-.43,-.352,1.195));normal=Vector((0,.87,.49)).normalized();ring=seal('SteeringRim',(0,0,0),.179,.016,trim,root,'Z',rings=256 if HI else 96,tube_sides=32 if HI else 12);ring.location=center;ring.rotation_euler=normal.to_track_quat('Z','Y').to_euler()
    basis_x=Vector((1,0,0));basis_y=normal.cross(basis_x);steering=[]
    steering.append(sweep('SteeringColumn',[(-.43,-.72,.91),(-.43,-.54,1.09),tuple(center)],[.033,.026,.024],steel,root,sides=48 if HI else 20,steps=18 if HI else 5))
    for a in [0,2.25,4.03]:steering.append(sweep('SteeringSpoke',[tuple(center),tuple(center+(basis_x*math.cos(a)+basis_y*math.sin(a))*.16)],[.016,.011],steel,root,sides=32 if HI else 12,steps=14 if HI else 4))
    join('SteeringControls',steering,root)
    rounded_seat('TransmissionTunnel',(0,.11,.82),(.25,1.35,.19),trim,root)
    sweep('GearLever',[(0,-.08,.84),(0,-.11,1.00),(-.012,-.10,1.085)],[.012,.010,.007],steel,root,sides=40 if HI else 16,steps=20 if HI else 6)
    uv_sphere('GearKnob',(-.012,-.10,1.08),(.027,.027,.024),trim,root,64 if HI else 24,40 if HI else 12)
    # Four tyres with true sculpted tread blocks, sidewalls, deep split-spoke rims and brake rotors.
    for side in [-1,1]:
        for yy in [-1.35,1.36]:
            turned('Wheel',[(side*1.025,.25),(side*1.025,.34),(side*1.065,.414),(side*1.10,.435),(side*1.19,.435),(side*1.237,.40),(side*1.247,.30),(side*1.239,.255)],tyre,root,'X',(0,yy,.43),sides=256 if HI else 96,steps=12 if HI else 4)
            tread=[];blocks=100 if HI else 72;rows=6 if HI else 5
            for row in range(rows):
                x=side*(1.075+.14*(row/(rows-1)))
                for j in range(blocks):
                    a=(j+(row%2)*.5)*math.tau/blocks;rad=.436-abs(row/(rows-1)-.5)*.024
                    o=box('ChevronTreadBlock',(.023 if HI else .026,.024 if HI else .033,.014),(x,yy+rad*math.cos(a),.43+rad*math.sin(a)),tyre,root,.0043)
                    normal_v=Vector((0,math.cos(a),math.sin(a)));tangent=Vector((0,math.sin(a),-math.cos(a)));axle=Vector((1,0,0))
                    o.rotation_euler=Matrix((axle,tangent,normal_v)).transposed().to_euler();tread.append(o)
            join('GeometricTyreTread',tread,root)
            rings=[]
            for r in [.316,.359,.383]:rings.append(seal('MouldedSidewallRing',(side*1.251,yy,.43),r,.0025,tyre,root,'X'))
            join('MouldedTyreSidewalls',rings,root)
            turned('DeepRimBarrel',[(side*1.210,.235),(side*1.25,.246),(side*1.268,.257),(side*1.277,.251),(side*1.278,.229),(side*1.253,.218)],steel,root,'X',(0,yy,.43),sides=192 if HI else 72,steps=12 if HI else 4,caps=False)
            rimparts=[]
            for j in range(5):
                a=j*math.tau/5
                for split in [-1,1]:
                    da=split*.09;pts=[(side*1.277,yy+.070*math.cos(a),.43+.070*math.sin(a)),(side*1.263,yy+.14*math.cos(a+da),.43+.14*math.sin(a+da)),(side*1.272,yy+.229*math.cos(a+da),.43+.229*math.sin(a+da))]
                    rimparts.append(sweep('SplitRimSpoke',pts,[.014,.016,.009],steel,root,sides=32 if HI else 12,steps=20 if HI else 6,ellipse=.62))
                rimparts.append(screw('LugNut',(side*1.290,yy+.061*math.cos(a),.43+.061*math.sin(a)),steel,root,'X',.009))
            join('SplitSpokeRimAndLugs',rimparts,root)
            turned('HubCap',[(side*1.28,.043),(side*1.294,.044),(side*1.300,.033)],steel,root,'X',(0,yy,.43),sides=128 if HI else 48,steps=10 if HI else 3)
            rotor=turned('BrakeDisc',[(side*1.215,.195),(side*1.225,.195)],steel,root,'X',(0,yy,.43),sides=128 if HI else 64,steps=2)
            rounded_seat('BrakeCaliper',(side*1.229,yy+.148,.43),(.071,.10,.14),rust,root)
            # Formed fender lip is a continuous curve around the real body opening.
            pts=[(side*1.096,yy+.492*math.cos(j*math.pi/32),.43+.492*math.sin(j*math.pi/32)) for j in range(33)]
            sweep('RolledArchLip',pts,[.0105]*len(pts),paint,root,sides=24 if HI else 10,steps=2 if HI else 1)
    # Bumpers have formed corners, real bracket mounts, glass optics and reflective housings.
    lights=[];bumps=[]
    for end in [-1,1]:
        y=end*2.108
        bumps.append(sweep('FormedBumper',[(-1.065,y-.025*end,.570),(-.91,y+.035*end,.576),(0,y+.051*end,.577),(.91,y+.035*end,.576),(1.065,y-.025*end,.57)],[.058,.065,.067,.065,.058],steel,root,sides=64 if HI else 24,steps=24 if HI else 8,ellipse=.73))
        for x in [-.77,.77]:
            if end<0:
                housing=turned('HeadlampReflector',[(0,.105),(.042,.103),(.074,.028)],steel,root,'Y',(x,y,.82),sides=128 if HI else 48,steps=12 if HI else 4,caps=False)
                # Headlamp cover is ribbed moulded glass with an actual optical perimeter.
                lights.append(turned('HeadlampLens',[(.001,.105),(-.009,.103),(-.013,.085),(-.014,.005)],headglass,root,'Y',(x,y,.82),sides=160 if HI else 56,steps=12 if HI else 4))
                for j in range(13):
                    xx=x+(j-6)*.013;dz=math.sqrt(max(.001,.094**2-(xx-x)**2));lights.append(sweep('MouldedLampPrism',[(xx,y-.016,.82-dz),(xx,y-.019,.82),(xx,y-.016,.82+dz)],[.0016]*3,headglass,root,sides=10 if HI else 6,steps=12 if HI else 4))
            else:lights.append(rounded_seat('RearLampAssembly',(x,y,.793),(.33,.034,.19),mat('Clouded rear-lamp polymer',(.21,.042,.021),.22),root))
        for x in [-.65,.65]:bumps.append(beam('BumperMount',(x,y,.53),(x,y-end*.17,.56),.032,rust,root))
    join('FormedBumpersAndMounts',bumps,root);join('RibbedLightingAssemblies',lights,root)
    grille=[]
    for j in range(19):grille.append(box('RadiatorSlat',(.022,.018,.17),(-.47+j*.052,-2.105,.78),steel,root,.005))
    join('RadiatorGrille',grille,root)
    # Underbody and running gear are visible from low nearby viewpoints.
    chassis=[]
    for x in [-.65,.65]:chassis.append(beam('ChassisRail',(x,-1.75,.47),(x,1.75,.47),.10,rust,root))
    for y in [-1.35,1.36]:chassis.append(sweep('AxleAndSuspension',[(-1.03,y,.43),(-.6,y,.43),(0,y,.42),(.6,y,.43),(1.03,y,.43)],[.044,.035,.034,.035,.044],steel,root,sides=48 if HI else 16,steps=16 if HI else 5))
    chassis.append(sweep('ExhaustPipe',[(.22,-1.42,.40),(.20,-.32,.395),(.36,.80,.40),(.72,1.74,.44),(.73,2.18,.43)],[.027]*5,steel,root,sides=48 if HI else 16,steps=28 if HI else 8))
    chassis.append(turned('ExhaustMuffler',[(-.24,.09),(.32,.09)],rust,root,'Y',(.30,.43,.395),sides=96 if HI else 32,steps=16 if HI else 4))
    join('CompleteRunningGear',chassis,root)
    floor=box('InteriorFloorPan',(1.88,3.20,.07),(0,.05,.67),dark,root,.04)
    root['quality_status']='High-resolution candidate: neutral and rain-night views require acceptance'
    return root

if ASSET in ['equipment','all']:
    HI=True;equipment();save_master('field_equipment');HI=False;equipment();save_runtime('field_equipment')
if ASSET in ['car','all']:
    HI=True;detailed_car();save_master('abandoned_car');HI=False;detailed_car();save_runtime('abandoned_car')
(Path(SOURCE/'COMMERCIAL_MODEL_MANIFEST.json')).write_text(json.dumps({'quality_status':'candidate pending visual acceptance','tool':'Blender 4.5 LTS','original_maps':True,'assets':COUNTS},indent=2)+'\n')
