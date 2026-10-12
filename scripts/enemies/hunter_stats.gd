extends Resource
# 配置模板可共享，但每个敌人保存独立副本与运行时血量。
@export var move_speed: float = 3.2
@export var max_health: float = 100.0
@export var charge_speed: float = 7.8
@export var charge_trigger_distance: float = 8.0
@export var charge_duration: float = 2.0
@export var charge_rest_duration: float = 8.0
@export var charge_warning_duration: float = 0.8
@export var attack_range: float = 1.35
@export var attack_interval: float = 1.4
@export var recycle_distance: float = 28.0
@export var spawn_min_distance: float = 16.0
@export var spawn_max_distance: float = 24.0
