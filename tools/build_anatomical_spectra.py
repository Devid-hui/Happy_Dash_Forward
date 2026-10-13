"""Anatomical open-hand -> joint-posed grip and compact field optics candidate.
Blender 4.5 LTS; modified CC0 MakeHuman hands and original field equipment.
"""
import bpy, math, numpy as np, json, types, sys
from pathlib import Path
from mathutils import Vector, Matrix
library=types.ModuleType('high_base');library.__file__=str(Path(__file__).with_name('build_high_fidelity_assets.py'))
exec(compile(Path(library.__file__).read_text().split('\nif ASSET in')[0],library.__file__,'exec'),library.__dict__)
ROOT=library.ROOT;OUT=library.OUT;SOURCE=library.SOURCE
sys.path.insert(0,str(Path(__file__).parent))
H=True
empty=library.empty;mesh=library.shaped_mesh;sweep=library.sweep;turned=library.turned;seal=library.seal;box=library.box;mat=library.mat;join=library.join;label=library.label

def compact_equipment():
    library.base.clear();root=empty('FieldEquipmentAsset');lamp=empty('LampAssembly',root)
    enamel=library.texture_material('Field graphite coated metal',(.062,.088,.076),'metal',metal=.45,rough=.42)
    metal=library.texture_material('Machined aluminium',(.35,.37,.34),'metal',metal=.85,rough=.30)
    rubber=library.texture_material('Grip vulcanised rubber',(.021,.028,.021),'cloth',size=2048,metal=0,rough=.68)
    skin=library.texture_material('Anatomical warm skin',(.42,.25,.16),'skin',metal=0,rough=.58)
    cloth=library.texture_material('Tailored storm shell',(.041,.075,.065),'cloth',metal=0,rough=.79)
    sealmat=mat('Compact nitrile seals',(.012,.018,.014),.75);gold=mat('Optical anodised accent',(.24,.20,.10),.3,.75)
    glass=mat('Clear achromatic coated glass',(.65,.73,.73),.045,.02);p=glass.node_tree.nodes.get('Principled BSDF');p.inputs['Alpha'].default_value=.09;glass.diffuse_color=(.65,.73,.73,.09);glass.surface_render_method='DITHERED'
    glow=mat('Optical emission core',(.09,.56,.39),.23,.14,emission=(.10,.52,.33));white=mat('Calibrated printed markings',(.61,.67,.55),.54)
    parts=[];parts.append(turned('BalancedShortOpticalHousing',[(-.071,.026),(-.062,.031),(-.018,.033),(.030,.038),(.080,.041),(.116,.044),(.121,.043),(.121,.037),(.079,.036),(-.014,.026),(-.071,.022)],enamel,lamp,steps=14 if H else 4))
    turned('ParabolicReflector',[(.067,.012),(.073,.023),(.086,.030),(.109,.036)],metal,lamp,caps=False)
    for i in range(3):turned('OpticalLensLayer'+str(i),[(.096+i*.007,.035-i*.002),(.101+i*.007,.023),(.103+i*.007,.001)],glass,lamp,steps=14 if H else 4)
    turned('CoatedOpticalLens',[(.120,.039),(.125,.032),(.127,.011),(.1275,.001)],glass,lamp,steps=14 if H else 4)
    turned('OpticalEmitter',[(.070,.013),(.075,.013)],glow,lamp,sides=112 if H else 44)
    for y,r in [(-.041,.034),(.039,.039),(.110,.044)]:parts.append(seal('OpticalRetainingSeal',(0,y,0),r,.0014,metal,lamp))
    # Short grip directly below the optical / battery centre of mass.
    parts.append(turned('ShortErgonomicGrip',[(-.154,.017),(-.145,.018),(-.091,.017),(-.057,.017),(-.032,.017),(-.021,.015)],rubber,lamp,'Z',(0,-.005,0),steps=15 if H else 5))
    parts.append(sweep('TriggerGuard',[(0,-.004,-.025),(0,.042,-.029),(0,.051,-.053),(0,.032,-.076),(0,-.005,-.076)],[.0035]*5,metal,lamp,sides=56 if H else 24,steps=25 if H else 8))
    parts.append(box('TriggerBlade',(.010,.013,.018),(0,.029,-.052),gold,lamp,.003))
    parts.append(box('ModeSwitch',(.015,.010,.006),(.014,-.034,-.045),white,lamp,.003))
    # Battery is enclosed behind the grip, never three unsupported heavy cans.
    parts.append(box('BalancedBatteryPack',(.062,.072,.035),(0,-.043,-.016),enamel,lamp,.009))
    parts.append(box('SealedBatteryLid',(.003,.060,.027),(.034,-.043,-.016),metal,lamp,.004))
    for y in [-.066,-.023]:
        for z in [-.022,-.007]:parts.append(library.screw('BatteryCaptiveFastener',(.036,y,z),metal,lamp,'X',.0025))
    for angle in range(48):
        a=angle*math.tau/48;parts.append(sweep('FocusCollarKnurl',[(.042*math.cos(a),.081,.042*math.sin(a)),(.043*math.cos(a+.02),.106,.043*math.sin(a+.02))],[.0008]*2,metal,lamp,sides=10 if H else 5,steps=14 if H else 4))
    # Lengthen the optics before merging, leaving guard, grip and battery exact.
    optics=('BalancedShortOpticalHousing','ParabolicReflector','OpticalLensLayer','CoatedOpticalLens','OpticalEmitter','OpticalRetainingSeal','FocusCollarKnurl')
    for part in lamp.children_recursive:
        if part.type == 'MESH' and part.name.startswith(optics):
            for vertex in part.data.vertices:
                if vertex.co.y > .030:vertex.co.y += .035*min(1,(vertex.co.y-.030)/.040)
    join('IntegratedEngineeringStructure',parts,lamp)
    sensor=empty('SensorModules',lamp);box('SensorHousing',(.023,.035,.011),(.020,-.015,.032),enamel,sensor,.004);box('SensorScreen',(.017,.025,.0015),(.020,-.015,.038),glow,sensor,.001)
    label('IdentificationPlate','SPECTRA 03',(0,-.080,-.013),.0068,white,lamp,(math.pi/2,0,0))
    props=empty('SkillTools',root)
    for key in ['ToolLuminol','ToolSalt','ToolMud']:empty(key,props)
    reagent=bpy.data.objects['ToolLuminol'];turned('ReagentBottle',[(0,.018),(.008,.021),(.060,.021),(.079,.016),(.095,.011)],glass,reagent,'Z');turned('DropperCap',[(.087,.013),(.097,.014),(.109,.008)],rubber,reagent,'Z')
    fluid=mat('Dilute luminol blue reagent',(.04,.14,.27),.20,.02);turned('ContainedReagent',[(.007,.017),(.057,.017)],fluid,reagent,'Z')
    salt=bpy.data.objects['ToolSalt'];box('SaltPouch',(.041,.023,.069),(0,0,.034),white,salt,.008);label('SaltMark','NaCl',(0,-.012,.052),.008,gold,salt,(math.pi/2,0,0))
    for x in [-.018,.018]:sweep('PouchWeldSeam',[(x,-.009,.006),(x,-.013,.034),(x,-.009,.064)],[.0008]*3,gold,salt,sides=10 if H else 6,steps=18 if H else 6)
    box('PouchPressSeal',(.035,.004,.004),(0,0,.066),gold,salt,.001)
    mud=bpy.data.objects['ToolMud'];turned('FieldMudCanister',[(0,.024),(.070,.024),(.075,.022)],enamel,mud,'Z');turned('SecureSampleLid',[(.070,.026),(.079,.026)],metal,mud,'Z')
    for z in [.008,.017,.056,.065]:seal('ContainerGripRib',(0,0,z),.024,.0012,rubber,mud,'Z')
    label('SampleCanisterLabel','MIRE / 03',(0,-.024,.038),.0055,white,mud,(math.pi/2,0,0))
    hand_module=types.ModuleType('mature_hand')
    exec(compile(Path(__file__).with_name('makehuman_hand.py').read_text(),str(Path(__file__).with_name('makehuman_hand.py')),'exec'),hand_module.__dict__)
    hand_module.build_hand(library,'RightGrip',False,skin,cloth,root,H)
    hand_module.build_hand(library,'LeftSupport',True,skin,cloth,root,H)
    root['beam_socket_source_y']=.163
    root['quality_status']='anatomy and engineered-grip prototype; requires native visual acceptance'
    return root

if __name__=='__main__':
    H=True;library.HI=True;compact_equipment();library.save_master('field_equipment')
    H=False;library.HI=False;compact_equipment();library.save_runtime('field_equipment',rest_position_armature=False)
    manifest_path=SOURCE/'COMMERCIAL_MODEL_MANIFEST.json'
    manifest=json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    manifest.update({'quality_status':'candidate pending visual acceptance','tool':'Blender 4.5 LTS','original_maps':True})
    manifest.setdefault('assets',{}).update(library.COUNTS)
    manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
