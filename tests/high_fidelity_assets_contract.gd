extends Node
# Geometry/API guards only. Visual acceptance is explicitly a separate human review.
const EQUIPMENT := preload("res://scripts/player/field_equipment.gd")
const LANDMARKS := preload("res://scripts/props/landmark_models.gd")
func _ready() -> void:
	call_deferred("run_contract")

func triangles(root: Node) -> int:
	var total := 0
	for instance in root.find_children("*","MeshInstance3D",true,false):
		var mesh: Mesh = instance.mesh
		for i in range(mesh.get_surface_count()):
			var a := mesh.surface_get_arrays(i)
			if not a.is_empty():
				total += int(a[Mesh.ARRAY_INDEX].size()/3) if not a[Mesh.ARRAY_INDEX].is_empty() else int(a[Mesh.ARRAY_VERTEX].size()/3)
	return total

func run_contract() -> void:
	var manifest: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://source_assets/COMMERCIAL_MODEL_MANIFEST.json"))
	assert(manifest.quality_status == "candidate pending visual acceptance")
	assert(manifest.assets.field_equipment.source_triangles >= 600000)
	assert(manifest.assets.abandoned_car.source_triangles >= 1000000)
	var camera := Camera3D.new(); add_child(camera)
	var eq := EQUIPMENT.new(); camera.add_child(eq); eq.setup(camera)
	assert(triangles(eq.asset) > 180000)
	assert(eq.right_skeleton.get_bone_count() >= 17 and eq.left_skeleton.get_bone_count() >= 17)
	for name in ["OpticalLensLayer0","OpticalLensLayer1","OpticalLensLayer2","CoatedOpticalLens"]:
		var layer := eq.asset.find_child(name,true,false) as MeshInstance3D
		assert(layer != null)
		var material := layer.mesh.surface_get_material(0) as StandardMaterial3D
		assert(material != null and material.transparency != BaseMaterial3D.TRANSPARENCY_DISABLED,"the authored lens stack uses transparent native materials")
	var finger := eq.right_skeleton.find_bone("RightGripIndex2")
	var neutral := eq.right_skeleton.get_bone_pose_rotation(finger)
	eq.trigger("flash"); eq.tick(.25)
	assert(eq.support.visible and not eq.right_skeleton.get_bone_pose_rotation(finger).is_equal_approx(neutral))
	eq.tick(1); assert(not eq.support.visible and eq.right_skeleton.get_bone_pose_rotation(finger).is_equal_approx(neutral))
	var car := Node3D.new(); LANDMARKS.car(car); add_child(car)
	assert(triangles(car) > 250000)
	assert(car.find_children("Wheel*","MeshInstance3D",true,false).size() == 4)
	for name in ["CompleteSeatsAndBelts","AnalogInstrumentCluster","SteeringRim","TransmissionTunnel","WindshieldWipers","CompleteRunningGear","DoorSeamLines","CrackedWindshield"]:
		assert(car.find_child(name,true,false) != null,"detailed vehicle structure missing: "+name)
	assert(car.find_children("GeometricTyreTread*","MeshInstance3D",true,false).size() == 4)
	var glass := car.find_child("FrontWindshield",true,false) as MeshInstance3D
	assert((glass.mesh.surface_get_material(0) as StandardMaterial3D).transparency != BaseMaterial3D.TRANSPARENCY_DISABLED)
	print("HIGH FIDELITY GEOMETRY/API GUARDS PASS: source budgets, native runtime meshes, transparent layered optics, actual grip bones, complete vehicle/tread/interior. VISUAL ACCEPTANCE REMAINS PENDING.")
	get_tree().quit()
