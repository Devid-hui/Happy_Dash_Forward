extends Node3D
const LANDMARKS := preload("res://scripts/props/landmark_models.gd")
const FOREST := preload("res://scripts/art/forest_detail.gd")
const BOOK := preload("res://scripts/props/research_book.gd")
const EQUIPMENT := preload("res://scripts/player/field_equipment.gd")
const TERRAIN := preload("res://scripts/art/terrain_detail.gd")
var camera: Camera3D
var root: Node3D
var equipment: Node3D
var frames := 0
var view := 0

func _ready() -> void:
	DirAccess.make_dir_recursive_absolute("res://docs/previews")
	var world_environment := WorldEnvironment.new(); var env := Environment.new()
	env.background_mode = Environment.BG_COLOR; env.background_color = Color(.12,.16,.17)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR; env.ambient_light_color = Color(.64,.71,.70); env.ambient_light_energy = .42
	env.tonemap_mode = Environment.TONE_MAPPER_FILMIC; world_environment.environment = env; add_child(world_environment)
	var key := DirectionalLight3D.new(); key.light_energy = 1.15; key.rotation_degrees = Vector3(-42,-28,0); add_child(key)
	var rim := OmniLight3D.new(); rim.omni_range = 30; rim.light_energy = 16; rim.position = Vector3(-3,5,-4); rim.light_color = Color(.30,.48,.52); add_child(rim)
	camera = Camera3D.new(); camera.current = true; camera.fov = 62; add_child(camera)
	root = Node3D.new(); add_child(root)
	_switch(0)

func _switch(index: int) -> void:
	for child in root.get_children(): child.free()
	if is_instance_valid(equipment): equipment.free()
	var plane := MeshInstance3D.new(); var plane_mesh := PlaneMesh.new(); plane_mesh.size = Vector2(30,30)
	plane.mesh = plane_mesh; plane.material_override = TERRAIN.ground_material(); root.add_child(plane)
	match index:
		0:
			LANDMARKS.car(root); camera.look_at_from_position(Vector3(4.2,2.3,5.3),Vector3(0,.85,0))
		1:
			LANDMARKS.tower(root); camera.look_at_from_position(Vector3(12,7,19),Vector3(0,6,0))
		2:
			LANDMARKS.dead_tree(root); camera.look_at_from_position(Vector3(5.0,3.0,8.0),Vector3(0,3.5,0))
		3:
			var tree := FOREST.build(41,false,FOREST.bark_material()); root.add_child(tree)
			camera.look_at_from_position(Vector3(5,3,8),Vector3(0,4.3,0))
		4:
			var book := BOOK.new(); root.add_child(book); book.position.y = .7
			camera.look_at_from_position(Vector3(.95,1.30,-1.5),Vector3(0,.70,0))
		5,6,7,9,10:
			camera.look_at_from_position(Vector3(0,1.5,3),Vector3(0,1.5,-5))
			equipment = EQUIPMENT.new(); camera.add_child(equipment); equipment.setup(self)
			if index == 6: equipment.trigger("flash"); equipment.tick(.27)
			if index == 7: equipment.trigger("luminol"); equipment.tick(.34)
			if index == 9: equipment.trigger("salt"); equipment.tick(.37)
			if index == 10: equipment.trigger("mud"); equipment.tick(.32)
		8:
			var specimen := (load(EQUIPMENT.ASSET_PATH) as PackedScene).instantiate() as Node3D
			root.add_child(specimen); specimen.position.y = 1.0
			(specimen.find_child("LeftSupport",true,false) as Node3D).visible = false
			(specimen.find_child("SkillTools",true,false) as Node3D).visible = false
			camera.look_at_from_position(Vector3(.65,1.43,-1.25),Vector3(0,.91,0))

func _process(_delta: float) -> void:
	frames += 1
	if frames%28 != 0: return
	var labels := ["CAR","TOWER","DEAD_TREE","FOREST_TREE","REPORT","SPECTROLAMP","BURST_GRIP","REAGENT_GRIP","OPTICAL_INSTRUMENT","SALT_PLACEMENT","MUD_THROW"]
	get_viewport().get_texture().get_image().save_png("res://docs/previews/REFINED_%s.png" % labels[view])
	view += 1
	if view >= labels.size(): print("ASSET PREVIEW PASS: eleven native-rendered fixed views"); get_tree().quit(); return
	_switch(view)
