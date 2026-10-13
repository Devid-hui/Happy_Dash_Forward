"""Repair only measured failing face UVs; keep all other corner UV bits exact."""
from pathlib import Path
import numpy as np,json,hashlib
root=Path(__file__).resolve().parent;base=root/'repacked-native-scale-7000-atlas.npz'
a=np.load(base);source=np.load(root/'source-body-geometry.npz');failure=np.load(root/'full-body-centroid-colour-audit.npz')
bad=failure['source_polygon_ids_requiring_uv_repair'];assert len(bad)==183
vertices=source['vertices'].astype(np.float64);faces=source['faces'];original=a['corner_uv'].reshape(-1,3,2)
assert float(original[:,:,0].max()*4096)<3572
uv=a['uv_vertex_coordinates'].copy();indices=a['uv_vertex_indices'].copy();mapping=a['source_vertex_index'].copy();chart=a['face_chart'].copy()
new_uv=[];new_mapping=[];records=[];base_chart=int(chart.max())
for ordinal,face_id in enumerate(bad):
    vids=faces[face_id];p=vertices[vids]
    order=max([(0,1,2),(1,2,0),(2,0,1)],key=lambda t:np.linalg.norm(p[t[1]]-p[t[0]]));v0,v1,v2=order
    edge=p[v1]-p[v0];length=np.linalg.norm(edge);axis=edge/length;normal=np.cross(edge,p[v2]-p[v0]);normal/=np.linalg.norm(normal);vertical=np.cross(normal,axis)
    x=(p[v2]-p[v0])@axis;height=(p[v2]-p[v0])@vertical;assert height>0
    width=min(64.,max(8.,4.*length/height));origin=np.array([3600+(ordinal%6)*72+.125,8+(ordinal//6)*12+.125])
    coords=np.empty((3,2));coords[v0]=origin;coords[v1]=origin+[width,0];coords[v2]=origin+[x/length*width,4.]
    assert coords[:,0].min()>3599 and coords[:,0].max()<4090 and coords[:,1].min()>0 and coords[:,1].max()<4090
    new_uv.append((coords/4096).astype(np.float32));new_mapping.extend(vids.tolist());indices[face_id]=len(uv)+ordinal*3+np.arange(3,dtype=np.uint32);chart[face_id]=base_chart+1+ordinal
    records.append({'source_polygon_id':int(face_id),'previous_measured_error':float(failure['error'][face_id]),'pixel_origin':origin.tolist(),'pixel_width':width,'pixel_height':4.,'scope':'Real triangle-plane coordinates with explicit raster-support span; source geometry/colour unchanged'})
uv=np.concatenate([uv,np.concatenate(new_uv)]);mapping=np.concatenate([mapping,np.asarray(new_mapping,dtype=np.uint32)]);corners=uv[indices].reshape(-1,2);assert np.array_equal(mapping[indices],faces)
other=np.ones(len(faces),dtype=bool);other[bad]=False;assert np.array_equal(corners.reshape(-1,3,2)[other],original[other])
t=corners.reshape(-1,3,2).astype(np.float64);area=np.abs((t[:,1,0]-t[:,0,0])*(t[:,2,1]-t[:,0,1])-(t[:,1,1]-t[:,0,1])*(t[:,2,0]-t[:,0,0]))*.5;assert bool((area>1e-16).all())
np.savez(root/'colour-island-local-atlas.npz',corner_uv=corners,source_vertex_index=mapping,uv_vertex_indices=indices,uv_vertex_coordinates=uv,face_chart=chart)
corners.astype('<f4').tofile(root/'colour-island-local-corners.bin')
report={'source_c3_sha256':'c3f08b4b01489b5cc548aac7f23717338d24819fbb0e514706d59986bfa6be8c','base_atlas_sha256':hashlib.sha256(base.read_bytes()).hexdigest(),'atlas_dimensions':[4096,4096],'atlas_count':1,'actual_source_face_and_corner_mapping_exact':True,'repaired_measured_faces':len(bad),'all_other_1803970_triangle_uv_corners_bit_exact':True,'geometry_original_colour_basis_open_focus_weights_changed':False,'uv_degenerate_triangles':0,'actual_triangle_uv_area_fraction':float(area.sum()),'unused_strip_verified_from_actual_max_u_pixels':float(original[:,:,0].max()*4096),'new_islands_min_u_pixels':3600.125,'tile_spacing_pixels':[72,12],'reserved_span':[8,64,4],'repairs':records,'scope':'Direct UV-only patches in actually empty right canvas. No global repack, and no other face UV is shifted. Needs independent overlap+realbake+all-centroid and same-source visual checks.'}
(root/'colour-island-local-metrics.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({k:v for k,v in report.items() if k!='repairs'},indent=2))
