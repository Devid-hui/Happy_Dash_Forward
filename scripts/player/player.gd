extends CharacterBody3D

var walk_speed := 5.0
var run_speed := 7.5
var backward_speed := 2.5
var stamina := 100.0
var health := 3
var look_sensitivity := 0.0018
var world
var pitch := 0.0
var cooldowns: Dictionary = {}
var echo_deafness := 0.0
var dehydration := 0.0
var filter_time := 0.0
var afterimage_ready := false
var afterimage_time := 0.0
var afterimage_window := 0.0
var in_mire := false
var in_salt := false
var camera: Camera3D
var hits := 0
var skill_manager
var step_timer := 0.0
var is_sprinting := false

func _ready() -> void:
	add_to_group("player")
	var capsule := CapsuleShape3D.new(); capsule.radius = 0.35; capsule.height = 1.7
	var collider := CollisionShape3D.new(); collider.shape = capsule; collider.position.y = 0.85; add_child(collider)
	camera = Camera3D.new(); camera.position.y = 1.5; camera.current = true; add_child(camera)
	# 游戏可读性补光：在低处照亮脚边地面，短范围衰减保留远处黑暗。
	var light := OmniLight3D.new()
	light.name = "RainScatteredNearLight"
	light.position = Vector3(0,.85,-.25)
	light.light_color = Color(.55,.62,.68)
	light.light_energy = 18.0 * GameState.brightness
	light.omni_range = 4.5
	light.omni_attenuation = 1.2
	light.light_volumetric_fog_energy = 0.0
	light.shadow_enabled = true
	add_child(light)
	skill_manager = preload("res://scripts/skills/skill_manager.gd").new(); add_child(skill_manager); skill_manager.setup(self, world)

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		rotate_y(-event.relative.x * look_sensitivity)
		pitch = clampf(pitch - event.relative.y * look_sensitivity, -1.35, 1.35)
		camera.rotation.x = pitch
	if event.is_action_pressed("interact"): world.interact()
	if event.is_action_pressed("skill_1"): use_slot(0)
	if event.is_action_pressed("skill_2"): use_slot(1)
	if event.is_action_pressed("skill_3"): use_slot(2)
	if event is InputEventKey and event.pressed and event.keycode == KEY_F: world.cycle_filter()

func _physics_process(delta: float) -> void:
	skill_manager.tick(delta)
	echo_deafness = maxf(0.0, echo_deafness - delta)
	afterimage_time = maxf(0.0, afterimage_time - delta)
	afterimage_window = maxf(0.0, afterimage_window - delta)
	if afterimage_window <= 0.0: afterimage_ready = false
	dehydration = maxf(0.0, dehydration - delta * 0.5)
	var was_filtering := filter_time > 0.0
	filter_time = maxf(0.0, filter_time - delta)
	if was_filtering and filter_time <= 0.0: world.set_filtering(false)
	var input := Input.get_vector("move_left", "move_right", "move_forward", "move_back")
	var movement := movement_settings(input, Input.is_action_pressed("sprint"))
	var running: bool = movement.running
	is_sprinting = running
	var direction := (transform.basis * Vector3(input.x, 0, input.y)).normalized()
	var speed: float = movement.speed
	if in_mire and speed < 5.8: speed *= 0.42
	if is_on_floor(): velocity.y = 0.0
	else: velocity.y -= 18.0 * delta
	velocity.x = move_toward(velocity.x, direction.x * speed, 20.0 * delta)
	velocity.z = move_toward(velocity.z, direction.z * speed, 20.0 * delta)
	if input.y > .01:
		var horizontal := Vector2(velocity.x,velocity.z).limit_length(speed)
		velocity.x = horizontal.x; velocity.z = horizontal.y
	if running: stamina = maxf(0.0, stamina - 25.0 * delta)
	else: stamina = minf(100.0, stamina + (7.0 if dehydration > 0 else 17.0) * delta)
	step_timer -= delta
	if input.length() > 0.1 and is_on_floor() and step_timer <= 0.0:
		world.play_footstep(global_position, running)
		step_timer = 0.3 if running else 0.5
	move_and_slide()
	if global_position.y < -5.0 and world:
		world.finish(false)
	if world: world.update_hud()

func movement_settings(input: Vector2, sprint_pressed: bool) -> Dictionary:
	# 只要输入含后退分量（包括斜后退），整个方向限速且不能奔跑。
	var backward := input.y > .01
	var running := sprint_pressed and not backward and stamina > 0.0 and input.length() > .1
	return {"running": running, "speed": backward_speed if backward else (run_speed if running else walk_speed)}

func use_slot(slot: int) -> void:
	skill_manager.cast_slot(slot)

func take_hit() -> void:
	hits += 1
	stamina = maxf(0.0, stamina - 20.0)
	if hits >= 2: world.finish(false)
	else: world.notice("奶龙撞击了你！再一次就会被捕获。")
