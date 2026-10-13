extends RefCounted
## Shared field-instrument typography and surfaces, designed at 1920 × 1080.

const INK := Color("101b1c")
const PANEL := Color("182728")
const PAPER := Color("ede7d8")
const MUTED := Color("a6b6ae")
const GREEN := Color("a6c5aa")
const AMBER := Color("dfb575")
const LINE := Color("3f5450")
static var _shared: Theme

static func get_theme() -> Theme:
	if _shared != null:
		return _shared
	_shared = Theme.new()
	var font := SystemFont.new()
	font.font_names = PackedStringArray(["PingFang SC", "Noto Sans CJK SC", "Microsoft YaHei", "Heiti SC", "sans-serif"])
	_shared.default_font = font
	_shared.default_font_size = 22
	_shared.set_color("font_color", "Label", PAPER)
	_shared.set_color("font_color", "Button", PAPER)
	_shared.set_color("font_hover_color", "Button", PAPER)
	_shared.set_color("font_pressed_color", "Button", INK)
	_shared.set_color("font_disabled_color", "Button", Color("6f817b"))
	_shared.set_stylebox("panel", "PanelContainer", surface())
	_shared.set_stylebox("normal", "Button", surface(Color("243735"), 1, 8, 20, 12))
	_shared.set_stylebox("hover", "Button", surface(Color("304743"), 1, 8, 20, 12, GREEN))
	_shared.set_stylebox("pressed", "Button", surface(GREEN, 1, 8, 20, 12, GREEN))
	_shared.set_stylebox("disabled", "Button", surface(Color("1c2a29"), 1, 8, 20, 12))
	_shared.set_stylebox("focus", "Button", surface(Color(0, 0, 0, 0), 2, 8, 20, 12, AMBER))
	_shared.set_stylebox("background", "ProgressBar", surface(Color("0f1c1b"), 0, 3, 0, 0))
	_shared.set_stylebox("fill", "ProgressBar", surface(GREEN, 0, 3, 0, 0))
	_shared.set_constant("separation", "VBoxContainer", 14)
	_shared.set_constant("separation", "HBoxContainer", 18)
	_shared.set_constant("h_separation", "GridContainer", 18)
	_shared.set_constant("v_separation", "GridContainer", 16)
	return _shared

static func surface(fill := PANEL, border := 1, radius := 10, horizontal := 24, vertical := 20, stroke := LINE) -> StyleBoxFlat:
	var style := StyleBoxFlat.new()
	style.bg_color = fill
	style.border_color = stroke
	style.set_border_width_all(border)
	style.set_corner_radius_all(radius)
	style.content_margin_left = horizontal
	style.content_margin_right = horizontal
	style.content_margin_top = vertical
	style.content_margin_bottom = vertical
	return style

static func label(text: String, size := 22, color := PAPER, wrap := true) -> Label:
	var node := Label.new()
	node.text = text
	node.add_theme_font_size_override("font_size", size)
	node.add_theme_color_override("font_color", color)
	if wrap:
		node.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		node.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	return node

static func button(text: String, callback: Callable, primary := false) -> Button:
	var node := Button.new()
	node.text = text
	node.custom_minimum_size.y = 56
	node.mouse_default_cursor_shape = Control.CURSOR_POINTING_HAND
	node.pressed.connect(callback)
	if primary:
		node.add_theme_stylebox_override("normal", surface(GREEN, 1, 8, 20, 12, GREEN))
		node.add_theme_color_override("font_color", INK)
		node.add_theme_stylebox_override("hover", surface(Color("bdd5bd"), 1, 8, 20, 12, GREEN))
		node.add_theme_color_override("font_hover_color", INK)
	return node

static func eyebrow(text: String) -> Label:
	return label(text, 16, GREEN)

static func divider() -> HSeparator:
	var line := HSeparator.new()
	line.add_theme_stylebox_override("separator", surface(LINE, 0, 0, 0, 0))
	line.custom_minimum_size.y = 1
	return line

static func margin(horizontal: int, vertical: int) -> MarginContainer:
	var node := MarginContainer.new()
	node.add_theme_constant_override("margin_left", horizontal)
	node.add_theme_constant_override("margin_right", horizontal)
	node.add_theme_constant_override("margin_top", vertical)
	node.add_theme_constant_override("margin_bottom", vertical)
	return node

static func backdrop(parent: Control) -> void:
	var gradient := Gradient.new()
	gradient.colors = PackedColorArray([Color("172c2b"), Color("0c1418")])
	var texture := GradientTexture2D.new()
	texture.gradient = gradient
	texture.fill_from = Vector2(0.0, 0.0)
	texture.fill_to = Vector2(0.8, 1.0)
	var background := TextureRect.new()
	background.texture = texture
	background.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	background.mouse_filter = Control.MOUSE_FILTER_IGNORE
	parent.add_child(background)
	# Rain slashes and a horizon repeat the game's weather without obscuring text.
	var horizon := ColorRect.new()
	horizon.color = Color(0.32, 0.44, 0.39, 0.15)
	horizon.set_anchors_and_offsets_preset(Control.PRESET_BOTTOM_WIDE)
	horizon.offset_top = -228
	horizon.offset_bottom = -227
	horizon.mouse_filter = Control.MOUSE_FILTER_IGNORE
	parent.add_child(horizon)
	for index in range(18):
		var rain := ColorRect.new()
		rain.color = Color(0.53, 0.66, 0.60, 0.045)
		rain.position = Vector2(760 + index * 67, 35 + (index % 5) * 96)
		rain.size = Vector2(1, 350 + (index % 3) * 65)
		rain.rotation = 0.20
		rain.mouse_filter = Control.MOUSE_FILTER_IGNORE
		parent.add_child(rain)
