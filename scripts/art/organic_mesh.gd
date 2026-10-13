extends RefCounted
# 沿中心线扫掠圆环，生成连续曲面；用于弯曲肢体、树根和树枝。
static func tube(points: Array[Vector3], radii: Array[float], sides: int = 14, ridges: float = 0.0) -> ArrayMesh:
	# 在控制点之间增加平滑采样；控制点少，成品曲面仍连续。
	var smooth_points: Array[Vector3] = []
	var smooth_radii: Array[float] = []
	for i in range(points.size()-1):
		for step in range(3):
			var t := step/3.0
			var p0 := points[maxi(0,i-1)]
			var p1 := points[i]
			var p2 := points[i+1]
			var p3 := points[mini(points.size()-1,i+2)]
			smooth_points.append(.5*((2*p1)+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t*t*t))
			smooth_radii.append(lerpf(radii[i],radii[i+1],t))
	smooth_points.append(points[-1]); smooth_radii.append(radii[-1])
	points = smooth_points; radii = smooth_radii
	var vertices := PackedVector3Array()
	var uvs := PackedVector2Array()
	var indices := PackedInt32Array()
	for ring in range(points.size()):
		var tangent := (points[mini(ring + 1, points.size()-1)] - points[maxi(ring-1, 0)]).normalized()
		var axis := Vector3.RIGHT if absf(tangent.dot(Vector3.UP)) > 0.95 else Vector3.UP
		var normal := tangent.cross(axis).normalized()
		var binormal := tangent.cross(normal).normalized()
		for side in range(sides + 1):
			var angle := TAU * side / sides
			var radius := radii[ring] * (1.0 + ridges * sin(angle * 7.0 + ring * 0.45))
			vertices.append(points[ring] + radius * (normal * cos(angle) + binormal * sin(angle)))
			uvs.append(Vector2(float(side)/sides, float(ring)/(points.size()-1)))
	for ring in range(points.size()-1):
		for side in range(sides):
			var a := ring * (sides+1) + side
			var b := a + sides + 1
			indices.append_array(PackedInt32Array([a, b, a+1, a+1, b, b+1]))
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = vertices
	arrays[Mesh.ARRAY_TEX_UV] = uvs
	arrays[Mesh.ARRAY_INDEX] = indices
	var mesh := ArrayMesh.new()
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	var surface := SurfaceTool.new()
	surface.create_from(mesh, 0)
	surface.generate_normals()
	return surface.commit()

static func part(parent: Node3D, mesh: Mesh, material: Material, label: String) -> MeshInstance3D:
	var instance := MeshInstance3D.new()
	instance.name = label
	instance.mesh = mesh
	instance.material_override = material
	parent.add_child(instance,true)
	return instance

# Same-material procedural parts become one immutable surface, shared by every variant instance.
# Existing tube()/part() behavior remains unchanged for hunter/legacy callers.
static func merge(meshes: Array[Mesh], transforms: Array[Transform3D] = []) -> ArrayMesh:
	var surface := SurfaceTool.new()
	surface.begin(Mesh.PRIMITIVE_TRIANGLES)
	for i in range(meshes.size()):
		var mesh := meshes[i]
		var transform_value := transforms[i] if i < transforms.size() else Transform3D.IDENTITY
		for index in range(mesh.get_surface_count()): surface.append_from(mesh,index,transform_value)
	return surface.commit()
