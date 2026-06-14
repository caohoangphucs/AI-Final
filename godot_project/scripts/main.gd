extends Node3D

@onready var campus: Node = $Campus
@onready var spawn: Marker3D = $Spawn
@onready var sun: DirectionalLight3D = $Sun
@onready var world_environment: WorldEnvironment = $WorldEnvironment
@onready var path_bot: CharacterBody3D = $PathBot

const NON_COLLIDABLE_PREFIXES := [
	"StairEntry_",
	"BridgeEntry_",
	"Cut_",
]

const NON_COLLIDABLE_NAME_PARTS := [
	"_Stair_Wall_",
	"A1_Tower_Canopy_Col",
]

var _algorithm_menu_layer: CanvasLayer
var _algorithm_menu_panel: PanelContainer
var _comparison_layer: CanvasLayer
var _pending_selection: String = ""
var _next_click_is_start := true


func _ready() -> void:
	_configure_lighting()
	_build_collisions(campus)
	_place_player()
	if path_bot != null and not path_bot.comparison_ready.is_connected(_on_comparison_ready):
		path_bot.comparison_ready.connect(_on_comparison_ready)
	if path_bot != null and not path_bot.search_result_ready.is_connected(_on_search_result_ready):
		path_bot.search_result_ready.connect(_on_search_result_ready)
	_setup_hud()
	_show_algorithm_menu()
	print("Main: press X to toggle campus model visibility")


func _setup_hud() -> void:
	var hud := CanvasLayer.new()
	hud.layer = 50
	add_child(hud)
	
	var margin := MarginContainer.new()
	margin.set_anchors_preset(Control.PRESET_BOTTOM_WIDE)
	margin.grow_vertical = Control.GROW_DIRECTION_BEGIN
	margin.add_theme_constant_override("margin_bottom", 36)
	margin.mouse_filter = Control.MOUSE_FILTER_IGNORE
	hud.add_child(margin)
	
	var label := Label.new()
	label.text = "Bấm [ESC] để vào Menu Chính\nBấm [X] để ẩn/hiện tường"
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label.add_theme_font_size_override("font_size", 22)
	label.add_theme_color_override("font_color", Color(1.0, 0.92, 0.2, 1.0))
	label.add_theme_color_override("font_outline_color", Color(0.0, 0.0, 0.0, 1.0))
	label.add_theme_constant_override("outline_size", 8)
	label.add_theme_color_override("font_shadow_color", Color(0.0, 0.0, 0.0, 0.6))
	label.add_theme_constant_override("shadow_offset_x", 2)
	label.add_theme_constant_override("shadow_offset_y", 2)
	label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	margin.add_child(label)


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.pressed and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		var result := _get_camera_center_raycast()
		if not result.is_empty():
			if _pending_selection == "start" and event.button_index == MOUSE_BUTTON_LEFT:
				if path_bot: path_bot.call("set_custom_start", result.position)
				_pending_selection = ""
			elif _pending_selection == "goal" and event.button_index == MOUSE_BUTTON_RIGHT:
				if path_bot: path_bot.call("set_custom_goal", result.position)
				_pending_selection = ""
			elif _pending_selection == "" or _pending_selection == "point":
				if event.button_index == MOUSE_BUTTON_LEFT:
					if path_bot: path_bot.call("set_custom_start", result.position)
					_pending_selection = ""
				elif event.button_index == MOUSE_BUTTON_RIGHT:
					if path_bot: path_bot.call("set_custom_goal", result.position)
					_pending_selection = ""

	if event is InputEventKey and event.pressed and not event.echo:
		match event.keycode:
			KEY_X:
				campus.visible = not campus.visible
				print("Main: campus model %s" % ("visible" if campus.visible else "hidden"))
			KEY_ESCAPE:
				_show_algorithm_menu()
				print("Main: returned to algorithm menu")


func _get_camera_center_raycast() -> Dictionary:
	var camera := $Player/Pivot/Camera3D as Camera3D
	if not camera:
		return {}
	var space_state := get_world_3d().direct_space_state
	var center := get_viewport().get_visible_rect().size / 2.0
	var from := camera.project_ray_origin(center)
	var to := from + camera.project_ray_normal(center) * 1000.0
	var query := PhysicsRayQueryParameters3D.create(from, to)
	return space_state.intersect_ray(query)


func _place_player() -> void:
	var player := $Player
	player.global_position = spawn.global_position


func _build_collisions(node: Node) -> void:
	for child in node.get_children():
		_build_collisions(child)

	if node is MeshInstance3D and node.mesh:
		if not _should_create_collision(node):
			return
		node.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		var has_static := false
		for child in node.get_children():
			if child is StaticBody3D:
				has_static = true
				break
		if not has_static:
			node.create_trimesh_collision()


func _should_create_collision(node: MeshInstance3D) -> bool:
	for prefix in NON_COLLIDABLE_PREFIXES:
		if node.name.begins_with(prefix):
			return false
	for part in NON_COLLIDABLE_NAME_PARTS:
		if node.name.contains(part):
			return false
	return true


func _configure_lighting() -> void:
	var env := world_environment.environment
	env.background_mode = Environment.BG_COLOR
	env.background_color = Color(0.72, 0.78, 0.86, 1.0)
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.92, 0.94, 0.98, 1.0)
	env.ambient_light_energy = 1.35
	env.tonemap_mode = Environment.TONE_MAPPER_REINHARDT
	sun.light_energy = 0.22
	sun.shadow_enabled = false


func _show_algorithm_menu() -> void:
	if path_bot == null:
		return
	path_bot.call("return_to_menu_state")
	if is_instance_valid(_algorithm_menu_layer):
		_algorithm_menu_layer.queue_free()
	if is_instance_valid(_comparison_layer):
		_comparison_layer.queue_free()

	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	_algorithm_menu_layer = CanvasLayer.new()
	_algorithm_menu_layer.layer = 200
	add_child(_algorithm_menu_layer)

	var backdrop := ColorRect.new()
	backdrop.set_anchors_preset(Control.PRESET_FULL_RECT)
	backdrop.color = Color(0.03, 0.05, 0.08, 0.78)
	_algorithm_menu_layer.add_child(backdrop)

	var root := MarginContainer.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.add_theme_constant_override("margin_left", 36)
	root.add_theme_constant_override("margin_top", 36)
	root.add_theme_constant_override("margin_right", 36)
	root.add_theme_constant_override("margin_bottom", 36)
	backdrop.add_child(root)

	var center := CenterContainer.new()
	root.add_child(center)

	var group_info_margin := MarginContainer.new()
	group_info_margin.size_flags_horizontal = Control.SIZE_SHRINK_END
	group_info_margin.size_flags_vertical = Control.SIZE_SHRINK_END
	root.add_child(group_info_margin)
	
	var group_info_panel := PanelContainer.new()
	var group_style := StyleBoxFlat.new()
	group_style.bg_color = Color(0.1, 0.15, 0.25, 0.95)
	group_style.corner_radius_top_left = 12
	group_style.corner_radius_top_right = 12
	group_style.corner_radius_bottom_left = 12
	group_style.corner_radius_bottom_right = 12
	group_style.border_width_left = 2
	group_style.border_width_top = 2
	group_style.border_width_right = 2
	group_style.border_width_bottom = 2
	group_style.border_color = Color(1.0, 0.85, 0.3, 1.0)
	group_info_panel.add_theme_stylebox_override("panel", group_style)
	group_info_margin.add_child(group_info_panel)
	
	var group_info_padding := MarginContainer.new()
	group_info_padding.add_theme_constant_override("margin_left", 20)
	group_info_padding.add_theme_constant_override("margin_right", 20)
	group_info_padding.add_theme_constant_override("margin_top", 16)
	group_info_padding.add_theme_constant_override("margin_bottom", 16)
	group_info_panel.add_child(group_info_padding)
	
	var group_info_label := Label.new()
	group_info_label.text = "NHÓM THỰC HIỆN:\n\n• Cao Hoàng Phúc (24110303)\n• Nguyễn Công Khoa (24110254)\n• Phan Thị Thùy Linh (24110271)"
	group_info_label.add_theme_color_override("font_color", Color(1.0, 0.98, 0.6))
	group_info_label.add_theme_font_size_override("font_size", 18)
	group_info_label.add_theme_color_override("font_shadow_color", Color(0, 0, 0, 0.8))
	group_info_label.add_theme_constant_override("shadow_offset_x", 2)
	group_info_label.add_theme_constant_override("shadow_offset_y", 2)
	group_info_padding.add_child(group_info_label)

	_algorithm_menu_panel = PanelContainer.new()
	_algorithm_menu_panel.custom_minimum_size = Vector2(1040, 700)
	center.add_child(_algorithm_menu_panel)

	var panel_style := StyleBoxFlat.new()
	panel_style.bg_color = Color(0.93, 0.96, 0.99, 0.97)
	panel_style.border_width_left = 2
	panel_style.border_width_top = 2
	panel_style.border_width_right = 2
	panel_style.border_width_bottom = 2
	panel_style.border_color = Color(0.13, 0.21, 0.32, 1.0)
	panel_style.corner_radius_top_left = 12
	panel_style.corner_radius_top_right = 12
	panel_style.corner_radius_bottom_right = 12
	panel_style.corner_radius_bottom_left = 12
	_algorithm_menu_panel.add_theme_stylebox_override("panel", panel_style)

	var shell := MarginContainer.new()
	shell.add_theme_constant_override("margin_left", 26)
	shell.add_theme_constant_override("margin_top", 22)
	shell.add_theme_constant_override("margin_right", 26)
	shell.add_theme_constant_override("margin_bottom", 22)
	_algorithm_menu_panel.add_child(shell)

	var content := VBoxContainer.new()
	content.add_theme_constant_override("separation", 14)
	shell.add_child(content)

	var main_title := Label.new()
	main_title.text = "MÔ PHỎNG TÌM ĐƯỜNG ĐI\nTRONG KHÔNG GIAN 3D Ở TRƯỜNG HỌC"
	main_title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	main_title.add_theme_font_size_override("font_size", 30)
	main_title.add_theme_color_override("font_color", Color(0.07, 0.18, 0.42, 1.0))
	main_title.add_theme_color_override("font_outline_color", Color(1.0, 1.0, 1.0, 0.0))
	main_title.add_theme_color_override("font_shadow_color", Color(0.12, 0.32, 0.78, 0.18))
	main_title.add_theme_constant_override("shadow_offset_x", 0)
	main_title.add_theme_constant_override("shadow_offset_y", 3)
	content.add_child(main_title)

	var divider := ColorRect.new()
	divider.custom_minimum_size = Vector2(0.0, 2.0)
	divider.color = Color(0.07, 0.18, 0.42, 0.18)
	content.add_child(divider)

	var title := Label.new()
	title.text = "Chọn thuật toán đường đi"
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title.add_theme_font_size_override("font_size", 20)
	title.add_theme_color_override("font_color", Color(0.2, 0.25, 0.35, 1.0))
	content.add_child(title)

	var subtitle := Label.new()
	subtitle.text = "Nhấn vào một dòng trong bảng để PathBot bắt đầu chạy trực tiếp bằng GDScript."
	subtitle.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	subtitle.add_theme_font_size_override("font_size", 15)
	subtitle.add_theme_color_override("font_color", Color.BLACK)
	content.add_child(subtitle)

	var header_actions := HBoxContainer.new()
	header_actions.alignment = BoxContainer.ALIGNMENT_CENTER
	header_actions.add_theme_constant_override("separation", 24)
	content.add_child(header_actions)
	
	var btn_select := Button.new()
	btn_select.text = "Chọn điểm Start/End (↙ Click để ẩn menu)"
	btn_select.custom_minimum_size = Vector2(360, 42)
	btn_select.add_theme_color_override("font_color", Color(0.08, 0.35, 0.65))
	btn_select.pressed.connect(_on_set_point_from_menu)
	header_actions.add_child(btn_select)

	var table_frame := PanelContainer.new()
	var table_style := StyleBoxFlat.new()
	table_style.bg_color = Color(1.0, 1.0, 1.0, 0.72)
	table_style.corner_radius_top_left = 10
	table_style.corner_radius_top_right = 10
	table_style.corner_radius_bottom_left = 10
	table_style.corner_radius_bottom_right = 10
	table_style.border_width_left = 1
	table_style.border_width_top = 1
	table_style.border_width_right = 1
	table_style.border_width_bottom = 1
	table_style.border_color = Color(0.78, 0.83, 0.9, 1.0)
	table_frame.add_theme_stylebox_override("panel", table_style)
	table_frame.size_flags_vertical = Control.SIZE_EXPAND_FILL
	content.add_child(table_frame)

	var table_shell := MarginContainer.new()
	table_shell.add_theme_constant_override("margin_left", 18)
	table_shell.add_theme_constant_override("margin_top", 18)
	table_shell.add_theme_constant_override("margin_right", 18)
	table_shell.add_theme_constant_override("margin_bottom", 18)
	table_frame.add_child(table_shell)

	var table_content := VBoxContainer.new()
	table_content.add_theme_constant_override("separation", 8)
	table_shell.add_child(table_content)

	table_content.add_child(_make_algorithm_header_row())

	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	scroll.custom_minimum_size = Vector2(0.0, 420.0)
	table_content.add_child(scroll)

	var rows_box := VBoxContainer.new()
	rows_box.add_theme_constant_override("separation", 8)
	rows_box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	rows_box.custom_minimum_size = Vector2(920.0, 0.0)
	scroll.add_child(rows_box)

	for row_variant in path_bot.call("get_algorithm_menu_rows"):
		rows_box.add_child(_make_algorithm_row(row_variant))

	var footer := Label.new()
	footer.text = "Bạn vẫn có thể đổi nhanh bằng phím 0-6 sau khi vào scene."
	footer.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	footer.add_theme_font_size_override("font_size", 14)
	footer.add_theme_color_override("font_color", Color.BLACK)
	content.add_child(footer)


func _on_set_start_from_menu() -> void:
	_pending_selection = "start"
	if is_instance_valid(_algorithm_menu_layer):
		_algorithm_menu_layer.queue_free()
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	print("Main: menu closed to select start point")


func _on_set_goal_from_menu() -> void:
	_pending_selection = "goal"
	if is_instance_valid(_algorithm_menu_layer):
		_algorithm_menu_layer.queue_free()
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	print("Main: menu closed to select goal point")


func _on_set_point_from_menu() -> void:
	_pending_selection = "point"
	if is_instance_valid(_algorithm_menu_layer):
		_algorithm_menu_layer.queue_free()
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED
	print("Main: menu closed - click L=Start R=End to select points")


func _on_algorithm_selected(algorithm_id: int) -> void:
	if path_bot != null:
		if algorithm_id == -1:
			path_bot.call("start_search_with_all")
		else:
			path_bot.call("start_search_with_algorithm", algorithm_id)
	if is_instance_valid(_algorithm_menu_layer):
		_algorithm_menu_layer.queue_free()
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED


func _make_text_label(text: String, font_size := 15, bold := false, min_width := 0.0, wrap := true) -> Label:
	var label := Label.new()
	label.text = text
	label.add_theme_font_size_override("font_size", font_size)
	label.add_theme_color_override("font_color", Color.BLACK)
	label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART if wrap else TextServer.AUTOWRAP_OFF
	if bold:
		label.modulate = Color(0.08, 0.08, 0.08, 1.0)
	if min_width > 0.0:
		label.custom_minimum_size = Vector2(min_width, 0.0)
	return label


func _make_algorithm_header_row() -> Control:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 16)
	row.add_child(_make_column_label("Phím", 70, true))
	row.add_child(_make_column_label("Thuật toán", 170, true))
	row.add_child(_make_column_label("Mô tả", 0, true, true))
	row.add_child(_make_column_label("Hành động", 120, true))
	return row


func _make_algorithm_row(row_data: Dictionary) -> Control:
	var wrapper := VBoxContainer.new()
	wrapper.add_theme_constant_override("separation", 8)
	wrapper.size_flags_horizontal = Control.SIZE_EXPAND_FILL

	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 16)
	row.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.custom_minimum_size = Vector2(920.0, 0.0)
	wrapper.add_child(row)

	row.add_child(_make_column_label(str(row_data.get("shortcut", "")), 70))
	row.add_child(_make_column_label(str(row_data.get("name", "")), 170))
	row.add_child(_make_column_label(str(row_data.get("description", "")), 0, false, true, true))

	var button := Button.new()
	button.text = "Chạy"
	button.custom_minimum_size = Vector2(120, 42)
	button.add_theme_color_override("font_color", Color.BLACK)
	button.pressed.connect(_on_algorithm_selected.bind(int(row_data.get("id", 0))))
	row.add_child(button)

	var separator := ColorRect.new()
	separator.custom_minimum_size = Vector2(0.0, 1.0)
	separator.color = Color(0.82, 0.85, 0.9, 1.0)
	wrapper.add_child(separator)
	return wrapper


func _make_column_label(text: String, width := 0.0, bold := false, expand := false, wrap := false) -> Label:
	var label := _make_text_label(text, 15 if not bold else 16, bold, 0.0, wrap)
	label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	if width > 0.0:
		label.custom_minimum_size = Vector2(width, 0.0)
	if expand:
		label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	return label


func _on_comparison_ready(rows: Array) -> void:
	_show_comparison_overlay(rows)


func _on_search_result_ready(result: Dictionary) -> void:
	_show_search_result_overlay(result)


func _show_comparison_overlay(rows: Array) -> void:
	if is_instance_valid(_comparison_layer):
		_comparison_layer.queue_free()
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE

	_comparison_layer = CanvasLayer.new()
	_comparison_layer.layer = 210
	add_child(_comparison_layer)

	var backdrop := ColorRect.new()
	backdrop.set_anchors_preset(Control.PRESET_FULL_RECT)
	backdrop.color = Color(0.02, 0.03, 0.05, 0.72)
	_comparison_layer.add_child(backdrop)

	var root := MarginContainer.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.add_theme_constant_override("margin_left", 24)
	root.add_theme_constant_override("margin_top", 24)
	root.add_theme_constant_override("margin_right", 24)
	root.add_theme_constant_override("margin_bottom", 24)
	backdrop.add_child(root)

	var center := CenterContainer.new()
	root.add_child(center)

	var panel := PanelContainer.new()
	panel.custom_minimum_size = Vector2(1180, 620)
	center.add_child(panel)

	var panel_style := StyleBoxFlat.new()
	panel_style.bg_color = Color(0.97, 0.98, 1.0, 0.99)
	panel_style.border_width_left = 2
	panel_style.border_width_top = 2
	panel_style.border_width_right = 2
	panel_style.border_width_bottom = 2
	panel_style.border_color = Color(0.12, 0.18, 0.28, 1.0)
	panel_style.corner_radius_top_left = 18
	panel_style.corner_radius_top_right = 18
	panel_style.corner_radius_bottom_right = 18
	panel_style.corner_radius_bottom_left = 18
	panel_style.shadow_color = Color(0.0, 0.0, 0.0, 0.18)
	panel_style.shadow_size = 12
	panel.add_theme_stylebox_override("panel", panel_style)

	var shell := MarginContainer.new()
	shell.add_theme_constant_override("margin_left", 28)
	shell.add_theme_constant_override("margin_top", 24)
	shell.add_theme_constant_override("margin_right", 28)
	shell.add_theme_constant_override("margin_bottom", 24)
	panel.add_child(shell)

	var content := VBoxContainer.new()
	content.add_theme_constant_override("separation", 16)
	shell.add_child(content)

	var title := _make_text_label("Bảng so sánh thuật toán", 30, true)
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	content.add_child(title)

	var subtitle := _make_text_label("Mỗi thuật toán đã chạy với một màu riêng trên PathBot và đường đi.", 15)
	subtitle.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	content.add_child(subtitle)

	var best_row := _find_best_comparison_row(rows)
	if not best_row.is_empty():
		content.add_child(_make_comparison_summary_card(best_row))

	content.add_child(_make_comparison_chart(rows))

	var table_frame := PanelContainer.new()
	var table_style := StyleBoxFlat.new()
	table_style.bg_color = Color(1.0, 1.0, 1.0, 0.82)
	table_style.border_width_left = 1
	table_style.border_width_top = 1
	table_style.border_width_right = 1
	table_style.border_width_bottom = 1
	table_style.border_color = Color(0.8, 0.84, 0.9, 1.0)
	table_style.corner_radius_top_left = 14
	table_style.corner_radius_top_right = 14
	table_style.corner_radius_bottom_right = 14
	table_style.corner_radius_bottom_left = 14
	table_frame.add_theme_stylebox_override("panel", table_style)
	content.add_child(table_frame)

	var table_shell := MarginContainer.new()
	table_shell.add_theme_constant_override("margin_left", 16)
	table_shell.add_theme_constant_override("margin_top", 16)
	table_shell.add_theme_constant_override("margin_right", 16)
	table_shell.add_theme_constant_override("margin_bottom", 16)
	table_frame.add_child(table_shell)

	var table_box := VBoxContainer.new()
	table_box.add_theme_constant_override("separation", 10)
	table_shell.add_child(table_box)

	table_box.add_child(_make_comparison_header_row())

	var rows_box := VBoxContainer.new()
	rows_box.add_theme_constant_override("separation", 8)
	table_box.add_child(rows_box)

	for row_variant in rows:
		rows_box.add_child(_make_comparison_row(row_variant, best_row))

	var footer := HBoxContainer.new()
	footer.alignment = BoxContainer.ALIGNMENT_END
	footer.add_theme_constant_override("separation", 10)
	content.add_child(footer)

	var close_button := Button.new()
	close_button.text = "Đóng"
	close_button.custom_minimum_size = Vector2(120, 42)
	close_button.add_theme_color_override("font_color", Color.BLACK)
	close_button.pressed.connect(_close_comparison_overlay)
	footer.add_child(close_button)

	var rerun_button := Button.new()
	rerun_button.text = "Chạy lại"
	rerun_button.custom_minimum_size = Vector2(120, 42)
	rerun_button.add_theme_color_override("font_color", Color.BLACK)
	rerun_button.pressed.connect(_rerun_all_algorithms)
	footer.add_child(rerun_button)


func _make_comparison_chart(rows: Array) -> Control:
	var chart_frame := PanelContainer.new()
	var frame_style := StyleBoxFlat.new()
	frame_style.bg_color = Color(0.06, 0.08, 0.14, 0.96)
	frame_style.corner_radius_top_left = 14
	frame_style.corner_radius_top_right = 14
	frame_style.corner_radius_bottom_left = 14
	frame_style.corner_radius_bottom_right = 14
	frame_style.border_width_left = 1
	frame_style.border_width_top = 1
	frame_style.border_width_right = 1
	frame_style.border_width_bottom = 1
	frame_style.border_color = Color(0.3, 0.36, 0.5, 0.8)
	chart_frame.add_theme_stylebox_override("panel", frame_style)

	var chart_pad := MarginContainer.new()
	chart_pad.add_theme_constant_override("margin_left", 20)
	chart_pad.add_theme_constant_override("margin_right", 20)
	chart_pad.add_theme_constant_override("margin_top", 14)
	chart_pad.add_theme_constant_override("margin_bottom", 14)
	chart_frame.add_child(chart_pad)

	var chart_vbox := VBoxContainer.new()
	chart_vbox.add_theme_constant_override("separation", 10)
	chart_pad.add_child(chart_vbox)

	var chart_title := Label.new()
	chart_title.text = "Biểu đồ Thời gian chạy (ms)"
	chart_title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	chart_title.add_theme_font_size_override("font_size", 16)
	chart_title.add_theme_color_override("font_color", Color(1.0, 0.98, 0.85))
	chart_vbox.add_child(chart_title)

	var max_time := 0.0
	for rv in rows:
		var r: Dictionary = rv
		if bool(r.get("found", false)):
			max_time = maxf(max_time, float(r.get("elapsed_ms", 0.0)))
	if max_time <= 0.0:
		max_time = 1.0

	const BAR_MAX_H := 120.0
	const BAR_W := 100.0
	const BAR_GAP := 22.0

	var bars_hbox := HBoxContainer.new()
	bars_hbox.alignment = BoxContainer.ALIGNMENT_CENTER
	bars_hbox.add_theme_constant_override("separation", int(BAR_GAP))
	bars_hbox.custom_minimum_size = Vector2(0.0, BAR_MAX_H + 48.0)
	chart_vbox.add_child(bars_hbox)

	for rv in rows:
		var row: Dictionary = rv
		var found := bool(row.get("found", false))
		var elapsed := float(row.get("elapsed_ms", 0.0)) if found else 0.0
		var algo_name := str(row.get("algorithm", "?"))
		var bar_color := Color(row.get("color", Color.GRAY))

		var col := VBoxContainer.new()
		col.custom_minimum_size = Vector2(BAR_W, 0.0)
		col.alignment = BoxContainer.ALIGNMENT_END
		bars_hbox.add_child(col)

		# Value label
		var val_label := Label.new()
		val_label.text = "%.1f ms" % elapsed if found else "—"
		val_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		val_label.add_theme_font_size_override("font_size", 13)
		val_label.add_theme_color_override("font_color", bar_color.lightened(0.3))
		col.add_child(val_label)

		# Bar
		var bar_height := (elapsed / max_time) * BAR_MAX_H if found else 4.0
		var bar := ColorRect.new()
		bar.custom_minimum_size = Vector2(BAR_W, bar_height)
		bar.color = bar_color
		col.add_child(bar)

		# Name label
		var name_label := Label.new()
		name_label.text = algo_name
		name_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		name_label.add_theme_font_size_override("font_size", 14)
		name_label.add_theme_color_override("font_color", Color(0.9, 0.92, 1.0))
		col.add_child(name_label)

	return chart_frame


func _find_best_comparison_row(rows: Array) -> Dictionary:
	var best: Dictionary = {}
	var best_time := INF
	for row_variant in rows:
		var row: Dictionary = row_variant
		if not bool(row.get("found", false)):
			continue
		var elapsed := float(row.get("elapsed_ms", INF))
		if elapsed < best_time:
			best_time = elapsed
			best = row
	return best


func _make_comparison_summary_card(best_row: Dictionary) -> Control:
	var panel := PanelContainer.new()
	var style := StyleBoxFlat.new()
	style.bg_color = Color(0.91, 0.96, 1.0, 0.95)
	style.border_width_left = 1
	style.border_width_top = 1
	style.border_width_right = 1
	style.border_width_bottom = 1
	style.border_color = Color(0.67, 0.8, 0.96, 1.0)
	style.corner_radius_top_left = 14
	style.corner_radius_top_right = 14
	style.corner_radius_bottom_right = 14
	style.corner_radius_bottom_left = 14
	panel.add_theme_stylebox_override("panel", style)

	var box := HBoxContainer.new()
	box.add_theme_constant_override("separation", 16)
	panel.add_child(box)

	var accent := ColorRect.new()
	accent.custom_minimum_size = Vector2(10, 72)
	accent.color = best_row.get("color", Color.WHITE)
	box.add_child(accent)

	var content := VBoxContainer.new()
	content.add_theme_constant_override("separation", 6)
	content.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	box.add_child(content)

	content.add_child(_make_text_label("Nhanh nhất: %s" % str(best_row.get("algorithm", "")), 20, true))
	content.add_child(_make_text_label(
		"Thời gian %.2f ms, chi phí %.2f, thăm %d đỉnh và %d cạnh." % [
			float(best_row.get("elapsed_ms", 0.0)),
			float(best_row.get("path_cost", 0.0)),
			int(best_row.get("visited_vertices", 0)),
			int(best_row.get("visited_edges", 0)),
		],
		14
	))
	return panel


func _make_comparison_header_row() -> Control:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 12)
	row.add_child(_make_metric_label("Màu", 64, true))
	row.add_child(_make_metric_label("Thuật toán", 150, true))
	row.add_child(_make_metric_label("Kết quả", 110, true))
	row.add_child(_make_metric_label("Thời gian", 130, true))
	row.add_child(_make_metric_label("Node đường đi", 130, true))
	row.add_child(_make_metric_label("Chi phí", 120, true))
	row.add_child(_make_metric_label("Đỉnh đã thăm", 130, true))
	row.add_child(_make_metric_label("Cạnh đã thăm", 130, true))
	return row


func _make_comparison_row(row_data: Dictionary, best_row: Dictionary) -> Control:
	var panel := PanelContainer.new()
	var style := StyleBoxFlat.new()
	var is_best := not best_row.is_empty() and str(best_row.get("algorithm", "")) == str(row_data.get("algorithm", ""))
	style.bg_color = Color(0.93, 0.97, 1.0, 0.85) if is_best else Color(1.0, 1.0, 1.0, 0.72)
	style.border_width_left = 1
	style.border_width_top = 1
	style.border_width_right = 1
	style.border_width_bottom = 1
	style.border_color = Color(0.68, 0.82, 1.0, 1.0) if is_best else Color(0.85, 0.88, 0.92, 1.0)
	style.corner_radius_top_left = 10
	style.corner_radius_top_right = 10
	style.corner_radius_bottom_right = 10
	style.corner_radius_bottom_left = 10
	panel.add_theme_stylebox_override("panel", style)

	var shell := MarginContainer.new()
	shell.add_theme_constant_override("margin_left", 12)
	shell.add_theme_constant_override("margin_top", 10)
	shell.add_theme_constant_override("margin_right", 12)
	shell.add_theme_constant_override("margin_bottom", 10)
	panel.add_child(shell)

	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 12)
	shell.add_child(row)

	var color_swatch := PanelContainer.new()
	var swatch_style := StyleBoxFlat.new()
	swatch_style.bg_color = row_data.get("color", Color.WHITE)
	swatch_style.corner_radius_top_left = 6
	swatch_style.corner_radius_top_right = 6
	swatch_style.corner_radius_bottom_right = 6
	swatch_style.corner_radius_bottom_left = 6
	color_swatch.add_theme_stylebox_override("panel", swatch_style)
	color_swatch.custom_minimum_size = Vector2(64, 30)
	row.add_child(color_swatch)

	row.add_child(_make_metric_label(str(row_data.get("algorithm", "")), 150, is_best))
	row.add_child(_make_metric_label("Tìm thấy" if bool(row_data.get("found", false)) else "Không", 110))
	row.add_child(_make_metric_label("%.2f ms" % float(row_data.get("elapsed_ms", 0.0)), 130, is_best))
	row.add_child(_make_metric_label(str(int(row_data.get("path_nodes", 0))), 130))
	row.add_child(_make_metric_label("%.2f" % float(row_data.get("path_cost", 0.0)), 120))
	row.add_child(_make_metric_label(str(int(row_data.get("visited_vertices", 0))), 130))
	row.add_child(_make_metric_label(str(int(row_data.get("visited_edges", 0))), 130))
	return panel


func _make_metric_label(text: String, width: float, bold := false) -> Label:
	var label := _make_text_label(text, 15 if not bold else 16, bold, 0.0, false)
	label.custom_minimum_size = Vector2(width, 0.0)
	label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	return label


func _make_result_stat_row(label_text: String, value_text: String) -> Control:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 16)

	var label := _make_text_label(label_text, 15, true, 220.0, false)
	row.add_child(label)

	var value := _make_text_label(value_text, 15, false, 0.0, false)
	value.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(value)
	return row


func _close_comparison_overlay() -> void:
	if is_instance_valid(_comparison_layer):
		_comparison_layer.queue_free()
	Input.mouse_mode = Input.MOUSE_MODE_CAPTURED


func _show_search_result_overlay(result: Dictionary) -> void:
	if is_instance_valid(_comparison_layer):
		_comparison_layer.queue_free()
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE

	_comparison_layer = CanvasLayer.new()
	_comparison_layer.layer = 210
	add_child(_comparison_layer)

	var backdrop := ColorRect.new()
	backdrop.set_anchors_preset(Control.PRESET_FULL_RECT)
	backdrop.color = Color(0.02, 0.03, 0.05, 0.68)
	_comparison_layer.add_child(backdrop)

	var root := MarginContainer.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.add_theme_constant_override("margin_left", 24)
	root.add_theme_constant_override("margin_top", 24)
	root.add_theme_constant_override("margin_right", 24)
	root.add_theme_constant_override("margin_bottom", 24)
	backdrop.add_child(root)

	var center := CenterContainer.new()
	root.add_child(center)

	var panel := PanelContainer.new()
	panel.custom_minimum_size = Vector2(760, 420)
	center.add_child(panel)

	var panel_style := StyleBoxFlat.new()
	panel_style.bg_color = Color(0.98, 0.99, 1.0, 0.99)
	panel_style.border_width_left = 2
	panel_style.border_width_top = 2
	panel_style.border_width_right = 2
	panel_style.border_width_bottom = 2
	panel_style.border_color = Color(0.12, 0.18, 0.28, 1.0)
	panel_style.corner_radius_top_left = 18
	panel_style.corner_radius_top_right = 18
	panel_style.corner_radius_bottom_right = 18
	panel_style.corner_radius_bottom_left = 18
	panel.add_theme_stylebox_override("panel", panel_style)

	var shell := MarginContainer.new()
	shell.add_theme_constant_override("margin_left", 26)
	shell.add_theme_constant_override("margin_top", 22)
	shell.add_theme_constant_override("margin_right", 26)
	shell.add_theme_constant_override("margin_bottom", 22)
	panel.add_child(shell)

	var content := VBoxContainer.new()
	content.add_theme_constant_override("separation", 14)
	shell.add_child(content)

	var title := _make_text_label("Kết quả tìm đường", 30, true)
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	content.add_child(title)

	var hero := PanelContainer.new()
	var hero_style := StyleBoxFlat.new()
	hero_style.bg_color = Color(0.92, 0.96, 1.0, 0.95)
	hero_style.border_width_left = 1
	hero_style.border_width_top = 1
	hero_style.border_width_right = 1
	hero_style.border_width_bottom = 1
	hero_style.border_color = Color(0.7, 0.82, 0.98, 1.0)
	hero_style.corner_radius_top_left = 14
	hero_style.corner_radius_top_right = 14
	hero_style.corner_radius_bottom_right = 14
	hero_style.corner_radius_bottom_left = 14
	hero.add_theme_stylebox_override("panel", hero_style)
	content.add_child(hero)

	var hero_row := HBoxContainer.new()
	hero_row.add_theme_constant_override("separation", 16)
	hero.add_child(hero_row)

	var accent := ColorRect.new()
	accent.custom_minimum_size = Vector2(10, 72)
	accent.color = result.get("color", Color.WHITE)
	hero_row.add_child(accent)

	var hero_text := VBoxContainer.new()
	hero_text.add_theme_constant_override("separation", 6)
	hero_text.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	hero_row.add_child(hero_text)

	hero_text.add_child(_make_text_label("Thuật toán: %s" % str(result.get("algorithm", "")), 20, true))
	hero_text.add_child(_make_text_label(
		"Đã tìm thấy đường từ node %d đến node %d trong %.2f ms." % [
			int(result.get("start_id", -1)),
			int(result.get("goal_id", -1)),
			float(result.get("elapsed_ms", 0.0)),
		],
		14
	))

	var stats_frame := PanelContainer.new()
	var stats_style := StyleBoxFlat.new()
	stats_style.bg_color = Color(1.0, 1.0, 1.0, 0.8)
	stats_style.border_width_left = 1
	stats_style.border_width_top = 1
	stats_style.border_width_right = 1
	stats_style.border_width_bottom = 1
	stats_style.border_color = Color(0.84, 0.87, 0.92, 1.0)
	stats_style.corner_radius_top_left = 14
	stats_style.corner_radius_top_right = 14
	stats_style.corner_radius_bottom_right = 14
	stats_style.corner_radius_bottom_left = 14
	stats_frame.add_theme_stylebox_override("panel", stats_style)
	content.add_child(stats_frame)

	var stats_shell := MarginContainer.new()
	stats_shell.add_theme_constant_override("margin_left", 18)
	stats_shell.add_theme_constant_override("margin_top", 18)
	stats_shell.add_theme_constant_override("margin_right", 18)
	stats_shell.add_theme_constant_override("margin_bottom", 18)
	stats_frame.add_child(stats_shell)

	var stats_box := VBoxContainer.new()
	stats_box.add_theme_constant_override("separation", 10)
	stats_shell.add_child(stats_box)

	for pair in [
		["Thời gian", "%.2f ms" % float(result.get("elapsed_ms", 0.0))],
		["Số node đường đi", str(int(result.get("path_nodes", 0)))],
		["Chi phí", "%.2f" % float(result.get("path_cost", 0.0))],
		["Đỉnh đã thăm", str(int(result.get("visited_vertices", 0)))],
		["Cạnh đã thăm", str(int(result.get("visited_edges", 0)))],
		["Đỉnh đã phát hiện", str(int(result.get("discovered_vertices", 0)))],
	]:
		stats_box.add_child(_make_result_stat_row(str(pair[0]), str(pair[1])))

	var footer := HBoxContainer.new()
	footer.alignment = BoxContainer.ALIGNMENT_END
	footer.add_theme_constant_override("separation", 10)
	content.add_child(footer)

	var close_button := Button.new()
	close_button.text = "Đóng"
	close_button.custom_minimum_size = Vector2(120, 42)
	close_button.add_theme_color_override("font_color", Color.BLACK)
	close_button.pressed.connect(_close_comparison_overlay)
	footer.add_child(close_button)


func _rerun_all_algorithms() -> void:
	_close_comparison_overlay()
	if path_bot != null:
		path_bot.call("start_search_with_all")
