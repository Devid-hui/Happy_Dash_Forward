extends Node3D
# View-only field equipment. Gameplay owns energy, cooldowns and success/rejection.
const ASSET_PATH := "res://assets/refined/field_equipment.glb"
var player: Node3D
var asset: Node3D
var lamp: Node3D
var support: Node3D
var right_grip: Node3D
var beam_socket: Node3D
var tools: Dictionary = {}
var _tool_grips: Dictionary = {}
var current_action := "idle"
var action_time := 0.0
var action_duration := 0.0
var pulse_mode := false
var lamp_level := 1
var cycle := 0.0
var _rest := Vector3(.25,-.15,-.52)
var _lamp_rest := Transform3D.IDENTITY
var _support_rest := Transform3D.IDENTITY
var _grip_rest := Transform3D.IDENTITY
var _charge_material: StandardMaterial3D
var _sensor_material: StandardMaterial3D
var right_skeleton: Skeleton3D
var left_skeleton: Skeleton3D
var _right_neutral: Dictionary = {}
var _left_neutral: Dictionary = {}
var _arm_frames: Dictionary = {}
var _thumb_axes: Dictionary = {}
var _finger_axes: Dictionary = {}
var _tool_poses: Dictionary = {}
var _support_deployment := 1.0
var _left_shoulder_weight := 0.0
var _right_shoulder_weight := 0.0
const SUPPORT_LOWERED_OFFSET := Vector3(-.10,-.18,.08)
# Raise the source display anchors to shoulder height and behind the grasp.
# Positions and the downward elbow pole use the same body/camera frame.
const LEFT_SHOULDER_OFFSET := Vector3(0,.29,.17)
const RIGHT_SHOULDER_OFFSET := Vector3(-.12,.26,.065)
const CARRY_OFFSET := Vector3(-.014,-.007,.022)

func setup(owner_player: Node3D) -> void:
	player = owner_player
	name = "FieldEquipment"
	position = _rest
	var packed := load(ASSET_PATH) as PackedScene
	assert(packed != null,"Refined field-equipment asset must exist")
	asset = packed.instantiate() as Node3D; asset.scale = Vector3.ONE; add_child(asset)
	_configure_linear_left_pigment(asset)
	lamp = asset.find_child("LampAssembly",true,false) as Node3D
	support = asset.find_child("LeftSupport",true,false) as Node3D
	right_grip = asset.find_child("RightGrip",true,false) as Node3D
	assert(lamp != null and support != null and right_grip != null)
	beam_socket = Node3D.new(); beam_socket.name = "OpticalBeamSocket"; beam_socket.position = Vector3(0,0,-.163); lamp.add_child(beam_socket)
	_lamp_rest = lamp.transform; _support_rest = support.transform; _grip_rest = right_grip.transform
	support.visible = false
	var right_rigs := right_grip.find_children("*","Skeleton3D",true,false)
	var left_rigs := support.find_children("*","Skeleton3D",true,false)
	assert(right_rigs.size() == 1 and left_rigs.size() == 1)
	right_skeleton = right_rigs[0]; left_skeleton = left_rigs[0]
	for hand_rig in [[right_grip,right_skeleton],[support,left_skeleton]]:
		var extra: Dictionary = hand_rig[0].get_meta("extras",{})
		var components: Array = extra.get("thumb2_flexion_axis_local",[])
		assert(components.size() == 3,"native thumb hinge must be exported with the authored hand")
		_thumb_axes[hand_rig[1]] = Vector3(components[0],components[1],components[2]).normalized()
		var finger_axes: Dictionary = JSON.parse_string(extra.get("finger_flexion_axes_json","{}"))
		assert(finger_axes.size() == 12,"each non-thumb phalanx requires its own authored transverse hinge")
		_finger_axes[hand_rig[1]] = {}
		for bone_name in finger_axes:
			var direction: Array = finger_axes[bone_name]
			_finger_axes[hand_rig[1]][bone_name] = Vector3(direction[0],direction[1],direction[2]).normalized()
	var left_extra: Dictionary = support.get_meta("extras",{})
	_tool_poses = JSON.parse_string(left_extra.get("tool_grip_poses_json","{}"))
	assert(_tool_poses.size() == 3,"each tool requires its own authored grip pose")
	for i in range(right_skeleton.get_bone_count()): _right_neutral[i] = right_skeleton.get_bone_pose_rotation(i)
	for i in range(left_skeleton.get_bone_count()): _left_neutral[i] = left_skeleton.get_bone_pose_rotation(i)
	_cache_arm(right_skeleton,"RightGrip")
	_cache_arm(left_skeleton,"LeftSupport")
	for pair in [["luminol","ToolLuminol"],["salt","ToolSalt"],["mud","ToolMud"]]:
		var tool := asset.find_child(pair[1],true,false) as Node3D
		assert(tool != null); tool.visible = false; tools[pair[0]] = tool
		var contact := support.find_child(String(pair[1]).trim_prefix("Tool")+"GripSocket",true,false) as Node3D
		assert(contact != null,"hand-authored tool contact must exist")
		_tool_grips[pair[0]] = contact
	# First-person geometry does not cast large moving shadows into the level.
	for part in asset.find_children("*","MeshInstance3D",true,false):
		part.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		part.extra_cull_margin = 1.0
		if part.name in ["OpticalEmitter","SensorScreen"] and part.mesh.get_surface_count() > 0:
			var m: Material = part.mesh.surface_get_material(0)
			if m is StandardMaterial3D:
				var local_material := m.duplicate() as StandardMaterial3D
				part.set_surface_override_material(0,local_material)
				if part.name == "OpticalEmitter": _charge_material = local_material
				else: _sensor_material = local_material

func set_mode(pulse: bool) -> void:
	pulse_mode = pulse
	trigger("mode")

func set_level(level: int) -> void:
	lamp_level = clampi(level,1,3)

func trigger(kind: String) -> void:
	# A release may replace ambient feedback, but it never blocks a gameplay action.
	var normalized := "mud" if kind == "mire" else ("infer" if kind == "filter" else kind)
	current_action = normalized; action_time = 0.0
	if is_instance_valid(support): support.visible = false
	action_duration = {"flash":1.10,"shot":.19,"mode":.32,"light":.25,"capture":.48,"boost":.45,"luminol":.78,"salt":.88,"mud":.73,"echo":.50,"afterimage":.36,"infer":.45}.get(normalized,.28)
	for tool in tools.values(): tool.visible = false

func tick(delta: float, movement: Vector2 = Vector2.ZERO, sprinting: bool = false, boost: bool = false, noise: float = 0.0) -> void:
	if not is_instance_valid(asset): return
	cycle += delta*(11.0 if sprinting else 7.0)*minf(1.0,movement.length())
	action_time = minf(action_duration,action_time+delta)
	var t := action_time/maxf(.001,action_duration)
	var envelope := sin(PI*t) if current_action != "idle" else 0.0
	var bob := minf(1.0,movement.length())*(.012 if sprinting else .006)
	position = _rest+Vector3(sin(cycle)*bob,absf(cos(cycle))*.75*bob,0)
	rotation = Vector3(.07 if sprinting else 0,-.045*movement.x,.035*sin(cycle)*minf(1,movement.length()))
	lamp.transform = _lamp_rest; right_grip.transform = _grip_rest; support.transform = _support_rest
	_support_deployment = 1.0
	_left_shoulder_weight = 0.0
	_right_shoulder_weight = envelope
	var recoil := Vector3.ZERO; var pivot := Vector3.ZERO
	match current_action:
		"flash":
			_support_deployment = _support_envelope(t)
			_left_shoulder_weight = _shoulder_envelope(t)
			support.visible = t < 1.0
			support.position = _support_rest.origin+SUPPORT_LOWERED_OFFSET*(1-_support_deployment)
			recoil = Vector3(0,.012,-.030)*pow(envelope,2)
			pivot.x = -.10*pow(envelope,2)
		"shot": recoil.z = .022*envelope; pivot.x = -.035*envelope
		"mode", "infer", "echo": pivot.z = -.10*envelope; pivot.y = .09*envelope
		"luminol", "salt", "mud":
			_support_deployment = _support_envelope(t)
			_left_shoulder_weight = _shoulder_envelope(t)
			var lower_lamp := Vector3(.04,-.08,.015)*envelope
			lamp.position += lower_lamp
			right_grip.position += lower_lamp
			var tool: Node3D = tools[current_action]
			var approach := SUPPORT_LOWERED_OFFSET*(1-_support_deployment)+Vector3(-.09,-.01,.03)*_support_deployment
			var tilt := -.10*_support_deployment if current_action == "luminol" else (-.16*_support_deployment if current_action == "salt" else .24*_support_deployment)
			var gesture := Transform3D(Basis(Vector3.RIGHT,tilt),approach)
			support.visible = t < 1.0
			support.transform = gesture*_support_rest
			tool.global_transform = _tool_grips[current_action].global_transform
			tool.visible = support.visible
		"boost", "afterimage": pivot.x = .10*envelope
		"capture": pivot.z = .025*sin(t*TAU*2.0)
	# Apply one equipment-space rigid transform to the lamp and both contacts.
	# Adding Euler angles to differently rotated hand roots separates the grip.
	var action_transform := Transform3D(Basis.from_euler(pivot),recoil)
	lamp.transform = action_transform*lamp.transform
	right_grip.transform = action_transform*right_grip.transform
	if current_action == "flash": support.transform = action_transform*support.transform
	# Bring the carried instrument toward the body and slightly inward. Both
	# hands keep their authored contacts while the fixed-length arms can fold
	# comfortably instead of presenting two nearly extended rods.
	var carry_transform := Transform3D(Basis.IDENTITY,CARRY_OFFSET)
	lamp.transform = carry_transform*lamp.transform
	right_grip.transform = carry_transform*right_grip.transform
	support.transform = carry_transform*support.transform
	if tools.has(current_action):
		tools[current_action].global_transform = _tool_grips[current_action].global_transform
	# Actual finger joints squeeze the trigger / mode control and release the reagent grip.
	right_skeleton.reset_bone_poses()
	left_skeleton.reset_bone_poses()
	var index_joint := right_skeleton.find_bone("RightGripIndex2")
	var thumb_joint := right_skeleton.find_bone("RightGripThumb2")
	if index_joint >= 0 and current_action in ["flash","shot"]:
		_bend_joint(right_skeleton,_right_neutral,index_joint,.03*envelope)
	if thumb_joint >= 0 and current_action in ["mode","light","infer","echo"]:
		_bend_joint(right_skeleton,_right_neutral,thumb_joint,.05*envelope)
	if current_action in ["luminol","salt","mud"]:
		var authored: Dictionary = _tool_poses[current_action]
		for bone_name in authored:
			var joint := left_skeleton.find_bone(bone_name)
			assert(joint >= 0)
			var q: Array = authored[bone_name]
			var target := Quaternion(q[0],q[1],q[2],q[3]).normalized()
			# Implements enter already held; the fingertips do not release the
			# object merely because the arm is travelling into or out of view.
			left_skeleton.set_bone_pose_rotation(joint,_left_neutral[joint]*target)
	_solve_arm(right_skeleton,"RightGrip")
	_solve_arm(left_skeleton,"LeftSupport")
	if boost: rotation.z += sin(cycle*1.23)*.014
	if noise > 0: rotation.y += sin(cycle*2.1)*minf(.012,noise*.00014)
	if _charge_material:
		var energy := .5+lamp_level*.13
		if current_action in ["flash","shot","capture","boost"]: energy += envelope*2.5
		_charge_material.emission_energy_multiplier = energy
	if _sensor_material:
		_sensor_material.emission = Color(.68,.35,.07) if pulse_mode else Color(.10,.53,.35)
		_sensor_material.emission_energy_multiplier = .7+envelope*2.0 if current_action in ["mode","echo","infer"] else .7
	if action_time >= action_duration and current_action != "idle":
		current_action = "idle"; support.visible = false
		for tool in tools.values(): tool.visible = false

static func _configure_linear_left_pigment(model: Node3D) -> void:
	# Godot's imported constant-colour skin surface can disable COLOR_0 while
	# neighbouring nail surfaces keep it, exposing a false material boundary.
	# These left-only materials use one compensated map and linear pigment.
	for found in model.find_children("*","MeshInstance3D",true,false):
		var mesh: MeshInstance3D = found
		for surface in mesh.mesh.get_surface_count():
			var imported := mesh.get_active_material(surface) as StandardMaterial3D
			if imported == null or not imported.resource_name.ends_with("left continuous pigment"): continue
			var pigment := imported.duplicate() as StandardMaterial3D
			pigment.vertex_color_use_as_albedo = true
			pigment.vertex_color_is_srgb = false
			mesh.set_surface_override_material(surface,pigment)

func _support_envelope(t: float) -> float:
	# The presentation can settle without adding a gameplay windup. All energy,
	# hit and cooldown decisions remain with the immediate player action.
	if t < .24: return smoothstep(0.0,.24,t)
	if t <= .68: return 1.0
	return 1.0-smoothstep(.68,1.0,t)

func _shoulder_envelope(t: float) -> float:
	# A small clavicle/shoulder lead starts the lift; the shoulder settles after
	# the hand begins lowering. The prop still determines the contact frame.
	if t < .20: return smoothstep(0.0,.20,t)
	if t <= .72: return 1.0
	return 1.0-smoothstep(.72,1.0,t)

# Arm reach is visual only. Shoulder anchors follow the equipment/camera frame;
# wrist targets follow the actual authored grasp and action, not a mirrored right fist.
func _bend_joint(skeleton: Skeleton3D, neutral: Dictionary, bone: int, angle: float) -> void:
	# Use the same joint-local transverse axis that authored the grip. A global
	# palm axis through an oblique finger adds an unwanted axial twist.
	var bone_name := skeleton.get_bone_name(bone)
	var axis: Vector3 = _thumb_axes[skeleton] if bone_name.ends_with("Thumb2") else _finger_axes[skeleton][bone_name]
	skeleton.set_bone_pose_rotation(bone,neutral[bone]*Quaternion(axis,-angle))

func _cache_arm(skeleton: Skeleton3D, prefix: String) -> void:
	var upper := skeleton.find_bone(prefix+"UpperArm")
	var fore := skeleton.find_bone(prefix+"ForeArm")
	var wrist := skeleton.find_bone("wrist")
	assert(upper >= 0 and fore >= 0 and wrist >= 0,"anatomical arm must retain shoulder/elbow/wrist")
	var up := skeleton.get_bone_global_rest(upper)
	var fp := skeleton.get_bone_global_rest(fore)
	var wp := skeleton.get_bone_global_rest(wrist)
	_arm_frames[prefix] = {"upper":upper,"fore":fore,"wrist":wrist,"up":up,"fp":fp,"wp":wp,
		"shoulder":asset.to_local(skeleton.to_global(up.origin)),
		"l1":up.origin.distance_to(fp.origin),"l2":fp.origin.distance_to(wp.origin)}

func _solve_arm(skeleton: Skeleton3D, prefix: String) -> void:
	var data: Dictionary = _arm_frames[prefix]
	var wanted := skeleton.get_bone_global_pose(data.wrist)
	var shoulder_shift := LEFT_SHOULDER_OFFSET+Vector3(.020,.016,-.030)*_left_shoulder_weight if prefix == "LeftSupport" else RIGHT_SHOULDER_OFFSET+Vector3(-.007,.004,-.012)*_right_shoulder_weight
	var start := skeleton.to_local(asset.to_global(data.shoulder+shoulder_shift))
	var target := wanted.origin
	var ray := target-start
	var distance := maxf(.001,ray.length())
	var direction := ray/distance
	var reach := clampf(distance,absf(data.l1-data.l2)+.001,data.l1+data.l2-.001)
	var along: float = (data.l1*data.l1-data.l2*data.l2+reach*reach)/(2*reach)
	var height := sqrt(maxf(0.0,data.l1*data.l1-along*along))
	# In the body/camera frame the elbow hangs below shoulder and wrist.
	# The old source-pose pole selected the upward branch, making the upper
	# arm run down from the elbow to a shoulder placed near the waist.
	var outward := -.45 if prefix == "LeftSupport" else .20
	var hint_position: Vector3 = data.shoulder+shoulder_shift+Vector3(outward,-1.0,0)
	var hint := skeleton.to_local(asset.to_global(hint_position))-start
	var bend := hint-direction*hint.dot(direction)
	if bend.length_squared() < .000001: bend = direction.cross(Vector3.RIGHT)
	var elbow: Vector3 = start+direction*along+bend.normalized()*height
	var up_basis: Basis = data.up.basis
	var fore_basis: Basis = data.fp.basis
	var up_rotation := Quaternion(up_basis.y.normalized(),(elbow-start).normalized())
	var fore_rotation := Quaternion(fore_basis.y.normalized(),(target-elbow).normalized())
	skeleton.set_bone_global_pose(data.upper,Transform3D(Basis(up_rotation)*up_basis,start))
	skeleton.set_bone_global_pose(data.fore,Transform3D(Basis(fore_rotation)*fore_basis,elbow))
	# Preserve the exact palm/weapon contact orientation while the elbow adapts.
	skeleton.set_bone_global_pose(data.wrist,wanted)
