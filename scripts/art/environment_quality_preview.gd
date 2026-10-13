extends Node3D
# This is an actual Godot material/geometry review scene, not an offline render.
const FOREST := preload("res://scripts/art/forest_detail.gd")
const TERRAIN := preload("res://scripts/art/terrain_detail.gd")
var clock := 0.0
var capture_path := ""
var camera: Camera3D
var review_environment: Environment
var review_sun: DirectionalLight3D
var review_spot: SpotLight3D
var review_view := "hero"
var review_debug := ""
var leaf_study_node: Node3D
var fixed_motion_time := -1.0

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	get_tree().paused = false
	get_window().size = Vector2i(1920,1080)
	get_window().mode = Window.MODE_WINDOWED
	get_window().visible = true
	get_window().grab_focus()
	get_viewport().msaa_3d = Viewport.MSAA_4X
	get_viewport().use_taa = true
	var view := "hero"
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--environment-view="): view = arg.get_slice("=",1)
		if arg.begins_with("--environment-capture="): capture_path = arg.get_slice("=",1)
		if arg.begins_with("--environment-debug="): review_debug = arg.get_slice("=",1)
		if arg.begins_with("--environment-fixed-time="): fixed_motion_time = float(arg.get_slice("=",1))
	review_view = view
	var env := Environment.new(); env.background_mode = Environment.BG_COLOR
	env.background_color = Color(.037,.053,.065)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(.44,.57,.70); env.ambient_light_energy = .55 if view != "night" else .26
	env.reflected_light_source = Environment.REFLECTION_SOURCE_DISABLED
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	var world := WorldEnvironment.new(); world.environment = env; add_child(world)
	review_environment = env
	var sun := DirectionalLight3D.new(); sun.rotation_degrees = Vector3(-39,-32,0)
	sun.light_color = Color(.84,.9,1); sun.light_energy = 1.8 if view != "night" else .23
	sun.shadow_enabled = true; sun.directional_shadow_max_distance = 35; add_child(sun)
	review_sun = sun
	var floor_node := MeshInstance3D.new(); var plane := PlaneMesh.new(); plane.size = Vector2(200,200)
	floor_node.mesh = plane; floor_node.material_override = TERRAIN.ground_material(); add_child(floor_node)
	var tree := FOREST.build(0,false,FOREST.bark_material()); add_child(tree)
	force_tree_debug(tree)
	for i in range(1,4):
		var companion := FOREST.build(i,false,FOREST.bark_material())
		companion.position = Vector3(-8+i*6,0,-9-i*1.5); companion.rotation.y = i*1.4; add_child(companion)
		force_tree_debug(companion)
	var undergrowth := TERRAIN.build(); add_child(undergrowth)
	for data in [["fern",Vector3(.8,0,1.2)],["grass",Vector3(-.65,0,1.3)],["stone",Vector3(-1.3,0,.9)],["leaf",Vector3(.2,.01,1.5)],["bush",Vector3(2.2,0,-.5)]]:
		var instance := MeshInstance3D.new(); instance.name = data[0]+"Specimen"
		instance.mesh = TERRAIN._mesh(data[0],1); instance.material_override = TERRAIN._material(data[0]); instance.position = data[1]
		add_child(instance)
	camera = Camera3D.new(); camera.fov = 55; camera.far = 150; add_child(camera); camera.current = true
	match view:
		"bark": camera.position = Vector3(1.4,1.55,2.6); camera.look_at(Vector3(0,1.2,0))
		"understory": camera.position = Vector3(1.7,1.0,3.0); camera.look_at(Vector3(.1,.25,1.1))
		"mid": camera.position = Vector3(0,6,30); camera.look_at(Vector3(0,4.3,0))
		"far": camera.position = Vector3(0,7.5,66); camera.look_at(Vector3(0,4.3,0))
		"leaf", "leaf_back":
			var study := (load("res://assets/refined/environment/leaf_detail_study.glb") as PackedScene).instantiate() as Node3D
			study.position = Vector3(6,1.05,2); add_child(study)
			for part in study.find_children("*","MeshInstance3D",true,false): part.material_override = FOREST._foliage_material(); part.lod_bias = 1000.0
			camera.position = Vector3(6.38,1.55 if view == "leaf" else .85,2.50); camera.look_at(Vector3(6,1.19,2))
		_: camera.position = Vector3(8.6,4.9,12.4); camera.look_at(Vector3(0,4.3,0))
	review_spot = SpotLight3D.new(); review_spot.light_color = Color(.86,.93,1); review_spot.light_energy = 75.0
	review_spot.spot_range = 25; review_spot.spot_angle = 39; review_spot.spot_attenuation = .7; review_spot.shadow_enabled = true
	review_spot.visible = view == "night"; camera.add_child(review_spot)
	if not capture_path.is_empty(): capture.call_deferred()

func show_leaf_study() -> void:
	if leaf_study_node == null:
		leaf_study_node = (load("res://assets/refined/environment/leaf_detail_study.glb") as PackedScene).instantiate() as Node3D
		leaf_study_node.position = Vector3(6,1.05,2); add_child(leaf_study_node)
		for part in leaf_study_node.find_children("*","MeshInstance3D",true,false):
			part.material_override = FOREST._foliage_material(); part.lod_bias = 1000.0
	leaf_study_node.visible = true

func force_tree_debug(tree: Node3D) -> void:
	if review_debug.is_empty(): return
	var material := StandardMaterial3D.new(); material.albedo_color = Color(.56,.56,.56)
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	for part in tree.get_children():
		if not part is MeshInstance3D: continue
		if review_debug.contains("near") or review_debug.contains("mid"):
			part.visible = String(part.name).begins_with("Near" if review_debug.contains("near") else "Mid")
			part.visibility_range_begin = 0; part.visibility_range_end = 0
			part.visibility_range_begin_margin = 0; part.visibility_range_end_margin = 0
			part.visibility_range_fade_mode = GeometryInstance3D.VISIBILITY_RANGE_FADE_DISABLED
		if review_debug.contains("flat") and "Bark" in String(part.name): part.material_override = material
		if review_debug.contains("noshadow") or review_debug.contains("flat"): part.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF

func _process(delta: float) -> void:
	if get_tree().paused: get_tree().paused = false
	clock = fixed_motion_time if fixed_motion_time >= 0.0 else clock+delta
	FOREST.set_motion_time(clock); TERRAIN.set_motion_time(clock)

func capture() -> void:
	if review_view == "bark_lod_audit":
		fixed_motion_time = 8.25
		var direction := Vector3(4.5,0,6.61).normalized()
		for distance in [8.0,9.0,10.0,12.0,10.0,9.0,8.0]:
			camera.position = direction*distance+Vector3(0,2.6,0); camera.look_at(Vector3(0,3.3,0))
			await save_capture(capture_path+"bark_"+str(distance)+"m_frame"+str(Engine.get_frames_drawn())+".png")
	elif review_view == "shadow_lod_audit":
		fixed_motion_time = 8.25
		camera.position = Vector3(4.5,2.6,6.61); camera.look_at(Vector3(0,3.3,0))
		for source_lod in ["Mid","Far"]:
			for tree in get_children():
				if tree.has_node("ShadowCanopy"):
					(tree.get_node("ShadowCanopy") as MeshInstance3D).mesh = (tree.get_node(source_lod+"Canopy") as MeshInstance3D).mesh
			await save_capture(capture_path+"8m_"+source_lod.to_lower()+"_canopy.png")
	elif review_view == "shadow_audit":
		# Matched render pair proves the proxies cast visible shadows while the
		# accepted visible geometry, camera, light and wind phase stay identical.
		fixed_motion_time = 8.25
		for shadows_enabled in [true,false]:
			for proxy in find_children("Shadow*","MeshInstance3D",true,false):
				proxy.visible = shadows_enabled
			await save_capture(capture_path+("shadow_on" if shadows_enabled else "shadow_off")+".png")
	elif review_view in ["all","foliage"]:
		var views := ["hero","leaf","leaf_back","mid","far","night"] if review_view == "foliage" else ["hero","bark","understory","night"]
		for view in views:
			if leaf_study_node: leaf_study_node.visible = false
			match view:
				"bark": camera.position = Vector3(1.4,1.55,2.6); camera.look_at(Vector3(0,1.2,0))
				"understory": camera.position = Vector3(1.7,1.0,3.0); camera.look_at(Vector3(.1,.25,1.1))
				"mid": camera.position = Vector3(0,6,30); camera.look_at(Vector3(0,4.3,0))
				"far": camera.position = Vector3(0,7.5,66); camera.look_at(Vector3(0,4.3,0))
				"leaf","leaf_back":
					show_leaf_study()
					camera.position = Vector3(6.38,1.55 if view == "leaf" else .85,2.50); camera.look_at(Vector3(6,1.19,2))
				_: camera.position = Vector3(8.6,4.9,12.4); camera.look_at(Vector3(0,4.3,0))
			review_spot.visible = view == "night"
			review_sun.light_energy = .23 if view == "night" else 1.8
			review_environment.ambient_light_energy = .26 if view == "night" else .55
			await save_capture(capture_path+view+".png")
	else: await save_capture(capture_path)
	# Release authored resource caches while the render loop is alive, then quit.
	FOREST.tree_cache.clear(); FOREST._bark = null; FOREST._foliage = null
	TERRAIN._mesh_cache.clear(); TERRAIN._material_cache.clear()
	for child in get_children():
		if child != camera: child.queue_free()
	for i in range(3): await RenderingServer.frame_post_draw
	get_tree().quit()

func save_capture(path: String) -> void:
	# Automated previews must still render when Codex receives foreground focus.
	# A paused/minimized window can stop the passive frame_post_draw signal.
	for i in range(72):
		await get_tree().process_frame
		RenderingServer.force_draw()
	var image := get_viewport().get_texture().get_image()
	assert(image.get_size() == Vector2i(1920,1080),"Preview must capture actual 1080p rendering without rescaling")
	image.save_png(path)
	print("ENVIRONMENT_PREVIEW ",path," actual_pixels=",image.get_size()," window=",get_window().size," renderer=",RenderingServer.get_current_rendering_method())
