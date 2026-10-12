extends CanvasLayer

var world
var objective_label: Label
var slots_label: Label
var stamina_bar: ProgressBar
var status_label: Label
var notice_timer := 0.0
var pause_overlay: PanelContainer
var handbook_panel: PanelContainer

func setup(game_world) -> void:
	world = game_world
	process_mode = Node.PROCESS_MODE_ALWAYS
	layer = 10
	_build()

func _build() -> void:
	var panel:=PanelContainer.new();panel.position=Vector2(10,8);panel.custom_minimum_size=Vector2(250,0);add_child(panel)
	var v:=VBoxContainer.new();panel.add_child(v)
	objective_label=Label.new();objective_label.add_theme_font_size_override("font_size",12);v.add_child(objective_label)
	slots_label=Label.new();slots_label.add_theme_font_size_override("font_size",10);slots_label.text="1/2/3 技能   E 交互   Shift 奔跑   TAB 手册";v.add_child(slots_label)
	stamina_bar=ProgressBar.new();stamina_bar.max_value=100;stamina_bar.show_percentage=false;stamina_bar.custom_minimum_size=Vector2(180,8);v.add_child(stamina_bar)
	status_label=Label.new();status_label.set_anchors_preset(Control.PRESET_CENTER_BOTTOM);status_label.position=Vector2(-260,-62);status_label.size=Vector2(520,36);status_label.add_theme_font_size_override("font_size",11);status_label.horizontal_alignment=HORIZONTAL_ALIGNMENT_CENTER;add_child(status_label)
	var cross:=Label.new();cross.text="+";cross.set_anchors_preset(Control.PRESET_CENTER);cross.position=Vector2(-5,-12);add_child(cross)

func update_display() -> void:
	if not is_instance_valid(objective_label) or not is_instance_valid(world.player): return
	objective_label.text="研究记录：%d / 3     试剂：%d\n体力：%d%%     追猎者：%s" % [world.collected,world.luminol_charges,roundi(world.player.stamina),world.hunter_state_label()]
	stamina_bar.value=world.player.stamina
	var names: Array[String]=[]
	for id in GameState.equipped: names.append(GameState.skill_data(id).name.split(" /")[0])
	slots_label.text="1 %s   2 %s   3 %s\nE 交互  ·  Shift 奔跑  ·  TAB 手册" % [names[0] if names.size()>0 else "—",names[1] if names.size()>1 else "—",names[2] if names.size()>2 else "—"]

	slots_label.text += "\n研究指引："+world.research_hint()

func notice(text: String) -> void:
	status_label.text=text
	notice_timer=3.5

func _process(delta: float) -> void:
	if notice_timer > 0.0:
		notice_timer -= delta
		if notice_timer <= 0.0 and is_instance_valid(status_label): status_label.text=""

func show_pause() -> void:
	if is_instance_valid(pause_overlay): pause_overlay.queue_free()
	pause_overlay=PanelContainer.new();pause_overlay.process_mode=Node.PROCESS_MODE_ALWAYS;pause_overlay.set_anchors_preset(Control.PRESET_CENTER);pause_overlay.position=Vector2(-180,-90);pause_overlay.custom_minimum_size=Vector2(360,180);add_child(pause_overlay)
	var v:=VBoxContainer.new();pause_overlay.add_child(v)
	var title:=Label.new();title.text="试炼暂停";title.horizontal_alignment=HORIZONTAL_ALIGNMENT_CENTER;v.add_child(title)
	var resume:=Button.new();resume.text="继续";resume.pressed.connect(world.toggle_pause);v.add_child(resume)
	var retry:=Button.new();retry.text="重新开始";retry.pressed.connect(func():world.get_tree().paused=false;world.retry_requested.emit());v.add_child(retry)
	var menu:=Button.new();menu.text="返回主菜单";menu.pressed.connect(func():world.get_tree().paused=false;Input.mouse_mode=Input.MOUSE_MODE_VISIBLE;world.return_to_menu.emit());v.add_child(menu)

func hide_pause() -> void:
	if is_instance_valid(pause_overlay): pause_overlay.queue_free()

func show_handbook(skill_entries: Array[String], fusion_entries: Array[String]) -> void:
	if is_instance_valid(handbook_panel): handbook_panel.queue_free()
	handbook_panel=PanelContainer.new();handbook_panel.process_mode=Node.PROCESS_MODE_ALWAYS;handbook_panel.set_anchors_preset(Control.PRESET_CENTER);handbook_panel.position=Vector2(-280,-160);handbook_panel.custom_minimum_size=Vector2(560,320);add_child(handbook_panel)
	var content:=VBoxContainer.new();handbook_panel.add_child(content)
	var title:=Label.new();title.text="研究手册 / FIELD NOTES";title.horizontal_alignment=HORIZONTAL_ALIGNMENT_CENTER;content.add_child(title)
	var scroll:=ScrollContainer.new();scroll.size_flags_vertical=Control.SIZE_EXPAND_FILL;content.add_child(scroll)
	var entries:=VBoxContainer.new();entries.size_flags_horizontal=Control.SIZE_EXPAND_FILL;scroll.add_child(entries)
	for text in skill_entries + fusion_entries:
		var label:=Label.new();label.text=text;label.autowrap_mode=TextServer.AUTOWRAP_WORD_SMART;entries.add_child(label)
	var close:=Button.new();close.text="关闭手册";close.pressed.connect(func():world.notebook=false;hide_handbook());content.add_child(close)

func hide_handbook() -> void:
	if is_instance_valid(handbook_panel): handbook_panel.queue_free()

func show_outcome(won: bool) -> void:
	var box:=PanelContainer.new();box.process_mode=Node.PROCESS_MODE_ALWAYS;box.set_anchors_preset(Control.PRESET_CENTER);box.position=Vector2(-190,-100);box.custom_minimum_size=Vector2(380,200);add_child(box)
	var v:=VBoxContainer.new();box.add_child(v)
	var label:=Label.new();label.text="你逃出了梦境。" if won else "You became part of the experiment.";label.horizontal_alignment=HORIZONTAL_ALIGNMENT_CENTER;v.add_child(label)
	var retry:=Button.new();retry.text="重新开始";retry.pressed.connect(func():world.get_tree().paused=false;world.retry_requested.emit());v.add_child(retry)
	var menu:=Button.new();menu.text="返回主菜单";menu.pressed.connect(func():world.get_tree().paused=false;world.return_to_menu.emit());v.add_child(menu)
