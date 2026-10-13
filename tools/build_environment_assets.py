"""Blender 4.5: editable botanical masters and three game representations.

Run with --background --python tools/build_environment_assets.py -- [--sample].
The masters retain the fused high-resolution root/trunk/branch surface. Runtime
LODs are exports derived from that same tree; they are not high subdivisions of
the previous primitive tree. No gameplay/collider coordinates are changed.
"""
import bpy, math, random, json, hashlib, sys
from pathlib import Path
from mathutils import Vector
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'assets/refined/environment'
SRC=ROOT/'source_assets/environment'
OUT.mkdir(parents=True, exist_ok=True); SRC.mkdir(parents=True,exist_ok=True)
MANIFEST={"generator":"tools/build_environment_assets.py", "software":bpy.app.version_string,
 "geometry_source":"original deterministic botanical construction, fused branching meshes and shaped laminae",
 "quality_note":"triangle counts are production evidence, not a claim of AAA visual acceptance", "trees":[],"terrain":[]}

def reset():
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    for data in list(bpy.data.meshes):
        if data.users==0:bpy.data.meshes.remove(data)

def mesh(name,verts,faces,uv=None,colors=None):
    data=bpy.data.meshes.new(name);data.from_pydata(verts,[],faces);data.update()
    obj=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(obj)
    for p in data.polygons:p.use_smooth=True
    if uv:
        layer=data.uv_layers.new(name='UVMap')
        for poly in data.polygons:
            for li in poly.loop_indices:layer.data[li].uv=uv[data.loops[li].vertex_index]
    if colors:
        layer=data.color_attributes.new(name='Color',type='FLOAT_COLOR',domain='POINT')
        for i,c in enumerate(colors):layer.data[i].color=c
    return obj

def material(name,color,rough=.7):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
    b=m.node_tree.nodes.get('Principled BSDF');b.inputs['Base Color'].default_value=(*color,1);b.inputs['Roughness'].default_value=rough
    if name in ['LeafPreview','DryLeaf','Grass','Fern','Shrub']:
        attribute=m.node_tree.nodes.new('ShaderNodeVertexColor');attribute.layer_name='Color'
        m.node_tree.links.new(attribute.outputs['Color'],b.inputs['Base Color'])
    return m

def triangulate(obj):
    mod=obj.modifiers.new('Export triangulation','TRIANGULATE');bpy.context.view_layer.objects.active=obj;bpy.ops.object.modifier_apply(modifier=mod.name)

def triangles(obj):return sum(len(p.vertices)-2 for p in obj.data.polygons)

def save_tree_sources(key,lod_objects):
    # Keep the full editable master and full runtime geometry without a single
    # 129-MiB blend blob: two native scenes preserve both independently.
    mothers=[o for o in bpy.data.objects if o.type=='MESH' and o.name.startswith('Master')]
    for suffix,objects in [('',mothers),('_runtime_lods',lod_objects)]:
        scene=bpy.data.scenes.new(key+suffix)
        for o in objects:scene.collection.objects.link(o)
        for o in objects:o.hide_viewport=False;o.hide_render=False
        bpy.data.libraries.write(str(SRC/(key+suffix+'.blend')),{scene},path_remap='RELATIVE_ALL',fake_user=True,compress=True)
        bpy.data.scenes.remove(scene)

def export(name,objects):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:o.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]
    bpy.ops.export_scene.gltf(filepath=str(OUT/(name+'.glb')),export_format='GLB',use_selection=True,
      export_apply=True,export_yup=True,export_normals=True,export_texcoords=True,export_materials='EXPORT')
    return hashlib.sha256((OUT/(name+'.glb')).read_bytes()).hexdigest()

def tube_arrays(verts,faces,points,radii,sides=14):
    start=len(verts);previous_cross=None
    for k,p in enumerate(points):
        p=Vector(p);direction=(Vector(points[min(k+1,len(points)-1)])-Vector(points[max(0,k-1)])).normalized()
        if previous_cross is None:
            reference=Vector((0,1,0)) if abs(direction.y)<.90 else Vector((1,0,0))
            cross=direction.cross(reference)
        else:
            # Parallel transport avoids a 90/180-degree frame jump when a
            # nearly vertical centerline crosses the global-UP singularity.
            cross=previous_cross-direction*previous_cross.dot(direction)
        if cross.length<.000001:
            reference=Vector((0,1,0)) if abs(direction.y)<.90 else Vector((1,0,0))
            cross=direction.cross(reference)
        cross.normalize();second=direction.cross(cross).normalized()
        previous_cross=cross.copy()
        for s in range(sides):
            a=s*math.tau/sides;ridge=1+.055*math.sin(s*3.0+k*.72)
            verts.append(tuple(p+(cross*math.cos(a)+second*math.sin(a))*radii[k]*ridge))
    for k in range(len(points)-1):
        for s in range(sides):
            a=start+k*sides+s;b=start+k*sides+(s+1)%sides;c=b+sides;d=a+sides;faces.append((a,b,c,d))
    faces.append(tuple(start+i for i in reversed(range(sides))))
    end=start+(len(points)-1)*sides;faces.append(tuple(end+i for i in range(sides)))

def leaf_arrays(verts,faces,uv,colors,base,tip,width,roll,segments,lanes,rng,dry=False,petiole=False):
    base=Vector(base);tip=Vector(tip);axis=(tip-base).normalized();length=(tip-base).length
    across=axis.cross(Vector((0,0,1)))
    if across.length<.01:across=Vector((1,0,0))
    across.normalize();normal=across.cross(axis).normalized()
    across=across*math.cos(roll)+normal*math.sin(roll);normal=across.cross(axis).normalized()
    if petiole:
        attachment=base.copy();base=base+axis*length*.12
        before=len(verts)
        tube_arrays(verts,faces,[tuple(attachment),tuple(attachment.lerp(base,.55)),tuple(base)],[.0015,.00115,.0008],4 if segments<14 else 6)
        for i in range(len(verts)-before):uv.append((2.0,0.0));colors.append((.14,.11,.04,1))
        length=(tip-base).length
    start=len(verts);tone=rng.uniform(.76,1.18);curl=rng.uniform(.045,.18);droop=rng.uniform(.035,.14)
    for i in range(segments+1):
        t=i/segments;shape=math.sin(math.pi*t)**.70*(.84+.23*t)
        # broad elliptic / subtly lobed lamina, physically rolled rims and midrib.
        serration=1+.025*math.cos(t*math.pi*30)
        center=base+axis*(t*length)+normal*(math.sin(t*math.pi)*length*.045-t*t*length*droop)
        for j in range(lanes+1):
            u=j/lanes*2-1;edge=width*shape*serration*u
            midrib=.0025*math.exp(-abs(u)*14)*math.sin(math.pi*t)
            vein_phase=t*math.pi*22-abs(u)*7
            secondary=.0017*max(0,math.cos(vein_phase))**8*math.sin(math.pi*t)*(1-abs(u))
            crease=length*(midrib+secondary+curl*u*u*math.sin(t*math.pi)+.005*math.sin(t*17+u*9)*abs(u)*math.sin(math.pi*t))
            if dry:crease+=length*.065*abs(u)**3*math.sin(t*math.pi)
            verts.append(tuple(center+across*edge+normal*crease));uv.append((.5 if i in [0,segments] else j/lanes,t))
            if dry:c=(.31*tone,.24*tone,.105*tone,1)
            else:c=(.19*tone,.32*tone,.065*tone,1)
            colors.append(c)
    for i in range(segments):
        for j in range(lanes):
            a=start+i*(lanes+1)+j
            # Single-point lamina base/tip use real triangle fans, avoiding
            # zero-area quads that merely inflate the reported polygon count.
            if i==0:faces.append((a,a+lanes+2,a+lanes+1))
            elif i==segments-1:faces.append((a,a+1,a+lanes+1))
            else:faces.append((a,a+1,a+lanes+2,a+lanes+1))

def plant_stem(verts,faces,uv,colors,points,radii,sides=6):
    before=len(verts);tube_arrays(verts,faces,points,radii,sides)
    for i in range(len(verts)-before):
        uv.append((2.0,i/max(1,len(verts)-before-1)));colors.append((.145,.105,.045,1))

def leaf_maps():
    n=4096;y,x=np.mgrid[0:n,0:n].astype(np.float32);u=x/(n-1);v=y/(n-1)
    edge=np.abs(u-.5)*2
    veins=np.exp(-np.square((u-.5)*125))
    for side in [-1,1]:
        for k in range(1,12):
            curve=k/13.0+np.abs(u-.5)*.66+.013*np.sin(u*13+k)
            veins+=np.exp(-np.square((v-curve)*135))*(side*(u-.5)>0)*.38
    # Fine tertiary venation is subordinate to the main/secondary veins.
    tertiary=(np.exp(-np.square(np.sin(u*113+v*67)*9))+np.exp(-np.square(np.sin(v*127-u*83)*10)))*.032
    veins+=tertiary
    grain=(np.sin(u*411+v*127)*np.sin(v*521-u*31)+np.sin(v*911+u*223))*.003
    mottles=np.sin(u*15+v*31)*np.sin(v*25-u*11)*.025
    rgb=np.zeros((n,n,4),np.float32);rgb[...,0]=.19+mottles+grain+veins*.08
    rgb[...,1]=.34+mottles+grain+veins*.11;rgb[...,2]=.068+mottles*.4+veins*.025
    rgb[...,:3]*=(1-edge[...,None]*.08);rgb[...,3]=1
    img=bpy.data.images.new('leaf_venation_color',width=n,height=n);img.pixels.foreach_set(rgb.ravel())
    img.filepath_raw=str(OUT/'leaf_venation_color.png');img.file_format='PNG';img.save()
    height=veins*.009+grain*.15
    gy,gx=np.gradient(height);normal=np.stack((-gx*n*.11,-gy*n*.11,np.ones_like(gx)),axis=-1)
    normal/=np.linalg.norm(normal,axis=-1)[...,None]
    rgba=np.concatenate((normal*.5+.5,np.ones((n,n,1),np.float32)),axis=-1)
    img=bpy.data.images.new('leaf_venation_normal',width=n,height=n);img.pixels.foreach_set(rgba.ravel())
    img.filepath_raw=str(OUT/'leaf_venation_normal.png');img.file_format='PNG';img.save()

def tree(variant,dead=False):
    reset();rng=random.Random(7139+variant*173+int(dead)*491)
    # Z-up Blender, export performs the standard GLTF Y-up coordinate conversion.
    height=8.0+rng.random()*1.7;lean=Vector((rng.uniform(-.55,.55),rng.uniform(-.55,.55),0))
    verts=[];faces=[];paths=[];sites=[]
    trunk=[];radii=[]
    for i in range(30):
        t=i/29;trunk.append(tuple(Vector((.065*math.sin(t*8),.07*math.sin(t*6),height*t*(1.0 if dead else .72)))+lean*t*t))
        radii.append((.38*(1-t)**.75+.018)*(1+.035*math.sin(i*.71)))
    tube_arrays(verts,faces,trunk,radii,32)
    # Buttress roots emerge tangentially from the trunk and are voxel-fused.
    for i in range(7):
        a=i*math.tau/7+rng.uniform(-.19,.19);ray=Vector((math.cos(a),math.sin(a),0));length=rng.uniform(1.0,1.6)
        points=[];rr=[]
        for k in range(10):
            t=k/9;points.append(tuple(ray*(.08+length*t)+Vector((0,0,.65*(1-t)**1.8-.005))))
            rr.append(.22*(1-t)**1.25+.009)
        tube_arrays(verts,faces,points,rr,18)
    # Live trees divide into a crown of competing scaffold branches instead
    # of ten horizontal rungs on one central pole. Crown endpoints populate
    # an irregular ellipsoid; tertiary forks carry terminal leaf-bearing stems.
    if not dead:
        for limb in range(7):
            a=limb*math.tau/7+rng.uniform(-.40,.40)
            h=rng.uniform(.37,.55);origin=Vector((0,0,height*h))+lean*h*h
            ray=Vector((math.cos(a),math.sin(a),0))
            reach=rng.uniform(1.50,2.3);up=rng.uniform(1.7,2.9)
            primary=[tuple(origin+ray*reach*(k/14)**1.15+Vector((0,0,up*(k/14)-.12*math.sin(k/14*math.pi)))) for k in range(15)]
            tube_arrays(verts,faces,primary,[.168*(1-k/14)**1.1+.014 for k in range(15)],20)
            for fork in range(6):
                t=.30+fork*.125;start=Vector(primary[min(14,int(t*14))])
                fa=a+rng.uniform(-1.25,1.25);direction=Vector((math.cos(fa),math.sin(fa),rng.uniform(.35,.95))).normalized()
                length=rng.uniform(.70,1.45);end=start+direction*length
                secondary=[tuple(start.lerp(end,k/8)+Vector((0,0,-.06*math.sin(k/8*math.pi)))) for k in range(9)]
                tube_arrays(verts,faces,secondary,[.052*(1-k/8)**1.15+.004 for k in range(9)],12)
                for twig in range(5):
                    st=Vector(secondary[2+twig]);ta=fa+(1 if twig%2 else -1)*rng.uniform(.45,1.25)
                    td=Vector((math.cos(ta),math.sin(ta),rng.uniform(-.20,.65))).normalized();te=st+td*rng.uniform(.45,.80)
                    tertiary=[tuple(st),tuple(st.lerp(te,.42)+Vector((0,0,.03))),tuple(st.lerp(te,.76)),tuple(te)]
                    tube_arrays(verts,faces,tertiary,[.018,.012,.007,.0015],8)
                    for sprig in range(6):
                        bt=st.lerp(te,.08+sprig*.145);turn=ta+(1 if sprig%2 else -1)*rng.uniform(.7,1.1)
                        bt_end=bt+Vector((math.cos(turn)*.19,math.sin(turn)*.19,rng.uniform(-.04,.12)))
                        sites.append((bt,bt_end,turn))
    else:
        for limb in range(8):
            h=.30+limb*.060+rng.uniform(-.025,.025);a=limb*2.399+rng.uniform(-.5,.5)
            origin=Vector((0,0,height*h))+lean*h*h;ray=Vector((math.cos(a),math.sin(a),0))
            reach=rng.uniform(1.55,2.8)*(1-(h-.45)*.5);up=rng.uniform(.75,1.65)
            pts=[tuple(origin+ray*reach*(k/14)+Vector((0,0,up*(k/14)**2-.18*math.sin(k/14*math.pi)))) for k in range(15)]
            tube_arrays(verts,faces,pts,[.118*(1-k/14)**1.23+.009 for k in range(15)],18)
            for fork in range(4):
                f=.46+fork*.145;start=Vector(pts[min(14,int(f*14))]);fa=a+rng.choice([-1,1])*rng.uniform(.40,1.10)
                dr=Vector((math.cos(fa),math.sin(fa),rng.uniform(.45,1.2))).normalized();end=start+dr*rng.uniform(.55,1.25)
                ps=[tuple(start.lerp(end,k/7)+Vector((0,0,-.08*math.sin(k/7*math.pi)))) for k in range(8)]
                tube_arrays(verts,faces,ps,[.047*(1-k/7)**1.3+.003 for k in range(8)],12)
                for sprig in range(7):
                    st=Vector(ps[min(7,int((.24+sprig*.10)*7))]);ta=fa+(1 if sprig%2 else -1)*rng.uniform(.6,1.15)
                    te=st+Vector((math.cos(ta),math.sin(ta),rng.uniform(.15,.55))).normalized()*rng.uniform(.32,.54)
                    sites.append((st,te,ta))
        for i in range(4):
            a=i*math.tau/4+.28;st=Vector(trunk[-7]);te=Vector(trunk[-1])+Vector((math.cos(a)*.86,math.sin(a)*.86,.12))
            tube_arrays(verts,faces,[tuple(st),tuple(st.lerp(te,.4)),tuple(st.lerp(te,.8)),tuple(te)],[.069,.041,.015,.002],12)
    bark=mesh('MasterContinuousRootTrunkBranches',verts,faces)
    bpy.context.view_layer.objects.active=bark;bark.select_set(True)
    mod=bark.modifiers.new('Fused branch crotches and buttress roots','REMESH');mod.mode='VOXEL';mod.voxel_size=.016 if dead else .026;mod.use_smooth_shade=True
    bpy.ops.object.modifier_apply(modifier=mod.name)
    sm=bark.modifiers.new('Cambium smooth transitions','SMOOTH');sm.factor=.50;sm.iterations=3;bpy.ops.object.modifier_apply(modifier=sm.name)
    # Sculpt multiscale bark bulges in the actual mesh, not only shading parallel lines.
    # Snapshot normals before edits; reading v.normal after every vertex edit
    # invalidates Blender's whole-mesh normal cache and makes sculpt O(n^2).
    surface_normals=[v.normal.copy() for v in bark.data.vertices]
    for v,n in zip(bark.data.vertices,surface_normals):
        p=v.co;theta=math.atan2(p.y,p.x)
        amount=.006*math.sin(p.z*8.1+theta*7)+.004*math.sin(p.z*27+theta*23)+.002*math.sin(p.x*67+p.y*31+p.z*53)
        v.co+=n*amount
    bark.data.update()
    # Fine stems are retained below the mother trunk's voxel pitch. They meet
    # fused forks and actually connect the lamina bases to living wood.
    core_mesh=bark.data.copy()
    twig_v=[];twig_f=[]
    for st,te,a in sites:
        tube_arrays(twig_v,twig_f,[tuple(st),tuple(st.lerp(te,.65)),tuple(te)],[.008,.004,.0012],6)
    twigs=mesh('LeafBearingTerminalTwigs',twig_v,twig_f)
    bpy.ops.object.select_all(action='DESELECT');bark.select_set(True);twigs.select_set(True)
    bpy.context.view_layer.objects.active=bark;bpy.ops.object.join()
    triangulate(bark); bark.data.validate()
    bark.data.materials.append(material('BarkPreview',(.22,.18,.105),.78))
    # Keep high-density editable mother geometry; runtime meshes derive from it.
    master_count=triangles(bark);bark.hide_render=False
    lod_objects=[];counts={}
    for prefix,target in [('Near',45000),('Mid',7200),('Far',2500)]:
        o=bark.copy();o.data=(core_mesh if prefix=='Far' else bark.data).copy();bpy.context.collection.objects.link(o);o.name=prefix+'Bark'
        bpy.context.view_layer.objects.active=o;dec=o.modifiers.new('Topology LOD','DECIMATE');dec.ratio=min(1,target/triangles(o));bpy.ops.object.modifier_apply(modifier=dec.name)
        o.data.validate()
        # UV projection is spatial / triplanar at runtime, full authored UVs retained for interchange.
        if not o.data.uv_layers:
            u=o.data.uv_layers.new(name='UVMap')
            for poly in o.data.polygons:
                for li in poly.loop_indices:
                    p=o.data.vertices[o.data.loops[li].vertex_index].co;u.data[li].uv=(math.atan2(p.y,p.x)/math.tau,p.z/2)
        counts[prefix+'Bark']=triangles(o);lod_objects.append(o)
    leaves_high=0
    if not dead:
        # Opposite / spiral phyllotaxis, loose leaves follow real secondary twigs.
        leaf_specs=[]
        for st,te,a in sites:
            for k in range(8):
                t=.10+k*.11;base=st.lerp(te,t);phi=a+(1 if k%2 else -1)*rng.uniform(.55,1.45)
                direction=Vector((math.cos(phi),math.sin(phi),rng.uniform(-.32,.65))).normalized()
                length=rng.uniform(.22,.36);leaf_specs.append((base,base+direction*length,length*rng.uniform(.23,.34),rng.uniform(-1.05,1.05)))
        leaf_counts={}
        # Medium leaves retain half the real distribution and increase projected
        # area moderately; petiole-sized details are below a pixel at that range.
        for prefix,seg,lanes,stride,size in [('Master',18,6,1,1.0),('Near',16,6,1,1.0),('Mid',5,2,2,1.25),('Far',2,2,6,1.95)]:
            lv=[];lf=[];lu=[];lc=[]
            leaf_counts[prefix]=len(leaf_specs[::stride])
            for base,tip,width,roll in leaf_specs[::stride]:
                adjusted_tip=base+(tip-base)*size
                leaf_arrays(lv,lf,lu,lc,base,adjusted_tip,width*size,roll,seg,lanes,rng,False,prefix in ['Master','Near'])
            o=mesh(prefix+'Canopy',lv,lf,lu,lc);triangulate(o)
            o.data.materials.append(material('LeafPreview',(.18,.31,.07),.62))
            if prefix=='Master':leaves_high=triangles(o);o.name='MasterDetailedLaminaVeins'
            else:counts[prefix+'Canopy']=triangles(o);lod_objects.append(o)
    key=('dead_tree_' if dead else 'broadleaf_tree_')+str(variant+1)
    save_tree_sources(key,lod_objects)
    sha=export(key,lod_objects)
    MANIFEST['trees'].append({'name':key,'height':height,'dead':dead,'source_triangles':master_count+leaves_high,
      'source_bark_triangles':master_count,'runtime_triangles':counts,'sha256':sha,
      'leaf_counts':leaf_counts if not dead else {},'leaf_support_twigs':len(sites) if not dead else 0,
      'crown_layers':({layer:sum(1 for spec in leaf_specs if ('inner' if math.hypot(spec[0].x,spec[0].y)<1.5 else 'middle' if math.hypot(spec[0].x,spec[0].y)<2.5 else 'outer')==layer) for layer in ['inner','middle','outer']} if not dead else {}),
      'authoring':'voxel fused buttress roots and branch crotches; asymmetric growth; meshed rolled laminae and midribs; UV venation map'})
    print('ENVIRONMENT_TREE',key,MANIFEST['trees'][-1],flush=True)

def terrain_kit():
    reset();rng=random.Random(6148);objects=[]
    # Actual multi-resolution weathered stones retain irregular silhouette and facets.
    for k in range(4):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=5,radius=1)
        o=bpy.context.object;o.name='Stone'+str(k+1)
        for v in o.data.vertices:
            p=v.co;f=1+.08*math.sin(p.x*7+p.z*2)+.045*math.sin(p.y*16-p.x*11)+.013*math.sin(p.z*37+p.y*31)
            p*=f;p.x*=.31+k*.012;p.y*=.24+k*.015;p.z*=.20;p.z=max(p.z,-.115)
        o.location.z=.11
        for p in o.data.polygons:p.use_smooth=True
        o.data.materials.append(material('WeatheredStone',(.24,.26,.235),.48));objects.append(o)
    # Full curling broadleaf litter. Six dry colors, full UV venation and meshed ribs.
    for k in range(4):
        v=[];f=[];uv=[];c=[];leaf_arrays(v,f,uv,c,(0,0,.013),(.07,.27,.021),.071,(-.13+k*.09),10,6,rng,True)
        o=mesh('LitterLeaf'+str(k+1),v,f,uv,c);o.data.materials.append(material('DryLeaf',(.30,.23,.10),.62));objects.append(o)
    # Botanical grass blades: curved, tapered, folded cross sections, not flat triangles.
    for k in range(3):
        v=[];f=[];uv=[];c=[]
        for blade in range(26):
            a=blade*2.399+k;base=Vector((math.cos(a)*rng.uniform(0,.13),math.sin(a)*rng.uniform(0,.13),0))
            length=rng.uniform(.19,.48);dr=Vector((math.cos(a),math.sin(a),0));cross=Vector((-dr.y,dr.x,0));start=len(v)
            for i in range(10):
                t=i/9;center=base+Vector((0,0,length*(t-.10*t*t)))+dr*(length*.58*t*t)
                width=.009*math.sin(math.pi*t)**.4+.0003
                for j in range(3):
                    v.append(tuple(center+cross*width*(j-1)+Vector((0,0,.002*(1-abs(j-1))))));uv.append((j/2,t));c.append((.17,.29,.055,1))
            for i in range(9):
                for j in range(2):
                    s=start+i*3+j;f.append((s,s+1,s+4,s+3))
        o=mesh('GrassClump'+str(k+1),v,f,uv,c);o.data.materials.append(material('Grass',(.11,.25,.055),.59));objects.append(o)
    for k in range(3):
        v=[];f=[];uv=[];c=[]
        for frond in range(8):
            a=frond*math.tau/8+k*.41;dr=Vector((math.cos(a),math.sin(a),0));length=rng.uniform(.50,.90)
            cross=Vector((-dr.y,dr.x,0))
            rachis=[tuple(dr*length*(i/20)+Vector((0,0,length*(.07+.72*(i/20)-.57*(i/20)**2)))) for i in range(21)]
            plant_stem(v,f,uv,c,[(0,0,0)]+rachis,[.008]+[.007*(1-i/20)+.001 for i in range(21)])
            for pinna in range(15):
                t=.12+pinna*.052;center=dr*length*t+Vector((0,0,length*(.07+.72*t-.57*t*t)))
                reach=length*.19*math.sin(math.pi*t)
                for side in [-1,1]:
                    tip=center+cross*side*reach+dr*reach*.45
                    leaf_arrays(v,f,uv,c,center,tip,reach*.16,side*.10,5,2,rng)
        o=mesh('Fern'+str(k+1),v,f,uv,c);o.data.materials.append(material('Fern',(.12,.27,.06),.60));objects.append(o)
    for k in range(2):
        v=[];f=[];uv=[];c=[]
        for stem in range(16):
            a=stem*2.399+k*1.1;height=rng.uniform(.35,.95);dr=Vector((math.cos(a),math.sin(a),0))
            branch=[tuple(dr*(.10+.35*(i/12)**2)+Vector((0,0,height*i/12))) for i in range(13)]
            plant_stem(v,f,uv,c,branch,[.011*(1-i/12)+.002 for i in range(13)])
            for leaf in range(14):
                t=.20+leaf*.052;base=dr*(.10+.35*t*t)+Vector((0,0,height*t))
                turn=a+(1 if leaf%2 else -1)*.89;tip=base+Vector((math.cos(turn)*.22,math.sin(turn)*.22,.08))
                leaf_arrays(v,f,uv,c,base,tip,.072,math.sin(leaf)*.19,6,4,rng)
        o=mesh('Shrub'+str(k+1),v,f,uv,c);o.data.materials.append(material('Shrub',(.15,.27,.05),.57));objects.append(o)
    # Uneven shallow pond outline is cosmetic; no geometry displaces the playable ground.
    v=[(0,0,.004)];f=[]
    for i in range(64):
        a=i*math.tau/64;r=1+.085*math.sin(a*3)+.025*math.cos(a*11);v.append((math.cos(a)*r,math.sin(a)*r*.67,.004))
    for i in range(64):f.append((0,1+i,1+(i+1)%64))
    pond=mesh('Puddle',v,f);pond.data.materials.append(material('RainPuddle',(.055,.08,.09),.12));objects.append(pond)
    for o in objects:
        bpy.context.view_layer.objects.active=o;triangulate(o)
        if o.location.length:
            bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
        MANIFEST['terrain'].append({'name':o.name,'triangles':triangles(o)})
    for i,o in enumerate(objects):o.location=(i%5*2.3,i//5*2.3,0)
    bpy.ops.wm.save_as_mainfile(filepath=str(SRC/'forest_understory_kit.blend'),compress=True)
    for o in objects:o.location=(0,0,0)
    MANIFEST['terrain_sha256']=export('forest_understory_kit',objects)
    print('ENVIRONMENT_TERRAIN',MANIFEST['terrain'],flush=True)

def leaf_study():
    # Same actual near-game lamina/petiole construction, isolated for close
    # grazing-light/underside review; not a separate higher-quality render asset.
    reset();rng=random.Random(9703);v=[];f=[];uv=[];c=[]
    plant_stem(v,f,uv,c,[(-.27,0,.10),(-.10,0,.12),(.12,.01,.16),(.28,.02,.20)],[.007,.006,.004,.001],8)
    for i in range(5):
        base=Vector((-.20+i*.095,0,.12+i*.014));side=-1 if i%2 else 1
        tip=base+Vector((.11,side*(.21+i*.017),.035+i*.018))
        leaf_arrays(v,f,uv,c,base,tip,.073,side*.32,16,6,rng,False,True)
    o=mesh('LeafStudy',v,f,uv,c);triangulate(o);o.data.materials.append(material('LeafPreview',(.18,.31,.07),.62))
    bpy.ops.wm.save_as_mainfile(filepath=str(SRC/'leaf_petiole_venation_study.blend'),compress=True)
    MANIFEST['leaf_study']={'leaf_count':5,'triangles':triangles(o),'sha256':export('leaf_detail_study',[o]),'construction':'exact near-game leaf/petiole specification'}

def recover_existing_tree(variant,dead=False):
    key=('dead_tree_' if dead else 'broadleaf_tree_')+str(variant+1)
    p=SRC/(key+'.blend')
    if not p.exists():return False
    bpy.ops.wm.open_mainfile(filepath=str(p))
    mothers=[o for o in bpy.data.objects if o.type=='MESH' and o.name.startswith('Master')]
    source=sum(triangles(o) for o in mothers)
    if source<(280000 if dead else 450000):return False
    bark_count=sum(triangles(o) for o in mothers if 'Branches' in o.name)
    objects=[o for o in bpy.data.objects if o.type=='MESH' and o.name.startswith(('Near','Mid','Far'))]
    if not objects and (SRC/(key+'_runtime_lods.blend')).exists():
        bpy.ops.wm.open_mainfile(filepath=str(SRC/(key+'_runtime_lods.blend')))
        objects=[o for o in bpy.data.objects if o.type=='MESH' and o.name.startswith(('Near','Mid','Far'))]
    counts={}
    for o in objects:o.data.validate();counts[o.name]=triangles(o);o.hide_viewport=True;o.hide_render=True
    if mothers and objects and not (SRC/(key+'_runtime_lods.blend')).exists():save_tree_sources(key,objects)
    for o in objects:o.hide_viewport=False;o.hide_render=False
    height=8.0+random.Random(7139+variant*173+int(dead)*491).random()*1.7
    previous={}
    if (OUT/'ENVIRONMENT_MANIFEST.json').exists():
        previous=next((dict(e) for e in json.loads((OUT/'ENVIRONMENT_MANIFEST.json').read_text()).get('trees',[]) if e['name']==key),{})
    previous.update({'name':key,'height':height,'dead':dead,'source_triangles':source,
      'source_bark_triangles':bark_count,
      'runtime_triangles':counts,'sha256':export(key,objects),
      'authoring':'voxel fused buttress roots and branch crotches; asymmetric growth; meshed rolled laminae and midribs; UV venation map'})
    MANIFEST['trees'].append(previous)
    print('ENVIRONMENT_RECOVERED',key,source,flush=True)
    return True

def repair_far_core(entry):
    key=entry['name'];bpy.ops.wm.open_mainfile(filepath=str(SRC/(key+'.blend')))
    master=next(o for o in bpy.data.objects if o.type=='MESH' and 'MasterContinuous' in o.name)
    data=master.data;adj=[[] for v in data.vertices]
    for edge in data.edges:
        a,b=edge.vertices;adj[a].append(b);adj[b].append(a)
    seen=set();largest=set()
    for start in range(len(adj)):
        if start in seen:continue
        component={start};stack=[start];seen.add(start)
        while stack:
            for nxt in adj[stack.pop()]:
                if nxt not in seen:seen.add(nxt);component.add(nxt);stack.append(nxt)
        if len(component)>len(largest):largest=component
    ordered=sorted(largest);indices={old:i for i,old in enumerate(ordered)}
    verts=[tuple(data.vertices[i].co) for i in ordered]
    faces=[tuple(indices[i] for i in poly.vertices) for poly in data.polygons if all(i in largest for i in poly.vertices)]
    bpy.ops.wm.open_mainfile(filepath=str(SRC/(key+'_runtime_lods.blend')))
    old=bpy.data.objects.get('FarBark');bpy.data.objects.remove(old,do_unlink=True)
    far=mesh('FarBark',verts,faces);bpy.context.view_layer.objects.active=far
    dec=far.modifiers.new('Core-only far silhouette','DECIMATE');dec.ratio=min(1,2500/triangles(far));bpy.ops.object.modifier_apply(modifier=dec.name);far.data.validate()
    layer=far.data.uv_layers.new(name='UVMap')
    for poly in far.data.polygons:
        for li in poly.loop_indices:
            p=far.data.vertices[far.data.loops[li].vertex_index].co;layer.data[li].uv=(math.atan2(p.y,p.x)/math.tau,p.z/2)
    far.data.materials.append(material('BarkPreview',(.22,.18,.105),.78))
    objects=[o for o in bpy.data.objects if o.type=='MESH' and o.name.startswith(('Near','Mid','Far'))]
    scene=bpy.data.scenes.new(key+'_runtime_lods')
    for o in objects:scene.collection.objects.link(o)
    bpy.data.libraries.write(str(SRC/(key+'_runtime_lods.blend')),{scene},path_remap='RELATIVE_ALL',fake_user=True,compress=True)
    bpy.data.scenes.remove(scene)
    entry['runtime_triangles']['FarBark']=triangles(far);entry['sha256']=export(key,objects)
    entry['far_bark_source']='largest continuous fused root/trunk/scaffold component, excluding detached terminal stems'
    print('REPAIRED_FAR_CORE',key,triangles(far),flush=True)

if __name__=='__main__':
    args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    if '--split-sources' not in args and '--far-core-only' not in args:leaf_maps()
    if '--far-core-only' in args:
        MANIFEST=json.loads((OUT/'ENVIRONMENT_MANIFEST.json').read_text())
        for entry in MANIFEST['trees']:repair_far_core(entry)
    elif '--split-sources' in args:
        MANIFEST=json.loads((OUT/'ENVIRONMENT_MANIFEST.json').read_text())
        for entry in MANIFEST['trees']:
            bpy.ops.wm.open_mainfile(filepath=str(SRC/(entry['name']+'.blend')))
            selected=[o for o in bpy.data.objects if o.type=='MESH' and o.name.startswith(('Near','Mid','Far'))]
            if selected:save_tree_sources(entry['name'],selected)
            entry['native_master']=entry['name']+'.blend';entry['native_lods']=entry['name']+'_runtime_lods.blend'
    elif '--repair-exports' in args:
        MANIFEST=json.loads((OUT/'ENVIRONMENT_MANIFEST.json').read_text())
        for entry in MANIFEST['trees']:
            bpy.ops.wm.open_mainfile(filepath=str(SRC/(entry['name']+'.blend')))
            native_path=SRC/(entry['name']+'_runtime_lods.blend')
            if native_path.exists():bpy.ops.wm.open_mainfile(filepath=str(native_path))
            selected=[]
            for o in bpy.data.objects:
                if o.type=='MESH' and o.name.startswith(('Near','Mid','Far')):
                    o.data.validate();selected.append(o);entry['runtime_triangles'][o.name]=triangles(o)
            for o in selected:o.hide_viewport=True;o.hide_render=True
            bpy.ops.wm.save_as_mainfile(filepath=str(native_path if native_path.exists() else SRC/(entry['name']+'.blend')),compress=True)
            for o in selected:o.hide_viewport=False;o.hide_render=False
            entry['sha256']=export(entry['name'],selected)
    elif '--terrain-only' in args:
        if (OUT/'ENVIRONMENT_MANIFEST.json').exists():MANIFEST=json.loads((OUT/'ENVIRONMENT_MANIFEST.json').read_text());MANIFEST['terrain']=[]
        terrain_kit()
    else:
        for i in range(1 if '--sample' in args else 6):
            if '--resume' not in args or '--crown-rebuild' in args or not recover_existing_tree(i):tree(i)
        for i in range(1 if '--sample' in args else 3):
            if '--resume' not in args or not recover_existing_tree(i,True):tree(i,True)
        terrain_kit();leaf_study()
    (OUT/'ENVIRONMENT_MANIFEST.json').write_text(json.dumps(MANIFEST,indent=2)+'\n')
