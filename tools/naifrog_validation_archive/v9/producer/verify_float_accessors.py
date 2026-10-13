"""Read every FLOAT glTF accessor, including matrices, and verify finite data."""
import pathlib
import importlib.util
import math
import json
import struct
import sys

sys.dont_write_bytecode=True
script=pathlib.Path('/Users/lpz/Documents/Happy_Dash_Forward/tools/naifrog_inspect.py')
spec=importlib.util.spec_from_file_location('naifrog_read',script)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
results=[]
for path in sorted(pathlib.Path(sys.argv[1]).glob('naifrog_lod*.glb')):
    document,binary,sha=module._read_glb(path);checks=[]
    for index,accessor in enumerate(document['accessors']):
        if accessor['componentType']!=5126:continue
        if accessor['type']=='MAT4':
            assert 'sparse' not in accessor
            view=document['bufferViews'][accessor['bufferView']]
            offset=view.get('byteOffset',0)+accessor.get('byteOffset',0);stride=view.get('byteStride',64)
            values=[struct.unpack_from('<16f',binary,offset+row*stride) for row in range(accessor['count'])]
        else:values=module._accessor(document,binary,index)
        bad=sum(not math.isfinite(value) for row in values for value in row)
        checks.append({'index':index,'type':accessor['type'],'count':accessor['count'],'nonfinite':bad})
    results.append({'file':str(path.resolve()),'sha256':sha,'float_accessors':len(checks),
        'nonfinite_total':sum(item['nonfinite'] for item in checks),
        'failed_accessors':[item for item in checks if item['nonfinite']],
        'COLOR_0_present':any('COLOR_0' in primitive['attributes'] for mesh in document['meshes'] for primitive in mesh['primitives'])})
pathlib.Path(sys.argv[2]).write_text(json.dumps(results,indent=2))
print(json.dumps(results))
if len(results)!=3 or any(item['nonfinite_total'] or item['COLOR_0_present'] for item in results):raise SystemExit(1)
