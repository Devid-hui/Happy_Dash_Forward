extends Node

const READINESS := preload("res://scripts/core/asset_readiness.gd")
const MAIN := preload("res://scripts/core/main.gd")

class ProbeMain extends MAIN:
	var spawn_count := 0
	func _spawn_world() -> void:
		spawn_count += 1
		screen = "gameplay"

var fixture_root := ""

func _ready() -> void:
	call_deferred("run_checks")

func _write(path: String, contents: String) -> void:
	var file := FileAccess.open(path, FileAccess.WRITE)
	assert(file != null)
	file.store_string(contents)
	file.close()

func _glb(path: String) -> void:
	# This fixture exercises delivery/header checks, not the glTF importer.
	var file := FileAccess.open(path, FileAccess.WRITE)
	assert(file != null)
	file.store_buffer("glTF".to_ascii_buffer())
	file.store_32(2)
	file.store_32(24)
	file.store_32(4)
	file.store_32(0x4e4f534a)
	file.store_buffer("{}  ".to_ascii_buffer())
	file.close()

func _manifest(path: String, asset: String) -> void:
	_write(path, JSON.stringify({"schema_version": 1, "resources": [{"path": asset, "kind": "glb"}]}))

func _single_problem(manifest: String, code: String) -> void:
	var report: Dictionary = READINESS.check_runtime(manifest)
	assert(not report.ok and report.issues.size() == 1)
	assert(report.issues[0].code == code, "%s must be distinguishable: %s" % [code, report])

func _delivery_fixture(asset: String, code: String) -> void:
	for path in [asset, asset + ".import"]:
		if FileAccess.file_exists(path): assert(DirAccess.remove_absolute(path) == OK)
	if code == "missing": return
	if code == "lfs_pointer":
		_write(asset, "version https://git-lfs.github.com/spec/v1\noid sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\nsize 24\n")
		return
	if code == "invalid_glb":
		_write(asset, "not a downloaded GLB")
		return
	_glb(asset)
	if code == "import_cache_missing":
		var imports := ConfigFile.new()
		imports.set_value("remap", "type", "PackedScene")
		imports.set_value("remap", "path", fixture_root.path_join("missing-cache.tscn"))
		assert(imports.save(asset + ".import") == OK)

func _find_button(node: Node, caption: String) -> Button:
	if node is Button and node.text == caption: return node
	for child in node.get_children():
		var result := _find_button(child, caption)
		if result != null: return result
	return null

func _settle() -> void:
	await get_tree().process_frame
	await get_tree().process_frame
	await get_tree().process_frame

func _capture_repair_screen() -> void:
	var directory := OS.get_environment("HDF_RESOURCE_CAPTURE_DIR")
	if directory.is_empty() or DisplayServer.get_name() == "headless": return
	assert(DirAccess.make_dir_recursive_absolute(directory) == OK)
	await RenderingServer.frame_post_draw
	assert(get_viewport().get_texture().get_image().save_png(directory.path_join("asset-repair-screen.png")) == OK)

func _remove_fixtures() -> void:
	for filename in DirAccess.get_files_at(fixture_root):
		assert(DirAccess.remove_absolute(fixture_root.path_join(filename)) == OK)
	assert(DirAccess.remove_absolute(fixture_root) == OK)

func run_checks() -> void:
	fixture_root = "user://asset-readiness-contract-%d" % Time.get_ticks_usec()
	assert(DirAccess.make_dir_recursive_absolute(fixture_root) == OK)
	var asset := fixture_root.path_join("model.glb")
	var manifest := fixture_root.path_join("manifest.json")
	_manifest(manifest, asset)
	_single_problem(manifest, "missing")
	_write(asset, "version https://git-lfs.github.com/spec/v1\noid sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\nsize 24\n")
	_single_problem(manifest, "lfs_pointer")
	_write(asset, "not a downloaded GLB")
	_single_problem(manifest, "invalid_glb")
	_glb(asset)
	_single_problem(manifest, "not_imported")
	var imports := ConfigFile.new()
	imports.set_value("remap", "type", "PackedScene")
	imports.set_value("remap", "path", fixture_root.path_join("missing-cache.tscn"))
	assert(imports.save(asset + ".import") == OK)
	_single_problem(manifest, "import_cache_missing")
	# All failure cases must stop the actual Main transition and retain navigation.
	var main := ProbeMain.new()
	main.asset_manifest_path = manifest
	add_child(main)
	await _settle()
	main._show_selection()
	main._on_skill_pressed("echo")
	main._on_skill_pressed("salt")
	for code in ["missing", "lfs_pointer", "invalid_glb", "not_imported", "import_cache_missing"]:
		_delivery_fixture(asset, code)
		main._start_game()
		await _settle()
		assert(main.spawn_count == 0 and main.world == null)
		assert(main.screen == "resource_error" and not main.transitioning)
		assert(is_instance_valid(main.root_ui) and not get_tree().paused)
		_find_button(main, "返回选科").pressed.emit()
		await _settle()
		assert(main.screen == "selection" and main.selected == ["echo", "salt"])
	main._start_game()
	await _settle()
	await _capture_repair_screen()
	var retry := _find_button(main, "重新检查并进入")
	assert(retry != null)
	retry.pressed.emit()
	await _settle()
	assert(main.spawn_count == 0 and main.screen == "resource_error")
	_find_button(main, "返回选科").pressed.emit()
	await _settle()
	assert(main.screen == "selection" and main.selected == ["echo", "salt"])
	main._start_game()
	await _settle()
	_find_button(main, "返回主菜单").pressed.emit()
	await _settle()
	assert(main.screen == "menu" and _find_button(main, "开始试炼") != null)
	# Repair only disposable user:// files; production model bytes stay untouched.
	var node := Node3D.new()
	var packed := PackedScene.new()
	assert(packed.pack(node) == OK)
	node.free()
	var cache := fixture_root.path_join("model-imported.tscn")
	assert(ResourceSaver.save(packed, cache) == OK)
	imports.set_value("remap", "path", cache)
	assert(imports.save(asset + ".import") == OK)
	assert(READINESS.check_runtime(manifest).ok)
	# Exported packages can retain the remap/cache without the original GLB.
	assert(DirAccess.remove_absolute(asset) == OK)
	assert(READINESS.check_runtime(manifest).ok, "valid imported scene does not require a raw GLB inside PCK")
	main._start_game()
	await _settle()
	assert(main.spawn_count == 1 and main.screen == "gameplay")
	main.queue_free()
	await _settle()
	var production: Dictionary = READINESS.check_runtime()
	assert(production.ok and production.checked >= 36, "current production models/PBR/imports must pass: %s" % production)
	var declared: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(READINESS.MANIFEST_PATH))
	var paths: Array[String] = []
	for entry in declared.resources: paths.append(entry.path)
	var bindings: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://assets/refined/environment/textures/PBR_TEXTURE_BINDINGS.json"))
	for alias in bindings:
		assert(paths.has("res://assets/refined/environment/textures/" + str(bindings[alias])), "every active scanned PBR binding must be checked")
	var stone: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://assets/refined/environment/textures/STONE_PBR_SOURCE.json"))
	for entry in stone.maps: assert(paths.has("res://" + str(entry.path)))
	_remove_fixtures()
	print("ASSET READINESS PASS: delivery fixtures, prevented empty World, recoverable menu, packaged remap, %d production resources" % production.checked)
	get_tree().quit(0)
