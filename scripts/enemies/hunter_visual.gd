extends Node3D
## Native skinned asset. Physics, target selection and navigation remain in hunter.gd.
const MODEL_PATH := "res://assets/refined/nailong/nailong_lod0.glb"
# Preserve the old envelope and include the reconstructed three-LOD pose union
# with its 0.10m margin. Renderer and Director use this same conservative box.
const ANIMATION_BOUNDS := AABB(Vector3(-1.30, -0.13, -1.28), Vector3(2.59, 3.15, 2.46))
const CLIPS := ["idle", "walk", "chase", "warn", "charge", "recover"]
static var cached_model: PackedScene
static var build_count := 0
static var cached_lod_meshes: Array[Dictionary] = []
static var cached_corneal_material: ShaderMaterial
var animation_player: AnimationPlayer
var skeleton: Skeleton3D
var meshes: Array[MeshInstance3D] = []
var current_clip := ""
var current_lod := 0
var pose_clock := 0.0
var _clip_names: Dictionary = {}
var _last_phase := -1
var _manual_pose := false
var _head_bone := -1
var _belly_bone := -1
var _has_shared_eyelid_faces := false

static func _prepare_asset() -> void:
	if cached_model != null:
		return
	cached_model = load(MODEL_PATH) as PackedScene
	assert(cached_model != null, "Native Nailong asset did not import")
	build_count += 1
	# All instances and all distance meshes use the LOD0 material/texture resources.
	var base := cached_model.instantiate()
	var base_materials: Dictionary = {}
	var base_meshes: Dictionary = {}
	for node in base.find_children("*", "MeshInstance3D", true, false):
		var part := node as MeshInstance3D
		base_meshes[String(part.name)] = part.mesh
		var materials: Array[Material] = []
		for surface in part.mesh.get_surface_count():
			var material := part.mesh.surface_get_material(surface) as StandardMaterial3D
			if material != null and material.resource_name.to_lower().contains("skin"):
				material.metallic_specular = .24
				material.subsurf_scatter_enabled = true
				material.subsurf_scatter_skin_mode = false
				material.subsurf_scatter_strength = .04
			materials.append(material)
		base_materials[String(part.name)] = materials
	cached_lod_meshes.append(base_meshes)
	base.free()
	for level in [1, 2]:
		var scene := load("res://assets/refined/nailong/nailong_lod%d.glb" % level) as PackedScene
		var instance := scene.instantiate()
		var lod_meshes: Dictionary = {}
		for node in instance.find_children("*", "MeshInstance3D", true, false):
			var part := node as MeshInstance3D
			var key := String(part.name)
			if base_materials.has(key):
				var materials: Array = base_materials[key]
				for surface in mini(materials.size(), part.mesh.get_surface_count()):
					part.mesh.surface_set_material(surface, materials[surface])
			lod_meshes[key] = part.mesh
		cached_lod_meshes.append(lod_meshes)
		instance.free()
	# Godot's material importer approximates KHR transmission; retain a clear wet eye
	# layer with native alpha and specular so it does not obscure the iris.
	cached_corneal_material = ShaderMaterial.new()
	var corneal_shader := Shader.new()
	corneal_shader.code = """shader_type spatial;
render_mode blend_add, depth_draw_never, cull_back;
void fragment() {
    ALBEDO = vec3(0.0);
    ROUGHNESS = 0.018;
    SPECULAR = 0.85;
    ALPHA = 0.65;
}
"""
	cached_corneal_material.shader = corneal_shader

func _ready() -> void:
	_build_model(self)
	animation_player = find_child("AnimationPlayer", true, false) as AnimationPlayer
	for node in find_children("*", "Skeleton3D", true, false):
		skeleton = node as Skeleton3D
		break
	assert(animation_player != null and skeleton != null, "Asset needs independent bones and native clips")
	_head_bone = skeleton.find_bone("head")
	_belly_bone = skeleton.find_bone("belly")
	for animation_name in animation_player.get_animation_list():
		for clip in CLIPS:
			if String(animation_name) == clip or String(animation_name).ends_with("/" + clip) or String(animation_name).ends_with("|" + clip):
				_clip_names[clip] = animation_name
				var animation := animation_player.get_animation(animation_name)
				animation.loop_mode = Animation.LOOP_NONE if clip == "warn" else Animation.LOOP_LINEAR
	# Physics drives animation time; do not allow a second idle callback to advance it.
	animation_player.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
	pose_clock = fmod(float(get_instance_id() % 997) * .031, 3.2)
	_play_clip("idle", 0.0)
	animation_player.seek(pose_clock, true)

func _build_model(root: Node3D) -> void:
	_prepare_asset()
	var model := cached_model.instantiate() as Node3D
	model.name = "NailongAsset"
	root.add_child(model)
	for node in model.find_children("*", "MeshInstance3D", true, false):
		var part := node as MeshInstance3D
		# This local box contains all bone poses. Director uses get_animation_bounds,
		# not imported rest get_aabb(), for the separate view-preservation decision.
		part.custom_aabb = ANIMATION_BOUNDS
		if String(part.name).to_lower().contains("corneal"):
			part.material_override = cached_corneal_material
		meshes.append(part)
		_has_shared_eyelid_faces = _has_shared_eyelid_faces or _is_shared_eyelid_face(part)
	# Legacy static previews call _build_model without putting the builder in-tree.
	# Give that entry the same neutral pose instead of the imported default pose.
	var player := model.find_child("AnimationPlayer", true, false) as AnimationPlayer
	if player != null:
		player.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
		for animation_name in player.get_animation_list():
			if String(animation_name) == "idle" or String(animation_name).ends_with("/idle"):
				player.play(animation_name, 0.0)
				player.seek(0.0, true)
				player.advance(0.0)
				break

func get_animation_bounds() -> AABB:
	return ANIMATION_BOUNDS

func _play_clip(clip: String, blend := .14) -> void:
	if current_clip == clip or not _clip_names.has(clip):
		return
	current_clip = clip
	animation_player.play(_clip_names[clip], blend)

func tick_pose(delta: float, horizontal_velocity: Vector3, charge_phase: int, stunned: bool) -> void:
	if _manual_pose or delta <= 0.0 or get_tree().paused:
		return
	pose_clock += delta
	var clip := "idle"
	var moving := horizontal_velocity.length_squared() > .05
	var recovering_motion := charge_phase == 3 and moving and not stunned
	if stunned:
		clip = "recover"
	elif charge_phase == 1:
		clip = "warn"
	elif charge_phase == 2:
		clip = "charge"
	elif moving:
		clip = "chase" if horizontal_velocity.length() > 3.0 else "walk"
	elif charge_phase == 3:
		clip = "recover"
	if charge_phase != _last_phase and clip == "warn":
		current_clip = ""
	_play_clip(clip)
	_last_phase = charge_phase
	animation_player.advance(delta)
	if recovering_motion:
		_apply_moving_recovery()
	_update_lod()

func _apply_moving_recovery() -> void:
	# Resting is an eight-second charge cooldown; AI keeps walking. Keep its gait
	# and add tired breathing/eyelids instead of moving a standing recovery pose.
	var breath := sin(pose_clock * 3.4)
	if _head_bone >= 0:
		var rotation := skeleton.get_bone_pose_rotation(_head_bone)
		skeleton.set_bone_pose_rotation(_head_bone, rotation * Quaternion(Vector3.RIGHT, .035 + .010 * breath))
	if _belly_bone >= 0:
		var scale_value := skeleton.get_bone_pose_scale(_belly_bone)
		skeleton.set_bone_pose_scale(_belly_bone, scale_value * Vector3(1 + .010 * breath, 1 + .016 * breath, 1 + .010 * breath))
	# The shared Face boundary follows Body's authored Focus curve. Changing
	# only Body separates their positions and normals during moving recovery.
	if _has_shared_eyelid_faces:
		return
	for part in meshes:
		# Joint eyelid targets already combine Blink with Focus. Applying the
		# complete Focus endpoint again breaks the authored convex combination.
		if _has_joint_lid_grid(part.mesh):
			continue
		for shape in part.mesh.get_blend_shape_count():
			if part.mesh.get_blend_shape_name(shape) == "Focus":
				part.set_blend_shape_value(shape, .22)

func _has_joint_lid_grid(mesh: Mesh) -> bool:
	var source := mesh as ArrayMesh
	if source == null:
		return false
	var declared_grid := false
	var has_blink := false
	var has_focus := false
	for shape in source.get_blend_shape_count():
		var target := String(source.get_blend_shape_name(shape))
		has_blink = has_blink or target == "Blink"
		has_focus = has_focus or target == "Focus"
		if target.length() == 11 and target.begins_with("LidB") and target.substr(7,1) == "F" and target.substr(4,3).is_valid_int() and target.substr(8,3).is_valid_int():
			declared_grid = true
	return declared_grid and has_blink and has_focus

func _is_shared_eyelid_face(part: MeshInstance3D) -> bool:
	if not String(part.name).begins_with("SharedEyelidFace_") or not _has_joint_lid_grid(part.mesh):
		return false
	for shape in part.mesh.get_blend_shape_count():
		if part.mesh.get_blend_shape_name(shape) == "Open":
			return true
	return false

func _update_lod() -> void:
	var camera := get_viewport().get_camera_3d()
	if camera == null:
		return
	var distance := camera.global_position.distance_to(global_position)
	var level := 2 if distance > 24.0 else 1 if distance > 11.0 else 0
	if level == current_lod:
		return
	set_lod(level)

func set_lod(level: int) -> void:
	current_lod = clampi(level, 0, 2)
	for part in meshes:
		var key := String(part.name)
		if cached_lod_meshes[current_lod].has(key):
			part.mesh = cached_lod_meshes[current_lod][key]

func set_preview_pose(clip: String, time: float) -> void:
	_manual_pose = true
	current_clip = ""
	_play_clip(clip, 0.0)
	animation_player.seek(time, true)
	animation_player.advance(0.0)
	if skeleton != null:
		skeleton.force_update_all_bone_transforms()
