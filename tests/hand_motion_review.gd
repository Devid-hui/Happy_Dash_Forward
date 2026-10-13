extends Node
# Controlled native animation review; this does not inject gameplay actions.
const STUDIO := preload("res://tests/anatomical_spectra_preview.gd")
const FPS := 30.0
var studio: Node3D
var directory := ""
var frame_number := 0
var intervals: Array[Dictionary] = []
var joint_samples: Array[Dictionary] = []
var right_joint_samples: Array[Dictionary] = []
var review_view := "first_person"

func _ready() -> void:
	assert(DisplayServer.get_name() != "headless","Hand motion review needs actual native rendering")
	directory = OS.get_environment("HDF_HAND_MOTION_DIR")
	assert(not directory.is_empty(),"Explicit hand review destination is required")
	DirAccess.make_dir_recursive_absolute(directory.path_join("frames"))
	get_window().size = Vector2i(1920,1080)
	get_window().visible = true
	get_window().grab_focus()
	studio = STUDIO.new()
	add_child(studio)
	studio.set_process(false)
	review_view = OS.get_environment("HDF_HAND_MOTION_VIEW")
	if review_view.is_empty(): review_view = "first_person"
	if review_view in ["left_oblique","right_oblique"]:
		# Observe the same equipment-camera rig from outside; moving its own
		# camera would move the attached arms too and hide shoulder problems.
		var observer := Camera3D.new()
		observer.fov = 58.0; observer.near = .025
		add_child(observer)
		var side := -1.0 if review_view == "left_oblique" else 1.0
		observer.look_at_from_position(studio.camera.to_global(Vector3(side*.9,-.18,.25)),studio.camera.to_global(Vector3(.02,-.36,-.43)))
		observer.current = true
	for warmup in range(45): await RenderingServer.frame_post_draw
	for spec in [["idle",.40],["shot",.45],["flash",.80],["luminol",.95],["salt",1.0],["mud",.9]]:
		if OS.get_environment("HDF_HAND_MOTION_ACTION") != "" and spec[0] != OS.get_environment("HDF_HAND_MOTION_ACTION"): continue
		await _review_action(spec[0],spec[1])
	var receipt := {"engine":Engine.get_version_info(),"device":RenderingServer.get_video_adapter_name(),
		"framebuffer":[1920,1080],"fps":FPS,"frames":frame_number,"intervals":intervals,"view":review_view,
		"native_skinned_equipment":true,"controlled_animation_review":true,"human_playthrough":false,
		"diagnostic_taa_disabled":true,"production_render_settings_changed":false}
	FileAccess.open(directory.path_join("motion-receipt.json"),FileAccess.WRITE).store_string(JSON.stringify(receipt,"\t"))
	FileAccess.open(directory.path_join("joint-samples.json"),FileAccess.WRITE).store_string(JSON.stringify(joint_samples,"\t"))
	FileAccess.open(directory.path_join("right-joint-samples.json"),FileAccess.WRITE).store_string(JSON.stringify(right_joint_samples,"\t"))
	studio.free()
	for cleanup in range(3): await get_tree().process_frame
	print("HAND MOTION REVIEW COMPLETE: ",frame_number," actual 1080p frames")
	get_tree().quit(0)

func _review_action(kind: String, duration: float) -> void:
	var equipment: Node3D = studio.equipment
	equipment.tick(2.0)
	if kind != "idle": equipment.trigger(kind)
	var start := frame_number
	# Review the entire current action, including the lowering and return to idle.
	# A fixed .8 s flash review previously cut off the new 1.1 s presentation.
	var frame_count := ceili(maxf(duration,equipment.action_duration+.16)*FPS)+1
	for index in range(frame_count):
		equipment.tick(0.0 if index == 0 else 1.0/FPS,Vector2.ZERO)
		await RenderingServer.frame_post_draw
		var shot := get_viewport().get_texture().get_image()
		assert(shot.get_size() == Vector2i(1920,1080))
		assert(shot.save_png(directory.path_join("frames/frame_%05d.png" % frame_number)) == OK)
		if index == frame_count/2:
			shot.save_png(directory.path_join("peak_"+kind+".png"))
		if index in [0,roundi(frame_count*.12),roundi(frame_count*.24),roundi(frame_count*.46),roundi(frame_count*.68),roundi(frame_count*.84),frame_count-1]:
			shot.save_png(directory.path_join("%s_step_%02d.png" % [kind,index]))
		_record_joints(equipment,kind,index/FPS)
		_record_joints(equipment,kind,index/FPS,"RightGrip")
		frame_number += 1
	intervals.append({"action":kind,"first_frame":start,"frames":frame_count})
	print("HAND MOTION ACTION ",kind," frames=",frame_count)

func _xyz(v: Vector3) -> Array:
	return [v.x,v.y,v.z]

func _record_joints(equipment: Node3D,kind: String,time: float,prefix: String = "LeftSupport") -> void:
	var skeleton: Skeleton3D = equipment.left_skeleton if prefix == "LeftSupport" else equipment.right_skeleton
	var points: Array[Vector3] = []
	var poses: Array[Transform3D] = []
	for name in [prefix+"UpperArm",prefix+"ForeArm","wrist"]:
		var pose := skeleton.get_bone_global_pose(skeleton.find_bone(name))
		poses.append(pose)
		points.append(studio.camera.to_local(skeleton.to_global(pose.origin)))
	var rest: Dictionary = equipment._arm_frames[prefix]
	var samples := joint_samples if prefix == "LeftSupport" else right_joint_samples
	samples.append({"frame":frame_number,"action":kind,"time":time,"support_visible":equipment.support.visible,
		"deployment":equipment._support_deployment,"shoulder_camera":_xyz(points[0]),"elbow_camera":_xyz(points[1]),"wrist_camera":_xyz(points[2]),
		"upper_length_error_m":absf(points[0].distance_to(points[1])-rest.l1),
		"fore_length_error_m":absf(points[1].distance_to(points[2])-rest.l2),
		"fore_transverse_axis":_xyz(poses[1].basis.x),"wrist_transverse_axis":_xyz(poses[2].basis.x)})
