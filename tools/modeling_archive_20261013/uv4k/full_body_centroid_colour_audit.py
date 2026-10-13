"""Every actual body triangle centroid, not just a favourable percentile sample."""
from pathlib import Path
import numpy as np,json,hashlib,sys
from PIL import Image
from transfer_uv_corners import selected_atlas_path
root=Path(__file__).resolve().parent
texture=Path(sys.argv[1]);output=Path(sys.argv[2])
source=np.load(root/'source-body-geometry.npz');atlas_path=selected_atlas_path(root);atlas=np.load(atlas_path)
uv=atlas['corner_uv'].reshape(-1,3,2);col=source['corner_rgba'].reshape(-1,3,4)
raw=np.asarray(Image.open(texture).convert('RGB')).astype(np.float64)/255.
linear=np.where(raw<=.04045,raw/12.92,((raw+.055)/1.055)**2.4)
points=uv.mean(axis=1);expected=col[:,:,:3].mean(axis=1)
x=points[:,0]*4096-.5;y=(1-points[:,1])*4096-.5
ix=np.floor(x).astype(np.int32);iy=np.floor(y).astype(np.int32);tx=x-ix;ty=y-iy;ix=np.clip(ix,0,4094);iy=np.clip(iy,0,4094)
value=linear[iy,ix]*(1-tx[:,None])*(1-ty[:,None])+linear[iy,ix+1]*tx[:,None]*(1-ty[:,None])+linear[iy+1,ix]*(1-tx[:,None])*ty[:,None]+linear[iy+1,ix+1]*tx[:,None]*ty[:,None]
error=np.linalg.norm(value-expected,axis=1);worst=np.argsort(error)[-30:][::-1]
report={'texture':str(texture.resolve()),'texture_sha256':hashlib.sha256(texture.read_bytes()).hexdigest(),'atlas':str(atlas_path),'atlas_sha256':hashlib.sha256(atlas_path.read_bytes()).hexdigest(),'source_c3_sha256':'c3f08b4b01489b5cc548aac7f23717338d24819fbb0e514706d59986bfa6be8c','triangles_checked':len(error),'linear_rgb_error_norm_percentiles':dict(zip(['p50','p90','p95','p99','p999','p100'],np.percentile(error,[50,90,95,99,99.9,100]).tolist())),'above_001':int((error>.01).sum()),'above_003':int((error>.03).sum()),'above_01':int((error>.1).sum()),'maximum_error':float(error.max()),'worst_records':[{'source_polygon_id':int(i),'error_norm':float(error[i]),'expected_linear_rgb':expected[i].tolist(),'sampled_linear_rgb':value[i].tolist(),'uv_centroid':points[i].tolist()} for i in worst],'scope':'Every original c3 triangle centroid, sRGB PNG decoded to linear before bilinear filtering. This does not prove every continuous surface point or graphical Godot acceptance.'}
output.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='worst_records'},indent=2))
