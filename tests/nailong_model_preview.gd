extends Node3D
var visual: Node3D
var camera: Camera3D
var caption: Label
var settings: Environment
var key: DirectionalLight3D
var face_key: DirectionalLight3D
var fill: OmniLight3D
var inspection_lamp: SpotLight3D

func _ready() -> void:
	var path := "res://scripts/enemies/hunter_visual.gd"
	var args := OS.get_cmdline_user_args()
	if args.has("--candidate-script"):
		path = args[args.find("--candidate-script") + 1]
	var script: Script = load(path)
	visual = script.new()
	add_child(visual)
	var environment := WorldEnvironment.new()
	settings = Environment.new()
	settings.background_mode = Environment.BG_COLOR
	settings.background_color = Color(.046, .062, .075)
	settings.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	settings.ambient_light_color = Color(.82, .89, 1)
	settings.ambient_light_energy = .34
	settings.tonemap_mode = Environment.TONE_MAPPER_ACES
	settings.tonemap_exposure = .85
	environment.environment = settings
	add_child(environment)
	key = DirectionalLight3D.new()
	key.rotation_degrees = Vector3(-34, -32, 0)
	key.light_color = Color(1, .96, .9)
	key.light_energy = 1.1
	key.shadow_enabled = true
	add_child(key)
	face_key = DirectionalLight3D.new()
	face_key.rotation_degrees = Vector3(-22, 165, 0)
	face_key.light_color = Color(1, .98, .9)
	face_key.light_energy = .85
	add_child(face_key)
	fill = OmniLight3D.new()
	fill.position = Vector3(-3, 3, -3)
	fill.light_color = Color(.80, .88, 1)
	fill.light_energy = 4.0
	fill.omni_range = 10
	add_child(fill)
	var floor := MeshInstance3D.new()
	var plane := PlaneMesh.new()
	plane.size = Vector2(100, 100)
	floor.mesh = plane
	var floor_material := StandardMaterial3D.new()
	floor_material.albedo_color = Color(.070, .088, .095)
	floor_material.roughness = .74
	floor.material_override = floor_material
	floor.position.y = .018
	add_child(floor)
	camera = Camera3D.new()
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	camera.size = 3.45
	add_child(camera)
	camera.make_current()
	inspection_lamp = SpotLight3D.new()
	inspection_lamp.light_color = Color(1, .94, .78)
	inspection_lamp.light_energy = 2.6
	inspection_lamp.spot_range = 12
	inspection_lamp.spot_angle = 27
	inspection_lamp.visible = false
	camera.add_child(inspection_lamp)
	var layer := CanvasLayer.new()
	caption = Label.new()
	caption.position = Vector2(36, 28)
	caption.add_theme_font_size_override("font_size", 24)
	caption.add_theme_color_override("font_color", Color(.90, .94, .88))
	layer.add_child(caption)
	add_child(layer)
	call_deferred("_capture_all")

func _capture_all() -> void:
	var directory := "res://docs/previews/nailong/reference_candidate" if OS.get_cmdline_user_args().has("--candidate-script") else "res://docs/previews/nailong"
	DirAccess.make_dir_recursive_absolute(directory)
	var views := [
		["godot_front", Vector3(0, 1.55, -7), Vector3(0, 1.4, 0), 3.45, "idle", 0.0],
		["godot_three_quarter", Vector3(4, 2.25, -7), Vector3(0, 1.4, 0), 3.45, "idle", .15],
		["godot_side", Vector3(7, 1.55, 0), Vector3(0, 1.4, 0), 3.45, "idle", 0.0],
		["godot_back", Vector3(0, 1.55, 7), Vector3(0, 1.4, 0), 3.45, "idle", 0.0],
		["godot_face", Vector3(0, 2.23, -7), Vector3(0, 2.20, -.3), 1.65, "idle", .10],
		["godot_walk", Vector3(4, 2.25, -7), Vector3(0, 1.4, 0), 3.45, "walk", .23],
		["godot_chase", Vector3(4, 2.25, -7), Vector3(0, 1.4, 0), 3.45, "chase", .19],
		["godot_warn", Vector3(4, 2.25, -7), Vector3(0, 1.4, 0), 3.45, "warn", .65],
		["godot_charge", Vector3(4, 2.25, -7), Vector3(0, 1.4, 0), 3.45, "charge", .13],
		["godot_recover", Vector3(4, 2.25, -7), Vector3(0, 1.4, 0), 3.45, "recover", .42],
		["godot_blink", Vector3(0, 2.23, -7), Vector3(0, 2.20, -.3), 1.65, "idle", 1.79],
		["godot_feet", Vector3(2, .50, -5), Vector3(0, .33, 0), 1.25, "idle", 0.0],
		["godot_side_feet", Vector3(5, .48, 0), Vector3(0, .33, 0), 1.25, "idle", 0.0],
		["godot_back_joints", Vector3(2, 1.65, 5), Vector3(0, 1.37, .12), 1.8, "idle", 0.0],
		["godot_mouth_closed", Vector3(0, 1.96, -6), Vector3(0, 1.96, -.4), .9, "idle", 0.0],
		["godot_mouth_open", Vector3(1.2, 2.03, -6), Vector3(0, 1.96, -.4), .9, "warn", .75],
		["godot_palms", Vector3(0, 1.40, -5), Vector3(0, 1.18, -.15), 1.65, "idle", 0.0],
		["godot_soles", Vector3(2, -1.2, -4), Vector3(0, .20, 0), 1.55, "chase", .19],
		["godot_night", Vector3(3, 2.10, -6), Vector3(0, 1.4, 0), 3.35, "recover", .43],
	]
	for view in views:
		camera.position = view[1]
		camera.look_at(view[2])
		camera.size = view[3]
		visual.set_lod(0)
		visual.set_preview_pose(view[4], view[5])
		if view[0] == "godot_mouth_closed":
			_set_mouth_open(0.0)
		if view[0] == "godot_mouth_open":
			_set_mouth_open(1.0)
		if view[0] == "godot_soles":
			visual.position.y = .36
		else:
			visual.position.y = 0.0
		if view[0] == "godot_night":
			settings.background_color = Color(.012, .027, .058)
			settings.ambient_light_color = Color(.34, .46, .72)
			settings.ambient_light_energy = .16
			key.light_energy = .12
			face_key.light_energy = .08
			fill.light_energy = .35
			inspection_lamp.visible = true
		caption.text = "NAILONG | " + String(view[0]).trim_prefix("godot_").to_upper() + " | native skinned LOD0"
		for frame in range(8):
			await get_tree().process_frame
		await RenderingServer.frame_post_draw
		var result := get_viewport().get_texture().get_image().save_png(directory + "/" + view[0] + ".png")
		assert(result == OK)
		print("NAILONG_PREVIEW ", view[0])
	get_tree().quit()

func _set_mouth_open(value: float) -> void:
	for part in visual.meshes:
		for shape in part.mesh.get_blend_shape_count():
			if part.mesh.get_blend_shape_name(shape) == "Open":
				part.set_blend_shape_value(shape, value)
