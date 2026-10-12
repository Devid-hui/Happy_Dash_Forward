extends Node

# A render/AI workload, not a gameplay or difficulty test. Only this scene ignores
# focus and outcome changes so a scripted route can complete without a death menu.
class BenchmarkWorld extends "res://scripts/world/world.gd":
	func _notification(_what: int) -> void:
		pass

	func _window_is_focused() -> bool:
		return true

	func _can_change_modal() -> bool:
		return false

	func finish(_won: bool) -> void:
		pass

const ROUTE := [Vector3.ZERO, Vector3(-24,0,-28), Vector3(35,0,-12), Vector3(22,0,34), Vector3(72,0,65), Vector3.ZERO]
const STRIKES := [Vector3(60,0,-40), Vector3(-30,0,50), Vector3(20,0,-25), Vector3(-65,0,-30)]
var world
var output: FileAccess
var duration := 60.0
var warmup := 5.0
var elapsed := 0.0
var measuring := false
var previous_usec := 0
var next_strike := 4.0
var strike_index := 0
var restart_count := 10
var startup_usec := 0
var active := false
var result_path := ""

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	duration = float(OS.get_environment("MIDNIGHT_BENCH_SECONDS")) if OS.has_environment("MIDNIGHT_BENCH_SECONDS") else 60.0
	warmup = float(OS.get_environment("MIDNIGHT_BENCH_WARMUP")) if OS.has_environment("MIDNIGHT_BENCH_WARMUP") else 5.0
	restart_count = int(OS.get_environment("MIDNIGHT_BENCH_RESTARTS")) if OS.has_environment("MIDNIGHT_BENCH_RESTARTS") else 10
	result_path = OS.get_environment("MIDNIGHT_BENCH_OUTPUT")
	assert(not result_path.is_empty(), "MIDNIGHT_BENCH_OUTPUT must be an absolute CSV path")
	if DisplayServer.get_name() == "headless":
		push_error("Performance benchmark requires an actual Forward+ window")
		get_tree().quit(1)
		return
	DisplayServer.window_set_size(Vector2i(640,360))
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	call_deferred("run_benchmark")

func _make_world() -> void:
	seed(721)
	GameState.equipped = ["afterimage", "echo", "mire"]
	GameState.reset_run()
	GameState.reduced_flashes = false
	GameState.brightness = 1.0
	world = BenchmarkWorld.new()
	world.process_mode = Node.PROCESS_MODE_PAUSABLE
	add_child(world)
	# The product intentionally pauses background startup. This test suppresses
	# only that modal state, for both snapshots, while keeping all five hunters.
	world.paused = false
	world.notebook = false
	get_tree().paused = false
	world.hud_controller.hide_pause()
	world.player.set_process_unhandled_input(false)
	world.hud_controller.set_process_input(false)
	world.storm_controller.set_process(false)
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE

func run_benchmark() -> void:
	startup_usec = Time.get_ticks_usec()
	_make_world()
	var build_ms := (Time.get_ticks_usec() - startup_usec) / 1000.0
	await get_tree().process_frame
	await get_tree().process_frame
	output = FileAccess.open(result_path, FileAccess.WRITE)
	assert(output != null, "cannot create benchmark CSV")
	output.store_csv_line(["elapsed_s","frame_interval_ms","time_process_ms","physics_process_ms","draw_calls","objects_rendered","static_memory_bytes","video_memory_bytes","node_count","lightning_active"])
	var metadata := {
		"engine": Engine.get_version_info().string,
		"cpu": OS.get_processor_name(), "logical_cpu_count": OS.get_processor_count(),
		"adapter": RenderingServer.get_video_adapter_name(),
		"renderer": RenderingServer.get_current_rendering_method(),
		"driver": RenderingServer.get_current_rendering_driver_name(),
		"display_server": DisplayServer.get_name(),
		"window_size": [DisplayServer.window_get_size().x, DisplayServer.window_get_size().y],
		"viewport_size": [get_viewport().get_visible_rect().size.x, get_viewport().get_visible_rect().size.y],
		"seed": 721, "duration_seconds": duration, "warmup_seconds": warmup,
		"world_build_ms": build_ms, "vsync": "disabled", "frame_cap": "disabled",
		"route": "six waypoints in 60s; continuous 15s yaw sweep and small pitch sweep",
		"limitations": "scripted positions bypass walking collisions; five hunter AI remain active; benchmark-only focus/outcome suppression; fixed scheduled lightning; no skill casts or book collection"
	}
	var metadata_file := FileAccess.open(result_path + ".metadata.json", FileAccess.WRITE)
	metadata_file.store_string(JSON.stringify(metadata,"\t"))
	metadata_file.close()
	active = true
	print("PERFORMANCE START: ", result_path)
	await get_tree().create_timer(warmup, true).timeout
	elapsed = 0.0
	next_strike = 4.0
	strike_index = 0
	measuring = true
	previous_usec = Time.get_ticks_usec()
	await get_tree().create_timer(duration, true).timeout
	measuring = false
	active = false
	output.close()
	output = null
	var restarts: Array[Dictionary] = []
	for index in range(restart_count + 1):
		if index > 0:
			world.process_mode = Node.PROCESS_MODE_DISABLED
			world.queue_free()
			await get_tree().process_frame
			_make_world()
			await get_tree().process_frame
		await get_tree().create_timer(2.0,true).timeout
		var point := {"restart": index,"elapsed_s":Time.get_ticks_usec()/1000000.0,"static_memory_bytes":Performance.get_monitor(Performance.MEMORY_STATIC),"video_memory_bytes":Performance.get_monitor(Performance.RENDER_VIDEO_MEM_USED),"node_count":Performance.get_monitor(Performance.OBJECT_NODE_COUNT),"resource_count":Performance.get_monitor(Performance.OBJECT_RESOURCE_COUNT),"orphan_nodes":Performance.get_monitor(Performance.OBJECT_ORPHAN_NODE_COUNT)}
		restarts.append(point)
		print("PERFORMANCE RESTART: ", JSON.stringify(point))
	var restart_file := FileAccess.open(result_path + ".restarts.json",FileAccess.WRITE)
	restart_file.store_string(JSON.stringify(restarts,"\t"))
	restart_file.close()
	world.queue_free()
	await get_tree().process_frame
	await get_tree().create_timer(.5,true).timeout
	print("PERFORMANCE PASS: ", result_path)
	get_tree().quit()

func _process(delta: float) -> void:
	if not active or not is_instance_valid(world): return
	assert(not get_tree().paused and not world.paused, "performance workload must never be paused")
	elapsed += delta
	var segment := fmod(elapsed,60.0) / 12.0
	var route_index := mini(int(segment), ROUTE.size()-2)
	world.player.global_position = ROUTE[route_index].lerp(ROUTE[route_index+1],fmod(segment,1.0))
	world.player.velocity = Vector3.ZERO
	world.player.rotation.y = elapsed * TAU / 15.0
	world.player.camera.rotation.x = sin(elapsed * TAU / 20.0) * .2
	world.player.stamina = 100.0
	world.storm_controller._process(delta)
	# Turn off random scheduling; the same four map strikes run every 5.2s.
	world.storm_controller.next_flash = 1000.0
	if elapsed >= next_strike:
		world.storm_controller.trigger_strike(STRIKES[strike_index % STRIKES.size()])
		strike_index += 1
		next_strike += 5.2
	if not measuring: return
	var now := Time.get_ticks_usec()
	var interval_ms := (now - previous_usec) / 1000.0
	previous_usec = now
	output.store_csv_line([elapsed,interval_ms,Performance.get_monitor(Performance.TIME_PROCESS)*1000.0,Performance.get_monitor(Performance.TIME_PHYSICS_PROCESS)*1000.0,Performance.get_monitor(Performance.RENDER_TOTAL_DRAW_CALLS_IN_FRAME),Performance.get_monitor(Performance.RENDER_TOTAL_OBJECTS_IN_FRAME),Performance.get_monitor(Performance.MEMORY_STATIC),Performance.get_monitor(Performance.RENDER_VIDEO_MEM_USED),Performance.get_monitor(Performance.OBJECT_NODE_COUNT),int(world.storm_controller.flash_timer > 0.0)])
