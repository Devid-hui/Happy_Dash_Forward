extends CharacterBody3D

const FIELD_EQUIPMENT := preload("res://scripts/player/field_equipment.gd")

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
var energy := 100.0
var noise := 0.0
var lamp_enabled := true
var pulse_mode := false
var daylight_time := 0.0
var blind_time := 0.0
var disturbance_time := 0.0
var equipment: Node3D
var lamp_light: SpotLight3D
var release_light: OmniLight3D
var sensor_overlay: ColorRect
var sensor_material: ShaderMaterial
var fire_cooldown := 0.0
var recovery_delay := 0.0
var noise_recovery_delay := 0.0
var gameplay_time := 0.0
var _scream_latched := false
var _pending_fire := false

func energy_capacity() -> float:
	return 100.0

func _ready() -> void:
	add_to_group("player")
	var capsule := CapsuleShape3D.new(); capsule.radius = 0.35; capsule.height = 1.7
	var collider := CollisionShape3D.new(); collider.shape = capsule; collider.position.y = 0.85; add_child(collider)
	camera = Camera3D.new(); camera.position.y = 1.5; camera.current = true; add_child(camera)
	# Passive near fill only makes nearby silhouettes readable. Usable detail
	# illumination comes from the independently controlled, energy-consuming lamp.
	var light := OmniLight3D.new()
	light.name = "RainScatteredNearLight"
	light.position = Vector3(0,.85,-.25)
	light.light_color = Color(.55,.62,.68)
	light.light_energy = 1.6 * GameState.brightness
	light.omni_range = 4.5
	light.omni_attenuation = 1.2
	light.light_volumetric_fog_energy = 0.0
	light.shadow_enabled = false
	add_child(light)
	equipment = FIELD_EQUIPMENT.new()
	camera.add_child(equipment)
	equipment.setup(self)
	lamp_light = SpotLight3D.new()
	lamp_light.name = "SpectrumBeam"
	lamp_light.light_color = Color(.88,.94,.83)
	lamp_light.light_energy = 5.2 * GameState.brightness
	lamp_light.spot_angle = 27.0
	lamp_light.spot_attenuation = 1.45
	lamp_light.shadow_enabled = true
	equipment.beam_socket.add_child(lamp_light)
	release_light = OmniLight3D.new()
	release_light.name = "SpectrumRelease"
	release_light.light_color = Color(.64,.88,.83)
	release_light.omni_range = 8.0
	release_light.shadow_enabled = false
	camera.add_child(release_light)
	_build_sensor_overlay()
	skill_manager = preload("res://scripts/skills/skill_manager.gd").new(); add_child(skill_manager); skill_manager.setup(self, world)

func _unhandled_input(event: InputEvent) -> void:
	if world == null or world.is_gameplay_blocked(): return
	if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		rotate_y(-event.relative.x * look_sensitivity)
		pitch = clampf(pitch - event.relative.y * look_sensitivity, -1.35, 1.35)
		camera.rotation.x = pitch
	if event.is_action_pressed("interact"): world.interact()
	if event.is_action_pressed("skill_1"): use_slot(0)
	if event.is_action_pressed("skill_2"): use_slot(1)
	if event.is_action_pressed("skill_3"): use_slot(2)
	if event.is_action_pressed("lamp_toggle"): toggle_lamp()
	# Space queries execute in the physics step, after input has been collected.
	if event.is_action_pressed("lamp_fire"): _pending_fire = true
	if event is InputEventKey and event.pressed and event.keycode == KEY_F: world.cycle_filter()

func _physics_process(delta: float) -> void:
	if world == null or world.is_gameplay_blocked():
		clear_gameplay_actions()
		return
	if _pending_fire:
		_pending_fire = false
		fire_lamp()
	gameplay_time += delta
	_tick_energy(delta)
	skill_manager.tick(delta)
	echo_deafness = maxf(0.0, echo_deafness - delta)
	afterimage_time = maxf(0.0, afterimage_time - delta)
	afterimage_window = maxf(0.0, afterimage_window - delta)
	if afterimage_window <= 0.0: afterimage_ready = false
	dehydration = maxf(0.0, dehydration - delta)
	var was_filtering := filter_time > 0.0
	filter_time = maxf(0.0, filter_time - delta)
	if was_filtering and filter_time <= 0.0: world.set_filtering(false)
	var input := Input.get_vector("move_left", "move_right", "move_forward", "move_back")
	var movement := movement_settings(input, Input.is_action_pressed("sprint"))
	var running: bool = movement.running
	is_sprinting = running
	var direction := (transform.basis * Vector3(input.x, 0, input.y)).normalized()
	var speed: float = movement.speed
	if daylight_time > 0.0:
		speed *= float(GameState.ability_values("daylight").boost_multiplier)
	if disturbance_time > 0.0 and input.length() > .1:
		direction = (direction + global_basis.x * sin(gameplay_time * 22.0) * .08).normalized()
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
	_update_sensory_feedback(delta, input)
	if global_position.y < -5.0 and world:
		world.finish(false)
	if world: world.update_hud()

func clear_gameplay_actions() -> void:
	_pending_fire = false

func _tick_energy(delta: float) -> void:
	fire_cooldown = maxf(0.0,fire_cooldown-delta)
	recovery_delay = maxf(0.0,recovery_delay-delta)
	noise_recovery_delay = maxf(0.0,noise_recovery_delay-delta)
	daylight_time = maxf(0.0,daylight_time-delta)
	blind_time = maxf(0.0,blind_time-delta)
	disturbance_time = maxf(0.0,disturbance_time-delta)
	if lamp_enabled:
		energy = maxf(0.0,energy-1.4*delta)
		if energy <= 0.0:
			lamp_enabled = false
			world.notice("谱灯储能耗尽。暗处仍可辨近处轮廓；关闭照明可缓慢回充。")
	elif recovery_delay <= 0.0 and daylight_time <= 0.0:
		energy = minf(energy_capacity(),energy+1.3*delta)
	if noise_recovery_delay <= 0.0:
		noise = maxf(0.0,noise-4.0*delta)
	if noise < 50.0: _scream_latched = false

func toggle_lamp() -> bool:
	if world == null or world.is_gameplay_blocked(): return false
	if not lamp_enabled and energy <= 1.0:
		world.notice("电量尚不足以照明。关闭照明后会缓慢回充。")
		return false
	lamp_enabled = not lamp_enabled
	play_equipment_action("light")
	return true

func toggle_pulse_mode() -> void:
	if not GameState.equipped.has("pulse") or world.is_gameplay_blocked(): return
	pulse_mode = not pulse_mode
	world.notice("乱频：点射模式，每次耗电并积累噪声。" if pulse_mode else "谱灯：集中爆发模式，释放当前全部储能。")

func activate_daylight() -> bool:
	if world == null or world.is_gameplay_blocked() or not GameState.equipped.has("daylight"): return false
	if daylight_time > 0.0 or energy < 25.0:
		world.notice("蓄昼需要25电量，并且当前不能已经处于加速中。")
		return false
	energy -= 25.0
	daylight_time = float(GameState.ability_values("daylight").boost_duration)
	disturbance_time = maxf(disturbance_time,1.35)
	recovery_delay = 1.0
	world.play_daylight_sound()
	world.notice("蓄昼将共享储能用于短时加速，保持方向并留意步态偏移。")
	return true

func capture_lightning() -> float:
	if world == null or world.is_gameplay_blocked() or not GameState.equipped.has("daylight"): return 0.0
	var before := energy
	energy = minf(energy_capacity(),energy+float(GameState.ability_values("daylight").capture_energy))
	play_equipment_action("capture")
	GameState.record_knowledge("daylight")
	return energy-before

func fire_lamp() -> bool:
	if world == null or world.is_gameplay_blocked() or fire_cooldown > 0.0: return false
	if pulse_mode:
		if not GameState.equipped.has("pulse"): return false
		var values := GameState.ability_values("pulse")
		var cost: float = values.shot_energy
		if energy < cost:
			world.notice("点射电量不足；关闭照明可以缓慢回充。")
			return false
		energy -= cost
		noise = minf(100.0,noise+float(values.noise_gain))
		noise_recovery_delay = 1.2
		fire_cooldown = float(values.shot_interval)
		recovery_delay = 1.0
		if noise >= 60.0: disturbance_time = maxf(disturbance_time,1.1)
		if noise >= 85.0 and not _scream_latched:
			_scream_latched = true
			disturbance_time = maxf(disturbance_time,2.2)
			world.play_disorientation_sound()
		world.release_spectrum(true,values,1.0)
		play_equipment_action("shot")
		GameState.record_knowledge("pulse")
	else:
		if energy < 12.0:
			world.notice("集中爆发至少需要12电量；关闭照明后可以缓慢回充。")
			return false
		var strength := energy/energy_capacity()
		var values := GameState.ability_values("lamp")
		energy = 0.0
		lamp_enabled = false
		blind_time = float(values.blind_duration)
		fire_cooldown = .65
		recovery_delay = 1.0
		world.release_spectrum(false,values,strength)
		play_equipment_action("flash")
		GameState.record_knowledge("lamp")
	return true

func play_equipment_action(kind: String) -> void:
	if not is_instance_valid(equipment): return
	if kind == "mode": equipment.set_mode(pulse_mode)
	else: equipment.trigger(kind)

func _build_sensor_overlay() -> void:
	var layer := CanvasLayer.new()
	layer.layer = 4
	add_child(layer)
	sensor_overlay = ColorRect.new()
	sensor_overlay.name = "SensoryFeedback"
	sensor_overlay.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	sensor_overlay.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var shader := Shader.new()
	shader.code = """shader_type canvas_item;
uniform sampler2D scene_image : hint_screen_texture, filter_linear_mipmap;
uniform float flash_amount = 0.0;
uniform float disorder = 0.0;
uniform float phase = 0.0;
void fragment(){
 vec2 uv=SCREEN_UV;uv.x+=sin(uv.y*24.0+phase*11.0)*.0008*disorder;
 vec3 image=textureLod(scene_image,uv,flash_amount*2.0).rgb;
 image=mix(image,vec3(.81,.90,.87),flash_amount*.30);
 float shade=pow(length(SCREEN_UV-.5)*1.15,2.0)*.12*disorder;
 COLOR=vec4(image-shade,1.0);
}
"""
	sensor_material = ShaderMaterial.new()
	sensor_material.shader = shader
	sensor_overlay.material = sensor_material
	layer.add_child(sensor_overlay)
	sensor_overlay.visible = false

func _update_sensory_feedback(delta: float, input: Vector2) -> void:
	var values := GameState.ability_values("lamp")
	lamp_light.visible = lamp_enabled and energy > 0.0
	lamp_light.spot_range = float(values.range)
	equipment.set_level(GameState.ability_level("lamp"))
	equipment.tick(delta,input,is_sprinting,daylight_time>0.0,noise)
	var action: String = equipment.current_action
	var envelope := sin(PI*equipment.action_time/maxf(.001,equipment.action_duration)) if action in ["flash","shot"] else 0.0
	release_light.light_energy = envelope*(6.0 if action=="flash" else 1.8)*(0.25 if GameState.reduced_flashes else 1.0)
	var flash := clampf(blind_time/maxf(.01,float(values.blind_duration)),0.0,1.0)
	var disorder := clampf(disturbance_time/2.2,0.0,1.0)
	var visual_scale := .18 if GameState.reduced_flashes else 1.0
	sensor_overlay.visible = flash > .01 or disorder > .01
	sensor_material.set_shader_parameter("flash_amount",flash*visual_scale)
	sensor_material.set_shader_parameter("disorder",disorder*visual_scale)
	sensor_material.set_shader_parameter("phase",gameplay_time)
	camera.rotation = Vector3(pitch+sin(gameplay_time*18.0)*.006*disorder*visual_scale,0,sin(gameplay_time*13.0)*.012*disorder*visual_scale)

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
	else: world.notice("奶蛙撞击了你！再一次就会被捕获。")
