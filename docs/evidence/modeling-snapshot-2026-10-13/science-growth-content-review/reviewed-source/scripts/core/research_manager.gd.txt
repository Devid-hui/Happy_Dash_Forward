extends Node

var collected_ids: Dictionary = {}
var pending_reports: Array[String] = []
var world
var _applying_upgrade := false

func setup(game_world) -> void:
	world = game_world

func collect(record_id: int) -> Dictionary:
	if record_id < 0 or record_id >= GameState.REPORTS.size() or collected_ids.has(record_id):
		return {"ok":false, "count":collected_ids.size(), "skill":"", "needs_upgrade":has_pending_upgrade()}
	var report: Dictionary = GameState.REPORTS[record_id]
	collected_ids[record_id] = true
	pending_reports.append(report.id)
	GameState.collected = collected_ids.size()
	GameState.record_report(report.id)
	GameState.state_changed.emit()
	return {"ok":true, "count":collected_ids.size(), "skill":"", "report_id":report.id, "needs_upgrade":true}

func has_pending_upgrade() -> bool:
	return not pending_reports.is_empty()

func apply_upgrade(skill_id: String) -> Dictionary:
	if _applying_upgrade or not has_pending_upgrade():
		return {"ok":false, "id":skill_id, "needs_upgrade":has_pending_upgrade()}
	_applying_upgrade = true
	if not GameState.upgrade_ability(skill_id):
		_applying_upgrade = false
		return {"ok":false, "id":skill_id, "needs_upgrade":true}
	var report_id: String = pending_reports.pop_front()
	GameState.record_knowledge(skill_id)
	var level: int = GameState.ability_level(skill_id)
	GameState.state_changed.emit()
	_applying_upgrade = false
	return {"ok":true, "id":skill_id, "level":level, "benefit":GameState.upgrade_benefit(skill_id, level), "report_id":report_id, "needs_upgrade":has_pending_upgrade()}

func clear_without_upgrade() -> Dictionary:
	if _applying_upgrade or not has_pending_upgrade() or not GameState.upgrade_options().is_empty():
		return {"ok":false, "needs_upgrade":has_pending_upgrade()}
	var report_id: String = pending_reports.pop_front()
	GameState.state_changed.emit()
	return {"ok":true, "id":"", "level":0, "report_id":report_id, "needs_upgrade":has_pending_upgrade()}

func reset() -> void:
	collected_ids.clear()
	pending_reports.clear()
	_applying_upgrade = false
