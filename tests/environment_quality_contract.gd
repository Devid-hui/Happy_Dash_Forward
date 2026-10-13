extends Node
const FOREST := preload("res://scripts/art/forest_detail.gd")
const TERRAIN := preload("res://scripts/art/terrain_detail.gd")

func _ready() -> void:
	call_deferred("run_contract")

func tris(mesh: Mesh) -> int:
	var count := 0
	for surface in range(mesh.get_surface_count()):
		var arrays := mesh.surface_get_arrays(surface)
		count += arrays[Mesh.ARRAY_INDEX].size()/3 if arrays[Mesh.ARRAY_INDEX] != null and arrays[Mesh.ARRAY_INDEX].size() > 0 else arrays[Mesh.ARRAY_VERTEX].size()/3
	return count

func assert_trunk_contours(mesh: Mesh, label: String) -> void:
	# Real horizontal cross sections catch the former tube-frame hourglass:
	# having triangles at a height does not establish a full trunk radius.
	var faces := mesh.get_faces()
	for height in [.8,1.0,1.2,1.4,1.6,1.8,2.0,2.2,2.4,2.6]:
		var points: Array[Vector2] = []
		for index in range(0,faces.size(),3):
			for edge in range(3):
				var a: Vector3 = faces[index+edge]; var b: Vector3 = faces[index+(edge+1)%3]
				if (a.y < height and b.y >= height) or (b.y < height and a.y >= height):
					var p := a.lerp(b,(height-a.y)/(b.y-a.y))
					if Vector2(p.x,p.z).length() < .65: points.append(Vector2(p.x,p.z))
		assert(points.size() >= 12,"Closed trunk section has a resolved contour: "+label)
		var center := Vector2.ZERO
		for p in points: center += p
		center /= points.size()
		var minimum_radius := 1.0
		for p in points: minimum_radius = minf(minimum_radius,p.distance_to(center))
		assert(minimum_radius >= .17,"No circumferential pinch at y=%s in %s, radius=%s" % [height,label,minimum_radius])

func run_contract() -> void:
	var manifest := JSON.parse_string(FileAccess.get_file_as_string("res://assets/refined/environment/ENVIRONMENT_MANIFEST.json")) as Dictionary
	assert(manifest.trees.size() == 9,"Full suite requires six botanical crowns and three dead trunk variants")
	for entry in manifest.trees:
		assert(entry.source_triangles >= (280000 if entry.dead else 450000),"Editable high-density mothers are retained")
		if not entry.dead:
			assert(entry.leaf_counts.Master >= 10000 and entry.leaf_counts.Near >= 10000,"Leaf population materially exceeds the previous sparse 4200-leaf crown")
			assert(entry.leaf_counts.Mid >= 5000 and entry.leaf_counts.Far >= 1600,"Middle/far retain distributed volumetric crown coverage")
			for layer in ["inner","middle","outer"]: assert(entry.crown_layers[layer] > 0,"All three supported crown layers are populated; actual mass is reviewed in rendered views")
			assert(entry.leaf_support_twigs >= 1200)
	var leaf_color := load("res://assets/refined/environment/leaf_venation_color.png") as Texture2D
	var leaf_normal := load("res://assets/refined/environment/leaf_venation_normal.png") as Texture2D
	assert(leaf_color.get_width() == 4096 and leaf_normal.get_width() == 4096,"Actual close leaf venation images are 4K")
	var envelopes := JSON.parse_string(FileAccess.get_file_as_string("res://assets/refined/environment/PHYSICS_ENVELOPE.json")) as Dictionary
	for dead_flag in [false,true]:
		for variant in range(3 if dead_flag else 6):
			var specimen := FOREST.build(variant,dead_flag,FOREST.bark_material())
			var specimen_key: String = String(specimen.get_meta("asset_source")).get_file().get_basename()
			assert(is_equal_approx(specimen.get_node("TreeTrunkCollision/CollisionShape3D").shape.height,envelopes[specimen_key].collision_height),"Foliage expansion retains the pre-existing collision envelope")
			for lod in ["NearBark","MidBark"]:
				assert_trunk_contours((specimen.get_node(lod) as MeshInstance3D).mesh,"%s/%s" % [specimen.get_meta("asset_source"),lod])
			var far_trunk := specimen.get_node("FarBark") as MeshInstance3D
			assert(far_trunk.mesh.get_aabb().size.y >= envelopes[specimen_key].collision_height*.85,"Far silhouette retains full structural trunk, not detached twigs")
			specimen.free()
	for texture in ["bark_basecolor","bark_normal","bark_roughness","floor_basecolor","floor_normal","floor_roughness"]:
		var t := FOREST._pbr_texture(texture)
		assert(t != null and t.get_width() >= 4096,"4K scanned PBR texture is present: "+texture)
	var first := FOREST.build(0,false,FOREST.bark_material())
	var second := FOREST.build(0,false,FOREST.bark_material())
	add_child(first); add_child(second)
	assert(first != second)
	assert(first.get_meta("botanical_high_fidelity"))
	assert(first.find_children("*","MeshInstance3D",true,false).size() == 8)
	assert(first.get_node("NearBark").visibility_parent == NodePath("../MidBark"))
	assert(first.get_node("MidBark").visibility_parent == NodePath("../FarBark"))
	assert(first.get_node("NearBark").visibility_range_end == 0.0 and first.get_node("MidBark").visibility_range_end == 0.0,"A shared visibility dependency selects one opaque bark LOD without independent-range gaps")
	for name in ["NearBark","MidBark","FarBark","NearCanopy","MidCanopy","FarCanopy"]:
		var a := first.get_node(name) as MeshInstance3D
		var b := second.get_node(name) as MeshInstance3D
		assert(a.mesh == b.mesh,"Variants share immutable authored geometry")
		assert(a.extra_cull_margin >= .5,"Wind deformation retains a conservative bound")
		var expected_fade := GeometryInstance3D.VISIBILITY_RANGE_FADE_DISABLED if "Bark" in name else GeometryInstance3D.VISIBILITY_RANGE_FADE_SELF
		assert(a.visibility_range_fade_mode == expected_fade,"Solid bark stays opaque during LOD transitions; foliage may crossfade")
		assert(a.lod_bias >= 100,"Authored topology is not replaced by a destructive automatic LOD")
		assert(a.cast_shadow == GeometryInstance3D.SHADOW_CASTING_SETTING_OFF,"Visible high-density LODs never enter shadow passes")
	var shadow_triangles := 0
	for name in ["Bark","Canopy"]:
		var proxy := first.get_node("Shadow"+name) as MeshInstance3D
		var source_lod: String = FOREST.SHADOW_CANOPY_LOD if name == "Canopy" else "Mid"
		var visible_source := first.get_node(source_lod+name) as MeshInstance3D
		assert(proxy.mesh == visible_source.mesh,"Shadow proxy shares existing botanical geometry")
		assert(proxy.material_override == visible_source.material_override,"Visible and shadow foliage share the same controlled wind")
		assert(proxy.cast_shadow == GeometryInstance3D.SHADOW_CASTING_SETTING_SHADOWS_ONLY)
		assert(proxy.visibility_range_begin == 0 and proxy.visibility_range_end > FOREST.NEAR_END,"Shadow representation remains independent of the close visual LOD transition")
		shadow_triangles += tris(proxy.mesh)
	assert(shadow_triangles < 100000,"Each tree submits fewer than 100k triangles per shadow pass while preserving leaf silhouettes")
	if FOREST.SHADOW_CANOPY_LOD == "Far":
		assert(shadow_triangles < 12000,"Far-canopy candidate keeps the mid trunk while bounding each tree shadow pass to 12k triangles")
	assert(tris(first.get_node("NearBark").mesh) >= 40000)
	assert(tris(first.get_node("NearCanopy").mesh) >= 100000)
	assert(tris(first.get_node("MidCanopy").mesh) < tris(first.get_node("NearCanopy").mesh))
	assert(first.get_node("TreeTrunkCollision") != second.get_node("TreeTrunkCollision"))
	assert(is_equal_approx(first.get_node("TreeTrunkCollision/CollisionShape3D").shape.radius,.37))
	FOREST.set_motion_time(8.25)
	var material := first.get_node("NearCanopy").material_override as ShaderMaterial
	assert(is_equal_approx(material.get_shader_parameter("motion_time"),8.25))
	assert(not material.shader.code.contains("TIME"),"Paused game clock owns foliage motion")
	var foliage_mesh := (first.get_node("NearCanopy") as MeshInstance3D).mesh
	var foliage_arrays: Array = foliage_mesh.surface_get_arrays(0)
	assert(foliage_arrays[Mesh.ARRAY_COLOR] != null and foliage_arrays[Mesh.ARRAY_COLOR].size() > 0,"Authored botanical color survives GLTF export")
	var terrain := TERRAIN.build(); add_child(terrain)
	assert(terrain.get_meta("cosmetic_only"))
	assert(terrain.find_children("*","CollisionObject3D",true,false).is_empty())
	assert(terrain.get_meta("detail_counts").fern > 100)
	TERRAIN.set_motion_time(8.25)
	for chunk in terrain.get_children():
		assert(chunk is MultiMeshInstance3D)
		assert(chunk.multimesh.get_aabb().size.x < 23 and chunk.multimesh.get_aabb().size.z < 23)
		assert(chunk.visibility_range_end <= 46)
		if chunk.material_override is ShaderMaterial:
			assert(is_equal_approx(chunk.material_override.get_shader_parameter("motion_time"),8.25))
			assert(not chunk.material_override.shader.code.contains("TIME"))
	print("ENVIRONMENT QUALITY PASS: nine retained high-density mother models, 180 actual horizontal trunk contours, three immutable game LODs, bounded shared shadow proxies, 4K scanned PBR, authored botanical vertex colors, local cosmetic bounds and paused motion")
	get_tree().quit()
