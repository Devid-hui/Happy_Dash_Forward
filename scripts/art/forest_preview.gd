extends Node
const WORLD := preload("res://scripts/world/world.gd")
var world: Node3D
var frames := 0
func _ready() -> void:
	seed(731)
	world = Node3D.new()
	world.set_script(WORLD)
	add_child(world)
func _process(_delta: float) -> void:
	frames += 1
	if frames < 5: return
	world.set_process(false)
	world.storm_controller.set_process(false)
	world.player.set_physics_process(false)
	var hunter: Node3D = world.hunter_nodes[0]
	hunter.set_physics_process(false)
	hunter.position = Vector3(0,0,-5)
	hunter.rotation.y = PI
	var camera: Camera3D = world.player.camera
	camera.look_at_from_position(Vector3(0,1.5,0),Vector3(0,1.5,-5))
	if frames == 25:
		get_viewport().get_texture().get_image().save_png("res://docs/previews/FOREST_DARK.png")
	if frames == 26:
		world.storm_controller.trigger_strike(Vector3(12,0,-20))
	if frames > 25:
		world.storm_controller.lightning.position = Vector3(12,18,-20)
		world.storm_controller.lightning.light_energy = 180.0
	if frames == 45:
		get_viewport().get_texture().get_image().save_png("res://docs/previews/FOREST_FLASH.png")
	if frames == 46:
		world.storm_controller.trigger_strike(Vector3(12,0,10))
	if frames > 45:
		world.storm_controller.lightning.position = Vector3(12,18,10)
	if frames == 65:
		get_viewport().get_texture().get_image().save_png("res://docs/previews/FOREST_FRONT_LIGHT.png")
	if frames > 65:
		world.notice("")
		world.storm_controller.lightning.light_energy = 0.0
		world.storm_controller.bolt.visible = false
		for npc in world.hunter_nodes: npc.set_physics_process(false)
		for tree in world.get_children():
			if tree.name.begins_with("Detailed"):
				world.player.global_position = tree.global_position+Vector3(0,0,3)
				camera.look_at_from_position(world.player.global_position+Vector3(0,1.5,0),tree.global_position+Vector3(0,.5,0))
				break
	if frames == 85:
		get_viewport().get_texture().get_image().save_png("res://docs/previews/NEAR_GROUND_DARK.png")
		get_tree().quit()
	return
