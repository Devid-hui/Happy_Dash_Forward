extends Node
# 世界负责装配；导演只管理数量和空间刷新，不负责敌人的追逐、模型或血量。
const Hunter := preload("res://scripts/enemies/hunter.gd")
const Stats := preload("res://scripts/enemies/hunter_stats.gd")
@export var population: int = 5
@export var archetype: Resource = preload("res://resources/enemies/nailong_default.tres")
var world: Node3D
var player: CharacterBody3D
var hunters: Array[Node]
var last_motion := Vector3.FORWARD
var recycle_cooldowns: Dictionary = {}
var pending_initial: Array[CharacterBody3D] = []
var scan_timer := 0.0
var initial_directions: Dictionary = {}
var ambush_cooldown := 0.0
@export var max_ambush_count := 3
@export var ambush_interval := 8.0

func setup(game_world: Node3D, tracked_player: CharacterBody3D, registry: Array[Node]) -> void:
	world = game_world; player = tracked_player; hunters = registry
	for i in range(population):
		var hunter := _create_hunter(i)
		# 等到物理帧检查位置后才允许移动，避免新建碰撞尚未同步。
		hunter.set_physics_process(false)
		pending_initial.append(hunter)
		var angle := TAU*i/population + randf_range(-.15,.15)
		initial_directions[hunter.get_instance_id()] = Vector3(cos(angle),0,sin(angle))

func _create_hunter(index: int) -> CharacterBody3D:
	var hunter := Hunter.new()
	hunter.stats = archetype
	hunter.name = "Nailong_%02d" % (index+1)
	hunter.target = player
	hunter.fields = world.fields
	var angle := TAU*index/population
	hunter.position = player.position+Vector3(cos(angle)*30.0,0,sin(angle)*30.0)
	hunter.trace_requested.connect(world.damage_hunter_trace)
	hunter.charge_warned.connect(_on_warning)
	hunter.died.connect(_on_death)
	world.add_child(hunter)
	hunters.append(hunter)
	var breathing: AudioStreamPlayer3D = world.make_hunter_audio()
	hunter.add_child(breathing); breathing.play()
	return hunter

func _on_warning(_hunter: CharacterBody3D) -> void:
	world.notice("尖叫逼近：奶龙即将冲刺！")

func _on_death(hunter: CharacterBody3D) -> void:
	var id := hunter.get_instance_id()
	hunters.erase(hunter)
	pending_initial.erase(hunter)
	recycle_cooldowns.erase(id)
	initial_directions.erase(id)
	# 死亡以后也保持目标数量，但补位发生在物理帧。

func candidate_is_clear(hunter: CharacterBody3D, candidate: Vector3) -> bool:
	if absf(candidate.x) > 97.0 or absf(candidate.z) > 97.0: return false
	if candidate.distance_to(player.global_position) < hunter.stats.spawn_min_distance: return false
	for other in hunters:
		if other != hunter and is_instance_valid(other) and candidate.distance_to(other.global_position) < 3.0: return false
	var shape := CapsuleShape3D.new()
	shape.radius = .7; shape.height = 2.8
	var query := PhysicsShapeQueryParameters3D.new()
	query.shape = shape
	query.transform = Transform3D(Basis.IDENTITY,candidate+Vector3(0,1.45,0))
	query.exclude = [hunter.get_rid()]
	query.collision_mask = 1
	return player.get_world_3d().direct_space_state.intersect_shape(query,1).is_empty()

func relocate(hunter: CharacterBody3D, forward: Vector3, initial := false) -> bool:
	var direction := Vector3(forward.x,0,forward.z).normalized()
	if direction.length_squared() < .01: direction = -player.global_basis.z
	for attempt in range(40):
		# 前方 ±55° 扇区，不把玩家视线方向误当成运动方向。
		var candidate := player.global_position+direction.rotated(Vector3.UP,randf_range(-.25,.25) if initial else randf_range(-.96,.96))*randf_range(hunter.stats.spawn_min_distance,hunter.stats.spawn_max_distance)
		candidate.y = 0.0
		if not candidate_is_clear(hunter,candidate): continue
		hunter.global_position = candidate
		hunter.reset_after_relocation()
		recycle_cooldowns[hunter.get_instance_id()] = 6.0
		return true
	# 没有合法点就下一次重试，不能强行生成到碰撞体中。
	return false

func _physics_process(delta: float) -> void:
	if not is_instance_valid(player): return
	var motion := Vector3(player.velocity.x,0,player.velocity.z)
	if motion.length_squared() > .09: last_motion = motion.normalized()
	elif last_motion.length_squared() < .01: last_motion = -player.global_basis.z
	for id in recycle_cooldowns.keys():
		recycle_cooldowns[id] = maxf(0.0,recycle_cooldowns[id]-delta)
	for hunter in pending_initial.duplicate():
		if not is_instance_valid(hunter):
			pending_initial.erase(hunter)
			continue
		if relocate(hunter,initial_directions.get(hunter.get_instance_id(),last_motion),initial_directions.has(hunter.get_instance_id())):
			hunter.set_physics_process(true)
			pending_initial.erase(hunter)
			initial_directions.erase(hunter.get_instance_id())
	while hunters.size() < population:
		var hunter := _create_hunter(hunters.size())
		hunter.set_physics_process(false)
		pending_initial.append(hunter)
	scan_timer -= delta
	if scan_timer > 0.0: return
	scan_timer = .5
	ambush_cooldown = maxf(0.0,ambush_cooldown-.5)
	if ambush_cooldown > 0.0 or not player.is_sprinting or motion.length() < 5.5: return
	# 当前视野里有奶龙时不传送，避免眼前的敌人突然消失。
	for hunter in hunters:
		if is_instance_valid(hunter) and is_in_view(hunter): return
	var candidates: Array[Node] = []
	for hunter in hunters:
		if not is_instance_valid(hunter) or pending_initial.has(hunter): continue
		var offset: Vector3 = hunter.global_position-player.global_position
		offset.y = 0.0
		if offset.length() >= hunter.stats.recycle_distance and offset.normalized().dot(last_motion) < -.25 and recycle_cooldowns.get(hunter.get_instance_id(),0.0) <= 0.0:
			candidates.append(hunter)
	candidates.shuffle()
	var moved := 0
	for hunter in candidates:
		if relocate(hunter,last_motion): moved += 1
		if moved >= max_ambush_count: break
	if moved > 0: ambush_cooldown = ambush_interval

func is_in_view(hunter: Node3D) -> bool:
	if not is_instance_valid(hunter) or not is_instance_valid(player) or not is_instance_valid(player.camera): return true
	var camera: Camera3D = player.camera
	if not camera.is_inside_tree(): return true
	var visual := hunter.get_node_or_null("VisualRoot")
	if visual == null: return true
	var bounds := AABB()
	var has_bounds := false
	for node in visual.find_children("*","MeshInstance3D",true,false):
		var part := node as MeshInstance3D
		if part.mesh == null: continue
		var part_bounds := part.global_transform * part.get_aabb()
		if not part_bounds.is_finite(): return true
		bounds = bounds.merge(part_bounds) if has_bounds else part_bounds
		has_bounds = true
	if not has_bounds: return true
	# 只有某个裁剪平面能排除整个模型时才允许传送，边缘接触也保护。
	for plane in camera.get_frustum():
		var outside := true
		for corner in range(8):
			if plane.distance_to(bounds.get_endpoint(corner)) <= .001:
				outside = false
				break
		if outside: return false
	return true
