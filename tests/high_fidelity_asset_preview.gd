extends Node3D
# Candidate review under neutral native lighting and actual GPU rain. No cinematic postprocess.
const EQUIPMENT := preload("res://scripts/player/field_equipment.gd")
const LANDMARKS := preload("res://scripts/props/landmark_models.gd")
var camera: Camera3D
var root: Node3D
var equipment: Node3D
var environment: Environment
var key: DirectionalLight3D
var rain: GPUParticles3D
var spotlight: SpotLight3D
var frame := 0
var view := 0
var views := ["HERO_FP","OPTICS_CLOSE","HAND_GRIP","CAR_FRONT","CAR_SIDE","CAR_INTERIOR","NIGHT_FP","NIGHT_CAR"]

func _ready() -> void:
	DirAccess.make_dir_recursive_absolute("res://docs/previews")
	var world_environment := WorldEnvironment.new(); environment = Environment.new()
	environment.background_mode = Environment.BG_SKY
	var sky := Sky.new(); var sky_material := ProceduralSkyMaterial.new()
	sky_material.sky_top_color = Color(.21,.25,.27); sky_material.sky_horizon_color = Color(.35,.37,.34)
	sky_material.ground_bottom_color = Color(.07,.085,.07); sky_material.ground_horizon_color = Color(.18,.20,.17)
	sky.sky_material = sky_material; environment.sky = sky
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR; environment.ambient_light_color = Color(.65,.68,.64)
	environment.ambient_light_energy = .72; environment.reflected_light_source = Environment.REFLECTION_SOURCE_SKY
	environment.tonemap_mode = Environment.TONE_MAPPER_LINEAR; world_environment.environment = environment; add_child(world_environment)
	key = DirectionalLight3D.new(); key.light_energy = 1.1; key.rotation_degrees = Vector3(-42,-30,0); key.shadow_enabled = true; add_child(key)
	camera = Camera3D.new(); camera.current = true; camera.fov = 58; add_child(camera)
	root = Node3D.new(); add_child(root)
	spotlight = SpotLight3D.new(); spotlight.spot_range = 18; spotlight.spot_angle = 33; spotlight.light_color = Color(.91,.98,.88); spotlight.shadow_enabled = true; add_child(spotlight)
	rain = GPUParticles3D.new(); rain.amount = 1100; rain.lifetime = 1.3; rain.position.y = 9
	rain.local_coords = false; rain.visibility_aabb = AABB(Vector3(-22,-12,-22),Vector3(44,26,44))
	var pm := ParticleProcessMaterial.new(); pm.direction = Vector3(.06,-1,.03); pm.spread = 3; pm.initial_velocity_min = 18; pm.initial_velocity_max = 24; pm.gravity = Vector3(0,-2,0)
	pm.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_BOX; pm.emission_box_extents = Vector3(12,9,12); rain.process_material = pm
	var rm := StandardMaterial3D.new(); rm.albedo_color = Color(.15,.20,.21); rm.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	var rq := QuadMesh.new(); rq.size = Vector2(.014,.26); rq.material = rm; rain.draw_pass_1 = rq; rain.transform_align = GPUParticles3D.TRANSFORM_ALIGN_Z_BILLBOARD_Y_TO_VELOCITY
	add_child(rain); _switch(0)

func _switch(index: int) -> void:
	for child in root.get_children(): child.free()
	if is_instance_valid(equipment): equipment.free()
	var ground := MeshInstance3D.new(); var ground_mesh := PlaneMesh.new(); ground_mesh.size = Vector2(48,48)
	ground.mesh = ground_mesh; var material := StandardMaterial3D.new(); material.albedo_color = Color(.075,.086,.067); material.roughness = .48
	ground.material_override = material; root.add_child(ground)
	rain.emitting = index >= 6; environment.ambient_light_energy = .08 if index >= 6 else .72; key.light_energy = .10 if index >= 6 else 1.1
	environment.fog_enabled = index >= 6; environment.fog_density = .006 if index >= 6 else 0; environment.fog_light_color = Color(.05,.085,.075)
	spotlight.light_energy = 12.0 if index >= 6 else 0.0
	if index in [0,6]:
		camera.look_at_from_position(Vector3(0,1.5,4),Vector3(0,1.5,-5))
		equipment = EQUIPMENT.new(); camera.add_child(equipment); equipment.setup(self)
		if index == 6: spotlight.global_transform = equipment.beam_socket.global_transform
	elif index in [1,2]:
		var specimen := (load(EQUIPMENT.ASSET_PATH) as PackedScene).instantiate() as Node3D
		root.add_child(specimen); specimen.position.y = 1.0
		(specimen.find_child("LeftSupport",true,false) as Node3D).visible = false
		(specimen.find_child("SkillTools",true,false) as Node3D).visible = false
		if index == 1: camera.look_at_from_position(Vector3(.44,1.33,-.67),Vector3(0,1.01,-.01))
		else: camera.look_at_from_position(Vector3(-.30,.94,.20),Vector3(-.04,.77,-.02))
	else:
		LANDMARKS.car(root)
		if index in [3,7]: camera.look_at_from_position(Vector3(3.1,1.90,4.5),Vector3(0,.91,0))
		if index == 4: camera.look_at_from_position(Vector3(4.1,1.3,.6),Vector3(0,.93,0))
		if index == 5: camera.look_at_from_position(Vector3(.58,1.36,-.73),Vector3(-.21,1.15,.55))
		if index == 7: spotlight.look_at_from_position(Vector3(3.5,1.6,3.5),Vector3(0,.93,0))

func _process(_delta: float) -> void:
	frame += 1
	if frame%42 != 0: return
	get_viewport().get_texture().get_image().save_png("res://docs/previews/CANDIDATE_%s.png" % views[view])
	print("HIGH CANDIDATE CAPTURE ",views[view]," viewport=",get_viewport().get_visible_rect().size," window=",DisplayServer.window_get_size())
	view += 1
	if view >= views.size(): get_tree().quit(); return
	_switch(view)
