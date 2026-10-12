extends SceneTree
const Visual := preload("res://scripts/enemies/hunter_visual.gd")
func _initialize() -> void:
	call_deferred("run_benchmark")
func run_benchmark() -> void:
	var builder := Visual.new()
	var start := Time.get_ticks_usec()
	for i in range(6):
		var model := Node3D.new()
		builder._build_model(model)
		model.free()
	var uncached_ms := (Time.get_ticks_usec()-start)/1000.0
	builder.free()
	var cold := Visual.new()
	start = Time.get_ticks_usec()
	root.add_child(cold)
	var cold_ms := (Time.get_ticks_usec()-start)/1000.0
	cold.free()
	start = Time.get_ticks_usec()
	for i in range(6):
		var model := Visual.new()
		root.add_child(model)
		model.free()
	var shared_ms := (Time.get_ticks_usec()-start)/1000.0
	assert(Visual.build_count == 1)
	print("MODEL CACHE BENCHMARK: six uncached %.2f ms; cold cache %.2f ms; six shared %.2f ms" % [uncached_ms,cold_ms,shared_ms])
	quit()
