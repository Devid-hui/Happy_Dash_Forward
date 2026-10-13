extends Node
# Same imported asset, with two close viewpoints exposing the support thumb.
const STUDIO := preload("res://tests/anatomical_spectra_preview.gd")

func _ready() -> void:
	assert(DisplayServer.get_name() != "headless")
	var directory := OS.get_environment("HDF_THUMB_REVIEW_DIR")
	assert(not directory.is_empty())
	DirAccess.make_dir_recursive_absolute(directory)
	get_window().size = Vector2i(1920,1080)
	var studio := STUDIO.new()
	add_child(studio)
	studio.set_process(false)
	for view in ["front_side","underside","first_person"]:
		if view == "first_person":
			studio._switch(3)
		else:
			studio._switch(4)
			studio.camera.fov = 48.0
			var origin := Vector3(-.22,1.035,-.23) if view == "front_side" else Vector3(-.18,.90,-.22)
			studio.camera.look_at_from_position(origin,Vector3(-.035,.998,-.132))
		for warmup in range(32): await RenderingServer.frame_post_draw
		var frame := get_viewport().get_texture().get_image()
		assert(frame.get_size() == Vector2i(1920,1080))
		assert(frame.save_png(directory.path_join(view+".png")) == OK)
		print("LEFT THUMB CAPTURE ",view)
	studio.free()
	for cleanup in range(3): await get_tree().process_frame
	print("LEFT THUMB REVIEW COMPLETE: 3 native 1080p views")
	get_tree().quit(0)
