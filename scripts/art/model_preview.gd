extends SceneTree
const HUNTER := preload("res://scripts/enemies/hunter.gd")
const FOREST := preload("res://scripts/art/forest_detail.gd")
var frames := 0
func _initialize() -> void:
	var scene := Node3D.new()
	root.add_child(scene)
	var camera := Camera3D.new()
	scene.add_child(camera)
	camera.position = Vector3(3,2.6,-5)
	camera.look_at_from_position(camera.position,Vector3(0,1.4,0))
	var model := Node3D.new()
	scene.add_child(model)
	var builder := CharacterBody3D.new()
	builder.set_script(HUNTER)
	builder._build_model(model)
	builder.free()
	var key := OmniLight3D.new()
	key.position = Vector3(1,3,-3)
	key.light_energy = 5.0
	key.omni_range = 15
	scene.add_child(key)
	var tree := FOREST.build(73,true,FOREST.bark_material())
	tree.position = Vector3(-3,0,2)
	scene.add_child(tree)
	var light := DirectionalLight3D.new()
	light.rotation_degrees = Vector3(-40,-35,0)
	light.light_energy = 1.8
	light.shadow_enabled = true
	scene.add_child(light)
	var environment := WorldEnvironment.new()
	var env := Environment.new()
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(.025,.032,.042)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(.25,.3,.4)
	env.ambient_light_energy = .3
	environment.environment = env
	scene.add_child(environment)
func _process(_delta: float) -> bool:
	frames += 1
	if frames == 20:
		root.get_texture().get_image().save_png("res://docs/previews/MODEL_PREVIEW.png")
		quit()
	return false
