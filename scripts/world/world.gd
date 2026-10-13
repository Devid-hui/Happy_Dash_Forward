extends Node3D

signal return_to_menu
signal retry_requested
const FOREST_DETAIL := preload("res://scripts/art/forest_detail.gd")
const TERRAIN_DETAIL := preload("res://scripts/art/terrain_detail.gd")
const BOOK := preload("res://scripts/props/research_book.gd")
const LANDMARK_MODELS := preload("res://scripts/props/landmark_models.gd")
const PLAYER_SCRIPT := preload("res://scripts/player/player.gd")
const HUNTER_DIRECTOR := preload("res://scripts/enemies/hunter_director.gd")
var hunter_director
const RESEARCH_MANAGER := preload("res://scripts/core/research_manager.gd")
const FUSION_MANAGER := preload("res://scripts/skills/fusion_manager.gd")
const STORM_CONTROLLER := preload("res://scripts/world/storm_controller.gd")
const HUD_CONTROLLER := preload("res://scripts/ui/hud_controller.gd")
const RAIN_LOOP := preload("res://assets/audio/rain_loop.ogg")
const CANOPY_RAIN_LOOP := preload("res://assets/audio/canopy_rain_loop.ogg")
const HUNTER_VOICE := preload("res://scripts/enemies/hunter_voice.gd")
var player: CharacterBody3D
var hunter_nodes: Array[Node] = []
var storm_controller
var environment: WorldEnvironment
var lightning_energy := 0.0
var collected := 0
var luminol_charges := 3
var objective_nodes: Array[Node3D] = []
var exit_node: Node3D
var hud_controller
var notebook := false
var traces: Array[Dictionary] = []
var fields: Array[Dictionary] = []
var echo_positions: Array[Vector3] = []
var research_manager
var fusion_manager
var paused := false
var filter_index := 0
var rain_audio: AudioStreamPlayer
var canopy_rain_audio: AudioStreamPlayer3D
var thunder_audio: AudioStreamPlayer3D
var rain_bus_index := -1
var rain_filter: AudioEffectBandPassFilter
var footsteps_audio: AudioStreamPlayer3D
var flash_snapshot_points: Array[Vector2] = []
var _modal_ready := false
var _leaving := false
var gameplay_elapsed := 0.0
var disorientation_audio: AudioStreamPlayer
var echo_audio: AudioStreamPlayer
var echo_filter: AudioEffectLowPassFilter
var pulse_noise_audio: AudioStreamPlayer
var daylight_audio: AudioStreamPlayer

func _ready() -> void:
	research_manager=RESEARCH_MANAGER.new(); add_child(research_manager); research_manager.setup(self)
	fusion_manager=FUSION_MANAGER.new(); add_child(fusion_manager); fusion_manager.setup(self)
	_build_environment(); _build_ground(); _build_landmarks(); _build_forest(); _build_player(); _build_hunter(); _build_objectives(); _build_rain(); _build_hud()
	GameState.record_knowledge("lamp")
	update_hud()
	_modal_ready = true
	paused = not _window_is_focused()
	_sync_modal_state()

func _exit_tree() -> void:
	for audio in get_tree().get_nodes_in_group("procedural_audio"):
		if audio is AudioStreamPlayer or audio is AudioStreamPlayer3D:
			audio.stop(); audio.stream = null
	if rain_bus_index > 0 and rain_bus_index < AudioServer.get_bus_count():
		AudioServer.remove_bus(rain_bus_index)
	# Remove only this world's temporary effect and preserve every other effect.
	for index in range(AudioServer.get_bus_effect_count(0)-1,-1,-1):
		if AudioServer.get_bus_effect(0,index) == echo_filter:
			AudioServer.remove_bus_effect(0,index)

func _mat(color: Color, emission := false) -> StandardMaterial3D:
	var m := StandardMaterial3D.new(); m.albedo_color = color; m.roughness = 1.0
	if emission: m.emission_enabled = true; m.emission = color; m.emission_energy_multiplier = 0.6
	return m

func _build_environment() -> void:
	environment = WorldEnvironment.new(); environment.name = "WorldEnvironment"
	var env := Environment.new(); env.background_mode = Environment.BG_COLOR; env.background_color = Color(0.0015,0.0025,0.004)
	# 只保留极低的环境填充光，形体主要由玩家近光和闪电揭示。
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR; env.ambient_light_color = Color(.28,.37,.40); env.ambient_light_energy = .24 * GameState.brightness
	env.fog_enabled = true; env.fog_light_color = Color(.055,.082,.092); env.fog_density = 0.014; env.fog_sky_affect = 0.0
	# 微弱体积雾只在灯光穿过雨幕时显形，环境本身不被抬亮。
	env.volumetric_fog_enabled = true; env.volumetric_fog_density = 0.006; env.volumetric_fog_albedo = Color(0.10, 0.14, 0.16); env.volumetric_fog_ambient_inject = 0.0; env.volumetric_fog_anisotropy = 0.32; env.volumetric_fog_length = 48.0; env.volumetric_fog_sky_affect = 0.0
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	environment.environment = env; add_child(environment)
	var moon := DirectionalLight3D.new(); moon.name = "CloudFilteredMoonlight"
	moon.rotation_degrees = Vector3(-52,-32,0); moon.light_color = Color(.42,.58,.67)
	moon.light_energy = .22 * GameState.brightness; moon.shadow_enabled = true
	moon.directional_shadow_max_distance = 45.0; add_child(moon)
	storm_controller=STORM_CONTROLLER.new();add_child(storm_controller);storm_controller.setup(self)
	storm_controller.lightning_started.connect(_on_lightning_started)

func _build_ground() -> void:
	var plane := MeshInstance3D.new(); var mesh := PlaneMesh.new(); mesh.size = Vector2(200,200); plane.mesh = mesh
	plane.position.y = -.006
	plane.material_override = TERRAIN_DETAIL.ground_material(); add_child(plane)
	var body := StaticBody3D.new(); var shape := CollisionShape3D.new(); var box := BoxShape3D.new(); box.size = Vector3(200,0.2,200); shape.shape = box; shape.position.y = -0.1; body.add_child(shape); add_child(body)
	for edge in [Vector3(-99.5,6,0),Vector3(99.5,6,0),Vector3(0,6,-99.5),Vector3(0,6,99.5)]:
		var wall := StaticBody3D.new()
		wall.name = "MapBoundary_%d" % get_child_count()
		var wall_shape := CollisionShape3D.new()
		var wall_box := BoxShape3D.new()
		wall_box.size = Vector3(1,12,200) if edge.x != 0 else Vector3(200,12,1)
		wall_shape.shape = wall_box
		wall.position = edge
		wall.add_child(wall_shape)
		add_child(wall)
	add_child(TERRAIN_DETAIL.build(731))

func _build_forest() -> void:
	# 中央保留可辨路面；树群围出林间空地，并在地标间形成遮挡层次。
	var bark := FOREST_DETAIL.bark_material()
	var planted := 0
	var attempts := 0
	while planted < 185 and attempts < 900:
		attempts += 1
		var x := randf_range(-92.0, 92.0); var z := randf_range(-92.0, 92.0); var p := Vector2(x,z)
		if p.length() < 7.0: continue
		# 留出通向地标的步行通道，避免密林封住任务路线。
		var on_path := false
		for endpoint in [Vector2(-24,-28),Vector2(35,-12),Vector2(22,34),Vector2(72,65)]:
			var t := clampf(p.dot(endpoint)/endpoint.length_squared(),0.0,1.0)
			if p.distance_to(endpoint*t) < 2.4: on_path = true
		if on_path: continue
		var near_landmark := false
		for landmark_pos in [Vector2(-24,-28), Vector2(35,-12), Vector2(22,34), Vector2(-35,25), Vector2(72,65)]:
			if p.distance_to(landmark_pos) < 8.0: near_landmark = true; break
		if near_landmark: continue
		var tree := FOREST_DETAIL.build(planted * 731 + 41, planted % 4 == 0,bark)
		tree.position = Vector3(x,0,z); tree.rotation.y = randf_range(0.0, TAU); tree.scale = Vector3.ONE * randf_range(0.85,1.25)
		add_child(tree)
		planted += 1

func _landmark(pos: Vector3, kind: String) -> void:
	var root := Node3D.new(); root.name = "Landmark_"+kind; root.set_meta("landmark_kind",kind); root.position = pos; add_child(root)
	if kind in ["tower","tree","car"]:
		var marker := Label3D.new()
		marker.text = {"tower":"输电塔","tree":"枯树","car":"废车"}[kind]
		marker.position.y = 3.0
		marker.font_size = 40; marker.pixel_size = .008
		marker.billboard = BaseMaterial3D.BILLBOARD_ENABLED
		marker.visibility_range_end = 18.0
		root.add_child(marker)
	if kind != "exit":
		var obstacle := StaticBody3D.new(); obstacle.name="LandmarkCollision"; root.add_child(obstacle)
		var collision := CollisionShape3D.new()
		var box := BoxShape3D.new()
		match kind:
			"tower": box.size=Vector3(4.6,12,4.6); collision.position.y=6
			"tree": box.size=Vector3(1.5,8.2,1.5); collision.position.y=4.1
			"car": box.size=Vector3(2.7,1.9,4.5); collision.position.y=.95
			"stone": box.size=Vector3(1.0,2.2,0.7); collision.position.y=1.1
		collision.shape=box; obstacle.add_child(collision)
	match kind:
		"tower": LANDMARK_MODELS.tower(root)
		"tree": LANDMARK_MODELS.dead_tree(root)
		"car": LANDMARK_MODELS.car(root)
		"stone":
			var slab:=MeshInstance3D.new();var b:=BoxMesh.new();b.size=Vector3(0.7,2.2,0.35);slab.mesh=b;slab.position.y=1.1;slab.rotation.z=0.08;slab.material_override=_mat(Color(0.17,0.18,0.18));root.add_child(slab)
		"exit":
			var arch:=MeshInstance3D.new();var b:=BoxMesh.new();b.size=Vector3(3.2,4.7,0.5);arch.mesh=b;arch.position.y=2.35;arch.material_override=_mat(Color(0.11,0.2,0.17),true);root.add_child(arch)
			var inner:=MeshInstance3D.new();var m:=PlaneMesh.new();m.size=Vector2(2.4,3.8);inner.mesh=m;inner.position=Vector3(0,2.0,-0.27);inner.material_override=_mat(Color(0.015,0.07,0.06),true);root.add_child(inner)
			if kind == "exit": exit_node=root

func _build_landmarks() -> void:
	_landmark(Vector3(-24,0,-28),"tower");_landmark(Vector3(35,0,-12),"tree");_landmark(Vector3(22,0,34),"car");_landmark(Vector3(-35,0,25),"stone")

func _build_player() -> void:
	player = CharacterBody3D.new(); player.set_script(PLAYER_SCRIPT); player.position=Vector3(0,0,0); player.world=self; add_child(player)

func _build_hunter() -> void:
	hunter_director = HUNTER_DIRECTOR.new()
	add_child(hunter_director)
	hunter_director.setup(self,player,hunter_nodes)

func _build_objectives() -> void:
	var locations := [Vector3(-20.6,.99,-27),Vector3(32,.99,-10),Vector3(22,.99,37)]
	var names := ["输电塔","枯树","废车"]
	for idx in range(3):
		var item := BOOK.new()
		item.position = locations[idx]
		item.rotation_degrees = Vector3(-12,[165,20,180][idx],0)
		item.set_meta("objective_index",idx)
		item.set_meta("landmark_name",names[idx])
		add_child(item)
		# Derive the support height from the actual rotated mesh, including its cover
		# and pages. This stays correct when the report asset is revised.
		var bottom := INF
		for part in item.find_children("*","MeshInstance3D",true,false):
			var bounds: AABB = part.global_transform * part.get_aabb()
			bottom = minf(bottom,bounds.position.y)
		if is_finite(bottom): item.position.y += .525-bottom
		# 书放在低木箱上，离开地标碰撞体，避免浮空或被车体挡住。
		LANDMARK_MODELS.box(self,"ResearchCrate",Vector3(.95,.52,.8),Vector3(item.position.x,.26,item.position.z),_mat(Color(.18,.12,.07)))
		var light := OmniLight3D.new()
		light.light_color = Color(.39,.55,.42)
		light.light_energy = 2.0; light.omni_range = 2.2
		light.position = Vector3(0,.4,-.5)
		item.add_child(light)
		objective_nodes.append(item)
	_landmark(Vector3(72,0,65),"exit")

func _build_rain() -> void:
	var rain:=GPUParticles3D.new();rain.name="Rain";rain.amount=1500;rain.lifetime=1.25;rain.emitting=true;rain.position.y=6
	rain.transform_align = GPUParticles3D.TRANSFORM_ALIGN_Z_BILLBOARD_Y_TO_VELOCITY
	rain.local_coords = false
	rain.visibility_aabb = AABB(Vector3(-64,-47,-64),Vector3(128,57,128))
	var process:=ParticleProcessMaterial.new();process.direction=Vector3(0.10,-1,0.06);process.spread=4.0;process.initial_velocity_min=20;process.initial_velocity_max=28;process.gravity=Vector3(0,-3,0);process.emission_shape=ParticleProcessMaterial.EMISSION_SHAPE_BOX;process.emission_box_extents=Vector3(18,8,18)
	process.collision_mode=ParticleProcessMaterial.COLLISION_HIDE_ON_CONTACT;process.sub_emitter_mode=ParticleProcessMaterial.SUB_EMITTER_AT_COLLISION;process.sub_emitter_amount_at_collision=2;process.sub_emitter_keep_velocity=true;rain.process_material=process
	var quad:=QuadMesh.new();quad.size=Vector2(0.016,0.36);var rain_material := _mat(Color(0.19,0.25,0.29));rain_material.shading_mode=BaseMaterial3D.SHADING_MODE_UNSHADED;quad.material=rain_material;rain.draw_pass_1=quad;add_child(rain)
	var collision := GPUParticlesCollisionBox3D.new(); collision.name = "RainGroundCollision"; collision.size = Vector3(38,0.18,38); collision.position.y = -6.0; rain.add_child(collision)
	var splashes := GPUParticles3D.new(); splashes.name = "RainSplashes"; splashes.amount = 900; splashes.lifetime = 0.34; splashes.explosiveness = 0.0
	splashes.transform_align = GPUParticles3D.TRANSFORM_ALIGN_Z_BILLBOARD
	splashes.local_coords = false
	splashes.visibility_aabb = AABB(Vector3(-35,-14,-35),Vector3(70,16,70))
	var splash_process := ParticleProcessMaterial.new(); splash_process.direction = Vector3.UP; splash_process.spread = 78.0; splash_process.initial_velocity_min = 0.35; splash_process.initial_velocity_max = 1.8; splash_process.gravity = Vector3(0,-5.0,0); splash_process.scale_min = 0.035; splash_process.scale_max = 0.11; splashes.process_material = splash_process
	var splash_mesh := QuadMesh.new(); splash_mesh.size = Vector2(0.12,0.12); var splash_mat := _mat(Color(0.14,0.2,0.22)); splash_mat.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED; splash_mat.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA; splash_mat.albedo_color.a = 0.45; splash_mesh.material = splash_mat; splashes.draw_pass_1 = splash_mesh; add_child(splashes)
	rain.sub_emitter = NodePath("../RainSplashes")
	_setup_audio()

func _make_noise_stream(sample_count: int, mix_rate: int, thunder: bool) -> AudioStreamWAV:
	var stream := AudioStreamWAV.new(); stream.format = AudioStreamWAV.FORMAT_16_BITS; stream.mix_rate = mix_rate; stream.stereo = false
	stream.loop_mode = AudioStreamWAV.LOOP_DISABLED if thunder else AudioStreamWAV.LOOP_FORWARD; stream.loop_end = sample_count
	var data := PackedByteArray(); data.resize(sample_count * 2)
	for i in range(sample_count):
		var t := float(i) / float(mix_rate)
		var envelope := exp(-t * 2.3) if thunder else 1.0
		var amplitude := 0.45 if thunder else 0.16
		var tonal := sin(TAU * 57.0 * t) * 0.45 if thunder else 0.0
		var sample := (tonal + randf_range(-0.5,0.5) * (amplitude if thunder else 0.7)) * envelope
		data.encode_s16(i * 2, int(clampf(sample, -1.0, 1.0) * 10000.0))
	stream.data = data
	return stream

func _make_footstep_stream() -> AudioStreamWAV:
	var stream := AudioStreamWAV.new(); stream.format=AudioStreamWAV.FORMAT_16_BITS; stream.mix_rate=22050; stream.stereo=false
	var count := 2205; var data := PackedByteArray(); data.resize(count*2)
	for i in range(count):
		var t := float(i)/22050.0
		var envelope := exp(-t*42.0)
		var sample := (sin(TAU*92.0*t)*0.25+randf_range(-0.65,0.65))*envelope
		data.encode_s16(i*2,int(clampf(sample,-1.0,1.0)*7000.0))
	stream.data=data
	return stream

func _make_breath_stream() -> AudioStreamWAV:
	var stream := AudioStreamWAV.new(); stream.format=AudioStreamWAV.FORMAT_16_BITS; stream.mix_rate=22050; stream.stereo=false
	stream.loop_mode=AudioStreamWAV.LOOP_FORWARD; stream.loop_end=44100
	var data := PackedByteArray(); data.resize(44100*2)
	for i in range(44100):
		var t := float(i)/22050.0
		var breath := pow(maxf(0.0,sin(PI*t/2.0)),2.0)
		var sample := sin(TAU*62.0*t)*breath*0.24+sin(TAU*83.0*t)*breath*0.08
		data.encode_s16(i*2,int(sample*6500.0))
	stream.data=data
	return stream

func play_footstep(position: Vector3, running: bool) -> void:
	if not is_instance_valid(footsteps_audio): return
	footsteps_audio.global_position=position
	footsteps_audio.volume_db=-16.0 if running else -22.0
	footsteps_audio.play()
	if running:
		for hunter in hunter_nodes:
			if is_instance_valid(hunter) and hunter.global_position.distance_to(position)<15.0: hunter.hear_noise(position)

func make_hunter_audio() -> AudioStreamPlayer3D:
	var audio := AudioStreamPlayer3D.new(); audio.add_to_group("procedural_audio"); audio.name="Breathing"; audio.stream=_make_breath_stream(); audio.volume_db=-27.0; audio.max_distance=28.0; audio.unit_size=5.0
	return audio

func _setup_audio() -> void:
	rain_bus_index = AudioServer.get_bus_index("Weather")
	if rain_bus_index < 0:
		AudioServer.add_bus(); rain_bus_index = AudioServer.get_bus_count() - 1; AudioServer.set_bus_name(rain_bus_index, "Weather"); AudioServer.set_bus_volume_db(rain_bus_index, -20.0)
	rain_filter = AudioEffectBandPassFilter.new(); rain_filter.cutoff_hz = 650.0; rain_filter.resonance = 0.7; AudioServer.add_bus_effect(rain_bus_index, rain_filter); AudioServer.set_bus_effect_enabled(rain_bus_index, 0, false)
	var distant_rain := RAIN_LOOP.duplicate() as AudioStreamOggVorbis; distant_rain.loop = true
	rain_audio = AudioStreamPlayer.new(); rain_audio.add_to_group("procedural_audio"); rain_audio.name="RainAudio"; rain_audio.bus="Weather"; rain_audio.stream=distant_rain; rain_audio.volume_db=-19.0; add_child(rain_audio); rain_audio.play()
	var canopy_rain := CANOPY_RAIN_LOOP.duplicate() as AudioStreamOggVorbis; canopy_rain.loop = true
	canopy_rain_audio = AudioStreamPlayer3D.new(); canopy_rain_audio.add_to_group("procedural_audio"); canopy_rain_audio.name="CanopyRainAudio"; canopy_rain_audio.bus="Weather"; canopy_rain_audio.stream=canopy_rain; canopy_rain_audio.volume_db=-27.0; canopy_rain_audio.max_distance=18.0; canopy_rain_audio.unit_size=7.0; add_child(canopy_rain_audio); canopy_rain_audio.play()
	thunder_audio = AudioStreamPlayer3D.new(); thunder_audio.add_to_group("procedural_audio"); thunder_audio.name="ThunderAudio"; thunder_audio.volume_db=-10; thunder_audio.max_distance=300; thunder_audio.unit_size=40; thunder_audio.stream=_make_noise_stream(66150,22050,true); add_child(thunder_audio)
	footsteps_audio=AudioStreamPlayer3D.new(); footsteps_audio.add_to_group("procedural_audio"); footsteps_audio.name="Footsteps"; footsteps_audio.stream=_make_footstep_stream(); footsteps_audio.max_distance=15.0; footsteps_audio.unit_size=4.0; add_child(footsteps_audio)
	echo_filter = AudioEffectLowPassFilter.new()
	echo_filter.cutoff_hz = 900.0
	AudioServer.add_bus_effect(0,echo_filter)
	AudioServer.set_bus_effect_enabled(0,AudioServer.get_bus_effect_count(0)-1,false)
	echo_audio = AudioStreamPlayer.new()
	echo_audio.name = "EchoTinnitus"
	echo_audio.add_to_group("procedural_audio")
	echo_audio.volume_db = -31.0
	var ringing := AudioStreamWAV.new()
	ringing.format = AudioStreamWAV.FORMAT_16_BITS
	ringing.mix_rate = 22050
	ringing.loop_mode = AudioStreamWAV.LOOP_FORWARD
	ringing.loop_end = 22050
	var ringing_data := PackedByteArray()
	ringing_data.resize(44100)
	for sample_index in range(22050):
		var t := float(sample_index)/22050.0
		ringing_data.encode_s16(sample_index*2,int(sin(TAU*1800.0*t)*1800.0))
	ringing.data = ringing_data
	echo_audio.stream = ringing
	add_child(echo_audio)
	pulse_noise_audio = AudioStreamPlayer.new()
	pulse_noise_audio.name = "SpectrumRadioNoise"
	pulse_noise_audio.add_to_group("procedural_audio")
	pulse_noise_audio.stream = _make_noise_stream(22050,22050,false)
	pulse_noise_audio.volume_db = -45.0
	add_child(pulse_noise_audio)
	daylight_audio = AudioStreamPlayer.new()
	daylight_audio.name = "DaylightEnergyDisorder"
	daylight_audio.add_to_group("procedural_audio")
	daylight_audio.volume_db = -26.0
	var chirp := AudioStreamWAV.new()
	chirp.format = AudioStreamWAV.FORMAT_16_BITS
	chirp.mix_rate = 22050
	var chirp_count := int(.85*22050)
	var chirp_data := PackedByteArray()
	chirp_data.resize(chirp_count*2)
	var chirp_phase := 0.0
	for sample_index in range(chirp_count):
		var t := float(sample_index)/22050.0
		var envelope := sin(PI*t/.85)
		chirp_phase += TAU*(420.0+900.0*exp(-t*5.0)+70.0*sin(t*31.0))/22050.0
		chirp_data.encode_s16(sample_index*2,int(envelope*(sin(chirp_phase)+.16*sin(chirp_phase*1.97))*6000.0))
	chirp.data = chirp_data
	daylight_audio.stream = chirp
	add_child(daylight_audio)

func set_filtering(enabled: bool) -> void:
	if is_instance_valid(rain_filter): AudioServer.set_bus_effect_enabled(rain_bus_index, 0, enabled)
	if is_instance_valid(rain_audio): rain_audio.volume_db = -26.0 if enabled else -20.0

func _play_thunder_after_delay(position: Vector3) -> void:
	var delay := position.distance_to(player.global_position)/343.0 + .08
	await get_tree().create_timer(delay,false).timeout
	if is_instance_valid(thunder_audio) and not GameState.game_over:
		thunder_audio.global_position = position
		thunder_audio.play()

func _build_hud() -> void:
	hud_controller=HUD_CONTROLLER.new();add_child(hud_controller);hud_controller.setup(self)

func _process(delta: float) -> void:
	if paused: return
	gameplay_elapsed += delta
	FOREST_DETAIL.set_motion_time(gameplay_elapsed)
	TERRAIN_DETAIL.set_motion_time(gameplay_elapsed)
	_update_echo_feedback()
	_update_pulse_noise_feedback()
	lightning_energy = storm_controller.lightning_energy
	if player:
		var rain: GPUParticles3D=get_node_or_null("Rain")
		if rain: rain.global_position=player.global_position+Vector3(0,6,0)
		var splashes: GPUParticles3D = get_node_or_null("RainSplashes")
		if splashes and rain: splashes.global_position = rain.global_position-Vector3(0,6,0)
		if is_instance_valid(canopy_rain_audio): canopy_rain_audio.global_position=player.global_position+Vector3(0,3.5,0)
	for i in range(fields.size()-1,-1,-1):
		fields[i].time-=delta
		if fields[i].time<=0: fields[i].node.queue_free();fields.remove_at(i)
	for i in range(traces.size()-1,-1,-1):
		traces[i].time-=delta*1.8
		traces[i].visible_time=maxf(0.0,float(traces[i].get("visible_time",0.0))-delta)
		if traces[i].visible_time <= 0.0 and is_instance_valid(traces[i].node): traces[i].node.visible=false
		if traces[i].time<=0: traces[i].node.queue_free();traces.remove_at(i)
	if player: _apply_fields()

func _on_lightning_started() -> void:
	if player:
		player.afterimage_ready=true; player.afterimage_window=5.0
		player.capture_lightning()
	_capture_flash_snapshot()
	var afterimage_slot := GameState.equipped.find("afterimage")
	_notice("闪电照亮了平原。按 %d 延长视觉后像。" % (afterimage_slot+1) if afterimage_slot >= 0 else "闪电照亮了平原。")
	_play_thunder_after_delay(storm_controller.strike_position)

func _apply_fields() -> void:
	player.in_mire=false;player.in_salt=false
	for field in fields:
		if player.global_position.distance_to(field.node.global_position)<field.radius:
			if field.kind=="mire": player.in_mire=true
			if field.kind=="salt": player.in_salt=true
	for hunter in hunter_nodes:
		if not is_instance_valid(hunter): continue
		for field in fields:
			if hunter.global_position.distance_to(field.node.global_position)<field.radius and field.kind=="salt":
				hunter.slow_timer=0.2
				var hunter_id := hunter.get_instance_id()
				var has_active_trace := traces.any(func(trace): return trace.salt_reactive and trace.time > 0.0 and is_instance_valid(trace.node) and trace.get("source_hunter_id",0) == hunter_id)
				if not has_active_trace: _spawn_trace(hunter.global_position,true,hunter_id)

func update_hud() -> void:
	if is_instance_valid(hud_controller): hud_controller.update_display()

func research_hint() -> String:
	var closest: Node3D
	var distance := INF
	var targets: Array = objective_nodes if not objective_nodes.is_empty() else [exit_node]
	for item in targets:
		if not is_instance_valid(item): continue
		var d: float = player.global_position.distance_to(item.global_position)
		if d < distance: closest = item; distance = d
	if closest == null: return ""
	var offset := player.global_basis.inverse()*(closest.global_position-player.global_position)
	var direction := "前方" if offset.z <= 0 else "身后"
	if absf(offset.x) > absf(offset.z)*.45:
		direction = ("左" if offset.x < 0 else "右")+("前方" if offset.z <= 0 else "后方")
	var target_name: String = closest.get_meta("landmark_name","学院出口")
	return "%s · %s · %d米%s" % [target_name,direction,int(distance)," · E收集研究书" if distance < 3 and not objective_nodes.is_empty() else ""]

func hunter_state_label() -> String:
	var charging := 0
	for hunter in hunter_nodes:
		if is_instance_valid(hunter) and hunter.charge_phase == hunter.ChargePhase.CHARGING: charging += 1
	return "%d只追踪 / %d只冲刺" % [hunter_nodes.size(),charging]

func interact() -> void:
	if is_gameplay_blocked(): return
	var nearest: Node3D=null;var best:=3.0
	for node in objective_nodes:
		if not is_instance_valid(node): continue
		var d:=player.global_position.distance_to(node.global_position)
		if d<best: best=d;nearest=node
	if nearest:
		var record_id := int(nearest.get_meta("objective_index", -1))
		var research_result: Dictionary = research_manager.collect(record_id)
		if not research_result.ok: _notice("这份研究记录已归档。"); return
		objective_nodes.erase(nearest);nearest.queue_free();collected=research_result.count
		_notice("研究记录 %d/3 已收录。选择一项能力强化。" % collected)
		_sync_modal_state()
		update_hud();return
	if exit_node and player.global_position.distance_to(exit_node.global_position)<5:
		if collected>=3: finish(true)
		else: _notice("学院出口尚未响应：还缺 %d 份研究记录。" % (3-collected))
	else: _notice("附近没有可交互目标。")

func _notification(what: int) -> void:
	if what == NOTIFICATION_WM_WINDOW_FOCUS_OUT and _can_change_modal():
		paused = true
		notebook = false
		_sync_modal_state()

func _window_is_focused() -> bool:
	return DisplayServer.get_name() == "headless" or DisplayServer.window_is_focused(get_window().get_window_id())

func _can_change_modal() -> bool:
	return _modal_ready and not _leaving and is_inside_tree() and not is_queued_for_deletion() and not GameState.game_over

func is_gameplay_blocked() -> bool:
	return paused or notebook or GameState.game_over or _leaving or (is_instance_valid(research_manager) and research_manager.has_pending_upgrade())

func _sync_modal_state() -> void:
	if not _modal_ready or not is_inside_tree() or is_queued_for_deletion(): return
	var blocked := is_gameplay_blocked()
	get_tree().paused = blocked
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE if blocked else Input.MOUSE_MODE_CAPTURED
	if blocked and is_instance_valid(player):
		player.clear_gameplay_actions()
		player.velocity.x = 0.0
		player.velocity.z = 0.0
		player.is_sprinting = false
	if GameState.game_over or _leaving:
		hud_controller.hide_handbook()
		hud_controller.hide_pause()
		hud_controller.hide_upgrade()
	elif notebook:
		hud_controller.hide_pause()
		hud_controller.hide_upgrade()
	elif paused:
		hud_controller.hide_handbook()
		hud_controller.hide_upgrade()
		hud_controller.show_pause()
	elif research_manager.has_pending_upgrade():
		hud_controller.hide_handbook()
		hud_controller.hide_pause()
		hud_controller.show_upgrade(GameState.upgrade_options())
	else:
		hud_controller.hide_handbook()
		hud_controller.hide_pause()
		hud_controller.hide_upgrade()

func confirm_upgrade(ability_id: String) -> void:
	if not _can_change_modal() or not research_manager.has_pending_upgrade(): return
	var result: Dictionary = research_manager.clear_without_upgrade() if ability_id.is_empty() else research_manager.apply_upgrade(ability_id)
	if not result.ok:
		_notice("这项能力当前无法强化，请重新选择。")
	else:
		if not ability_id.is_empty():
			_notice("%s已提升至%s。%s" % [GameState.skill_data(ability_id).name.split(" /")[0], GameState.LEVEL_NAMES[result.level - 1], "三份报告齐备，出口已开启。" if collected == 3 else "继续寻找科研报告。"])
		else:
			_notice("本局可强化能力已满。" + ("三份报告齐备，出口已开启。" if collected == 3 else "继续寻找科研报告。"))
	hud_controller.hide_upgrade()
	_sync_modal_state()
	update_hud()

func toggle_pause() -> void:
	if not _can_change_modal(): return
	if paused and not _window_is_focused(): return
	paused = not paused
	_sync_modal_state()

func toggle_handbook() -> void:
	if not _can_change_modal(): return
	if not notebook and not _window_is_focused(): return
	notebook=not notebook
	if notebook:
		var entries: Array[String] = []
		var abilities: Array[String] = ["lamp"]
		abilities.append_array(GameState.equipped)
		for id in abilities:
			var data: Dictionary = GameState.skill_data(id)
			entries.append(data.name + " · " + GameState.LEVEL_NAMES[GameState.ability_level(id) - 1] + "\n" + data.science + "\n" + data.effect + "\n代价：" + data.cost + "\n本局参数：" + GameState.upgrade_benefit(id, GameState.ability_level(id)))
		var fusion_entries: Array[String] = ["\n学科融合（✓ 已观察，· 待触发）"]
		for pair_id in fusion_manager.DESCRIPTIONS:
			var mark := "✓ " if fusion_manager.discovered.has(pair_id) else "· "
			fusion_entries.append(mark + fusion_manager.DESCRIPTIONS[pair_id])
		hud_controller.show_handbook(entries,fusion_entries)
	else:
		hud_controller.hide_handbook()
	_sync_modal_state()

func request_retry() -> void:
	_request_scene_change(true)

func request_menu() -> void:
	_request_scene_change(false)

func _request_scene_change(retry: bool) -> void:
	if _leaving or is_queued_for_deletion(): return
	_leaving = true
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	hud_controller.set_process_input(false)
	if retry: retry_requested.emit()
	else: return_to_menu.emit()

func cycle_filter() -> void:
	filter_index=(filter_index+1)%3
	if is_instance_valid(rain_filter): rain_filter.cutoff_hz = [350.0,650.0,1400.0][filter_index]
	_notice("保留雨声中的%s频段；其余雨声频率被衰减。" % ["低频", "中频", "高频"][filter_index])

func _notice(text: String) -> void:
	if is_instance_valid(hud_controller): hud_controller.notice(text)

func notice(text: String) -> void: _notice(text)

func finish(won: bool) -> void:
	if GameState.game_over:return
	GameState.game_over=true;GameState.outcome="胜利" if won else "You became part of the experiment."
	notebook = false
	_sync_modal_state()
	hud_controller.show_outcome(won)

func emit_echo(position: Vector3, highlight_duration: float = 7.0) -> void:
	echo_positions.append(position)
	for h in hunter_nodes:
		if is_instance_valid(h):h.hear_noise(position)
	var ring:=MeshInstance3D.new();var torus:=TorusMesh.new();torus.inner_radius=0.08;torus.outer_radius=0.12;ring.mesh=torus;ring.position=position+Vector3(0,0.1,0);ring.material_override=_mat(Color(0.4,0.72,0.65,true));add_child(ring)
	var ring_material := _mat(Color(0.4,0.72,0.65,0.8)); ring_material.transparency=BaseMaterial3D.TRANSPARENCY_ALPHA; ring.material_override=ring_material
	var tween:=create_tween();tween.tween_property(ring,"scale",Vector3.ONE*18,1.2);tween.parallel().tween_property(ring_material,"albedo_color:a",0.0,1.2);tween.tween_callback(ring.queue_free)
	for obj in objective_nodes: obj.highlight(highlight_duration)
	_notice("回声脉冲发出：研究记录被标亮。奶龙仍持续锁定你。")

func _capture_flash_snapshot() -> void:
	flash_snapshot_points.clear()
	if not player: return
	for hunter in hunter_nodes:
		if not is_instance_valid(hunter) or player.camera.is_position_behind(hunter.global_position): continue
		flash_snapshot_points.append(player.camera.unproject_position(hunter.global_position + Vector3(0,1.45,0)))

func show_afterimage(duration: float) -> void:
	var overlay:=ColorRect.new();overlay.color=Color(0.5,0.67,0.64,0.08);overlay.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT);overlay.mouse_filter=Control.MOUSE_FILTER_IGNORE;hud_controller.add_child(overlay)
	for saved_point in flash_snapshot_points:
		var marker:=Label.new();marker.text="◇";marker.position=saved_point-Vector2(12,12);marker.add_theme_font_size_override("font_size",22);marker.add_theme_color_override("font_color",Color(0.56,0.83,0.69,0.9));overlay.add_child(marker)
	var timer:=Timer.new();timer.process_mode=Node.PROCESS_MODE_PAUSABLE;timer.wait_time=duration;timer.one_shot=true;overlay.add_child(timer);timer.timeout.connect(overlay.queue_free);timer.start()
	_notice("雷痕保留了闪电时敌人的旧屏幕位置；目标移动后，残像也不会更新。")

func reveal_traces(improved: bool = false, reveal_duration: float = 8.0, salt_emission: float = 1.2) -> void:
	var count:=0
	for trace in traces:
		if not is_instance_valid(trace.node): continue
		trace.node.visible=true; trace.visible_time=reveal_duration; count+=1
		var material := trace.node.material_override as StandardMaterial3D
		if material: material.emission_energy_multiplier = salt_emission if improved and trace.salt_reactive else 0.6
	_notice("鲁米诺显影 %d 处仍未被暴雨冲淡的反应性痕迹。" % count if count>0 else "没有合适的催化痕迹；干净地面不会发光。")

func place_field(kind: String, position: Vector3, radius: float = 2.4, duration: float = 11.0) -> void:
	var node:=MeshInstance3D.new();var mesh:=CylinderMesh.new();mesh.top_radius=radius;mesh.bottom_radius=radius;mesh.height=0.06;node.mesh=mesh;node.position=position+Vector3(0,0.03,0);node.material_override=_mat(Color(0.04,0.055,0.045,0.72) if kind=="mire" else Color(0.65,0.66,0.59,0.32),kind=="salt");add_child(node)
	fields.append({"node":node,"kind":kind,"time":duration,"radius":radius})
	_notice("泥区已形成：追猎者减速且无法开始冲刺；玩家低速受阻，高速可通过。暴雨会逐渐稀释。" if kind=="mire" else "高渗盐阵已形成。暴雨会逐渐稀释。")

func _spawn_trace(position: Vector3, salt_reactive := false, source_hunter_id := 0) -> void:
	var mark:=MeshInstance3D.new();var mesh:=SphereMesh.new();mesh.radius=0.16;mesh.height=0.05;mark.mesh=mesh;mark.position=position+Vector3(0,0.04,0);mark.visible=false;mark.material_override=_mat(Color(0.2,0.55,0.95),true);add_child(mark);traces.append({"node":mark,"time":20.0,"visible_time":0.0,"salt_reactive":salt_reactive,"source_hunter_id":source_hunter_id})

func check_fusion(skill: String) -> void:
	var discovered_description: String = fusion_manager.check_trigger(skill)
	if not discovered_description.is_empty():
		var titles: Array[String] = []
		for description in discovered_description.split("\n"): titles.append(description.split("｜")[0])
		_notice("融合记录发现：%s。按 Tab 查看手册。" % "、".join(titles))

func toggle_mire_state(_enabled: bool) -> void: pass

func damage_hunter_trace(position: Vector3, salt_reactive := false) -> void: _spawn_trace(position,salt_reactive)

func release_spectrum(point_shot: bool, values: Dictionary, charge_ratio: float) -> Dictionary:
	var origin: Vector3 = player.camera.global_position
	var forward: Vector3 = -player.camera.global_basis.z
	var maximum: float = values.range if point_shot else values.burst_range
	var endpoint := origin+forward*maximum
	var affected := 0
	if point_shot:
		var query := PhysicsRayQueryParameters3D.create(origin,endpoint,1,[player.get_rid()])
		var hit := get_world_3d().direct_space_state.intersect_ray(query)
		if not hit.is_empty():
			endpoint = hit.position
			if hit.collider.has_method("repel"):
				hit.collider.repel(forward,float(values.impulse),.2)
				affected = 1
	else:
		var cosine := cos(deg_to_rad(float(values.burst_half_angle_deg)))
		for hunter in hunter_nodes:
			if not is_instance_valid(hunter): continue
			var target_point: Vector3 = hunter.global_position+Vector3(0,1.3,0)
			var offset := target_point-origin
			if offset.length() > maximum or forward.dot(offset.normalized()) < cosine: continue
			var query := PhysicsRayQueryParameters3D.create(origin,target_point,1,[player.get_rid()])
			var hit := get_world_3d().direct_space_state.intersect_ray(query)
			if not hit.is_empty() and hit.collider != hunter: continue
			hunter.repel(offset,float(values.burst_impulse)*clampf(charge_ratio,.12,1.0),.45)
			affected += 1
	_spectrum_beam(player.equipment.beam_socket.global_position,endpoint,point_shot)
	_notice("点射击退了追猎者。" if point_shot and affected>0 else ("点射已释放；未命中追猎者。" if point_shot else "集中爆发击退 %d 只追猎者，当前储能已释放。" % affected))
	return {"hits":affected,"endpoint":endpoint}

func _spectrum_beam(start: Vector3, finish_position: Vector3, point_shot: bool) -> void:
	var direction := finish_position-start
	if direction.length_squared() < .001: return
	var beam := MeshInstance3D.new()
	beam.name = "SpectrumPulse" if point_shot else "SpectrumBurst"
	var mesh := CylinderMesh.new()
	mesh.top_radius = .013 if point_shot else .04
	mesh.bottom_radius = .01 if point_shot else .018
	mesh.height = direction.length(); mesh.radial_segments = 12
	beam.mesh = mesh; beam.position = (start+finish_position)*.5
	beam.quaternion = Quaternion(Vector3.UP,direction.normalized())
	var material := _mat(Color(.46,.83,.73,.72),true)
	material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	beam.material_override = material
	beam.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(beam)
	var tween := create_tween()
	tween.tween_property(material,"albedo_color:a",0.0,.11 if point_shot else .22)
	tween.tween_callback(beam.queue_free)

func play_disorientation_sound() -> void:
	if not is_instance_valid(disorientation_audio):
		disorientation_audio = AudioStreamPlayer.new()
		disorientation_audio.name = "PulseDisorientation"
		disorientation_audio.add_to_group("procedural_audio")
		disorientation_audio.stream = HUNTER_VOICE.warning_stream
		disorientation_audio.volume_db = -18.0
		add_child(disorientation_audio)
	disorientation_audio.play()
	_notice("乱频噪声过载：短暂眩晕与尖叫，仍可控制方向。")

func _update_echo_feedback() -> void:
	if not is_instance_valid(player) or not is_instance_valid(echo_filter): return
	var active: bool = player.echo_deafness > 0.0
	echo_filter.cutoff_hz = lerpf(16000.0,900.0,clampf(player.echo_deafness/.8,0.0,1.0))
	for index in range(AudioServer.get_bus_effect_count(0)):
		if AudioServer.get_bus_effect(0,index) == echo_filter:
			AudioServer.set_bus_effect_enabled(0,index,active)
	if active and not echo_audio.playing: echo_audio.play()
	elif not active and echo_audio.playing: echo_audio.stop()

func play_daylight_sound() -> void:
	if is_instance_valid(daylight_audio): daylight_audio.play()

func _update_pulse_noise_feedback() -> void:
	if not is_instance_valid(player) or not is_instance_valid(pulse_noise_audio): return
	var amount: float = clampf(player.noise/100.0,0.0,1.0)
	pulse_noise_audio.volume_db = lerpf(-45.0,-25.0,amount)
	if amount > .02 and not pulse_noise_audio.playing: pulse_noise_audio.play()
	elif amount <= .02 and pulse_noise_audio.playing: pulse_noise_audio.stop()
