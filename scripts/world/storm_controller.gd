extends Node
signal lightning_started
const FREQUENCY_MULTIPLIER := 2.5
var world
var lightning: OmniLight3D
var bolt: MeshInstance3D
var strike_position := Vector3.ZERO
var lightning_energy := 0.0
var flash_timer := 0.0
var next_flash := 10.0 / FREQUENCY_MULTIPLIER

func setup(game_world) -> void:
	world = game_world
	lightning = OmniLight3D.new()
	lightning.name = "Lightning"
	lightning.light_color = Color(.76,.84,1.0)
	lightning.omni_range = 230.0
	lightning.omni_attenuation = .6
	lightning.shadow_enabled = true
	lightning.light_volumetric_fog_energy = .02
	lightning.light_energy = 0.0
	world.add_child(lightning)
	bolt = MeshInstance3D.new()
	bolt.name = "LightningBolt"
	bolt.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	var material := StandardMaterial3D.new()
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	material.cull_mode = BaseMaterial3D.CULL_DISABLED
	material.albedo_color = Color(.86,.92,1)
	material.emission_enabled = true
	material.emission = Color(.7,.82,1)
	material.emission_energy_multiplier = 4.0
	bolt.material_override = material
	bolt.visible = false
	world.add_child(bolt)

func _ribbon(surface: SurfaceTool, start: Vector3, end: Vector3, width: float) -> void:
	for axis in [Vector3.RIGHT,Vector3.FORWARD]:
		var offset: Vector3 = axis*width
		for vertex in [start-offset,start+offset,end-offset,start+offset,end+offset,end-offset]:
			surface.add_vertex(vertex)

func trigger_strike(position: Vector3) -> void:
	strike_position = Vector3(position.x,0,position.z)
	# 光源跟随地图落雷点，不跟随玩家；背光面由法线和阴影自然保持暗色。
	lightning.position = strike_position+Vector3(0,18,0)
	var surface := SurfaceTool.new()
	surface.begin(Mesh.PRIMITIVE_TRIANGLES)
	var last := Vector3(0,48,0)
	for i in range(1,13):
		var point := Vector3(randf_range(-2.0,2.0),48-i*4.0,randf_range(-2.0,2.0)) if i < 12 else Vector3.ZERO
		_ribbon(surface,last,point,.09)
		if i % 3 == 0:
			_ribbon(surface,point,point+Vector3(randf_range(-6,6),-5,randf_range(-6,6)),.04)
		last = point
	bolt.mesh = surface.commit()
	bolt.position = strike_position
	bolt.visible = true
	flash_timer = .42
	lightning_energy = .28 if GameState.reduced_flashes else 1.8
	lightning.light_energy = lightning_energy*100.0*GameState.brightness
	lightning_started.emit()

func _process(delta: float) -> void:
	if world.paused: return
	if flash_timer > 0.0:
		flash_timer = maxf(0.0,flash_timer-delta)
		var falloff := 1.0 if flash_timer > .17 else flash_timer/.17
		lightning_energy = falloff*(.28 if GameState.reduced_flashes else 1.8)
		lightning.light_energy = lightning_energy*100.0*GameState.brightness
		if flash_timer <= 0.0:
			bolt.visible = false
			lightning.light_energy = 0.0
	else:
		next_flash -= delta
		if next_flash <= 0.0:
			# Accessibility changes the visible flash, retaining capture opportunities.
			next_flash = randf_range(8,16)/FREQUENCY_MULTIPLIER
			trigger_strike(Vector3(randf_range(-85,85),0,randf_range(-85,85)))
