extends CharacterBody3D

signal comparison_ready(rows: Array)
signal search_result_ready(result: Dictionary)

const BOT_SPEED := 4.5
const WAYPOINT_REACHED_DIST := 0.22
const MARKER_HEIGHT := 0.4
const MARKER_SCALE := Vector3(0.5, 0.5, 0.5)
const PATH_MARKER_SCALE := Vector3(0.62, 0.62, 0.62)
const MIN_SEARCH_STEPS_PER_TICK := 1
const MAX_SEARCH_STEPS_PER_TICK := 64
const FRONTIER_QUEUE_COMPACT_INTERVAL := 256
const DEBUG_OVERLAY_REFRESH_SEC := 0.12
const MAX_FRONTIER_MARKERS_DRAW := 1200
const MAX_CLOSED_MARKERS_DRAW := 1800
const MAX_SEARCH_LINE_SEGMENTS_DRAW := 900
const SINGLE_RUN_TICKS_PER_SEC := 30.0
const SINGLE_RUN_TICK_DELAY := 1.0 / SINGLE_RUN_TICKS_PER_SEC
const RUN_ALL_TICKS_PER_SEC := 40.0
const RUN_ALL_TICK_DELAY := 1.0 / RUN_ALL_TICKS_PER_SEC
const RUN_ALL_STEPS_PER_TICK := MAX_SEARCH_STEPS_PER_TICK
const RUN_ALL_VISUAL_UPDATE_INTERVAL := 32
const EDGE_LENGTH_WEIGHT := 1.0
const ASCENT_COST_WEIGHT := 4.0
const ALL_ALGORITHMS_ID := -1

enum SearchAlgorithm {
	ASTAR,
	BFS,
	DFS,
	UCS,
	GREEDY,
	HILL_CLIMBING,
}

const ALGORITHM_SEQUENCE := [
	SearchAlgorithm.ASTAR,
	SearchAlgorithm.BFS,
	SearchAlgorithm.DFS,
	SearchAlgorithm.UCS,
	SearchAlgorithm.GREEDY,
	SearchAlgorithm.HILL_CLIMBING,
]

@export var start_marker_path: NodePath
@export var goal_marker_path: NodePath
@export_range(1, 64, 1) var search_steps_per_tick := 30
@export_range(0.01, 1.0, 0.01) var search_tick_delay := SINGLE_RUN_TICK_DELAY
@export_range(1, 64, 1) var visual_update_interval := 10
@export_enum("A*", "BFS", "DFS", "UCS", "Greedy", "HillClimbing") var search_algorithm: int = SearchAlgorithm.ASTAR

@onready var debug_root: Node3D = $Debug
@onready var all_nodes_markers: MultiMeshInstance3D = $Debug/AllNodesMarkers
@onready var frontier_markers: MultiMeshInstance3D = $Debug/FrontierMarkers
@onready var closed_markers: MultiMeshInstance3D = $Debug/ClosedMarkers
@onready var path_markers: MultiMeshInstance3D = $Debug/PathMarkers
@onready var search_lines: MeshInstance3D = $Debug/SearchLines
@onready var path_lines: MeshInstance3D = $Debug/PathLines
@onready var traveled_lines: MeshInstance3D = $Debug/TraveledLines
@onready var body_mesh: MeshInstance3D = $BodyMesh

var _all_nodes_dim_material: StandardMaterial3D
var _all_nodes_highlight_material: StandardMaterial3D
var _body_material: StandardMaterial3D
var _graph_positions: Dictionary = {}
var _graph_neighbors: Dictionary = {}
var _search_frontier: Array[int] = []
var _priority_frontier_heap: Array = []
var _frontier_membership: Dictionary = {}
var _search_closed_order: Array[int] = []
var _closed_membership: Dictionary = {}
var _g_score: Dictionary = {}
var _f_score: Dictionary = {}
var _came_from: Dictionary = {}
var _search_started := false
var _search_finished := false
var _path_found := false
var _search_start_id := -1
var _search_goal_id := -1
var _path_node_ids: Array[int] = []
var _path_points: Array[Vector3] = []
var _travel_points: Array[Vector3] = []
var _current_waypoint_idx := 0
var _visual_tick := 0
var _last_reported_waypoint := -1
var _search_tick_timer := 0.0
var _frontier_queue_head := 0
var _debug_overlay_refresh_accum := 0.0
var _all_nodes_highlighted := true
var _debug_canvas: CanvasLayer
var _debug_panel: PanelContainer
var _debug_label: Label
var _debug_overlay_visible := true
var _debug_overlay_dirty := true
var _visited_vertex_count := 0
var _visited_edge_count := 0
var _discovered_vertex_count := 0
var _path_total_cost := 0.0
var _awaiting_algorithm_selection := true
var _run_all_mode := false
var _run_all_queue: Array[int] = []
var _comparison_rows: Array[Dictionary] = []
var _current_search_started_usec := 0
var _skip_path_follow := false
var _default_search_tick_delay := 0.0
var _default_search_steps_per_tick := 0
var _default_visual_update_interval := 0
var _start_highlight: MeshInstance3D
var _goal_highlight: MeshInstance3D


func _ready() -> void:
	debug_root.top_level = true
	debug_root.global_transform = Transform3D.IDENTITY
	_default_search_tick_delay = search_tick_delay
	_default_search_steps_per_tick = search_steps_per_tick
	_default_visual_update_interval = visual_update_interval
	_load_navigation_graph()
	_setup_debug_meshes()
	_setup_debug_overlay()
	_snap_to_start()
	_init_goal_marker()
	_update_highlight_positions()
	print("PathBot: chọn một thuật toán từ bảng hoặc nhấn 1-6, F3 để bật/tắt debug, H để tô sáng node")


func _init_goal_marker() -> void:
	var goal_marker := get_node_or_null(goal_marker_path) as Marker3D
	if goal_marker:
		_search_goal_id = _snap_marker_to_nearest_node(goal_marker, "goal")


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		match event.keycode:
			KEY_H:
				_all_nodes_highlighted = not _all_nodes_highlighted
				all_nodes_markers.material_override = _all_nodes_highlight_material if _all_nodes_highlighted else _all_nodes_dim_material
				print("PathBot: all nodes highlight %s" % ("ON" if _all_nodes_highlighted else "OFF"))
			KEY_F3:
				_debug_overlay_visible = not _debug_overlay_visible
				_debug_canvas.visible = _debug_overlay_visible
				_update_debug_overlay()
				print("PathBot: debug overlay %s" % ("ON" if _debug_overlay_visible else "OFF"))
			KEY_1:
				_set_search_algorithm(SearchAlgorithm.ASTAR)
			KEY_2:
				_set_search_algorithm(SearchAlgorithm.BFS)
			KEY_3:
				_set_search_algorithm(SearchAlgorithm.DFS)
			KEY_4:
				_set_search_algorithm(SearchAlgorithm.UCS)
			KEY_5:
				_set_search_algorithm(SearchAlgorithm.GREEDY)
			KEY_6:
				_set_search_algorithm(SearchAlgorithm.HILL_CLIMBING)
			KEY_0:
				start_search_with_all()
			KEY_7:
				_adjust_search_speed(-1)
			KEY_8:
				_adjust_search_speed(1)


func _physics_process(delta: float) -> void:
	if _awaiting_algorithm_selection:
		_refresh_debug_overlay_if_needed(delta)
		return
	if not _search_finished:
		_search_tick_timer += delta
		if _search_tick_timer >= search_tick_delay:
			_search_tick_timer = 0.0
			_step_search()
	elif _path_found and not _skip_path_follow:
		_follow_path(delta)
	else:
		velocity = Vector3.ZERO
	_refresh_debug_overlay_if_needed(delta)


func _setup_debug_meshes() -> void:
	var cube := BoxMesh.new()
	cube.size = Vector3.ONE
	var node_capacity: int = max(_graph_positions.size(), 1)
	all_nodes_markers.multimesh = _create_multimesh(cube, node_capacity)
	frontier_markers.multimesh = _create_multimesh(cube, node_capacity)
	closed_markers.multimesh = _create_multimesh(cube, node_capacity)
	path_markers.multimesh = _create_multimesh(cube, node_capacity)
	_all_nodes_dim_material = _make_unshaded_material(Color(0.7, 0.9, 1.0, 0.45), true)
	_all_nodes_highlight_material = _make_unshaded_material(Color(1.0, 0.98, 0.2, 1.0), true)
	_body_material = _make_unshaded_material(_get_algorithm_color(search_algorithm))
	body_mesh.material_override = _body_material
	all_nodes_markers.material_override = _all_nodes_highlight_material if _all_nodes_highlighted else _all_nodes_dim_material
	
	_start_highlight = MeshInstance3D.new()
	var start_mesh := CylinderMesh.new()
	start_mesh.top_radius = 0.6
	start_mesh.bottom_radius = 0.6
	start_mesh.height = 2.0
	_start_highlight.mesh = start_mesh
	_start_highlight.material_override = _make_unshaded_material(Color(0.2, 1.0, 0.2, 0.6), true)
	debug_root.add_child(_start_highlight)
	
	_goal_highlight = MeshInstance3D.new()
	var goal_mesh := CylinderMesh.new()
	goal_mesh.top_radius = 0.6
	goal_mesh.bottom_radius = 0.6
	goal_mesh.height = 2.0
	_goal_highlight.mesh = goal_mesh
	_goal_highlight.material_override = _make_unshaded_material(Color(1.0, 0.2, 0.2, 0.6), true)
	debug_root.add_child(_goal_highlight)
	
	_apply_algorithm_visual_theme(search_algorithm)
	_refresh_all_nodes_visual()


func _setup_debug_overlay() -> void:
	_debug_canvas = CanvasLayer.new()
	_debug_canvas.layer = 100
	_debug_canvas.visible = _debug_overlay_visible
	add_child(_debug_canvas)

	_debug_panel = PanelContainer.new()
	var panel_style := StyleBoxFlat.new()
	panel_style.bg_color = Color(0.04, 0.07, 0.11, 0.88)
	panel_style.border_width_left = 2
	panel_style.border_width_top = 2
	panel_style.border_width_right = 2
	panel_style.border_width_bottom = 2
	panel_style.border_color = Color(0.42, 0.68, 0.98, 0.95)
	panel_style.corner_radius_top_left = 16
	panel_style.corner_radius_top_right = 16
	panel_style.corner_radius_bottom_right = 16
	panel_style.corner_radius_bottom_left = 16
	_debug_panel.add_theme_stylebox_override("panel", panel_style)
	_debug_panel.custom_minimum_size = Vector2(760.0, 118.0)
	_debug_panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_debug_canvas.add_child(_debug_panel)

	var debug_margin := MarginContainer.new()
	debug_margin.add_theme_constant_override("margin_left", 18)
	debug_margin.add_theme_constant_override("margin_top", 12)
	debug_margin.add_theme_constant_override("margin_right", 18)
	debug_margin.add_theme_constant_override("margin_bottom", 12)
	debug_margin.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_debug_panel.add_child(debug_margin)

	_debug_label = Label.new()
	_debug_label.size = Vector2(724.0, 94.0)
	_debug_label.autowrap_mode = TextServer.AUTOWRAP_OFF
	_debug_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_LEFT
	_debug_label.vertical_alignment = VERTICAL_ALIGNMENT_TOP
	_debug_label.add_theme_font_size_override("font_size", 14)
	_debug_label.add_theme_color_override("font_color", Color(0.95, 0.98, 1.0, 1.0))
	_debug_label.add_theme_color_override("font_shadow_color", Color(0.0, 0.0, 0.0, 0.92))
	_debug_label.add_theme_constant_override("shadow_offset_x", 2)
	_debug_label.add_theme_constant_override("shadow_offset_y", 2)
	_debug_label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	debug_margin.add_child(_debug_label)
	get_viewport().size_changed.connect(_update_debug_overlay_layout)
	_update_debug_overlay_layout()


func _update_debug_overlay_layout() -> void:
	if _debug_panel == null:
		return
	var viewport_size := get_viewport().get_visible_rect().size
	var panel_size := _debug_panel.custom_minimum_size
	_debug_panel.position = Vector2(16.0, 16.0)


func _create_multimesh(mesh: Mesh, capacity: int) -> MultiMesh:
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.use_colors = false
	mm.use_custom_data = false
	mm.mesh = mesh
	mm.instance_count = capacity
	mm.visible_instance_count = 0
	return mm


func _load_navigation_graph() -> void:
	var graph_path := "res://assets/navigation_graph.json"
	var file := FileAccess.open(graph_path, FileAccess.READ)
	if file == null:
		var fallback_path := ProjectSettings.globalize_path("res://").path_join("../data/navigation_graph.json").simplify_path()
		file = FileAccess.open(fallback_path, FileAccess.READ)
	if file == null:
		push_error("Unable to open navigation graph")
		return
	var parsed: Variant = JSON.parse_string(file.get_as_text())
	if typeof(parsed) != TYPE_DICTIONARY:
		push_error("Navigation graph JSON is invalid")
		return

	for node_data in parsed.get("nodes", []):
		var node_id: int = int(node_data["id"])
		var pos_arr: Array = node_data["position"]
		var pos := Vector3(float(pos_arr[0]), float(pos_arr[2]), -float(pos_arr[1]))
		_graph_positions[node_id] = pos
		_graph_neighbors[node_id] = node_data.get("neighbors", [])
	print("PathBot: loaded %d navigation nodes" % _graph_positions.size())


func _snap_to_start() -> void:
	var start_marker := get_node_or_null(start_marker_path) as Marker3D
	if start_marker:
		_search_start_id = _snap_marker_to_nearest_node(start_marker, "start")
		if _search_start_id != -1:
			global_position = _graph_positions[_search_start_id]
		else:
			global_position = start_marker.global_position
		_travel_points = [global_position + Vector3(0.0, 0.1, 0.0)]


func _begin_search() -> void:
	if _graph_positions.is_empty():
		return
	var start_marker := get_node_or_null(start_marker_path) as Marker3D
	var goal_marker := get_node_or_null(goal_marker_path) as Marker3D
	if start_marker == null or goal_marker == null:
		push_error("Bot markers are missing")
		return

	_search_start_id = _snap_marker_to_nearest_node(start_marker, "start")
	_search_goal_id = _snap_marker_to_nearest_node(goal_marker, "goal")
	if _search_start_id == -1 or _search_goal_id == -1:
		push_error("Could not resolve start/goal nodes")
		return

	_awaiting_algorithm_selection = false
	_update_highlight_positions()
	_reset_search_state()
	_apply_algorithm_visual_theme(search_algorithm)
	_start_local_search()


func _update_highlight_positions() -> void:
	if _start_highlight != null and _search_start_id != -1:
		_start_highlight.global_position = _graph_positions[_search_start_id] + Vector3(0.0, 1.0, 0.0)
	if _goal_highlight != null and _search_goal_id != -1:
		_goal_highlight.global_position = _graph_positions[_search_goal_id] + Vector3(0.0, 1.0, 0.0)


func set_custom_start(pos: Vector3) -> void:
	var start_marker := get_node_or_null(start_marker_path) as Marker3D
	if start_marker:
		start_marker.global_position = pos
		var id := _snap_marker_to_nearest_node(start_marker, "start")
		if _start_highlight != null and id != -1:
			_start_highlight.global_position = _graph_positions[id] + Vector3(0.0, 1.0, 0.0)
	if not _awaiting_algorithm_selection:
		_begin_search()


func set_custom_goal(pos: Vector3) -> void:
	var goal_marker := get_node_or_null(goal_marker_path) as Marker3D
	if goal_marker:
		goal_marker.global_position = pos
		var id := _snap_marker_to_nearest_node(goal_marker, "goal")
		if _goal_highlight != null and id != -1:
			_goal_highlight.global_position = _graph_positions[id] + Vector3(0.0, 1.0, 0.0)
	if not _awaiting_algorithm_selection:
		_begin_search()


func _reset_search_state() -> void:
	_search_frontier.clear()
	_priority_frontier_heap.clear()
	_frontier_membership.clear()
	_search_closed_order.clear()
	_closed_membership.clear()
	_g_score.clear()
	_f_score.clear()
	_came_from.clear()
	_path_node_ids.clear()
	_path_points.clear()
	_path_total_cost = 0.0
	_current_waypoint_idx = 0
	_last_reported_waypoint = -1
	_search_started = true
	_search_finished = false
	_path_found = false
	_visual_tick = 0
	_search_tick_timer = 0.0
	_frontier_queue_head = 0
	_debug_overlay_refresh_accum = 0.0
	_debug_overlay_dirty = true
	_visited_vertex_count = 0
	_visited_edge_count = 0
	_discovered_vertex_count = 0
	velocity = Vector3.ZERO
	global_position = _graph_positions[_search_start_id]
	_travel_points = [global_position + Vector3(0.0, 0.1, 0.0)]
	_current_search_started_usec = Time.get_ticks_usec()


func _start_local_search() -> void:
	if search_algorithm == SearchAlgorithm.HILL_CLIMBING:
		print("PathBot: searching from node %d to node %d with %s" % [_search_start_id, _search_goal_id, _get_algorithm_name()])
		_run_hill_climbing_search()
		return

	_g_score[_search_start_id] = 0.0
	_f_score[_search_start_id] = _frontier_priority(_search_start_id, 0.0)
	_push_frontier(_search_start_id)
	print("PathBot: searching from node %d to node %d with %s" % [_search_start_id, _search_goal_id, _get_algorithm_name()])
	_refresh_debug_visuals()


func _snap_marker_to_nearest_node(marker: Marker3D, label: String) -> int:
	var node_id := _find_nearest_node_id(marker.global_position)
	if node_id == -1:
		return -1
	var snapped_pos: Vector3 = _graph_positions[node_id]
	marker.global_position = snapped_pos
	print("PathBot: snapped %s marker to node %d at %s" % [label, node_id, snapped_pos])
	return node_id


func _step_search() -> void:
	if not _search_started or search_algorithm == SearchAlgorithm.HILL_CLIMBING:
		return
	for _i in range(search_steps_per_tick):
		if _frontier_membership.is_empty():
			_search_finished = true
			_path_found = false
			print("PathBot: no path found")
			_refresh_debug_visuals()
			_on_search_complete()
			return

		var current_id := _pop_frontier_node()
		if current_id == -1:
			_search_finished = true
			_path_found = false
			print("PathBot: search aborted")
			_refresh_debug_visuals()
			_on_search_complete()
			return

		_closed_membership[current_id] = true
		_search_closed_order.append(current_id)
		_visited_vertex_count += 1
		if current_id == _search_goal_id:
			_finalize_path()
			return

		for neighbor_id_variant in _graph_neighbors.get(current_id, []):
			var neighbor_id := int(neighbor_id_variant)
			_visited_edge_count += 1
			if _closed_membership.has(neighbor_id):
				continue

			match search_algorithm:
				SearchAlgorithm.ASTAR, SearchAlgorithm.UCS, SearchAlgorithm.GREEDY:
					var tentative_g: float = float(_g_score.get(current_id, INF)) + _distance_between(current_id, neighbor_id)
					if tentative_g < float(_g_score.get(neighbor_id, INF)):
						_came_from[neighbor_id] = current_id
						_g_score[neighbor_id] = tentative_g
						_f_score[neighbor_id] = _frontier_priority(neighbor_id, tentative_g)
						_push_frontier(neighbor_id)
				SearchAlgorithm.BFS, SearchAlgorithm.DFS:
					if _frontier_membership.has(neighbor_id) or neighbor_id == _search_start_id or _came_from.has(neighbor_id):
						continue
					_came_from[neighbor_id] = current_id
					_g_score[neighbor_id] = float(_g_score.get(current_id, 0.0)) + _distance_between(current_id, neighbor_id)
					_push_frontier(neighbor_id)

		_visual_tick += 1
		if _visual_tick % visual_update_interval == 0:
			_refresh_debug_visuals()


func _run_hill_climbing_search() -> void:
	const MAX_RESTARTS := 6
	_came_from.clear()
	_g_score.clear()
	_search_closed_order.clear()
	_closed_membership.clear()
	_frontier_membership.clear()
	_discovered_vertex_count = 0
	_visited_vertex_count = 0
	_visited_edge_count = 0

	var found := false
	var best_came_from: Dictionary = {}
	var best_g_score: Dictionary = {}

	for restart_num in range(MAX_RESTARTS + 1):
		if found:
			break
		if not _search_started or _awaiting_algorithm_selection:
			return

		var current_id := _search_start_id
		var visited: Dictionary = {current_id: true}
		var local_came_from: Dictionary = {}
		var local_g: Dictionary = {current_id: 0.0}
		var ops := 0

		for _step in range(_graph_positions.size() * 2):
			if current_id == _search_goal_id:
				found = true
				best_came_from = local_came_from
				best_g_score = local_g
				break

			if not _search_started or _awaiting_algorithm_selection:
				return

			ops += 1
			if ops >= search_steps_per_tick:
				ops = 0
				if search_tick_delay > 0:
					await get_tree().create_timer(search_tick_delay).timeout
				else:
					await get_tree().process_frame

			_closed_membership[current_id] = true
			if not _search_closed_order.has(current_id):
				_search_closed_order.append(current_id)
			_visited_vertex_count += 1
			_visual_tick += 1
			if _visual_tick % visual_update_interval == 0:
				_refresh_debug_visuals()

			var neighbors: Array = _graph_neighbors.get(current_id, [])
			var candidates: Array = []
			for neighbor_id_variant in neighbors:
				var neighbor_id := int(neighbor_id_variant)
				_visited_edge_count += 1
				_discovered_vertex_count += 1
				if not visited.has(neighbor_id):
					candidates.append([_heuristic(neighbor_id, _search_goal_id), neighbor_id])

			if candidates.is_empty():
				break  # stuck — trigger restart

			candidates.sort()

			# Lần đầu: luôn chọn tốt nhất. Lần restart: chọn ngẫu nhiên trong top-3
			var pick_idx := 0
			if restart_num > 0 and candidates.size() > 1:
				pick_idx = randi() % mini(3, candidates.size())

			var best_id := int(candidates[pick_idx][1])
			visited[best_id] = true
			_frontier_membership[best_id] = true
			local_came_from[best_id] = current_id
			local_g[best_id] = float(local_g.get(current_id, 0.0)) + _distance_between(current_id, best_id)
			current_id = best_id

		if not found and restart_num < MAX_RESTARTS:
			print("PathBot: Hill Climbing restart #%d" % (restart_num + 1))

	if found:
		_came_from = best_came_from
		_g_score = best_g_score
		_finalize_path()
		return

	_search_finished = true
	_path_found = false
	print("PathBot: Hill Climbing failed after %d restarts" % MAX_RESTARTS)
	_refresh_debug_visuals()
	_on_search_complete()

func _push_frontier(node_id: int) -> void:
	var is_new := not _frontier_membership.has(node_id)
	_frontier_membership[node_id] = true
	if _uses_priority_frontier():
		_heap_push(float(_f_score.get(node_id, INF)), node_id)
	else:
		_search_frontier.append(node_id)
	if is_new:
		_discovered_vertex_count += 1


func _pop_frontier_node() -> int:
	if _frontier_membership.is_empty():
		return -1

	var picked_id := -1
	match search_algorithm:
		SearchAlgorithm.ASTAR, SearchAlgorithm.UCS, SearchAlgorithm.GREEDY:
			while not _priority_frontier_heap.is_empty():
				var entry: Array = _heap_pop()
				var candidate_id := int(entry[1])
				if not _frontier_membership.has(candidate_id):
					continue
				picked_id = candidate_id
				break
		SearchAlgorithm.BFS:
			var found_in_bfs := false
			while _frontier_queue_head < _search_frontier.size():
				var candidate_id := int(_search_frontier[_frontier_queue_head])
				_frontier_queue_head += 1
				if _frontier_membership.has(candidate_id):
					picked_id = candidate_id
					found_in_bfs = true
					break
			if not found_in_bfs and _frontier_queue_head >= FRONTIER_QUEUE_COMPACT_INTERVAL and _frontier_queue_head * 2 >= _search_frontier.size():
				_search_frontier = _search_frontier.slice(_frontier_queue_head)
				_frontier_queue_head = 0
			elif _frontier_queue_head >= FRONTIER_QUEUE_COMPACT_INTERVAL and _frontier_queue_head * 2 >= _search_frontier.size():
				_search_frontier = _search_frontier.slice(_frontier_queue_head)
				_frontier_queue_head = 0
		SearchAlgorithm.DFS:
			while not _search_frontier.is_empty():
				var candidate_id := int(_search_frontier.pop_back())
				if not _frontier_membership.has(candidate_id):
					continue
				picked_id = candidate_id
				break

	if picked_id != -1:
		_frontier_membership.erase(picked_id)
	return picked_id


func _finalize_path() -> void:
	_search_finished = true
	_path_found = true
	_path_node_ids = _reconstruct_path(_search_goal_id)
	_path_points.clear()
	_path_total_cost = 0.0
	for node_id in _path_node_ids:
		var p: Vector3 = _graph_positions[node_id]
		_path_points.append(Vector3(p.x, p.y + 0.1, p.z))
	for i in range(_path_node_ids.size() - 1):
		_path_total_cost += _distance_between(_path_node_ids[i], _path_node_ids[i + 1])
	_current_waypoint_idx = 0
	_last_reported_waypoint = -1
	print("PathBot: %s path found with %d nodes, cost %.2f" % [_get_algorithm_name(), _path_node_ids.size(), _path_total_cost])
	_refresh_debug_visuals()
	_emit_single_search_result()
	_on_search_complete()


func _reconstruct_path(goal_id: int) -> Array[int]:
	var path: Array[int] = [goal_id]
	var current := goal_id
	while _came_from.has(current):
		current = int(_came_from[current])
		path.push_front(current)
	return path


func _follow_path(delta: float) -> void:
	if _current_waypoint_idx >= _path_points.size():
		velocity = Vector3.ZERO
		return

	var target := _path_points[_current_waypoint_idx]
	if _current_waypoint_idx != _last_reported_waypoint:
		_last_reported_waypoint = _current_waypoint_idx
		print("PathBot: moving to waypoint %d / %d" % [_current_waypoint_idx + 1, _path_points.size()])
	var to_target := target - global_position
	var flat_to_target := Vector3(to_target.x, 0.0, to_target.z)
	if to_target.length() <= WAYPOINT_REACHED_DIST:
		_current_waypoint_idx += 1
		_record_travel_point(target)
		_refresh_traveled_visual()
		if _current_waypoint_idx >= _path_points.size():
			print("PathBot: destination reached")
		return

	global_position = global_position.move_toward(target, BOT_SPEED * delta)
	velocity = to_target.normalized() * BOT_SPEED
	var move_dir := flat_to_target.normalized()
	if move_dir.length() > 0.01:
		look_at(global_position + move_dir, Vector3.UP)


func _record_travel_point(point: Vector3) -> void:
	if _travel_points.is_empty() or _travel_points.back().distance_to(point) > 0.15:
		_travel_points.append(point)


func _find_nearest_node_id(world_pos: Vector3) -> int:
	var best_id := -1
	var best_dist := INF
	for node_id_variant in _graph_positions.keys():
		var node_id := int(node_id_variant)
		var p: Vector3 = _graph_positions[node_id]
		var d := p.distance_squared_to(world_pos)
		if d < best_dist:
			best_dist = d
			best_id = node_id
	return best_id


func _heuristic(a: int, b: int) -> float:
	var from_pos: Vector3 = _graph_positions[a]
	var to_pos: Vector3 = _graph_positions[b]
	return from_pos.distance_to(to_pos) * EDGE_LENGTH_WEIGHT


func _frontier_priority(node_id: int, g_cost: float) -> float:
	match search_algorithm:
		SearchAlgorithm.UCS:
			return g_cost
		SearchAlgorithm.GREEDY:
			return _heuristic(node_id, _search_goal_id)
		_:
			return g_cost + _heuristic(node_id, _search_goal_id)


func _distance_between(a: int, b: int) -> float:
	var from_pos: Vector3 = _graph_positions[a]
	var to_pos: Vector3 = _graph_positions[b]
	var edge_length: float = from_pos.distance_to(to_pos)
	var ascent_delta: float = to_pos.y - from_pos.y
	var ascent: float = maxf(0.0, ascent_delta)
	return edge_length * EDGE_LENGTH_WEIGHT + ascent * ASCENT_COST_WEIGHT


func _refresh_debug_visuals() -> void:
	_refresh_frontier_markers()
	_refresh_closed_markers()
	_refresh_path_visuals()
	_refresh_search_lines()
	_refresh_traveled_visual()
	_request_debug_overlay_refresh()


func _refresh_all_nodes_visual() -> void:
	var all_ids: Array[int] = []
	for node_id_variant in _graph_positions.keys():
		all_ids.append(int(node_id_variant))
	all_ids.sort()
	_apply_marker_instances(all_nodes_markers.multimesh, all_ids, Vector3(0.24, 0.24, 0.24))


func _refresh_frontier_markers() -> void:
	var ids: Array = _sample_node_ids(_frontier_node_ids(), MAX_FRONTIER_MARKERS_DRAW)
	_apply_marker_instances(frontier_markers.multimesh, ids, MARKER_SCALE)


func _refresh_closed_markers() -> void:
	_apply_marker_instances(closed_markers.multimesh, _sample_node_ids(_search_closed_order, MAX_CLOSED_MARKERS_DRAW), MARKER_SCALE)


func _refresh_path_visuals() -> void:
	_apply_marker_instances(path_markers.multimesh, _path_node_ids, PATH_MARKER_SCALE)
	path_lines.mesh = _build_line_mesh(_path_points, Color(0.2, 0.85, 1.0, 1.0))


func _refresh_traveled_visual() -> void:
	traveled_lines.mesh = _build_line_mesh(_travel_points, Color(0.15, 1.0, 0.35, 1.0))


func _refresh_search_lines() -> void:
	var points: Array[Vector3] = []
	var frontier_ids: Array = _sample_node_ids(_frontier_node_ids(), MAX_SEARCH_LINE_SEGMENTS_DRAW)
	for node_id in frontier_ids:
		if not _came_from.has(node_id):
			continue
		var from_id := int(_came_from[node_id])
		points.append(_graph_positions[from_id] + Vector3(0.0, 0.06, 0.0))
		points.append(_graph_positions[node_id] + Vector3(0.0, 0.06, 0.0))
	search_lines.mesh = _build_line_mesh(points, Color(1.0, 0.55, 0.15, 1.0))


func _apply_marker_instances(multimesh: MultiMesh, node_ids: Array, marker_scale: Vector3) -> void:
	if multimesh == null:
		return
	var count: int = min(node_ids.size(), multimesh.instance_count)
	multimesh.visible_instance_count = count
	for i in range(count):
		var node_id := int(node_ids[i])
		var pos: Vector3 = _graph_positions[node_id] + Vector3(0.0, MARKER_HEIGHT, 0.0)
		var marker_transform := Transform3D(Basis().scaled(marker_scale), pos)
		multimesh.set_instance_transform(i, marker_transform)


func _build_line_mesh(points: Array[Vector3], color: Color) -> ImmediateMesh:
	var mesh := ImmediateMesh.new()
	if points.size() < 2:
		return mesh
	var material := _make_unshaded_material(color)
	mesh.surface_begin(Mesh.PRIMITIVE_LINES, material)
	for i in range(points.size() - 1):
		mesh.surface_set_color(color)
		mesh.surface_add_vertex(points[i])
		mesh.surface_add_vertex(points[i + 1])
	mesh.surface_end()
	return mesh


func _make_unshaded_material(color: Color, transparent := false) -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	material.albedo_color = color
	material.vertex_color_use_as_albedo = true
	if transparent:
		material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
		material.no_depth_test = false
	return material


func _uses_priority_frontier() -> bool:
	return search_algorithm == SearchAlgorithm.ASTAR or search_algorithm == SearchAlgorithm.UCS or search_algorithm == SearchAlgorithm.GREEDY


func _heap_push(priority: float, node_id: int) -> void:
	_priority_frontier_heap.append([priority, node_id])
	var idx := _priority_frontier_heap.size() - 1
	while idx > 0:
		var parent := (idx - 1) / 2
		parent = int(parent)
		if float(_priority_frontier_heap[parent][0]) <= float(_priority_frontier_heap[idx][0]):
			break
		var temp = _priority_frontier_heap[parent]
		_priority_frontier_heap[parent] = _priority_frontier_heap[idx]
		_priority_frontier_heap[idx] = temp
		idx = parent


func _heap_pop() -> Array:
	var top: Array = _priority_frontier_heap[0]
	var last: Array = _priority_frontier_heap.pop_back()
	if not _priority_frontier_heap.is_empty():
		_priority_frontier_heap[0] = last
		var idx := 0
		while true:
			var left := idx * 2 + 1
			var right := left + 1
			var smallest := idx
			if left < _priority_frontier_heap.size() and float(_priority_frontier_heap[left][0]) < float(_priority_frontier_heap[smallest][0]):
				smallest = left
			if right < _priority_frontier_heap.size() and float(_priority_frontier_heap[right][0]) < float(_priority_frontier_heap[smallest][0]):
				smallest = right
			if smallest == idx:
				break
			var temp = _priority_frontier_heap[idx]
			_priority_frontier_heap[idx] = _priority_frontier_heap[smallest]
			_priority_frontier_heap[smallest] = temp
			idx = smallest
	return top


func _frontier_node_ids() -> Array:
	var ids: Array = []
	for node_id_variant in _frontier_membership.keys():
		ids.append(int(node_id_variant))
	return ids


func _sample_node_ids(node_ids: Array, max_count: int) -> Array:
	if node_ids.size() <= max_count:
		return node_ids
	var sampled: Array = []
	var step := float(node_ids.size()) / float(max_count)
	var cursor := 0.0
	while sampled.size() < max_count:
		var idx := mini(int(cursor), node_ids.size() - 1)
		sampled.append(node_ids[idx])
		cursor += step
	return sampled


func _request_debug_overlay_refresh() -> void:
	_debug_overlay_dirty = true


func _refresh_debug_overlay_if_needed(delta: float, force := false) -> void:
	if _debug_label == null or not _debug_overlay_visible:
		return
	_debug_overlay_refresh_accum += delta
	if force or _debug_overlay_dirty or _debug_overlay_refresh_accum >= DEBUG_OVERLAY_REFRESH_SEC:
		_debug_overlay_refresh_accum = 0.0
		_update_debug_overlay()
		_debug_overlay_dirty = false


func _set_search_algorithm(next_algorithm: int) -> void:
	if search_algorithm == next_algorithm and not _awaiting_algorithm_selection:
		return
	_run_all_mode = false
	_run_all_queue.clear()
	_comparison_rows.clear()
	_skip_path_follow = false
	search_tick_delay = SINGLE_RUN_TICK_DELAY
	search_steps_per_tick = _default_search_steps_per_tick
	visual_update_interval = _default_visual_update_interval
	search_algorithm = next_algorithm
	print("PathBot: switched algorithm to %s" % _get_algorithm_name())
	_begin_search()


func start_search_with_algorithm(next_algorithm: int) -> void:
	_set_search_algorithm(next_algorithm)


func return_to_menu_state() -> void:
	_run_all_mode = false
	_run_all_queue.clear()
	_comparison_rows.clear()
	_skip_path_follow = false
	_search_started = false
	_search_finished = true
	_path_found = false
	_awaiting_algorithm_selection = true
	_search_tick_timer = 0.0
	_frontier_queue_head = 0
	velocity = Vector3.ZERO
	search_tick_delay = _default_search_tick_delay
	search_steps_per_tick = _default_search_steps_per_tick
	visual_update_interval = _default_visual_update_interval
	_search_frontier.clear()
	_priority_frontier_heap.clear()
	_frontier_membership.clear()
	_search_closed_order.clear()
	_closed_membership.clear()
	_came_from.clear()
	_g_score.clear()
	_f_score.clear()
	_path_node_ids.clear()
	_path_points.clear()
	_request_debug_overlay_refresh()
	_refresh_debug_visuals()


func start_search_with_all() -> void:
	_run_all_mode = true
	_skip_path_follow = true
	_comparison_rows.clear()
	search_tick_delay = RUN_ALL_TICK_DELAY
	search_steps_per_tick = RUN_ALL_STEPS_PER_TICK
	visual_update_interval = RUN_ALL_VISUAL_UPDATE_INTERVAL
	_run_all_queue.clear()
	for algorithm_id in ALGORITHM_SEQUENCE:
		_run_all_queue.append(int(algorithm_id))
	_start_next_algorithm_in_queue()


func get_algorithm_menu_rows() -> Array[Dictionary]:
	return [
		{
			"id": ALL_ALGORITHMS_ID,
			"name": "Tất cả",
			"shortcut": "0",
			"description": "Chạy A*, BFS, DFS, UCS, Greedy, HillClimbing và hiện bảng so sánh.",
		},
		{
			"id": SearchAlgorithm.ASTAR,
			"name": "A*",
			"shortcut": "1",
			"description": "Cân bằng giữa chi phí đã đi và ước lượng đến đích.",
		},
		{
			"id": SearchAlgorithm.BFS,
			"name": "BFS",
			"shortcut": "2",
			"description": "Duyệt theo từng lớp, hợp với đường đi ít cung.",
		},
		{
			"id": SearchAlgorithm.DFS,
			"name": "DFS",
			"shortcut": "3",
			"description": "Đi sâu theo nhánh, dễ quan sát cách mở rộng trạng thái.",
		},
		{
			"id": SearchAlgorithm.UCS,
			"name": "UCS",
			"shortcut": "4",
			"description": "Luôn mở rộng nút có chi phí tích lũy nhỏ nhất.",
		},
		{
			"id": SearchAlgorithm.GREEDY,
			"name": "Greedy",
			"shortcut": "5",
			"description": "Chọn nút có heuristic tốt nhất, nhanh nhưng dễ lệch hướng.",
		},
		{
			"id": SearchAlgorithm.HILL_CLIMBING,
			"name": "HillClimbing",
			"shortcut": "6",
			"description": "Chọn hàng xóm tốt nhất theo heuristic, nhanh nhưng có thể bị kẹt ở cực trị cục bộ.",
		},
	]


func _get_algorithm_name() -> String:
	match search_algorithm:
		SearchAlgorithm.ASTAR:
			return "A*"
		SearchAlgorithm.BFS:
			return "BFS"
		SearchAlgorithm.DFS:
			return "DFS"
		SearchAlgorithm.UCS:
			return "UCS"
		SearchAlgorithm.GREEDY:
			return "Greedy"
		SearchAlgorithm.HILL_CLIMBING:
			return "HillClimbing"
	return "Unknown"


func _get_algorithm_color(algorithm_id: int) -> Color:
	match algorithm_id:
		SearchAlgorithm.ASTAR:
			return Color(0.1, 0.72, 1.0, 1.0)
		SearchAlgorithm.BFS:
			return Color(0.16, 0.82, 0.38, 1.0)
		SearchAlgorithm.DFS:
			return Color(0.95, 0.52, 0.16, 1.0)
		SearchAlgorithm.UCS:
			return Color(0.92, 0.24, 0.36, 1.0)
		SearchAlgorithm.GREEDY:
			return Color(0.58, 0.34, 0.98, 1.0)
		SearchAlgorithm.HILL_CLIMBING:
			return Color(0.96, 0.77, 0.12, 1.0)
	return Color(0.15, 0.85, 1.0, 1.0)


func _apply_algorithm_visual_theme(algorithm_id: int) -> void:
	var accent := _get_algorithm_color(algorithm_id)
	var frontier_color := accent.lightened(0.12)
	var closed_color := accent.darkened(0.24)
	var traveled_color := accent.lerp(Color(1.0, 1.0, 1.0, 1.0), 0.2)
	if _body_material != null:
		_body_material.albedo_color = accent
	body_mesh.material_override = _body_material
	frontier_markers.material_override = _make_unshaded_material(frontier_color)
	closed_markers.material_override = _make_unshaded_material(closed_color)
	path_markers.material_override = _make_unshaded_material(accent)
	path_lines.mesh = _build_line_mesh(_path_points, accent)
	search_lines.mesh = _build_line_mesh([], frontier_color)
	traveled_lines.mesh = _build_line_mesh(_travel_points, traveled_color)


func _start_next_algorithm_in_queue() -> void:
	if _run_all_queue.is_empty():
		_run_all_mode = false
		search_tick_delay = _default_search_tick_delay
		search_steps_per_tick = _default_search_steps_per_tick
		visual_update_interval = _default_visual_update_interval
		comparison_ready.emit(_comparison_rows.duplicate(true))
		return
	search_algorithm = int(_run_all_queue.pop_front())
	print("PathBot: chạy thuật toán %s trong chế độ so sánh" % _get_algorithm_name())
	_begin_search()


func _on_search_complete() -> void:
	if not _run_all_mode:
		return
	var elapsed_ms := maxf(0.0, float(Time.get_ticks_usec() - _current_search_started_usec) / 1000.0)
	_comparison_rows.append({
		"algorithm_id": search_algorithm,
		"algorithm": _get_algorithm_name(),
		"color": _get_algorithm_color(search_algorithm),
		"found": _path_found,
		"elapsed_ms": elapsed_ms,
		"path_nodes": _path_node_ids.size(),
		"path_cost": _path_total_cost,
		"visited_vertices": _visited_vertex_count,
		"visited_edges": _visited_edge_count,
		"discovered_vertices": _discovered_vertex_count,
	})
	call_deferred("_start_next_algorithm_in_queue")


func _emit_single_search_result() -> void:
	if _run_all_mode or not _path_found:
		return
	var elapsed_ms := maxf(0.0, float(Time.get_ticks_usec() - _current_search_started_usec) / 1000.0)
	search_result_ready.emit({
		"algorithm_id": search_algorithm,
		"algorithm": _get_algorithm_name(),
		"color": _get_algorithm_color(search_algorithm),
		"found": _path_found,
		"elapsed_ms": elapsed_ms,
		"path_nodes": _path_node_ids.size(),
		"path_cost": _path_total_cost,
		"visited_vertices": _visited_vertex_count,
		"visited_edges": _visited_edge_count,
		"discovered_vertices": _discovered_vertex_count,
		"start_id": _search_start_id,
		"goal_id": _search_goal_id,
	})


func _get_search_status() -> String:
	if _awaiting_algorithm_selection:
		return "waiting selection"
	if not _search_started:
		return "idle"
	if _run_all_mode:
		return "running all"
	if _path_found and _search_finished:
		return "path found"
	if _search_finished:
		return "failed"
	return "searching"


func _update_debug_overlay() -> void:
	if _debug_label == null:
		return
	var current_waypoint_display := 0
	if not _path_points.is_empty():
		current_waypoint_display = min(_current_waypoint_idx + 1, _path_points.size())
	var lines := [
		"PathBot Debug",
		"Algorithm: %s" % _get_algorithm_name(),
		"Backend: Local GDScript",
		"Status: %s" % _get_search_status(),
		"Start -> Goal: %d -> %d" % [_search_start_id, _search_goal_id],
		"Visited vertices: %d" % _visited_vertex_count,
		"Visited edges: %d" % _visited_edge_count,
		"Discovered vertices: %d" % _discovered_vertex_count,
		"Tick rate: %.1f ticks/s" % (1.0 / search_tick_delay if search_tick_delay > 0.0 else 0.0),
		"Work rate: %d steps/tick" % search_steps_per_tick,
		"Frontier size: %d" % _frontier_membership.size(),
		"Closed size: %d" % _search_closed_order.size(),
		"Path nodes: %d" % _path_node_ids.size(),
		"Path cost: %.2f" % _path_total_cost,
		"Waypoint: %d / %d" % [current_waypoint_display, _path_points.size()],
		"Hotkeys: 0=All  1=A*  2=BFS  3=DFS  4=UCS  5=Greedy  6=IDDFS",
		"         7/8=speed  F3=overlay  H=highlight",
	]
	_debug_label.text = "\n".join(lines)


func _adjust_search_speed(delta_steps: int) -> void:
	var previous_steps := search_steps_per_tick
	search_steps_per_tick = clamp(search_steps_per_tick + delta_steps, MIN_SEARCH_STEPS_PER_TICK, MAX_SEARCH_STEPS_PER_TICK)
	if previous_steps != search_steps_per_tick:
		print("PathBot: search speed = %d steps/tick" % search_steps_per_tick)
		_update_debug_overlay()
