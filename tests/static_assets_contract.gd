extends Node
# Structural checks support, but do not replace, rendered first-person / landmark review.
const FOREST := preload("res://scripts/art/forest_detail.gd")
const LANDMARKS := preload("res://scripts/props/landmark_models.gd")
const TERRAIN := preload("res://scripts/art/terrain_detail.gd")
const EQUIPMENT := preload("res://scripts/player/field_equipment.gd")
const BOOK := preload("res://scripts/props/research_book.gd")

func _ready() -> void:
	call_deferred("run_contract")

func run_contract() -> void:
	var bark := FOREST.bark_material()
	var first := FOREST.build(41,false,bark); var second := FOREST.build(41,false,bark)
	add_child(first); add_child(second)
	var first_meshes := first.find_children("*","MeshInstance3D",true,false)
	var second_meshes := second.find_children("*","MeshInstance3D",true,false)
	assert(first_meshes.size() == 8,"living tree retains three wood/leaf LODs plus two shared shadow proxies")
	assert(first_meshes.size() == second_meshes.size())
	for i in range(first_meshes.size()):
		assert(first_meshes[i].mesh == second_meshes[i].mesh,"cached variants share immutable meshes")
		var opaque_bark: bool = "Bark" in String(first_meshes[i].name) and not String(first_meshes[i].name).begins_with("Shadow")
		var expected_fade := GeometryInstance3D.VISIBILITY_RANGE_FADE_DISABLED if opaque_bark else GeometryInstance3D.VISIBILITY_RANGE_FADE_SELF
		assert(first_meshes[i].visibility_range_fade_mode == expected_fade)
	assert(first.find_children("*","StaticBody3D",true,false).size() == 1,"tree collider is retained")
	var dead := FOREST.build(41,true,bark); add_child(dead)
	assert(dead.find_children("*","MeshInstance3D",true,false).size() == 4,"dead tree retains three explicit geometry LODs plus a shared shadow proxy")
	FOREST.set_motion_time(4.2)
	var foliage := first.find_child("Near*Canopy*",true,false) as MeshInstance3D
	assert(foliage != null,"near foliage must retain its own controlled wind material")
	assert(is_equal_approx(foliage.material_override.get_shader_parameter("motion_time"),4.2),"foliage motion is explicitly controlled by paused gameplay time")
	assert(not (foliage.material_override as ShaderMaterial).shader.code.contains("TIME"))
	var near_surface: Mesh = first_meshes[0].mesh
	assert(near_surface.get_faces().size() > 1800,"near tree preserves continuous roots/branches rather than a far impostor")
	var terrain := TERRAIN.build(731); add_child(terrain)
	assert(terrain.get_meta("cosmetic_only")); assert(terrain.get_meta("spatial_cell_size") == 16.0)
	assert(terrain.find_children("*","CollisionObject3D",true,false).is_empty(),"detail must not obstruct task routes")
	TERRAIN.set_motion_time(4.2)
	for chunk in terrain.get_children():
		assert(chunk is MultiMeshInstance3D)
		assert(chunk.multimesh.instance_count > 0)
		if chunk.material_override is ShaderMaterial:
			assert(is_equal_approx(chunk.material_override.get_shader_parameter("motion_time"),4.2))
			assert(not (chunk.material_override as ShaderMaterial).shader.code.contains("TIME"))
		assert(chunk.multimesh.get_aabb().size.x < 23 and chunk.multimesh.get_aabb().size.z < 23,"batch bounds remain local")
	var car := Node3D.new(); LANDMARKS.car(car); add_child(car)
	assert(car.find_children("Wheel*","MeshInstance3D",true,false).size() == 4)
	assert(car.find_child("FrontWindshield",true,false) != null)
	assert(car.find_child("DoorSeam*",true,false) != null)
	var tower := Node3D.new(); LANDMARKS.tower(tower); add_child(tower)
	assert(tower.find_children("SaggingCable*","MeshInstance3D",true,false).size() == 8)
	assert(tower.find_child("Insulators",true,false) != null)
	var report := BOOK.new(); add_child(report)
	assert(report.has_node("Pages") and report.has_node("FrontCover") and report.has_node("Spine"))
	report.highlight(.1); assert(report.cover_material.emission_energy_multiplier > .5)
	await get_tree().create_timer(.2).timeout
	assert(report.cover_material.emission_energy_multiplier <= .51,"highlight duration restores cover appearance")
	var camera := Camera3D.new(); add_child(camera)
	var equipment := EQUIPMENT.new(); camera.add_child(equipment); equipment.setup(camera)
	assert(equipment.asset.find_children("*","Skeleton3D",true,false).size() == 2,"each hand retains an independently articulated skeleton")
	for skeleton in equipment.asset.find_children("*","Skeleton3D",true,false):assert(skeleton.get_bone_count() >= 17)
	var finger := equipment.right_skeleton.find_bone("RightGripIndex2")
	assert(finger >= 0)
	var neutral := equipment.right_skeleton.get_bone_pose_rotation(finger)
	equipment.trigger("flash"); equipment.tick(.2)
	assert(not equipment.right_skeleton.get_bone_pose_rotation(finger).is_equal_approx(neutral),"trigger squeeze uses an actual finger joint")
	assert(equipment.support.visible and equipment.current_action == "flash","concentrated burst braces with the assisting hand")
	equipment.tick(equipment.action_duration+.01); assert(not equipment.support.visible and equipment.current_action == "idle")
	assert(equipment.right_skeleton.get_bone_pose_rotation(finger).is_equal_approx(neutral),"finger returns to its neutral grip")
	equipment.trigger("flash"); equipment.tick(.2); assert(equipment.support.visible)
	equipment.set_mode(true); equipment.tick(.15)
	assert(equipment.pulse_mode and not equipment.support.visible,"interrupting the burst cleans up the old bracing pose")
	var native_support: Transform3D = equipment.support.transform
	for kind in ["luminol","salt","mud"]:
		equipment.trigger(kind); equipment.tick(.15); assert(equipment.tools[kind].visible and equipment.support.visible)
		# A native underside hand has an authored roll, so an absolute Euler-X
		# limit would require destroying that grip orientation. Bound motion
		# relative to its real rest, and require the implement to follow it.
		var relative: Basis = equipment.support.basis*native_support.basis.inverse()
		assert(relative.get_rotation_quaternion().angle_to(Quaternion.IDENTITY) <= .65,"wrist gesture remains bounded relative to the actual native support pose")
		assert(equipment.tools[kind].global_position.distance_to(equipment.support.global_position) < .18,"held tool must remain within the supporting hand span")
		equipment.tick(1); assert(not equipment.tools[kind].visible)
	# Scene rebuild must not retain an old hand's animation state.
	var replacement := EQUIPMENT.new(); camera.add_child(replacement); replacement.setup(camera)
	assert(replacement.current_action == "idle" and not replacement.support.visible)
	assert(replacement.asset != equipment.asset and replacement.right_skeleton != equipment.right_skeleton)
	equipment.trigger("shot"); equipment.tick(.07)
	var replacement_finger := replacement.right_skeleton.find_bone("RightGripIndex2")
	assert(replacement.right_skeleton.get_bone_pose_rotation(replacement_finger).is_equal_approx(neutral),"one grip animation cannot mutate another scene instance")
	print("STATIC ASSETS PASS: merged forest/LOD, local cosmetic terrain batches, detailed landmarks/report, skinned grips and actual instrument actions")
	get_tree().quit()
