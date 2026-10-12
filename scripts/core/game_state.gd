extends Node

signal state_changed

const SKILLS := [
	{"id":"afterimage", "name":"雷痕 / Retinal Epitaph", "field":"视觉神经科学", "science":"视觉后像：强光刺激停止后，感光系统仍短暂保留旧影像。", "effect":"在闪电后保留敌人的旧屏幕位置；它不会跟随目标。Lv.2 延长持续时间。", "cost":"消耗 8 点体力；冷却 8 秒。"},
	{"id":"echo", "name":"还声 / The Returning Voice", "field":"声学", "science":"回声定位：发声并接收反射声波，可粗略判断距离与形状。", "effect":"发出脉冲，标亮研究记录；追猎者仍持续锁定玩家。", "cost":"冷却 8 秒。"},
	{"id":"luminol", "name":"蓝色供词 / Luminol Confession", "field":"分析化学", "science":"鲁米诺在氧化剂与血红素催化下可发生化学发光。", "effect":"显影仍有效的普通与盐反应痕迹；暴雨会冲淡痕迹。Lv.2 强化盐反应痕迹的蓝光。", "cost":"每次消耗一份有限试剂；冷却 8 秒。"},
	{"id":"mire", "name":"不许停步之泥 / The Unyielding Mire", "field":"材料科学与流变学", "science":"剪切增稠悬浮液在较快形变下表观黏度上升。", "effect":"铺设泥区；缓慢通过者受阻，高速通过者受影响较小。", "cost":"规则对玩家与追猎者相同。"},
	{"id":"salt", "name":"盐之誓约 / Covenant of Salt", "field":"细胞生理学", "science":"渗透压来自半透膜两侧溶质浓度差。", "effect":"盐阵短暂减缓具有湿润组织的追猎者。", "cost":"消耗体力与水分；雨水会稀释盐阵。"},
	{"id":"filter", "name":"剥噪 / Spectral Absolution", "field":"数学与信号处理", "science":"傅里叶分析把复杂信号分解为不同频率成分。", "effect":"10 秒内削弱雨声，保留所选频段；按 F 选择低、中或高频。敌人、脚步与雷声不受此滤波影响。", "cost":"其余频段的雨声信息也会减弱；冷却 8 秒。"}
]

var equipped: Array[String] = ["afterimage", "echo", "mire"]
var collected := 0
var upgrades := 0
var skill_levels: Dictionary = {}
var reduced_flashes := false
var brightness := 1.0
var game_over := false
var outcome := ""

func reset_run() -> void:
	collected = 0
	upgrades = 0
	skill_levels.clear()
	game_over = false
	outcome = ""
	state_changed.emit()

func skill_data(skill_id: String) -> Dictionary:
	for item in SKILLS:
		if item.id == skill_id:
			return item
	return SKILLS[0]
