"""Render an isolated source preview on CPU, leaving the .blend unchanged."""
import bpy
import sys
from pathlib import Path
from mathutils import Vector

args = sys.argv[sys.argv.index('--') + 1:]
out = Path(args[0]).resolve()
meshes = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH' and not obj.hide_render]
for obj in list(bpy.context.scene.objects):
    if obj.type in ('CAMERA', 'LIGHT'):
        bpy.data.objects.remove(obj, do_unlink=True)
points = [obj.matrix_world @ Vector(corner) for obj in meshes for corner in obj.bound_box]
lo = Vector([min(v[i] for v in points) for i in range(3)])
hi = Vector([max(v[i] for v in points) for i in range(3)])
center = (lo + hi) * .5
extent = max(hi - lo)
camera_data = bpy.data.cameras.new('ResearchPreviewCamera')
camera = bpy.data.objects.new('ResearchPreviewCamera', camera_data)
bpy.context.scene.collection.objects.link(camera)
camera.location = center + Vector((1.5, -2.0, 1.15)) * extent
camera.rotation_euler = (center - camera.location).to_track_quat('-Z', 'Y').to_euler()
camera_data.type = 'ORTHO'; camera_data.ortho_scale = extent * 1.4
bpy.context.scene.camera = camera
for name, offset, energy, size in [('Key',(-2,-3,4),1500,3), ('Fill',(3,-1,2),800,3), ('Rim',(0,3,3),1200,2)]:
    data=bpy.data.lights.new(name,'AREA'); data.energy=energy*extent*extent; data.shape='DISK'; data.size=size*extent
    obj=bpy.data.objects.new(name,data); bpy.context.scene.collection.objects.link(obj)
    obj.location=center+Vector(offset)*extent
    obj.rotation_euler=(center-obj.location).to_track_quat('-Z','Y').to_euler()
scene=bpy.context.scene
scene.render.engine='CYCLES'; scene.cycles.device='CPU'; scene.cycles.samples=24
scene.render.resolution_x=640;scene.render.resolution_y=640;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.film_transparent=False
scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.16,.16,.18,1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.4
scene.render.filepath=str(out)
bpy.ops.render.render(write_still=True)
print('SOURCE_PREVIEW_WRITTEN',str(out))
