extends Node

const WORLD := preload("res://scripts/world/world.gd")
const FIELD := preload("res://scripts/ui/field_theme.gd")
const ASSET_READINESS := preload("res://scripts/core/asset_readiness.gd")
var asset_manifest_path := ASSET_READINESS.MANIFEST_PATH
var root_ui: Control
var body: VBoxContainer
var screen := "menu"
var world: Node3D
var selected: Array[String] = []
var skill_buttons: Dictionary = {}
var transitioning := false
var selection_summary: Label
var skill_detail: VBoxContainer
var detail_id := ""

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_build_shell()
	_show_menu()

func _build_shell() -> void:
	root_ui = Control.new()
	root_ui.name = "FieldMenu"
	root_ui.theme = FIELD.get_theme()
	root_ui.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(root_ui)
	FIELD.backdrop(root_ui)
	var inset := FIELD.margin(80, 64)
	inset.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	root_ui.add_child(inset)
	body = VBoxContainer.new()
	body.name = "ScreenContent"
	body.add_theme_constant_override("separation", 24)
	inset.add_child(body)

func _clear() -> void:
	for child in body.get_children():
		body.remove_child(child)
		child.queue_free()
	selection_summary = null
	skill_detail = null

func _label(text: String, size := 22, color := FIELD.PAPER) -> Label:
	var label := FIELD.label(text, size, color)
	body.add_child(label)
	return label

func _button(text: String, action: Callable) -> void:
	body.add_child(FIELD.button(text, action))

func _show_menu() -> void:
	screen = "menu"
	_clear()
	var top := HBoxContainer.new()
	body.add_child(top)
	top.add_child(FIELD.eyebrow("THE MIDNIGHT ACADEMY"))
	var edition := FIELD.label("野外研究试炼  /  FIELD STUDY", 16, FIELD.MUTED)
	edition.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	top.add_child(edition)
	var space := Control.new()
	space.size_flags_vertical = Control.SIZE_EXPAND_FILL
	body.add_child(space)
	var layout := HBoxContainer.new()
	layout.add_theme_constant_override("separation", 100)
	body.add_child(layout)
	var intro := VBoxContainer.new()
	intro.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	intro.size_flags_stretch_ratio = 1.4
	layout.add_child(intro)
	intro.add_child(FIELD.eyebrow("THE RAINFIELD"))
	intro.add_child(FIELD.label("雨夜平原", 76))
	intro.add_child(FIELD.label("雨幕之后，有什么在寻找你。", 28, FIELD.MUTED))
	var breathing := Control.new()
	breathing.custom_minimum_size.y = 30
	intro.add_child(breathing)
	intro.add_child(FIELD.label("带上谱灯与三项学科能力，在森林地标之间寻找科研报告。每一次发现，都为逃生带来新的选择。", 24))
	intro.add_child(FIELD.label("三份报告 · 三次自主强化 · 一条归途", 20, FIELD.GREEN))
	var menu := VBoxContainer.new()
	menu.custom_minimum_size.x = 430
	layout.add_child(menu)
	menu.add_child(FIELD.button("开始试炼", _show_selection, true))
	menu.add_child(FIELD.button("研究档案", _show_archive))
	menu.add_child(FIELD.button("设置与操作", _show_settings))
	menu.add_child(FIELD.button("退出", func(): get_tree().quit()))
	menu.add_child(FIELD.label("选科后进入森林。\n谱灯为基础装备，不占技能槽。", 18, FIELD.MUTED))
	var lower_space := Control.new()
	lower_space.size_flags_vertical = Control.SIZE_EXPAND_FILL
	body.add_child(lower_space)
	body.add_child(FIELD.divider())
	_label("WASD 移动   ·   Shift 奔跑   ·   E 交互   ·   Tab 研究手册   ·   Esc 暂停", 18, FIELD.MUTED)
	_focus_first(menu)

func _show_settings() -> void:
	screen = "settings"
	_clear()
	_label("设置与操作", 48)
	_label("让雨夜保留压迫感，也让近处路线和障碍可以辨认。", 22, FIELD.MUTED)
	var panel := PanelContainer.new()
	body.add_child(panel)
	var content := VBoxContainer.new()
	panel.add_child(content)
	content.add_child(FIELD.button("减少闪光  [%s]" % ("开" if GameState.reduced_flashes else "关"), _toggle_flashes))
	content.add_child(FIELD.label("降低闪电与技能画面的干扰强度；耗电、噪声与战术代价保留。", 20, FIELD.MUTED))
	content.add_child(FIELD.button("画面亮度  %.1f" % GameState.brightness, _cycle_brightness))
	content.add_child(FIELD.label("0.8 / 1.0 / 1.2。用于适应显示环境，照明仍提供局部细节。", 20, FIELD.MUTED))
	var controls := GridContainer.new()
	controls.columns = 2
	controls.add_theme_constant_override("h_separation", 64)
	content.add_child(controls)
	for pair in [["WASD / 鼠标", "移动与观察"], ["Shift", "奔跑"], ["E", "拾取报告 / 进入出口"], ["1 / 2 / 3", "使用对应装备技能"], ["鼠标左键 / L或右键", "谱灯释放 / 照明开关"], ["F", "选择剥噪频段"], ["Tab / Esc", "研究手册 / 暂停"]]:
		controls.add_child(FIELD.label(pair[0], 22, FIELD.GREEN))
		controls.add_child(FIELD.label(pair[1], 22))
	_button("返回", _show_menu)
	_focus_first(body)

func _toggle_flashes() -> void:
	GameState.reduced_flashes = not GameState.reduced_flashes
	_show_settings()

func _cycle_brightness() -> void:
	GameState.brightness = 0.8 if GameState.brightness >= 1.2 else snappedf(GameState.brightness + 0.2, 0.1)
	_show_settings()

func _show_selection() -> void:
	screen = "selection"
	_clear()
	selected.clear()
	skill_buttons.clear()
	var header := HBoxContainer.new()
	body.add_child(header)
	var titles := VBoxContainer.new()
	titles.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	header.add_child(titles)
	titles.add_child(FIELD.eyebrow("LOADOUT  /  出发准备"))
	titles.add_child(FIELD.label("选择你的学科能力", 44))
	titles.add_child(FIELD.label("最多装备三项。科研谱灯随身携带，不占槽位。", 21, FIELD.MUTED))
	var lamp := PanelContainer.new()
	lamp.custom_minimum_size.x = 320
	header.add_child(lamp)
	var lamp_text := VBoxContainer.new()
	lamp.add_child(lamp_text)
	lamp_text.add_child(FIELD.eyebrow("基础装备  /  Lv.1"))
	lamp_text.add_child(FIELD.label("谱灯 · 便携光学仪器", 24))
	lamp_text.add_child(FIELD.label("照明与集中爆发，共享电量。", 18, FIELD.MUTED))
	var layout := HBoxContainer.new()
	layout.size_flags_vertical = Control.SIZE_EXPAND_FILL
	layout.add_theme_constant_override("separation", 32)
	body.add_child(layout)
	var scroll := ScrollContainer.new()
	scroll.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	layout.add_child(scroll)
	var grid := GridContainer.new()
	grid.columns = 2
	grid.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(grid)
	for skill in GameState.SKILLS:
		var button := Button.new()
		button.name = "Select_" + skill.id
		button.set_meta("skill_id", skill.id)
		button.custom_minimum_size = Vector2(350, 119)
		button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		button.alignment = HORIZONTAL_ALIGNMENT_LEFT
		button.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
		button.text = _card_caption(skill.id, false)
		button.tooltip_text = "%s\n%s\n%s" % [skill.science, skill.effect, skill.cost]
		button.pressed.connect(_on_skill_pressed.bind(skill.id))
		button.mouse_entered.connect(_show_skill_detail.bind(skill.id))
		button.focus_entered.connect(_show_skill_detail.bind(skill.id))
		grid.add_child(button)
		skill_buttons[skill.id] = button
	var detail_panel := PanelContainer.new()
	detail_panel.custom_minimum_size.x = 500
	layout.add_child(detail_panel)
	var detail_scroll := ScrollContainer.new()
	detail_scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	detail_panel.add_child(detail_scroll)
	skill_detail = VBoxContainer.new()
	skill_detail.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	detail_scroll.add_child(skill_detail)
	_show_skill_detail(GameState.SKILLS[0].id)
	var footer := HBoxContainer.new()
	body.add_child(footer)
	selection_summary = FIELD.label("已选择 0 / 3  ·  未选择时使用雷痕、还声、泥浆。", 20, FIELD.MUTED)
	footer.add_child(selection_summary)
	footer.add_child(FIELD.button("返回", _show_menu))
	footer.add_child(FIELD.button("进入平原", _start_game, true))
	_focus_first(grid)

func _short_skill_name(skill_id: String) -> String:
	var item: Dictionary = GameState.skill_data(skill_id)
	return "%s · %s" % [item.name.split(" /")[0], item.field]

func _card_caption(skill_id: String, checked: bool) -> String:
	var item: Dictionary = GameState.skill_data(skill_id)
	return "%s %s\n     %s" % ["✓" if checked else "＋", item.name.split(" /")[0], item.field]

func _show_skill_detail(skill_id: String) -> void:
	if not is_instance_valid(skill_detail): return
	detail_id = skill_id
	for child in skill_detail.get_children():
		skill_detail.remove_child(child)
		child.queue_free()
	var item: Dictionary = GameState.skill_data(skill_id)
	skill_detail.add_child(FIELD.eyebrow("FIELD NOTE  /  学科原理"))
	skill_detail.add_child(FIELD.label(item.name.split(" /")[0], 32))
	skill_detail.add_child(FIELD.label(item.field, 20, FIELD.GREEN))
	skill_detail.add_child(FIELD.divider())
	skill_detail.add_child(FIELD.label(item.science, 22))
	skill_detail.add_child(FIELD.eyebrow("在雨夜中使用"))
	skill_detail.add_child(FIELD.label(item.effect, 21))
	skill_detail.add_child(FIELD.eyebrow("代价与限制"))
	skill_detail.add_child(FIELD.label(item.cost, 21, FIELD.AMBER))
	skill_detail.add_child(FIELD.label("科学原理用于理解能力；游戏效果经过放大。每份科研报告可将一项本局能力提升一级。", 18, FIELD.MUTED))

func _on_skill_pressed(skill_id: String) -> void:
	_toggle_skill(skill_id)
	_refresh_skill_buttons()
	_show_skill_detail(skill_id)

func _toggle_skill(skill_id: String) -> void:
	if selected.has(skill_id): selected.erase(skill_id)
	elif selected.size() < 3: selected.append(skill_id)

func _refresh_skill_buttons() -> void:
	for skill_id in skill_buttons:
		var button: Button = skill_buttons[skill_id]
		var chosen := selected.has(skill_id)
		button.text = _card_caption(skill_id, chosen)
		if chosen:
			button.add_theme_stylebox_override("normal", FIELD.surface(Color("30463c"), 2, 8, 20, 12, FIELD.GREEN))
		else:
			button.remove_theme_stylebox_override("normal")
		button.disabled = selected.size() >= 3 and not chosen
	if is_instance_valid(selection_summary):
		var names: Array[String] = []
		for id in selected: names.append(GameState.skill_data(id).name.split(" /")[0])
		selection_summary.text = "已选择 %d / 3  ·  %s" % [selected.size(), " / ".join(names) if not names.is_empty() else "未选择时使用雷痕、还声、泥浆。"]

func _show_archive() -> void:
	screen = "archive"
	_clear()
	_label("研究档案", 48)
	_label("知识、报告与融合发现会保存在本机。每局的能力等级重新从基础开始。", 22, FIELD.MUTED)
	var panel := PanelContainer.new()
	panel.size_flags_vertical = Control.SIZE_EXPAND_FILL
	body.add_child(panel)
	var scroll := ScrollContainer.new()
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	panel.add_child(scroll)
	var entries := VBoxContainer.new()
	entries.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	entries.add_theme_constant_override("separation", 20)
	scroll.add_child(entries)
	var lines: Array[String] = GameState.archive_lines()
	if lines.is_empty(): lines = ["尚未建立研究记录。进入雨夜，收集报告并尝试学科融合。"]
	for line in lines:
		entries.add_child(FIELD.label(str(line), 22))
	_button("返回", _show_menu)
	_focus_first(body)

func _focus_first(node: Node) -> void:
	for child in node.get_children():
		if child is Button:
			_focus_when_live.call_deferred(child)
			return
		if child.get_child_count() > 0:
			_focus_first(child)
			if _has_button(child): return

func _focus_when_live(control: Control) -> void:
	# A screen can be replaced before its deferred focus request executes.
	if is_instance_valid(control) and control.is_inside_tree() and control.is_visible_in_tree():
		control.grab_focus()

func _has_button(node: Node) -> bool:
	if node is Button: return true
	for child in node.get_children():
		if _has_button(child): return true
	return false

func _start_game() -> void:
	if transitioning: return
	transitioning = true
	_clear()
	_label("正在准备雨夜森林……", 32)
	await get_tree().process_frame
	await get_tree().process_frame
	var readiness: Dictionary = ASSET_READINESS.check_runtime(asset_manifest_path)
	if not readiness.ok:
		_show_resource_problem(readiness)
		transitioning = false
		return
	if selected.is_empty(): selected = ["afterimage", "echo", "mire"]
	GameState.equipped = selected.duplicate()
	GameState.reset_run()
	_spawn_world()
	root_ui.queue_free()
	transitioning = false

func _show_resource_problem(report: Dictionary) -> void:
	screen = "resource_error"
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	_clear()
	_label("运行模型与材质尚未准备好", 44)
	_label("发现 %d 项资源问题，已暂停进入地图。修复后可以直接重新检查。" % report.issues.size(), 22, FIELD.AMBER)
	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	body.add_child(scroll)
	var details := VBoxContainer.new()
	details.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	details.add_theme_constant_override("separation", 12)
	scroll.add_child(details)
	for problem in report.issues:
		details.add_child(FIELD.label("%s\n%s" % [problem.message, String(problem.path).trim_prefix("res://")], 19, FIELD.MUTED))
	_label("源码版本：先运行 tools/bootstrap_project.py，下载 Git LFS 模型与材质，再用 Godot 4.7.2 打开项目并等待导入完成。", 21)
	_label("已打包版本：重新下载完整安装包。若资源检查通过但画面仍异常，请保留 Godot 的完整报错日志。", 19, FIELD.MUTED)
	var actions := HBoxContainer.new()
	actions.add_theme_constant_override("separation", 24)
	body.add_child(actions)
	actions.add_child(FIELD.button("重新检查并进入", _start_game, true))
	actions.add_child(FIELD.button("返回选科", _return_to_selection))
	actions.add_child(FIELD.button("返回主菜单", _show_menu))
	_focus_first(actions)
	print("ASSET READINESS BLOCKED: ", JSON.stringify(report))

func _return_to_selection() -> void:
	var previous := selected.duplicate()
	_show_selection()
	selected.assign(previous)
	_refresh_skill_buttons()

func _spawn_world() -> void:
	screen = "gameplay"
	world = WORLD.new()
	world.process_mode = Node.PROCESS_MODE_PAUSABLE
	add_child(world)
	world.return_to_menu.connect(_show_menu_from_world)
	world.retry_requested.connect(_restart_world)

func _restart_world() -> void:
	if transitioning: return
	transitioning = true
	get_tree().paused = false
	# Signal callbacks may be running on buttons inside the retiring world.
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
	transitioning = true
	get_tree().paused = false
	if is_instance_valid(world): world.queue_free()
	world = null
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	_build_shell()
	_show_menu()
	transitioning = false
