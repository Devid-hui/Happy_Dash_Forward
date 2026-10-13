extends Node

signal state_changed

const LAMP := {"id":"lamp", "name":"谱灯 / Spectrum Lamp", "field":"光学与能量转换", "science":"电能可以转为光能；光具有动量，但现实中便携灯具的光压极小。", "effect":"基础装备，不占技能槽。照明与集中爆发共用电量；爆发释放当前全部储能，击退强度随释放电量变化。大幅击退追猎者属于游戏夸张。", "cost":"照明持续耗电，爆发至少需要 12 电量，释放后电量清零并短暂干扰视线；关灯且不处于加速时，释放后的短暂等待结束后才缓慢回充。"}
const SKILLS := [
	{"id":"afterimage", "name":"雷痕 / Retinal Epitaph", "field":"视觉神经科学", "science":"视觉后像：强光刺激停止后，感光系统仍短暂保留旧影像。", "effect":"在闪电后保留敌人的旧屏幕位置；它不会跟随目标。强化延长后像持续时间。", "cost":"消耗 8 点体力；冷却 8 秒。"},
	{"id":"echo", "name":"还声 / The Returning Voice", "field":"声学", "science":"回声定位：发声并接收反射声波，可粗略判断距离与形状。", "effect":"发出脉冲，标亮研究记录；追猎者仍持续锁定玩家。强化延长标亮、缩短短暂听觉干扰与冷却。", "cost":"施放后有短暂听觉干扰；基础冷却 8 秒。"},
	{"id":"luminol", "name":"蓝色供词 / Luminol Confession", "field":"分析化学", "science":"鲁米诺在氧化剂与血红素催化下可发生化学发光。", "effect":"显影仍有效的普通与盐反应痕迹；暴雨会冲淡痕迹。强化延长显影、提高盐反应蓝光；游戏中的反应痕迹不等于现实检测结论。", "cost":"每次消耗一份有限试剂；冷却 8 秒。"},
	{"id":"mire", "name":"不许停步之泥 / The Unyielding Mire", "field":"材料科学与流变学", "science":"剪切增稠悬浮液在较快形变下表观黏度上升。", "effect":"铺设泥区，减缓经过的追猎者并阻止其开始冲刺；玩家低速移动时也会受阻，高速移动时不受这项减速。这些效果是游戏设定，不能作为真实流变规律；强化扩大范围并延长持续。", "cost":"玩家低速移动时也会受阻；雨水会稀释泥区，基础冷却 8 秒。"},
	{"id":"salt", "name":"盐之誓约 / Covenant of Salt", "field":"细胞生理学", "science":"渗透压来自半透膜两侧溶质浓度差。", "effect":"盐阵短暂减缓具有湿润组织的追猎者；瞬时生物脱水属于游戏夸张。强化扩大范围、延长持续；精修减少自身脱水。", "cost":"消耗体力与水分；雨水会稀释盐阵，进阶的体力代价更高。"},
	{"id":"filter", "name":"剥噪 / Spectral Absolution", "field":"数学与信号处理", "science":"傅里叶分析把复杂信号分解为不同频率成分。", "effect":"削弱雨声并保留所选频段；按 F 选择低、中或高频。敌人、脚步与雷声不受此滤波影响。强化延长持续并缩短冷却。", "cost":"其余频段的雨声信息也会减弱；基础持续 10 秒、冷却 8 秒。"},
	{"id":"daylight", "name":"蓄昼 / Captured Daylight", "field":"半导体物理", "science":"光伏效应：半导体吸收光能后产生可移动的电荷，内部电场使电荷分离，从而产生电流。闪电光不能为随身设备提供游戏表现的巨大能量。", "effect":"装备后在闪电时被动捕光，为共享电池充能；主动耗电短时加速。高速运动和大量闪电捕能属于游戏夸张。", "cost":"每次加速耗 25 共享电量，冷却 8 秒，并产生可控的视听干扰与短促步态偏移；减弱画面干扰不会取消资源代价。"},
	{"id":"pulse", "name":"乱频 / Disordered Pulse", "field":"电子学与通信工程", "science":"脉冲调制通过组织脉冲的时序、宽度或频率传递或控制信号；例如 PWM 以脉宽占周期的比例调节输出。调制本身不会让便携灯产生强力击退。", "effect":"主动切换谱灯的集中爆发／短促点射；照明仍独立控制。按次点射可击退追猎者，强力光压与噪声引发的感官紊乱属于游戏夸张。", "cost":"点射按次消耗共享电量、累积噪声；噪声产生可控的视听干扰与短促步态偏移。"}
]

# First prototype values, shared by handbook, upgrade choices and gameplay.
# Each array is ordered 基础 / 进阶 / 精修; these are not balance conclusions.
const LEVEL_VALUES := {
	"lamp": {"range":[12.0,15.0,18.0], "burst_range":[10.0,12.0,14.0], "burst_impulse":[11.0,14.0,17.0], "burst_half_angle_deg":[28.0,34.0,40.0], "blind_duration":[0.8,0.6,0.4]},
	"afterimage": {"duration":[2.5,3.5,5.0]},
	"echo": {"highlight_duration":[7.0,10.0,14.0], "deafness":[4.0,3.0,2.0], "cooldown":[8.0,7.0,6.0]},
	"luminol": {"reveal_duration":[8.0,12.0,16.0], "salt_emission":[0.6,1.2,1.8]},
	"mire": {"radius":[2.4,3.1,3.7], "duration":[11.0,14.0,17.0]},
	"salt": {"radius":[2.4,3.0,3.5], "duration":[11.0,14.0,17.0], "stamina_cost":[22.0,30.0,30.0], "dehydration":[18.0,18.0,14.0]},
	"filter": {"duration":[10.0,13.0,16.0], "cooldown":[8.0,7.0,6.0]},
	"daylight": {"capture_energy":[18.0,25.0,32.0], "boost_duration":[2.4,3.2,4.0], "boost_multiplier":[1.28,1.38,1.48]},
	"pulse": {"impulse":[4.0,5.5,7.0], "noise_gain":[13.0,10.0,8.0], "shot_energy":[8.0,8.0,8.0], "shot_interval":[0.34,0.30,0.26], "range":[12.0,15.0,18.0]}
}
const LEVEL_NAMES := ["基础", "进阶", "精修"]
const REPORTS := [
	{"id":"tower", "name":"输电塔研究报告", "location":"输电塔"},
	{"id":"dead_tree", "name":"枯树研究报告", "location":"枯树"},
	{"id":"car", "name":"废车研究报告", "location":"废车"}
]
const ARCHIVE_SCHEMA_VERSION := 1
const DEFAULT_ARCHIVE_PATH := "user://research_archive.json"

var equipped: Array[String] = ["afterimage", "echo", "mire"]:
	set(value):
		var valid: Array[String] = []
		for skill_id in value:
			if LEVEL_VALUES.has(skill_id) and skill_id != "lamp" and not valid.has(skill_id):
				valid.append(skill_id)
				if valid.size() == 3:
					break
		equipped = valid
var collected := 0
var upgrades := 0
var skill_levels: Dictionary = {}
var reduced_flashes := false
var brightness := 1.0
var game_over := false
var outcome := ""

var archive_path := DEFAULT_ARCHIVE_PATH
var archive_writable := true
var last_archive_error := ""
var _archive: Dictionary = {}

func _ready() -> void:
	var explicit_archive_path := OS.get_environment("HDF_ARCHIVE_PATH")
	if not explicit_archive_path.is_empty():
		archive_path = explicit_archive_path
	_load_archive()

func reset_run() -> void:
	collected = 0
	upgrades = 0
	skill_levels.clear()
	game_over = false
	outcome = ""
	state_changed.emit()

func skill_data(skill_id: String) -> Dictionary:
	if skill_id == "lamp":
		return LAMP
	for item in SKILLS:
		if item.id == skill_id:
			return item
	# Keep the previous API's fallback for existing callers; upgrade validation
	# separately checks identifiers and never treats an unknown ID as afterimage.
	return SKILLS[0]

func ability_level(skill_id: String) -> int:
	return clampi(int(skill_levels.get(skill_id, 1)), 1, 3)

func ability_values(skill_id: String, level: int = 0) -> Dictionary:
	if not LEVEL_VALUES.has(skill_id):
		return {}
	var index := clampi(level if level > 0 else ability_level(skill_id), 1, 3) - 1
	var values: Dictionary = {}
	for parameter in LEVEL_VALUES[skill_id]:
		values[parameter] = LEVEL_VALUES[skill_id][parameter][index]
	return values

func upgrade_options() -> Array[Dictionary]:
	var choices: Array[Dictionary] = []
	var eligible: Array[String] = ["lamp"]
	eligible.append_array(equipped)
	for skill_id in eligible:
		var level := ability_level(skill_id)
		if level >= 3:
			continue
		var data := skill_data(skill_id)
		choices.append({"id":skill_id, "name":data.name, "field":data.field, "level":level, "next_level":level + 1, "benefit":upgrade_benefit(skill_id, level + 1), "cost":upgrade_cost_summary(skill_id)})
	return choices

func upgrade_ability(skill_id: String) -> bool:
	if not LEVEL_VALUES.has(skill_id) or (skill_id != "lamp" and not equipped.has(skill_id)) or ability_level(skill_id) >= 3:
		return false
	skill_levels[skill_id] = ability_level(skill_id) + 1
	upgrades += 1
	state_changed.emit()
	return true

func upgrade_benefit(skill_id: String, level: int) -> String:
	var values := ability_values(skill_id, level)
	if values.is_empty():
		return ""
	# Compare the previous fixed level with the requested level. This remains
	# accurate when shown after confirmation, when the current level has changed.
	var previous := ability_values(skill_id, maxi(1, level - 1))
	# A level-one handbook describes its actual starting behavior, not a
	# nonexistent upgrade from level one to itself.
	if level <= 1:
		match skill_id:
			"lamp": return "照明%.0f m，爆发%.0f m；释放当前储能，视线干扰%.1f秒。" % [values.range,values.burst_range,values.blind_duration]
			"afterimage": return "后像保留%.1f秒；记录闪电时的旧位置，不追踪移动目标。" % values.duration
			"echo": return "报告标亮%.0f秒；听觉干扰%.0f秒，冷却%.0f秒。" % [values.highlight_duration,values.deafness,values.cooldown]
			"luminol": return "有效痕迹显影%.0f秒；雨水仍会冲淡痕迹。" % values.reveal_duration
			"mire": return "泥区半径%.1f m，初始持续%.0f秒；慢行的玩家也会受阻。" % [values.radius,values.duration]
			"salt": return "盐阵半径%.1f m，初始持续%.0f秒；仍有自身脱水代价。" % [values.radius,values.duration]
			"filter": return "雨声滤波持续%.0f秒，冷却%.0f秒；保留所选频段。" % [values.duration,values.cooldown]
			"daylight": return "每次最多捕光%.0f电量，电池上限100；加速%.1f秒，移动速度提高%.0f%%。" % [values.capture_energy,values.boost_duration,(values.boost_multiplier-1.0)*100.0]
			"pulse": return "点射范围%.0f m，间隔%.2f秒；单次噪声%.0f点。" % [values.range,values.shot_interval,values.noise_gain]
	match skill_id:
		"lamp":
			return "照明%.0f→%.0f m，爆发%.0f→%.0f m；爆发范围扩大、击退增强，视线干扰%.1f→%.1f秒。" % [previous.range, values.range, previous.burst_range, values.burst_range, previous.blind_duration, values.blind_duration]
		"afterimage":
			return "后像保留%.1f→%.1f秒；更久看清闪电时的旧位置，仍不追踪移动目标。" % [previous.duration, values.duration]
		"echo":
			return "报告标亮%.0f→%.0f秒；听觉干扰%.0f→%.0f秒，冷却%.0f→%.0f秒。" % [previous.highlight_duration, values.highlight_duration, previous.deafness, values.deafness, previous.cooldown, values.cooldown]
		"luminol":
			return "有效痕迹显影%.0f→%.0f秒；盐反应痕迹的蓝光更清楚。" % [previous.reveal_duration, values.reveal_duration]
		"mire":
			return "泥区半径%.1f→%.1f m，初始持续%.0f→%.0f秒；覆盖更大区域。" % [previous.radius, values.radius, previous.duration, values.duration]
		"salt":
			var dehydration_benefit := "自身脱水减轻。" if values.dehydration < previous.dehydration else ""
			return "盐阵半径%.1f→%.1f m，初始持续%.0f→%.0f秒。%s" % [previous.radius, values.radius, previous.duration, values.duration, dehydration_benefit]
		"filter":
			return "雨声滤波持续%.0f→%.0f秒，冷却%.0f→%.0f秒；更久保留所选频段。" % [previous.duration, values.duration, previous.cooldown, values.cooldown]
		"daylight":
			return "每次最多捕光%.0f→%.0f电量，电池上限100；加速%.1f→%.1f秒，提速更明显。" % [previous.capture_energy, values.capture_energy, previous.boost_duration, values.boost_duration]
		"pulse":
			return "点射%.0f→%.0f m，间隔%.2f→%.2f秒；击退增强，单次噪声更少。" % [previous.range, values.range, previous.shot_interval, values.shot_interval]
	return ""

func upgrade_cost_summary(skill_id: String) -> String:
	var values := ability_values(skill_id, mini(3, ability_level(skill_id) + 1))
	if values.is_empty():
		return ""
	match skill_id:
		"lamp":
			return "爆发至少12电量，释放后清零；照明持续耗电。"
		"afterimage":
			return "需近期闪电；耗8体力，冷却8秒；后像不会跟随目标。"
		"echo":
			return "施放后短暂听觉受扰，冷却%.0f秒；奶蛙仍会追踪。" % values.cooldown
		"luminol":
			return "每次耗一份有限试剂，冷却8秒；雨水仍会冲淡痕迹。"
		"mire":
			return "慢行的玩家也会受阻；雨水会稀释，冷却8秒。"
		"salt":
			return "耗%.0f体力；仍有脱水和暴雨稀释代价，冷却8秒。" % values.stamina_cost
		"filter":
			return "未选频段的雨声信息减弱；敌人、脚步和雷声保持原样。"
		"daylight":
			return "每次加速耗25共享电量，冷却8秒；有短促视听与步态干扰。"
		"pulse":
			return "每次点射耗%.0f电量；噪声仍累积，干扰视听与步态。" % values.shot_energy
	return ""

func set_archive_path(path: String) -> void:
	# Also used by isolated contract tests; production keeps DEFAULT_ARCHIVE_PATH.
	archive_path = path
	_load_archive()

func record_knowledge(skill_id: String) -> bool:
	if not LEVEL_VALUES.has(skill_id):
		return false
	var data := skill_data(skill_id)
	return _record_entry("knowledge", skill_id, {"name":data.name, "field":data.field, "science":data.science, "effect":data.effect})

func record_report(report_id: String) -> bool:
	for report in REPORTS:
		if report.id == report_id:
			return _record_entry("reports", report_id, {"name":report.name, "location":report.location})
	return false

func record_fusion(fusion_id: String, description: String) -> bool:
	if fusion_id.is_empty() or description.is_empty():
		return false
	return _record_entry("fusions", fusion_id, {"description":description})

func archive_lines() -> Array[String]:
	var lines: Array[String] = ["研究档案跨局保留知识与发现；能力等级每局重新成长。"]
	lines.append("\n知识 · %d" % _archive.get("knowledge", {}).size())
	for key in _archive.get("knowledge", {}):
		var entry: Variant = _archive.knowledge[key]
		if entry is Dictionary:
			# Known ability descriptions follow the current rules without rewriting
			# the saved discovery or its metadata. Unknown entries keep their text.
			var display_entry: Dictionary = skill_data(str(key)) if LEVEL_VALUES.has(str(key)) else entry
			lines.append("%s｜%s\n%s\n%s" % [display_entry.get("name", key), display_entry.get("field", ""), display_entry.get("science", ""), display_entry.get("effect", "")])
	lines.append("\n报告 · %d/3" % _known_report_count())
	for report in REPORTS:
		if _archive.get("reports", {}).has(report.id):
			lines.append("已收录：%s（%s）" % [report.name, report.location])
	lines.append("\n融合 · %d" % _archive.get("fusions", {}).size())
	for key in _archive.get("fusions", {}):
		var entry: Variant = _archive.fusions[key]
		if entry is Dictionary:
			lines.append(String(entry.get("description", key)))
	if not last_archive_error.is_empty():
		lines.append("\n档案暂未保存：%s。原文件保留，本局成长仍可使用。" % last_archive_error)
	return lines

func _known_report_count() -> int:
	var count := 0
	for report in REPORTS:
		if _archive.get("reports", {}).has(report.id):
			count += 1
	return count

func _empty_archive() -> Dictionary:
	return {"schema_version":ARCHIVE_SCHEMA_VERSION, "knowledge":{}, "reports":{}, "fusions":{}}

func _load_archive() -> void:
	_archive = _empty_archive()
	archive_writable = true
	last_archive_error = ""
	if not FileAccess.file_exists(archive_path):
		return
	var file := FileAccess.open(archive_path, FileAccess.READ)
	if file == null:
		_block_archive("无法读取档案（错误 %d）" % FileAccess.get_open_error())
		return
	var text := file.get_as_text()
	file.close()
	var parser := JSON.new()
	if parser.parse(text) != OK or not parser.data is Dictionary:
		_block_archive("档案内容损坏，已停止写入以保留恢复材料")
		return
	var loaded: Dictionary = parser.data
	if loaded.get("schema_version", -1) != ARCHIVE_SCHEMA_VERSION:
		_block_archive("档案版本尚不支持，已停止写入")
		return
	for section in ["knowledge", "reports", "fusions"]:
		if not loaded.get(section) is Dictionary:
			_block_archive("档案结构异常，已停止写入以保留恢复材料")
			return
	# Keep the full root and dictionaries, including unrelated future metadata.
	_archive = loaded

func _block_archive(reason: String) -> void:
	archive_writable = false
	last_archive_error = reason

func _record_entry(section: String, entry_id: String, data: Dictionary) -> bool:
	if _archive.is_empty():
		_archive = _empty_archive()
	if _archive[section].has(entry_id):
		# A transient failed write can be retried by the next real discovery of
		# the same knowledge without requiring a second, unrelated entry.
		return _save_archive() if archive_writable and not last_archive_error.is_empty() else false
	var entry := data.duplicate(true)
	entry["first_recorded_at"] = Time.get_datetime_string_from_system(false, true)
	_archive[section][entry_id] = entry
	var persisted := _save_archive()
	state_changed.emit()
	return persisted

func _save_archive() -> bool:
	if not archive_writable:
		return false
	# Write and flush a sibling first. A failed open/write/rename never truncates
	# an existing archive; a rename failure leaves the temporary file recoverable.
	var temporary_path := archive_path + ".tmp"
	var file := FileAccess.open(temporary_path, FileAccess.WRITE)
	if file == null:
		last_archive_error = "无法创建档案临时文件（错误 %d）" % FileAccess.get_open_error()
		return false
	file.store_string(JSON.stringify(_archive, "\t"))
	file.flush()
	var write_error := file.get_error()
	file.close()
	if write_error != OK:
		last_archive_error = "档案写入失败（错误 %d）" % write_error
		return false
	var rename_error := DirAccess.rename_absolute(temporary_path, archive_path)
	if rename_error != OK:
		last_archive_error = "档案替换失败（错误 %d）" % rename_error
		return false
	last_archive_error = ""
	return true
