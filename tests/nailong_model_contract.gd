extends Node
var failures: Array[String] = []
var checks := 0
var candidate: Script

func expect(condition: bool, message: String) -> void:
	checks += 1
	if not condition:
		failures.append(message)
		push_error(message)

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	var path := "res://scripts/enemies/hunter_visual.gd"
	var args := OS.get_cmdline_user_args()
	if args.has("--candidate-script"):
		path = args[args.find("--candidate-script") + 1]
	candidate = load(path)
	call_deferred("_run")

func _run() -> void:
	var actors: Array[Node3D] = []
	for i in range(5):
		var actor: Node3D = candidate.new()
		add_child(actor)
		actors.append(actor)
	expect(candidate.get("build_count") == 1, "Five actors must reuse a single asset cache")
	var first: Node3D = actors[0]
	expect(first.skeleton.get_bone_count() == 24, "Native anatomical skeleton is present")
	expect(first._clip_names.size() == 6, "All six native animation clips import")
	var facial_parts: Array[MeshInstance3D] = []
	for part in first.meshes:
		if part.mesh.get_blend_shape_count() > 0:
			facial_parts.append(part)
	expect(facial_parts.size() >= 6, "Primary skin, real mouth interior, lips, tongue and eyelids contain native facial morphs")
	first.set_preview_pose("idle", 1.79)
	var blink_found := false
	for part in facial_parts:
		for shape in part.mesh.get_blend_shape_count():
			if part.mesh.get_blend_shape_name(shape) == "Blink":
				blink_found = blink_found or part.get_blend_shape_value(shape) > .65
	expect(blink_found, "Idle clip closes eyelid geometry while keeping the eye globe intact")
	first.set_preview_pose("warn", .75)
	var focus_found := false
	for part in facial_parts:
		for shape in part.mesh.get_blend_shape_count():
			if part.mesh.get_blend_shape_name(shape) == "Focus":
				focus_found = focus_found or part.get_blend_shape_value(shape) > .25
	expect(focus_found, "Warning clip changes eyelid and mouth expression")
	var opening_found := false
	for part in facial_parts:
		for shape in part.mesh.get_blend_shape_count():
			if part.mesh.get_blend_shape_name(shape) == "Open":
				opening_found = opening_found or part.get_blend_shape_value(shape) > .6
	expect(opening_found, "Warning drives real skin/cavity/lip/tongue opening tracks")
	for i in range(1, actors.size()):
		expect(first.skeleton != actors[i].skeleton, "Skeleton pose must be instance independent")
		expect(first.animation_player != actors[i].animation_player, "Animation player must be instance independent")
		for part in first.meshes:
			var other: MeshInstance3D = actors[i].find_child(String(part.name), true, false)
			expect(other != null and part.mesh == other.mesh, "Mesh resources are shared: " + String(part.name))
			if other != null:
				for surface in part.mesh.get_surface_count():
					expect(part.mesh.surface_get_material(surface) == other.mesh.surface_get_material(surface), "PBR materials are shared")
	var close_triangles := _triangles(first)
	expect(close_triangles >= 200000 and close_triangles <= 400000, "LOD0 preserves the close-view production geometry budget")
	first.set_lod(1)
	var middle_triangles := _triangles(first)
	_expect_opening_geometry(first, 1)
	first.set_lod(2)
	var far_triangles := _triangles(first)
	_expect_opening_geometry(first, 2)
	expect(middle_triangles < close_triangles * .4 and far_triangles < middle_triangles * .4, "Distance LODs reduce actual submitted geometry")
	first.set_lod(0)
	first.set_preview_pose("chase", .19)
	actors[1].set_preview_pose("recover", .43)
	var head: int = first.skeleton.find_bone("head")
	expect(not first.skeleton.get_bone_pose(head).is_equal_approx(actors[1].skeleton.get_bone_pose(head)), "Independent states produce different bone poses")
	var measured := AABB()
	var initialized := false
	for clip in ["idle", "walk", "chase", "warn", "charge", "recover"]:
		var animation: Animation = first.animation_player.get_animation(first._clip_names[clip])
		expect(animation.length > .3, "Animation has a real timeline: " + clip)
		for fraction in [0.0, .23, .49, .74, .96]:
			first.set_preview_pose(clip, animation.length * fraction)
			var sample := _skin_bounds(first)
			measured = measured.merge(sample) if initialized else sample
			initialized = true
			expect(first.get_animation_bounds().encloses(sample), "Conservative box encloses all skinned vertices: " + clip + str(fraction))
			expect(sample.position.y > -.015, "Feet remain within 1.5 cm of the visual floor: " + clip)
	print("NAILONG_SKINNED_POSE_BOUNDS ", measured)
	first._manual_pose = false
	first.tick_pose(.1, Vector3(0, 0, -4), 1, false)
	expect(first.current_clip == "warn", "Physics warning phase selects anticipation")
	first.tick_pose(.1, Vector3(0, 0, -4), 2, false)
	expect(first.current_clip == "charge", "Physics charge phase selects sprint")
	first.tick_pose(.1, Vector3.ZERO, 3, false)
	expect(first.current_clip == "recover", "Resting phase selects recovery")
	first.tick_pose(.1, Vector3(0, 0, -3.2), 3, false)
	expect(first.current_clip == "chase", "Moving charge cooldown keeps leg motion instead of a standing slide")
	var time: float = first.animation_player.current_animation_position
	get_tree().paused = true
	first.tick_pose(.2, Vector3(0, 0, -4), 2, false)
	expect(is_equal_approx(first.animation_player.current_animation_position, time), "Paused gameplay freezes pose advancement")
	get_tree().paused = false
	for actor in actors:
		actor.queue_free()
	await get_tree().process_frame
	var reopened: Node3D = candidate.new()
	add_child(reopened)
	expect(candidate.get("build_count") == 1, "Restart reuses the cache")
	print("NAILONG_MODEL_CONTRACT checks=", checks, " failures=", failures.size(), " tris=", close_triangles, "/", middle_triangles, "/", far_triangles)
	get_tree().quit(0 if failures.is_empty() else 1)

func _triangles(actor: Node3D) -> int:
	var count := 0
	for part in actor.meshes:
		for surface in part.mesh.get_surface_count():
			var arrays: Array = part.mesh.surface_get_arrays(surface)
			var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
			count += indices.size() / 3
	return count

func _expect_opening_geometry(actor: Node3D, level: int) -> void:
	for part in actor.meshes:
		if not String(part.name).contains("NailongSkin"):
			continue
		var found := false
		for shape in part.mesh.get_blend_shape_count():
			if part.mesh.get_blend_shape_name(shape) != "Open":
				continue
			for surface in part.mesh.get_surface_count():
				var original: PackedVector3Array = part.mesh.surface_get_arrays(surface)[Mesh.ARRAY_VERTEX]
				var target: PackedVector3Array = part.mesh.surface_get_blend_shape_arrays(surface)[shape][Mesh.ARRAY_VERTEX]
				for i in original.size():
					var difference := target[i] - original[i] if part.mesh.blend_shape_mode == Mesh.BLEND_SHAPE_MODE_NORMALIZED else target[i]
					if absf(difference.y) > .065:
						found = true
						break
		expect(found, "Distance mouth retains a meaningful closed-to-open skin delta: LOD" + str(level))

func _skin_bounds(actor: Node3D) -> AABB:
	var low := Vector3(INF, INF, INF)
	var high := Vector3(-INF, -INF, -INF)
	var skeleton: Skeleton3D = actor.skeleton
	skeleton.force_update_all_bone_transforms()
	for part in actor.meshes:
		var skin: Skin = part.skin
		var transforms: Array[Transform3D] = []
		for bind in skin.get_bind_count():
			var bone := skin.get_bind_bone(bind)
			if bone < 0:
				bone = skeleton.find_bone(skin.get_bind_name(bind))
			transforms.append(actor.global_transform.affine_inverse() * skeleton.global_transform * skeleton.get_bone_global_pose(bone) * skin.get_bind_pose(bind))
		for surface in part.mesh.get_surface_count():
			var arrays: Array = part.mesh.surface_get_arrays(surface)
			var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
			var shapes: Array = part.mesh.surface_get_blend_shape_arrays(surface)
			if not shapes.is_empty():
				var base_vertices := vertices.duplicate()
				for shape in shapes.size():
					var value: float = part.get_blend_shape_value(shape)
					if absf(value) < .00001:
						continue
					var shape_vertices: PackedVector3Array = shapes[shape][Mesh.ARRAY_VERTEX]
					for i in vertices.size():
						var displacement := shape_vertices[i]
						if part.mesh.blend_shape_mode == Mesh.BLEND_SHAPE_MODE_NORMALIZED:
							displacement -= base_vertices[i]
						vertices[i] += displacement * value
			var bones: PackedInt32Array = arrays[Mesh.ARRAY_BONES]
			var weights: PackedFloat32Array = arrays[Mesh.ARRAY_WEIGHTS]
			for i in vertices.size():
				var vertex := Vector3.ZERO
				for influence in range(4):
					var index := i * 4 + influence
					vertex += (transforms[bones[index]] * vertices[i]) * weights[index]
				low = low.min(vertex)
				high = high.max(vertex)
	return AABB(low, high - low)
