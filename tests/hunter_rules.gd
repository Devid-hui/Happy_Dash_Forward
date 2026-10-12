extends Node
const World := preload("res://scripts/world/world.gd")

func _ready() -> void:
	call_deferred("run_checks")

func run_checks() -> void:
	seed(721)
	get_tree().root.size = Vector2i(640,360)
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
	check_model_visibility(player,hunter,director)
	hunter.global_position = Vector3(-90,0,0)
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
	assert(director.ambush_cooldown == 8.0,"a successful recycle batch must start the full eight-second interval")
	for npc in world.hunter_nodes:
		npc.global_position = Vector3(-45,0,world.hunter_nodes.find(npc)*4.0)
		director.recycle_cooldowns[npc.get_instance_id()] = 0.0
	for i in range(15):
		director.scan_timer = 0.0
		director._physics_process(.5)
		for npc in world.hunter_nodes:
			assert(npc.global_position.x < 0.0,"recycling must remain blocked throughout the eight-second batch interval")
	director.scan_timer = 0.0
	director._physics_process(.5)
	assert(world.hunter_nodes.filter(func(npc): return npc.global_position.x > 0.0).size() == 3,"recycling must resume with the three-hunter cap once the interval expires")
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
	var dead_id: int = hunter.get_instance_id()
	hunter.take_damage(1000.0)
	assert(world.hunter_nodes.size() == 4)
	assert(not director.recycle_cooldowns.has(dead_id) and not director.initial_directions.has(dead_id),"normal death must clear director dictionaries")
	director._physics_process(.016)
	assert(world.hunter_nodes.size() == 5,"director must replace dead hunters")
	var replacement = director.pending_initial[0]
	var replacement_id: int = replacement.get_instance_id()
	var survivors := world.hunter_nodes.filter(func(npc): return npc != replacement)
	var survivor_health: Array[float] = []
	var survivor_positions: Array[Vector3] = []
	for npc in survivors:
		survivor_health.append(npc.health)
		survivor_positions.append(npc.global_position)
	replacement.take_damage(1000.0)
	assert(not director.pending_initial.has(replacement),"death while waiting for replacement placement must clear the queue")
	assert(not director.recycle_cooldowns.has(replacement_id) and not director.initial_directions.has(replacement_id))
	for i in range(survivors.size()):
		assert(world.hunter_nodes.has(survivors[i]) and survivors[i].health == survivor_health[i] and survivors[i].global_position == survivor_positions[i],"death must leave surviving hunters unchanged")
	await get_tree().physics_frame
	director._physics_process(.016)
	for i in range(4):
		await get_tree().physics_frame
		director._physics_process(.016)
	assert(world.hunter_nodes.size() == 5 and director.pending_initial.is_empty(),"replacement must complete positioning after queued frees")
	for npc in world.hunter_nodes:
		assert(is_instance_valid(npc),"replacement registry cannot retain freed objects")
	world.queue_free()
	await get_tree().process_frame
	await check_initial_death()
	# 等待音频混音线程处理停止事件，避免把过早退出误报为资源泄漏。
	await get_tree().create_timer(1.0).timeout
	print("HUNTER RULES PASS: reverse movement, five independent hunters, global chase, charge/rest/audio, forward collision-safe recycle, model-frustum edges, health and positioned replacement")
	get_tree().quit()

func check_model_visibility(player: CharacterBody3D, hunter: CharacterBody3D, director: Node) -> void:
	var camera: Camera3D = player.camera
	camera.fov = 75.0
	camera.look_at_from_position(Vector3(0,1.5,0),Vector3(0,1.5,-5))
	hunter.global_position = Vector3(41.43,0,-30)
	hunter.look_at(Vector3(0,0,0),Vector3.UP)
	var missed_vertex := Vector3(40.76921,.218,-30.43514)
	var closest_vertex_distance := INF
	for vertex in model_world_vertices(hunter):
		closest_vertex_distance = minf(closest_vertex_distance,vertex.distance_to(missed_vertex))
	assert(closest_vertex_distance < .001,"the regression point must belong to the actual generated hunter mesh")
	assert(camera.is_position_in_frustum(missed_vertex),"the original right-foot regression point must really enter the 640x360 frustum")
	var old_sampling_visible := false
	for height in [.2,1.35,2.65]:
		for side in [-.5,0.0,.5]:
			old_sampling_visible = old_sampling_visible or camera.is_position_in_frustum(hunter.global_position+Vector3(side,height,0))
	assert(not old_sampling_visible,"the original point regression must exercise a gap in the old body sampling")
	assert(director.is_in_view(hunter),"visible model feet must protect the hunter from teleporting")
	var watched_positions: Array[Vector3] = []
	for npc in director.hunters:
		watched_positions.append(npc.global_position)
		director.recycle_cooldowns[npc.get_instance_id()] = 0.0
	director.scan_timer = 0.0
	director.ambush_cooldown = 0.0
	director._physics_process(.5)
	for i in range(director.hunters.size()):
		assert(director.hunters[i].global_position == watched_positions[i],"a visible model extremity must protect the entire actual recycle scan")
	# 用真实网格顶点放置画面四边；不同朝向会改变手、脚和头的投影边界。
	for angle in [0.0,45.0,90.0,180.0]:
		hunter.rotation_degrees = Vector3(0,angle,0)
		hunter.global_position = Vector3(0,0,-30)
		var vertices := model_world_vertices(hunter)
		assert(not vertices.is_empty())
		for edge in range(4):
			var extremity: Vector3 = vertices[0]
			for vertex in vertices:
				if (edge == 0 and vertex.x > extremity.x) or (edge == 1 and vertex.x < extremity.x) or (edge == 2 and vertex.y < extremity.y) or (edge == 3 and vertex.y > extremity.y):
					extremity = vertex
			var pixel: Vector2 = [Vector2(1,180),Vector2(639,180),Vector2(320,1),Vector2(320,359)][edge]
			var anchor := camera.project_position(pixel,30.0)
			var local_extremity := extremity-hunter.global_position
			hunter.global_position = anchor-local_extremity
			assert(camera.is_position_in_frustum(anchor),"edge fixture must include a real visible model vertex")
			assert(director.is_in_view(hunter),"all model rotations and left/right/head/foot edges must be protected")
			hunter.global_position = Vector3(0,0,-30)
	hunter.global_position = Vector3(90,0,-30)
	assert(not director.is_in_view(hunter),"a model entirely outside the frustum must remain recyclable")
	hunter.global_position = Vector3(0,0,-camera.near)
	assert(director.is_in_view(hunter),"a model intersecting the near plane must be protected")
	hunter.global_position = Vector3(0,0,0)
	assert(director.is_in_view(hunter),"camera inside model bounds must be protected")
	var unknown := Node3D.new()
	get_parent().add_child(unknown)
	assert(director.is_in_view(unknown),"unknown model bounds must conservatively block teleporting")
	unknown.queue_free()

func model_world_vertices(hunter: Node3D) -> Array[Vector3]:
	var vertices: Array[Vector3] = []
	for part in hunter.get_node("VisualRoot").find_children("*","MeshInstance3D",true,false):
		for surface in range(part.mesh.get_surface_count()):
			for vertex in part.mesh.surface_get_arrays(surface)[Mesh.ARRAY_VERTEX]:
				vertices.append(part.global_transform*vertex)
	return vertices

func check_initial_death() -> void:
	GameState.game_over = false
	var world := World.new()
	add_child(world)
	var director = world.hunter_director
	director.set_physics_process(false)
	world.player.set_physics_process(false)
	var victim = world.hunter_nodes[0]
	var id: int = victim.get_instance_id()
	assert(director.pending_initial.has(victim) and director.initial_directions.has(id))
	director.recycle_cooldowns[id] = 6.0
	victim.take_damage(1000.0)
	assert(world.hunter_nodes.size() == 4)
	assert(not director.pending_initial.has(victim),"death before first positioning must clear waiting instances")
	assert(not director.initial_directions.has(id) and not director.recycle_cooldowns.has(id),"death must clear every waiting ID")
	await get_tree().physics_frame
	assert(not is_instance_valid(victim),"test must cross the actual queued-free boundary")
	for i in range(5):
		director._physics_process(.016)
		await get_tree().physics_frame
	assert(world.hunter_nodes.size() == 5 and director.pending_initial.is_empty(),"initial death must recover five fully positioned hunters")
	assert(director.initial_directions.is_empty(),"completed initial placement must release direction entries")
	for npc in world.hunter_nodes:
		assert(is_instance_valid(npc) and npc.is_physics_processing(),"all replacements must be alive and enabled after positioning")
		assert(npc.global_position.distance_to(world.player.global_position) >= 15.0,"replacement cannot remain at an unvalidated nearby location")
	world.queue_free()
	await get_tree().process_frame
