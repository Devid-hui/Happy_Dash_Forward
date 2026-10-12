extends Node

var world
var discovered: Array[String] = []

const DESCRIPTIONS := {
	"echo_filter": "谱化回声｜条件：剥噪生效时发出还声。频率滤波降低雨噪，帮助辨认回声；奶龙仍持续锁定玩家。滤掉的同频线索也会变弱。",
	"echo_afterimage": "过去与现在｜条件：闪电后保存雷痕，再于残像有效时还声。视觉后像保留旧屏幕位置，还声标亮研究记录；残像不追踪目标，奶龙仍持续锁定玩家。",
	"echo_mire": "诱导沉陷｜条件：先布置泥浆再还声。奶龙始终追踪玩家，还声提供位置线索，泥区减缓经过的敌人并阻止其开始冲刺；泥浆同样会拖慢玩家并被雨水稀释。",
	"salt_luminol": "盐渍证言｜条件：湿润追猎者进入盐阵并留下反应性痕迹，再使用鲁米诺。渗透压是现实依据，瞬时生物脱水属于梦境夸张；雨水会稀释盐阵并冲淡痕迹，试剂有限。"
}

func setup(game_world) -> void:
	world = game_world

func check_trigger(skill_id: String) -> String:
	var player = world.player
	var conditions := {
		"echo_filter": skill_id == "echo" and player.filter_time > 0.0,
		"echo_afterimage": skill_id == "echo" and player.afterimage_time > 0.0,
		"echo_mire": skill_id == "echo" and world.fields.any(func(field): return field.kind == "mire" and field.time > 0.0),
		"salt_luminol": skill_id == "luminol" and world.traces.any(func(trace): return trace.salt_reactive and trace.time > 0.0)
	}
	var found: Array[String] = []
	var equipped: Array = GameState.equipped
	for pair_id in conditions:
		var pair_parts: PackedStringArray = pair_id.split("_")
		if equipped.has(pair_parts[0]) and equipped.has(pair_parts[1]) and conditions[pair_id] and not discovered.has(pair_id):
			discovered.append(pair_id)
			found.append(DESCRIPTIONS[pair_id])
	return "\n".join(found)
