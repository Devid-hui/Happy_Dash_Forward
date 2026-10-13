extends RefCounted
# Do not load the large scenes here: read source headers and import/remap metadata.
# This catches delivery/import failures, not renderer, driver or every glTF error.
const MANIFEST_PATH := "res://assets/refined/RUNTIME_ASSET_PATHS.json"
const LFS_HEADER := "version https://git-lfs.github.com/spec/v1"

static func _issue(code: String, path: String) -> Dictionary:
	var messages := {
		"missing": "文件缺失",
		"unreadable": "文件无法读取",
		"lfs_pointer": "尚未下载 Git LFS 大文件",
		"invalid_glb": "模型文件不完整或格式错误",
		"invalid_texture": "材质图片不完整或格式错误",
		"invalid_json": "资源清单格式错误",
		"not_imported": "资源尚未完成 Godot 导入",
		"import_cache_missing": "Godot 导入缓存缺失",
		"invalid_import": "Godot 导入信息损坏",
		"manifest_invalid": "运行资源清单缺失或格式错误",
	}
	return {"code": code, "path": path, "message": messages.get(code, "资源尚未准备好")}

static func _source_problem(path: String, kind: String) -> String:
	var file := FileAccess.open(path, FileAccess.READ)
	if file == null: return "unreadable"
	var length := file.get_length()
	var header := file.get_buffer(mini(256, length))
	if header.slice(0, LFS_HEADER.length()) == LFS_HEADER.to_ascii_buffer(): return "lfs_pointer"
	if kind == "glb":
		if length < 20 or header.slice(0, 4).get_string_from_ascii() != "glTF": return "invalid_glb"
		file.seek(4)
		if file.get_32() != 2 or file.get_32() != length: return "invalid_glb"
	elif kind == "texture":
		var extension := path.get_extension().to_lower()
		if extension == "png" and (length < 24 or header.slice(0, 8) != PackedByteArray([137, 80, 78, 71, 13, 10, 26, 10])):
			return "invalid_texture"
		if extension in ["jpg", "jpeg"] and (length < 4 or header.slice(0, 3) != PackedByteArray([255, 216, 255])):
			return "invalid_texture"
	elif kind == "json":
		file.seek(0)
		if not JSON.parse_string(file.get_as_text()) is Dictionary: return "invalid_json"
	return ""

static func _import_problem(path: String, kind: String, source_exists: bool) -> String:
	var expected := "PackedScene" if kind == "glb" else "CompressedTexture2D"
	var import_path := path + ".import"
	if not FileAccess.file_exists(import_path):
		# Exporters may resolve the original name through a packaged remap. Raw
		# project files still require import metadata, even when exists() sees GLB.
		if not source_exists and ResourceLoader.exists(path, expected): return ""
		return "not_imported" if source_exists else "missing"
	var config := ConfigFile.new()
	if config.load(import_path) != OK or not config.has_section("remap"): return "invalid_import"
	if str(config.get_value("remap", "type", "")) != expected: return "invalid_import"
	var destinations: Array[String] = []
	var direct := str(config.get_value("remap", "path", ""))
	if not direct.is_empty(): destinations.append(direct)
	# VRAM textures can have path.s3tc/path.etc2/path.astc rather than path.
	for key in config.get_section_keys("remap"):
		if key.begins_with("path.") and OS.has_feature(key.trim_prefix("path.")):
			var destination := str(config.get_value("remap", key, ""))
			if not destination.is_empty(): destinations.append(destination)
	if destinations.is_empty(): return "invalid_import"
	for destination in destinations:
		if FileAccess.file_exists(destination) or ResourceLoader.exists(destination, expected): return ""
	return "import_cache_missing"

static func check_runtime(manifest_path: String = MANIFEST_PATH) -> Dictionary:
	var issues: Array[Dictionary] = []
	var checked := 0
	if not FileAccess.file_exists(manifest_path):
		issues.append(_issue("manifest_invalid", manifest_path))
		return {"ok": false, "checked": checked, "issues": issues}
	var manifest = JSON.parse_string(FileAccess.get_file_as_string(manifest_path))
	if not manifest is Dictionary or manifest.get("schema_version") != 1 or not manifest.get("resources") is Array or manifest.resources.is_empty():
		issues.append(_issue("manifest_invalid", manifest_path))
		return {"ok": false, "checked": checked, "issues": issues}
	for entry in manifest.resources:
		if not entry is Dictionary or not entry.get("path") is String or not ["glb", "texture", "json"].has(entry.get("kind")):
			issues.append(_issue("manifest_invalid", manifest_path))
			break
		var path: String = entry.path
		var kind: String = entry.kind
		checked += 1
		var source_exists := FileAccess.file_exists(path)
		var problem := _source_problem(path, kind) if source_exists else ""
		if problem.is_empty():
			if kind == "json": problem = "missing" if not source_exists else ""
			else: problem = _import_problem(path, kind, source_exists)
		if not problem.is_empty(): issues.append(_issue(problem, path))
	return {"ok": issues.is_empty(), "checked": checked, "issues": issues}
