extends Node

var collected_ids: Dictionary = {}
var world

func setup(game_world) -> void:
	world = game_world

func collect(record_id: int) -> Dictionary:
	if collected_ids.has(record_id):
		return {"ok": false, "count": collected_ids.size(), "skill": ""}
	collected_ids[record_id] = true
	GameState.collected = collected_ids.size()
	GameState.upgrades += 1
	var equipped_count := GameState.equipped.size()
	if equipped_count == 0:
		return {"ok": true, "count": collected_ids.size(), "skill": ""}
	var skill_id: String = GameState.equipped[(collected_ids.size() - 1) % equipped_count]
	GameState.skill_levels[skill_id] = 2
	return {"ok": true, "count": collected_ids.size(), "skill": skill_id}

func reset() -> void:
	collected_ids.clear()
