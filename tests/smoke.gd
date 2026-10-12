extends Node

const WorldScript = preload("res://scripts/world/world.gd")
const MainScript = preload("res://scripts/core/main.gd")

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	call_deferred("run_smoke")

func run_smoke() -> void:
	var main = MainScript.new()
	add_child(main)
	main._show_selection()
	main._toggle_skill("echo")
	main._toggle_skill("filter")
	await main._start_game()
	assert(main.world != null, "discipline selection should enter gameplay")
	assert(GameState.equipped.size() == 2, "selection should persist")
	var world = main.world
	await get_tree().process_frame
	assert(world.player != null, "player should spawn")
	assert(world.hunter_nodes.size() == 5, "five hunters should spawn at start")
	assert(world.objective_nodes.size() == 3, "three records should spawn")
	for book in world.objective_nodes:
		assert(book.has_node("Pages") and book.has_node("FrontCover") and book.has_node("Spine"))
		assert(book.has_node("InteractionLabel") and book.has_meta("landmark_name"))
	assert(world.get_node("Landmark_car").find_children("Wheel*","MeshInstance3D",false,false).size() == 4)
	assert(world.get_node("Landmark_tower").find_children("SaggingCable*","MeshInstance3D",false,false).size() == 8)
	assert(world.get_node("Landmark_tree").has_node("BleachedTrunk"))
	assert(not world.research_hint().is_empty())
	world.toggle_handbook()
	assert(is_instance_valid(world.hud_controller.handbook_panel), "research handbook should open")
	world.toggle_handbook()
	world.toggle_pause()
	assert(get_tree().paused, "pause should freeze gameplay")
	world.toggle_pause()
	assert(not get_tree().paused, "resume should unpause gameplay")
	GameState.equipped = ["afterimage", "echo", "luminol", "mire", "salt", "filter"]
	world.player.afterimage_ready = true
	world.player.afterimage_window = 5.0
	for slot in range(6): world.player.use_slot(slot)
	assert(world.luminol_charges == 2, "luminol should consume reagent")
	assert(world.fields.size() == 2, "mire and salt should create fields")
	world.player.filter_time = 5.0
	world.player.skill_manager.cooldowns["echo"] = 0.0
	world.player.use_slot(1)
	world.player.skill_manager.cooldowns["echo"] = 0.0
	world.player.use_slot(1)
	world.hunter_nodes[0].global_position = world.player.global_position
	world._apply_fields()
	world.player.skill_manager.cooldowns["luminol"] = 0.0
	world.player.use_slot(2)
	assert(world.fusion_manager.discovered.size() == 4, "all four fusion conditions should be discoverable")
	world.player.afterimage_ready = false
	world.player.skill_manager.cast_slot(0)
	assert(world.player.skill_manager.cooldowns.has("afterimage"), "afterimage cooldown should start after success")
	for objective in world.objective_nodes.duplicate():
		world.player.global_position = objective.global_position
		world.interact()
	assert(world.collected == 3, "all research records should be collectible")
	assert(world.hunter_nodes.size() == 5, "third record should preserve five hunters")
	world.player.global_position = world.exit_node.global_position
	world.interact()
	assert(GameState.game_over, "exit should finish the run")
	assert(GameState.outcome == "胜利", "exit should produce a win")
	await main._restart_world()
	assert(main.world.collected == 0 and main.world.hunter_nodes.size() == 5, "retry should reset records and hunter count")
	# 使用真实死亡界面的按钮信号，而不是只直接调用重开函数。
	for attempt in range(3):
		var old_id: int = main.world.get_instance_id()
		main.world.player.take_hit(); main.world.player.take_hit()
		assert(GameState.game_over and get_tree().paused)
		var retry: Button = find_retry(main.world.hud_controller)
		assert(retry != null)
		retry.pressed.emit()
		await get_tree().process_frame
		await get_tree().process_frame
		assert(is_instance_valid(main.world) and main.world.get_instance_id() != old_id)
		assert(not get_tree().paused and not GameState.game_over)
		assert(main.world.hunter_nodes.size() == 5 and main.world.player.hits == 0)

	get_tree().paused=false
	assert(preload("res://scripts/enemies/hunter_visual.gd").build_count == 1,"restarts must reuse cached model")
	main.world.free()
	await get_tree().create_timer(1.0).timeout
	print("SMOKE PASS: menu selection, six skills, research, five hunters, and victory")
	await get_tree().create_timer(1.0).timeout
	get_tree().quit()

func find_retry(node: Node) -> Button:
	if node is Button and node.text == "重新开始": return node
	for child in node.get_children():
		var result := find_retry(child)
		if result != null: return result
	return null
