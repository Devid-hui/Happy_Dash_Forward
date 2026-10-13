"""Remove source-only normal-fan faces after storing the evaluated normals."""
import bpy,bmesh,numpy as np
def snapshots(actors):
 graph=bpy.context.evaluated_depsgraph_get();pairs=[]
 for actor in actors:
  if actor.type!='MESH' or actor.hide_render:continue
  attribute=actor.data.attributes.get('NormalFanGhost')
  if attribute is None:continue
  evaluated=actor.evaluated_get(graph);original=evaluated.to_mesh()
  mesh=original.copy();evaluated.to_mesh_clear()
  flags=np.empty(len(mesh.polygons),dtype=bool);mesh.attributes['NormalFanGhost'].data.foreach_get('value',flags)
  normals=np.empty(len(mesh.loops)*3,dtype=np.float32);mesh.corner_normals.foreach_get('vector',normals);normals=normals.reshape(-1,3)
  counts=np.array([p.loop_total for p in mesh.polygons]);keep=np.repeat(~flags,counts)
  bm=bmesh.new();bm.from_mesh(mesh);bm.faces.ensure_lookup_table()
  bmesh.ops.delete(bm,geom=[bm.faces[i] for i in np.flatnonzero(flags)],context='FACES_ONLY');bm.to_mesh(mesh);bm.free();mesh.update()
  mesh.normals_split_custom_set(normals[keep].tolist())
  clone=bpy.data.objects.new(actor.name+' visible posed normal snapshot',mesh)
  bpy.context.scene.collection.objects.link(clone);clone.matrix_world=actor.matrix_world.copy()
  # A copied evaluated mesh can retain the source shape-key block. It must be
  # made static before rendering; otherwise the pose is evaluated twice.
  posed=np.empty(len(mesh.vertices)*3,dtype=np.float32);mesh.vertices.foreach_get('co',posed)
  if mesh.shape_keys is not None:
   clone.shape_key_clear();mesh.vertices.foreach_set('co',posed);mesh.update()
   mesh.normals_split_custom_set(normals[keep].tolist())
  assert mesh.shape_keys is None
  pairs.append((actor,clone));actor.hide_render=True
 return pairs
def restore(pairs):
 for actor,clone in pairs:
  actor.hide_render=False;mesh=clone.data;bpy.data.objects.remove(clone,do_unlink=True);bpy.data.meshes.remove(mesh)
