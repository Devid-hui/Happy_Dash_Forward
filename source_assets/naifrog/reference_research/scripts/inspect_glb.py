"""Inventory glTF JSON chunk; does not imply visual or engine acceptance."""
from pathlib import Path
import struct
import json
import hashlib
import sys

p=Path(sys.argv[1]); d=p.read_bytes()
magic,version,length=struct.unpack_from('<4sII',d)
n,kind=struct.unpack_from('<II',d,12)
assert magic==b'glTF' and version==2 and length==len(d) and kind==0x4E4F534A
r=json.loads(d[20:20+n])
out={'file':str(p),'bytes':len(d),'sha256':hashlib.sha256(d).hexdigest(),
     'header':{'magic':magic.decode(),'version':version,'declared_bytes':length},
     'skins':[{'name':s.get('name'),'joints':len(s['joints'])} for s in r.get('skins',[])],
     'meshes':[{'name':m.get('name'),'primitives':[
        {'attributes':q.get('attributes'),'indices_count':r['accessors'][q['indices']]['count'],
         'vertex_count':r['accessors'][q['attributes']['POSITION']]['count']}
        for q in m['primitives']]} for m in r.get('meshes',[])],
     'animations':[{'name':a.get('name'),'channels':len(a['channels']),
                    'samplers':len(a['samplers']),
                    'duration_seconds':max((r['accessors'][s['input']].get('max',[0])[0]
                        for s in a['samplers']),default=0)} for a in r.get('animations',[])],
     'images':[{'name':i.get('name'),'mimeType':i.get('mimeType'),
                 'embedded':'bufferView' in i} for i in r.get('images',[])],
     'materials':[{'name':m.get('name'),'fields':list(m)} for m in r.get('materials',[])]}
Path(sys.argv[2]).write_text(json.dumps(out,indent=2))
print(json.dumps(out,indent=2))
