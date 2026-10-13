extends Node
# This controlled workload uses actual rendering, physics and five active actors.
# Death prevention and replenishment exist only here and are recorded in the receipt.
class BenchmarkWorld:
	extends "res://scripts/world/world.gd"
	var contacts := 0
	func finish(_won: bool) -> void:
		contacts += 1
		player.hits = 0
	func _notification(_what: int) -> void: pass
	func _window_is_focused() -> bool: return true

const PHASES := ["rain_walk","five_near_chase","lightning_burst"]
var world
var output_directory := ""
var samples_per_phase := 720
var warmup_frames := 120
var frame_index := 0
var phase_index := 0
var previous_usec := 0
var samples: Array[Dictionary] = []
var receipt: Dictionary = {}

func _ready() -> void:
	var arguments := OS.get_cmdline_user_args()
	if arguments.has("--performance-parse-only"):
		print("NATIVE PERFORMANCE PROBE PARSE PASS: scene/autoload integration")
		get_tree().quit(0)
		return
	assert(DisplayServer.get_name() != "headless","Performance acceptance requires a real graphical display")
	for index in range(arguments.size()-1):
		if arguments[index] == "--performance-output": output_directory = arguments[index+1]
		if arguments[index] == "--performance-samples": samples_per_phase = int(arguments[index+1])
	assert(not output_directory.is_empty(),"An explicit output directory is required")
	DirAccess.make_dir_recursive_absolute(output_directory)
	GameState.set_archive_path(output_directory.path_join("isolated-benchmark-archive.json"))
	process_mode = Node.PROCESS_MODE_ALWAYS
	get_window().size = Vector2i(1920,1080)
	RenderingServer.viewport_set_measure_render_time(get_viewport().get_viewport_rid(),true)
	receipt = {
		"engine":Engine.get_version_info(),"device":RenderingServer.get_video_adapter_name(),
		"rendering_method":RenderingServer.get_current_rendering_method(),
		"controlled_workload":true,"ordinary_playtest":false,
		"controls":"benchmark-only death prevention, energy/stamina replenishment, staged near actors; production physics/AI/shaders/audio remain active",
		"msaa":get_viewport().msaa_3d,"taa":get_viewport().use_taa,"phases":[],"rebuild_ms":[],
		"raw_samples_file":"native-frame-samples.json"
	}
	_begin_phase()

func _begin_phase() -> void:
	Input.action_release("move_forward")
	Input.action_release("sprint")
	if is_instance_valid(world): world.free()
	GameState.equipped = ["echo","daylight","pulse"]
	GameState.reset_run()
	seed(731)
	var started := Time.get_ticks_usec()
	world = BenchmarkWorld.new()
	add_child(world)
	world.paused = false
	world._sync_modal_state()
	receipt.rebuild_ms.append(float(Time.get_ticks_usec()-started)/1000.0)
	frame_index = 0
	previous_usec = Time.get_ticks_usec()
	if PHASES[phase_index] == "rain_walk":
		Input.action_press("move_forward")
		Input.action_press("sprint")
	else:
		world.player.global_position = Vector3.ZERO
		world.player.rotation.y = 0.0
		for index in range(5):
			world.hunter_nodes[index].global_position = Vector3((index-2)*1.4,0,-7.0-abs(index-2)*.4)
		world.hunter_director.pending_initial.clear()
		world.hunter_director.initial_directions.clear()
		for hunter in world.hunter_nodes: hunter.set_physics_process(true)
	print("NATIVE PERF phase=",PHASES[phase_index]," actors=",world.hunter_nodes.size()," warmup=",warmup_frames)

func _process(_delta: float) -> void:
	if not is_instance_valid(world): return
	if world.paused:
		world.paused = false
		world._sync_modal_state()
	var now := Time.get_ticks_usec()
	var wall_ms := float(now-previous_usec)/1000.0
	previous_usec = now
	frame_index += 1
	world.player.stamina = 100.0
	if PHASES[phase_index] == "rain_walk":
		world.player.rotate_y(.007)
		if Vector2(world.player.position.x,world.player.position.z).length() > 70.0:
			world.player.position = Vector3.ZERO
	else:
		for index in range(5):
			var hunter = world.hunter_nodes[index]
			if hunter.global_position.distance_to(world.player.global_position) < 2.0:
				hunter.global_position = Vector3((index-2)*1.4,0,-7.0-abs(index-2)*.4)
				hunter.reset_after_relocation()
	if PHASES[phase_index] == "lightning_burst":
		if frame_index % 90 == 0:
			world.storm_controller.trigger_strike(Vector3(-5,0,-3))
			world.player.energy = 100.0
			world.player.fire_cooldown = 0.0
			world.player.pulse_mode = false
			world.player._pending_fire = true
		elif frame_index % 20 == 0:
			world.player.energy = 100.0
			world.player.pulse_mode = true
			world.player._pending_fire = true
	if frame_index > warmup_frames:
		var viewport_rid := get_viewport().get_viewport_rid()
		samples.append({
			"phase":PHASES[phase_index],"wall_ms":wall_ms,
			"cpu_render_ms":RenderingServer.viewport_get_measured_render_time_cpu(viewport_rid),
			"gpu_render_ms":RenderingServer.viewport_get_measured_render_time_gpu(viewport_rid),
			"process_ms":Performance.get_monitor(Performance.TIME_PROCESS)*1000.0,
			"physics_ms":Performance.get_monitor(Performance.TIME_PHYSICS_PROCESS)*1000.0,
			"draw_calls":Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME),
			"triangles":Performance.get_monitor(Performance.RENDER_TOTAL_PRIMITIVES_IN_FRAME),
			"video_memory_bytes":Performance.get_monitor(Performance.RENDER_VIDEO_MEM_USED),
			"actors":world.hunter_nodes.size(),"blocked":world.is_gameplay_blocked()
		})
	if frame_index == warmup_frames+samples_per_phase:
		await _finish_phase()

func _percentile(values: Array, fraction: float) -> float:
	values.sort()
	return float(values[mini(values.size()-1,int(ceil((values.size()-1)*fraction)))])

func _finish_phase() -> void:
	set_process(false)
	await RenderingServer.frame_post_draw
	var image := get_viewport().get_texture().get_image()
	assert(image.get_size() == Vector2i(1920,1080),"Measured framebuffer must actually be 1920x1080")
	image.save_png(output_directory.path_join("performance_%s.png" % PHASES[phase_index]))
	var current := samples.filter(func(sample): return sample.phase == PHASES[phase_index])
	var walls := current.map(func(sample): return sample.wall_ms)
	var gpu := current.map(func(sample): return sample.gpu_render_ms)
	var sum_wall := 0.0
	for value in walls: sum_wall += value
	var result := {
		"name":PHASES[phase_index],"samples":current.size(),"framebuffer":[1920,1080],
		"mean_fps":1000.0/(sum_wall/walls.size()),"wall_p50_ms":_percentile(walls,.50),
		"wall_p95_ms":_percentile(walls,.95),"wall_p99_ms":_percentile(walls,.99),
		"gpu_p95_ms":_percentile(gpu,.95),"gpu_timing_available":gpu.any(func(value): return value>0.0),
		"min_actors":current.map(func(sample): return sample.actors).min(),
		"blocked_frames":current.filter(func(sample): return sample.blocked).size(),
		"max_draw_calls":current.map(func(sample): return sample.draw_calls).max(),
		"max_triangles":current.map(func(sample): return sample.triangles).max(),
		"max_video_memory_bytes":current.map(func(sample): return sample.video_memory_bytes).max(),
		"benchmark_contact_events":world.contacts
	}
	receipt.phases.append(result)
	print("NATIVE PERF RESULT ",JSON.stringify(result))
	phase_index += 1
	if phase_index < PHASES.size():
		_begin_phase()
		set_process(true)
	else:
		Input.action_release("move_forward")
		Input.action_release("sprint")
		world.free()
		var clean_until := Time.get_ticks_msec()+100
		while Time.get_ticks_msec()<clean_until: await get_tree().process_frame
		FileAccess.open(output_directory.path_join("native-performance.json"),FileAccess.WRITE).store_string(JSON.stringify(receipt,"\t"))
		FileAccess.open(output_directory.path_join("native-frame-samples.json"),FileAccess.WRITE).store_string(JSON.stringify(samples))
		print("NATIVE PERFORMANCE CAPTURE COMPLETE: actual 1080p; measured results require review against 60 FPS budget")
		get_tree().quit(0)
