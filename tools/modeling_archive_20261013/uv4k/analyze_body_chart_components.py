"""Read-only actual c3 component and original-atlas chart distributions."""
from pathlib import Path
import numpy as np,json,hashlib
root=Path(__file__).resolve().parent
s=np.load(root/'source-body-geometry.npz');a=np.load(root/'body-atlas.npz')
vertices=s['vertices'].astype(np.float64);faces=s['faces'];chart=a['face_chart']
component=np.fromfile(root/'body-components-per-vertex.bin',dtype='<u4')
face_component=component[faces[:,0]]
assert np.array_equal(face_component,component[faces[:,1]]) and np.array_equal(face_component,component[faces[:,2]])
points=vertices[faces];world_area=np.linalg.norm(np.cross(points[:,1]-points[:,0],points[:,2]-points[:,0]),axis=1)*.5
uv=a['corner_uv'].reshape(-1,3,2).astype(np.float64)
uv_area=np.abs((uv[:,1,0]-uv[:,0,0])*(uv[:,2,1]-uv[:,0,1])-(uv[:,1,1]-uv[:,0,1])*(uv[:,2,0]-uv[:,0,0]))*.5
def rows_for(ids):
    unique,inv=np.unique(ids,return_inverse=True)
    counts=np.bincount(inv);area3=np.bincount(inv,weights=world_area);area2=np.bincount(inv,weights=uv_area)
    low=np.full((len(unique),3),np.inf);high=np.full((len(unique),3),-np.inf)
    for corner in range(3):
        for axis in range(3):
            np.minimum.at(low[:,axis],inv,points[:,corner,axis]);np.maximum.at(high[:,axis],inv,points[:,corner,axis])
    return unique,inv,counts,area3,area2,low,high
comp,comp_inv,cnt,c3,c2,lo,hi=rows_for(face_component)
ch,ch_inv,tc,t3,t2,tl,th=rows_for(chart)
valid=ch!=np.uint32(4294967295)
statistics=lambda x:dict(zip(['p0','p1','p5','p50','p95','p99','p100'],np.percentile(x,[0,1,5,50,95,99,100]).tolist()))
def record(i,labels,counts,area3,area2,low,high):return {'id':int(labels[i]),'triangles':int(counts[i]),'world_area_m2':float(area3[i]),'uv_area_fraction':float(area2[i]),'bbox_min':low[i].tolist(),'bbox_max':high[i].tolist()}
component_order=np.argsort(c3)[::-1]
chart_component_pairs=np.unique(np.column_stack([chart[chart!=np.uint32(4294967295)],face_component[chart!=np.uint32(4294967295)]]),axis=0)
charts_per_component={int(k):int(v) for k,v in zip(*np.unique(chart_component_pairs[:,1],return_counts=True))}
report={'source_c3_sha256':'c3f08b4b01489b5cc548aac7f23717338d24819fbb0e514706d59986bfa6be8c','source_geometry_sha256':hashlib.sha256((root/'source-body-geometry.npz').read_bytes()).hexdigest(),'exact_topological_component_count':len(comp),'orphan_vertices':int((component==np.uint32(4294967295)).sum()),'component_triangle_count_percentiles':statistics(cnt),'component_area_m2_percentiles':statistics(c3),'component_counts_le_10_triangles':int((cnt<=10).sum()),'component_counts_le_100_triangles':int((cnt<=100).sum()),'component_total_surface_area_m2':float(c3.sum()),'largest_components':[dict(record(i,comp,cnt,c3,c2,lo,hi),chart_count=charts_per_component.get(int(comp[i]),0)) for i in component_order[:30]],'valid_charts':int(valid.sum()),'chart_triangle_count_percentiles':statistics(tc[valid]),'chart_world_area_m2_percentiles':statistics(t3[valid]),'chart_uv_area_fraction_percentiles':statistics(t2[valid]),'charts_le_10_triangles':int((tc[valid]<=10).sum()),'charts_le_100_triangles':int((tc[valid]<=100).sum()),'small_chart_world_area_fraction_le_10tri':float(t3[valid & (tc<=10)].sum()/world_area.sum()),'small_chart_world_area_fraction_le_100tri':float(t3[valid & (tc<=100)].sum()/world_area.sum()),'chart_component_association_count':len(chart_component_pairs),'charts_spanning_multiple_topological_components':int((np.unique(chart_component_pairs[:,0],return_counts=True)[1]>1).sum()),'largest_world_area_charts':[record(i,ch,tc,t3,t2,tl,th) for i in np.argsort(t3[valid])[-20:][::-1]],'scope':'Actual shared-vertex-index components and per-chart 3D/UV area. Bboxes and tiny-component sizes are measured; interior/exterior visibility is not inferred merely from chart count. No geometry, vertex colors, Basis/Open/Focus or weights were changed.'}
np.savez(root/'body-components-and-chart-distribution.npz',face_component=face_component,component_ids=comp,component_triangle_count=cnt,component_world_area=c3,component_uv_area=c2,component_bbox_min=lo,component_bbox_max=hi,chart_ids=ch,chart_triangle_count=tc,chart_world_area=t3,chart_uv_area=t2,chart_bbox_min=tl,chart_bbox_max=th)
(root/'BODY_COMPONENT_AND_CHART_AREA_REVIEW.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
