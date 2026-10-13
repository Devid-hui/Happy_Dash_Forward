extends RefCounted
# Fused botanical masters, rolled leaf laminae and three shared geometry LODs.
const ASSET_ROOT := "res://assets/refined/environment/"
const NEAR_END := 9.0
const MID_END := 53.0
const SHADOW_CANOPY_LOD := "Far"
static var tree_cache: Dictionary = {}
static var _bark: Material
static var _foliage: ShaderMaterial
static var _motion_time := 0.0

static func _texture(path: String) -> Texture2D:
	return load(path) as Texture2D if ResourceLoader.exists(path) else null

static func _pbr_texture(alias: String) -> Texture2D:
	var manifest_path := ASSET_ROOT+"textures/PBR_TEXTURE_BINDINGS.json"
	assert(FileAccess.file_exists(manifest_path),"Scanned PBR binding manifest is required")
	var bindings := JSON.parse_string(FileAccess.get_file_as_string(manifest_path)) as Dictionary
	assert(bindings.has(alias),"Missing verified material binding: "+alias)
	var path: String = bindings[alias] if bindings[alias] is String else bindings[alias].path
	if not path.begins_with("res://"):
		path = "res://"+path if path.begins_with("assets/") else ASSET_ROOT+"textures/"+path
	var texture := load(path) as Texture2D
	assert(texture != null and texture.get_width() >= 4096,"Verified 4K scanned PBR is required: "+path)
	return texture

static func bark_material() -> Material:
	if _bark: return _bark
	var m := StandardMaterial3D.new()
	m.albedo_color = Color(.68,.65,.57)
	m.albedo_texture = _pbr_texture("bark_basecolor")
	m.roughness_texture = _pbr_texture("bark_roughness")
	m.roughness = .72
	m.normal_enabled = true
	m.normal_texture = _pbr_texture("bark_normal")
	m.normal_scale = .86
	m.uv1_triplanar = true; m.uv1_triplanar_sharpness = 5.0
	# Poly Haven Bark Brown 02 is a one-metre scan, retaining real grain scale.
	m.uv1_scale = Vector3.ONE; m.metallic_specular = .34
	_bark = m; return _bark

static func _foliage_material() -> ShaderMaterial:
	if _foliage: return _foliage
	var shader := Shader.new()
	shader.code = """shader_type spatial; render_mode cull_disabled;
uniform float motion_time = 0.0;
uniform sampler2D leaf_color : source_color, filter_linear_mipmap, repeat_disable;
uniform sampler2D leaf_normal : hint_normal, filter_linear_mipmap, repeat_disable;
varying vec3 botanical_color;
void vertex(){
 botanical_color=COLOR.rgb;
 vec3 world=(MODEL_MATRIX*vec4(VERTEX,1.)).xyz;
 float crown=max(VERTEX.y-2.3,0.);
 float wind=sin(motion_time*1.17+world.x*.19+world.z*.13)*.017;
 float flutter=sin(motion_time*3.2+world.x*2.7+world.z*1.9)*.009;
 // The petiole/lamina base is anchored to wood; flutter bends the leaf tip.
 VERTEX.x+=(wind+flutter*UV.y)*crown*UV.y;
 VERTEX.z+=sin(motion_time*.91+world.x*.1)*.007*crown*UV.y;
}
void fragment(){
 vec3 leaf=texture(leaf_color,UV).rgb;
 bool stalk=UV.x>1.5;
 if(stalk){ALBEDO=botanical_color;ROUGHNESS=.70;SPECULAR=.20;NORMAL_MAP=vec3(.5,.5,1.);}
 else{
  vec3 tint=mix(vec3(.8),botanical_color/vec3(.19,.32,.065),.42);
  // A waxy upper lamina and a paler matte underside read differently in grazing light.
  ALBEDO=leaf*tint*(FRONT_FACING?1.:1.16);
  ROUGHNESS=FRONT_FACING?.46:.68;SPECULAR=FRONT_FACING?.34:.22;
  NORMAL_MAP=texture(leaf_normal,UV).rgb;NORMAL_MAP_DEPTH=.65;
  BACKLIGHT=vec3(.08,.135,.026);
 }
}
"""
	_foliage = ShaderMaterial.new(); _foliage.shader = shader
	_foliage.set_shader_parameter("leaf_color",_texture(ASSET_ROOT + "leaf_venation_color.png"))
	_foliage.set_shader_parameter("leaf_normal",_texture(ASSET_ROOT + "leaf_venation_normal.png"))
	_foliage.set_shader_parameter("motion_time",_motion_time); return _foliage

static func set_motion_time(value: float) -> void:
	_motion_time = value
	if _foliage: _foliage.set_shader_parameter("motion_time",value)

static func _clone_meshes(imported: Node, root: Node3D, material: Material) -> void:
	for child in imported.get_children():
		if child is MeshInstance3D:
			var part := MeshInstance3D.new(); part.name = child.name; part.mesh = child.mesh
			part.transform = child.transform
			part.material_override = _foliage_material() if "Canopy" in String(child.name) else material
			var prefix := String(child.name)
			if prefix.begins_with("Near"):
				part.visibility_range_end = NEAR_END; part.visibility_range_end_margin = 2.0
			elif prefix.begins_with("Mid"):
				part.visibility_range_begin = NEAR_END; part.visibility_range_begin_margin = 2.0
				part.visibility_range_end = MID_END; part.visibility_range_end_margin = 4.0
			else:
				part.visibility_range_begin = MID_END; part.visibility_range_begin_margin = 4.0
				part.visibility_range_end = 145.0
			# Alpha-blending two solid trunks makes the forest floor visible through
			# the bark at the transition. Wood stays opaque; hysteresis prevents
			# rapid switching while the leaf canopy retains its smooth fade.
			part.visibility_range_fade_mode = GeometryInstance3D.VISIBILITY_RANGE_FADE_DISABLED if "Bark" in prefix else GeometryInstance3D.VISIBILITY_RANGE_FADE_SELF
			# Three authored representations already provide LOD; importer-generated
			# simplification must not split the narrow continuous trunk at distance.
			part.lod_bias = 1000.0
			part.extra_cull_margin = .55
			# A high-density canopy must never enter a shadow pass. Camera LOD
			# ranges alone are not a reliable shadow-geometry budget for a forest.
			part.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
			root.add_child(part)
			if prefix.begins_with("Mid"):
				# One stable, shared representation prevents duplicate LOD shadows
				# while retaining actual branch and leaf silhouettes under the lamp.
				var shadow := MeshInstance3D.new()
				shadow.name = prefix.replace("Mid","Shadow")
				shadow.mesh = part.mesh; shadow.transform = part.transform
				shadow.material_override = part.material_override
				shadow.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_SHADOWS_ONLY
				shadow.lod_bias = 1000.0; shadow.extra_cull_margin = .55
				shadow.visibility_range_end = MID_END
				shadow.visibility_range_end_margin = 4.0
				shadow.visibility_range_fade_mode = GeometryInstance3D.VISIBILITY_RANGE_FADE_SELF
				root.add_child(shadow)
		else: _clone_meshes(child,root,material)

static func _own_children(node: Node, owner_root: Node) -> void:
	for child in node.get_children(): child.owner = owner_root; _own_children(child,owner_root)

static func build(seed_value: int, dead: bool, bark: Material) -> Node3D:
	var variant := posmod(seed_value,3 if dead else 6); var key := variant*2+int(dead)
	if not tree_cache.has(key):
		var path := ASSET_ROOT + ("dead_tree_%d.glb" if dead else "broadleaf_tree_%d.glb") % (variant+1)
		if not ResourceLoader.exists(path): path = ASSET_ROOT + ("dead_tree_1.glb" if dead else "broadleaf_tree_1.glb")
		var packed := load(path) as PackedScene
		assert(packed != null,"Detailed botanical asset must be imported: " + path)
		var imported := packed.instantiate()
		var root := Node3D.new(); root.name = "DetailedDeadTree" if dead else "DetailedForestTree"
		_clone_meshes(imported,root,bark); imported.free()
		# One visibility dependency chain makes opaque wood LODs exclusive.
		# Independent begin/end hysteresis can hide both meshes when the first
		# camera frame starts inside the margin, or draw both while reversing.
		var near_bark := root.get_node("NearBark") as MeshInstance3D
		var mid_bark := root.get_node("MidBark") as MeshInstance3D
		near_bark.visibility_range_end = 0.0; near_bark.visibility_range_end_margin = 0.0
		near_bark.visibility_parent = NodePath("../MidBark")
		mid_bark.visibility_range_end = 0.0; mid_bark.visibility_range_end_margin = 0.0
		mid_bark.visibility_parent = NodePath("../FarBark")
		if not dead:
			# Only the invisible shadow representation changes. All 10,080 near
			# leaves and the authored middle/far visible crowns remain untouched.
			(root.get_node("ShadowCanopy") as MeshInstance3D).mesh = (root.get_node(SHADOW_CANOPY_LOD+"Canopy") as MeshInstance3D).mesh
		var envelope := JSON.parse_string(FileAccess.get_file_as_string(ASSET_ROOT+"PHYSICS_ENVELOPE.json")) as Dictionary
		var height: float = envelope[path.get_file().get_basename()].collision_height
		var body := StaticBody3D.new(); body.name = "TreeTrunkCollision"
		var collision := CollisionShape3D.new(); collision.name = "CollisionShape3D"; var shape := CylinderShape3D.new()
		shape.radius = .37; shape.height = height; collision.shape = shape; collision.position.y = height*.5
		body.add_child(collision); root.add_child(body)
		root.set_meta("asset_source",path); root.set_meta("mesh_batches",4 if dead else 8)
		root.set_meta("visible_mesh_batches",3 if dead else 6)
		root.set_meta("shadow_mesh_batches",1 if dead else 2)
		root.set_meta("shadow_canopy_lod",SHADOW_CANOPY_LOD if not dead else "none")
		root.set_meta("near_far_distance",MID_END); root.set_meta("near_mid_distance",NEAR_END)
		root.set_meta("botanical_high_fidelity",true)
		root.set_meta("dense_layered_crown",not dead)
		_own_children(root,root)
		var scene := PackedScene.new(); scene.pack(root); tree_cache[key] = scene; root.free()
	return tree_cache[key].instantiate() as Node3D
