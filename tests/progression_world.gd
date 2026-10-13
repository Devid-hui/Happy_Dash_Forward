extends Node

const WORLD := preload("res://scripts/world/world.gd")
var checks := 0
var world

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	call_deferred("run_contract")

func expect(condition: bool, description: String) -> void:
	if not condition:
		push_error(description)
		get_tree().quit(1)
		assert(false, description)
	checks += 1

func choose_button(node: Node) -> Button:
	if node is Button: return node
	for child in node.get_children():
		var result := choose_button(child)
		if result != null: return result
	return null

func run_contract() -> void:
	var original_path: String = GameState.archive_path
	var test_path := "user://progression-world-contract.json"
	if FileAccess.file_exists(test_path): DirAccess.remove_absolute(test_path)
	GameState.set_archive_path(test_path)
	GameState.equipped = ["echo", "daylight", "pulse"]
	GameState.reset_run()
	world = WORLD.new()
	add_child(world)
	for hunter in world.hunter_nodes: hunter.process_mode = Node.PROCESS_MODE_DISABLED
	await get_tree().process_frame
	expect(world.objective_nodes.size() == 3, "three physical reports must exist")
	var report = world.objective_nodes[0]
	world.player.global_position = report.global_position
	world.interact()
	expect(world.collected == 1 and GameState.upgrades == 0, "collecting must not automatically apply a level")
	expect(get_tree().paused and world.is_gameplay_blocked(), "report choice must block gameplay")
	expect(Input.mouse_mode == Input.MOUSE_MODE_VISIBLE, "report choice must release the mouse")
	expect(is_instance_valid(world.hud_controller.upgrade_panel), "real upgrade UI must be present")
	var level_before := GameState.ability_level("lamp")
	var collected_before: int = world.collected
	world.interact()
	expect(world.collected == collected_before, "interaction while choosing must not collect a second report")
	world.confirm_upgrade("salt")
	expect(GameState.ability_level("lamp") == level_before and world.research_manager.has_pending_upgrade(), "un-equipped choice must be rejected without consuming the report")
	world.toggle_handbook()
	expect(world.notebook and get_tree().paused and is_instance_valid(world.hud_controller.handbook_panel), "handbook remains available during pending choice")
	world.toggle_handbook()
	expect(not world.notebook and world.research_manager.has_pending_upgrade() and is_instance_valid(world.hud_controller.upgrade_panel), "closing handbook restores pending choice")
	world._notification(NOTIFICATION_WM_WINDOW_FOCUS_OUT)
	expect(world.paused and world.research_manager.has_pending_upgrade(), "focus loss must keep the pending report")
	world.toggle_pause()
	expect(not world.paused and get_tree().paused and is_instance_valid(world.hud_controller.upgrade_panel), "continue returns to choice before gameplay")
	world.confirm_upgrade("lamp")
	expect(GameState.ability_level("lamp") == 2 and GameState.upgrades == 1, "first report applies one chosen level")
	expect(not world.is_gameplay_blocked() and not get_tree().paused, "successful choice resumes gameplay")
	world.confirm_upgrade("lamp")
	expect(GameState.ability_level("lamp") == 2 and GameState.upgrades == 1, "repeated confirmation must not grant a second upgrade")
	for index in range(2):
		var next_report = world.objective_nodes[0]
		world.player.global_position = next_report.global_position
		world.interact()
		expect(get_tree().paused, "every report independently pauses for choice")
		world.confirm_upgrade("lamp" if index == 0 else "echo")
	expect(world.collected == 3 and GameState.upgrades == 3, "three reports provide three chosen upgrades")
	expect(GameState.ability_level("lamp") == 3 and GameState.ability_level("echo") == 2, "specialization and distributed growth can coexist")
	expect(world.hunter_nodes.size() == 5, "report growth preserves five hunters")
	world.player.global_position = world.exit_node.global_position
	world.interact()
	expect(GameState.game_over and GameState.outcome == "胜利", "collecting three reports opens the actual exit")
	get_tree().paused = false
	world.free()
	await get_tree().process_frame
	GameState.reset_run()
	world = WORLD.new()
	add_child(world)
	for hunter in world.hunter_nodes: hunter.process_mode = Node.PROCESS_MODE_DISABLED
	await get_tree().process_frame
	expect(GameState.ability_level("lamp") == 1 and GameState.upgrades == 0 and world.collected == 0, "new run resets numeric advantages")
	expect(GameState.archive_lines().any(func(line): return line.contains("输电塔研究报告")), "archive knowledge survives the new run")
	# Model two queued opportunities to verify a stale UI callback cannot apply
	# a second report after World replaces the first choice panel in the same frame.
	world.research_manager.collect(0)
	world.research_manager.collect(1)
	world._sync_modal_state()
	var stale_button := choose_button(world.hud_controller.upgrade_panel)
	expect(stale_button != null, "queued report creates an actionable panel")
	stale_button.pressed.emit()
	var applied_before := GameState.upgrades
	stale_button.pressed.emit()
	expect(GameState.upgrades == applied_before and world.research_manager.has_pending_upgrade(), "stale callback must not consume the next report")
	get_tree().paused = false
	world.free()
	await get_tree().process_frame
	await get_tree().create_timer(0.2).timeout
	DirAccess.remove_absolute(test_path)
	GameState.set_archive_path(original_path)
	GameState.reset_run()
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	print("PROGRESSION WORLD PASS: %d checks across real collection, pause/focus/handbook, choice idempotency, exit and new-run archive" % checks)
	get_tree().quit()
