extends Node

const MAIN := preload("res://scripts/core/main.gd")
const HUD := preload("res://scripts/ui/hud_controller.gd")

class FakeSkills extends Node:
	var cooldowns := {"echo": 3.2}

class FakePlayer extends Node3D:
	var stamina := 71.0
	var energy := 63.0
	var noise := 82.0
	var lamp_enabled := true
	var pulse_mode := true
	var skill_manager := FakeSkills.new()
	func energy_capacity() -> float: return 120.0

class FakeWorld extends Node3D:
	var player := FakePlayer.new()
	var collected := 2
	var luminol_charges := 2
	var notebook := false
	var paused := false
	var confirmations: Array[String] = []
	var on_confirmation := Callable()
	var retries := 0
	var menus := 0
	func research_hint() -> String: return "前往输电塔，寻找下一份报告。"
	func hunter_state_label() -> String: return "追逐"
	func is_gameplay_blocked() -> bool: return paused or notebook
	func toggle_pause() -> void: paused = not paused
	func toggle_handbook() -> void: notebook = not notebook
	func request_retry() -> void: retries += 1
	func request_menu() -> void: menus += 1
	func confirm_upgrade(id: String) -> void:
		confirmations.append(id)
		if on_confirmation.is_valid(): on_confirmation.call()

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	call_deferred("run_checks")

func _settle() -> void:
	await get_tree().process_frame
	await get_tree().process_frame
	await get_tree().process_frame

func _assert_inside(node: Control, boundary: Rect2, description: String) -> void:
	var rect := node.get_global_rect()
	assert(rect.size.x > 0.0 and rect.size.y > 0.0, "%s must have a laid-out rectangle" % description)
	assert(boundary.encloses(rect), "%s outside 1080p viewport: %s" % [description, rect])

func _capture(name: String) -> void:
	var directory := OS.get_environment("HDF_UI_CAPTURE_DIR")
	if directory.is_empty() or DisplayServer.get_name() == "headless": return
	var selected_capture := OS.get_environment("HDF_UI_CAPTURE_ONLY")
	if not selected_capture.is_empty() and selected_capture != name: return
	DirAccess.make_dir_recursive_absolute(directory)
	await RenderingServer.frame_post_draw
	var result := get_viewport().get_texture().get_image().save_png(directory.path_join(name + ".png"))
	assert(result == OK, "UI preview must save successfully")

func _find_button(node: Node, caption: String) -> Button:
	if node is Button and node.text == caption: return node
	for child in node.get_children():
		var candidate := _find_button(child, caption)
		if candidate != null: return candidate
	return null

func _assert_upgrade_buttons_visible(hud, options: Array[Dictionary]) -> void:
	var scroll := hud.upgrade_panel.find_child("UpgradeScroll", true, false) as ScrollContainer
	assert(scroll != null and scroll.scroll_vertical == 0, "upgrade choices must be comparable from the initial scroll position")
	var visible_rect := scroll.get_global_rect()
	for option in options:
		var card: Node = hud.upgrade_panel.find_child("Upgrade_" + str(option.id), true, false)
		assert(card != null)
		var button := _find_button(card, "强化这项能力")
		assert(button != null)
		_assert_inside(button, visible_rect, "initial upgrade button " + str(option.id))

func run_checks() -> void:
	get_window().size = Vector2i(1920, 1080)
	get_window().content_scale_size = Vector2i(1920, 1080)
	var bounds := Rect2(Vector2.ZERO, Vector2(1920, 1080))
	GameState.reset_run()
	var main := MAIN.new()
	add_child(main)
	await _settle()
	_assert_inside(main.body, bounds, "main menu")
	var start := _find_button(main, "开始试炼")
	assert(start != null and start.size.y >= 56 and start.get_theme_font_size("font_size") >= 22, "menu must have readable 1080p controls")
	var font := start.get_theme_font("font")
	for character in "雨夜平原谱灯科研强化蓄昼乱频档案":
		assert(font.has_char(character.unicode_at(0)), "CJK font fallback must contain " + character)
	await _capture("01-menu")
	start.pressed.emit()
	await _settle()
	assert(main.screen == "selection")
	assert(GameState.SKILLS.size() == 8, "all eight optional abilities must appear in the new loadout")
	assert(main.skill_buttons.size() == GameState.SKILLS.size(), "selection must represent every available skill")
	assert(not main.skill_buttons.has("lamp"), "base lamp never consumes one of three skill slots")
	for id in main.skill_buttons:
		var card: Button = main.skill_buttons[id]
		assert(card.size.y >= 119)
		_assert_inside(card, bounds, "selection card " + id)
	await _capture("02-selection")
	for id in ["afterimage", "echo", "mire"]:
		main._on_skill_pressed(id)
	main._toggle_skill("salt")
	assert(main.selected.size() == 3)
	assert(main.skill_buttons["salt"].disabled, "fourth choice cannot be added")
	main._on_skill_pressed("echo")
	assert(not main.skill_buttons["salt"].disabled, "deselecting frees a slot")
	main._show_settings()
	await _settle()
	_assert_inside(main.body, bounds, "settings")
	await _capture("03-settings")
	main._show_archive()
	await _settle()
	_assert_inside(main.body, bounds, "archive")
	await _capture("04-archive")
	main.queue_free()
	await _settle()
	var world := FakeWorld.new()
	add_child(world)
	var hud := HUD.new()
	world.add_child(hud)
	hud.setup(world)
	GameState.equipped = ["echo", "salt", "luminol"]
	hud.update_display()
	await _settle()
	print("UI RECTS root=",hud.hud_root.get_global_rect()," lamp=",hud.lamp_label.get_global_rect()," energy=",hud.energy_bar.get_global_rect()," notice=",hud.status_label.get_global_rect())
	assert(hud.energy_bar.value == 63.0 and hud.energy_bar.max_value == 120.0)
	assert(hud.stamina_bar.value == 71.0 and hud.noise_bar.value == 82.0)
	assert("点射" in hud.lamp_label.text and "照明开" in hud.lamp_label.text)
	assert("3.2s" in hud.slot_labels[0].text, "cooldown must reflect actual resource state")
	for control in [hud.objective_label, hud.research_label, hud.energy_bar, hud.status_label, hud.lamp_label]:
		_assert_inside(control, bounds, "gameplay HUD")
	assert(hud.hud_root.mouse_filter == Control.MOUSE_FILTER_IGNORE)
	assert(not get_tree().paused, "HUD may not independently pause the tree")
	await _capture("05-hud-layout")
	hud.show_pause()
	await _settle()
	_assert_inside(hud.pause_overlay, bounds, "pause dialog")
	await _capture("06-pause")
	_find_button(hud.pause_overlay, "继续").pressed.emit()
	assert(world.paused and not get_tree().paused, "pause button delegates state to World")
	hud.hide_pause()
	world.paused = false
	hud.show_handbook(["雷痕：强光停止后，视觉系统短暂保留旧影像。"], ["还声 + 雷痕：本局已发现。"])
	await _settle()
	_assert_inside(hud.handbook_panel, bounds, "handbook")
	await _capture("07-handbook")
	_find_button(hud.handbook_panel, "历史研究档案").pressed.emit()
	_find_button(hud.handbook_panel, "关闭手册").pressed.emit()
	assert(world.notebook)
	hud.hide_handbook()
	world.notebook = false
	GameState.equipped = ["echo", "salt", "luminol"]
	var options: Array[Dictionary] = GameState.upgrade_options()
	assert(options.size() == 4 and options[0].id == "lamp", "upgrade preview must use the base lamp and three actually equipped abilities")
	hud.show_upgrade(options)
	await _settle()
	_assert_inside(hud.upgrade_panel, bounds, "upgrade dialog")
	_assert_upgrade_buttons_visible(hud, options)
	await _capture("08-upgrade")
	var choice := _find_button(hud.upgrade_panel, "强化这项能力")
	assert(choice != null)
	choice.pressed.emit()
	choice.pressed.emit()
	assert(world.confirmations == ["lamp"], "double activation may only submit one upgrade")
	assert(choice.disabled)
	hud.hide_upgrade()
	hud.show_upgrade([])
	await _settle()
	_find_button(hud.upgrade_panel, "继续探索").pressed.emit()
	assert(world.confirmations == ["lamp", ""], "empty options retain a continuation action")
	hud.hide_upgrade()
	# An accepted choice can immediately create the next pending report's panel.
	# Signals already queued on the old button may not consume that new report.
	world.on_confirmation = func():
		hud.hide_upgrade()
		hud.show_upgrade(options)
	hud.show_upgrade(options)
	await _settle()
	var retiring_choice := _find_button(hud.upgrade_panel, "强化这项能力")
	retiring_choice.pressed.emit()
	assert(world.confirmations == ["lamp", "", "lamp"])
	retiring_choice.pressed.emit()
	assert(world.confirmations == ["lamp", "", "lamp"], "retiring panel's signal may not spend the next pending report")
	var next_choice := _find_button(hud.upgrade_panel, "强化这项能力")
	assert(next_choice != retiring_choice and not next_choice.disabled)
	next_choice.pressed.emit()
	assert(world.confirmations == ["lamp", "", "lamp", "lamp"], "next panel must remain independently actionable")
	world.on_confirmation = Callable()
	hud.hide_upgrade()
	# Use real product copy at both tiers, including the longest new ability
	# costs, rather than short placeholders that hide clipped second-row actions.
	for loadout in [["echo", "salt", "luminol"], ["afterimage", "mire", "filter"], ["daylight", "pulse", "salt"]]:
		for base_level in [1, 2]:
			GameState.equipped.assign(loadout)
			GameState.skill_levels.clear()
			for id in ["lamp"] + loadout: GameState.skill_levels[id] = base_level
			var actual_options: Array[Dictionary] = GameState.upgrade_options()
			hud.show_upgrade(actual_options)
			await _settle()
			_assert_inside(hud.upgrade_panel, bounds, "real-copy upgrade dialog")
			_assert_upgrade_buttons_visible(hud, actual_options)
			hud.hide_upgrade()
	GameState.skill_levels.clear()
	hud.show_outcome(true)
	await _settle()
	_assert_inside(hud.outcome_panel, bounds, "outcome dialog")
	await _capture("09-outcome")
	_find_button(hud.outcome_panel, "重新开始").pressed.emit()
	assert(world.retries == 1)
	world.player.skill_manager.free()
	world.player.free()
	world.queue_free()
	await _settle()
	print("UI CONTRACT PASS: 1080p menu/selection/settings/archive/HUD/modals, three-slot limits, live meters/cooldowns, delegated pause, cross-panel submit guard, empty-upgrade continuation and all four initial upgrade buttons with real copy at both tiers")
	get_tree().quit()
