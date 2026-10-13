"""Deterministic authoring of the rain-forest field assets in Blender 4.5 LTS.
Run: blender --background --python tools/build_field_assets.py -- --output-root /path/to/repo
The .blend master retains separate named parts, hand skeletons, UVs and materials.
GLBs are native Godot imports, without generated collision. No external downloads.
"""
import bpy, bmesh, math, os, sys, json, random
from mathutils import Vector
from pathlib import Path

args = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
ROOT = Path(args[args.index('--output-root')+1]) if '--output-root' in args else Path(__file__).resolve().parents[1]
OUT = ROOT/'assets'/'refined'; SOURCE = ROOT/'source_assets'; OUT.mkdir(parents=True, exist_ok=True); SOURCE.mkdir(exist_ok=True)
(SOURCE/'.gdignore').write_text('')
RNG = random.Random(731)
STATS = {}

def clear():
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    for pool in (bpy.data.meshes, bpy.data.curves, bpy.data.armatures, bpy.data.materials):
        for data in list(pool):
            if data.users == 0: pool.remove(data)

def mat(name, rgb, rough=.45, metal=0, emission=None):
    m=bpy.data.materials.new(name); m.diffuse_color=(*rgb,1); m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF'); p.inputs['Base Color'].default_value=(*rgb,1);p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal
    if emission:
        p.inputs['Emission Color'].default_value=(*emission,1);p.inputs['Emission Strength'].default_value=.45
    return m

def skin_mat():
    m=mat('Warm skin - natural tonal variation',(.57,.36,.23),.57)
    p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Subsurface Weight'].default_value=.12
    return m

def parent_obj(obj,parent):
    if parent: obj.parent=parent
    return obj

def empty(name,parent=None,loc=(0,0,0)):
    obj=bpy.data.objects.new(name,None);bpy.context.collection.objects.link(obj);obj.location=loc;return parent_obj(obj,parent)

def finish_mesh(obj,m=None,bevel=0,smooth=True):
    bm=bmesh.new();bm.from_mesh(obj.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(obj.data);bm.free()
    if m: obj.data.materials.append(m)
    if bevel:
        mod=obj.modifiers.new('Manufactured corner radii','BEVEL');mod.width=bevel;mod.segments=3
        bpy.context.view_layer.objects.active=obj;bpy.ops.object.modifier_apply(modifier=mod.name)
    if smooth:
        for poly in obj.data.polygons:poly.use_smooth=True
    if bevel:
        normal=obj.modifiers.new('Weighted panel normals','WEIGHTED_NORMAL');normal.keep_sharp=True;normal.weight=40
        bpy.context.view_layer.objects.active=obj;bpy.ops.object.modifier_apply(modifier=normal.name)
    return obj

def mesh(name,verts,faces,m,parent=None,bevel=0,smooth=True):
    data=bpy.data.meshes.new(name+' geometry');data.from_pydata(verts,[],faces);data.update()
    obj=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(obj);parent_obj(obj,parent);return finish_mesh(obj,m,bevel,smooth)

def box(name,size,loc,m,parent=None,bevel=.015):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc);o=bpy.context.object;o.name=name;o.dimensions=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);parent_obj(o,parent);return finish_mesh(o,m,bevel)

def uv_sphere(name,loc,scale,m,parent=None,segments=24,rings=12):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments,ring_count=rings,location=loc);o=bpy.context.object;o.name=name;o.scale=scale
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);parent_obj(o,parent);return finish_mesh(o,m)

def tube(name,points,radii,m,parent=None,sides=12):
    # Explicit sweeping provides UVs, tapered caps and continuous normals.
    verts=[];faces=[]
    pts=[Vector(p) for p in points]
    for i,p in enumerate(pts):
        tangent=(pts[min(i+1,len(pts)-1)]-pts[max(0,i-1)]).normalized();axis=Vector((0,0,1))
        if abs(tangent.dot(axis))>.96:axis=Vector((1,0,0))
        n=tangent.cross(axis).normalized();b=tangent.cross(n).normalized()
        for j in range(sides):
            a=math.tau*j/sides;verts.append(tuple(p+radii[i]*(n*math.cos(a)+b*math.sin(a))))
    for i in range(len(pts)-1):
        for j in range(sides):
            a=i*sides+j;c=i*sides+(j+1)%sides;d=(i+1)*sides+(j+1)%sides;b=(i+1)*sides+j;faces.append((a,b,d,c))
    faces.append(tuple(reversed(range(sides))));faces.append(tuple((len(pts)-1)*sides+j for j in range(sides)))
    return mesh(name,verts,faces,m,parent)

def lathe(name,profile,m,parent=None,sides=48,loc=(0,0,0),axis='Z'):
    verts=[];faces=[]
    for z,r in profile:
        for j in range(sides):
            a=math.tau*j/sides
            v=(r*math.cos(a),r*math.sin(a),z)
            if axis=='Y':v=(v[0],v[2],v[1])
            if axis=='X':v=(v[2],v[0],v[1])
            verts.append(tuple(v[i]+loc[i] for i in range(3)))
    for k in range(len(profile)-1):
        for j in range(sides):
            faces.append((k*sides+j,k*sides+(j+1)%sides,(k+1)*sides+(j+1)%sides,(k+1)*sides+j))
    faces.append(tuple(reversed(range(sides))));faces.append(tuple((len(profile)-1)*sides+j for j in range(sides)))
    return mesh(name,verts,faces,m,parent)

def torus(name,loc,major,minor,m,parent=None,axis='Z'):
    bpy.ops.mesh.primitive_torus_add(major_segments=40,minor_segments=8,location=loc,major_radius=major,minor_radius=minor)
    o=bpy.context.object;o.name=name
    if axis=='Y':o.rotation_euler.x=math.pi/2
    elif axis=='X':o.rotation_euler.y=math.pi/2
    parent_obj(o,parent);return finish_mesh(o,m)

def beam(name,a,b,width,m,parent=None):
    av,bv=Vector(a),Vector(b);obj=box(name,(width,width,(bv-av).length),tuple((av+bv)/2),m,parent,bevel=width*.12)
    obj.rotation_euler=(bv-av).to_track_quat('Z','Y').to_euler();return obj

def label(name,text,loc,size,m,parent=None,rotation=(0,0,0)):
    curve=bpy.data.curves.new(name,'FONT');curve.body=text;curve.size=size;curve.extrude=.0005;curve.align_x='CENTER';curve.align_y='CENTER';curve.resolution_u=3
    o=bpy.data.objects.new(name,curve);bpy.context.collection.objects.link(o);o.location=loc;o.rotation_euler=rotation;parent_obj(o,parent);curve.materials.append(m)
    bpy.context.view_layer.objects.active=o;o.select_set(True);bpy.ops.object.convert(target='MESH');o=bpy.context.object;o.select_set(False);return o

def join_group(name,objects,parent=None):
    bpy.ops.object.select_all(action='DESELECT')
    objs=[o for o in objects if o and o.type=='MESH']
    if not objs:return None
    for obj in objs:obj.select_set(True)
    bpy.context.view_layer.objects.active=objs[0];bpy.ops.object.join();o=bpy.context.object;o.name=name
    if parent:o.parent=parent
    o.select_set(False);return o

def export(asset):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in bpy.context.scene.objects:
        if obj.type=='MESH':
            # Smart UVs retained in the editable master; generated textures can be added without re-authoring.
            bpy.context.view_layer.objects.active=obj;obj.select_set(True)
            if len(obj.data.uv_layers)==0:
                bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(66),island_margin=.015);bpy.ops.object.mode_set(mode='OBJECT')
            obj.select_set(False)
    bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE/(asset+'.blend')))
    bpy.ops.export_scene.gltf(filepath=str(OUT/(asset+'.glb')),export_format='GLB',export_yup=True,export_apply=True,export_animations=False,export_extras=True,export_cameras=False,export_lights=False)
    meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
    STATS[asset]={'mesh_objects':len(meshes),'triangles':sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in meshes),'armatures':sum(o.type=='ARMATURE' for o in bpy.context.scene.objects),'source':f'source_assets/{asset}.blend','runtime':f'assets/refined/{asset}.glb'}
    print('ASSET_EXPORTED',asset,STATS[asset],flush=True)

# -------------------------- field equipment --------------------------
def hand(name,side,m,sleeve,parent):
    # Palm is a shaped loft, fingers follow explicit anatomical joints around the handle.
    s=side;root=empty(name,parent)
    palm_center=Vector((s*.052,-.035,-.215))
    verts=[];faces=[];rings=[(-.29,.040,.028),(-.25,.052,.029),(-.20,.057,.030),(-.165,.050,.025)]
    for z,rx,ry in rings:
        for j in range(16):
            a=math.tau*j/16;verts.append((palm_center.x+rx*math.cos(a),palm_center.y+ry*math.sin(a),z))
    for i in range(3):
        for j in range(16):faces.append((i*16+j,i*16+(j+1)%16,(i+1)*16+(j+1)%16,(i+1)*16+j))
    faces.extend([tuple(reversed(range(16))),tuple(48+j for j in range(16))]);palm=mesh(name+'Palm',verts,faces,m,root)
    pieces=[palm];bones=[('wrist',(s*.052,-.035,-.305),(s*.052,-.035,-.24),None),('palm',(s*.052,-.035,-.24),(s*.052,-.035,-.17),'wrist')]
    assignments=[(palm,'palm')]
    nail_material=mat(name+' translucent nails',(.62,.43,.32),.37)
    for finger in range(4):
        z=-.175-finger*.024
        # Four finger pads curl across the front of the pistol grip, no unconnected knuckle spheres.
        pts=[(s*.087,-.032,z),(s*.071,.008,z+.005),(s*.033,.026,z+.003),(s*.005,.009,z-.006)]
        finger_name=name+['Index','Middle','Ring','Little'][finger]
        f=tube(finger_name,pts,[.011,.0107,.0100,.007],m,root,14);pieces.append(f)
        prev='palm'
        for joint in range(3):
            bn=f'{finger_name}{joint+1}';bones.append((bn,pts[joint],pts[joint+1],prev));prev=bn
        assignments.append((f,finger_name+'1'))
        nail=uv_sphere(finger_name+'Nail',tuple(Vector(pts[-1])+Vector((s*.002,-.001,.006))),(.006,.009,.0015),nail_material,root,16,6)
        pieces.append(nail);assignments.append((nail,prev))
    tpts=[(s*.078,-.064,-.205),(s*.058,-.083,-.168),(s*.019,-.076,-.152),(s*-.005,-.049,-.164)]
    thumb=tube(name+'Thumb',tpts,[.016,.014,.012,.009],m,root,16);pieces.append(thumb)
    prev='palm'
    for j in range(3):bn=name+f'Thumb{j+1}';bones.append((bn,tpts[j],tpts[j+1],prev));prev=bn
    assignments.append((thumb,name+'Thumb1'))
    # Cuff and forearm connect continuously to wrist, toward the camera.
    cuff=lathe(name+'Cuff',[(-.35,.051),(-.343,.056),(-.30,.056),(-.29,.049)],sleeve,root,24,loc=(s*.052,-.035,0))
    arm_side=1 if name=='RightGrip' else s
    arm=tube(name+'Sleeve',[(s*.052,-.035,-.335),(arm_side*.09,-.19,-.43),(arm_side*.16,-.43,-.51),(arm_side*.22,-.67,-.59)],[.050,.068,.080,.092],sleeve,root,24)
    seam=tube(name+'SleeveSeam',[(s*.10,-.08,-.36),(arm_side*.14,-.24,-.44),(arm_side*.21,-.47,-.51),(arm_side*.27,-.66,-.58)],[.0025]*4,mat(name+' seam',(.17,.23,.23),.8),root,6)
    # Preserve a real per-hand skin and skeleton. Each finger is weighted by its closest bone segment.
    arm_data=bpy.data.armatures.new(name+'Skeleton');rig=bpy.data.objects.new(name+'Skeleton',arm_data);bpy.context.collection.objects.link(rig);rig.parent=root
    bpy.context.view_layer.objects.active=rig;rig.select_set(True);bpy.ops.object.mode_set(mode='EDIT')
    for bn,a,b,pn in bones:
        eb=arm_data.edit_bones.new(bn);eb.head=a;eb.tail=b
        if pn:eb.parent=arm_data.edit_bones[pn]
    bpy.ops.object.mode_set(mode='OBJECT');rig.select_set(False)
    for o,bn in assignments:
        # Three-segment finger weights retain actual joint deformation rather than one rigid finger.
        related=[b for b in bones if b[0].startswith(bn[:-1])] if bn[-1:].isdigit() else []
        if not related:related=[b for b in bones if b[0]==bn]
        groups={b[0]:o.vertex_groups.new(name=b[0]) for b in related}
        for v in o.data.vertices:
            local=o.matrix_world@v.co;distances=[]
            for bone in related:
                a,b=Vector(bone[1]),Vector(bone[2]);t=max(0,min(1,(local-a).dot(b-a)/max(1e-8,(b-a).length_squared)));distances.append(((local-a.lerp(b,t)).length,bone[0]))
            distances.sort();groups[distances[0][1]].add([v.index],1,'REPLACE')
        mod=o.modifiers.new('Articulated grip','ARMATURE');mod.object=rig
    join_group(name+'SleeveTextile',[cuff,arm,seam],root)
    skin=join_group(name+'SkinnedHand',pieces,root)
    # Join retains the 17 named vertex groups and active armature modifier.
    # Skin and textile each draw once (plus nail material), independent per hand.
    if not any(mod.type=='ARMATURE' for mod in skin.modifiers):
        mod=skin.modifiers.new('Articulated grip','ARMATURE');mod.object=rig
    return root

def field_equipment():
    clear();root=empty('FieldEquipmentAsset');lamp=empty('LampAssembly',root)
    enamel=mat('Graphite enamel - wet highlight',(.115,.155,.15),.30,.45);metal=mat('Anodised aluminium',(.35,.40,.41),.26,.78);black=mat('Rubber seals',(.025,.033,.029),.67);ceramic=mat('Ivory ceramic',(.66,.63,.48),.41)
    brass=mat('Brushed brass',(.45,.31,.10),.31,.70);blue=mat('Optical lens - coated cyan',(.06,.28,.36),.13,.38,emission=(.04,.29,.31));white=mat('Engraved pale lettering',(.71,.79,.69),.52);glow=mat('Energy cells',(.10,.66,.46),.24,.12,emission=(.10,.53,.35))
    main=[]
    main.append(lathe('Optical housing',[( -.18,.092),(-.16,.112),(-.08,.118),(.08,.145),(.20,.146),(.226,.131)],enamel,lamp,64,axis='Y'))
    main.append(lathe('Cooling collar',[(-.155,.119),(-.13,.123),(-.095,.123),(-.08,.118)],metal,lamp,48,axis='Y'))
    # Broad connected casing behind optics, with a rounded back and separate service panel.
    main.append(box('Battery protective housing',(.18,.21,.135),(0,-.17,-.035),enamel,lamp,.027))
    main.append(box('Battery service cover',(.014,.16,.095),(.101,-.17,-.032),metal,lamp,.01))
    main.append(box('Grip shoulder',(.068,.078,.055),(0,-.035,-.116),enamel,lamp,.018))
    main.append(box('Pistol grip',(.066,.089,.20),(0,-.034,-.23),black,lamp,.022))
    main.append(box('Grip heel',(.082,.109,.035),(0,-.034,-.328),enamel,lamp,.012))
    # Reinforced trigger guard is a continuous closed curved tube.
    main.append(tube('Trigger guard',[(.045,-.01,-.132),(.05,.083,-.14),(.05,.106,-.21),(.05,.064,-.273),(.043,-.012,-.273)],[.008]*5,metal,lamp,12))
    main.append(box('Mode control',(.027,.027,.008),(-.025,-.061,-.154),ceramic,lamp,.007))
    main.append(box('Recessed trigger',(.011,.025,.045),(.037,.015,-.162),brass,lamp,.007))
    join_group('SealedHousingAndGrip',main,lamp)
    rings=[]
    for y in [-.12,-.098,.05,.084,.177,.206]:rings.append(torus('Machined retaining ring',(0,y,0),.123 if y<.03 else .146,.0045,metal,lamp,'Y'))
    rings.append(lathe('Lens bezel',[(.221,.135),(.23,.137),(.243,.126),(.243,.109),(.235,.102)],brass,lamp,64,axis='Y'))
    join_group('LensRetainers',rings,lamp)
    lens=lathe('CoatedOpticalLens',[(.232,.108),(.247,.10),(.256,.052),(.259,.001)],blue,lamp,64,axis='Y')
    emitter=lathe('OpticalEmitter',[(.263,.037),(.266,.040),(.269,.032)],glow,lamp,48,axis='Y')
    fins=[]
    for angle in range(12):
        a=angle*math.tau/12
        fin=box('Cooling fin',(.019,.10,.011),(.122*math.cos(a),-.113,.122*math.sin(a)),metal,lamp,.003);fin.rotation_euler.y=-a;fins.append(fin)
    join_group('CoolingFins',fins,lamp)
    cells=[]
    for x in [-.06,0,.06]:
        cells.append(lathe('Capacitor sleeve',[(-.216,.021),(-.206,.026),(-.11,.026),(-.10,.021)],ceramic,lamp,24,loc=(x,0,-.115),axis='Y'))
        cells.append(box('Capacitor charge strip',(.008,.086,.007),(x,-.158,-.087),glow,lamp,.003))
    join_group('StorageCells',cells,lamp)
    bolts=[]
    for z in [-.07,0]:
        for y in [-.23,-.12]:bolts.append(lathe('Service fastener',[(.110,.006),(.112,.008),(.115,.006)],metal,lamp,6,loc=(0,y,z),axis='X'))
    join_group('CaptiveFasteners',bolts,lamp)
    label('Spec plate','SPECTRA / 03',(0,-.276,-.029),.014,white,lamp,rotation=(math.pi/2,0,0))
    sensor=empty('SensorModules',lamp)
    screen=box('SensorScreen',(.047,.033,.004),(.047,-.116,.115),glow,sensor,.005)
    label('Screen mark','nm',(.047,-.115,.12),.009,white,sensor)
    hand('RightGrip',-1,skin_mat(),mat('Rain shell textile',(.075,.135,.13),.8),root)
    support=hand('LeftSupport',-1,skin_mat(),mat('Left rain shell textile',(.075,.135,.13),.8),root)
    # Rest support palm lies under front housing; helper hides it until the flash braces.
    support.location=( -.075,.15,.08);support.rotation_euler.y=.13
    props=empty('SkillTools',root)
    reagent=empty('ToolLuminol',props);reagent.location=(-.24,.02,-.22)
    fluid=mat('Luminol solution',(.12,.36,.63),.18,.05,emission=(.05,.2,.48));bottle=mat('Bottle frosted glass',(.42,.57,.57),.26,.08)
    lathe('ReagentBottle',[(0,.028),(.01,.033),(.09,.033),(.12,.019),(.15,.017)],bottle,reagent,40)
    lathe('BlueFluid',[(.01,.026),(.08,.026)],fluid,reagent,32)
    lathe('DropperCap',[(.145,.021),(.16,.021),(.18,.012)],black,reagent,32)
    box('ReagentLabel',(.001,.039,.037),(.033,0,.065),ceramic,reagent,.002)
    label('Chemical legend','LUM',(.034,-.003,.067),.011,white,reagent,rotation=(math.pi/2,0,math.pi/2))
    salt=empty('ToolSalt',props);salt.location=(-.24,.03,-.22)
    # Flexible gusseted package with sealed seam and folded spout.
    bagverts=[(-.043,-.02,0),(.043,-.02,0),(.037,.025,0),(-.036,.025,0),(-.033,-.012,.13),(.033,-.012,.13),(.025,.013,.13),(-.028,.014,.13)]
    mesh('SaltPouch',bagverts,[(0,1,2,3),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0),(4,7,6,5)],ceramic,salt,.006)
    box('SealedPouchRim',(.074,.026,.008),(0,0,.132),metal,salt,.002)
    label('Salt formula','NaCl',(0,-.024,.07),.016,brass,salt,rotation=(math.pi/2,0,0))
    mud=empty('ToolMud',props);mud.location=(-.24,.03,-.22)
    lathe('MudCanister',[(0,.043),(.009,.048),(.12,.048),(.13,.044)],enamel,mud,40)
    lathe('SealedCanisterLid',[(.13,.05),(.142,.05),(.147,.044)],metal,mud,40)
    label('Mud scientific mark','SiO2',(0,-.048,.063),.015,white,mud,rotation=(math.pi/2,0,0))
    root['authoring']='Original parametric assets, field-science art direction';root['camera_forward']='Blender +Y exports Godot -Z';root['hand_bones_per_rig']=17
    export('field_equipment')

# ------------------------ abandoned forest car -----------------------
def car():
    clear();root=empty('RefinedCar');paint=mat('Weathered olive paint',(.24,.28,.18),.39,.36);rust=mat('Exposed oxide',(.29,.13,.065),.72,.15);metal=mat('Old trim',(.34,.38,.35),.32,.75);rubber=mat('Wet tyre rubber',(.028,.034,.03),.48);glass=mat('Smoked broken glazing',(.065,.125,.13),.16,.4);light=mat('Clouded lamp glass',(.48,.43,.28),.29)
    # Body uses variable-width cross-sections, shoulders, wheel arches and bevelled seams.
    profile=[(-2.07,1.01,.63,.97),(-1.80,1.10,.59,1.05),(-.91,1.09,.60,1.08),(.88,1.09,.60,1.09),(1.80,1.06,.59,.95),(2.07,.94,.62,.85)]
    verts=[];faces=[]
    for y,w,bottom,top in profile:
        verts.extend([(-w*.80,y,bottom),(-w,y,bottom+.16),(-w,y,top-.11),(-w*.89,y,top),(w*.89,y,top),(w,y,top-.11),(w,y,bottom+.16),(w*.80,y,bottom)])
    for k in range(len(profile)-1):
        for i in range(8):faces.append((k*8+i,k*8+(i+1)%8,(k+1)*8+(i+1)%8,(k+1)*8+i))
    faces.extend([tuple(reversed(range(8))),tuple((len(profile)-1)*8+i for i in range(8))]);body=mesh('Body',verts,faces,paint,root,.027)
    # True open wheel arches through the continuous shell, with rounded formed lips.
    for y in [-1.35,1.36]:
        bpy.ops.mesh.primitive_cylinder_add(vertices=48,radius=.481,depth=2.8,location=(0,y,.43),rotation=(0,math.pi/2,0))
        cutter=bpy.context.object;cutter.name='Wheel-arch authoring cut'
        boolean=body.modifiers.new('Open wheel arch','BOOLEAN');boolean.operation='DIFFERENCE';boolean.object=cutter
        bpy.context.view_layer.objects.active=body;bpy.ops.object.modifier_apply(modifier=boolean.name);bpy.data.objects.remove(cutter,do_unlink=True)
    # Tapered cabin integrated into actual slanted windscreen frames, separate door panels.
    cabinverts=[(-.94,-.88,1.03),(.94,-.88,1.03),(.94,.99,1.03),(-.94,.99,1.03),(-.77,-.55,1.73),(.77,-.55,1.73),(.77,.67,1.73),(-.77,.67,1.73)]
    mesh('CabinShell',cabinverts,[(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)],paint,root,.025)
    windows=[]
    for side in [-1,1]:
        windows.append(mesh('SideWindow',[(side*.96,-.79,1.10),(side*.96,-.02,1.10),(side*.79,-.02,1.65),(side*.79,-.51,1.65)],[(0,1,2,3)],glass,root,0,False))
        windows.append(mesh('SideWindow',[(side*.96,.04,1.10),(side*.96,.89,1.10),(side*.79,.61,1.65),(side*.79,.04,1.65)],[(0,1,2,3)],glass,root,0,False))
        # Sheet-metal seams are placed on the actual side profile, not floating decoration.
        pts=[(side*1.094,-.84,.69),(side*1.10,-.84,1.02),(side*.969,-.83,1.09),(side*.969,.92,1.09),(side*1.10,.92,1.02),(side*1.094,.92,.69),(side*1.094,-.84,.69)]
        tube('DoorSeam',pts,[.007]*len(pts),rubber,root,6)
        box('DoorHandle',(.031,.19,.037),(side*1.112,.64,.988),metal,root,.011)
        for y in [-1.35,1.36]:
            # tyre shoulder profile with recessed wheel hub and raised sidewall ring.
            wheel=lathe('Wheel',[(side*1.01,.29),(side*1.03,.385),(side*1.055,.43),(side*1.20,.43),(side*1.245,.39),(side*1.25,.29)],rubber,root,48,loc=(0,y,.43),axis='X')
            torus('TyreSidewall',(side*1.25,y,.43),.341,.011,rubber,root,'X')
            lathe('RimHub',[(side*1.252,.24),(side*1.257,.245),(side*1.267,.16)],metal,root,32,loc=(0,y,.43),axis='X')
            spokes=[]
            for j in range(5):
                a=math.tau*j/5;spokes.append(beam('HubSpoke',(side*1.268,y,.43),(side*1.268,y+.19*math.cos(a),.43+.19*math.sin(a)),.027,metal,root))
            join_group('RimSpokes',spokes,root)
            archpts=[]
            for j in range(13):
                a=math.pi*j/12;archpts.append((side*1.10,y+.49*math.cos(a),.43+.49*math.sin(a)))
            tube('ArchLip',archpts,[.018]*len(archpts),rust,root,8)
    mesh('FrontWindshield',[(-.88,-.91,1.10),(.88,-.91,1.10),(.70,-.59,1.64),(-.70,-.59,1.64)],[(0,1,2,3)],glass,root,0,False)
    crack_material=mat('Weathered glass fractures',(.23,.32,.31),.33)
    cracks=[]
    def glass_point(x,z):return (x,-.919+.32*(z-1.10)/.54,z)
    center=glass_point(-.32,1.33)
    for x,z in [(-.70,1.13),(-.68,1.53),(-.20,1.62),(.20,1.51),(.39,1.19),(-.01,1.10)]:
        middle=glass_point((x-.32)/2+RNG.uniform(-.035,.035),(z+1.33)/2)
        cracks.append(tube('FracturedGlazing',[center,middle,glass_point(x,z)],[.003,.0027,.001],crack_material,root,5))
    join_group('CrackedWindshield',cracks,root)
    mesh('RearWindshield',[(-.88,1.015,1.10),(.88,1.015,1.10),(.70,.71,1.64),(-.70,.71,1.64)],[(0,1,2,3)],glass,root,0,False)
    for y in [-2.11,2.11]:
        box('Bumper',(2.15,.12,.17),(0,y,.55),metal,root,.04)
        for x in [-.77,.77]:box('BrokenLamp',(.40,.027,.22),(x,y,.83),light,root,.028)
    hood=box('BentHood',(1.98,1.12,.045),(0,-1.45,1.064),paint,root,.02);hood.rotation_euler.x=-.055
    box('Grille',(1.09,.030,.17),(0,-2.081,.75),rubber,root,.01)
    bars=[]
    for x in [-.42,-.28,-.14,0,.14,.28,.42]:bars.append(box('GrilleRib',(.034,.032,.155),(x,-2.103,.75),metal,root,.008))
    join_group('GrilleSlats',bars,root)
    # Rust chips sit flush against lower panel and broken hood edges. Limited accents preserve stylised unity.
    chips=[]
    for side in [-1,1]:
        for j in range(22):
            y=RNG.uniform(-1.85,1.85);z=RNG.uniform(.64,.81)
            chips.append(uv_sphere('PanelOxide',(side*1.102,y,z),(.004,RNG.uniform(.025,.07),RNG.uniform(.013,.03)),rust,root,12,5))
    join_group('WeatheredPanelEdges',chips,root)
    root['model_features']='lofted body, tapered cabin, 4 sculpted tyres, door seams, wet oxide';export('abandoned_car')

# ------------------------------- tower -------------------------------
def tower():
    clear();root=empty('RefinedTower');steel=mat('Galvanised storm steel',(.34,.39,.39),.37,.78);rust=mat('Joint oxidation',(.24,.14,.065),.65,.32);porcelain=mat('Porcelain insulators',(.55,.61,.54),.21,.05);wire=mat('Weathered aluminium cables',(.20,.25,.25),.45,.75)
    structure=[];plates=[];bolts=[]
    def r(z):return 2.2-(1.65*z/12)
    for sx in [-1,1]:
        for sy in [-1,1]:
            structure.append(beam('TowerLeg',(sx*2.2,sy*2.2,0),(sx*.55,sy*.55,12),.15,steel,root))
            box('ConcreteFooting',(.60,.60,.30),(sx*2.2,sy*2.2,.15),mat('Wet concrete',(.26,.28,.25),.8),root,.025)
            plates.append(box('AnchorPlate',(.39,.39,.033),(sx*2.2,sy*2.2,.32),rust,root,.01))
    for level in range(4):
        lo=level*3;hi=lo+3
        for side in [-1,1]:
            for axis in [0,1]:
                a=[-r(lo),side*r(lo),lo];b=[r(hi),side*r(hi),hi];c=[r(lo),side*r(lo),lo];d=[-r(hi),side*r(hi),hi]
                if axis:a[0],a[1]=a[1],a[0];b[0],b[1]=b[1],b[0];c[0],c[1]=c[1],c[0];d[0],d[1]=d[1],d[0]
                structure.extend([beam('DiagonalBrace',a,b,.072,steel,root),beam('DiagonalBrace',c,d,.072,steel,root)])
            structure.append(beam('RingBeam',(-r(hi),side*r(hi),hi),(r(hi),side*r(hi),hi),.088,steel,root))
            structure.append(beam('RingBeam',(side*r(hi),-r(hi),hi),(side*r(hi),r(hi),hi),.088,steel,root))
        for sx in [-1,1]:
            for sy in [-1,1]:
                p=(sx*r(hi),sy*r(hi),hi);plates.append(box('GussetPlate',(.25,.026,.31),p,steel,root,.01))
                for z in [-.09,.09]:bolts.append(lathe('Rivet',[(0,.025),(.023,.025)],rust,root,6,loc=(p[0],p[1]-.022,p[2]+z),axis='Y'))
    structure.append(beam('Crown',(0,0,11),(0,0,15),.18,steel,root))
    insulators=[]
    for z in [10.5,13.0]:
        span=4.2 if z<12 else 3.3
        structure.append(beam('CrossArm',(-span,0,z),(span,0,z),.17,steel,root))
        for side in [-1,1]:
            structure.append(beam('ArmSupport',(0,0,z-1.2),(side*span,0,z),.084,steel,root))
            # Bell-disc insulator stack and hardware connect cable and crossarm.
            insulators.append(lathe('InsulatorPin',[(z-.78,.031),(z+.04,.031)],steel,root,12,loc=(side*span,0,0)))
            for j in range(6):
                zz=z-.12-j*.10
                insulators.append(lathe('InsulatorDisc',[(zz-.035,.07),(zz-.008,.14),(zz+.017,.075),(zz+.035,.06)],porcelain,root,24,loc=(side*span,0,0)))
            for direction in [-1,1]:
                pts=[]
                for j in range(21):
                    t=j/20;y=direction*38*t;zz=z-.78-.48*t-1.55*math.sin(math.pi*t)
                    pts.append((side*span,y,zz))
                tube('SaggingCable',pts,[.026]*len(pts),wire,root,6)
    join_group('TowerLattice',structure,root);join_group('JointPlates',plates,root);join_group('JointFasteners',bolts,root);join_group('Insulators',insulators,root)
    # Small climber ladder, warning board and broken lower service box give near-ground scale.
    ladder=[]
    for sx in [-.28,.28]:ladder.append(beam('LadderRail',(sx,-.9,.35),(sx,-.9,8),.045,steel,root))
    for j in range(25):ladder.append(beam('LadderRung',(-.28,-.9,.45+j*.30),(.28,-.9,.45+j*.30),.035,steel,root))
    join_group('InspectionLadder',ladder,root);box('WarningPlate',(.58,.024,.38),(0,-1.78,1.60),rust,root,.016)
    label('High-voltage sign','DANGER',(0,-1.798,1.60),.082,porcelain,root,rotation=(math.pi/2,0,0))
    root['model_features']='tapered load-bearing lattice, joint plates, 8 sagging cables, porcelain stacks';export('power_tower')

# ------------------------------ research -----------------------------
def book():
    clear();root=empty('ResearchReportAsset');cover=mat('Waterproof field notebook cloth',(.12,.28,.235),.62);paper=mat('Layered warm paper',(.72,.69,.54),.82);gold=mat('Foil research markings',(.59,.47,.20),.38,.58);elastic=mat('Elastic closure',(.13,.16,.13),.8)
    box('Pages',(.595,.11,.83),(0,0,0),paper,root,.009)
    box('FrontCover',(.68,.021,.92),(0,-.076,0),cover,root,.008)
    box('BackCover',(.68,.021,.92),(0,.076,0),cover,root,.008)
    # Spine is a rounded hollow back with two raised bands.
    spine=tube('Spine',[(-.313,-.071,-.45),(-.333,-.041,-.45),(-.343,0,-.45),(-.333,.043,-.45),(-.313,.072,-.45)],[.015]*5,cover,root,16)
    # Make a continuous longitudinal rounded spine, retaining a dedicated named mesh.
    bpy.data.objects.remove(spine,do_unlink=True)
    verts=[];faces=[]
    for z in [-.455,.455]:
        for j in range(13):
            a=-math.pi/2+math.pi*j/12;verts.append((-.315-.045*math.cos(a),.076*math.sin(a),z))
    for j in range(12):faces.append((j,j+1,j+14,j+13))
    mesh('Spine',verts,faces,cover,root,.002)
    edges=[]
    for i in range(24):
        y=-.052+i*.0045;edges.append(box('PageEdge',(.002,.0016,.807),(.298,y,0),gold,root,0))
    join_group('IndividualPageEdges',edges,root)
    for z in [-.30,.30]:box('CoverRule',(.49,.002,.012),(0,-.089,z),gold,root,.001)
    box('ElasticClosure',(.017,.002,.91),(.236,-.089,0),elastic,root,.003)
    # Diagram, plate and durable sewn spine refer to actual field instrumentation.
    label('English title','FIELD NOTES',(0,-.09,.14),.055,gold,root,rotation=(math.pi/2,0,0))
    label('Index plate','SPECTRAL RESEARCH',(0,-.09,.035),.025,gold,root,rotation=(math.pi/2,0,0))
    box('Corner reinforcement',(.115,.006,.042),(-.251,-.09,-.405),gold,root,.008)
    box('Research index tab',(.12,.013,.08),(.278,.006,.364),gold,root,.004)
    torus('Optics emblem',(0,-.09,-.155),.071,.004,gold,root,'Y')
    emblem=[]
    for x in [-.04,0,.04]:emblem.append(beam('Spectrum stripe',(x,-.092,-.192),(x,-.092,-.12),.004,gold,root))
    join_group('SpectrumEmblem',emblem,root);export('research_report')

field_equipment();car();tower();book()
(OUT/'ASSET_MANIFEST.json').write_text(json.dumps({'author':'Original procedural authoring by Codex for Happy Dash Forward','tool':'Blender 4.5 LTS','seed':731,'assets':STATS},indent=2)+'\n')
(OUT/'ASSET_LICENSE.txt').write_text('Original assets generated for Happy Dash Forward. No external meshes or textures were used. Editable Blender masters and deterministic generation script are included.\n')
