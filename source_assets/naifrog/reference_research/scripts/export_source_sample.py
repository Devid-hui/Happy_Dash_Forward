"""Create a glTF research sample from a downloaded source without saving the .blend."""
import bpy
import sys
from pathlib import Path

out = Path(sys.argv[sys.argv.index('--') + 1]).resolve()
for action in bpy.data.actions:
    action.use_fake_user = True
for obj in bpy.context.scene.objects:
    if obj.type in ('MESH', 'ARMATURE'):
        obj.hide_set(False)
        obj.hide_viewport = False
    obj.select_set(obj.type in ('MESH', 'ARMATURE'))
    if obj.type == 'MESH':
        obj.animation_data_clear()
    elif obj.type == 'ARMATURE' and obj.animation_data:
        for track in list(obj.animation_data.nla_tracks):
            obj.animation_data.nla_tracks.remove(track)
bpy.ops.export_scene.gltf(filepath=str(out), export_format='GLB', use_selection=True,
    export_animations=True, export_animation_mode='ACTIONS', export_force_sampling=True,
    export_skins=True, export_def_bones=True, export_apply=False, export_yup=True,
    export_image_format='AUTO')
print('RESEARCH_GLB_EXPORTED', str(out))
