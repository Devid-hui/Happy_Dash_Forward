extends Node3D
var cover_material: StandardMaterial3D
var interaction_label: Label3D

func _box(label: String, size: Vector3, position: Vector3, material: Material) -> void:
	var part := MeshInstance3D.new()
	part.name = label
	var mesh := BoxMesh.new(); mesh.size = size
	part.mesh = mesh; part.position = position; part.material_override = material
	add_child(part)

func _ready() -> void:
	name = "ResearchBook"
	cover_material = StandardMaterial3D.new()
	cover_material.albedo_color = Color(.13,.28,.23)
	cover_material.roughness = .8
	cover_material.emission_enabled = true
	cover_material.emission = Color(.055,.12,.09)
	cover_material.emission_energy_multiplier = .5
	var paper := StandardMaterial3D.new()
	paper.albedo_color = Color(.72,.67,.48)
	var gold := StandardMaterial3D.new()
	gold.albedo_color = Color(.65,.49,.18)
	_box("Pages",Vector3(.60,.84,.12),Vector3.ZERO,paper)
	_box("FrontCover",Vector3(.68,.92,.035),Vector3(0,0,-.078),cover_material)
	_box("BackCover",Vector3(.68,.92,.035),Vector3(0,0,.078),cover_material)
	_box("Spine",Vector3(.065,.92,.19),Vector3(-.32,0,0),cover_material)
	for i in range(8):
		_box("PageEdge",Vector3(.61,.012,.002),Vector3(0,-.35+i*.10,-.063),gold)
	for y in [-.30,.30]:
		_box("CoverRule",Vector3(.49,.018,.012),Vector3(0,y,-.101),gold)
	var title := Label3D.new()
	title.name = "CoverTitle"; title.text = "学院研究\nFIELD NOTES"
	title.font_size = 38; title.pixel_size = .0019
	title.position = Vector3(0,.06,-.106)
	title.modulate = Color(.82,.76,.49)
	title.rotation.y = PI
	add_child(title)
	var tag := Label3D.new()
	tag.name = "InteractionLabel"; tag.text = "研究记录"
	interaction_label = tag
	tag.font_size = 28; tag.pixel_size = .003
	tag.position.y = .73
	tag.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	tag.visibility_range_end = 9.0
	add_child(tag)

func highlight() -> void:
	cover_material.emission_energy_multiplier = 1.3

func _process(_delta: float) -> void:
	var player := get_tree().get_first_node_in_group("player") as Node3D
	if player != null:
		interaction_label.text = "研究记录 · E 收集" if global_position.distance_to(player.global_position) < 3.0 else "研究记录"
