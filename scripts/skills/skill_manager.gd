extends Node

var player
var world
var cooldowns: Dictionary = {}

func setup(owner_player, game_world) -> void:
	player = owner_player
	world = game_world

func cast_slot(slot: int) -> void:
	if slot >= GameState.equipped.size(): return
	var skill_id: String = GameState.equipped[slot]
	if cooldowns.get(skill_id, 0.0) > 0.0:
		world.notice("能力尚在恢复。"); return
	var success := false
	match skill_id:
		"afterimage":
			if not player.afterimage_ready or player.afterimage_window <= 0.0: world.notice("没有近期闪电，无法记录后像。"); return
			player.afterimage_ready = false; player.afterimage_time = 3.5 if GameState.skill_levels.get(skill_id, 1) >= 2 else 2.5; world.show_afterimage(player.afterimage_time); player.stamina = maxf(0, player.stamina - 8); success = true
		"echo":
			world.emit_echo(player.global_position); player.echo_deafness = 4.0; success = true
		"luminol":
			if world.luminol_charges <= 0: world.notice("鲁米诺试剂已用尽。"); return
			world.luminol_charges -= 1; world.reveal_traces(GameState.skill_levels.get(skill_id, 1) >= 2); success = true
		"mire":
			world.place_field("mire", player.global_position - player.global_basis.z * 2.0, 3.1 if GameState.skill_levels.get(skill_id, 1) >= 2 else 2.4); success = true
		"salt":
			var salt_cost := 30.0 if GameState.skill_levels.get(skill_id, 1) >= 2 else 22.0
			if player.stamina < salt_cost: world.notice("体力不足，无法结成盐阵。"); return
			player.stamina -= salt_cost; player.dehydration = 18.0; world.place_field("salt", player.global_position, 3.0 if salt_cost > 22.0 else 2.4); success = true
		"filter":
			player.filter_time = 10.0; world.set_filtering(true); world.notice("剥噪生效：雨声减弱并保留所选频段。敌人、脚步与雷声不受此滤波影响。"); success = true
	if success:
		cooldowns[skill_id] = 8.0
		world.check_fusion(skill_id)

func tick(delta: float) -> void:
	for key in cooldowns.keys(): cooldowns[key] = maxf(0.0, cooldowns[key] - delta)

func reset() -> void:
	cooldowns.clear()
