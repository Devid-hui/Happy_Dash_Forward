extends Node3D
const EQUIPMENT := preload("res://scripts/player/field_equipment.gd")
# Reference from the unmodified MakeHuman OBJ joint-r marker centroids, scaled to metres.
const SOURCE_RIGHT_ROOT_TRIPLE_PRODUCT := 7.826859546125192e-05
var checks := 0
var max_wrist_angle := 0.0
var failures: Array[String] = []
func _check(value: bool, message: String) -> void:
	checks += 1
	if not value:
		failures.append(message)
		push_error(message)
func _wrist_angle(skeleton: Skeleton3D,prefix: String) -> float:
	var fore := skeleton.get_bone_global_pose(skeleton.find_bone(prefix+"ForeArm"))
	var wrist := skeleton.get_bone_global_pose(skeleton.find_bone("wrist"))
	var palm := skeleton.get_bone_global_pose(skeleton.find_bone("palm"))
	return rad_to_deg((wrist.origin-fore.origin).normalized().angle_to(palm.basis.y.normalized()))
func _chirality(skeleton: Skeleton3D,prefix: String) -> float:
	var roots: Array[Vector3] = []
	for landmark in ["wrist",prefix+"Index1",prefix+"Little1",prefix+"Thumb1"]:
		roots.append(skeleton.to_global(skeleton.get_bone_global_pose(skeleton.find_bone(landmark)).origin))
	return (roots[1]-roots[0]).cross(roots[2]-roots[0]).dot(roots[3]-roots[0])
func _check_handedness(equipment: Node3D) -> void:
	# The runtime wrist anchor is 18 mm proximal to the source marker. Its
	# nonzero signed volume preserves the source sign through proper rotations.
	var lower_bound := absf(SOURCE_RIGHT_ROOT_TRIPLE_PRODUCT)*.25
	_check(_chirality(equipment.right_skeleton,"RightGrip")>lower_bound,"runtime right palm must preserve source-right handedness, including node transforms")
	_check(_chirality(equipment.left_skeleton,"LeftSupport") < -lower_bound,"runtime left palm must have the opposite signed root volume")
func _ready() -> void:
	var equipment := EQUIPMENT.new(); add_child(equipment); equipment.setup(self)
	_check_handedness(equipment)
	for found in equipment.support.find_children("*","MeshInstance3D",true,false):
		var mesh: MeshInstance3D = found
		for surface in mesh.mesh.get_surface_count():
			var pigment := mesh.get_active_material(surface) as StandardMaterial3D
			if pigment != null and pigment.resource_name.ends_with("left continuous pigment"):
				_check(pigment.vertex_color_use_as_albedo and not pigment.vertex_color_is_srgb,"left skin and nail surfaces must use the same linear pigment multiplication")
	var barrel_forward: Vector3 = (equipment.lamp.global_basis*Vector3.FORWARD).normalized()
	for thumb_name in ["LeftSupportThumb1","LeftSupportThumb2","LeftSupportThumb3"]:
		var thumb_bone: int = equipment.left_skeleton.find_bone(thumb_name)
		var segment_forward: Vector3 = (equipment.left_skeleton.global_basis*equipment.left_skeleton.get_bone_global_pose(thumb_bone).basis.y).normalized()
		_check(segment_forward.dot(barrel_forward)>0.0,"support thumb must extend toward the muzzle along the entire chain, not fold back: %s projection=%s" % [thumb_name,segment_forward.dot(barrel_forward)])
	for hand in [equipment.right_skeleton,equipment.left_skeleton]:
		var thumb_axis: Vector3 = equipment._thumb_axes[hand]
		_check(absf(thumb_axis.length()-1.0)<.0001,"source thumb hinge remains a unit direction")
		_check(absf(thumb_axis.dot(Vector3.UP))<.0001,"either thumb flexes perpendicular to its own phalanx, without axial twisting")
	for pair in [[equipment.right_skeleton,"RightGrip"],[equipment.left_skeleton,"LeftSupport"]]:
		var axes: Dictionary = equipment._finger_axes[pair[0]]
		_check(axes.size() == 12,"all four three-joint fingers retain individual authored hinges")
		for bone_name in axes:
			var axis: Vector3 = axes[bone_name]
			_check(absf(axis.length()-1.0)<.0001,"authored finger hinge is a unit direction")
			_check(absf(axis.dot(Vector3.UP))<.0001,"each finger hinge is perpendicular to its own longitudinal bone axis")
		var angle := _wrist_angle(pair[0],pair[1])
		_check(angle < 35.0,"authored palm must align with its own forearm before runtime IK")
		print("HAND REST WRIST ",pair[1]," degrees=",angle)
	for action in ["flash","shot","luminol","salt","mud","mode","boost"]:
		for sample in range(11):
			equipment.trigger(action)
			equipment.tick(equipment.action_duration*float(sample)/10.0,Vector2(.4,.7),sample%2 == 0)
			_check_handedness(equipment)
			for pair in [[equipment.right_skeleton,"RightGrip"],[equipment.left_skeleton,"LeftSupport"]]:
				var angle := _wrist_angle(pair[0],pair[1]);max_wrist_angle=maxf(max_wrist_angle,angle)
				_check(is_finite(angle) and angle<55.0,"action must not reconstruct the rejected 66-75 degree folded wrist: %s sample=%s hand=%s angle=%s" % [action,sample,pair[1],angle])
				if pair[1] == "RightGrip" or (equipment.support.visible and equipment._support_deployment > .999):
					var arm: Skeleton3D = pair[0]
					var shoulder := equipment.asset.to_local(arm.to_global(arm.get_bone_global_pose(arm.find_bone(pair[1]+"UpperArm")).origin))
					var elbow := equipment.asset.to_local(arm.to_global(arm.get_bone_global_pose(arm.find_bone(pair[1]+"ForeArm")).origin))
					var wrist := equipment.asset.to_local(arm.to_global(arm.get_bone_global_pose(arm.find_bone("wrist")).origin))
					_check(elbow.y < minf(shoulder.y,wrist.y)-.01,"held arm must fall from wrist to elbow and rise from elbow to shoulder: %s sample=%s hand=%s heights=%s" % [action,sample,pair[1],[shoulder.y,elbow.y,wrist.y]])
			if action == "salt" and sample == 5:
				var thumb_index: int = equipment.left_skeleton.find_bone("LeftSupportThumb2")
				var q: Array = equipment._tool_poses.salt["LeftSupportThumb2"]
				var expected_thumb: Quaternion = equipment._left_neutral[thumb_index]*Quaternion(q[0],q[1],q[2],q[3]).normalized()
				var actual_thumb: Quaternion = equipment.left_skeleton.get_bone_pose_rotation(thumb_index)
				# acos(dot) gives a false nonzero angle for identical single-precision
				# quaternions. Compare their components, allowing the equivalent sign.
				var direct_error := maxf(maxf(absf(actual_thumb.x-expected_thumb.x),absf(actual_thumb.y-expected_thumb.y)),maxf(absf(actual_thumb.z-expected_thumb.z),absf(actual_thumb.w-expected_thumb.w)))
				var sign_error := maxf(maxf(absf(actual_thumb.x+expected_thumb.x),absf(actual_thumb.y+expected_thumb.y)),maxf(absf(actual_thumb.z+expected_thumb.z),absf(actual_thumb.w+expected_thumb.w)))
				_check(minf(direct_error,sign_error)<.00001,"salt pinch must use its own authored target pose: component_error=%s" % minf(direct_error,sign_error))
			if equipment.tools.has(action) and equipment.tools[action].visible:
				_check(equipment.tools[action].global_transform.is_equal_approx(equipment._tool_grips[action].global_transform),"implement must use its authored hand contact throughout the action")
			_check(equipment.right_skeleton.get_bone_global_pose(0).basis.determinant() > .99,"arm solve must preserve positive unit bone scale")
			var lamp_delta: Transform3D = equipment.lamp.transform*equipment._lamp_rest.affine_inverse()
			var grip_delta: Transform3D = equipment.right_grip.transform*equipment._grip_rest.affine_inverse()
			_check(lamp_delta.is_equal_approx(grip_delta),"lamp and true right hand must share one rigid action transform")
			if action == "flash" and sample == 5:
				var support_delta: Transform3D = equipment.support.transform*equipment._support_rest.affine_inverse()
				_check(lamp_delta.is_equal_approx(support_delta),"burst contact peak rotates the support palm with the lamp")
	if failures.is_empty(): print("HAND ANATOMY PASS: ",checks," checks; max dynamic wrist degrees=",max_wrist_angle)
	else: print("HAND ANATOMY FAIL: ",failures.size()," of ",checks," checks; max dynamic wrist degrees=",max_wrist_angle)
	get_tree().quit(0 if failures.is_empty() else 1)
