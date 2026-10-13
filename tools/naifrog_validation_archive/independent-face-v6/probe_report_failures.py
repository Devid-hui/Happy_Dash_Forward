"""Second algorithm: edge/plane intersection witnesses for reported source failures."""
import json
from pathlib import Path
import sys
import numpy as np
sys.path.insert(0,str(Path(__file__).parent))
import check_frozen_face as c

def bary(point,tri):
    # Project to the plane's dominant axes and solve independently of the crossing kernel.
    normal=np.cross(tri[1]-tri[0],tri[2]-tri[0])
    axes=[i for i in range(3) if i != int(np.argmax(np.abs(normal)))]
    matrix=np.stack([(tri[1]-tri[0])[axes],(tri[2]-tri[0])[axes]],axis=1)
    uv=np.linalg.solve(matrix,(point-tri[0])[axes])
    return [float(1-uv.sum()),float(uv[0]),float(uv[1])]

def hits(left,right):
    n=np.cross(right[1]-right[0],right[2]-right[0]);n=n/np.linalg.norm(n)
    result=[]
    for i in range(3):
        a,b=left[i],left[(i+1)%3]
        da,db=float((a-right[0])@n),float((b-right[0])@n)
        if da*db>=0 or abs(da-db)<1e-12:
            continue
        t=da/(da-db);p=a+(b-a)*t;weights=bary(p,right)
        if 1e-7<t<1-1e-7 and min(weights)>1e-7:
            result.append({'edge':i,'edge_parameter':t,'point_global_gltf_m':p.tolist(),'opposite_triangle_barycentric':weights})
    return result

args=sys.argv[sys.argv.index('--')+1:]
report=json.loads(Path(args[0]).read_text())
state=next(s for s in report['SOURCE']['states'] if s['strict_intersections'])
body=next(obj for name,obj in c.read_source().items() if name.startswith('NaifrogContinuousSkin'))
vertices=body['basis'].copy()
for key,value in state['values'].items():
    vertices+=body['morphs'][key]*value
result={'source':report['source'],'source_sha256':c.sha(report['source']),'state':state['values'],'witnesses':[]}
for failure in state['intersection_examples'][:10]:
    a,b=failure['face_a'],failure['face_b']
    ta,tb=vertices[body['faces'][a]],vertices[body['faces'][b]]
    ab,ba=hits(ta,tb),hits(tb,ta)
    result['witnesses'].append({**failure,'source_polygon_a':int(body['source_polygon_ids'][a]),'source_polygon_b':int(body['source_polygon_ids'][b]),
                              'vertices_a':body['faces'][a].tolist(),'vertices_b':body['faces'][b].tolist(),
                              'A_edge_strictly_pierces_B':ab,'B_edge_strictly_pierces_A':ba,
                              'proper_crossing_edge_witness_count':len(ab)+len(ba)})
result['all_probed_pairs_have_two_or_more_strict_edge_plane_witnesses']=all(w['proper_crossing_edge_witness_count']>=2 for w in result['witnesses'])
Path(args[1]).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'output':args[1],'witness_pairs':len(result['witnesses']),'independent_edge_plane_confirmation':result['all_probed_pairs_have_two_or_more_strict_edge_plane_witnesses']}))
