"""MIT xatlas unwrap; preserve original body vertex/face correspondence."""
from pathlib import Path
import time,json,hashlib,importlib.metadata
import numpy as np,xatlas
from PIL import Image
root=Path(__file__).resolve().parent
data=np.load(root/'source-body-geometry.npz');vertices=data['vertices'];faces=data['faces'].astype(np.uint32)
started=time.time();atlas=xatlas.Atlas()
print('XATLAS_ACTUAL_INPUT',vertices.shape,faces.shape,flush=True)
atlas.add_mesh(vertices,faces)
chart=xatlas.ChartOptions();chart.max_iterations=1;chart.fix_winding=True
pack=xatlas.PackOptions();pack.resolution=4096;pack.padding=16;pack.bilinear=True;pack.blockAlign=True;pack.create_image=True
atlas.generate(chart_options=chart,pack_options=pack,verbose=True)
mapping,indices,uv=atlas[0]
if not np.array_equal(mapping[indices],faces):raise RuntimeError('Atlas changed original face/corner ordering')
corner_uv=uv[indices].reshape(-1,2)
assignments,chart_ids=atlas.get_mesh_vertex_assignment(0)
face_chart=chart_ids[indices[:,0]]
image=np.asarray(atlas.chart_image,dtype=np.uint8)
np.savez(root/'body-atlas.npz',corner_uv=corner_uv,source_vertex_index=mapping,uv_vertex_indices=indices,uv_vertex_coordinates=uv,face_chart=face_chart,chart_image=image)
tri=corner_uv.reshape(-1,3,2);cross=(tri[:,1,0]-tri[:,0,0])*(tri[:,2,1]-tri[:,0,1])-(tri[:,1,1]-tri[:,0,1])*(tri[:,2,0]-tri[:,0,0])
world=vertices[faces];area3=np.linalg.norm(np.cross(world[:,1]-world[:,0],world[:,2]-world[:,0]),axis=1)*.5
area2=np.abs(cross)*.5;valid=(area3>1e-16)&(area2>1e-16)
density=np.sqrt(area2[valid]/area3[valid])*4096
folds=0
for chart_id in np.unique(face_chart):
    values=cross[face_chart==chart_id];nonzero=values[np.abs(values)>1e-16]
    if len(nonzero):folds+=int(min((nonzero>0).sum(),(nonzero<0).sum()))
inside=np.any(image!=0,axis=2)
Image.fromarray(image).save(root/'body-uv-chart-layout.png')
report={'algorithm':'xatlas 0.0.11 MIT, actual parameterization plus packing','input_vertices':len(vertices),'input_triangles':len(faces),'original_face_and_corner_mapping_exact':True,'atlas_width':atlas.width,'atlas_height':atlas.height,'atlas_count':atlas.atlas_count,'charts':atlas.get_mesh_chart_count(0),'atlas_reported_utilization':atlas.utilization,'corner_uv_finite':bool(np.isfinite(corner_uv).all()),'uv_min':corner_uv.min(axis=0).tolist(),'uv_max':corner_uv.max(axis=0).tolist(),'uv_degenerate_triangles':int((area2<=1e-16).sum()),'source_geometric_degenerate_triangles':int((area3<=1e-16).sum()),'intra_chart_inconsistent_winding_triangles':folds,'normalized_triangle_uv_area_sum':float(area2.sum()),'surface_area_m2':float(area3.sum()),'texel_density_pixels_per_meter_percentiles':dict(zip(['p0','p1','p5','p50','p95','p99','p100'],np.percentile(density,[0,1,5,50,95,99,100]).tolist())),'raster_chart_marked_pixels':int(inside.sum()),'raster_chart_coverage_fraction':float(inside.mean()),'pack_padding_pixels':pack.padding,'elapsed_seconds':time.time()-started,'binding_version':importlib.metadata.version('xatlas'),'overlap_scope':'Packing occupancy and chart winding are measured; independent triangle overlap audit follows, not inferred from the library claim.'}
(root/'ATLAS_METRICS.json').write_text(json.dumps(report,indent=2)+'\n');print('BODY_UV_ATLAS_GENERATED',json.dumps(report),flush=True)
