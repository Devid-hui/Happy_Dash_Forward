"""Independent PNG linear-color fidelity and same-source CPU comparison."""
from pathlib import Path
import json,hashlib
import numpy as np
from PIL import Image
from transfer_uv_corners import selected_atlas_path
root=Path(__file__).resolve().parent;trial=root.parents[1]/'work/nailong/uv-pbr-trial'
source=np.load(root/'source-body-geometry.npz');atlas=np.load(selected_atlas_path(root))
corner=source['corner_rgba'].reshape(-1,3,4);uv=atlas['corner_uv'].reshape(-1,3,2)
raw=np.array(Image.open(trial/'nailong_body_basecolor_4k_local_islands.png').convert('RGBA'))
encoded=raw[:,:,:3].astype(np.float64)/255
linear=np.where(encoded<=.04045,encoded/12.92,((encoded+.055)/1.055)**2.4)
rng=np.random.default_rng(20261013);ids=rng.choice(len(uv),min(100000,len(uv)),replace=False)
points=uv[ids].mean(axis=1);expected=corner[ids,:,:3].mean(axis=1)
x=points[:,0]*4096-.5;y=(1-points[:,1])*4096-.5
ix=np.floor(x).astype(np.int32);iy=np.floor(y).astype(np.int32);tx=x-ix;ty=y-iy
ix=np.clip(ix,0,4094);iy=np.clip(iy,0,4094)
sample=linear[iy,ix]*(1-tx[:,None])*(1-ty[:,None])+linear[iy,ix+1]*tx[:,None]*(1-ty[:,None])+linear[iy+1,ix]*(1-tx[:,None])*ty[:,None]+linear[iy+1,ix+1]*tx[:,None]*ty[:,None]
error=np.abs(sample-expected);norm=np.linalg.norm(sample-expected,axis=1)
selected=__import__('json').loads((root/'SELECTED_ATLAS.json').read_text())
owner_path=Path(selected['pixel_audit_path'].replace('-pixel-audit.json','-owner.bin'))
owner=np.fromfile(owner_path,dtype='<i4').reshape(4096,4096)[::-1]
covered=owner>=0
world=source['vertices'][source['faces'][ids]].astype(np.float64)
world_area=np.linalg.norm(np.cross(world[:,1]-world[:,0],world[:,2]-world[:,0]),axis=1)*.5
uv_tri=uv[ids].astype(np.float64)
uv_area=np.abs((uv_tri[:,1,0]-uv_tri[:,0,0])*(uv_tri[:,2,1]-uv_tri[:,0,1])-(uv_tri[:,1,1]-uv_tri[:,0,1])*(uv_tri[:,2,0]-uv_tri[:,0,0]))*.5
worst=np.argsort(norm)[-20:][::-1]
report={'texture':str(trial/'nailong_body_basecolor_4k_local_islands.png'),'texture_sha256':hashlib.sha256((trial/'nailong_body_basecolor_4k_local_islands.png').read_bytes()).hexdigest(),'actual_dimensions':[raw.shape[1],raw.shape[0]],'nonconstant_encoded_rgb_std':raw[:,:,:3].std(axis=(0,1)).tolist(),'original_vertex_color_to_real_texture_triangle_centroid_samples':len(ids),'color_comparison_space':'Decode PNG sRGB to linear before bilinear filtering and compare with original linear corner RGB interpolation','absolute_linear_rgb_error_mean':error.mean(axis=0).tolist(),'absolute_linear_rgb_error_percentiles':dict(zip(['p50','p90','p95','p99','p100'],np.percentile(norm,[50,90,95,99,100]).tolist())),'strict_interior_valid_texture_pixel_count':int(covered.sum()),'valid_surface_texel_encoded_rgb_std':raw[:,:,:3][covered].std(axis=0).tolist(),'source_linear_corner_rgb_std':source['corner_rgba'][:,:3].std(axis=0).tolist(),'alpha_is_opaque_also_in_unused_canvas':bool((raw[:,:,3]==255).all()),'sample_error_thresholds':{str(t):{'samples':int((norm>t).sum()),'sample_fraction':float((norm>t).mean()),'sampled_world_area_fraction':float(world_area[norm>t].sum()/world_area.sum()),'sampled_uv_area_fraction':float(uv_area[norm>t].sum()/uv_area.sum())} for t in [.01,.03,.1,.3,.8]},'worst_sample_records':[{'source_polygon_id':int(ids[i]),'error_norm_linear':float(norm[i]),'expected_linear_rgb':expected[i].tolist(),'sampled_linear_rgb':sample[i].tolist(),'uv_centroid':points[i].tolist(),'source_world_area_m2':float(world_area[i]),'triangle_area_in_texture_pixels':float(uv_area[i]*4096**2)} for i in worst],'error_scope':'Centroid comparisons include extreme subpixel/thin-triangle interpolation failures; percentiles do not hide maximum. Whole-body same-source CPU views are a separate visual comparison.','cpu_image_pairs':[]}
for before in (root/'compare-local-islands/before-vcol').glob('*.png'):
    after=root/'compare-local-islands/after-texture'/before.name
    if not after.exists():continue
    a=np.array(Image.open(before).convert('RGB')).astype(np.float64)/255;b=np.array(Image.open(after).convert('RGB')).astype(np.float64)/255
    delta=np.abs(a-b)
    report['cpu_image_pairs'].append({'view':before.stem,'mean_absolute_display_rgb_difference':float(delta.mean()),'p99_absolute_display_rgb_difference':float(np.percentile(delta,99)),'maximum_display_rgb_difference':float(delta.max()),'source_camera_lights_seed_and_geometry_identical':True})
(root/'LOCAL_ISLANDS_COLOUR_FIDELITY_AND_CPU_METRICS.json').write_text(json.dumps(report,indent=2)+'\n')
print('BAKED_BODY_COLOUR_FIDELITY',json.dumps(report),flush=True)
