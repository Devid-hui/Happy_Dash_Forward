extends CanvasLayer

const FIELD := preload("res://scripts/ui/field_theme.gd")
var world
var objective_label: Label
var slots_label: Label
var stamina_bar: ProgressBar
var energy_bar: ProgressBar
var noise_bar: ProgressBar
var energy_label: Label
var stamina_label: Label
var noise_label: Label
var lamp_label: Label
var hunter_label: Label
var research_label: Label
var status_label: Label
var slot_labels: Array[Label] = []
var notice_timer := 0.0
var pause_overlay: PanelContainer
var handbook_panel: PanelContainer
var upgrade_panel: PanelContainer
var outcome_panel: PanelContainer
var hud_root: Control
var _upgrade_submitted := false
var _upgrade_generation := 0
var _handbook_entries: Array[String] = []
var _fusion_entries: Array[String] = []
var _handbook_body: VBoxContainer

func setup(game_world) -> void:
	world = game_world
	process_mode = Node.PROCESS_MODE_ALWAYS
	layer = 10
	_build()

func _input(event: InputEvent) -> void:
	if not is_instance_valid(world) or world.is_queued_for_deletion() or GameState.game_over: return
	if not event.is_action_pressed("handbook", true) and not event.is_action_pressed("ui_cancel", true): return
	get_viewport().set_input_as_handled()
	if event is InputEventKey and event.echo: return
	if event.is_action_pressed("handbook") or world.notebook:
		world.toggle_handbook()
	else:
		world.toggle_pause()

func _build() -> void:
	hud_root = Control.new()
	hud_root.name = "FieldHUD"
	hud_root.theme = FIELD.get_theme()
	hud_root.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	hud_root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(hud_root)
	var mission := PanelContainer.new()
	mission.name = "Mission"
	mission.position = Vector2(32, 28)
	mission.custom_minimum_size = Vector2(470, 0)
	mission.add_theme_stylebox_override("panel", FIELD.surface(Color(0.055, 0.105, 0.105, 0.78), 1, 8, 20, 16))
	hud_root.add_child(mission)
	var notes := VBoxContainer.new()
	notes.add_theme_constant_override("separation", 6)
	mission.add_child(notes)
	notes.add_child(FIELD.eyebrow("FIELD STUDY  /  科研报告"))
	objective_label = FIELD.label("0 / 3  ·  寻找森林地标", 25)
	notes.add_child(objective_label)
	research_label = FIELD.label("", 18, FIELD.MUTED)
	research_label.custom_minimum_size.x = 430
	notes.add_child(research_label)
	var lamp := VBoxContainer.new()
	lamp.set_anchors_and_offsets_preset(Control.PRESET_TOP_RIGHT)
	lamp.position = Vector2(-430, 30)
	lamp.custom_minimum_size.x = 398
	hud_root.add_child(lamp)
	lamp_label = FIELD.label("谱灯 Lv.1  ·  集中爆发", 21, FIELD.GREEN)
	lamp_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	lamp.add_child(lamp_label)
	hunter_label = FIELD.label("", 18, FIELD.MUTED)
	hunter_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	lamp.add_child(hunter_label)
	var keys := FIELD.label("左键 释放  ·  L / 右键 照明\nE 交互  ·  Tab 手册  ·  Esc 暂停", 17, FIELD.MUTED)
	keys.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	lamp.add_child(keys)
	var resources := PanelContainer.new()
	resources.name = "SharedResources"
	resources.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_LEFT)
	resources.position = Vector2(32, -224)
	resources.custom_minimum_size = Vector2(348, 118)
	resources.add_theme_stylebox_override("panel", FIELD.surface(Color(0.055, 0.105, 0.105, 0.80), 1, 8, 18, 12))
	hud_root.add_child(resources)
	var meters := VBoxContainer.new()
	meters.add_theme_constant_override("separation", 7)
	resources.add_child(meters)
	var energy_row := _meter(meters, "共享电量", FIELD.GREEN)
	energy_label = energy_row.label
	energy_bar = energy_row.bar
	var stamina_row := _meter(meters, "体力", FIELD.PAPER)
	stamina_label = stamina_row.label
	stamina_bar = stamina_row.bar
	var noise_row := _meter(meters, "乱频噪声", FIELD.AMBER)
	noise_label = noise_row.label
	noise_bar = noise_row.bar
	var slots := HBoxContainer.new()
	slots.name = "EquipmentSlots"
	slots.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_LEFT)
	slots.position = Vector2(32, -95)
	slots.add_theme_constant_override("separation", 12)
	hud_root.add_child(slots)
	for index in range(3):
		var panel := PanelContainer.new()
		panel.custom_minimum_size = Vector2(248, 66)
		panel.add_theme_stylebox_override("panel", FIELD.surface(Color(0.055, 0.105, 0.105, 0.82), 1, 7, 16, 9))
		slots.add_child(panel)
		var slot := FIELD.label("%d  —" % (index + 1), 19)
		slot.name = "Slot%d" % (index + 1)
		panel.add_child(slot)
		slot_labels.append(slot)
	# Retained for existing consumers; the three cards carry the visible layout.
	slots_label = FIELD.label("", 18)
	slots_label.visible = false
	hud_root.add_child(slots_label)
	status_label = FIELD.label("", 22)
	status_label.name = "FieldNotice"
	status_label.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_WIDE)
	status_label.offset_left = 450
	status_label.offset_right = -450
	status_label.offset_top = -292
	status_label.offset_bottom = -240
	status_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	status_label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	status_label.add_theme_color_override("font_shadow_color", Color(0, 0, 0, 0.9))
	status_label.add_theme_constant_override("shadow_offset_x", 1)
	status_label.add_theme_constant_override("shadow_offset_y", 2)
	hud_root.add_child(status_label)
	var cross := FIELD.label("·", 28, Color(0.91, 0.94, 0.85, 0.72), false)
	cross.name = "Crosshair"
	cross.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
	cross.position = Vector2(-5, -20)
	hud_root.add_child(cross)
	_ignore_pointer(hud_root)

func _meter(parent: VBoxContainer, caption: String, color: Color) -> Dictionary:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 12)
	parent.add_child(row)
	var text := FIELD.label(caption, 17, color, false)
	text.custom_minimum_size.x = 122
	row.add_child(text)
	var bar := ProgressBar.new()
	bar.max_value = 100
	bar.show_percentage = false
	bar.custom_minimum_size = Vector2(172, 7)
	bar.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	bar.add_theme_stylebox_override("fill", FIELD.surface(color, 0, 3, 0, 0))
	row.add_child(bar)
	return {"label": text, "bar": bar}

func _ignore_pointer(node: Node) -> void:
	if node is Control: node.mouse_filter = Control.MOUSE_FILTER_IGNORE
	for child in node.get_children(): _ignore_pointer(child)

func _level(id: String) -> int:
	return GameState.ability_level(id)

func update_display() -> void:
	if not is_instance_valid(objective_label) or not is_instance_valid(world.player): return
	objective_label.text = "%d / 3  ·  %s" % [world.collected, "出口已开启" if world.collected >= 3 else "寻找森林地标"]
	research_label.text = world.research_hint()
	hunter_label.text = "追猎者：%s  ·  试剂 %d" % [world.hunter_state_label(), world.luminol_charges]
	var stamina: float = world.player.stamina
	var energy: float = world.player.energy
	var capacity: float = world.player.energy_capacity()
	var noise: float = world.player.noise
	stamina_bar.value = stamina
	stamina_label.text = "体力  %d" % roundi(stamina)
	energy_bar.max_value = capacity
	energy_bar.value = energy
	energy_label.text = "电量  %d/%d" % [roundi(energy), roundi(capacity)]
	noise_bar.value = noise
	noise_label.text = "噪声  %d" % roundi(noise)
	noise_label.modulate = Color(1.0, 0.70, 0.52) if noise >= 70.0 else Color.WHITE
	var mode: bool = world.player.pulse_mode
	var enabled: bool = world.player.lamp_enabled
	lamp_label.text = "谱灯 Lv.%d  ·  %s  ·  %s" % [_level("lamp"), "点射" if mode else "集中爆发", "照明开" if enabled else "照明关"]
	var names: Array[String] = []
	for index in range(3):
		if index < GameState.equipped.size():
			var id: String = GameState.equipped[index]
			var name: String = GameState.skill_data(id).name.split(" /")[0]
			var cooldown := 0.0
			if is_instance_valid(world.player.skill_manager):
				cooldown = float(world.player.skill_manager.cooldowns.get(id, 0.0))
			slot_labels[index].text = "%d  %s\n    Lv.%d  ·  %s" % [index + 1, name, _level(id), "%.1fs" % cooldown if cooldown > 0.0 else "就绪"]
			slot_labels[index].modulate = Color(0.75, 0.82, 0.78) if cooldown > 0.0 else Color.WHITE
			names.append("%d %s Lv.%d" % [index + 1, name, _level(id)])
		else:
			slot_labels[index].text = "%d  空槽\n    未装备能力" % (index + 1)
	slots_label.text = "   ".join(names) + "\nE 交互  ·  Shift 奔跑  ·  Tab 手册\n研究指引：" + world.research_hint()

func notice(text: String) -> void:
	status_label.text = text
	notice_timer = 3.5

func _process(delta: float) -> void:
	if not is_instance_valid(world) or world.is_queued_for_deletion() or world.is_gameplay_blocked(): return
	if notice_timer > 0.0:
		notice_timer -= delta
		if notice_timer <= 0.0 and is_instance_valid(status_label): status_label.text = ""

func _modal(title: String, subtitle: String, dimensions: Vector2) -> Dictionary:
	var shell := Control.new()
	shell.name = "Modal_" + title
	shell.theme = FIELD.get_theme()
	shell.process_mode = Node.PROCESS_MODE_ALWAYS
	shell.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(shell)
	var shade := ColorRect.new()
	shade.color = Color(0.015, 0.035, 0.037, 0.87)
	shade.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	shell.add_child(shade)
	var inset := FIELD.margin(64, 48)
	inset.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	shell.add_child(inset)
	var center := CenterContainer.new()
	inset.add_child(center)
	var panel := PanelContainer.new()
	panel.custom_minimum_size = dimensions
	panel.set_meta("modal_shell", shell)
	center.add_child(panel)
	var content := VBoxContainer.new()
	content.add_theme_constant_override("separation", 18)
	panel.add_child(content)
	content.add_child(FIELD.eyebrow("THE MIDNIGHT ACADEMY  /  FIELD STUDY"))
	content.add_child(FIELD.label(title, 38))
	if not subtitle.is_empty(): content.add_child(FIELD.label(subtitle, 21, FIELD.MUTED))
	content.add_child(FIELD.divider())
	return {"panel": panel, "content": content}

func _discard_modal(panel: PanelContainer) -> void:
	if not is_instance_valid(panel): return
	var shell: Control = panel.get_meta("modal_shell", null)
	if is_instance_valid(shell): shell.queue_free()
	else: panel.queue_free()

func _focus_first(node: Node) -> bool:
	if node is Button and not node.disabled:
		node.call_deferred("grab_focus")
		return true
	for child in node.get_children():
		if _focus_first(child): return true
	return false

func show_pause() -> void:
	if is_instance_valid(pause_overlay): return
	var view := _modal("试炼暂停", "雨声暂歇，研究记录与本局成长保留。", Vector2(640, 0))
	pause_overlay = view.panel
	var content: VBoxContainer = view.content
	content.add_child(FIELD.button("继续", world.toggle_pause, true))
	content.add_child(FIELD.button("重新开始", world.request_retry))
	content.add_child(FIELD.button("返回主菜单", world.request_menu))
	content.add_child(FIELD.label("Esc 继续  ·  Tab 查阅手册", 18, FIELD.MUTED))
	_focus_first(pause_overlay)

func hide_pause() -> void:
	_discard_modal(pause_overlay)
	pause_overlay = null

func show_handbook(skill_entries: Array[String], fusion_entries: Array[String]) -> void:
	_discard_modal(handbook_panel)
	_handbook_entries = skill_entries.duplicate()
	_fusion_entries = fusion_entries.duplicate()
	var view := _modal("研究手册", "学科原理、游戏放大与限制分开阅读。升级只作用于本局。", Vector2(1080, 800))
	handbook_panel = view.panel
	var content: VBoxContainer = view.content
	var tabs := HBoxContainer.new()
	content.add_child(tabs)
	tabs.add_child(FIELD.button("本局能力与融合", _render_handbook.bind(false)))
	tabs.add_child(FIELD.button("历史研究档案", _render_handbook.bind(true)))
	var scroll := ScrollContainer.new()
	scroll.name = "HandbookScroll"
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	content.add_child(scroll)
	_handbook_body = VBoxContainer.new()
	_handbook_body.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_handbook_body.add_theme_constant_override("separation", 22)
	scroll.add_child(_handbook_body)
	_render_handbook(false)
	content.add_child(FIELD.button("关闭手册", world.toggle_handbook, true))
	_focus_first(handbook_panel)

func _render_handbook(history: bool) -> void:
	if not is_instance_valid(_handbook_body): return
	for child in _handbook_body.get_children():
		_handbook_body.remove_child(child)
		child.queue_free()
	var lines: Array = []
	if history:
		lines = GameState.archive_lines()
		_handbook_body.add_child(FIELD.eyebrow("历史发现  /  本机保存"))
		_handbook_body.add_child(FIELD.label("档案保留知识、报告和融合记录；新的一局重新获得基础等级。", 20, FIELD.MUTED))
	else:
		_handbook_body.add_child(FIELD.eyebrow("本局能力"))
		lines.append("谱灯 Lv.%d：便携科研光学仪器。右键独立开关照明，左键释放；照明、爆发、点射与加速共用电量。关灯且不加速时，释放后的短暂等待结束后才缓慢回充。强光与乱频有短暂视听代价。" % _level("lamp"))
		lines.append_array(_handbook_entries)
		lines.append("本局融合发现")
		lines.append_array(_fusion_entries)
	if lines.is_empty(): lines.append("尚未建立研究记录。进入雨夜，收集报告并尝试学科融合。")
	for text in lines:
		_handbook_body.add_child(FIELD.label(str(text), 21))
	var scroll := _handbook_body.get_parent() as ScrollContainer
	scroll.scroll_vertical = 0

func hide_handbook() -> void:
	_discard_modal(handbook_panel)
	handbook_panel = null
	_handbook_body = null

func show_upgrade(options: Array[Dictionary]) -> void:
	_discard_modal(upgrade_panel)
	_upgrade_generation += 1
	_upgrade_submitted = false
	var view := _modal("科研报告已收录", "第 %d / 3 份报告  ·  选择一项能力强化，确认后继续探索。" % world.collected, Vector2(1140, 900))
	upgrade_panel = view.panel
	var content: VBoxContainer = view.content
	content.add_theme_constant_override("separation", 12)
	var scroll := ScrollContainer.new()
	scroll.name = "UpgradeScroll"
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	content.add_child(scroll)
	var grid := GridContainer.new()
	grid.columns = 2
	grid.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(grid)
	for option in options:
		var card := PanelContainer.new()
		card.name = "Upgrade_" + str(option.id)
		card.custom_minimum_size = Vector2(510, 205)
		card.size_flags_horizontal = Control.SIZE_EXPAND_FILL
		card.add_theme_stylebox_override("panel", FIELD.surface(Color("223431"), 1, 8, 20, 14))
		grid.add_child(card)
		var details := VBoxContainer.new()
		details.add_theme_constant_override("separation", 7)
		card.add_child(details)
		details.add_child(FIELD.eyebrow("Lv.%d → Lv.%d  /  %s" % [option.level, option.next_level, "进阶" if int(option.next_level) == 2 else "精修"]))
		details.add_child(FIELD.label(str(option.name).split(" /")[0], 26))
		details.add_child(FIELD.label(str(option.benefit), 20))
		var cost: String = str(option.get("cost", ""))
		if cost.is_empty():
			cost = "照明与释放仍消耗共享电量，强光后保留短暂视线干扰。" if option.id == "lamp" else str(GameState.skill_data(option.id).cost)
		if not cost.is_empty(): details.add_child(FIELD.label("仍需承担：" + cost, 17, FIELD.AMBER))
		details.add_child(FIELD.button("强化这项能力", _choose_upgrade.bind(str(option.id), _upgrade_generation)))
	if options.is_empty():
		grid.add_child(FIELD.label("本局可选能力均已达到精修等级。报告已经收录，出口条件继续保留。", 24))
		content.add_child(FIELD.button("继续探索", _choose_upgrade.bind("", _upgrade_generation), true))
	content.add_child(FIELD.label("共三次自主强化，可专精或分散投入。不会增加技能槽，也不会中途更换装备。", 18, FIELD.MUTED))
	_focus_first(upgrade_panel)

func _choose_upgrade(id: String, generation: int) -> void:
	# Confirmation may synchronously build a second pending report's panel.
	# Its buttons own a new generation; a retiring panel cannot spend that report.
	if generation != _upgrade_generation or _upgrade_submitted or not is_instance_valid(upgrade_panel): return
	_upgrade_submitted = true
	_disable_buttons(upgrade_panel)
	world.confirm_upgrade(id)

func _disable_buttons(node: Node) -> void:
	if node is Button: node.disabled = true
	for child in node.get_children(): _disable_buttons(child)

func hide_upgrade() -> void:
	_upgrade_generation += 1
	_discard_modal(upgrade_panel)
	upgrade_panel = null
	_upgrade_submitted = false

func show_outcome(won: bool) -> void:
	if is_instance_valid(outcome_panel): return
	var view := _modal("你逃出了梦境。" if won else "雨夜仍在继续。", "带回的研究发现已进入本机档案。" if won else "You became part of the experiment.", Vector2(760, 0))
	outcome_panel = view.panel
	var content: VBoxContainer = view.content
	content.add_child(FIELD.label("科研报告  %d / 3    ·    自主强化  %d 次" % [world.collected, GameState.upgrades], 23, FIELD.GREEN))
	content.add_child(FIELD.label("下一局重新从基础等级出发，保留已经理解的学科知识和融合发现。", 21, FIELD.MUTED))
	content.add_child(FIELD.button("重新开始", world.request_retry, true))
	content.add_child(FIELD.button("返回主菜单", world.request_menu))
	_focus_first(outcome_panel)
