extends RefCounted
const ORGANIC := preload("res://scripts/art/organic_mesh.gd")

static func bark_material() -> ShaderMaterial:
	var shader := Shader.new()
	shader.code = """shader_type spatial;
varying vec3 local_position;
void vertex(){local_position=VERTEX;}
void fragment(){
 float grooves=sin(UV.x*110.0+sin(UV.y*27.0)*1.8);
 float flecks=fract(sin(dot(floor(local_position*32.0),vec3(13.1,71.7,31.4)))*43758.5);
 vec3 bark=mix(vec3(.085,.063,.045),vec3(.23,.19,.13),smoothstep(-.7,.6,grooves));
 float moss=(1.0-smoothstep(.1,1.4,local_position.y))*smoothstep(.25,.8,flecks);
 ALBEDO=mix(bark,vec3(.065,.12,.057),moss)*(0.82+flecks*.3);
 ROUGHNESS=.72;
 SPECULAR=.28;
 NORMAL_MAP=vec3(.5+.14*cos(UV.x*110.0),.5,.98);
}
"""
	var material := ShaderMaterial.new()
	material.shader = shader
	return material

static var tree_cache: Dictionary = {}

static func _own_children(node: Node, owner_root: Node) -> void:
	for child in node.get_children():
		child.owner = owner_root
		_own_children(child,owner_root)

static func build(seed_value: int, dead: bool, bark: Material) -> Node3D:
	# 六种树形 × 活树/枯树。随机旋转与缩放保留环境变化，网格跨实例、跨重开共享。
	var variant := posmod(seed_value,6)
	var key := variant*2+int(dead)
	if not tree_cache.has(key):
		var tree := _build_uncached(variant*731+41,dead,bark)
		_own_children(tree,tree)
		var scene := PackedScene.new()
		scene.pack(tree)
		tree_cache[key] = scene
		tree.free()
	return tree_cache[key].instantiate() as Node3D

static func _build_uncached(seed_value: int, dead: bool, bark: Material) -> Node3D:
	var rng := RandomNumberGenerator.new()
	rng.seed = seed_value
	var root := Node3D.new()
	root.name = "DetailedDeadTree" if dead else "DetailedForestTree"
	var height := rng.randf_range(6.5,10.5)
	var lean := Vector3(rng.randf_range(-.7,.7),0,rng.randf_range(-.7,.7))
	var trunk_points: Array[Vector3] = []
	var trunk_radii: Array[float] = []
	for i in range(9):
		var t := i/8.0
		trunk_points.append(Vector3(0,height*t,0)+lean*t*t)
		trunk_radii.append(lerpf(.38,.025,t)*(1.0+.08*sin(i*2.1)))
	ORGANIC.part(root,ORGANIC.tube(trunk_points,trunk_radii,16,.11),bark,"RidgedTrunk")
	for i in range(5):
		var angle := TAU*i/5+rng.randf_range(-.2,.2)
		var direction := Vector3(cos(angle),0,sin(angle))
		var points: Array[Vector3] = [Vector3(0,.4,0),direction*.5+Vector3(0,.15,0),direction*1.05+Vector3(0,.06,0),direction*1.7]
		var radii: Array[float] = [.20,.14,.075,.003]
		ORGANIC.part(root,ORGANIC.tube(points,radii,10,.09),bark,"ExposedRoot")
	var leaves := StandardMaterial3D.new()
	leaves.albedo_color = Color(.095,.16,.095)
	leaves.roughness = .9
	leaves.cull_mode = BaseMaterial3D.CULL_DISABLED
	for i in range(10):
		var level := .32+i*.055
		var origin := Vector3(0,height*level,0)+lean*level*level
		var angle := i*2.399+rng.randf_range(-.3,.3)
		var direction := Vector3(cos(angle),0,sin(angle))
		var length := rng.randf_range(1.6,2.8)*(1.2-level*.5)
		var tip := origin+direction*length+Vector3(0,.5,0)
		var points: Array[Vector3] = [origin,origin+direction*length*.4+Vector3(0,-.16,0),tip,tip+direction*.3+Vector3(0,.45,0)]
		var radii: Array[float] = [.12,.08,.034,.003]
		ORGANIC.part(root,ORGANIC.tube(points,radii,10,.08),bark,"CurvedBranch")
		for fork in [-1.0,1.0]:
			var start := origin.lerp(tip,.68)
			var end: Vector3 = tip+Vector3(-direction.z,0,direction.x)*fork*.65+Vector3(0,.4,0)
			var twig_points: Array[Vector3] = [start,start.lerp(end,.6),end]
			var twig_radii: Array[float] = [.045,.022,.002]
			ORGANIC.part(root,ORGANIC.tube(twig_points,twig_radii,7),bark,"BranchFork")
		if not dead:
			# 分叉针叶片打破圆团树冠的轮廓，闪电下能读到枝叶间隙。
			var surface := SurfaceTool.new()
			surface.begin(Mesh.PRIMITIVE_TRIANGLES)
			for frond in range(36):
				var angle_leaf := rng.randf_range(0,TAU)
				var center := Vector3(rng.randf_range(-.65,.65),rng.randf_range(-.15,.25),rng.randf_range(-.65,.65))
				var ray := Vector3(cos(angle_leaf),rng.randf_range(-.25,.05),sin(angle_leaf))*rng.randf_range(.45,1.0)
				var width := Vector3(-ray.z,.05,ray.x).normalized()*.15
				for vertex in [center-width,center+width,center+ray]:
					surface.add_vertex(vertex)
			surface.generate_normals()
			var foliage := ORGANIC.part(root,surface.commit(),leaves,"NeedleSprays")
			foliage.position = tip
			foliage.scale = Vector3(1.6,1,1.6)

	var body := StaticBody3D.new()
	var collision := CollisionShape3D.new()
	var shape := CylinderShape3D.new()
	shape.radius = .37; shape.height = height
	collision.shape = shape; collision.position.y = height*.5
	body.add_child(collision); root.add_child(body)
	return root
