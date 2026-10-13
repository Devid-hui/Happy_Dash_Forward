extends Node

const SKILL_MANAGER := preload("res://scripts/skills/skill_manager.gd")

class MockPlayer:
	extends RefCounted
	var global_position := Vector3(3, 0, 4)
	var global_basis := Basis.IDENTITY
	var stamina := 100.0
	var afterimage_ready := true
	var afterimage_window := 2.0
	var afterimage_time := 0.0
	var echo_deafness := 0.0
	var dehydration := 0.0
	var filter_time := 0.0
	var energy := 100.0
	var pulse_mode := false
	var toggle_count := 0
	var daylight_attempts := 0
	var actions: Array[String] = []

	func toggle_pulse_mode() -> void:
		pulse_mode = not pulse_mode
		toggle_count += 1

	func activate_daylight() -> bool:
		daylight_attempts += 1
		# A fake lower-level failure boundary. The actual cost/motion belongs to
		# Player, verified separately by the real-world integration contract.
		return energy > 0.0

	func play_equipment_action(kind: String) -> void:
		actions.append(kind)

class MockWorld:
	extends RefCounted
	var blocked := false
	var luminol_charges := 3
	var calls: Array[Dictionary] = []
	var notices: Array[String] = []
	var fusions: Array[String] = []

	func is_gameplay_blocked() -> bool:
		return blocked

	func notice(message: String) -> void:
		notices.append(message)

	func check_fusion(skill_id: String) -> void:
		fusions.append(skill_id)

	func show_afterimage(duration: float) -> void:
		calls.append({"kind":"afterimage", "duration":duration})

	func emit_echo(position: Vector3, highlight_duration: float = 7.0) -> void:
		calls.append({"kind":"echo", "position":position, "highlight_duration":highlight_duration})

	func reveal_traces(improved: bool = false, reveal_duration: float = 8.0, salt_emission: float = 1.2) -> void:
		calls.append({"kind":"luminol", "improved":improved, "reveal_duration":reveal_duration, "salt_emission":salt_emission})

	func place_field(kind: String, position: Vector3, radius: float = 2.4, duration: float = 11.0) -> void:
		calls.append({"kind":kind, "position":position, "radius":radius, "duration":duration})

	func set_filtering(enabled: bool) -> void:
		calls.append({"kind":"filter", "enabled":enabled})

var failures: Array[String] = []
var checks := 0
var completed_routes := 0
var test_directory: String

func _ready() -> void:
	var explicit_archive_path := OS.get_environment("HDF_ARCHIVE_PATH")
	if not explicit_archive_path.is_empty():
		_check(GameState.archive_path == explicit_archive_path, "GameState startup must honor the explicit per-process archive isolation path")
	test_directory = "user://skills_contract_%d" % OS.get_process_id()
	DirAccess.make_dir_recursive_absolute(test_directory)
	GameState.set_archive_path(test_directory.path_join("archive.json"))
	_check_equipment_and_modal_guards()
	_check_all_levels()
	_check(completed_routes == 24, "all eight optional abilities at all three levels must complete validation")
	_check_failed_casts()
	_check_switch_and_cooldowns()
	_cleanup()
	if failures.is_empty():
		print("SKILLS CONTRACT PASS: %d checks; all 24 level routes, equipment/modal guards, call parameters, resource failures, success-only discovery, pulse switching, cooldown tick/reset" % checks)
		get_tree().quit(0)
	else:
		for message in failures:
			push_error(message)
		get_tree().quit(1)

func _check(condition: bool, message: String) -> void:
	checks += 1
	if not condition:
		failures.append(message)

func _make_context(skill_id: String, level: int = 1) -> Dictionary:
	var loadout: Array[String] = [skill_id]
	GameState.equipped = loadout
	GameState.reset_run()
	GameState.skill_levels[skill_id] = level
	var player := MockPlayer.new()
	var world := MockWorld.new()
	var manager := SKILL_MANAGER.new()
	add_child(manager)
	manager.setup(player, world)
	return {"player":player, "world":world, "manager":manager}

func _check_equipment_and_modal_guards() -> void:
	GameState.equipped = ["lamp", "afterimage", "echo", "echo", "salt", "pulse"]
	_check(GameState.equipped == ["afterimage", "echo", "salt"], "eight choices must still use only three optional equipment slots")
	var context := _make_context("echo")
	for slot in [-1, 1, 3, 999]:
		context.manager.cast_slot(slot)
	_check(context.world.calls.is_empty() and context.world.fusions.is_empty(), "negative, empty, fourth and out-of-range slots must not cast")
	GameState.equipped.append("lamp")
	GameState.equipped.append("unknown_ability")
	GameState.equipped.append("salt")
	for slot in [1, 2, 3]: context.manager.cast_slot(slot)
	_check(context.world.calls.is_empty(), "malformed or fourth entries cannot expose the base lamp or an unequipped ability through slots")
	GameState.equipped = []
	context.manager.cast_slot(0)
	_check(context.world.calls.is_empty(), "an unequipped slot must not cast")
	GameState.equipped = ["echo"]
	context.world.blocked = true
	context.manager.cast_slot(0)
	_check(context.world.calls.is_empty() and context.manager.cooldowns.is_empty(), "modal states must block casts and cooldown consumption")
	_check(not FileAccess.file_exists(GameState.archive_path), "blocked/invalid casts must not record knowledge")
	context.manager.queue_free()

func _check_all_levels() -> void:
	for skill in GameState.SKILLS:
		for level in [1, 2, 3]:
			var context := _make_context(skill.id, level)
			var values := GameState.ability_values(skill.id)
			context.manager.cast_slot(0)
			_check(context.world.fusions == [skill.id], "%s Lv%d success must check fusion exactly once" % [skill.id, level])
			_check(context.player.actions.size() == 1, "%s Lv%d success must trigger one equipment action" % [skill.id, level])
			var action := String(context.player.actions[0]) if not context.player.actions.is_empty() else ""
			var call: Dictionary = context.world.calls[0] if not context.world.calls.is_empty() else {}
			match skill.id:
				"afterimage":
					_check(call.get("duration") == values.duration and context.player.afterimage_time == values.duration, "afterimage Lv%d must use duration in both presentation and logic" % level)
					_check(context.player.stamina == 92.0 and not context.player.afterimage_ready and action == "afterimage", "afterimage must spend stamina and its flash opportunity once")
				"echo":
					_check(call.get("highlight_duration") == values.highlight_duration and call.get("position") == context.player.global_position, "echo Lv%d must pass marker duration without a new range limit" % level)
					_check(context.player.echo_deafness == values.deafness and action == "echo", "echo Lv%d must use its actual deafness duration" % level)
				"luminol":
					_check(call.get("reveal_duration") == values.reveal_duration and call.get("salt_emission") == values.salt_emission and call.get("improved") == (level >= 2), "luminol Lv%d must pass reveal and salt intensity parameters" % level)
					_check(context.world.luminol_charges == 2 and action == "luminol", "luminol must consume one finite reagent per successful cast")
				"mire":
					_check(call.get("radius") == values.radius and call.get("duration") == values.duration, "mire Lv%d must pass its actual radius/duration" % level)
					_check(call.get("position") == context.player.global_position - context.player.global_basis.z * 2.0 and action == "mud", "mire placement and equipment action must retain their existing meaning")
				"salt":
					_check(call.get("radius") == values.radius and call.get("duration") == values.duration, "salt Lv%d must pass its actual radius/duration" % level)
					_check(context.player.stamina == 100.0 - values.stamina_cost and context.player.dehydration == values.dehydration and action == "salt", "salt Lv%d must retain actual stamina and dehydration costs" % level)
				"filter":
					_check(context.player.filter_time == values.duration and call.get("enabled", false), "filter Lv%d must use actual duration and enable existing rain filter" % level)
					_check(action == "filter", "filter action must correspond to its successful activation")
				"daylight":
					_check(context.player.daylight_attempts == 1 and action == "boost", "daylight must delegate the actual energy/motion operation to Player")
					_check(context.player.energy == 100.0, "the manager must not double-deduct energy already owned by Player")
				"pulse":
					_check(context.player.pulse_mode and context.player.toggle_count == 1 and action == "mode", "pulse must delegate mode switching to Player")
					_check(not context.manager.cooldowns.has("pulse"), "pulse mode switching must have no eight-second cooldown")
			if skill.id != "pulse":
				_check(context.manager.cooldowns.get(skill.id, -1.0) == values.get("cooldown", 8.0), "%s Lv%d must use its actual cooldown" % [skill.id, level])
			var parser := JSON.new()
			var parse_error := parser.parse(FileAccess.get_file_as_string(GameState.archive_path))
			var persisted: Dictionary = parser.data if parse_error == OK and parser.data is Dictionary else {}
			_check(persisted.get("knowledge", {}).has(skill.id), "%s successful activation must persist knowledge" % skill.id)
			completed_routes += 1
			context.manager.queue_free()

func _check_failed_casts() -> void:
	for failure in ["flash_missing", "flash_expired", "stamina_missing", "reagent_missing", "salt_stamina", "daylight_energy"]:
		GameState.set_archive_path(test_directory.path_join(failure + ".json"))
		var skill_id := "afterimage"
		if failure == "reagent_missing": skill_id = "luminol"
		elif failure == "salt_stamina": skill_id = "salt"
		elif failure == "daylight_energy": skill_id = "daylight"
		var context := _make_context(skill_id)
		match failure:
			"flash_missing": context.player.afterimage_ready = false
			"flash_expired": context.player.afterimage_window = 0.0
			"stamina_missing": context.player.stamina = 7.0
			"reagent_missing": context.world.luminol_charges = 0
			"salt_stamina": context.player.stamina = 21.0
			"daylight_energy": context.player.energy = 0.0
		var stamina_before: float = context.player.stamina
		context.manager.cast_slot(0)
		_check(context.manager.cooldowns.is_empty() and context.world.calls.is_empty(), "%s failure must not apply an effect or cooldown" % failure)
		_check(context.world.fusions.is_empty() and context.player.actions.is_empty() and not FileAccess.file_exists(GameState.archive_path), "%s failure must not count as knowledge, fusion or a performed equipment action" % failure)
		_check(context.player.stamina == stamina_before, "%s failure must not consume stamina" % failure)
		context.manager.queue_free()

func _check_switch_and_cooldowns() -> void:
	GameState.set_archive_path(test_directory.path_join("switch.json"))
	var pulse := _make_context("pulse")
	for index in range(4): pulse.manager.cast_slot(0)
	_check(pulse.player.toggle_count == 4 and not pulse.player.pulse_mode and pulse.manager.cooldowns.is_empty(), "pulse must switch repeatedly in both directions without cooldown")
	pulse.world.blocked = true
	pulse.manager.cast_slot(0)
	_check(pulse.player.toggle_count == 4, "modal blocking also applies to mode switching")
	pulse.manager.queue_free()
	var echo := _make_context("echo", 3)
	echo.manager.cast_slot(0)
	echo.manager.cast_slot(0)
	_check(echo.world.calls.size() == 1 and echo.player.actions.size() == 1 and echo.world.fusions.size() == 1, "cooldown rejection must not duplicate effects, actions or discoveries")
	echo.manager.tick(2.0)
	_check(echo.manager.cooldowns.echo == 4.0, "cooldown tick must decrement the level-specific duration")
	echo.manager.tick(-1.0)
	_check(echo.manager.cooldowns.echo == 4.0, "invalid negative elapsed time must not lengthen or consume cooldown")
	echo.manager.tick(100.0)
	_check(echo.manager.cooldowns.echo == 0.0, "cooldown tick must clamp at zero")
	echo.manager.cast_slot(0)
	_check(echo.world.calls.size() == 2, "expired cooldown must permit a new cast")
	echo.manager.reset()
	_check(echo.manager.cooldowns.is_empty(), "new run/reset must clear skill cooldowns")
	echo.manager.queue_free()

func _cleanup() -> void:
	var directory := DirAccess.open(test_directory)
	for filename in directory.get_files(): directory.remove(filename)
	DirAccess.remove_absolute(test_directory)
