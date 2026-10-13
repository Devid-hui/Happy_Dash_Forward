"""Editable field-report and steel tower detail, independent of hand/forest workers."""
import bpy,math,json,types,sys
from pathlib import Path
from mathutils import Vector
lib=types.ModuleType('research_high');lib.__file__=str(Path(__file__).with_name('build_high_fidelity_assets.py'))
exec(compile(Path(lib.__file__).read_text().split('\nif ASSET in')[0],lib.__file__,'exec'),lib.__dict__)
ROOT=lib.ROOT;OUT=lib.OUT;SOURCE=lib.SOURCE
H=True

def rounded_plate(name,size,loc,m,parent,bevel=.003):
    o=lib.box(name,size,loc,m,parent,bevel)
    return o

def report():
    lib.base.clear();root=lib.empty('ResearchReportAsset')
    cover=lib.texture_material('Waterproof bound research cloth',(.080,.21,.16),'cloth',metal=0,rough=.69)
    paper=lib.texture_material('Aged field paper',(.69,.64,.48),'metal',size=2048,metal=0,rough=.88)
    gold=lib.mat('Embossed notebook foil',(.55,.38,.12),.43,.67);thread=lib.mat('Notebook binding thread',(.45,.43,.29),.85)
    # Actual layered sheets have separated curved fore-edges and a compressed sewn spine.
    sheets=[];count=72 if H else 40
    for i in range(count):
        y=-.010+.020*i/(count-1)
        nu=64 if H else 24;nv=80 if H else 30;verts=[];faces=[];uv=[]
        for u in range(nu):
            x=-.288+.579*u/(nu-1)
            for v in range(nv):
                z=-.409+.818*v/(nv-1)
                curl=.0010*math.sin(i*1.7+v*.17)*(u/(nu-1))**4
                verts.append((x,y+curl,z));uv.append((u/(nu-1),v/(nv-1)))
        for u in range(nu-1):
            for v in range(nv-1):
                a=u*nv+v;faces.append((a,a+1,a+nv+1,a+nv))
        o=lib.shaped_mesh('IndividualPaperSheet',verts,faces,paper,root,uv)
        mod=o.modifiers.new('Real paper thickness','SOLIDIFY');mod.thickness=.020/count*.92;bpy.context.view_layer.objects.active=o;bpy.ops.object.modifier_apply(modifier=mod.name)
        sheets.append(o)
    lib.join('Pages',sheets,root)
    rounded_plate('FrontCover',(.676,.004,.914),(0,-.014,0),cover,root,.002)
    rounded_plate('BackCover',(.676,.004,.914),(0,.014,0),cover,root,.002)
    # Hollow curved spine wraps the sewn leaves and joins both covers.
    verts=[];faces=[];n=100 if H else 40;kcount=60 if H else 24
    for k in range(kcount):
        z=-.456+.912*k/(kcount-1)
        for j in range(n):
            a=-math.pi/2+math.pi*j/(n-1);verts.append((-.314-.015*math.cos(a),.015*math.sin(a),z))
    for k in range(kcount-1):
        for j in range(n-1):faces.append((k*n+j,k*n+j+1,(k+1)*n+j+1,(k+1)*n+j))
    spine=lib.shaped_mesh('Spine',verts,faces,cover,root)
    mod=spine.modifiers.new('Real spine backing','SOLIDIFY');mod.thickness=.003;bpy.context.view_layer.objects.active=spine;bpy.ops.object.modifier_apply(modifier=mod.name)
    bindings=[]
    for z in [-.29,-.13,.04,.20,.34]:
        bindings.append(lib.sweep('SewnBinding',[(-.310,-.010,z),(-.328,0,z),(-.310,.010,z)],[.0012]*3,thread,root,sides=16 if H else 8,steps=24 if H else 7))
    lib.join('SewnSignatures',bindings,root)
    embossed=[]
    for z in [-.303,.303]:embossed.append(rounded_plate('CoverFoilRule',(.486,.0012,.008),(0,-.017,z),gold,root,.001))
    for x in [-.248,.248]:
        for z in [-.396,.396]:embossed.append(rounded_plate('RoundedCornerGuard',(.105,.001,.042),(x,-.017,z),gold,root,.009))
    lib.join('FoilAndCornerGuards',embossed,root)
    lib.label('FieldTitle','FIELD NOTES',(0,-.017,.135),.052,gold,root,(math.pi/2,0,0))
    lib.label('ScienceSubtitle','SPECTRAL RESEARCH',(0,-.017,.033),.023,gold,root,(math.pi/2,0,0))
    lib.label('ArchiveReference','RAINFIELD / 03',(0,-.017,-.244),.017,gold,root,(math.pi/2,0,0))
    lib.seal('EngravedOpticsEmblem',(0,-.018,-.135),.065,.0012,gold,root,'Y')
    for x in [-.034,0,.034]:lib.sweep('SpectrumLine',[(x,-.018,-.174),(x,-.018,-.098)],[.0010]*2,gold,root,sides=12 if H else 6,steps=14 if H else 4)
    rounded_plate('IndexTab',(.084,.010,.072),(.286,.0,.351),gold,root,.004)
    rounded_plate('ElasticClosure',(.014,.002,.914),(.233,-.019,0),lib.mat('Wet elastic closure',(.042,.070,.046),.82),root,.001)
    root['quality_status']='candidate report: layered sheets, sewn spine, real covers and cloth PBR'

def angle_beam(name,a,b,w,m,parent):
    av,bv=Vector(a),Vector(b);direction=(bv-av).normalized();u=direction.cross(Vector((0,0,1))).normalized()
    if u.length<.001:u=Vector((1,0,0))
    v=direction.cross(u).normalized();t=w*.13
    section=[(0,0),(w,0),(w,t),(t,t),(t,w),(0,w)]
    verts=[];faces=[];steps=16 if H else 4
    for j in range(steps):
        p=av.lerp(bv,j/(steps-1))
        for x,y in section:verts.append(tuple(p+u*(x-w*.35)+v*(y-w*.35)))
    for j in range(steps-1):
        for k in range(6):faces.append((j*6+k,j*6+(k+1)%6,(j+1)*6+(k+1)%6,(j+1)*6+k))
    faces.extend([tuple(reversed(range(6))),tuple((steps-1)*6+k for k in range(6))])
    return lib.shaped_mesh(name,verts,faces,m,parent,bevel=0) if False else lib.shaped_mesh(name,verts,faces,m,parent)

def tower():
    lib.base.clear();root=lib.empty('RefinedTower')
    steel=lib.texture_material('Galvanised tower steel',(.25,.28,.27),'metal',metal=.81,rough=.39)
    oxide=lib.texture_material('Weathered tower joints',(.18,.095,.037),'car',size=2048,metal=.28,rough=.72)
    ceramic=lib.mat('Glazed porcelain insulators',(.47,.56,.48),.22,.01);wire=lib.mat('Weathered stranded cable',(.11,.14,.13),.53,.69)
    structure=[];connections=[];insulators=[]
    r=lambda z:2.2-1.65*z/12
    for sx in [-1,1]:
        for sy in [-1,1]:
            structure.append(angle_beam('MainAngleLeg',(sx*2.2,sy*2.2,0),(sx*.55,sy*.55,12),.19,steel,root))
            rounded_plate('ConcreteFooting',(.64,.64,.34),(sx*2.2,sy*2.2,.17),lib.mat('Wet foundation concrete',(.25,.27,.22),.83),root,.022)
            connections.append(rounded_plate('AnchorPlate',(.41,.41,.032),(sx*2.2,sy*2.2,.357),oxide,root,.005))
            for dx in [-.14,.14]:
                for dy in [-.14,.14]:connections.append(lib.screw('FoundationAnchorBolt',(sx*2.2+dx,sy*2.2+dy,.374),steel,root,'Z',.025))
    for level in range(4):
        lo=level*3.;hi=lo+3.
        for side in [-1,1]:
            for axis in [0,1]:
                a=[-r(lo),side*r(lo),lo];b=[r(hi),side*r(hi),hi];c=[r(lo),side*r(lo),lo];d=[-r(hi),side*r(hi),hi]
                if axis:
                    a[0],a[1]=a[1],a[0];b[0],b[1]=b[1],b[0];c[0],c[1]=c[1],c[0];d[0],d[1]=d[1],d[0]
                structure.extend([angle_beam('DiagonalAngleBrace',a,b,.086,steel,root),angle_beam('DiagonalAngleBrace',c,d,.086,steel,root)])
            structure.extend([angle_beam('HorizontalRing',(-r(hi),side*r(hi),hi),(r(hi),side*r(hi),hi),.10,steel,root),angle_beam('HorizontalRing',(side*r(hi),-r(hi),hi),(side*r(hi),r(hi),hi),.10,steel,root)])
        for sx in [-1,1]:
            for sy in [-1,1]:
                p=(sx*r(hi),sy*r(hi),hi);connections.append(rounded_plate('GussetPlate',(.30,.024,.38),p,steel,root,.009))
                for dx in [-.08,.08]:
                    for dz in [-.12,0,.12]:connections.append(lib.screw('GussetFastener',(p[0]+dx,p[1]-.026,p[2]+dz),oxide,root,'Y',.023))
    structure.append(angle_beam('CrownSupport',(0,0,11),(0,0,15),.21,steel,root))
    for z in [10.5,13.]:
        span=4.2 if z<12 else 3.3
        structure.append(angle_beam('StructuralCrossArm',(-span,0,z),(span,0,z),.23,steel,root))
        for side in [-1,1]:
            structure.append(angle_beam('CrossArmTie',(0,0,z-1.2),(side*span,0,z),.11,steel,root))
            connections.append(rounded_plate('ArmConnectionPlate',(.39,.035,.40),(side*.46,0,z-.11),oxide,root,.009))
            for j in range(7):
                zz=z-.10-j*.095
                insulators.append(lib.turned('PorcelainWeatherDisc',[(zz-.025,.054),(zz-.007,.141),(zz+.013,.08),(zz+.025,.054)],ceramic,root,'Z',(side*span,0,0),sides=160 if H else 56,steps=14 if H else 4))
            insulators.append(lib.turned('InsulatorSteelPin',[(z-.80,.023),(z+.07,.023)],steel,root,'Z',(side*span,0,0),sides=48 if H else 20,steps=16 if H else 5))
            for direction in [-1,1]:
                points=[]
                for j in range(61 if H else 31):
                    t=j/(60 if H else 30);points.append((side*span,direction*38*t,z-.78-.48*t-1.55*math.sin(math.pi*t)))
                lib.sweep('SaggingCable',points,[.026]*len(points),wire,root,sides=20 if H else 8,steps=1)
    lib.join('StructuralSteelAngles',structure,root);lib.join('JointPlatesAndFasteners',connections,root);lib.join('Insulators',insulators,root)
    ladder=[]
    for x in [-.29,.29]:ladder.append(angle_beam('LadderRail',(x,-.92,.3),(x,-.92,8.4),.055,steel,root))
    for j in range(28):ladder.append(lib.sweep('LadderRung',[(-.29,-.92,.44+j*.28),(.29,-.92,.44+j*.28)],[.019,.019],steel,root,sides=32 if H else 12,steps=10 if H else 3))
    lib.join('InspectionLadder',ladder,root)
    rounded_plate('WarningPlate',(.68,.020,.40),(0,-1.8,1.65),oxide,root,.007);lib.label('HighVoltageWarning','HIGH VOLTAGE',(0,-1.813,1.65),.066,ceramic,root,(math.pi/2,0,0))
    root['quality_status']='candidate tower: L-section members, connected bolted plates, porcelain stacks and eight cables'

if __name__=='__main__':
    for name,fn in [('power_tower',tower),('research_report',report)]:
        if '--only-report' in sys.argv and name!='research_report':continue
        H=True;lib.HI=True;fn();lib.save_master(name)
        H=False;lib.HI=False;fn();lib.save_runtime(name)
    (SOURCE/'COMMERCIAL_MODEL_MANIFEST.json').write_text(json.dumps({'quality_status':'candidate pending visual acceptance','tool':'Blender 4.5 LTS','original_maps':True,'assets':lib.COUNTS},indent=2)+'\n')
