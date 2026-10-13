"""Read-only LBS evaluation of the real neutral thumb pad and nail surface."""
import numpy as np


class ThumbSkinFit:
    def __init__(self,obj,rig,name,dorsal):
        mesh=obj.data;bone=rig.data.bones[name+'Thumb3'];head=np.asarray(bone.head_local);axis=np.asarray(bone.tail_local)-head;length=float(np.linalg.norm(axis));axis/=length
        coordinates=np.asarray([list(v.co)+[1.] for v in mesh.vertices]);normal=np.asarray([list(v.normal) for v in mesh.vertices]);dorsal=np.asarray(dorsal)
        groups={g.index:g.name for g in obj.vertex_groups};thumb_groups={i for i,n in groups.items() if 'Thumb' in n};distal=obj.vertex_groups[name+'Thumb3'].index
        thumb=np.asarray([sum(g.weight for g in v.groups if g.group in thumb_groups) for v in mesh.vertices]);distal_weight=np.asarray([sum(g.weight for g in v.groups if g.group==distal) for v in mesh.vertices]);t=np.sum((coordinates[:,:3]-head)*axis,axis=1)/length
        pads=np.flatnonzero((distal_weight>.45)&(t>.32)&(t<.80)&(np.sum(normal*dorsal,axis=1)<-.80));assert len(pads)>20
        skin_ids=np.flatnonzero(thumb>.5)[::48]
        polygons={p.index for p in mesh.polygons if 'keratin' in mesh.materials[p.material_index].name and all(thumb[i]>.5 for i in p.vertices)};mesh.calc_loop_triangles();triangles=[list(tri.vertices) for tri in mesh.loop_triangles if tri.polygon_index in polygons];assert triangles
        nail_ids=sorted({v for tri in triangles for v in tri});lookup={v:i for i,v in enumerate(nail_ids)};self.triangles=np.asarray([[lookup[v] for v in tri] for tri in triangles],dtype=np.int32)
        self.rest={};self.moments={};self.nail_weights={};self.skin_weights={}
        for index,bn in groups.items():
            if bn not in rig.data.bones:continue
            weights=np.asarray([sum(g.weight for g in v.groups if g.group==index) for v in mesh.vertices])
            if not np.any(weights[pads]>1e-8) and not np.any(weights[nail_ids]>1e-8) and not np.any(weights[skin_ids]>1e-8):continue
            self.rest[bn]=np.asarray(rig.data.bones[bn].matrix_local.inverted())
            self.moments[bn]=np.mean(coordinates[pads]*weights[pads,None],axis=0)
            self.nail_weights[bn]=coordinates[nail_ids]*weights[nail_ids,None]
            self.skin_weights[bn]=coordinates[skin_ids]*weights[skin_ids,None]
        self.pad_vertices=len(pads);self.nail_triangles=len(triangles)

    def evaluate(self,matrices):
        pad=np.zeros(4);nail=np.zeros_like(next(iter(self.nail_weights.values())));skin=np.zeros_like(next(iter(self.skin_weights.values())))
        for bn,rest in self.rest.items():
            transform=np.einsum('ik,kj->ij',np.asarray(matrices[bn]),rest,optimize=False) if bn in matrices else np.eye(4)
            pad+=np.sum(transform*self.moments[bn][None,:],axis=1)
            nail+=np.einsum('ni,ji->nj',self.nail_weights[bn],transform,optimize=False)
            skin+=np.einsum('ni,ji->nj',self.skin_weights[bn],transform,optimize=False)
        points=nail[:,:3];tri=points[self.triangles];normal=np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]).sum(axis=0);normal/=np.linalg.norm(normal)
        assert np.isfinite(pad).all() and np.isfinite(normal).all()
        return pad[:3],normal,skin[:,:3]
