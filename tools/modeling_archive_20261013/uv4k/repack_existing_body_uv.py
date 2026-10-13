"""Reuse actual xatlas charts; UV-only planar repair of 11 unassigned faces."""
from pathlib import Path
import numpy as np,xatlas,json,time,hashlib,sys
from PIL import Image
root=Path(__file__).resolve().parent;density=float(sys.argv[1]) if len(sys.argv)>1 else 8500.0
name='repacked-native-scale-'+str(int(density));started=time.time()
s=np.load(root/'source-body-geometry.npz');a=np.load(root/'body-atlas.npz')
source_vertices=s['vertices'].astype(np.float64);source_faces=s['faces']
uv=a['uv_vertex_coordinates'].copy();indices=a['uv_vertex_indices'].copy();mapping=a['source_vertex_index'].copy();materials=a['face_chart'].copy()
tri=uv[indices].astype(np.float64);cross=(tri[:,1,0]-tri[:,0,0])*(tri[:,2,1]-tri[:,0,1])-(tri[:,1,1]-tri[:,0,1])*(tri[:,2,0]-tri[:,0,0])
degenerate=np.flatnonzero(np.abs(cross)<=1e-16);assert len(degenerate)==11
new_uv=[];new_mapping=[];repairs=[];max_chart=int(materials[materials!=np.uint32(4294967295)].max())
for ordinal,face_id in enumerate(degenerate):
    vertex_ids=source_faces[face_id];p=source_vertices[vertex_ids];edge=p[1]-p[0];length=np.linalg.norm(edge);axis=edge/length
    normal=np.cross(edge,p[2]-p[0]);normal/=np.linalg.norm(normal);axis_v=np.cross(normal,axis)
    planar=np.array([[0.,0.],[length,0.],[(p[2]-p[0])@axis,(p[2]-p[0])@axis_v]])
    area=abs(planar[1,0]*planar[2,1]-planar[1,1]*planar[2,0])*.5;assert area>0
    # Uniformly scale the actual triangle's unfolded shape; reserve sufficient
    # pixels for this otherwise unassigned microtriangle, without a fake square.
    scale=np.sqrt(1e-6/area);coordinates=(planar*scale).astype(np.float32)
    base=len(uv)+len(new_uv)*3;indices[face_id]=base+np.arange(3,dtype=np.uint32)
    new_uv.append(coordinates);new_mapping.extend(vertex_ids.tolist());materials[face_id]=max_chart+1+ordinal
    repairs.append({'source_polygon_id':int(face_id),'source_vertex_ids':vertex_ids.tolist(),'world_area_m2':float(area),'unpacked_uniform_scale':float(scale),'new_unpacked_uv_area':1e-6,'scope':'UV-only individual actual-triangle planar unfolding; no source geometry change'})
uv=np.concatenate([uv,np.concatenate(new_uv)],axis=0);mapping=np.concatenate([mapping,np.array(new_mapping,dtype=np.uint32)])
assert np.array_equal(mapping[indices],source_faces)
# AddUvMesh tests each input UV triangle against absolute FLT_EPSILON area
# (vendor f700c779 xatlas.cpp:9343). Normalized dense 0..1 UVs would therefore
# cause valid source faces to be ignored. A power-of-two units conversion is
# exact for float32 and changes no parameterization, seam, index or geometry.
input_units_scale=16384.0
uv*=np.float32(input_units_scale)
scaled_tri=uv[indices].astype(np.float64)
scaled_area=np.abs((scaled_tri[:,1,0]-scaled_tri[:,0,0])*(scaled_tri[:,2,1]-scaled_tri[:,0,1])-(scaled_tri[:,1,1]-scaled_tri[:,0,1])*(scaled_tri[:,2,0]-scaled_tri[:,0,0]))*.5
assert bool((scaled_area>np.finfo(np.float32).eps).all())
atlas=xatlas.Atlas();atlas.add_uv_mesh(uv,indices,materials[:,None])
pack=xatlas.PackOptions();pack.resolution=4096;pack.texels_per_unit=density/input_units_scale;pack.padding=2;pack.bilinear=True;pack.blockAlign=False;pack.create_image=True
print('EXISTING_CHART_REPACK_BEGIN',name,'preserved_source_faces',len(source_faces),flush=True)
atlas.generate(pack_options=pack,verbose=True)
second_map,second_indices,result=atlas[0];original_map=mapping[second_map]
assert np.array_equal(original_map[second_indices],source_faces)
corner_uv=result[second_indices].reshape(-1,2);assignment,chart_ids=atlas.get_mesh_vertex_assignment(0);face_chart=chart_ids[second_indices[:,0]]
t=corner_uv.reshape(-1,3,2).astype(np.float64);det=(t[:,1,0]-t[:,0,0])*(t[:,2,1]-t[:,0,1])-(t[:,1,1]-t[:,0,1])*(t[:,2,0]-t[:,0,0]);area2=np.abs(det)*.5
world=source_vertices[source_faces];area3=np.linalg.norm(np.cross(world[:,1]-world[:,0],world[:,2]-world[:,0]),axis=1)*.5
valid=area2>1e-16;texel=np.sqrt(area2[valid]/area3[valid])*4096
report={'source_c3_sha256':'c3f08b4b01489b5cc548aac7f23717338d24819fbb0e514706d59986bfa6be8c','original_atlas_sha256':hashlib.sha256((root/'body-atlas.npz').read_bytes()).hexdigest(),'operation':'ExistingUV chart repack, not repeated 3D ComputeCharts; 11 actual planar microtriangle UV repairs','atlas_dimensions':[atlas.width,atlas.height],'atlas_count':atlas.atlas_count,'charts':atlas.chart_count,'requested_texels_per_original_normalized_uv_unit':density,'input_uv_units_scale_exact_power_of_two':input_units_scale,'input_area_below_vendor_flt_epsilon_after_units_conversion':int((scaled_area<=np.finfo(np.float32).eps).sum()),'actual_texels_per_uv_unit':atlas.texels_per_unit,'actual_padding_pixels':2,'bilinear_guard':True,'original_face_corner_mapping_exact':True,'source_geometry_or_vertex_color_changed':False,'corner_uv_finite':bool(np.isfinite(corner_uv).all()),'uv_min':corner_uv.min(axis=0).tolist(),'uv_max':corner_uv.max(axis=0).tolist(),'uv_degenerate_triangles':int((area2<=1e-16).sum()),'unassigned_face_charts':int((face_chart==np.uint32(4294967295)).sum()),'normalized_actual_triangle_uv_area_sum':float(area2.sum()),'source_surface_area_m2':float(area3.sum()),'texel_density_pixels_per_meter_percentiles':dict(zip(['p0','p1','p5','p50','p95','p99','p100'],np.percentile(texel,[0,1,5,50,95,99,100]).tolist())),'elapsed_seconds':time.time()-started,'repairs':repairs,'scope':'True4096 pack dimensions and one-sheet policy are checked, but must pass independent4K overlap audit and actual bake/color/render tests before selection.'}
(root/(name+'-metrics.json')).write_text(json.dumps(report,indent=2)+'\n')
if atlas.atlas_count==1:
    assert atlas.width==atlas.height==4096
    np.savez(root/(name+'-atlas.npz'),corner_uv=corner_uv,source_vertex_index=original_map,uv_vertex_indices=second_indices,uv_vertex_coordinates=result,face_chart=face_chart)
    Image.fromarray(np.asarray(atlas.chart_image,dtype=np.uint8)).save(root/(name+'-layout.png'))
    corner_uv.astype('<f4').tofile(root/(name+'-corners.bin'))
print('EXISTING_CHART_REPACK_COMPLETE',json.dumps(report),flush=True)
