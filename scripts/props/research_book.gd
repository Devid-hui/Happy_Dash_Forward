extends Node3D
const LANDMARKS := preload("res://scripts/props/landmark_models.gd")
var cover_material: StandardMaterial3D
var interaction_label: Label3D
var highlight_time := 0.0

func _ready() -> void:
	name = "ResearchBook"
	# Authoring front faces Blender -Y; rotate so the runtime front faces local -Z.
	LANDMARKS.populate(self,"res://assets/refined/research_report.glb",Transform3D(Basis(Vector3.UP,PI),Vector3.ZERO))
	var front := get_node("FrontCover") as MeshInstance3D
	var authored := front.mesh.surface_get_material(0) as StandardMaterial3D
	assert(authored != null,"research cloth cover must retain its native PBR material")
	cover_material = authored.duplicate() as StandardMaterial3D
	cover_material.emission_enabled = true
	cover_material.emission = Color(.055,.12,.09); cover_material.emission_energy_multiplier = .5
	for part_name in ["FrontCover","BackCover","Spine"]:
		var part := get_node(part_name) as MeshInstance3D; part.material_override = cover_material
	var title := Label3D.new(); title.name = "CoverTitle"; title.text = "学院研究"
	title.font_size = 36; title.pixel_size = .0019; title.position = Vector3(0,.32,-.019)
	title.modulate = Color(.82,.76,.49); title.rotation.y = PI; add_child(title)
	var tag := Label3D.new(); tag.name = "InteractionLabel"; tag.text = "研究记录"; interaction_label = tag
	tag.font_size = 28; tag.pixel_size = .003; tag.position.y = .73
	tag.billboard = BaseMaterial3D.BILLBOARD_ENABLED; tag.visibility_range_end = 9.0; add_child(tag)

func highlight(duration: float = 7.0) -> void:
	highlight_time = maxf(highlight_time,duration); cover_material.emission_energy_multiplier = 1.3

func _process(delta: float) -> void:
	if highlight_time > 0.0:
		highlight_time = maxf(0.0,highlight_time-delta)
		if highlight_time <= 0.0: cover_material.emission_energy_multiplier = .5
	var player := get_tree().get_first_node_in_group("player") as Node3D
	if player != null:
		interaction_label.text = "研究记录 · E 收集" if global_position.distance_to(player.global_position) < 3.0 else "研究记录"
