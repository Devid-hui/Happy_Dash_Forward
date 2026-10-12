extends Node

const WORLD := preload("res://scripts/world/world.gd")
const MAIN := preload("res://scripts/core/main.gd")

class GuiConsumer extends Control:
	var key_events := 0
	func _gui_input(event: InputEvent) -> void:
		if event is InputEventKey and event.pressed:
			key_events += 1
			accept_event()

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	call_deferred("run_checks")

func _freeze_hunters(world) -> void:
	world.hunter_director.set_physics_process(false)
	world.storm_controller.set_process(false)
	for hunter in world.hunter_nodes:
		hunter.set_physics_process(false)

func _key(code: Key, repeated := false) -> void:
	var event := InputEventKey.new()
	event.keycode = code
	event.physical_keycode = code
	event.pressed = true
	event.echo = repeated
	Input.parse_input_event(event)
	await get_tree().process_frame
	event = InputEventKey.new()
	event.keycode = code
	event.physical_keycode = code
	Input.parse_input_event(event)
	await get_tree().process_frame

func _assert_modal(world, expected_paused: bool, expected_notebook: bool) -> void:
	assert(world.paused == expected_paused, "manual pause reason must be preserved")
	assert(world.notebook == expected_notebook, "handbook state must match input")
	var blocked: bool = expected_paused or expected_notebook or GameState.game_over
	assert(world.is_gameplay_blocked() == blocked)
	assert(get_tree().paused == blocked, "tree pause must derive from all modal reasons")
	# The dummy headless display server does not retain mouse capture; Metal acceptance checks it.
	if DisplayServer.get_name() != "headless":
		assert(Input.mouse_mode == (Input.MOUSE_MODE_VISIBLE if blocked else Input.MOUSE_MODE_CAPTURED), "cursor mode must follow modal state")

func _find_button(node: Node, caption: String) -> Button:
	if node is Button and node.text == caption:
		return node
	for child in node.get_children():
		var result := _find_button(child, caption)
		if result != null:
			return result
	return null

func _check_modal_input(world) -> void:
	_assert_modal(world, false, false)
	var consumer := GuiConsumer.new()
	consumer.focus_mode = Control.FOCUS_ALL
	world.hud_controller.add_child(consumer)
	consumer.grab_focus()
	await _key(KEY_BACKSPACE)
	_assert_modal(world, false, false)
	await _key(KEY_TAB)
	_assert_modal(world, false, true)
	assert(is_instance_valid(world.hud_controller.handbook_panel))
	assert(consumer.key_events == 1, "Backspace reaches GUI; Tab must be consumed before GUI focus handling")
	await _key(KEY_TAB, true)
	_assert_modal(world, false, true)
	await _key(KEY_ESCAPE)
	_assert_modal(world, false, false)
	await _key(KEY_ESCAPE)
	_assert_modal(world, true, false)
	await _key(KEY_ESCAPE, true)
	_assert_modal(world, true, false)
	await _key(KEY_TAB)
	_assert_modal(world, true, true)
	await _key(KEY_ESCAPE)
	_assert_modal(world, true, false)
	await _key(KEY_TAB)
	var close := _find_button(world.hud_controller.handbook_panel, "关闭手册")
	assert(close != null)
	close.pressed.emit()
	await get_tree().process_frame
	_assert_modal(world, true, false)
	var resume := _find_button(world.hud_controller.pause_overlay, "继续")
	assert(resume != null)
	resume.pressed.emit()
	await get_tree().process_frame
	_assert_modal(world, false, false)
	consumer.queue_free()
	await _key(KEY_TAB)
	world.notification(NOTIFICATION_WM_WINDOW_FOCUS_OUT)
	await get_tree().process_frame
	_assert_modal(world, true, false)
	world.notification(NOTIFICATION_WM_WINDOW_FOCUS_OUT)
	world.notification(NOTIFICATION_WM_WINDOW_FOCUS_IN)
	await get_tree().process_frame
	_assert_modal(world, true, false)
	await _key(KEY_ESCAPE)
	_assert_modal(world, false, false)

func _check_paused_timers(world) -> void:
	GameState.equipped = ["afterimage", "echo", "mire"]
	world.player.afterimage_ready = true
	world.player.afterimage_window = 5.0
	world.player.use_slot(0)
	var timers: Array[Node] = world.hud_controller.find_children("*", "Timer", true, false)
	assert(timers.size() == 1, "successful afterimage must create one visual timer")
	var timer: Timer = timers[0]
	assert(timer.process_mode == Node.PROCESS_MODE_PAUSABLE)
	var hunter = world.hunter_nodes[0]
	hunter.set_physics_process(true)
	world.place_field("mire", Vector3(80, 0, 80), 2.4)
	world.damage_hunter_trace(Vector3(80, 0, 80))
	world.toggle_pause()
	var hunter_position: Vector3 = hunter.global_position
	var field_time: float = world.fields.back().time
	var trace_time: float = world.traces.back().time
	var visual_time := timer.time_left
	var logic_time: float = world.player.afterimage_time
	var cooldown: float = world.player.skill_manager.cooldowns["afterimage"]
	var notice_time: float = world.hud_controller.notice_timer
	var player_position: Vector3 = world.player.global_position
	await get_tree().create_timer(0.18).timeout
	assert(is_equal_approx(timer.time_left, visual_time), "afterimage visual must freeze while paused")
	assert(is_equal_approx(world.player.afterimage_time, logic_time), "afterimage logic must freeze while paused")
	assert(is_equal_approx(world.player.skill_manager.cooldowns["afterimage"], cooldown))
	assert(is_equal_approx(world.hud_controller.notice_timer, notice_time), "HUD notice must use gameplay time")
	assert(world.player.global_position == player_position)
	assert(hunter.global_position == hunter_position, "a live hunter must freeze while paused")
	assert(is_equal_approx(world.fields.back().time, field_time))
	assert(is_equal_approx(world.traces.back().time, trace_time))
	world.toggle_pause()
	await get_tree().create_timer(0.12).timeout
	assert(timer.time_left < visual_time and world.player.afterimage_time < logic_time)
	assert(world.hud_controller.notice_timer < notice_time)
	assert(hunter.global_position != hunter_position, "a live hunter must resume after pause")
	assert(world.fields.back().time < field_time and world.traces.back().time < trace_time)
	hunter.set_physics_process(false)
	timer.get_parent().queue_free()
	world.player.afterimage_time = 0.0

func _check_traces(world) -> void:
	for trace in world.traces:
		trace.node.queue_free()
	world.traces.clear()
	GameState.equipped = ["luminol", "salt"]
	GameState.skill_levels.clear()
	world.player.skill_manager.reset()
	world.damage_hunter_trace(Vector3(0, 0, -2))
	var ordinary: Dictionary = world.traces.back()
	world.player.use_slot(0)
	assert(ordinary.node.visible and world.luminol_charges == 2)
	ordinary.node.visible = false
	var upgrade: Dictionary = world.research_manager.collect(0)
	assert(upgrade.ok and GameState.skill_levels["luminol"] == 2)
	world.player.skill_manager.cooldowns["luminol"] = 0.0
	world.player.use_slot(0)
	assert(ordinary.node.visible and world.luminol_charges == 1, "Lv.2 must continue revealing ordinary traces")
	var hunter = world.hunter_nodes[0]
	hunter.global_position = Vector3(12, 0, 12)
	world.place_field("salt", hunter.global_position, 2.4)
	world._apply_fields()
	var salted: Dictionary = world.traces.back()
	assert(salted.salt_reactive and salted.source_hunter_id == hunter.get_instance_id())
	var original_count: int = world.traces.size()
	for contact in range(5):
		world._apply_fields()
	assert(world.traces.size() == original_count, "active salt trace must deduplicate repeated contact")
	world.reveal_traces(true)
	assert(is_equal_approx(salted.node.material_override.emission_energy_multiplier, 1.2), "Lv.2 strengthens salt traces")
	salted.time = 0.01
	world._process(0.02)
	assert(world.traces.size() == original_count, "washed salt trace must be replaced while contact persists")
	var replacement: Dictionary = world.traces.back()
	assert(replacement.source_hunter_id == hunter.get_instance_id() and replacement.node != salted.node)
	world._apply_fields()
	assert(world.traces.size() == original_count, "regenerated trace must also deduplicate")
	world.fields.clear()

func _check_lightning_hint(world) -> void:
	for loadout in [["echo"], ["afterimage"], ["echo", "afterimage"], ["echo", "filter", "afterimage"]]:
		GameState.equipped.assign(loadout)
		world.player.afterimage_ready = false
		world.player.afterimage_window = 0.0
		world.storm_controller.trigger_strike(Vector3(0, 0, -20))
		var slot: int = loadout.find("afterimage")
		var expected := "闪电照亮了平原。"
		if slot >= 0:
			expected += "按 %d 延长视觉后像。" % (slot+1)
		assert(world.hud_controller.status_label.text == expected, "lightning hint must use the equipped afterimage slot or omit an unavailable skill")
		assert(world.player.afterimage_ready and is_equal_approx(world.player.afterimage_window, 5.0), "lightning must preserve the existing afterimage readiness window")

func _check_legal_fusions(world) -> void:
	world.fusion_manager.discovered.clear()
	GameState.equipped = ["afterimage", "echo", "filter"]
	world.player.skill_manager.reset()
	world.player.afterimage_ready = true
	world.player.afterimage_window = 5.0
	world.player.use_slot(0)
	world.player.use_slot(2)
	world.player.use_slot(1)
	assert(world.fusion_manager.discovered.has("echo_afterimage"))
	assert(world.fusion_manager.discovered.has("echo_filter"))
	assert(not "条件：" in world.hud_controller.status_label.text, "notification must show titles rather than long descriptions")
	assert("Tab" in world.hud_controller.status_label.text or "TAB" in world.hud_controller.status_label.text)
	GameState.equipped = ["echo", "mire"]
	world.player.skill_manager.reset()
	world.player.use_slot(1)
	world.player.use_slot(0)
	assert(world.fusion_manager.discovered.has("echo_mire"))
	GameState.equipped = ["salt", "luminol"]
	world.player.skill_manager.reset()
	world.player.stamina = 100.0
	world.luminol_charges = 3
	world.hunter_nodes[0].global_position = world.player.global_position
	world.player.use_slot(0)
	world._apply_fields()
	world.player.use_slot(1)
	assert(world.fusion_manager.discovered.has("salt_luminol"))
	assert(world.fusion_manager.discovered.size() == 4, "four fusion rules must work with legal loadouts")
	assert(world.hud_controller.status_label.autowrap_mode == TextServer.AUTOWRAP_WORD_SMART)
	assert(world.hud_controller.status_label.size.x <= get_viewport().get_visible_rect().size.x - 31.0)

func _check_boundary(world) -> void:
	world.fields.clear()
	world.player.skill_manager.reset()
	world.player.in_mire = false
	world.player.in_salt = false
	for edge in [Vector3(1, 0, 0), Vector3(-1, 0, 0), Vector3(0, 0, 1), Vector3(0, 0, -1)]:
		world.player.global_position = edge * 97.0 + Vector3(0, 0.02, 0)
		world.player.rotation.y = atan2(-edge.x, -edge.z)
		world.player.velocity = Vector3.ZERO
		world.player.stamina = 100.0
		Input.action_press("move_forward")
		Input.action_press("sprint")
		for frame in range(45):
			await get_tree().physics_frame
		Input.action_release("move_forward")
		Input.action_release("sprint")
		assert(absf(world.player.global_position.x) < 99.0 and absf(world.player.global_position.z) < 99.0, "map edge must block outward walking")
		assert(world.player.global_position.y > -0.5 and not GameState.game_over, "edge contact must preserve a playable run")
	world.player.global_position = Vector3(0, -6, 0)
	await get_tree().physics_frame
	await get_tree().physics_frame
	assert(GameState.game_over and GameState.outcome != "胜利", "falling below the floor must finish as a loss")
	_assert_modal(world, false, false)
	await _key(KEY_TAB)
	await _key(KEY_ESCAPE)
	_assert_modal(world, false, false)

func _check_legal_selection() -> void:
	var main := MAIN.new()
	add_child(main)
	for loadout in [["echo"], ["salt", "luminol"], ["echo", "mire", "filter"]]:
		main._show_selection()
		for skill in loadout:
			main._toggle_skill(skill)
		if loadout.size() == 3:
			main._toggle_skill("afterimage")
			assert(main.selected.size() == 3, "selection must enforce three skill slots")
		await main._start_game()
		_freeze_hunters(main.world)
		assert(GameState.equipped.size() == loadout.size())
		assert(GameState.equipped == loadout)
		assert(not get_tree().paused and not GameState.game_over)
		main.world.request_menu()
		await get_tree().process_frame
		await get_tree().process_frame
		assert(main.screen == "menu" and not get_tree().paused)
	main.queue_free()
	await get_tree().process_frame

func run_checks() -> void:
	seed(721)
	if DisplayServer.get_name() == "headless":
		print("AUDIT NOTE: headless display cannot verify mouse capture; graphical acceptance is required")
	GameState.reset_run()
	GameState.equipped = ["afterimage", "echo", "mire"]
	var world := WORLD.new()
	world.process_mode = Node.PROCESS_MODE_PAUSABLE
	add_child(world)
	_freeze_hunters(world)
	await get_tree().physics_frame
	await _check_modal_input(world)
	await _check_paused_timers(world)
	_check_traces(world)
	_check_lightning_hint(world)
	_check_legal_fusions(world)
	await _check_boundary(world)
	get_tree().paused = false
	world.queue_free()
	await get_tree().process_frame
	await _check_legal_selection()
	# Audio playback releases are consumed by the audio thread after node deletion.
	# Wait in wall-clock time so accelerated headless frames cannot outrun that cleanup.
	var cleanup_until := Time.get_ticks_msec() + 100
	while Time.get_ticks_msec() < cleanup_until:
		await get_tree().process_frame
	print("AUDIT REGRESSIONS PASS: real Tab/Esc input, GUI consumption, modal/focus lifecycle, paused visual and logic timers, four edges/fall, upgraded traces, repeat salt contact, equipped lightning hints, legal loadouts and four fusions")
	get_tree().quit()
