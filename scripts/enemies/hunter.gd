extends CharacterBody3D
signal charge_warned(hunter)
signal trace_requested(position: Vector3)
signal health_changed(current: float, maximum: float)
signal died(hunter)
const Stats := preload("res://scripts/enemies/hunter_stats.gd")
const Visual := preload("res://scripts/enemies/hunter_visual.gd")
const Voice := preload("res://scripts/enemies/hunter_voice.gd")
enum State { WANDER, INVESTIGATE, CHASE, SEARCH }
enum ChargePhase { NORMAL, WARNING, CHARGING, RESTING }
@export var stats: Resource
var state := State.CHASE
var charge_phase := ChargePhase.NORMAL
var phase_remaining := 0.0
var health := 100.0
var target: CharacterBody3D
var stunned := 0.0
var slow_timer := 0.0
var attack_cooldown := 0.0
var trace_timer := 0.0
var voice: AudioStreamPlayer3D
var movement_direction := Vector3.FORWARD
var avoidance_side := 1.0
var fields: Array[Dictionary] = []
var knockback := Vector3.ZERO
var visual_root: Node3D
# 兼容旧调试预览；正式实例直接创建独立表现组件。
func _build_model(root: Node3D) -> void:
	var builder := Visual.new()
	builder._build_model(root)
	builder.free()

func _ready() -> void:
	stats = Stats.new() if stats == null else stats.duplicate(true)
	health = stats.max_health
	add_to_group("hunters")
	var capsule := CapsuleShape3D.new()
	capsule.radius = .55; capsule.height = 2.7
	var collision := CollisionShape3D.new()
	collision.shape = capsule; collision.position.y = 1.35
	add_child(collision)
	visual_root = Visual.new()
	visual_root.name = "VisualRoot"
	add_child(visual_root)
	voice = Voice.new()
	add_child(voice)

func take_damage(amount: float) -> void:
	if amount <= 0.0 or health <= 0.0: return
	health = maxf(0.0,health-amount)
	health_changed.emit(health,stats.max_health)
	if health == 0.0:
		died.emit(self)
		queue_free()

func reset_after_relocation() -> void:
	velocity = Vector3.ZERO
	knockback = Vector3.ZERO
	charge_phase = ChargePhase.RESTING
	phase_remaining = stats.charge_rest_duration
	attack_cooldown = 1.0
	voice.stop()

func repel(direction: Vector3, impulse: float, interruption: float = .35) -> void:
	if health <= 0.0 or impulse <= 0.0: return
	var horizontal := Vector3(direction.x,0,direction.z)
	if horizontal.length_squared() < .001: return
	knockback = horizontal.normalized()*minf(18.0,impulse)
	stunned = maxf(stunned,interruption)
	if charge_phase in [ChargePhase.WARNING,ChargePhase.CHARGING]:
		charge_phase = ChargePhase.RESTING
		phase_remaining = stats.charge_rest_duration
	voice.stop()

func tick_charge(delta: float, distance: float, can_charge: bool) -> void:
	# 只在普通状态进入警告；冲刺结束必须完整休息，近距离不会重置计时。
	if charge_phase == ChargePhase.NORMAL:
		if can_charge and distance <= stats.charge_trigger_distance:
			charge_phase = ChargePhase.WARNING
			phase_remaining = stats.charge_warning_duration
			voice.play()
			charge_warned.emit(self)
		return
	phase_remaining = maxf(0.0,phase_remaining-delta)
	if phase_remaining > 0.0: return
	match charge_phase:
		ChargePhase.WARNING:
			charge_phase = ChargePhase.CHARGING if can_charge else ChargePhase.RESTING
			phase_remaining = stats.charge_duration if can_charge else stats.charge_rest_duration
		ChargePhase.CHARGING:
			charge_phase = ChargePhase.RESTING
			phase_remaining = stats.charge_rest_duration
		ChargePhase.RESTING:
			charge_phase = ChargePhase.NORMAL

func current_speed() -> float:
	var speed: float = stats.charge_speed if charge_phase == ChargePhase.CHARGING else stats.move_speed
	return speed * (.42 if slow_timer > 0.0 else 1.0)

func _steer(direction: Vector3) -> Vector3:
	# 近距碰撞预判，绕开树干；不依赖世界对象或玩家的输入实现。
	var origin := global_position + Vector3.UP
	var exclusions: Array[RID] = [get_rid(),target.get_rid()]
	var query := PhysicsRayQueryParameters3D.create(origin,origin+direction*2.4,collision_mask,exclusions)
	var hit := get_world_3d().direct_space_state.intersect_ray(query)
	if hit.is_empty(): return direction
	var tangent := direction.rotated(Vector3.UP,avoidance_side*PI*.45)
	query.to = origin+tangent*2.0
	if not get_world_3d().direct_space_state.intersect_ray(query).is_empty():
		avoidance_side *= -1.0
		tangent = direction.rotated(Vector3.UP,avoidance_side*PI*.45)
	return tangent

func _physics_process(delta: float) -> void:
	attack_cooldown = maxf(0.0,attack_cooldown-delta)
	slow_timer = maxf(0.0,slow_timer-delta)
	if not is_instance_valid(target):
		target = get_tree().get_first_node_in_group("player") as CharacterBody3D
	if not is_instance_valid(target): return
	state = State.CHASE
	var offset := target.global_position-global_position
	offset.y = 0.0
	var distance := offset.length()
	var in_mire := false
	for field in fields:
		if is_instance_valid(field.node) and field.kind == "mire" and global_position.distance_to(field.node.global_position) < field.radius:
			in_mire = true
	tick_charge(delta,distance,stunned <= 0.0 and not in_mire and slow_timer <= 0.0)
	if stunned > 0.0 or knockback.length_squared() > .01:
		stunned = maxf(0.0,stunned-delta)
		if charge_phase == ChargePhase.CHARGING:
			charge_phase = ChargePhase.RESTING; phase_remaining = stats.charge_rest_duration
		velocity.x = knockback.x; velocity.z = knockback.z
		knockback = knockback.move_toward(Vector3.ZERO,18.0*delta)
	else:
		var direction := _steer(offset.normalized()) if distance > .3 else Vector3.ZERO
		var speed := current_speed() * (.42 if in_mire else 1.0)
		velocity.x = direction.x*speed; velocity.z = direction.z*speed
		if direction.length_squared() > .01: look_at(global_position+direction,Vector3.UP)
	if not is_on_floor(): velocity.y -= 18.0*delta
	else: velocity.y = 0.0
	move_and_slide()
	if visual_root.has_method("tick_pose"):
		visual_root.tick_pose(delta,Vector3(velocity.x,0,velocity.z),charge_phase,stunned>0.0 or knockback.length_squared()>.01)
	trace_timer += delta
	if trace_timer >= 3.0:
		trace_timer = 0.0; trace_requested.emit(global_position)
	if stunned <= 0.0 and global_position.distance_to(target.global_position) < stats.attack_range and attack_cooldown <= 0.0:
		attack_cooldown = stats.attack_interval
		if target.has_method("take_hit"): target.take_hit()

func hear_noise(_position: Vector3) -> void:
	# 全图锁定规则优先；声音技能继续生效于痕迹系统，不覆盖追踪目标。
	state = State.CHASE

func _exit_tree() -> void:
	for child in get_children():
		if child is AudioStreamPlayer3D:
			child.stop()
			child.stream = null
