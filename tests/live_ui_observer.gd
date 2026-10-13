extends Node
# Observes native user input; it does not drive UI/gameplay actions.
const MAIN := preload("res://scripts/core/main.gd")
var main
var directory := ""
var events: Array[Dictionary] = []
var capture_index := 0
var status_timer := 0.0

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	directory = OS.get_environment("HDF_LIVE_OBSERVER_DIR")
	assert(not directory.is_empty(),"An explicit acceptance directory is required")
	assert(DisplayServer.get_name() != "headless","Live native input requires a graphical window")
	DirAccess.make_dir_recursive_absolute(directory)
	main = MAIN.new()
	add_child(main)
	print("LIVE UI OBSERVER READY: actual production menu; F9 captures current framebuffer/state")

func current_state() -> Dictionary:
	var state := {"screen":main.screen,"selected":main.selected.duplicate(),"mouse_mode":Input.mouse_mode,"tree_paused":get_tree().paused,"viewport_size":get_viewport().get_visible_rect().size,"tick_msec":Time.get_ticks_msec(),"archive":GameState.archive_path,"game_over":GameState.game_over,"outcome":GameState.outcome}
	if is_instance_valid(main.world):
		var world = main.world
		state.merge({"world_paused":world.paused,"handbook":world.notebook,"reports":world.collected,"pending_upgrade":world.research_manager.has_pending_upgrade(),"gameplay_blocked":world.is_gameplay_blocked(),"world_clock":world.gameplay_elapsed,"actors":world.hunter_nodes.size(),"levels":GameState.skill_levels.duplicate(),"energy":world.player.energy,"noise":world.player.noise,"pulse_mode":world.player.pulse_mode,"lamp_enabled":world.player.lamp_enabled,"daylight_time":world.player.daylight_time,"position":world.player.global_position,"velocity":world.player.velocity})
		var position: Vector3 = world.player.global_position
		state.merge({"position_xyz":[position.x,position.y,position.z],"yaw_radians":world.player.rotation.y,"pitch_radians":world.player.pitch,"stamina":world.player.stamina,"hits":world.player.hits})
	var focused := get_viewport().gui_get_focus_owner()
	state["focus"] = focused.text if focused is Button else (focused.name if is_instance_valid(focused) else "none")
	return state

func _process(delta: float) -> void:
	status_timer += delta
	if status_timer >= .25:
		status_timer = 0.0
		var state := current_state()
		FileAccess.open(directory.path_join("current-state.json"),FileAccess.WRITE).store_string(JSON.stringify(state,"\t"))
		var timeline_path := directory.path_join("state-timeline.jsonl")
		var timeline := FileAccess.open(timeline_path,FileAccess.READ_WRITE if FileAccess.file_exists(timeline_path) else FileAccess.WRITE)
		timeline.seek_end()
		timeline.store_line(JSON.stringify(state))
		FileAccess.open(directory.path_join("native-input-events.json"),FileAccess.WRITE).store_string(JSON.stringify(events,"\t"))

func _input(event: InputEvent) -> void:
	if event is InputEventKey and not event.echo:
		events.append({"event":event.as_text(),"pressed":event.pressed,"tick_msec":Time.get_ticks_msec()})
		if event.pressed and event.keycode == KEY_F9: capture.call_deferred()
	elif event is InputEventMouseButton:
		events.append({"event":event.as_text(),"pressed":event.pressed,"position":event.position,"tick_msec":Time.get_ticks_msec()})
	elif event is InputEventMouseMotion:
		events.append({"event":"mouse_motion","relative_xy":[event.relative.x,event.relative.y],"tick_msec":Time.get_ticks_msec()})

func capture() -> void:
	await RenderingServer.frame_post_draw
	capture_index += 1
	var label := "%02d-%s" % [capture_index,main.screen]
	var pixels := get_viewport().get_texture().get_image()
	assert(pixels.get_size() == Vector2i(1920,1080),"Native input evidence uses a real1920x1080 framebuffer")
	pixels.save_png(directory.path_join(label+".png"))
	var state := current_state()
	state["capture"] = label
	state["actual_native_input"] = true
	state["observer_driven_actions"] = false
	FileAccess.open(directory.path_join(label+".json"),FileAccess.WRITE).store_string(JSON.stringify(state,"\t"))
	FileAccess.open(directory.path_join("native-input-events.json"),FileAccess.WRITE).store_string(JSON.stringify(events,"\t"))
	print("LIVE INPUT CAPTURE ",label," ",JSON.stringify(state))
