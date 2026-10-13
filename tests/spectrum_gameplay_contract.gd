extends Node
# Real player/world/physics contracts; controlled input is distinct from a human playtest.
const WORLD := preload("res://scripts/world/world.gd")
var world
var checks := 0
var failures: Array[String] = []

func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	call_deferred("run_contract")

func expect(condition: bool, message: String) -> void:
	checks += 1
	if not condition:
		failures.append(message)
		push_error(message)
		if is_instance_valid(world):
			print("SPECTRUM FAILURE STATE ",JSON.stringify({"paused":world.paused,"tree_paused":get_tree().paused,"game_over":GameState.game_over,"focused":world._window_is_focused(),"display":DisplayServer.get_name(),"physics_frame":Engine.get_physics_frames()}))

func frames(count: int) -> void:
	for index in range(count): await get_tree().physics_frame

func press_fire() -> void:
	var input := InputEventAction.new()
	input.action = "lamp_fire"
	input.pressed = true
	world.player._unhandled_input(input)

func run_contract() -> void:
	var original_archive: String = GameState.archive_path
	var test_archive := "user://spectrum_gameplay_contract_%d.json" % OS.get_process_id()
	GameState.set_archive_path(test_archive)
	GameState.equipped = ["echo","daylight","pulse"]
	GameState.reset_run()
	world = WORLD.new()
	add_child(world)
	world.hunter_director.set_physics_process(false)
	world.storm_controller.set_process(false)
	for hunter in world.hunter_nodes:
		hunter.set_physics_process(false)
	await frames(2)
	var player = world.player
	player.global_position = Vector3.ZERO
	player.rotation = Vector3.ZERO
	player.pitch = 0.0
	player.camera.rotation = Vector3.ZERO
	player.velocity = Vector3.ZERO
	for index in range(5): world.hunter_nodes[index].global_position = Vector3(42+index*4,0,0)
	await frames(2)

	# Shared battery and bounded passive recovery.
	player.energy = 50.0
	player.lamp_enabled = true
	player._tick_energy(1.0)
	expect(is_equal_approx(player.energy,48.6),"lighting consumes the shared battery at its documented rate")
	player.lamp_enabled = false
	player._tick_energy(1.0)
	expect(is_equal_approx(player.energy,49.9),"switching off lighting permits slow recovery")
	player.energy = 99.8
	player._tick_energy(1.0)
	expect(player.energy == player.energy_capacity(),"recovery cannot exceed capacity")
	player.energy = .1
	player.lamp_enabled = true
	player._tick_energy(1.0)
	expect(player.energy == 0.0 and not player.lamp_enabled,"empty battery automatically extinguishes lighting")
	expect(not player.toggle_lamp(),"lighting cannot turn on before adequate recovery")
	player.energy = 80.0
	player.daylight_time = 0.0
	player.disturbance_time = 0.0
	expect(player.activate_daylight(),"equipped daylight can activate with enough shared energy")
	expect(is_equal_approx(player.energy,55.0) and player.daylight_time > 2.0,"daylight consumes 25 energy and starts its actual duration")
	expect(player.disturbance_time > 0.0,"daylight keeps its brief controllable gait disturbance")
	expect(world.daylight_audio.playing and world.daylight_audio.stream != null,"daylight has its distinct short audible energy disturbance")
	expect(not player.activate_daylight(),"an already active boost cannot spend energy again")
	player.energy = 10.0
	player.daylight_time = 0.0
	expect(not player.activate_daylight() and player.energy == 10.0,"failed activation preserves energy")
	player.energy = 60.0
	GameState.reduced_flashes = true
	expect(is_equal_approx(player.capture_lightning(),18.0),"reduced flashes retain the same passive capture energy")
	player.energy = 95.0
	expect(is_equal_approx(player.capture_lightning(),5.0) and player.energy == 100.0,"light capture is capped at the shared capacity")
	player.daylight_time = 0.0
	player.disturbance_time = 0.0
	player.recovery_delay = 0.0
	player.energy = 80.0
	player.lamp_enabled = false
	player.skill_manager.cast_slot(2)
	expect(player.pulse_mode and not player.cooldowns.has("pulse"),"pulse toggles mode without introducing an eight-second cooldown")
	player.skill_manager.cast_slot(2)
	expect(not player.pulse_mode,"the same slot can immediately toggle back")
	player.skill_manager.cast_slot(2)

	# Actual query hits a hunter, keeps health, and imparts horizontal momentum.
	var target = world.hunter_nodes[0]
	target.global_position = Vector3(0,0,-6)
	await frames(2)
	var health_before: float = target.health
	var energy_before: float = player.energy
	press_fire()
	expect(is_equal_approx(player.energy,energy_before),"input queues the ray rather than querying the physics space in input dispatch")
	await frames(2)
	expect(is_equal_approx(player.energy,energy_before-8.0),"a real queued point shot spends exactly eight shared energy")
	expect(target.knockback.length() > 3.9 and target.health == health_before,"point shot applies momentum without unrequested health damage")
	expect(player.noise == 13.0 and player.fire_cooldown > 0.0,"point shot retains noise and a brief firing interval")
	world._update_pulse_noise_feedback()
	expect(world.pulse_noise_audio.playing,"accumulating pulse noise has an actual audible signal before scream overload")
	var spent: float = player.energy
	expect(not player.fire_lamp() and player.energy == spent,"firing during the interval cannot spend again")

	# Walls must block both point shots and cone effects.
	var wall := StaticBody3D.new()
	var shape := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = Vector3(3,3,.5)
	shape.shape = box
	wall.position = Vector3(0,1.5,-3)
	wall.add_child(shape)
	world.add_child(wall)
	await frames(2)
	target.knockback = Vector3.ZERO
	player.fire_cooldown = 0.0
	press_fire()
	await frames(2)
	expect(target.knockback == Vector3.ZERO,"solid geometry occludes point-shot recoil")
	player.pulse_mode = false
	player.energy = 100.0
	player.fire_cooldown = 0.0
	press_fire()
	await frames(2)
	expect(target.knockback == Vector3.ZERO,"solid geometry occludes a concentrated burst")
	expect(player.energy == 0.0 and not player.lamp_enabled and player.blind_time > 0.0,"burst consumes the entire battery and retains its brief visual cost")
	wall.free()
	await frames(2)
	world.hunter_nodes[0].global_position = Vector3(-1,0,-7)
	world.hunter_nodes[1].global_position = Vector3(1,0,-7)
	world.hunter_nodes[2].global_position = Vector3(0,0,7)
	for hunter in world.hunter_nodes: hunter.knockback = Vector3.ZERO
	await frames(2)
	player.energy = 75.0
	player.fire_cooldown = 0.0
	press_fire()
	await frames(2)
	expect(world.hunter_nodes[0].knockback.length() > 7.0 and world.hunter_nodes[1].knockback.length() > 7.0,"burst affects multiple visible hunters in its forward cone")
	expect(world.hunter_nodes[2].knockback == Vector3.ZERO,"burst does not hit a hunter behind the player")
	var knocked = world.hunter_nodes[0]
	knocked.charge_phase = knocked.ChargePhase.CHARGING
	knocked.repel(Vector3.FORWARD,12.0,.4)
	expect(knocked.charge_phase == knocked.ChargePhase.RESTING and knocked.stunned >= .4,"a successful repel interrupts charge and starts recovery")
	knocked.reset_after_relocation()
	expect(knocked.knockback == Vector3.ZERO,"relocation clears residual momentum")

	player.energy = 100.0
	player.pulse_mode = true
	player.noise = 84.0
	player.fire_cooldown = 0.0
	press_fire()
	await frames(2)
	expect(player.noise >= 85.0 and player.disturbance_time > 2.0,"overload produces its bounded disturbance even with reduced flashes")
	expect(is_instance_valid(world.disorientation_audio) and world.disorientation_audio.stream != null,"noise overload has a real scream stream")
	player.echo_deafness = 1.0
	world._update_echo_feedback()
	expect(world.echo_audio.playing,"echo deafness has actual audible tinnitus")
	var own_effect: AudioEffectLowPassFilter = world.echo_filter
	var effect_index := -1
	for index in range(AudioServer.get_bus_effect_count(0)):
		if AudioServer.get_bus_effect(0,index) == own_effect: effect_index = index
	expect(effect_index >= 0 and AudioServer.is_bus_effect_enabled(0,effect_index),"echo deafness enables the world's temporary sound filter")
	player.echo_deafness = 0.0
	world._update_echo_feedback()
	expect(not world.echo_audio.playing and not AudioServer.is_bus_effect_enabled(0,effect_index),"hearing restoration disables both tinnitus and filter")
	player.noise = 0.0
	world._update_pulse_noise_feedback()
	expect(not world.pulse_noise_audio.playing,"radio interference stops when pulse noise has dissipated")

	# Actual movement speed, pause freeze, and stale-input rejection.
	player.global_position = Vector3.ZERO
	player.velocity = Vector3.ZERO
	player.disturbance_time = 0.0
	player.daylight_time = 0.0
	Input.action_press("move_forward")
	await frames(25)
	var normal_speed := Vector2(player.velocity.x,player.velocity.z).length()
	player.daylight_time = 2.4
	await frames(25)
	var boosted_speed := Vector2(player.velocity.x,player.velocity.z).length()
	Input.action_release("move_forward")
	expect(normal_speed > 4.9 and boosted_speed > normal_speed*1.27,"daylight changes real movement velocity according to its level")
	press_fire()
	world.toggle_pause()
	var paused_energy: float = player.energy
	var paused_clock: float = world.gameplay_elapsed
	await frames(4)
	expect(player.energy == paused_energy and world.gameplay_elapsed == paused_clock,"pause freezes resources, world time and wind clock")
	world.toggle_pause()
	await frames(2)
	expect(player.energy == paused_energy,"a queued shot cannot leak through pause/resume")
	world.free()
	await get_tree().process_frame
	for index in range(AudioServer.get_bus_effect_count(0)):
		expect(AudioServer.get_bus_effect(0,index) != own_effect,"world teardown removes only its own temporary auditory effect")
	GameState.reduced_flashes = false
	if FileAccess.file_exists(test_archive): DirAccess.remove_absolute(test_archive)
	GameState.set_archive_path(original_archive)
	var cleanup_until := Time.get_ticks_msec()+100
	while Time.get_ticks_msec() < cleanup_until:
		await get_tree().process_frame
	if failures.is_empty():
		print("SPECTRUM GAMEPLAY PASS: %d real-resource, physics-ray, collision-occlusion, cone, knockback, sound, movement, pause and input checks" % checks)
	else:
		print("SPECTRUM GAMEPLAY FAIL: %d of %d checks failed" % [failures.size(),checks])
	get_tree().quit(0 if failures.is_empty() else 1)
