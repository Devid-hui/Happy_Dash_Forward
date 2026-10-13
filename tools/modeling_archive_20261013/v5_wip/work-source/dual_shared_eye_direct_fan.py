"""Single left-eye prototype with real shared annulus/lid boundary vertices."""
import bpy,bmesh,math,json,importlib.util
import numpy as np
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import delaunay_2d_cdt

BASE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('v3_face_geometry',BASE/'face_v3_frozen.py');h=importlib.util.module_from_spec(spec);spec.loader.exec_module(h)

def boundary_loops(faces):
 es=np.sort(np.concatenate([faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]]),axis=1);uni,counts=np.unique(es,axis=0,return_counts=True)
 edges=uni[counts==1];adj={}
 for a,b in edges:adj.setdefault(int(a),[]).append(int(b));adj.setdefault(int(b),[]).append(int(a))
 bad={a:len(v) for a,v in adj.items() if len(v)!=2}
 if bad:raise RuntimeError('Actual source boundary is not a 2-valent loop: '+str(bad))
 remaining={tuple(map(int,e)) for e in edges};loops=[]
 while remaining:
  start,current=next(iter(remaining));previous=start;loop=[start,current];remaining.remove(tuple(sorted((start,current))))
  while current!=start:
   following=next(i for i in adj[current] if i!=previous);edge=tuple(sorted((current,following)))
   if edge not in remaining:raise RuntimeError('Actual source boundary does not close')
   remaining.remove(edge);loop.append(following);previous,current=current,following
  loops.append(loop[:-1])
 return loops

def normal_fan_material():
 mat=bpy.data.materials.get('Eye transition normal fan alpha zero')
 if mat is None:
  mat=bpy.data.materials.new('Eye transition normal fan alpha zero');mat.use_nodes=True
  shader=mat.node_tree.nodes.get('Principled BSDF')
  shader.inputs['Base Color'].default_value=(0,0,0,0);shader.inputs['Alpha'].default_value=0
  if 'surface_render_method' in mat.bl_rna.properties:mat.surface_render_method='DITHERED'
 return mat

def build_eye_patch(rig,skin,manifest,inspection,side,final_joint=True):
 m=skin.data;original=h.oral_coordinates(m.shape_keys.key_blocks['Basis']);keys={k.name:h.oral_coordinates(k) for k in m.shape_keys.key_blocks}
 loops=np.empty(len(m.loops),dtype=np.int32);m.loops.foreach_get('vertex_index',loops);source_faces=loops.reshape(-1,3)
 component=next(c for c in inspection['components'] if c['triangle_normal_y_median']>0 and len(c['boundary_loops'])==1 and not c['non_manifold_boundary_vertices'])
 selected=np.asarray(component['body_face_indices']);selected_faces=source_faces[selected]
 frame=manifest['face_helper']['measured_eyes'][side];c=np.asarray(frame['center']);r=np.asarray(frame['radii'])
 centroids=original[selected_faces].mean(axis=1);dz=centroids[:,2]-c[2];q=((centroids[:,0]-c[0])/.20)**2+(dz/np.where(dz>=0,.185,.165))**2
 keep=q>=1.;annulus=selected_faces[keep];annulus_source_ids=selected[keep]
 rings=boundary_loops(annulus)
 def ring_radius(ids):
  p=original[ids];z=p[:,2]-c[2]
  return float(np.median(((p[:,0]-c[0])/.20)**2+(z/np.where(z>=0,.185,.165))**2))
 if len(rings)!=2:raise RuntimeError('Expected actual outer/inner annular loops, got '+str([(len(a),ring_radius(a)) for a in rings]))
 rings.sort(key=ring_radius);inner_ids=rings[0];outer_ids=rings[1]
 # Keep counterclockwise projected order for radial bridges facing +Y.
 pts=original[inner_ids];area=float(np.sum(pts[:,0]*np.roll(pts[:,2],-1)-pts[:,2]*np.roll(pts[:,0],-1)))
 if area<0:inner_ids=list(reversed(inner_ids))
 ids=np.unique(annulus);local={int(v):i for i,v in enumerate(ids)}
 vertices=original[ids].tolist();faces=[[local[int(v)] for v in f] for f in annulus]
 old_colors,attr=h.colors_of(skin);colors=old_colors[ids,:3].tolist();source_ids=ids.tolist()
 outer_set={local[int(v)] for v in outer_ids};inner_local=[local[int(v)] for v in inner_ids]
 surface=h.FaceSurface(skin,original,old_colors)
 original_inner_local=list(inner_local);original_count=len(ids);rows=20;n=128
 theta=np.linspace(0,math.tau,n,endpoint=False);cos=np.cos(theta);sin=np.sin(theta);upper=sin>=0
 endpoint=np.column_stack((c[0]+.17*cos,np.zeros(n),c[2]+np.where(upper,.155,.145)*sin))
 foreground_vertices,foreground_inverse=np.unique(selected_faces,return_inverse=True)
 foreground=BVHTree.FromPolygons(original[foreground_vertices].tolist(),foreground_inverse.reshape(-1,3).tolist(),all_triangles=True)
 boundary_normals=[]
 for i,p in enumerate(endpoint):
  hit,normal,face,distance=foreground.ray_cast(Vector((p[0],3,p[2])),Vector((0,-1,0)),4)
  if hit is None:raise RuntimeError('Regular inner transition ring missed actual foreground')
  endpoint[i,1]=hit.y;boundary_normals.append(list(normal))
 boundary_normals=np.asarray(boundary_normals)
 annulus_points=np.concatenate([original[ids],endpoint]).astype(np.float32)
 inner_local=list(range(original_count,original_count+n))
 for point in endpoint:
  colors.append(surface.sample(float(point[0]),float(point[2]))[1].tolist());source_ids.append(-1)
 outer_xz=original[inner_ids][:,[0,2]];input_points=np.concatenate([outer_xz,endpoint[:,[0,2]]])
 constraints=[(i,(i+1)%len(inner_ids)) for i in range(len(inner_ids))]+[(len(inner_ids)+i,len(inner_ids)+(i+1)%n) for i in range(n)]
 cdt=delaunay_2d_cdt([Vector(tuple(p)) for p in input_points],constraints,[],0,1e-8,True)
 def inside(point,poly):
  x,z=point;result=False
  for a,b in zip(poly,np.roll(poly,-1,axis=0)):
   if (a[1]>z)!=(b[1]>z) and x<(b[0]-a[0])*(z-a[1])/(b[1]-a[1])+a[0]:result=not result
  return result
 local_cdt=[]
 for origins in cdt[3]:
  if len(origins)!=1:raise RuntimeError('CDT produced merged/new vertex without explicit source mapping: '+str(origins))
  index=origins[0];local_cdt.append(original_inner_local[index] if index<len(inner_ids) else inner_local[index-len(inner_ids)])
 transition_count=0
 for tri in cdt[2]:
  pts=np.asarray([cdt[0][i][:] for i in tri]);center=pts.mean(axis=0)
  if not inside(center,outer_xz) or inside(center,endpoint[:,[0,2]]):continue
  area=float(np.cross(pts[1]-pts[0],pts[2]-pts[0]));face=[local_cdt[i] for i in tri]
  if area>0:face.reverse()
  faces.append(face);transition_count+=1
 # The source ring is unmodified. CDT supplies a genuine variable-count bridge
 # to a regular ring, avoiding angular backtracking and microscopic fan cells.
 displacement=np.zeros((original_count,3));unwrapped=theta.copy()
 def state(blink,focus=0):
  arrays=[annulus_points.copy()]
  for row in range(rows):
   t=row/rows;blend=t*t*(3-2*t)
   edge_x=c[0]+.98*r[0]*cos
   medial=(-1 if side=="right" else 1)*cos
   opening=np.where(upper,.94-.58*focus-.30*focus*medial,.92-.06*focus)
   edge_z=c[2]+r[2]*opening*sin
   closed_z=c[2]-.30*r[2]*(1-cos*cos)
   edge_z=edge_z*(1-blink)+closed_z*blink
   x=edge_x*(1-t)+endpoint[:,0]*t
   closed_at_x=c[2]-.30*r[2]*(1-((x-c[0])/(.98*r[0]))**2)
   z=((c[2]+r[2]*opening*sin)*(1-blink)+closed_at_x*blink)*(1-t)+endpoint[:,2]*t
   qedge=((edge_x-c[0])/r[0])**2+((edge_z-c[2])/r[2])**2
   edge_y=c[1]+r[1]*np.sqrt(np.maximum(0,1-qedge))+.0103
   by=np.asarray([surface.sample(float(a),float(b))[0] for a,b in zip(x,z)])
   # Outer three radial rows use the true face profile, staying tangent to the
   # retained original annulus. Interior uses the same intact globe envelope.
   dx=endpoint[:,0]-edge_x;dz=endpoint[:,2]-edge_z
   denom=np.sqrt(np.maximum(.015,1-qedge))
   s0=-r[1]*((edge_x-c[0])*dx/(r[0]*r[0])+(edge_z-c[2])*dz/(r[2]*r[2]))/denom
   s1=-(boundary_normals[:,0]*dx+boundary_normals[:,2]*dz)/np.maximum(.15,boundary_normals[:,1])
   s0=np.clip(s0,-.45,.45);s1=np.clip(s1,-.45,.45)
   y=(2*t**3-3*t*t+1)*edge_y+(t**3-2*t*t+t)*s0+(-2*t**3+3*t*t)*endpoint[:,1]+(t**3-t*t)*s1
   points=np.column_stack((x,y,z));lip=np.where(upper,.0012*(1-cos*cos)*math.exp(-t/.045),0)
   points=h.conform_over_globe(points,c,r,lip)
   arrays.append(points.astype(np.float32))
  return np.concatenate(arrays).astype(np.float32)
 annulus_count=len(annulus_points)
 for row in range(rows):
  ring=annulus_count+row*n
  next_ring=annulus_count+(row+1)*n if row<rows-1 else None
  for col in range(n):
   nxt=(col+1)%n
   a=ring+col;b=ring+nxt;cc=next_ring+nxt if next_ring is not None else inner_local[nxt];d=next_ring+col if next_ring is not None else inner_local[col]
   faces.append([a,b,cc,d])
 adjacency=np.unique(np.sort(np.asarray([edge for face in faces for edge in zip(face,face[1:]+face[:1])],dtype=np.int32),axis=1),axis=0)
 def fair_state(blink,focus=0):
  points=state(blink,focus).astype(np.float64)
  if focus:
   points+=focus*body_follow
  distance=np.linalg.norm((points[adjacency[:,0]]-points[adjacency[:,1]])[:,[0,2]],axis=1)
  weight=1/np.maximum(.001,distance)
  degree=np.zeros(len(points));np.add.at(degree,adjacency[:,0],weight);np.add.at(degree,adjacency[:,1],weight)
  pinned=np.zeros(len(points),dtype=bool);pinned[list(outer_set)]=True
  for polygon in faces:
   if any(i in outer_set for i in polygon):pinned[polygon]=True
  pinned[annulus_count:annulus_count+n]=True
  fixed_y=points[:,1].copy()
  # Remove the high-frequency derivative noise inherited from the voxel rim.
  # One connected facial sheet is faired, with outer head and inner margin held;
  # the unchanged globe is an obstacle. No whole-body or full-head smoothing.
  for iteration in range(700):
   accum=np.zeros(len(points));np.add.at(accum,adjacency[:,0],weight*points[adjacency[:,1],1]);np.add.at(accum,adjacency[:,1],weight*points[adjacency[:,0],1])
   points[~pinned,1]=accum[~pinned]/np.maximum(degree[~pinned],1e-12)
   points=h.conform_over_globe(points,c,r,np.zeros(len(points)))
   points[pinned,1]=fixed_y[pinned]
  return points.astype(np.float32)
 basis=fair_state(0);half=fair_state(.5);closed=fair_state(1)
 body_follow=np.zeros_like(basis)
 body_follow[:original_count]=keys['Focus'][ids]-original[ids]
 for index in range(original_count,len(basis)):
  factor=1.0 if index<annulus_count else ((index-annulus_count)//n/rows)**2*(3-2*((index-annulus_count)//n/rows))
  body_follow[index]=surface.focus_at(float(basis[index,0]),float(basis[index,2]))*factor
 joint={}
 if final_joint:
  for focus_index in range(11):
   for blink_index in range(11):
    # Existing 121 targets are real globe-constrained surfaces, not chords of
    # only three Y anchors. This corrects the measured intermediate cornea hit.
    points=(basis if blink_index==0 else half if blink_index==5 else closed) if focus_index==0 and blink_index in [0,5,10] else fair_state(blink_index/10,focus_index/10)
    joint[(blink_index,focus_index)]=points.astype(np.float32)
  print('JOINT_GRID_CREATED',side,len(joint),flush=True)
 else:
  joint={(0,0):basis,(5,0):half,(10,0):closed}
 # Keep a quad unless its standard first diagonal changes projected direction.
 # A replacement uses the same four vertices/targets, and is recorded explicitly.
 split_changes=[];stable_faces=[]
 targets=np.stack(list(joint.values()))
 for polygon_index,face in enumerate(faces):
  if len(face)!=4:
   stable_faces.append(face);continue
  a,b,cc,d=face
  first=np.array([[a,b,cc],[a,cc,d]])
  pts=targets[:,first]
  normal=np.cross(pts[:,:,1]-pts[:,:,0],pts[:,:,2]-pts[:,:,0])
  minimum=float((normal[:,:,1]/np.maximum(np.linalg.norm(normal,axis=2),1e-30)).min())
  if minimum>=-1e-8:
   stable_faces.append(face);continue
  alternative=np.array([[a,b,d],[b,cc,d]])
  pts=targets[:,alternative];alternate=np.cross(pts[:,:,1]-pts[:,:,0],pts[:,:,2]-pts[:,:,0])
  if float((alternate[:,:,1]/np.maximum(np.linalg.norm(alternate,axis=2),1e-30)).min())<-1e-8:
   raise RuntimeError('Neither diagonal stays oriented for '+side+' / '+str(polygon_index))
  stable_faces.extend(alternative.tolist());split_changes.append({'original_polygon':polygon_index,'original_quad':face,'new_triangles':alternative.tolist(),'old_min_normal_y':minimum,'alternate_min_signed_y_area_twice':float(alternate[:,:,1].min())})
 faces=stable_faces
 for row in range(rows):
  t=row/rows
  for index,p in enumerate(basis[annulus_count+row*n:annulus_count+(row+1)*n]):
   color=surface.sample(float(p[0]),float(p[2]))[1];tint=1
   if row==0:tint=.16 if upper[index] else .7
   colors.append((color*tint).tolist());source_ids.append(-1)
 # Invisible source one-ring supplies the actual same normal fan on both
 # objects. This is explicitly marked geometry, not a smoothing approximation.
 outside=np.flatnonzero(np.any(np.isin(source_faces,outer_ids),axis=1)&~np.isin(np.arange(len(source_faces)),selected))
 inside_ghost=annulus_source_ids[np.any(np.isin(annulus,outer_ids),axis=1)]
 original_visible_face_count=len(faces)
 original_visible_vertex_count=len(basis)
 ghost_ids=np.setdiff1d(np.unique(source_faces[outside]),np.asarray(source_ids)[np.asarray(source_ids)>=0])
 ghost_local={int(src):original_visible_vertex_count+i for i,src in enumerate(ghost_ids)}
 all_source_local={int(src):i for i,src in enumerate(source_ids) if src>=0};all_source_local.update(ghost_local)
 ghost_faces=[[all_source_local[int(src)] for src in source_faces[index]] for index in outside]
 faces.extend(ghost_faces)
 for src in ghost_ids:
  colors.append(old_colors[src,:3].tolist());source_ids.append(int(src))
 for pair,points in list(joint.items()):
  ghost_points=original[ghost_ids]+pair[1]/10*(keys['Focus'][ghost_ids]-original[ghost_ids])
  joint[pair]=np.concatenate([points,ghost_points]).astype(np.float32)
 basis=joint[(0,0)]
 half=joint[(5,0)];closed=joint[(10,0)]
 local.update(ghost_local)
 mesh=bpy.data.meshes.new('Shared '+side+' face and eyelid joint patch');mesh.from_pydata(basis.tolist(),[],faces);mesh.update()
 obj=bpy.data.objects.new('SharedEyelidFace_'+side,mesh);bpy.context.collection.objects.link(obj);mesh.materials.append(m.materials[0].copy());mesh.materials.append(normal_fan_material())
 for p in mesh.polygons:
  p.use_smooth=True
  if p.index>=original_visible_face_count:p.material_index=1
 normal_only=mesh.attributes.new(name='NormalFanGhost',type='BOOLEAN',domain='FACE')
 normal_only.data.foreach_set('value',np.arange(len(mesh.polygons))>=original_visible_face_count)
 pigment=mesh.color_attributes.new(name=attr.name,type='FLOAT_COLOR',domain='POINT');pigment.data.foreach_set('color',np.column_stack((colors,np.ones(len(colors)))).astype(np.float32).ravel());mesh.color_attributes.active_color=pigment
 source_attr=mesh.attributes.new(name='OriginalSourceVertexID',type='INT',domain='POINT');source_attr.data.foreach_set('value',np.asarray(source_ids,dtype=np.int32))
 obj.shape_key_add(name='Basis')
 if final_joint:
  for (blink_index,focus_index),points in joint.items():
   if blink_index or focus_index:obj.shape_key_add(name=h.lid_key(blink_index,focus_index)).data.foreach_set('co',points.ravel())
 else:
  for name,points in [('Half',half),('Closed',closed)]:obj.shape_key_add(name=name).data.foreach_set('co',points.ravel())
 # Preserve original outer body expression/weights; prototype new inner points
 # use head and get only the original body's measured expression at that ray.
 for name in (['Open'] if final_joint else ['Open','Focus']):
  delta=np.zeros_like(basis);valid=np.flatnonzero(np.asarray(source_ids)>=0);source_indices=np.asarray(source_ids)[valid];delta[valid]=keys[name][source_indices]-original[source_indices]
  obj.shape_key_add(name=name).data.foreach_set('co',(basis+delta).ravel())
 groups={g.index:obj.vertex_groups.new(name=g.name) for g in skin.vertex_groups}
 for source,local_index in local.items():
  for group in m.vertices[source].groups:groups[group.group].add([local_index],group.weight,'REPLACE')
 groups[next(g.index for g in skin.vertex_groups if g.name=='head')].add(np.flatnonzero(np.asarray(source_ids)<0).tolist(),1,'REPLACE')
 mod=obj.modifiers.new('Native shared face armature','ARMATURE');mod.object=rig;obj.parent=rig
 # Only distant split boundary corners inherit custom normals. Interior is
 # automatic, and the actual lid/annulus junction is a truly shared edge fan.
 source_normals=np.empty(len(m.loops)*3,dtype=np.float32);m.corner_normals.foreach_get('vector',source_normals);source_normals=source_normals.reshape(-1,3)
 custom=np.zeros((len(mesh.loops),3),dtype=np.float32)
 for i,p in enumerate(mesh.polygons[:len(annulus)]):
  for corner,loop_index in enumerate(p.loop_indices):
   if mesh.loops[loop_index].vertex_index in outer_set:custom[loop_index]=source_normals[annulus_source_ids[i]*3+corner]
 for local_polygon,source_polygon in enumerate(outside,start=original_visible_face_count):
  polygon=mesh.polygons[local_polygon]
  for corner,loop_index in enumerate(polygon.loop_indices):
   if mesh.loops[loop_index].vertex_index in outer_set:custom[loop_index]=source_normals[source_polygon*3+corner]
 mesh.normals_split_custom_set(custom.tolist())
 # Body face cleanup is deferred until both patches have sampled the same
 # unchanged c3 source. No original Body vertex/key/group array is edited.
 removed_background=[]
 for old_component in inspection['components']:
  if old_component['triangle_normal_y_median']<0:removed_background.extend(old_component['body_face_indices'])
 # Verify the inserted radial surface and original face annulus have the same
 # vertex index on each edge; every shared ring edge has precisely two faces.
 edges_count={}
 for p in mesh.polygons:
  for e in p.edge_keys:edges_count[tuple(sorted(e))]=edges_count.get(tuple(sorted(e)),0)+1
 common=[tuple(sorted((inner_local[i],inner_local[(i+1)%n]))) for i in range(n)]
 assert all(edges_count[e]==2 for e in common)
 report={'object':obj.name,'source_component_label':component['label'],'selected_source_body_face_ids':selected.tolist(),'removed_background_source_body_face_ids':removed_background,
 'selected_front_normal_y_median':component['triangle_normal_y_median'],'original_annular_faces':len(annulus),'annular_source_vertices':original_count,'annulus_and_transition_ring_vertices':annulus_count,'cdt_transition_triangles':transition_count,'actual_source_inner_ring_vertices':len(inner_ids),'actual_inner_loop_vertices':n,'actual_outer_loop_vertices':len(outer_ids),'new_radial_vertices':rows*n,'total_local_mesh_vertices':len(mesh.vertices),'source_body_vertex_count':len(m.vertices),'visible_face_count':original_visible_face_count,'visible_vertex_count':original_visible_vertex_count,'face_normal_fan_ghost_source_face_ids':outside.tolist(),'body_normal_fan_ghost_source_face_ids':inside_ghost.tolist(),'normal_fan_ghost_added_original_vertex_ids':ghost_ids.tolist(),'normal_fan_material_alpha':0.0,'actual_common_boundary_local_vertex_ids':inner_local,'all_common_ring_edges_two_faces':True,'new_target_names':[k.name for k in obj.data.shape_keys.key_blocks],
 'parameter_correction_max_degrees':float(np.degrees(np.max(np.abs(theta-unwrapped)))),'minimum_angle_step_radians':float(np.diff(theta).min()),'local_annulus_displacement_max_m':float(np.linalg.norm(displacement,axis=1).max()),'prototype_only':not final_joint,'diagonal_repairs':split_changes,'joint_key_grid':final_joint,'removed_faces_deferred':True,'Focus_LODs_six_clips_not_verified':True}
 return obj,report
