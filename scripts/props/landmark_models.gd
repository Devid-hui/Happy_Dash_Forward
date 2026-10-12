extends RefCounted
const ORGANIC := preload("res://scripts/art/organic_mesh.gd")

static func material(color: Color) -> StandardMaterial3D:
	var m := StandardMaterial3D.new(); m.albedo_color = color; m.roughness = .82
	return m

static func box(root: Node3D, label: String, size: Vector3, position: Vector3, m: Material) -> MeshInstance3D:
	var mesh := BoxMesh.new(); mesh.size = size
	var part := ORGANIC.part(root,mesh,m,label); part.position = position
	return part

static func beam(root: Node3D, start: Vector3, end: Vector3, radius: float, m: Material) -> void:
	var mesh := CylinderMesh.new()
	mesh.top_radius = radius; mesh.bottom_radius = radius
	mesh.height = start.distance_to(end); mesh.radial_segments = 6
	var part := ORGANIC.part(root,mesh,m,"Beam")
	part.position = (start+end)*.5
	part.quaternion = Quaternion(Vector3.UP,(end-start).normalized())

static func tower(root: Node3D) -> void:
	var steel := material(Color(.33,.36,.37))
	var ceramic := material(Color(.38,.44,.41))
	for x in [-1.0,1.0]:
		for z in [-1.0,1.0]:
			beam(root,Vector3(x*2.2,0,z*2.2),Vector3(x*.55,12,z*.55),.11,steel)
	for level in range(4):
		var low := level*3.0
		var high := low+3.0
		var r0 := lerpf(2.2,.55,low/12)
		var r1 := lerpf(2.2,.55,high/12)
		for side in [-1.0,1.0]:
			beam(root,Vector3(-r0,low,side*r0),Vector3(r1,high,side*r1),.06,steel)
			beam(root,Vector3(r0,low,side*r0),Vector3(-r1,high,side*r1),.06,steel)
			beam(root,Vector3(side*r0,low,-r0),Vector3(side*r1,high,r1),.06,steel)
			beam(root,Vector3(side*r0,low,r0),Vector3(side*r1,high,-r1),.06,steel)
	beam(root,Vector3(0,11,0),Vector3(0,15,0),.12,steel)
	for level in [10.5,13.0]:
		var span := 4.2 if level < 12 else 3.3
		beam(root,Vector3(-span,level,0),Vector3(span,level,0),.13,steel)
		for side in [-1.0,1.0]:
			beam(root,Vector3(0,level-1.2,0),Vector3(side*span,level,0),.065,steel)
			beam(root,Vector3(side*span,level,0),Vector3(side*span,level-.7,0),.12,ceramic)
			for direction in [-1.0,1.0]:
				var points: Array[Vector3] = [Vector3(side*span,level-.7,0),Vector3(side*span,level-2.6,direction*18),Vector3(side*span,level-1.2,direction*38)]
				var radii: Array[float] = [.026,.026,.026]
				ORGANIC.part(root,ORGANIC.tube(points,radii,5),steel,"SaggingCable")

static func car(root: Node3D) -> void:
	var rust := material(Color(.28,.16,.095))
	var trim := material(Color(.19,.21,.21))
	var glass := material(Color(.025,.055,.065))
	var rubber := material(Color(.028,.03,.028))
	box(root,"Body",Vector3(2.3,.60,4.2),Vector3(0,.72,0),rust)
	box(root,"Cabin",Vector3(1.95,.75,1.85),Vector3(0,1.35,.0),rust)
	box(root,"Roof",Vector3(2.05,.10,1.95),Vector3(0,1.78,0),trim)
	box(root,"FrontWindshield",Vector3(1.74,.52,.028),Vector3(0,1.38,-.95),glass)
	box(root,"RearWindshield",Vector3(1.74,.46,.028),Vector3(0,1.40,.95),glass)
	for side in [-1.0,1.0]:
		for z in [-.48,.48]:
			box(root,"SideWindow",Vector3(.026,.48,.75),Vector3(side*.986,1.4,z),glass)
		for z in [-1.38,1.38]:
			var wheel := CylinderMesh.new()
			wheel.top_radius = .43; wheel.bottom_radius = .43; wheel.height = .27; wheel.radial_segments = 16
			var part := ORGANIC.part(root,wheel,rubber,"Wheel")
			part.position = Vector3(side*1.15,.43,z); part.rotation.z = PI/2
		box(root,"DoorHandle",Vector3(.08,.055,.24),Vector3(side*1.17,.98,.30),trim)
	for z in [-2.13,2.13]:
		box(root,"Bumper",Vector3(2.4,.14,.15),Vector3(0,.51,z),trim)
		for x in [-.82,.82]:
			box(root,"BrokenLamp",Vector3(.38,.20,.04),Vector3(x,.79,z),material(Color(.42,.39,.25)))
	var hood := box(root,"BentHood",Vector3(2.18,.09,1.16),Vector3(0,1.02,-1.55),rust)
	hood.rotation.x = -.12

static func dead_tree(root: Node3D) -> void:
	var bark := material(Color(.46,.40,.28))
	var points: Array[Vector3] = [Vector3.ZERO,Vector3(-.2,1.4,0),Vector3(.2,3.5,0),Vector3(-.35,5.8,.1),Vector3(-.2,8.2,0)]
	var radii: Array[float] = [.7,.5,.39,.24,.08]
	ORGANIC.part(root,ORGANIC.tube(points,radii,18,.13),bark,"BleachedTrunk")
	for side in [-1.0,1.0]:
		var branch_points: Array[Vector3] = [Vector3(0,3.2,0),Vector3(side*1.3,4.0,0),Vector3(side*2.6,4.9,-.2),Vector3(side*2.9,6.2,-.2)]
		var branch_radii: Array[float] = [.28,.21,.13,.015]
		ORGANIC.part(root,ORGANIC.tube(branch_points,branch_radii,12,.1),bark,"BrokenFork")
		var root_points: Array[Vector3] = [Vector3(0,.4,0),Vector3(side*1.0,.12,-.5),Vector3(side*2.1,0,-.9)]
		var root_radii: Array[float] = [.3,.16,.01]
		ORGANIC.part(root,ORGANIC.tube(root_points,root_radii,10),bark,"Root")
	box(root,"WarningPlaque",Vector3(.7,.45,.08),Vector3(0,1.65,-.52),material(Color(.22,.12,.06)))
