extends Node
# Controlled photographs of the production world; separate from input/performance acceptance.
class ReviewWorld:
	extends "res://scripts/world/world.gd"
	func _notification(_what: int) -> void: pass
	func _window_is_focused() -> bool: return true

var world
var directory := ""
var records: Array[Dictionary] = []

func _ready() -> void:
	var arguments := OS.get_cmdline_user_args()
	if arguments.has("--scene-review-parse-only"):
		print("NATIVE SCENE REVIEW PARSE PASS")
		get_tree().quit()
		return
	assert(DisplayServer.get_name() != "headless","Native scene review requires actual rendering")
	directory = OS.get_environment("HDF_SCENE_REVIEW_DIR")
	assert(not directory.is_empty(),"An explicit review output directory is required")
	DirAccess.make_dir_recursive_absolute(directory)
	process_mode = Node.PROCESS_MODE_ALWAYS
	get_window().size = Vector2i(1920,1080)
	GameState.set_archive_path(directory.path_join("isolated-review-archive.json"))
	GameState.equipped = ["echo","daylight","pulse"]
	GameState.reset_run()
	seed(731)
	world = ReviewWorld.new()
	add_child(world)
	world.player.set_physics_process(false)
	world.hunter_director.set_physics_process(false)
	world.storm_controller.set_process(false)
	for hunter in world.hunter_nodes: hunter.set_physics_process(false)
	world.player.energy = 100.0
	world.player.lamp_enabled = true
	world.player._update_sensory_feedback(.016,Vector2.ZERO)
	call_deferred("run_review")

func set_view(position: Vector3, target: Vector3) -> void:
	world.player.global_position = position
	world.player.rotation = Vector3.ZERO
	world.player.look_at(Vector3(target.x,position.y,target.z),Vector3.UP)
	world.player.camera.look_at(target,Vector3.UP)
	world.player.pitch = world.player.camera.rotation.x
	world.player.camera.rotation.z = 0.0
	world.player.lamp_light.visible = world.player.lamp_enabled

func _capture(label: String, frames: int = 90) -> void:
	for frame in range(frames): await RenderingServer.frame_post_draw
	assert(not world.is_gameplay_blocked(),"A blocked or paused world cannot be accepted as a scene review")
	assert(not is_instance_valid(world.hud_controller.pause_panel),"Review must not photograph a pause overlay")
	var image := get_viewport().get_texture().get_image()
	assert(image.get_size() == Vector2i(1920,1080),"Native framebuffer must be 1920x1080")
	var path := directory.path_join(label+".png")
	assert(image.save_png(path) == OK)
	records.append({"name":label,"framebuffer":[1920,1080],"player":world.player.global_position,"camera":world.player.camera.global_transform,"lamp":world.player.lamp_enabled,"actors":world.hunter_nodes.size(),"controlled_view":true,"human_input":false})
	print("NATIVE SCENE CAPTURE ",path)

func _process(_delta: float) -> void:
	# The controlled camera session must stay distinct from the production focus
	# handling. Godot delivers notifications to inherited scripts as well.
	if is_instance_valid(world):
		if world.paused:
			world.paused = false
			world._sync_modal_state()
		world.update_hud()

func run_review() -> void:
	set_view(Vector3(0,0,0),Vector3(-6,1.4,-12))
	world.player.lamp_enabled = false
	world.player.lamp_light.visible = false
	await _capture("01-start-dark")
	world.player.lamp_enabled = true
	world.player.lamp_light.visible = true
	await _capture("02-start-lamp")
	world.storm_controller.trigger_strike(Vector3(-12,0,-18))
	await _capture("03-start-lightning",2)
	world.storm_controller.lightning.light_energy = 0.0
	world.storm_controller.bolt.visible = false
	world.storm_controller.lightning_energy = 0.0
	for shot in [
		{"name":"04-tower-report","position":Vector3(-17,0,-21),"target":Vector3(-23,2.2,-28)},
		{"name":"05-dead-tree-report","position":Vector3(30,0,-6),"target":Vector3(35,2,-12)},
		{"name":"06-car-report","position":Vector3(28,0,40),"target":Vector3(22,1.1,34)},
		{"name":"07-report-support","position":Vector3(-20.6,0,-24.2),"target":Vector3(-20.6,.85,-27)}
	]:
		set_view(shot.position,shot.target)
		await _capture(shot.name)
	# Actual production actions and articulated hand state, observed in the world.
	set_view(Vector3(0,0,0),Vector3(-6,1.4,-12))
	for action in ["flash","shot","luminol","salt","mud"]:
		world.player.equipment.trigger(action)
		world.player._update_sensory_feedback(.25,Vector2.ZERO)
		await _capture("08-action-"+action,2)
		world.player.equipment.tick(1.0)
		world.player.release_light.light_energy = 0.0
	world.player._update_sensory_feedback(.016,Vector2.ZERO)
	set_view(Vector3(0,0,0),Vector3(0,1.4,-6))
	for index in range(5):
		var hunter = world.hunter_nodes[index]
		hunter.global_position = Vector3((index-2)*2.2,0,-7.0-abs(index-2))
		hunter.look_at(Vector3(0,0,0),Vector3.UP)
		var visual: Node3D = hunter.get_node("VisualRoot")
		if visual.has_method("set_preview_pose"):
			visual.set_preview_pose("charge" if index==2 else "chase",.19+index*.09)
	await _capture("09-five-hunters")
	var receipt := {"engine":Engine.get_version_info(),"device":RenderingServer.get_video_adapter_name(),"rendering_method":RenderingServer.get_current_rendering_method(),"actual_world":true,"controlled_views":true,"ordinary_playtest":false,"captures":records}
	FileAccess.open(directory.path_join("scene-review-receipt.json"),FileAccess.WRITE).store_string(JSON.stringify(receipt,"\t"))
	world.free()
	var cleanup_until := Time.get_ticks_msec()+100
	while Time.get_ticks_msec()<cleanup_until: await get_tree().process_frame
	print("NATIVE SCENE REVIEW CAPTURE COMPLETE")
	get_tree().quit()
