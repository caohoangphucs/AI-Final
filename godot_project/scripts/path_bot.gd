extends CharacterBody3D

const BOT_SPEED := 4.5
const WAYPOINT_REACHED_DIST := 0.22
const MARKER_HEIGHT := 0.4
const MARKER_SCALE := Vector3(0.5, 0.5, 0.5)
const PATH_MARKER_SCALE := Vector3(0.62, 0.62, 0.62)
const MIN_SEARCH_STEPS_PER_TICK := 1
const MAX_SEARCH_STEPS_PER_TICK := 64
const USE_REMOTE_SOLVER := true
const EDGE_LENGTH_WEIGHT := 1.0
const ASCENT_COST_WEIGHT := 4.0

enum SearchAlgorithm {
	ASTAR,
	BFS,
	DFS,
	UCS,
	GREEDY,
	IDDFS,
}

@export var start_marker_path: NodePath
@export var goal_marker_path: NodePath
@export_range(1, 64, 1) var search_steps_per_tick := 2
@export_range(0.01, 1.0, 0.01) var search_tick_delay := 0.08
@export_range(1, 64, 1) var visual_update_interval := 1
@export_enum("A*", "BFS", "DFS", "UCS", "Greedy", "IDDFS") var search_algorithm: int = SearchAlgorithm.ASTAR
@export var remote_solver_url := "http://127.0.0.1:8000/solve-path"
@export var remote_benchmark_url := "http://127.0.0.1:8000/benchmark-path"
@export_range(1.0, 60.0, 0.5) var remote_solver_timeout_sec := 10.0

@onready var debug_root: Node3D = $Debug
@onready var all_nodes_markers: MultiMeshInstance3D = $Debug/AllNodesMarkers
@onready var frontier_markers: MultiMeshInstance3D = $Debug/FrontierMarkers
@onready var closed_markers: MultiMeshInstance3D = $Debug/ClosedMarkers
@onready var path_markers: MultiMeshInstance3D = $Debug/PathMarkers
@onready var search_lines: MeshInstance3D = $Debug/SearchLines
@onready var path_lines: MeshInstance3D = $Debug/PathLines
@onready var traveled_lines: MeshInstance3D = $Debug/TraveledLines

var _all_nodes_dim_material: StandardMaterial3D
var _all_nodes_highlight_material: StandardMaterial3D
var _graph_positions: Dictionary = {}
var _graph_neighbors: Dictionary = {}
var _search_frontier: Array[int] = []
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
var _all_nodes_highlighted := true
var _debug_canvas: CanvasLayer
var _debug_label: Label
var _debug_overlay_visible := true
var _visited_vertex_count := 0
var _visited_edge_count := 0
var _discovered_vertex_count := 0
var _path_total_cost := 0.0
var _using_remote_path := false
var _remote_request_in_flight := false
var _http_request: HTTPRequest
var _benchmark_request_in_flight := false
var _benchmark_http_request: HTTPRequest
var _benchmark_summary_text := ""


func _ready() -> void:
	debug_root.top_level = true
	debug_root.global_transform = Transform3D.IDENTITY
	_load_navigation_graph()
	_setup_debug_meshes()
	_setup_debug_overlay()
	_setup_http_request()
	_snap_to_start()
	_begin_search()
	print("PathBot: 1=A*, 2=BFS, 3=DFS, 4=UCS, 5=Greedy, 6=IDDFS, P=benchmark all, F3=toggle debug info, H=highlight all nodes")


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
				_set_search_algorithm(SearchAlgorithm.IDDFS)
			KEY_P:
				_run_remote_benchmark()
			KEY_7:
				_adjust_search_speed(-1)
			KEY_8:
				_adjust_search_speed(1)


func _physics_process(delta: float) -> void:
	if not _search_finished and not _using_remote_path:
		_search_tick_timer += delta
		if _search_tick_timer >= search_tick_delay:
			_search_tick_timer = 0.0
			_step_search()
	elif _path_found:
		_follow_path(delta)
	else:
		velocity = Vector3.ZERO
	_update_debug_overlay()


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
	all_nodes_markers.material_override = _all_nodes_highlight_material if _all_nodes_highlighted else _all_nodes_dim_material
	frontier_markers.material_override = _make_unshaded_material(Color(1.0, 0.58, 0.15, 1.0))
	closed_markers.material_override = _make_unshaded_material(Color(1.0, 0.2, 0.2, 1.0))
	path_markers.material_override = _make_unshaded_material(Color(0.15, 0.85, 1.0, 1.0))
	_refresh_all_nodes_visual()


func _setup_debug_overlay() -> void:
	_debug_canvas = CanvasLayer.new()
	_debug_canvas.layer = 100
	_debug_canvas.visible = _debug_overlay_visible
	add_child(_debug_canvas)

	_debug_label = Label.new()
	_debug_label.position = Vector2(max(get_viewport().get_visible_rect().size.x - 536.0, 16.0), 16.0)
	_debug_label.size = Vector2(520.0, 260.0)
	_debug_label.autowrap_mode = TextServer.AUTOWRAP_OFF
	_debug_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_LEFT
	_debug_label.vertical_alignment = VERTICAL_ALIGNMENT_TOP
	_debug_label.add_theme_font_size_override("font_size", 15)
	_debug_label.add_theme_color_override("font_color", Color(0.95, 0.98, 1.0, 1.0))
	_debug_label.add_theme_color_override("font_shadow_color", Color(0.02, 0.03, 0.05, 0.95))
	_debug_label.add_theme_constant_override("shadow_offset_x", 1)
	_debug_label.add_theme_constant_override("shadow_offset_y", 1)
	_debug_canvas.add_child(_debug_label)
	get_viewport().size_changed.connect(_update_debug_overlay_layout)
	_update_debug_overlay_layout()


func _update_debug_overlay_layout() -> void:
	if _debug_label == null:
		return
	var viewport_width: float = get_viewport().get_visible_rect().size.x
	_debug_label.position = Vector2(maxf(viewport_width - _debug_label.size.x - 16.0, 16.0), 16.0)


func _setup_http_request() -> void:
	_http_request = HTTPRequest.new()
	_http_request.timeout = remote_solver_timeout_sec
	add_child(_http_request)
	_http_request.request_completed.connect(_on_remote_request_completed)

	_benchmark_http_request = HTTPRequest.new()
	_benchmark_http_request.timeout = remote_solver_timeout_sec
	add_child(_benchmark_http_request)
	_benchmark_http_request.request_completed.connect(_on_benchmark_request_completed)


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
	var graph_path := ProjectSettings.globalize_path("res://").path_join("../data/navigation_graph.json").simplify_path()
	var file := FileAccess.open(graph_path, FileAccess.READ)
	if file == null:
		push_error("Unable to open navigation graph: %s" % graph_path)
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
		var start_id := _snap_marker_to_nearest_node(start_marker, "start")
		if start_id != -1:
			global_position = _graph_positions[start_id]
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

	_reset_search_state()
	if USE_REMOTE_SOLVER and _start_remote_search_request():
		return
	_start_local_search()


func _reset_search_state() -> void:
	_search_frontier.clear()
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
	_visited_vertex_count = 0
	_visited_edge_count = 0
	_discovered_vertex_count = 0
	_using_remote_path = false
	_remote_request_in_flight = false
	velocity = Vector3.ZERO
	global_position = _graph_positions[_search_start_id]
	_travel_points = [global_position + Vector3(0.0, 0.1, 0.0)]


func _start_local_search() -> void:
	_using_remote_path = false
	if search_algorithm == SearchAlgorithm.IDDFS:
		print("PathBot: local fallback for IDDFS uses DFS; full IDDFS runs on Python service")

	_g_score[_search_start_id] = 0.0
	_f_score[_search_start_id] = _frontier_priority(_search_start_id, 0.0)
	_push_frontier(_search_start_id)
	print("PathBot: searching from node %d to node %d with %s" % [_search_start_id, _search_goal_id, _get_algorithm_name()])
	_refresh_debug_visuals()


func _start_remote_search_request() -> bool:
	if _http_request == null:
		return false

	var payload := JSON.stringify({
		"start_id": _search_start_id,
		"goal_id": _search_goal_id,
		"algorithm": _get_algorithm_slug(),
	})
	var err := _http_request.request(
		remote_solver_url,
		["Content-Type: application/json"],
		HTTPClient.METHOD_POST,
		payload,
	)
	if err != OK:
		print("PathBot: remote solver unavailable (request error %d), falling back to local search" % err)
		return false

	_using_remote_path = true
	_remote_request_in_flight = true
	print("PathBot: requesting remote %s path from node %d to node %d" % [_get_algorithm_name(), _search_start_id, _search_goal_id])
	_refresh_debug_visuals()
	return true


func _run_remote_benchmark() -> void:
	if not USE_REMOTE_SOLVER:
		print("PathBot: benchmark requires remote solver")
		return
	if _benchmark_http_request == null or _remote_request_in_flight or _benchmark_request_in_flight:
		print("PathBot: benchmark request is busy")
		return
	if _search_start_id == -1 or _search_goal_id == -1:
		print("PathBot: benchmark unavailable until start/goal are resolved")
		return

	var payload := JSON.stringify({
		"start_id": _search_start_id,
		"goal_id": _search_goal_id,
	})
	var err := _benchmark_http_request.request(
		remote_benchmark_url,
		["Content-Type: application/json"],
		HTTPClient.METHOD_POST,
		payload,
	)
	if err != OK:
		print("PathBot: benchmark request error %d" % err)
		return

	_benchmark_request_in_flight = true
	_benchmark_summary_text = "Benchmark: running all algorithms..."
	print("PathBot: benchmarking all algorithms from node %d to node %d" % [_search_start_id, _search_goal_id])
	_update_debug_overlay()


func _on_remote_request_completed(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	if not _remote_request_in_flight:
		return
	_remote_request_in_flight = false

	if result != HTTPRequest.RESULT_SUCCESS or response_code < 200 or response_code >= 300:
		print("PathBot: remote solver failed (result=%d, status=%d), falling back to local search" % [result, response_code])
		_reset_search_state()
		_start_local_search()
		return

	var body_text := body.get_string_from_utf8()
	var parsed: Variant = JSON.parse_string(body_text)
	if typeof(parsed) != TYPE_DICTIONARY:
		print("PathBot: remote solver returned invalid JSON, falling back to local search")
		_reset_search_state()
		_start_local_search()
		return

	_apply_remote_solution(parsed)


func _on_benchmark_request_completed(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	_benchmark_request_in_flight = false

	if result != HTTPRequest.RESULT_SUCCESS or response_code < 200 or response_code >= 300:
		_benchmark_summary_text = "Benchmark: request failed (result=%d, status=%d)" % [result, response_code]
		print("PathBot: benchmark failed (result=%d, status=%d)" % [result, response_code])
		_update_debug_overlay()
		return

	var body_text := body.get_string_from_utf8()
	var parsed: Variant = JSON.parse_string(body_text)
	if typeof(parsed) != TYPE_DICTIONARY:
		_benchmark_summary_text = "Benchmark: invalid JSON response"
		print("PathBot: benchmark returned invalid JSON")
		_update_debug_overlay()
		return

	_benchmark_summary_text = _format_benchmark_summary(parsed)
	print("PathBot: benchmark complete")
	_update_debug_overlay()


func _apply_remote_solution(payload: Dictionary) -> void:
	_using_remote_path = true
	_search_started = true
	_search_finished = true
	_path_found = bool(payload.get("found", false))
	_visited_vertex_count = int(payload.get("visited_vertices", 0))
	_visited_edge_count = int(payload.get("visited_edges", 0))
	_discovered_vertex_count = int(payload.get("discovered_vertices", 0))
	_path_total_cost = float(payload.get("path_cost", 0.0))
	_path_node_ids.clear()
	_path_points.clear()
	_current_waypoint_idx = 0
	_last_reported_waypoint = -1

	for node_id_variant in payload.get("path_node_ids", []):
		_path_node_ids.append(int(node_id_variant))

	if _path_found:
		for node_id in _path_node_ids:
			var p: Vector3 = _graph_positions.get(node_id, Vector3.ZERO)
			_path_points.append(Vector3(p.x, p.y + 0.1, p.z))
		print("PathBot: remote %s path found with %d nodes, cost %.2f" % [_get_algorithm_name(), _path_node_ids.size(), _path_total_cost])
	else:
		print("PathBot: remote solver returned no path")

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
	if not _search_started:
		return
	for _i in range(search_steps_per_tick):
		if _search_frontier.is_empty():
			_search_finished = true
			_path_found = false
			print("PathBot: no path found")
			_refresh_debug_visuals()
			return

		var current_id := _pop_frontier_node()
		if current_id == -1:
			_search_finished = true
			_path_found = false
			print("PathBot: search aborted")
			_refresh_debug_visuals()
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
						if not _frontier_membership.has(neighbor_id):
							_push_frontier(neighbor_id)
				SearchAlgorithm.BFS, SearchAlgorithm.DFS, SearchAlgorithm.IDDFS:
					if _frontier_membership.has(neighbor_id) or neighbor_id == _search_start_id or _came_from.has(neighbor_id):
						continue
					_came_from[neighbor_id] = current_id
					_g_score[neighbor_id] = float(_g_score.get(current_id, 0.0)) + _distance_between(current_id, neighbor_id)
					_push_frontier(neighbor_id)

		_visual_tick += 1
		if _visual_tick % visual_update_interval == 0:
			_refresh_debug_visuals()


func _push_frontier(node_id: int) -> void:
	_search_frontier.append(node_id)
	_frontier_membership[node_id] = true
	_discovered_vertex_count += 1


func _pop_frontier_node() -> int:
	if _search_frontier.is_empty():
		return -1

	var picked_id := -1
	match search_algorithm:
		SearchAlgorithm.ASTAR, SearchAlgorithm.UCS, SearchAlgorithm.GREEDY:
			var best_idx := -1
			var best_score := INF
			for i in range(_search_frontier.size()):
				var node_id := int(_search_frontier[i])
				var score := float(_f_score.get(node_id, INF))
				if score < best_score:
					best_score = score
					best_idx = i
			if best_idx != -1:
				picked_id = int(_search_frontier[best_idx])
				_search_frontier.remove_at(best_idx)
		SearchAlgorithm.BFS:
			picked_id = int(_search_frontier.pop_front())
		SearchAlgorithm.DFS, SearchAlgorithm.IDDFS:
			picked_id = int(_search_frontier.pop_back())

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
	_update_debug_overlay()


func _refresh_all_nodes_visual() -> void:
	var all_ids: Array[int] = []
	for node_id_variant in _graph_positions.keys():
		all_ids.append(int(node_id_variant))
	all_ids.sort()
	_apply_marker_instances(all_nodes_markers.multimesh, all_ids, Vector3(0.24, 0.24, 0.24))


func _refresh_frontier_markers() -> void:
	var ids: Array = _search_frontier.duplicate()
	ids.sort()
	_apply_marker_instances(frontier_markers.multimesh, ids, MARKER_SCALE)


func _refresh_closed_markers() -> void:
	_apply_marker_instances(closed_markers.multimesh, _search_closed_order, MARKER_SCALE)


func _refresh_path_visuals() -> void:
	_apply_marker_instances(path_markers.multimesh, _path_node_ids, PATH_MARKER_SCALE)
	path_lines.mesh = _build_line_mesh(_path_points, Color(0.2, 0.85, 1.0, 1.0))


func _refresh_traveled_visual() -> void:
	traveled_lines.mesh = _build_line_mesh(_travel_points, Color(0.15, 1.0, 0.35, 1.0))


func _refresh_search_lines() -> void:
	var points: Array[Vector3] = []
	for node_id in _search_frontier:
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


func _set_search_algorithm(next_algorithm: int) -> void:
	if search_algorithm == next_algorithm:
		return
	search_algorithm = next_algorithm
	print("PathBot: switched algorithm to %s" % _get_algorithm_name())
	_begin_search()


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
		SearchAlgorithm.IDDFS:
			return "IDDFS"
	return "Unknown"


func _get_algorithm_slug() -> String:
	match search_algorithm:
		SearchAlgorithm.ASTAR:
			return "astar"
		SearchAlgorithm.BFS:
			return "bfs"
		SearchAlgorithm.DFS:
			return "dfs"
		SearchAlgorithm.UCS:
			return "ucs"
		SearchAlgorithm.GREEDY:
			return "greedy"
		SearchAlgorithm.IDDFS:
			return "iddfs"
	return "astar"


func _get_search_status() -> String:
	if not _search_started:
		return "idle"
	if _remote_request_in_flight:
		return "waiting remote"
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
		"Backend: %s" % ("Remote Python API" if _using_remote_path or _remote_request_in_flight else "Local GDScript"),
		"Status: %s" % _get_search_status(),
		"Start -> Goal: %d -> %d" % [_search_start_id, _search_goal_id],
		"Visited vertices: %d" % _visited_vertex_count,
		"Visited edges: %d" % _visited_edge_count,
		"Discovered vertices: %d" % _discovered_vertex_count,
		"Search speed: %d steps/tick" % search_steps_per_tick,
		"Frontier size: %d" % _search_frontier.size(),
		"Closed size: %d" % _search_closed_order.size(),
		"Path nodes: %d" % _path_node_ids.size(),
		"Path cost: %.2f" % _path_total_cost,
		"Waypoint: %d / %d" % [current_waypoint_display, _path_points.size()],
		"Hotkeys: 1=A*  2=BFS  3=DFS  4=UCS  5=Greedy  6=IDDFS",
		"         P=benchmark all  7/8=speed  F3=overlay  H=highlight",
	]
	if _benchmark_summary_text != "":
		lines.append("")
		lines.append(_benchmark_summary_text)
	_debug_label.text = "\n".join(lines)


func _format_benchmark_summary(payload: Dictionary) -> String:
	var header := "Benchmark Summary"
	var meta := "Graph: %d nodes, %d directed edges | Start->Goal: %d -> %d" % [
		int(payload.get("graph_node_count", 0)),
		int(payload.get("graph_edge_count", 0)),
		int(payload.get("start_id", -1)),
		int(payload.get("goal_id", -1)),
	]
	var lines := [
		header,
		meta,
		"Algo     Found  Time(ms)  PathNodes  Cost     VisitedN  VisitedE  Discovered",
	]
	for row_variant in payload.get("rows", []):
		var row: Dictionary = row_variant
		var algo := _pad_right(str(row.get("algorithm", "")), 8)
		var found := _pad_right("yes" if bool(row.get("found", false)) else "no", 6)
		var elapsed := _pad_left("%.2f" % float(row.get("elapsed_ms", 0.0)), 8)
		var path_nodes := _pad_left(str(int(row.get("path_nodes", 0))), 10)
		var cost := _pad_left("%.2f" % float(row.get("path_cost", 0.0)), 8)
		var visited_vertices := _pad_left(str(int(row.get("visited_vertices", 0))), 9)
		var visited_edges := _pad_left(str(int(row.get("visited_edges", 0))), 9)
		var discovered := _pad_left(str(int(row.get("discovered_vertices", 0))), 11)
		lines.append("%s %s %s %s %s %s %s %s" % [
			algo,
			found,
			elapsed,
			path_nodes,
			cost,
			visited_vertices,
			visited_edges,
			discovered,
		])
	return "\n".join(lines)


func _pad_right(value: String, width: int) -> String:
	if value.length() >= width:
		return value.substr(0, width)
	return value + " ".repeat(width - value.length())


func _pad_left(value: String, width: int) -> String:
	if value.length() >= width:
		return value.substr(0, width)
	return " ".repeat(width - value.length()) + value


func _adjust_search_speed(delta_steps: int) -> void:
	var previous_steps := search_steps_per_tick
	search_steps_per_tick = clamp(search_steps_per_tick + delta_steps, MIN_SEARCH_STEPS_PER_TICK, MAX_SEARCH_STEPS_PER_TICK)
	if previous_steps != search_steps_per_tick:
		print("PathBot: search speed = %d steps/tick" % search_steps_per_tick)
		_update_debug_overlay()
