extends RefCounted
# Cosmetic understory only: no collision, navigation, report or route changes.
# Authored curved blades/fern pinnae/rolled laminae and weathered stones, local batches.
const CELL_SIZE := 16.0
const ASSET_ROOT := "res://assets/refined/environment/"
static var _mesh_cache: Dictionary = {}
static var _material_cache: Dictionary = {}
static var _motion_time := 0.0

static func _texture(path: String) -> Texture2D:
	return load(path) as Texture2D if ResourceLoader.exists(path) else null

static func _pbr_texture(alias: String) -> Texture2D:
	var path := ""
	if alias.begins_with("stone_"):
		var source_path := ASSET_ROOT+"textures/STONE_PBR_SOURCE.json"
		assert(FileAccess.file_exists(source_path),"Verified stone material source manifest is required")
		var source := JSON.parse_string(FileAccess.get_file_as_string(source_path)) as Dictionary
		for item in source.maps:
			if String(item.path).get_file().get_basename() == alias: path = item.path; break
	else:
		var source_path := ASSET_ROOT+"textures/PBR_TEXTURE_BINDINGS.json"
		assert(FileAccess.file_exists(source_path),"Verified environment material binding manifest is required")
		var bindings := JSON.parse_string(FileAccess.get_file_as_string(source_path)) as Dictionary
		assert(bindings.has(alias),"Missing verified material binding: "+alias)
		path = bindings[alias] if bindings[alias] is String else bindings[alias].path
	assert(not path.is_empty(),"Scanned material binding must resolve: "+alias)
	if not path.begins_with("res://"):
		path = "res://"+path if path.begins_with("assets/") else ASSET_ROOT+"textures/"+path
	var texture := load(path) as Texture2D
	assert(texture != null and texture.get_width() >= 4096,"Actual 4K PBR texture dimensions are required: "+path)
	return texture

static func ground_material() -> ShaderMaterial:
	if _material_cache.has("ground"): return _material_cache.ground
	var shader := Shader.new()
	shader.code = """shader_type spatial;
uniform sampler2D floor_color : source_color, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D floor_normal : hint_normal, filter_linear_mipmap_anisotropic, repeat_enable;
uniform sampler2D floor_roughness : filter_linear_mipmap_anisotropic, repeat_enable;
uniform float motion_time=0.0;
varying vec3 world_position;
float hash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453);}
float noise(vec2 p){vec2 i=floor(p);vec2 f=fract(p);f=f*f*(3.-2.*f);return mix(mix(hash(i),hash(i+vec2(1,0)),f.x),mix(hash(i+vec2(0,1)),hash(i+vec2(1,1)),f.x),f.y);}
void vertex(){world_position=(MODEL_MATRIX*vec4(VERTEX,1.)).xyz;}
void fragment(){
 vec2 p=world_position.xz;vec2 uv=p*.476190476;
 float wet=smoothstep(.48,.70,noise(p*.12));
 vec3 soil=texture(floor_color,uv).rgb;
 ALBEDO=soil*mix(.91,.64,wet);
 // Wet dirt remains a rough material; polished puddles are separate geometry.
 // A roughness floor prevents the scanned micro-normal becoming white sparkle.
 ROUGHNESS=max(.40,mix(texture(floor_roughness,uv).r*.91,.32,wet*.70));SPECULAR=.30;
 NORMAL_MAP=texture(floor_normal,uv).rgb;NORMAL_MAP_DEPTH=mix(.40,.28,wet);
}
"""
	var m := ShaderMaterial.new(); m.shader = shader
	m.set_shader_parameter("floor_color",_pbr_texture("floor_basecolor"))
	m.set_shader_parameter("floor_normal",_pbr_texture("floor_normal"))
	m.set_shader_parameter("floor_roughness",_pbr_texture("floor_roughness"))
	m.set_shader_parameter("motion_time",_motion_time)
	_material_cache.ground = m; return m

static func _material(kind: String) -> Material:
	if _material_cache.has(kind): return _material_cache[kind]
	if kind == "stone":
		var m := StandardMaterial3D.new()
		m.albedo_color = Color(.65,.70,.62)
		m.albedo_texture = _pbr_texture("stone_basecolor")
		m.roughness_texture = _pbr_texture("stone_roughness")
		m.roughness = .62; m.normal_enabled = true; m.normal_scale = .7
		m.normal_texture = _pbr_texture("stone_normal")
		m.uv1_triplanar = true; m.uv1_triplanar_sharpness = 5.0; m.uv1_scale = Vector3(.667,.667,.667)
		_material_cache[kind] = m; return m
	var shader := Shader.new()
	if kind == "water":
		shader.code = """shader_type spatial;
uniform float motion_time=0.0;
varying vec3 world_position;
void vertex(){world_position=(MODEL_MATRIX*vec4(VERTEX,1.)).xyz;}
void fragment(){vec2 p=world_position.xz;
 float ripple=sin(length(fract(p*.66)-.5)*56.-motion_time*9.);
 ALBEDO=vec3(.065,.088,.09);ROUGHNESS=.12;SPECULAR=.85;
 NORMAL_MAP=vec3(.5+.022*cos(p.x*31.+motion_time*4.)*ripple,.5+.022*sin(p.y*29.-motion_time*3.)*ripple,.999);
}
"""
	else:
		shader.code = """shader_type spatial; render_mode cull_disabled;
uniform float motion_time=0.0;
uniform bool dry_leaf=false;
uniform bool grass_blade=false;
uniform sampler2D leaf_color : source_color, filter_linear_mipmap, repeat_disable;
uniform sampler2D leaf_normal : hint_normal, filter_linear_mipmap, repeat_disable;
varying vec3 plant_color;
void vertex(){plant_color=COLOR.rgb;vec3 world=(MODEL_MATRIX*vec4(VERTEX,1.)).xyz;
 float bend=sin(motion_time*1.5+world.x*.21+world.z*.14)*.024;
 if(!dry_leaf){VERTEX.x+=bend*max(VERTEX.y,0.);VERTEX.z+=sin(motion_time*1.1+world.z*.22)*.01*max(VERTEX.y,0.);}}
void fragment(){
 vec3 veins=texture(leaf_color,UV).rgb;
 if(UV.x>1.5){ALBEDO=plant_color;}
 else if(dry_leaf){ALBEDO=plant_color*(.77+veins.g*.8);}
 else if(grass_blade){ALBEDO=plant_color*mix(.68,1.13,UV.y);}
 else{ALBEDO=veins*mix(vec3(.8),plant_color/vec3(.19,.32,.065),.35);}
 ROUGHNESS=dry_leaf?.64:.55;SPECULAR=.29;
 NORMAL_MAP=UV.x>1.5?vec3(.5,.5,1.):texture(leaf_normal,UV).rgb;NORMAL_MAP_DEPTH=.7;
 BACKLIGHT=dry_leaf?vec3(.018):vec3(.07,.12,.027);
}
"""
	var m := ShaderMaterial.new(); m.shader = shader
	m.set_shader_parameter("motion_time",_motion_time)
	if kind != "water":
		m.set_shader_parameter("dry_leaf",kind == "leaf"); m.set_shader_parameter("grass_blade",kind == "grass")
		m.set_shader_parameter("leaf_color",_texture(ASSET_ROOT+"leaf_venation_color.png"))
		m.set_shader_parameter("leaf_normal",_texture(ASSET_ROOT+"leaf_venation_normal.png"))
	_material_cache[kind] = m; return m

static func set_motion_time(value: float) -> void:
	_motion_time = value
	for kind in _material_cache:
		if _material_cache[kind] is ShaderMaterial:
			(_material_cache[kind] as ShaderMaterial).set_shader_parameter("motion_time",value)

static func _extract_meshes(node: Node) -> void:
	for child in node.get_children():
		if child is MeshInstance3D: _mesh_cache[String(child.name)] = child.mesh
		else: _extract_meshes(child)

static func _mesh(kind: String, variant: int = 0) -> Mesh:
	if _mesh_cache.is_empty():
		var packed := load(ASSET_ROOT+"forest_understory_kit.glb") as PackedScene
		assert(packed != null,"Botanical understory kit must be imported")
		var imported := packed.instantiate(); _extract_meshes(imported); imported.free()
	var name_lookup := {"leaf":"LitterLeaf","stone":"Stone","grass":"GrassClump","fern":"Fern","bush":"Shrub","water":"Puddle"}
	var sizes := {"leaf":4,"stone":4,"grass":3,"fern":3,"bush":2,"water":1}
	var key: String = name_lookup[kind]
	if kind != "water": key += str(posmod(variant,sizes[kind])+1)
	assert(_mesh_cache.has(key),"Missing authored understory mesh: "+key)
	return _mesh_cache[key]

static func build(seed_value: int = 731) -> Node3D:
	var root := Node3D.new(); root.name = "RefinedTerrainDetails"
	var rng := RandomNumberGenerator.new(); rng.seed = seed_value
	var groups: Dictionary = {}
	var counts := {"leaf":1800,"grass":940,"fern":145,"bush":110,"stone":180,"water":32}
	var actual_counts := {"leaf":0,"grass":0,"fern":0,"bush":0,"stone":0,"water":0}
	for kind in counts:
		for i in range(counts[kind]):
			var p := Vector3(rng.randf_range(-82,82),.008,rng.randf_range(-82,82))
			if Vector2(p.x,p.z).length() < (8.0 if kind in ["bush","fern"] else 2.0): continue
			if kind in ["stone","bush","fern"]:
				var clear := false
				for end in [Vector2(-24,-28),Vector2(35,-12),Vector2(22,34),Vector2(72,65)]:
					var v := Vector2(p.x,p.z); var t := clampf(v.dot(end)/end.length_squared(),0,1)
					if v.distance_to(end*t) < 2.4: clear = true
				if clear: continue
			var cell := Vector2i(floori(p.x/CELL_SIZE),floori(p.z/CELL_SIZE))
			var key := "%s_%d_%d" % [kind,cell.x,cell.y]
			if not groups.has(key): groups[key] = {"kind":kind,"cell":cell,"variant":absi(cell.x*7+cell.y*13),"transforms":[],"colors":[]}
			var scale_value := rng.randf_range(.7,1.55)
			var scale_vector := Vector3(scale_value,rng.randf_range(.78,1.2),scale_value*rng.randf_range(.8,1.2))
			if kind == "water": scale_vector = Vector3(rng.randf_range(.7,2.5),1,rng.randf_range(.7,1.8))
			var local := p-Vector3(cell.x*CELL_SIZE,0,cell.y*CELL_SIZE)
			groups[key].transforms.append(Transform3D(Basis(Vector3.UP,rng.randf_range(0,TAU)).scaled(scale_vector),local))
			groups[key].colors.append(Color(rng.randf_range(.68,1.05),rng.randf_range(.68,1.03),rng.randf_range(.65,1.02)))
			actual_counts[kind] += 1
	for key in groups:
		var data: Dictionary = groups[key]; var multi := MultiMesh.new()
		multi.transform_format = MultiMesh.TRANSFORM_3D; multi.use_colors = true
		multi.mesh = _mesh(data.kind,data.variant); multi.instance_count = data.transforms.size()
		for i in range(multi.instance_count):
			multi.set_instance_transform(i,data.transforms[i]); multi.set_instance_color(i,data.colors[i])
		var part := MultiMeshInstance3D.new(); part.name = key; part.multimesh = multi; part.material_override = _material(data.kind)
		part.position = Vector3(data.cell.x*CELL_SIZE,0,data.cell.y*CELL_SIZE)
		part.visibility_range_end = 24.0 if data.kind in ["leaf","grass","stone"] else 46.0
		part.visibility_range_end_margin = 5.0
		part.lod_bias = 1000.0
		part.extra_cull_margin = .12; part.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		root.add_child(part)
	root.set_meta("spatial_cell_size",CELL_SIZE); root.set_meta("cosmetic_only",true)
	root.set_meta("detail_counts",actual_counts); root.set_meta("requested_detail_counts",counts); root.set_meta("spatial_batch_count",groups.size())
	root.set_meta("botanical_high_fidelity",true)
	return root
