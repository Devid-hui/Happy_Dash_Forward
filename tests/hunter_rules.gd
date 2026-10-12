extends Node
const World := preload("res://scripts/world/world.gd")

func _ready() -> void:
	call_deferred("run_checks")

func run_checks() -> void:
	seed(721)
	GameState.game_over = false
	var world := World.new()
	add_child(world)
	await get_tree().physics_frame
	await get_tree().physics_frame
	world.player.set_physics_process(false)
	world.hunter_director.set_physics_process(false)
	for hunter in world.hunter_nodes: hunter.set_physics_process(false)
	var player = world.player
	var hunter = world.hunter_nodes[0]
	var other = world.hunter_nodes[1]
	assert(world.hunter_nodes.size() == 5)
	var directions: Array[Vector3] = []
	for npc in world.hunter_nodes: directions.append((npc.global_position-world.player.global_position).normalized())
	var surrounds := false
	for a in directions:
		for b in directions:
			if a.dot(b) < -.7: surrounds = true
	assert(surrounds,"initial spawn must surround player instead of sharing one forward cone")
	var Visual := preload("res://scripts/enemies/hunter_visual.gd")
	assert(Visual.build_count == 1,"all instances must share one generated model")
	var mesh_a: MeshInstance3D = world.hunter_nodes[0].get_node("VisualRoot").get_child(0).get_child(0)
	var mesh_b: MeshInstance3D = world.hunter_nodes[1].get_node("VisualRoot").get_child(0).get_child(0)
	assert(mesh_a.mesh == mesh_b.mesh,"mesh resources must be shared")
	assert(hunter.stats != other.stats,"configuration copies must be independent")
	hunter.stats.max_health = 120.0
	assert(other.stats.max_health == 100.0)
	hunter.take_damage(12.0)
	assert(hunter.health == 88.0 and other.health == 100.0)
	hunter.take_damage(-5.0)
	assert(hunter.health == 88.0)
	for input in [Vector2(0,1),Vector2(.7,.7),Vector2(-.7,.7)]:
		var movement: Dictionary = player.movement_settings(input,true)
		assert(not movement.running and movement.speed < hunter.stats.move_speed,"backward sprint must be blocked")
	assert(player.movement_settings(Vector2(0,-1),true).speed == player.run_speed)
	player.stamina = 0.0
	assert(not player.movement_settings(Vector2(0,-1),true).running)
	player.stamina = 100.0
	player.velocity = Vector3(0,0,7.5)
	Input.action_press("move_back"); Input.action_press("sprint")
	player._physics_process(.016)
	assert(Vector2(player.velocity.x,player.velocity.z).length() <= player.backward_speed+.001,"previous sprint inertia must not bypass backward cap")
	assert(player.stamina == 100.0,"backward Shift must not drain sprint stamina")
	Input.action_release("move_back"); Input.action_release("sprint")
	hunter.charge_phase = hunter.ChargePhase.NORMAL
	hunter.tick_charge(.1,100.0,true)
	assert(hunter.charge_phase == hunter.ChargePhase.NORMAL)
	hunter.tick_charge(.1,6.0,true)
	assert(hunter.charge_phase == hunter.ChargePhase.WARNING and hunter.voice.playing)
	hunter.tick_charge(hunter.stats.charge_warning_duration,6.0,true)
	assert(hunter.charge_phase == hunter.ChargePhase.CHARGING)
	assert(hunter.current_speed() > player.run_speed and hunter.current_speed() < player.run_speed*1.2)
	assert(hunter.stats.charge_duration == 2.0)
	hunter.tick_charge(1.9,6.0,true)
	assert(hunter.charge_phase == hunter.ChargePhase.CHARGING)
	hunter.tick_charge(.11,6.0,true)
	assert(hunter.charge_phase == hunter.ChargePhase.RESTING and hunter.current_speed() == hunter.stats.move_speed)
	hunter.tick_charge(7.9,6.0,true)
	assert(hunter.charge_phase == hunter.ChargePhase.RESTING)
	hunter.tick_charge(.11,6.0,true)
	assert(hunter.charge_phase == hunter.ChargePhase.NORMAL)
	hunter.tick_charge(.1,6.0,false)
	assert(hunter.charge_phase == hunter.ChargePhase.NORMAL)
	# 玩家朝 -Z 看但向 +X 移动，刷新必须出现在 +X 前方扇区。
	player.global_position = Vector3.ZERO
	player.velocity = Vector3(7.5,0,0)
	player.is_sprinting = true
	for npc in world.hunter_nodes: npc.global_position = Vector3(-45,0,world.hunter_nodes.find(npc)*4.0)
	player.rotation.y = 0
	hunter.global_position = Vector3(-90,0,0)
	var director = world.hunter_director
	for npc in world.hunter_nodes: director.recycle_cooldowns[npc.get_instance_id()] = 0.0
	director.scan_timer = 0.0
	# 看着后方敌人时必须保留原位置，即使运动方向朝 +X。
	player.camera.look_at_from_position(Vector3(0,1.5,0),Vector3(-45,1.5,0))
	director._physics_process(.5)
	assert(hunter.global_position.x < 0.0,"watched enemies must not teleport")
	player.camera.look_at_from_position(Vector3(0,1.5,0),Vector3(0,1.5,-5))
	director.scan_timer = 0.0
	director._physics_process(.5)
	var transported := 0
	for npc in world.hunter_nodes:
		if npc.global_position.x > 0.0: transported += 1
	assert(transported == 3,"one batch must move at most three of five enemies")
	var moved_hunter = world.hunter_nodes.filter(func(npc): return npc.global_position.x > 0.0)[0]
	var offset: Vector3 = moved_hunter.global_position-player.global_position
	assert(offset.x > 0.0 and offset.length() >= 16.0 and offset.length() <= 24.1)
	assert(moved_hunter.charge_phase == hunter.ChargePhase.RESTING,"relocation must not charge immediately")
	assert(hunter.health == 88.0,"relocation preserves health")
	var storm = world.storm_controller
	storm.set_process(false)
	assert(storm.lightning is OmniLight3D and storm.lightning.shadow_enabled)
	storm.trigger_strike(Vector3(60,0,-40))
	assert(storm.lightning.position == Vector3(60,18,-40) and storm.bolt.visible)
	storm.trigger_strike(Vector3(-30,0,50))
	assert(storm.lightning.position == Vector3(-30,18,50))
	storm._process(.5)
	assert(storm.lightning.light_energy == 0.0 and not storm.bolt.visible)
	var obstacle := StaticBody3D.new()
	var collision := CollisionShape3D.new()
	var box := BoxShape3D.new(); box.size = Vector3(4,4,4)
	collision.shape = box; obstacle.add_child(collision)
	obstacle.position = Vector3(25,2,0); world.add_child(obstacle)
	await get_tree().physics_frame
	assert(not director.candidate_is_clear(hunter,Vector3(25,0,0)),"spawn capsule must reject obstacles")
	assert(not director.candidate_is_clear(hunter,Vector3(1,0,0)),"spawn must reject near player")
	# 黑暗、远距离、静止玩家均不能使追踪目标丢失。
	hunter.global_position = Vector3(0,0,50)
	hunter.stunned = 0.0
	hunter._physics_process(.016)
	assert(hunter.state == hunter.State.CHASE and hunter.velocity.z < 0.0)
	hunter.take_damage(1000.0)
	assert(world.hunter_nodes.size() == 4)
	director._physics_process(.016)
	assert(world.hunter_nodes.size() == 5,"director must replace dead hunters")
	world.queue_free()
	await get_tree().create_timer(1.0).timeout
	print("HUNTER RULES PASS: reverse movement, five independent hunters, global chase, charge/rest/audio, forward collision-safe recycle, health and replacement")
	get_tree().quit()
