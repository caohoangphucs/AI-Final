extends Node3D

@onready var campus: Node = $Campus
@onready var spawn: Marker3D = $Spawn
@onready var sun: DirectionalLight3D = $Sun
@onready var world_environment: WorldEnvironment = $WorldEnvironment
@onready var path_bot: CharacterBody3D = $PathBot

const ROUTE_MINIMAP_SCRIPT := preload("res://scripts/route_minimap.gd")
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
var _next_click_is_start := true
var _hud_label: Label
var _menu_section := ""
var _selected_route_index := 0
var _minimap_layer: CanvasLayer
var _minimap_panel: PanelContainer
var _minimap_viewport: SubViewport
var _minimap_viewport_container: SubViewportContainer
var _minimap_camera: Camera3D
var _minimap_title: Label
var _minimap_subtitle: Label
var _minimap_focus_overlay: ColorRect
var _minimap_bot_indicator: PanelContainer
var _minimap_route_overlay: Control

const MINIMAP_3D_HEIGHT := 3.9
const MINIMAP_3D_DISTANCE := 6.1
const MINIMAP_3D_SIDE_SHIFT := 0.9
const MINIMAP_2D_HEIGHT := 120.0
const MINIMAP_2D_SIZE := 190.0
const MINIMAP_2D_CENTER := Vector3(44.0, 0.0, 18.5)
const MINIMAP_FOLLOW_SMOOTH := 8.0

const DEFAULT_HUD_TEXT := "Bấm [ESC] để vào Menu Chính\nBấm [X] để ẩn/hiện tường"
const PRESET_ROUTES := [
	{
		"name": "Sảnh A2 -> Thư viện",
		"start": Vector3(-32.5, 0.0, 87.8),
		"goal": Vector3(0.0, 0.0, 13.0),
	},
	{
		"name": "Giảng đường A3 -> Khối B",
		"start": Vector3(-32.5, 0.0, 79.8),
		"goal": Vector3(2.35, 0.0, -38.75),
	},
	{
		"name": "Khối C -> Khối H",
		"start": Vector3(-35.0, 0.0, -33.2),
		"goal": Vector3(88.0, 2.5, -18.0),
	},
	{
		"name": "Khối D -> Khối I",
		"start": Vector3(-48.0, 0.0, -13.2),
		"goal": Vector3(120.0, 2.5, -10.0),
	},
	{
		"name": "Sân trước A -> Khối K",
		"start": Vector3(-35.0, 0.0, 92.0),
		"goal": Vector3(96.0, 0.0, 18.0),
	},
	{
		"name": "Trục tháp -> Khối N",
		"start": Vector3(118.0, 0.0, 5.0),
		"goal": Vector3(165.0, 2.5, -4.0),
	},
	{
		"name": "Khối L -> Khối O",
		"start": Vector3(-86.0, 0.0, 20.0),
		"goal": Vector3(195.0, 2.5, -4.0),
	},
	{
		"name": "Khối M -> Khối J",
		"start": Vector3(118.0, 5.0, 28.0),
		"goal": Vector3(-84.0, 5.0, -40.0),
	},
	{
		"name": "Đường giữa A -> Khối C",
		"start": Vector3(-35.0, 0.0, 84.0),
		"goal": Vector3(-35.0, 0.0, -26.0),
	},
	{
		"name": "Đường sau A -> Khối H",
		"start": Vector3(-35.0, 0.0, 66.0),
		"goal": Vector3(88.0, 2.5, -18.0),
	},
]


func _ready() -> void:
	_configure_lighting()
	_build_collisions(campus)
	_place_player()
	if path_bot != null and not path_bot.comparison_ready.is_connected(_on_comparison_ready):
		path_bot.comparison_ready.connect(_on_comparison_ready)
	if path_bot != null and not path_bot.search_result_ready.is_connected(_on_search_result_ready):
		path_bot.search_result_ready.connect(_on_search_result_ready)
	_setup_hud()
	_setup_minimap()
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
	label.text = DEFAULT_HUD_TEXT
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
	_hud_label = label


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		match event.keycode:
			KEY_X:
				campus.visible = not campus.visible
				print("Main: campus model %s" % ("visible" if campus.visible else "hidden"))
			KEY_ESCAPE:
				_show_algorithm_menu()
				print("Main: returned to algorithm menu")


func _process(_delta: float) -> void:
	if path_bot == null or _minimap_camera == null or _minimap_panel == null:
		return
	_update_minimap(_delta)


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
	_update_hud_text()
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
	backdrop.color = Color(0.02, 0.05, 0.09, 0.84)
	_algorithm_menu_layer.add_child(backdrop)

	var ambient_glow := ColorRect.new()
	ambient_glow.set_anchors_preset(Control.PRESET_FULL_RECT)
	ambient_glow.color = Color(0.05, 0.18, 0.34, 0.12)
	ambient_glow.mouse_filter = Control.MOUSE_FILTER_IGNORE
	backdrop.add_child(ambient_glow)

	var root := MarginContainer.new()
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.add_theme_constant_override("margin_left", 32)
	root.add_theme_constant_override("margin_top", 28)
	root.add_theme_constant_override("margin_right", 32)
	root.add_theme_constant_override("margin_bottom", 28)
	backdrop.add_child(root)

	var center := CenterContainer.new()
	root.add_child(center)

	_algorithm_menu_panel = PanelContainer.new()
	_algorithm_menu_panel.custom_minimum_size = Vector2(1080, 660)
	center.add_child(_algorithm_menu_panel)

	var panel_style := StyleBoxFlat.new()
	panel_style.bg_color = Color(0.94, 0.97, 1.0, 0.985)
	panel_style.border_width_left = 1
	panel_style.border_width_top = 1
	panel_style.border_width_right = 1
	panel_style.border_width_bottom = 1
	panel_style.border_color = Color(0.23, 0.38, 0.56, 0.95)
	panel_style.corner_radius_top_left = 18
	panel_style.corner_radius_top_right = 18
	panel_style.corner_radius_bottom_right = 18
	panel_style.corner_radius_bottom_left = 18
	panel_style.shadow_color = Color(0.0, 0.0, 0.0, 0.22)
	panel_style.shadow_size = 16
	_algorithm_menu_panel.add_theme_stylebox_override("panel", panel_style)

	var shell := MarginContainer.new()
	shell.add_theme_constant_override("margin_left", 28)
	shell.add_theme_constant_override("margin_top", 26)
	shell.add_theme_constant_override("margin_right", 28)
	shell.add_theme_constant_override("margin_bottom", 24)
	_algorithm_menu_panel.add_child(shell)

	var content := VBoxContainer.new()
	content.add_theme_constant_override("separation", 18)
	shell.add_child(content)

	var chooser_panel := PanelContainer.new()
	var chooser_style := StyleBoxFlat.new()
	chooser_style.bg_color = Color(0.08, 0.15, 0.26, 0.98)
	chooser_style.border_width_left = 1
	chooser_style.border_width_top = 1
	chooser_style.border_width_right = 1
	chooser_style.border_width_bottom = 1
	chooser_style.border_color = Color(0.39, 0.62, 0.94, 0.75)
	chooser_style.corner_radius_top_left = 16
	chooser_style.corner_radius_top_right = 16
	chooser_style.corner_radius_bottom_left = 16
	chooser_style.corner_radius_bottom_right = 16
	chooser_panel.add_theme_stylebox_override("panel", chooser_style)
	chooser_panel.visible = _menu_section == ""
	content.add_child(chooser_panel)

	var chooser_margin := MarginContainer.new()
	chooser_margin.add_theme_constant_override("margin_left", 26)
	chooser_margin.add_theme_constant_override("margin_top", 24)
	chooser_margin.add_theme_constant_override("margin_right", 26)
	chooser_margin.add_theme_constant_override("margin_bottom", 24)
	chooser_panel.add_child(chooser_margin)

	var chooser_box := VBoxContainer.new()
	chooser_box.add_theme_constant_override("separation", 18)
	chooser_margin.add_child(chooser_box)

	var chooser_eyebrow := Label.new()
	chooser_eyebrow.text = "MÔ PHỎNG TÌM ĐƯỜNG ĐI TRONG KHÔNG GIAN 3D Ở TRƯỜNG HỌC"
	chooser_eyebrow.add_theme_font_size_override("font_size", 14)
	chooser_eyebrow.add_theme_color_override("font_color", Color(0.95, 0.81, 0.34, 1.0))
	chooser_box.add_child(chooser_eyebrow)

	var chooser_title := Label.new()
	chooser_title.text = "Chọn mục bạn muốn mở"
	chooser_title.add_theme_font_size_override("font_size", 34)
	chooser_title.add_theme_color_override("font_color", Color(0.97, 0.99, 1.0, 1.0))
	chooser_box.add_child(chooser_title)

	var chooser_desc := Label.new()
	chooser_desc.text = "Vào phần chơi để chọn thuật toán và chạy PathBot, hoặc mở thông tin nhóm để xem thành viên thực hiện dự án."
	chooser_desc.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	chooser_desc.add_theme_font_size_override("font_size", 15)
	chooser_desc.add_theme_color_override("font_color", Color(0.83, 0.9, 0.98, 0.96))
	chooser_box.add_child(chooser_desc)

	var chooser_actions := HBoxContainer.new()
	chooser_actions.add_theme_constant_override("separation", 18)
	chooser_box.add_child(chooser_actions)

	var chooser_play := _make_menu_tab_button("Chạy mô phỏng", true)
	chooser_play.custom_minimum_size = Vector2(220, 56)
	chooser_play.pressed.connect(func() -> void:
		_switch_menu_section("play")
	)
	chooser_actions.add_child(chooser_play)

	var chooser_info := _make_menu_tab_button("Thông tin nhóm", false)
	chooser_info.custom_minimum_size = Vector2(220, 56)
	chooser_info.pressed.connect(func() -> void:
		_switch_menu_section("group")
	)
	chooser_actions.add_child(chooser_info)

	var menu_tabs := HBoxContainer.new()
	menu_tabs.add_theme_constant_override("separation", 12)
	menu_tabs.visible = _menu_section != ""
	content.add_child(menu_tabs)

	var play_tab := _make_menu_tab_button("Chạy mô phỏng", _menu_section == "play")
	play_tab.pressed.connect(func() -> void:
		_switch_menu_section("play")
	)
	menu_tabs.add_child(play_tab)

	var info_tab := _make_menu_tab_button("Thông tin nhóm", _menu_section == "group")
	info_tab.pressed.connect(func() -> void:
		_switch_menu_section("group")
	)
	menu_tabs.add_child(info_tab)

	var hero_panel := PanelContainer.new()
	var hero_style := StyleBoxFlat.new()
	hero_style.bg_color = Color(0.08, 0.15, 0.26, 0.98)
	hero_style.border_width_left = 1
	hero_style.border_width_top = 1
	hero_style.border_width_right = 1
	hero_style.border_width_bottom = 1
	hero_style.border_color = Color(0.39, 0.62, 0.94, 0.75)
	hero_style.corner_radius_top_left = 16
	hero_style.corner_radius_top_right = 16
	hero_style.corner_radius_bottom_right = 16
	hero_style.corner_radius_bottom_left = 16
	hero_panel.add_theme_stylebox_override("panel", hero_style)
	content.add_child(hero_panel)
	hero_panel.visible = _menu_section == "play"

	var hero_margin := MarginContainer.new()
	hero_margin.add_theme_constant_override("margin_left", 24)
	hero_margin.add_theme_constant_override("margin_top", 22)
	hero_margin.add_theme_constant_override("margin_right", 24)
	hero_margin.add_theme_constant_override("margin_bottom", 22)
	hero_panel.add_child(hero_margin)

	var hero_row := HBoxContainer.new()
	hero_row.add_theme_constant_override("separation", 24)
	hero_margin.add_child(hero_row)

	var hero_copy := VBoxContainer.new()
	hero_copy.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	hero_copy.add_theme_constant_override("separation", 10)
	hero_row.add_child(hero_copy)

	var eyebrow := Label.new()
	eyebrow.text = "MÔ PHỎNG TÌM ĐƯỜNG ĐI TRONG KHÔNG GIAN 3D Ở TRƯỜNG HỌC • NAVIGATION LAB"
	eyebrow.add_theme_font_size_override("font_size", 14)
	eyebrow.add_theme_color_override("font_color", Color(0.95, 0.81, 0.34, 1.0))
	hero_copy.add_child(eyebrow)

	var main_title := Label.new()
	main_title.text = "Mô phỏng tìm đường 3D\ntrong môi trường trường học"
	main_title.add_theme_font_size_override("font_size", 33)
	main_title.add_theme_color_override("font_color", Color(0.97, 0.99, 1.0, 1.0))
	main_title.add_theme_color_override("font_shadow_color", Color(0.0, 0.0, 0.0, 0.35))
	main_title.add_theme_constant_override("shadow_offset_x", 0)
	main_title.add_theme_constant_override("shadow_offset_y", 3)
	hero_copy.add_child(main_title)

	var subtitle := Label.new()
	subtitle.text = "Trực quan hóa cách các thuật toán tìm đường hoạt động trên campus 3D với PathBot chạy trực tiếp bằng GDScript."
	subtitle.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	subtitle.add_theme_font_size_override("font_size", 15)
	subtitle.add_theme_color_override("font_color", Color(0.83, 0.9, 0.98, 0.96))
	hero_copy.add_child(subtitle)

	var chip_row := HBoxContainer.new()
	chip_row.add_theme_constant_override("separation", 12)
	hero_copy.add_child(chip_row)
	chip_row.add_child(_make_menu_chip("6 thuật toán"))
	chip_row.add_child(_make_menu_chip("Minimap theo bot"))
	chip_row.add_child(_make_menu_chip("Chọn Start / Goal tự do"))

	var section_row := HBoxContainer.new()
	section_row.add_theme_constant_override("separation", 18)
	content.add_child(section_row)
	section_row.visible = _menu_section == "play"

	var section_title_box := VBoxContainer.new()
	section_title_box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	section_title_box.add_theme_constant_override("separation", 6)
	section_row.add_child(section_title_box)

	var title := Label.new()
	title.text = "Chọn thuật toán đường đi"
	title.add_theme_font_size_override("font_size", 24)
	title.add_theme_color_override("font_color", Color(0.11, 0.19, 0.31, 1.0))
	section_title_box.add_child(title)

	var section_subtitle := Label.new()
	section_subtitle.text = "Chọn một thuật toán để bot chạy ngay, hoặc mở chế độ so sánh toàn bộ để benchmark trực quan."
	section_subtitle.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	section_subtitle.add_theme_font_size_override("font_size", 15)
	section_subtitle.add_theme_color_override("font_color", Color(0.26, 0.34, 0.46, 0.95))
	section_title_box.add_child(section_subtitle)

	var header_actions := HBoxContainer.new()
	header_actions.alignment = BoxContainer.ALIGNMENT_END
	header_actions.add_theme_constant_override("separation", 12)
	section_row.add_child(header_actions)

	var route_panel := PanelContainer.new()
	var route_style := StyleBoxFlat.new()
	route_style.bg_color = Color(0.92, 0.96, 1.0, 0.85)
	route_style.border_width_left = 1
	route_style.border_width_top = 1
	route_style.border_width_right = 1
	route_style.border_width_bottom = 1
	route_style.border_color = Color(0.77, 0.84, 0.94, 1.0)
	route_style.corner_radius_top_left = 12
	route_style.corner_radius_top_right = 12
	route_style.corner_radius_bottom_left = 12
	route_style.corner_radius_bottom_right = 12
	route_panel.add_theme_stylebox_override("panel", route_style)
	route_panel.custom_minimum_size = Vector2(360, 0)
	header_actions.add_child(route_panel)

	var route_margin := MarginContainer.new()
	route_margin.add_theme_constant_override("margin_left", 14)
	route_margin.add_theme_constant_override("margin_top", 10)
	route_margin.add_theme_constant_override("margin_right", 14)
	route_margin.add_theme_constant_override("margin_bottom", 10)
	route_panel.add_child(route_margin)

	var route_box := VBoxContainer.new()
	route_box.add_theme_constant_override("separation", 8)
	route_margin.add_child(route_box)

	var route_label := Label.new()
	route_label.text = "Tuyến đường định sẵn"
	route_label.add_theme_font_size_override("font_size", 14)
	route_label.add_theme_color_override("font_color", Color(0.15, 0.24, 0.37, 0.96))
	route_box.add_child(route_label)

	var route_select := OptionButton.new()
	route_select.fit_to_longest_item = false
	route_select.custom_minimum_size = Vector2(320, 42)
	for index in range(PRESET_ROUTES.size()):
		route_select.add_item(str(PRESET_ROUTES[index]["name"]), index)
	route_select.select(_selected_route_index)
	route_select.item_selected.connect(_on_route_selected)
	route_box.add_child(route_select)

	var table_frame := PanelContainer.new()
	var table_style := StyleBoxFlat.new()
	table_style.bg_color = Color(1.0, 1.0, 1.0, 0.78)
	table_style.corner_radius_top_left = 14
	table_style.corner_radius_top_right = 14
	table_style.corner_radius_bottom_left = 14
	table_style.corner_radius_bottom_right = 14
	table_style.border_width_left = 1
	table_style.border_width_top = 1
	table_style.border_width_right = 1
	table_style.border_width_bottom = 1
	table_style.border_color = Color(0.76, 0.84, 0.93, 1.0)
	table_frame.add_theme_stylebox_override("panel", table_style)
	table_frame.size_flags_vertical = Control.SIZE_EXPAND_FILL
	content.add_child(table_frame)
	table_frame.visible = _menu_section == "play"

	var table_shell := MarginContainer.new()
	table_shell.add_theme_constant_override("margin_left", 20)
	table_shell.add_theme_constant_override("margin_top", 20)
	table_shell.add_theme_constant_override("margin_right", 20)
	table_shell.add_theme_constant_override("margin_bottom", 20)
	table_frame.add_child(table_shell)

	var table_content := VBoxContainer.new()
	table_content.add_theme_constant_override("separation", 8)
	table_shell.add_child(table_content)

	table_content.add_child(_make_algorithm_header_row())

	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	scroll.custom_minimum_size = Vector2(0.0, 310.0)
	table_content.add_child(scroll)

	var rows_box := VBoxContainer.new()
	rows_box.add_theme_constant_override("separation", 8)
	rows_box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	rows_box.custom_minimum_size = Vector2(920.0, 0.0)
	scroll.add_child(rows_box)

	for row_variant in path_bot.call("get_algorithm_menu_rows"):
		rows_box.add_child(_make_algorithm_row(row_variant))

	var footer := Label.new()
	footer.text = "Chọn một trong 10 tuyến có sẵn rồi chạy thuật toán. Bạn vẫn có thể mở lại menu bằng ESC."
	footer.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	footer.add_theme_font_size_override("font_size", 14)
	footer.add_theme_color_override("font_color", Color(0.2, 0.28, 0.39, 0.95))
	content.add_child(footer)
	footer.visible = _menu_section == "play"

	var group_section := PanelContainer.new()
	var group_section_style := StyleBoxFlat.new()
	group_section_style.bg_color = Color(0.08, 0.15, 0.26, 0.98)
	group_section_style.border_width_left = 1
	group_section_style.border_width_top = 1
	group_section_style.border_width_right = 1
	group_section_style.border_width_bottom = 1
	group_section_style.border_color = Color(0.39, 0.62, 0.94, 0.75)
	group_section_style.corner_radius_top_left = 16
	group_section_style.corner_radius_top_right = 16
	group_section_style.corner_radius_bottom_left = 16
	group_section_style.corner_radius_bottom_right = 16
	group_section.add_theme_stylebox_override("panel", group_section_style)
	group_section.size_flags_vertical = Control.SIZE_EXPAND_FILL
	group_section.visible = _menu_section == "group"
	content.add_child(group_section)

	var group_section_margin := MarginContainer.new()
	group_section_margin.add_theme_constant_override("margin_left", 28)
	group_section_margin.add_theme_constant_override("margin_top", 26)
	group_section_margin.add_theme_constant_override("margin_right", 28)
	group_section_margin.add_theme_constant_override("margin_bottom", 26)
	group_section.add_child(group_section_margin)

	var group_section_box := VBoxContainer.new()
	group_section_box.add_theme_constant_override("separation", 18)
	group_section_margin.add_child(group_section_box)

	var group_eyebrow := Label.new()
	group_eyebrow.text = "THÔNG TIN NHÓM"
	group_eyebrow.add_theme_font_size_override("font_size", 14)
	group_eyebrow.add_theme_color_override("font_color", Color(0.95, 0.81, 0.34, 1.0))
	group_section_box.add_child(group_eyebrow)

	var group_main_title := Label.new()
	group_main_title.text = "Nhóm thực hiện dự án"
	group_main_title.add_theme_font_size_override("font_size", 32)
	group_main_title.add_theme_color_override("font_color", Color(0.97, 0.99, 1.0, 1.0))
	group_section_box.add_child(group_main_title)

	var group_desc := Label.new()
	group_desc.text = "Dự án mô phỏng tìm đường 3D trong môi trường trường học, tập trung vào trực quan hóa thuật toán và trải nghiệm quan sát PathBot."
	group_desc.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	group_desc.add_theme_font_size_override("font_size", 15)
	group_desc.add_theme_color_override("font_color", Color(0.83, 0.9, 0.98, 0.96))
	group_section_box.add_child(group_desc)

	var member_grid := GridContainer.new()
	member_grid.columns = 3
	member_grid.add_theme_constant_override("h_separation", 16)
	member_grid.add_theme_constant_override("v_separation", 16)
	group_section_box.add_child(member_grid)
	member_grid.add_child(_make_member_card("Cao Hoàng Phúc", "24110303"))
	member_grid.add_child(_make_member_card("Nguyễn Công Khoa", "24110254"))
	member_grid.add_child(_make_member_card("Phan Thị Thùy Linh", "24110271"))

	if _menu_section == "play":
		call_deferred("_apply_selected_route")


func _on_algorithm_selected(algorithm_id: int) -> void:
	_update_hud_text()
	if path_bot != null:
		if algorithm_id == -1:
			path_bot.call("start_search_with_all")
		else:
			path_bot.call("start_search_with_algorithm", algorithm_id)
	if is_instance_valid(_algorithm_menu_layer):
		_algorithm_menu_layer.queue_free()
	var player := $Player
	if player != null:
		player.call("suspend_mouse_capture", 0.35)
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE


func _update_hud_text() -> void:
	if _hud_label == null:
		return
	_hud_label.text = DEFAULT_HUD_TEXT


func _switch_menu_section(section: String) -> void:
	_menu_section = section
	call_deferred("_show_algorithm_menu")


func _on_route_selected(index: int) -> void:
	_selected_route_index = index
	_apply_selected_route()


func _apply_selected_route() -> void:
	if path_bot == null or _selected_route_index < 0 or _selected_route_index >= PRESET_ROUTES.size():
		return
	var route: Dictionary = PRESET_ROUTES[_selected_route_index]
	path_bot.call("set_custom_start", route["start"])
	path_bot.call("set_custom_goal", route["goal"])


func _make_menu_chip(text: String) -> Control:
	var chip := PanelContainer.new()
	var chip_style := StyleBoxFlat.new()
	chip_style.bg_color = Color(1.0, 1.0, 1.0, 0.08)
	chip_style.border_width_left = 1
	chip_style.border_width_top = 1
	chip_style.border_width_right = 1
	chip_style.border_width_bottom = 1
	chip_style.border_color = Color(1.0, 1.0, 1.0, 0.1)
	chip_style.corner_radius_top_left = 999
	chip_style.corner_radius_top_right = 999
	chip_style.corner_radius_bottom_left = 999
	chip_style.corner_radius_bottom_right = 999
	chip.add_theme_stylebox_override("panel", chip_style)

	var label := Label.new()
	label.text = text
	label.add_theme_font_size_override("font_size", 13)
	label.add_theme_color_override("font_color", Color(0.94, 0.97, 1.0, 0.95))
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	label.custom_minimum_size = Vector2(0.0, 30.0)
	chip.add_child(label)
	return chip


func _make_menu_tab_button(text: String, active: bool) -> Button:
	var button := Button.new()
	button.text = text
	button.custom_minimum_size = Vector2(180, 44)
	button.add_theme_color_override("font_color", Color.WHITE if active else Color(0.14, 0.23, 0.36, 1.0))
	var style := StyleBoxFlat.new()
	style.bg_color = Color(0.1, 0.44, 0.78, 1.0) if active else Color(0.87, 0.91, 0.97, 1.0)
	style.corner_radius_top_left = 12
	style.corner_radius_top_right = 12
	style.corner_radius_bottom_left = 12
	style.corner_radius_bottom_right = 12
	style.border_width_left = 1
	style.border_width_top = 1
	style.border_width_right = 1
	style.border_width_bottom = 1
	style.border_color = Color(0.63, 0.84, 1.0, 0.9) if active else Color(0.73, 0.81, 0.92, 1.0)
	button.add_theme_stylebox_override("normal", style)
	var hover := style.duplicate()
	hover.bg_color = Color(0.13, 0.5, 0.88, 1.0) if active else Color(0.81, 0.88, 0.97, 1.0)
	button.add_theme_stylebox_override("hover", hover)
	var pressed := style.duplicate()
	pressed.bg_color = Color(0.07, 0.36, 0.66, 1.0) if active else Color(0.76, 0.84, 0.94, 1.0)
	button.add_theme_stylebox_override("pressed", pressed)
	return button


func _make_member_card(name_text: String, student_id: String) -> Control:
	var card := PanelContainer.new()
	var style := StyleBoxFlat.new()
	style.bg_color = Color(1.0, 1.0, 1.0, 0.08)
	style.border_width_left = 1
	style.border_width_top = 1
	style.border_width_right = 1
	style.border_width_bottom = 1
	style.border_color = Color(1.0, 1.0, 1.0, 0.12)
	style.corner_radius_top_left = 14
	style.corner_radius_top_right = 14
	style.corner_radius_bottom_left = 14
	style.corner_radius_bottom_right = 14
	card.add_theme_stylebox_override("panel", style)

	var margin := MarginContainer.new()
	margin.add_theme_constant_override("margin_left", 18)
	margin.add_theme_constant_override("margin_top", 18)
	margin.add_theme_constant_override("margin_right", 18)
	margin.add_theme_constant_override("margin_bottom", 18)
	card.add_child(margin)

	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 8)
	margin.add_child(box)

	var name := Label.new()
	name.text = name_text
	name.add_theme_font_size_override("font_size", 20)
	name.add_theme_color_override("font_color", Color(0.97, 0.99, 1.0, 1.0))
	box.add_child(name)

	var sid := Label.new()
	sid.text = "MSSV: %s" % student_id
	sid.add_theme_font_size_override("font_size", 15)
	sid.add_theme_color_override("font_color", Color(0.83, 0.9, 0.98, 0.96))
	box.add_child(sid)
	return card


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
	var panel := PanelContainer.new()
	var style := StyleBoxFlat.new()
	style.bg_color = Color(0.9, 0.95, 1.0, 0.9)
	style.corner_radius_top_left = 10
	style.corner_radius_top_right = 10
	style.corner_radius_bottom_left = 10
	style.corner_radius_bottom_right = 10
	style.border_width_left = 1
	style.border_width_top = 1
	style.border_width_right = 1
	style.border_width_bottom = 1
	style.border_color = Color(0.79, 0.86, 0.95, 1.0)
	panel.add_theme_stylebox_override("panel", style)

	var shell := MarginContainer.new()
	shell.add_theme_constant_override("margin_left", 14)
	shell.add_theme_constant_override("margin_top", 12)
	shell.add_theme_constant_override("margin_right", 14)
	shell.add_theme_constant_override("margin_bottom", 12)
	panel.add_child(shell)

	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 16)
	shell.add_child(row)
	row.add_child(_make_column_label("Phím", 70, true))
	row.add_child(_make_column_label("Thuật toán", 170, true))
	row.add_child(_make_column_label("Mô tả", 0, true, true))
	row.add_child(_make_column_label("Hành động", 120, true))
	return panel


func _make_algorithm_row(row_data: Dictionary) -> Control:
	var panel := PanelContainer.new()
	panel.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var style := StyleBoxFlat.new()
	style.bg_color = Color(1.0, 1.0, 1.0, 0.84)
	style.corner_radius_top_left = 12
	style.corner_radius_top_right = 12
	style.corner_radius_bottom_left = 12
	style.corner_radius_bottom_right = 12
	style.border_width_left = 1
	style.border_width_top = 1
	style.border_width_right = 1
	style.border_width_bottom = 1
	style.border_color = Color(0.84, 0.88, 0.94, 1.0)
	panel.add_theme_stylebox_override("panel", style)

	var shell := MarginContainer.new()
	shell.add_theme_constant_override("margin_left", 14)
	shell.add_theme_constant_override("margin_top", 12)
	shell.add_theme_constant_override("margin_right", 14)
	shell.add_theme_constant_override("margin_bottom", 12)
	panel.add_child(shell)

	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 16)
	row.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.custom_minimum_size = Vector2(920.0, 0.0)
	shell.add_child(row)

	row.add_child(_make_column_label(str(row_data.get("shortcut", "")), 70))
	row.add_child(_make_column_label(str(row_data.get("name", "")), 170))
	row.add_child(_make_column_label(str(row_data.get("description", "")), 0, false, true, true))

	var button := Button.new()
	button.text = "Khởi chạy"
	button.custom_minimum_size = Vector2(120, 42)
	button.add_theme_color_override("font_color", Color.WHITE)
	button.add_theme_color_override("font_hover_color", Color.WHITE)
	button.add_theme_color_override("font_pressed_color", Color.WHITE)
	var button_style := StyleBoxFlat.new()
	button_style.bg_color = Color(0.08, 0.37, 0.69, 1.0)
	button_style.corner_radius_top_left = 10
	button_style.corner_radius_top_right = 10
	button_style.corner_radius_bottom_left = 10
	button_style.corner_radius_bottom_right = 10
	button_style.border_width_left = 1
	button_style.border_width_top = 1
	button_style.border_width_right = 1
	button_style.border_width_bottom = 1
	button_style.border_color = Color(0.62, 0.84, 1.0, 0.8)
	button.add_theme_stylebox_override("normal", button_style)
	var button_hover := button_style.duplicate()
	button_hover.bg_color = Color(0.11, 0.45, 0.82, 1.0)
	button.add_theme_stylebox_override("hover", button_hover)
	var button_pressed := button_style.duplicate()
	button_pressed.bg_color = Color(0.05, 0.31, 0.58, 1.0)
	button.add_theme_stylebox_override("pressed", button_pressed)
	button.pressed.connect(_on_algorithm_selected.bind(int(row_data.get("id", 0))))
	row.add_child(button)
	return panel


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


func _setup_minimap() -> void:
	_minimap_layer = CanvasLayer.new()
	_minimap_layer.layer = 140
	add_child(_minimap_layer)

	_minimap_panel = PanelContainer.new()
	_minimap_panel.set_anchors_preset(Control.PRESET_TOP_RIGHT)
	_minimap_panel.offset_left = -348.0
	_minimap_panel.offset_top = 16.0
	_minimap_panel.offset_right = -16.0
	_minimap_panel.offset_bottom = 284.0
	_minimap_panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var panel_style := StyleBoxFlat.new()
	panel_style.bg_color = Color(0.03, 0.06, 0.1, 0.9)
	panel_style.border_width_left = 2
	panel_style.border_width_top = 2
	panel_style.border_width_right = 2
	panel_style.border_width_bottom = 2
	panel_style.border_color = Color(0.42, 0.7, 0.98, 0.95)
	panel_style.corner_radius_top_left = 16
	panel_style.corner_radius_top_right = 16
	panel_style.corner_radius_bottom_right = 16
	panel_style.corner_radius_bottom_left = 16
	_minimap_panel.add_theme_stylebox_override("panel", panel_style)
	_minimap_layer.add_child(_minimap_panel)

	var shell := MarginContainer.new()
	shell.add_theme_constant_override("margin_left", 12)
	shell.add_theme_constant_override("margin_top", 12)
	shell.add_theme_constant_override("margin_right", 12)
	shell.add_theme_constant_override("margin_bottom", 12)
	shell.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_minimap_panel.add_child(shell)

	var content := VBoxContainer.new()
	content.add_theme_constant_override("separation", 8)
	content.mouse_filter = Control.MOUSE_FILTER_IGNORE
	shell.add_child(content)

	_minimap_title = Label.new()
	_minimap_title.text = "Minimap"
	_minimap_title.add_theme_font_size_override("font_size", 16)
	_minimap_title.add_theme_color_override("font_color", Color.WHITE)
	_minimap_title.mouse_filter = Control.MOUSE_FILTER_IGNORE
	content.add_child(_minimap_title)

	_minimap_subtitle = Label.new()
	_minimap_subtitle.text = "Sẵn sàng"
	_minimap_subtitle.add_theme_font_size_override("font_size", 13)
	_minimap_subtitle.add_theme_color_override("font_color", Color(0.82, 0.9, 1.0, 0.95))
	_minimap_subtitle.mouse_filter = Control.MOUSE_FILTER_IGNORE
	content.add_child(_minimap_subtitle)

	var viewport_frame := PanelContainer.new()
	viewport_frame.custom_minimum_size = Vector2(308.0, 204.0)
	viewport_frame.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var frame_style := StyleBoxFlat.new()
	frame_style.bg_color = Color(0.0, 0.0, 0.0, 0.2)
	frame_style.border_width_left = 1
	frame_style.border_width_top = 1
	frame_style.border_width_right = 1
	frame_style.border_width_bottom = 1
	frame_style.border_color = Color(1.0, 1.0, 1.0, 0.08)
	frame_style.corner_radius_top_left = 10
	frame_style.corner_radius_top_right = 10
	frame_style.corner_radius_bottom_right = 10
	frame_style.corner_radius_bottom_left = 10
	viewport_frame.add_theme_stylebox_override("panel", frame_style)
	content.add_child(viewport_frame)

	var viewport_stack := Control.new()
	viewport_stack.set_anchors_preset(Control.PRESET_FULL_RECT)
	viewport_stack.mouse_filter = Control.MOUSE_FILTER_IGNORE
	viewport_frame.add_child(viewport_stack)

	_minimap_viewport_container = SubViewportContainer.new()
	_minimap_viewport_container.set_anchors_preset(Control.PRESET_FULL_RECT)
	_minimap_viewport_container.stretch = true
	_minimap_viewport_container.mouse_filter = Control.MOUSE_FILTER_IGNORE
	viewport_stack.add_child(_minimap_viewport_container)

	_minimap_viewport = SubViewport.new()
	_minimap_viewport.disable_3d = false
	_minimap_viewport.transparent_bg = false
	_minimap_viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	_minimap_viewport.msaa_3d = Viewport.MSAA_2X
	_minimap_viewport.size = Vector2i(616, 408)
	_minimap_viewport.world_3d = get_viewport().world_3d
	_minimap_viewport_container.add_child(_minimap_viewport)

	_minimap_camera = Camera3D.new()
	_minimap_camera.current = true
	_minimap_camera.near = 0.05
	_minimap_camera.far = 2000.0
	_minimap_viewport.add_child(_minimap_camera)

	_minimap_focus_overlay = ColorRect.new()
	_minimap_focus_overlay.set_anchors_preset(Control.PRESET_FULL_RECT)
	_minimap_focus_overlay.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_minimap_focus_overlay.color = Color.WHITE
	var focus_shader := Shader.new()
	focus_shader.code = """
shader_type canvas_item;

uniform vec4 veil_color : source_color = vec4(0.03, 0.07, 0.11, 0.26);
uniform vec4 ring_color : source_color = vec4(0.86, 0.96, 1.0, 0.32);
uniform float hole_radius = 0.15;
uniform float feather = 0.08;

void fragment() {
	vec2 centered = (UV - vec2(0.5)) * vec2(1.0, 1.35);
	float d = length(centered);
	float veil = smoothstep(hole_radius, hole_radius + feather, d);
	float ring = smoothstep(hole_radius - 0.035, hole_radius, d) * (1.0 - smoothstep(hole_radius, hole_radius + feather, d));
	vec3 color = mix(veil_color.rgb, ring_color.rgb, ring);
	float alpha = max(veil * veil_color.a, ring * ring_color.a);
	COLOR = vec4(color, alpha);
}
"""
	var focus_material := ShaderMaterial.new()
	focus_material.shader = focus_shader
	_minimap_focus_overlay.material = focus_material
	viewport_stack.add_child(_minimap_focus_overlay)

	_minimap_bot_indicator = PanelContainer.new()
	_minimap_bot_indicator.set_anchors_preset(Control.PRESET_CENTER)
	_minimap_bot_indicator.custom_minimum_size = Vector2(18.0, 18.0)
	_minimap_bot_indicator.offset_left = -9.0
	_minimap_bot_indicator.offset_top = -9.0
	_minimap_bot_indicator.offset_right = 9.0
	_minimap_bot_indicator.offset_bottom = 9.0
	_minimap_bot_indicator.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var bot_indicator_style := StyleBoxFlat.new()
	bot_indicator_style.bg_color = Color(1.0, 0.95, 0.2, 0.96)
	bot_indicator_style.corner_radius_top_left = 9
	bot_indicator_style.corner_radius_top_right = 9
	bot_indicator_style.corner_radius_bottom_right = 9
	bot_indicator_style.corner_radius_bottom_left = 9
	bot_indicator_style.border_width_left = 2
	bot_indicator_style.border_width_top = 2
	bot_indicator_style.border_width_right = 2
	bot_indicator_style.border_width_bottom = 2
	bot_indicator_style.border_color = Color(1.0, 1.0, 1.0, 0.9)
	_minimap_bot_indicator.add_theme_stylebox_override("panel", bot_indicator_style)
	viewport_stack.add_child(_minimap_bot_indicator)

	_minimap_route_overlay = ROUTE_MINIMAP_SCRIPT.new()
	_minimap_route_overlay.set_anchors_preset(Control.PRESET_FULL_RECT)
	_minimap_route_overlay.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_minimap_route_overlay.visible = false
	viewport_stack.add_child(_minimap_route_overlay)
	_minimap_panel.visible = false


func _update_minimap(delta: float) -> void:
	var snapshot: Dictionary = path_bot.call("get_minimap_snapshot")
	var is_visible := bool(snapshot.get("visible", false))
	_minimap_panel.visible = is_visible
	if not is_visible:
		return

	var mode := str(snapshot.get("mode", "3d"))
	var bot_position: Vector3 = snapshot.get("bot_position", path_bot.global_position)
	_minimap_title.text = "Camera 3D theo bot" if mode == "3d" else "Góc nhìn từ trên xuống"
	_minimap_subtitle.text = str(snapshot.get("floor_label", ""))
	_minimap_focus_overlay.visible = false
	_minimap_bot_indicator.visible = mode == "2d"
	_minimap_route_overlay.visible = mode == "2d"
	_minimap_viewport_container.visible = mode == "3d"

	var blend: float = clamp(delta * MINIMAP_FOLLOW_SMOOTH, 0.0, 1.0)
	if mode == "2d":
		_minimap_route_overlay.call("set_snapshot", snapshot)
		return

	_minimap_camera.projection = Camera3D.PROJECTION_PERSPECTIVE
	_minimap_camera.fov = 46.0
	var backward := path_bot.global_basis.z.normalized()
	var side := path_bot.global_basis.x.normalized()
	var target := bot_position + Vector3(0.0, 1.6, 0.0)
	var desired_position := target + backward * MINIMAP_3D_DISTANCE + side * MINIMAP_3D_SIDE_SHIFT + Vector3(0.0, MINIMAP_3D_HEIGHT, 0.0)
	_minimap_camera.global_position = _minimap_camera.global_position.lerp(desired_position, blend)
	_minimap_camera.look_at(target, Vector3.UP)
