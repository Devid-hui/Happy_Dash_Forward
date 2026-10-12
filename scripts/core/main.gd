extends Node

const WORLD := preload("res://scripts/world/world.gd")
var root_ui: Control
var body: VBoxContainer
var screen := "menu"
var world: Node3D
var selected: Array[String] = []
var skill_buttons: Dictionary = {}
var transitioning := false

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_build_shell()
	_show_menu()

func _build_shell() -> void:
	root_ui = Control.new()
	root_ui.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(root_ui)
	var bg := ColorRect.new()
	bg.color = Color(0.012, 0.018, 0.025, 1)
	bg.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	root_ui.add_child(bg)
	var center := CenterContainer.new()
	center.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	root_ui.add_child(center)
	body = VBoxContainer.new()
	body.custom_minimum_size = Vector2(450, 0)
	body.add_theme_constant_override("separation", 12)
	center.add_child(body)

func _clear() -> void:
	for child in body.get_children(): child.queue_free()

func _label(text: String, size := 18, color := Color(0.78, 0.84, 0.86)) -> Label:
	var label := Label.new()
	label.text = text
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	label.add_theme_font_size_override("font_size", size)
	label.add_theme_color_override("font_color", color)
	body.add_child(label)
	return label

func _button(text: String, action: Callable) -> void:
	var button := Button.new()
	button.text = text
	button.custom_minimum_size.y = 28
	button.pressed.connect(action)
	body.add_child(button)

func _show_menu() -> void:
	screen = "menu"
	_clear()
	_label("THE MIDNIGHT ACADEMY", 27, Color(0.82, 0.87, 0.84))
	_label("THE RAINFIELD  /  雨夜平原", 15, Color(0.35, 0.58, 0.49))
	_label("雨幕之后，有什么在寻找你。", 15)
	_button("开始试炼 / START GAME", _show_selection)
	_button("选择学科 / SELECT DISCIPLINES", _show_selection)
	_button("设置：减少闪光  [%s]" % ("开" if GameState.reduced_flashes else "关"), _toggle_flashes)
	_button("画面亮度：%.1f" % GameState.brightness, _cycle_brightness)
	_button("退出 / QUIT", func(): get_tree().quit())

func _toggle_flashes() -> void:
	GameState.reduced_flashes = not GameState.reduced_flashes
	_show_menu()

func _cycle_brightness() -> void:
	GameState.brightness = 0.8 if GameState.brightness >= 1.2 else GameState.brightness + 0.2
	_show_menu()

func _show_selection() -> void:
	screen = "selection"
	_clear()
	body.add_theme_constant_override("separation", 4)
	selected.clear()
	skill_buttons.clear()
	_label("选择三门学科", 25)
	_label("选择 1–3 项；悬停卡片查看科学依据与代价。", 13)
	var grid := GridContainer.new()
	grid.columns = 2
	grid.add_theme_constant_override("h_separation", 6)
	grid.add_theme_constant_override("v_separation", 4)
	body.add_child(grid)
	for skill in GameState.SKILLS:
		var button := Button.new()
		button.set_meta("skill_id", skill.id)
		button.text = _short_skill_name(skill.id)
		button.tooltip_text = "%s\n%s\n%s" % [skill.science, skill.effect, skill.cost]
		button.custom_minimum_size = Vector2(220, 30)
		button.pressed.connect(_on_skill_pressed.bind(skill.id))
		grid.add_child(button)
		skill_buttons[skill.id] = button
	_label("未选择时将自动装备雷痕、还声与泥浆。", 12, Color(0.42, 0.58, 0.55))
	_button("进入平原", _start_game)
	_button("返回", _show_menu)

func _short_skill_name(skill_id: String) -> String:
	var short_names := {"afterimage":"雷痕 · 视觉神经科学", "echo":"还声 · 声学", "luminol":"蓝色供词 · 分析化学", "mire":"不许停步之泥 · 流变学", "salt":"盐之誓约 · 细胞生理学", "filter":"剥噪 · 信号处理"}
	return short_names.get(skill_id, skill_id)

func _on_skill_pressed(skill_id: String) -> void:
	_toggle_skill(skill_id)
	_refresh_skill_buttons()

func _toggle_skill(skill_id: String) -> void:
	if selected.has(skill_id): selected.erase(skill_id)
	elif selected.size() < 3: selected.append(skill_id)

func _refresh_skill_buttons() -> void:
	for skill_id in skill_buttons:
		var button: Button = skill_buttons[skill_id]
		button.text = ("✓ " if selected.has(skill_id) else "") + _short_skill_name(skill_id)

func _start_game() -> void:
	if transitioning: return
	transitioning = true
	if selected.is_empty(): selected = ["afterimage", "echo", "mire"]
	GameState.equipped = selected.duplicate()
	GameState.reset_run()
	_clear()
	_label("正在准备雨夜森林……", 22)
	await get_tree().process_frame
	await get_tree().process_frame
	_spawn_world()
	root_ui.queue_free()
	transitioning = false

func _spawn_world() -> void:
	world = WORLD.new()
	world.process_mode = Node.PROCESS_MODE_PAUSABLE
	add_child(world)
	world.return_to_menu.connect(_show_menu_from_world)
	world.retry_requested.connect(_restart_world)

func _restart_world() -> void:
	if transitioning: return
	transitioning = true
	get_tree().paused = false
	# 按钮属于旧世界。信号回调中不能立即 free 它，否则正在执行的 UI 被销毁。
	if is_instance_valid(world):
		world.process_mode = Node.PROCESS_MODE_DISABLED
		world.queue_free()
	world = null
	await get_tree().process_frame
	GameState.reset_run()
	_spawn_world()
	transitioning = false

func _show_menu_from_world() -> void:
	if transitioning: return
	get_tree().paused = false
	if is_instance_valid(world): world.queue_free()
	_build_shell()
	_show_menu()
