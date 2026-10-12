extends Node3D
const ORGANIC := preload("res://scripts/art/organic_mesh.gd")
var eyes_light: OmniLight3D
static var cached_model: PackedScene
static var build_count := 0

func _ready() -> void:
	if cached_model == null:
		var template := Node3D.new()
		_build_model(template)
		_assign_owner(template,template)
		cached_model = PackedScene.new()
		cached_model.pack(template)
		template.free()
		build_count += 1
	# Mesh、材质、Shader 资源共享；节点、变换和光源状态仍是每只独立的。
	add_child(cached_model.instantiate())

func _assign_owner(node: Node, root: Node) -> void:
	for child in node.get_children():
		child.owner = root
		_assign_owner(child,root)

func _material(color: Color, glow := false) -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.albedo_color = color
	material.roughness = 0.88
	if glow:
		material.emission_enabled = true
		material.emission = color
		material.emission_energy_multiplier = 0.42
	return material

func _mesh_part(parent: Node3D, mesh: Mesh, part_name: String, position: Vector3, scale_value: Vector3, material: Material, rotation := Vector3.ZERO) -> MeshInstance3D:
	var part := MeshInstance3D.new()
	part.name = part_name
	part.mesh = mesh
	part.position = position
	part.scale = scale_value
	part.rotation_degrees = rotation
	part.material_override = material
	parent.add_child(part)
	return part

func _sphere(radius := 0.5, height := 1.0, segments := 28) -> SphereMesh:
	var mesh := SphereMesh.new()
	mesh.radius = radius
	mesh.height = height
	mesh.radial_segments = segments
	mesh.rings = 18
	return mesh

func _capsule(radius := 0.22, height := 0.8) -> CapsuleMesh:
	var mesh := CapsuleMesh.new()
	mesh.radius = radius
	mesh.height = height
	mesh.radial_segments = 20
	return mesh

func _skin_material(base: Color) -> ShaderMaterial:
	var shader := Shader.new()
	shader.code = """shader_type spatial;
uniform vec4 skin_color : source_color;
varying vec3 skin_position;
void vertex(){skin_position=VERTEX;}
void fragment(){
 float pores=fract(sin(dot(floor(skin_position*95.0),vec3(13.17,73.91,37.3)))*43758.5453);
 float mottling=sin(skin_position.x*19.0+sin(skin_position.y*23.0))*sin(skin_position.z*27.0);
 ALBEDO=skin_color.rgb*(.85+.12*mottling+.12*pores);
 ROUGHNESS=.69+.18*pores;
 SPECULAR=.28;
}
"""
	var material := ShaderMaterial.new()
	material.shader = shader
	material.set_shader_parameter("skin_color",base)
	return material

func _build_model(visual: Node3D) -> void:
	# 连续扫掠曲面和独立面部细节，仍受场景真实灯光影响。
	var gold := _skin_material(Color(0.52, 0.34, 0.075))
	var shadow_gold := _material(Color(0.25, 0.16, 0.038))
	var belly_material := _skin_material(Color(0.52, 0.51, 0.43))
	var hand_material := _material(Color(0.12, 0.13, 0.12))
	var mouth_material := _material(Color(0.008, 0.009, 0.008))
	var tooth_material := _material(Color(0.64, 0.65, 0.56))
	var eye_material := _material(Color(0.24, 0.82, 0.51), true)
	# 连续轮廓从腹部收进颈部再扩张到头部，消除原先球体拼接的台阶。
	var contour: Array[Vector3] = [Vector3(0,.36,.02),Vector3(0,.48,.02),Vector3(0,.75,0),Vector3(0,1.05,0),Vector3(0,1.32,.02),Vector3(0,1.55,.04),Vector3(0,1.8,.04),Vector3(0,2.03,.02),Vector3(0,2.22,0),Vector3(0,2.46,0),Vector3(0,2.65,0),Vector3(0,2.76,0)]
	var widths: Array[float] = [.02,.48,.69,.73,.62,.4,.29,.3,.4,.43,.31,.005]
	var skin := ORGANIC.part(visual, ORGANIC.tube(contour,widths,36,.022),gold,"ContinuousSkin")
	skin.scale.z = .76
	_mesh_part(visual,_sphere(.62,1.25),"PaleBelly",Vector3(0,.98,-.43),Vector3(.98,.94,.29),belly_material)
	_mesh_part(visual,_sphere(.25,.55),"MouthCavity",Vector3(0,2.21,-.32),Vector3(.86,1,.45),mouth_material)
	# 唇缘沿开口形成椭圆，遮住口腔边缘，双排牙齿朝向口内。
	var lip_points: Array[Vector3] = []
	var lip_radii: Array[float] = []
	for i in range(33):
		var angle := TAU*i/32
		lip_points.append(Vector3(.22*cos(angle),2.21+.28*sin(angle),-.43))
		lip_radii.append(.032)
	ORGANIC.part(visual,ORGANIC.tube(lip_points,lip_radii,10),shadow_gold,"LipRim")
	for row in [-1.0,1.0]:
		for i in range(9):
			var x := (i-4)*.043
			var fang := CylinderMesh.new()
			fang.top_radius = .023 if row > 0 else 0.0
			fang.bottom_radius = 0.0 if row > 0 else .023
			fang.height = .085 + .02*sin(i*1.7)
			fang.radial_segments = 10
			_mesh_part(visual,fang,"Tooth",Vector3(x,2.21+row*(.205-.045*absf(x)/.18),-.457),Vector3.ONE,tooth_material)
	for side in [-1.0,1.0]:
		_mesh_part(visual,_sphere(.13,.24),"EyeSocket",Vector3(side*.215,2.51,-.30),Vector3(1.18,1,.72),shadow_gold)
		_mesh_part(visual,_sphere(.097,.19),"Eye",Vector3(side*.215,2.51,-.365),Vector3(1,1.05,.52),eye_material)
		_mesh_part(visual,_sphere(.08,.13),"Nostril",Vector3(side*.064,2.35,-.368),Vector3(.35,1,.4),mouth_material)
		var arm_points: Array[Vector3] = [Vector3(side*.45,1.42,0),Vector3(side*.61,1.25,-.05),Vector3(side*.77,1.03,-.16),Vector3(side*.78,.88,-.32),Vector3(side*.63,.76,-.48),Vector3(side*.43,.75,-.59)]
		var arm_radii: Array[float] = [.19,.22,.21,.19,.17,.13]
		ORGANIC.part(visual,ORGANIC.tube(arm_points,arm_radii,20,.035),gold,"BentArm")
		_mesh_part(visual,_sphere(.2,.32),"Palm",Vector3(side*.34,.75,-.64),Vector3(1,.8,.44),hand_material)
		for finger in range(4):
			var y := .82-finger*.068
			var points: Array[Vector3] = [Vector3(side*.36,y,-.66),Vector3(side*.24,y-.02,-.72),Vector3(side*.13,y-.07,-.73),Vector3(side*.09,y-.09,-.71)]
			var radii: Array[float] = [.044,.048,.035,.004]
			ORGANIC.part(visual,ORGANIC.tube(points,radii,12),hand_material,"CurvedFinger")
		var leg_points: Array[Vector3] = [Vector3(side*.43,.66,.13),Vector3(side*.72,.66,.02),Vector3(side*.86,.48,-.03),Vector3(side*.75,.26,-.05),Vector3(side*.72,.12,-.17)]
		var leg_radii: Array[float] = [.28,.32,.28,.17,.15]
		ORGANIC.part(visual,ORGANIC.tube(leg_points,leg_radii,24,.025),gold,"CrouchedLeg")
		_mesh_part(visual,_sphere(.31,.59),"RoundedThigh",Vector3(side*.69,.58,.02),Vector3(1.15,1,1),gold)
		_mesh_part(visual,_sphere(.25,.28),"Foot",Vector3(side*.74,.12,-.28),Vector3(1.22,.7,1.3),hand_material)
		for toe in range(3):
			var x: float = side*(.58+toe*.14)
			_mesh_part(visual,_sphere(.085,.15),"Toe",Vector3(x,.075,-.47),Vector3(1,.7,1.6),hand_material)
	eyes_light = OmniLight3D.new()
	eyes_light.name = "FaintEyeBounce"
	eyes_light.light_color = Color(0.20, 0.65, 0.40)
	eyes_light.light_energy = 0.08
	eyes_light.omni_range = 2.2
	eyes_light.shadow_enabled = false
	eyes_light.position = Vector3(0, 2.42, -0.55)
	visual.add_child(eyes_light)

