extends Node

const RESEARCH := preload("res://scripts/core/research_manager.gd")
const FUSION := preload("res://scripts/skills/fusion_manager.gd")

class MockPlayer:
	extends RefCounted
	var filter_time := 2.0
	var afterimage_time := 0.0

class MockWorld:
	extends RefCounted
	var player := MockPlayer.new()
	var fields: Array = []
	var traces: Array = []

var failures: Array[String] = []
var checks := 0
var progression_routes_checked := 0
var restart_probe_mode := ""
var test_directory: String

func _ready() -> void:
	var arguments := OS.get_cmdline_user_args()
	if arguments.size() == 2 and arguments[0] in ["--restart-write", "--restart-read"]:
		restart_probe_mode = arguments[0]
		_check_actual_restart(arguments[0], arguments[1])
		_finish()
		return
	test_directory = "user://progression_contract_%d" % OS.get_process_id()
	DirAccess.make_dir_recursive_absolute(test_directory)
	var archive_path := test_directory.path_join("archive.json")
	GameState.set_archive_path(archive_path)
	_check_report_transactions()
	_check_three_report_choices()
	_check(progression_routes_checked == 9, "every one of the nine ability routes must finish validation")
	_check_upgrade_copy()
	_check_archive_restart(archive_path)
	_check_corrupt_and_future_archive()
	_check_fusion_runs()
	_remove_test_files()
	_finish()

func _finish() -> void:
	if failures.is_empty():
		if restart_probe_mode.is_empty():
			print("PROGRESSION CONTRACT PASS: %d checks; report transactions, 9 ability routes, 3 report choices, archive reload, corruption preservation, independent run fusions" % checks)
		else:
			print("RESTART CONTRACT PASS %s: %d checks" % [restart_probe_mode, checks])
		get_tree().quit(0)
	else:
		for message in failures:
			push_error(message)
		get_tree().quit(1)

func _check(condition: bool, message: String) -> void:
	checks += 1
	if not condition:
		failures.append(message)

func _check_report_transactions() -> void:
	GameState.equipped = ["daylight", "pulse", "echo"]
	GameState.reset_run()
	var research := RESEARCH.new()
	add_child(research)
	_check(GameState.SKILLS.size() == 8, "eight optional abilities must be selectable")
	_check(GameState.skill_data("lamp").id == "lamp", "the lamp must have its own data")
	_check(GameState.upgrade_options().size() == 4, "only lamp and three equipped abilities are candidates")
	_check(not research.collect(-1).ok and not research.collect(3).ok, "invalid report indices cannot alter collection")
	var collected: Dictionary = research.collect(0)
	_check(collected.ok and collected.needs_upgrade and collected.count == 1, "a collected report must create an upgrade opportunity")
	_check(GameState.upgrades == 0 and GameState.ability_level("lamp") == 1, "collection must not auto-upgrade any ability")
	_check(not research.collect(0).ok and research.pending_reports.size() == 1, "duplicate report collection must not create more opportunities")
	_check(not research.apply_upgrade("salt").ok and research.has_pending_upgrade(), "unequipped abilities must not consume a report")
	var applied: Dictionary = research.apply_upgrade("lamp")
	_check(applied.ok and applied.level == 2 and GameState.upgrades == 1, "one confirmation must apply exactly one upgrade")
	_check(not research.apply_upgrade("lamp").ok and GameState.upgrades == 1, "double confirmation without another report cannot upgrade twice")
	research.collect(1)
	_check(research.apply_upgrade("lamp").ok and GameState.ability_level("lamp") == 3, "two reports may specialize the lamp to level three")
	research.collect(2)
	_check(GameState.collected == 3 and research.has_pending_upgrade(), "third report count is independent of its pending choice")
	_check(not research.apply_upgrade("lamp").ok and research.has_pending_upgrade(), "a max-level selection cannot consume the third report")
	_check(research.apply_upgrade("pulse").ok and GameState.upgrades == 3, "the remaining report may improve another equipped ability")
	GameState.reset_run()
	research.reset()
	_check(GameState.collected == 0 and GameState.upgrades == 0 and GameState.skill_levels.is_empty(), "a new run must remove every numeric advantage")
	_check(not research.has_pending_upgrade() and research.collected_ids.is_empty(), "a new run must clear report transactions")
	GameState.equipped = ["lamp", "afterimage", "echo", "echo", "salt", "filter"]
	_check(GameState.equipped == ["afterimage", "echo", "salt"], "equipment must exclude lamp, duplicates, and a fourth slot")
	research.queue_free()
	# A signal listener must not spend one pending report a second time while
	# the first confirmation is still completing.
	GameState.equipped = ["echo"]
	GameState.reset_run()
	var guarded := RESEARCH.new()
	add_child(guarded)
	guarded.collect(0)
	var reentrant_results: Array[Dictionary] = []
	var listener := func(): reentrant_results.append(guarded.apply_upgrade("lamp"))
	GameState.state_changed.connect(listener)
	var guarded_result: Dictionary = guarded.apply_upgrade("lamp")
	GameState.state_changed.disconnect(listener)
	_check(guarded_result.ok and GameState.upgrades == 1 and GameState.ability_level("lamp") == 2, "reentrant state listeners cannot spend a report twice")
	_check(reentrant_results.all(func(result): return not result.ok), "every reentrant confirmation must be rejected")
	guarded.queue_free()

func _check_three_report_choices() -> void:
	for ability in ["lamp", "afterimage", "echo", "luminol", "mire", "salt", "filter", "daylight", "pulse"]:
		var loadout: Array[String] = []
		loadout.append(ability if ability != "lamp" else "echo")
		GameState.equipped = loadout
		GameState.reset_run()
		var research := RESEARCH.new()
		add_child(research)
		for report in [0, 1]:
			research.collect(report)
			var option: Dictionary = GameState.upgrade_options()[0]
			for candidate in GameState.upgrade_options():
				if candidate.id == ability:
					option = candidate
			_check(not String(option.benefit).is_empty(), "%s must explain both upgrade benefits" % ability)
			_check(research.apply_upgrade(ability).ok, "%s must support three fixed levels" % ability)
		_check(GameState.ability_level(ability) == 3 and not GameState.upgrade_ability(ability), "%s cannot exceed level three" % ability)
		_check(not GameState.ability_values(ability).is_empty(), "%s must expose actual prototype values" % ability)
		progression_routes_checked += 1
		research.queue_free()
	# Degenerate empty equipment: after lamp reaches its cap, explicitly discard the
	# last opportunity without inventing a replacement reward.
	GameState.equipped = []
	GameState.reset_run()
	var research := RESEARCH.new()
	add_child(research)
	for report in [0, 1]:
		research.collect(report)
		research.apply_upgrade("lamp")
	research.collect(2)
	_check(GameState.upgrade_options().is_empty(), "maxed lamp with no equipment has no legal candidate")
	_check(research.clear_without_upgrade().ok and not research.has_pending_upgrade() and GameState.upgrades == 2, "empty choice clears its transaction without awarding an upgrade")
	research.queue_free()

func _check_archive_restart(archive_path: String) -> void:
	GameState.record_knowledge("lamp")
	GameState.record_knowledge("daylight")
	GameState.record_fusion("contract_fusion", "隔离测试融合：只检验档案，不授予数值。")
	var persisted: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(archive_path))
	_check(persisted.reports.has("tower") and persisted.reports.has("dead_tree") and persisted.reports.has("car"), "persistent reports must use stable landmark identities")
	persisted["unrelated_metadata"] = {"keep": "original"}
	persisted.knowledge["external_note"] = {"name": "外部备注", "science": "应保留的未知知识条目"}
	persisted.knowledge["mire"] = {"name":"旧泥区名称", "science":"过时的科学说明", "effect":"双方完全相同的旧规则", "first_recorded_at":"preserve-original-time", "extension":{"keep":true}}
	_write_json(archive_path, persisted)
	GameState.set_archive_path(archive_path)
	var bytes_before_display := FileAccess.get_file_as_bytes(archive_path)
	var archive_display := "\n".join(GameState.archive_lines())
	_check("阻止其开始冲刺" in archive_display and not "双方完全相同的旧规则" in archive_display, "known archived abilities must display the current rules after a copy correction")
	_check("应保留的未知知识条目" in archive_display, "unknown archived knowledge must retain its original display instead of falling back to a known skill")
	_check(FileAccess.get_file_as_bytes(archive_path) == bytes_before_display, "displaying corrected knowledge must not rewrite the historical archive")
	GameState.record_knowledge("pulse")
	persisted = JSON.parse_string(FileAccess.get_file_as_string(archive_path))
	_check(persisted.unrelated_metadata.keep == "original" and persisted.knowledge.has("external_note"), "normal writes must preserve unrelated archive keys and entries")
	_check(persisted.knowledge.mire.first_recorded_at == "preserve-original-time" and persisted.knowledge.mire.extension.keep, "later discoveries must retain existing first-discovery metadata and extension fields")
	GameState.skill_levels["pulse"] = 3
	GameState.set_archive_path(archive_path)
	GameState.reset_run()
	_check(GameState.ability_level("pulse") == 1 and GameState.archive_lines().any(func(line): return "乱频" in line), "restart reload preserves knowledge but cannot import skill strength")
	_check(GameState.archive_lines().any(func(line): return "隔离测试融合" in line), "fusion descriptions must survive restart")

func _check_upgrade_copy() -> void:
	GameState.reset_run()
	for ability in ["lamp", "afterimage", "echo", "luminol", "mire", "salt", "filter", "daylight", "pulse"]:
		var base_description := GameState.upgrade_benefit(ability,1)
		_check(not base_description.is_empty() and not "→" in base_description,"%s base handbook must describe actual parameters without an imaginary upgrade" % ability)
		for target_level in [2, 3]:
			var benefit := GameState.upgrade_benefit(ability, target_level)
			_check("→" in benefit, "%s Lv%d choice must compare current and next-level useful values" % [ability, target_level])
			_check(not "半角" in benefit and not "击退强度" in benefit and not "蓝光强度" in benefit, "%s choice must express player effects rather than unitless debug values" % ability)
		_check(not GameState.upgrade_cost_summary(ability).is_empty(), "%s must retain a meaningful compact cost" % ability)
	GameState.equipped = ["salt", "pulse", "daylight"]
	var choices := GameState.upgrade_options()
	for choice in choices:
		_check(choice.cost == GameState.upgrade_cost_summary(choice.id), "candidate costs must use the compact summary API")
	_check("照明12→15 m" in choices[0].benefit and "爆发10→12 m" in choices[0].benefit and "0.8→0.6秒" in choices[0].benefit, "lamp must preserve its real distance and interference improvements")
	_check("30体力" in GameState.upgrade_cost_summary("salt"), "salt next-level card must expose its increased actual stamina cost")
	GameState.skill_levels["salt"] = 2
	_check("自身脱水减轻" in GameState.upgrade_benefit("salt", 3), "salt precision upgrade must expose the implemented dehydration improvement")
	_check("每次点射耗8电量" in GameState.upgrade_cost_summary("pulse"), "pulse must retain its per-shot shared energy cost")
	_check(GameState.upgrade_cost_summary("unknown").is_empty(), "unknown ability IDs cannot inherit another ability's cost")
	_check("光具有动量" in GameState.skill_data("lamp").science and "全部储能" in GameState.skill_data("lamp").effect, "compact choices must preserve the full scientific handbook and discharge boundary")
	GameState.reset_run()

func _check_corrupt_and_future_archive() -> void:
	for scenario in ["corrupt", "future", "malformed_schema"]:
		var path := test_directory.path_join(scenario + ".json")
		var bytes := "{ unfinished archive"
		if scenario == "future":
			bytes = JSON.stringify({"schema_version": 999, "retain": "future payload"})
		elif scenario == "malformed_schema":
			bytes = JSON.stringify({"schema_version": 1, "knowledge": [], "reports": {}, "fusions": {}})
		var file := FileAccess.open(path, FileAccess.WRITE)
		file.store_string(bytes)
		file.close()
		GameState.set_archive_path(path)
		GameState.record_knowledge("lamp")
		_check(FileAccess.get_file_as_string(path) == bytes, "%s source must remain recoverable byte-for-byte" % scenario)
		_check(not GameState.archive_writable and not GameState.last_archive_error.is_empty(), "%s must surface its read-only recovery state" % scenario)
	# A blocked directory is a real write failure, not a successful archive save.
	GameState.set_archive_path(test_directory.path_join("missing/subdirectory/archive.json"))
	GameState.record_knowledge("lamp")
	_check(not GameState.last_archive_error.is_empty(), "a failed write must expose an actual persistence error")
	GameState.set_archive_path(test_directory.path_join("archive.json"))

func _check_fusion_runs() -> void:
	GameState.equipped = ["echo", "filter"]
	for run in range(2):
		var fusion := FUSION.new()
		add_child(fusion)
		fusion.setup(MockWorld.new())
		_check(not fusion.check_trigger("echo").is_empty(), "run %d must announce its own actual discovery even with old history" % run)
		_check(fusion.check_trigger("echo").is_empty(), "run %d must deduplicate its own fusion notice" % run)
		fusion.queue_free()
	GameState.set_archive_path(test_directory.path_join("archive.json"))
	_check(GameState.archive_lines().any(func(line): return "谱化回声" in line), "actual fusion triggers must persist the discovered description")

func _write_json(path: String, content: Dictionary) -> void:
	var file := FileAccess.open(path, FileAccess.WRITE)
	file.store_string(JSON.stringify(content, "\t"))
	file.close()

func _check_actual_restart(mode: String, path: String) -> void:
	GameState.set_archive_path(path)
	if mode == "--restart-write":
		_check(not FileAccess.file_exists(path), "restart writer must receive a new isolated fixture")
		_check(GameState.record_knowledge("daylight"), "restart fixture must save actual knowledge")
		_check(GameState.record_report("tower"), "restart fixture must save a stable report")
		_check(GameState.record_fusion("restart_pair", "跨进程融合记录"), "restart fixture must save its fusion")
		GameState.equipped = ["daylight"]
		GameState.upgrade_ability("daylight")
	else:
		_check(FileAccess.file_exists(path), "restart reader must observe the written fixture")
		_check(GameState.ability_level("daylight") == 1 and GameState.upgrades == 0 and GameState.collected == 0, "a genuinely new process must not inherit run power or progress")
		var lines := "\n".join(GameState.archive_lines())
		_check("蓄昼" in lines and "输电塔研究报告" in lines and "跨进程融合记录" in lines, "a genuinely new process must read knowledge, stable reports and fusions")

func _remove_test_files() -> void:
	var directory := DirAccess.open(test_directory)
	for filename in directory.get_files():
		directory.remove(filename)
	DirAccess.remove_absolute(test_directory)
