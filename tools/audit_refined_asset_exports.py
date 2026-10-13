"""Canonical GLB geometry inventory; never equate export validity with visual acceptance."""
from pathlib import Path
import hashlib, json, struct, math, datetime

ROOT=Path(__file__).resolve().parents[1]

def glb_info(path):
    data=path.read_bytes();magic,version,length=struct.unpack_from('<4sII',data)
    assert magic==b'glTF' and version==2 and length==len(data),path
    offset=12;document=None;binary=None
    while offset<len(data):
        size,kind=struct.unpack_from('<II',data,offset);chunk=data[offset+8:offset+8+size];offset+=8+size
        if kind==0x4e4f534a:document=json.loads(chunk)
        elif kind==0x004e4942:binary=chunk
    assert document and binary is not None,path
    triangles=0;primitives=0;positions=0
    accessors=document.get('accessors',[])
    for mesh in document.get('meshes',[]):
        for primitive in mesh['primitives']:
            assert primitive.get('mode',4)==4,(path,'unexpected non-triangle primitive')
            primitives+=1
            if 'indices' in primitive:triangles+=accessors[primitive['indices']]['count']//3
            else:triangles+=accessors[primitive['attributes']['POSITION']]['count']//3
            acc=accessors[primitive['attributes']['POSITION']];positions+=acc['count']
            assert acc['componentType']==5126 and acc['type']=='VEC3',path
            view=document['bufferViews'][acc['bufferView']];start=view.get('byteOffset',0)+acc.get('byteOffset',0);stride=view.get('byteStride',12)
            for i in range(acc['count']):
                point=struct.unpack_from('<fff',binary,start+i*stride)
                assert all(math.isfinite(x) for x in point),(path,'nonfinite exported vertex',i)
    return {'runtime':str(path.relative_to(ROOT)),'triangles':triangles,'meshes':len(document.get('meshes',[])),
        'primitives':primitives,'exported_vertices':positions,'skins':len(document.get('skins',[])),
        'joints_per_skin':[len(s['joints']) for s in document.get('skins',[])],
        'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'finite_positions':True,
        'quality_status':'candidate pending native visual acceptance'}

def main():
    assets={str(p.relative_to(ROOT/'assets/refined')):glb_info(p) for p in sorted((ROOT/'assets/refined').rglob('*.glb'))}
    previous=json.loads((ROOT/'assets/refined/ASSET_MANIFEST.json').read_text())
    history=previous.get('history',[])
    if not history:
        history=[{'batch':'original medium detail','quality_status':'rejected by user; archived',
            'counts':{k:v['triangles'] for k,v in previous.get('assets',{}).items()},
            'recoverable_archive':'task work/stage2/rejected-medium-poly-backup'}]
    manifest={'generated_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'tool':'Blender 4.5 LTS; Godot native glTF importer',
        'count_method':'Sum index accessor counts / 3 for actual triangle primitives; source counts stored separately',
        'quality_status':'candidate pending native visual acceptance; contract or density is not artistic acceptance',
        'provenance':{'hands':'source_assets/reference_cc0/PROVENANCE.json','environment':'assets/refined/environment/ENVIRONMENT_MANIFEST.json',
            'nailong':'assets/refined/nailong/reference_candidate/ASSET_PROVENANCE.txt',
            'original_field_assets':'assets/refined/ASSET_LICENSE.txt'},'history':history,'assets':assets}
    (ROOT/'assets/refined/ASSET_MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
    source_path=ROOT/'source_assets/COMMERCIAL_MODEL_MANIFEST.json';source=json.loads(source_path.read_text())
    for name,entry in source.get('assets',{}).items():
        for suffix in ['', '_lod1','_lod2']:
            filename=name+suffix+'.glb'
            if filename in assets:
                entry['exported'+suffix+'_triangles']=assets[filename]['triangles'];entry['exported'+suffix+'_sha256']=assets[filename]['sha256']
    source['hand_provenance']='reference_cc0/PROVENANCE.json';source_path.write_text(json.dumps(source,indent=2)+'\n')
    print('CANONICAL_EXPORT_INVENTORY',len(assets),'GLBs; finite geometry; candidate visual status retained')
    for name in ['field_equipment.glb','field_equipment_lod1.glb','field_equipment_lod2.glb','abandoned_car.glb','power_tower.glb','research_report.glb']:
        print(name,assets[name]['triangles'],assets[name]['sha256'])

if __name__=='__main__':main()
