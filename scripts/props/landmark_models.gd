extends RefCounted
const ORGANIC := preload("res://scripts/art/organic_mesh.gd")
const FOREST := preload("res://scripts/art/forest_detail.gd")
static var _scene_cache: Dictionary = {}

static func material(color: Color) -> StandardMaterial3D:
	var m := StandardMaterial3D.new(); m.albedo_color = color; m.roughness = .58; return m

static func box(root: Node3D, label: String, size: Vector3, position: Vector3, m: Material) -> MeshInstance3D:
	var mesh := BoxMesh.new(); mesh.size = size
	var part := ORGANIC.part(root,mesh,m,label); part.position = position; return part

static func beam(root: Node3D, start: Vector3, end: Vector3, radius: float, m: Material) -> void:
	var mesh := CylinderMesh.new(); mesh.top_radius = radius; mesh.bottom_radius = radius
	mesh.height = start.distance_to(end); mesh.radial_segments = 8
	var part := ORGANIC.part(root,mesh,m,"Beam"); part.position = (start+end)*.5; part.quaternion = Quaternion(Vector3.UP,(end-start).normalized())

static func _flatten(node: Node3D, root: Node3D, inherited: Transform3D = Transform3D.IDENTITY) -> void:
	var composed := inherited*node.transform
	for child in node.get_children().duplicate():
		if child is MeshInstance3D:
			child.owner = null
			node.remove_child(child); root.add_child(child,true); child.transform = composed*child.transform
		elif child is Node3D: _flatten(child,root,composed)

static func populate(root: Node3D, path: String, transform_value: Transform3D = Transform3D.IDENTITY) -> void:
	if not _scene_cache.has(path): _scene_cache[path] = load(path) as PackedScene
	var imported := (_scene_cache[path] as PackedScene).instantiate() as Node3D
	assert(imported != null,"Refined landmark asset must import successfully")
	_flatten(imported,root,transform_value); imported.free()
	root.set_meta("refined_asset",path)

static func tower(root: Node3D) -> void:
	populate(root,"res://assets/refined/power_tower.glb")

static func car(root: Node3D) -> void:
	populate(root,"res://assets/refined/abandoned_car.glb")

static func dead_tree(root: Node3D) -> void:
	var tree := FOREST.build(1,true,FOREST.bark_material())
	tree.name = "DetailedDeadTree"
	tree.scale = Vector3.ONE * (8.2/9.6079)
	var duplicate_collision := tree.get_node_or_null("TreeTrunkCollision")
	if duplicate_collision != null: duplicate_collision.free()
	root.add_child(tree)
	box(root,"WarningPlaque",Vector3(.65,.43,.07),Vector3(0,1.67,-.49),material(Color(.24,.14,.071)))
	root.set_meta("refined_asset","res://assets/refined/environment/dead_tree_2.glb")
