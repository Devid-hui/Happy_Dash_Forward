extends "res://tests/high_fidelity_asset_preview.gd"
const BOOK := preload("res://scripts/props/research_book.gd")

func _ready() -> void:
	views = ["TOWER_CONNECTIONS","REPORT_PAPER","TOWER_NIGHT","REPORT_NIGHT"]
	super._ready()

func _switch(index: int) -> void:
	for child in root.get_children(): child.free()
	var ground := MeshInstance3D.new(); var plane := PlaneMesh.new(); plane.size = Vector2(40,40)
	ground.mesh = plane; var material := StandardMaterial3D.new(); material.albedo_color = Color(.075,.086,.067); material.roughness = .48
	ground.material_override = material; root.add_child(ground)
	var dark := index >= 2
	rain.emitting = dark; environment.ambient_light_energy = .11 if dark else .72
	key.light_energy = .16 if dark else 1.1
	environment.fog_enabled = dark; environment.fog_density = .006 if dark else 0
	spotlight.light_energy = 14.0 if dark else 0.0
	if index in [0,2]:
		LANDMARKS.tower(root)
		camera.look_at_from_position(Vector3(3.1,4.1,4.7),Vector3(0,3.4,0))
		spotlight.look_at_from_position(Vector3(2.5,4.1,3.5),Vector3(0,3.3,0))
		if index == 2:
			camera.look_at_from_position(Vector3(12,11,18),Vector3(0,7.5,0))
			spotlight.look_at_from_position(Vector3(5,8,9),Vector3(0,8,0))
	else:
		var book := BOOK.new(); root.add_child(book); book.position.y = 1.457
		var crate := MeshInstance3D.new(); var cube := BoxMesh.new(); cube.size = Vector3(.65,1.0,.42); crate.mesh = cube; crate.position.y = .5
		var wood := StandardMaterial3D.new(); wood.albedo_color = Color(.15,.12,.085); wood.roughness = .85; crate.material_override = wood; root.add_child(crate)
		camera.look_at_from_position(Vector3(.65,1.82,-1.06),Vector3(0,1.50,0))
		spotlight.look_at_from_position(Vector3(.45,1.9,-.8),Vector3(0,1.5,0))
