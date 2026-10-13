import bpy
import sys
import json
import importlib.util
import numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform

out=Path(sys.argv[sys.argv.index('--')+1])
spec=importlib.util.spec_from_file_location('nfbuild','/Users/lpz/Documents/Happy_Dash_Forward/tools/build_naifrog_asset.py')
nf=importlib.util.module_from_spec(spec);spec.loader.exec_module(nf)
o=bpy.data.objects['NaifrogContinuousSkin'];mesh=o.data;mesh.calc_loop_triangles()
positions=nf.array_coords(mesh)
triangles=np.empty(len(mesh.loop_triangles)*3,np.int32);mesh.loop_triangles.foreach_get('vertices',triangles);triangles=triangles.reshape(-1,3)
loops=np.empty(len(mesh.loop_triangles)*3,np.int32);mesh.loop_triangles.foreach_get('loops',loops);loops=loops.reshape(-1,3)
uv=np.empty(len(mesh.uv_layers.active.data)*2,np.float32);mesh.uv_layers.active.data.foreach_get('uv',uv);uv=uv.reshape(-1,2)
uvtri=uv[loops]
tree=BVHTree.FromPolygons([tuple(c) for c in positions],[tuple(t) for t in triangles],all_triangles=True)
attr=mesh.attributes['NaiFrogOralWeight'];oral=np.empty(len(positions),np.float32);attr.data.foreach_get('value',oral)
regions=np.empty(len(mesh.polygons),np.int32);mesh.attributes['NaiFrogFacialPatch'].data.foreach_get('value',regions)
uvregions=np.empty(len(mesh.polygons),np.int32)
layer=mesh.attributes.get('NaiFrogUVRegion')
if layer:layer.data.foreach_get('value',uvregions)
else:uvregions[:]=0
poly=np.empty(len(mesh.loop_triangles),np.int32);mesh.loop_triangles.foreach_get('polygon_index',poly)
material=mesh.materials[0];base=material.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].links[0].from_node.image
pixels=np.empty(len(base.pixels),np.float32);base.pixels.foreach_get(pixels);pixels=pixels.reshape(base.size[1],base.size[0],4)
samples=[]
for x,z in [(-.08,2.38),(-.05,2.36),(0,2.36),(.04,2.38),(-.64,1.30),(-.68,1.34),(-.70,1.34),(.64,1.30),(.68,1.34),(.70,1.34),(0,1.49)]:
    hit,normal,index,distance=tree.ray_cast(Vector((x,3,z)),Vector((0,-1,0)),6)
    if hit is None:continue
    tri=triangles[index];p=positions[tri]
    q=barycentric_transform(hit,*[Vector(v) for v in p],*[Vector((v[0],v[1],0)) for v in uvtri[index]])
    weights=barycentric_transform(hit,*[Vector(v) for v in p],Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1)))
    mask=float(np.dot(np.asarray(weights),oral[tri]));color=nf.color_field(np.array([list(hit)]))[0]
    desired=color[:3]*(1-mask)+np.array([.024,.009,.007])*mask
    desired_srgb=np.where(desired<=.0031308,desired*12.92,1.055*np.maximum(desired,0)**(1/2.4)-.055)
    tx=min(base.size[0]-1,max(0,round(q.x*(base.size[0]-1))));ty=min(base.size[1]-1,max(0,round(q.y*(base.size[1]-1))))
    actual=pixels[ty,tx,:3]
    query=np.array([q.x,q.y]);candidate=np.flatnonzero(np.all(uvtri.min(axis=1)<=query+1e-8,axis=1)&np.all(uvtri.max(axis=1)>=query-1e-8,axis=1))
    covers=[]
    for j in candidate:
        a,b,c=uvtri[j];ab=b-a;ac=c-a;d=query-a;den=ab[0]*ac[1]-ab[1]*ac[0]
        if abs(den)<1e-14:continue
        u=(d[0]*ac[1]-d[1]*ac[0])/den;v=(ab[0]*d[1]-ab[1]*d[0])/den
        if u>=-1e-6 and v>=-1e-6 and u+v<=1+1e-6:
            covers.append({'triangle':int(j),'polygon':int(poly[j]),'region':int(regions[poly[j]]),
                'uv_region':int(uvregions[poly[j]]),
                'world_center':positions[triangles[j]].mean(axis=0).tolist(),
                'oral_mean':float(oral[triangles[j]].mean())})
    samples.append({'surface_point':list(hit),'triangle':int(index),'region':int(regions[poly[index]]),
        'oral_mask':mask,'uv':[q.x,q.y],'sample_pixel':[tx,ty],
        'baked_pixel_rgb':actual.tolist(),'expected_linear_field_rgb':desired.tolist(),
        'expected_srgb':desired_srgb.tolist(),'rgb_max_abs_error':float(np.max(np.abs(actual-desired_srgb))),
        'UV_covering_triangles':covers})
report={'source':bpy.data.filepath,'image':base.name,'dimensions':list(base.size),'samples':samples}
out.write_text(json.dumps(report,indent=2));print('UV_SAMPLE_DIAGNOSED',str(out))
