extends Node
const WORLD := preload("res://scripts/world/world.gd")
var world
var frames := 0
func _ready() -> void:
	seed(731)
	world = WORLD.new()
	add_child(world)
	world.set_process(false)
	world.storm_controller.set_process(false)
	world.hunter_director.set_physics_process(false)
	world.player.set_physics_process(false)
	for hunter in world.hunter_nodes: hunter.set_physics_process(false)
func _process(_delta: float) -> void:
	frames += 1
	var item: Node3D = world.objective_nodes[0]
	if frames <= 25:
		world.player.global_position = item.global_position-item.global_basis.z*2.2+Vector3(0,.05,0)
		world.player.camera.look_at_from_position(world.player.global_position+Vector3(0,1.3,0),item.global_position)
		world.storm_controller.lightning.light_energy = 0
		if frames == 25: get_viewport().get_texture().get_image().save_png("res://docs/previews/RESEARCH_BOOK.png")
	else:
		var index := mini(2,int((frames-26)/25))
		var center: Vector3 = [Vector3(-24,0,-28),Vector3(35,0,-12),Vector3(22,0,34)][index]
		world.player.global_position = center+(Vector3(7,0,10) if index == 0 else Vector3(4,0,6))
		var target := center+Vector3(0,5 if index == 0 else 2,0)
		world.player.camera.look_at_from_position(world.player.global_position+Vector3(0,1.5,0),target)
		world.storm_controller.lightning.position = center+Vector3(4,18,10)
		world.storm_controller.lightning.light_energy = 55
		if frames in [50,75,100]:
			get_viewport().get_texture().get_image().save_png("res://docs/previews/LANDMARK_%d.png" % index)
		if frames == 100: get_tree().quit()
	world.update_hud()
