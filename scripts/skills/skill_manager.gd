extends Node

var player
var world
var cooldowns: Dictionary = {}

func setup(owner_player, game_world) -> void:
	player = owner_player
	world = game_world

func cast_slot(slot: int) -> void:
	if player == null or world == null or slot < 0 or slot >= mini(3, GameState.equipped.size()):
		return
	if world.is_gameplay_blocked():
		return
	var skill_id: String = GameState.equipped[slot]
	var values := GameState.ability_values(skill_id)
	if values.is_empty() or skill_id == "lamp":
		return
	# Pulse is a release-mode switch, not a cast with an eight-second lockout.
	if skill_id != "pulse" and cooldowns.get(skill_id, 0.0) > 0.0:
		world.notice("能力尚在恢复。")
		return
	var success := false
	var equipment_action := skill_id
	match skill_id:
		"afterimage":
			if not player.afterimage_ready or player.afterimage_window <= 0.0:
				world.notice("没有近期闪电，无法记录后像。")
				return
			if player.stamina < 8.0:
				world.notice("体力不足，无法记录后像。")
				return
			player.afterimage_ready = false
			player.afterimage_time = values.duration
			player.stamina -= 8.0
			world.show_afterimage(player.afterimage_time)
			success = true
		"echo":
			world.emit_echo(player.global_position, values.highlight_duration)
			player.echo_deafness = values.deafness
			success = true
		"luminol":
			if world.luminol_charges <= 0:
				world.notice("鲁米诺试剂已用尽。")
				return
			world.luminol_charges -= 1
			world.reveal_traces(GameState.ability_level(skill_id) >= 2, values.reveal_duration, values.salt_emission)
			success = true
		"mire":
			world.place_field("mire", player.global_position - player.global_basis.z * 2.0, values.radius, values.duration)
			equipment_action = "mud"
			success = true
		"salt":
			if player.stamina < values.stamina_cost:
				world.notice("体力不足，无法结成盐阵。")
				return
			player.stamina -= values.stamina_cost
			player.dehydration = values.dehydration
			world.place_field("salt", player.global_position, values.radius, values.duration)
			success = true
		"filter":
			player.filter_time = values.duration
			world.set_filtering(true)
			world.notice("剥噪生效：雨声减弱并保留所选频段。敌人、脚步与雷声不受此滤波影响。")
			success = true
		"daylight":
			success = player.activate_daylight()
			equipment_action = "boost"
		"pulse":
			player.toggle_pulse_mode()
			equipment_action = "mode"
			success = true
	if success:
		if skill_id != "pulse":
			cooldowns[skill_id] = float(values.get("cooldown", 8.0))
		player.play_equipment_action(equipment_action)
		GameState.record_knowledge(skill_id)
		world.check_fusion(skill_id)

func tick(delta: float) -> void:
	if delta <= 0.0:
		return
	for key in cooldowns.keys():
		cooldowns[key] = maxf(0.0, cooldowns[key] - delta)

func reset() -> void:
	cooldowns.clear()
