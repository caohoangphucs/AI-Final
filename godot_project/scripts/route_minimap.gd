extends Control

const WORLD_MIN := Vector2(-118.0, -56.0)
const WORLD_MAX := Vector2(206.0, 93.0)
const BG_COLOR := Color(0.05, 0.08, 0.12, 1.0)
const GRID_COLOR := Color(0.16, 0.24, 0.34, 0.45)
const PATH_LINE_COLOR := Color(0.28, 0.76, 1.0, 0.55)
const PATH_NODE_COLOR := Color(0.39, 0.84, 1.0, 1.0)
const BOT_GLOW_COLOR := Color(1.0, 0.92, 0.25, 0.28)
const BOT_COLOR := Color(1.0, 0.94, 0.2, 1.0)

var _snapshot: Dictionary = {}


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE


func set_snapshot(snapshot: Dictionary) -> void:
	_snapshot = snapshot
	queue_redraw()


func _draw() -> void:
	draw_rect(Rect2(Vector2.ZERO, size), BG_COLOR, true)
	_draw_grid()

	var path_points: Array = _snapshot.get("path_points", [])
	if path_points.size() >= 2:
		var polyline := PackedVector2Array()
		for point_variant in path_points:
			polyline.append(_world_to_canvas(point_variant))
		draw_polyline(polyline, PATH_LINE_COLOR, 2.0, true)

	for point_variant in path_points:
		draw_circle(_world_to_canvas(point_variant), 3.2, PATH_NODE_COLOR)

	var bot_position: Vector3 = _snapshot.get("bot_position", Vector3.ZERO)
	var bot_point := _world_to_canvas(bot_position)
	draw_circle(bot_point, 14.0, BOT_GLOW_COLOR)
	draw_circle(bot_point, 6.0, BOT_COLOR)
	draw_arc(bot_point, 10.0, 0.0, TAU, 32, Color(1.0, 1.0, 1.0, 0.9), 2.0)


func _draw_grid() -> void:
	for t in [0.25, 0.5, 0.75]:
		var x: float = size.x * t
		var y: float = size.y * t
		draw_line(Vector2(x, 0.0), Vector2(x, size.y), GRID_COLOR, 1.0)
		draw_line(Vector2(0.0, y), Vector2(size.x, y), GRID_COLOR, 1.0)


func _world_to_canvas(point: Vector3) -> Vector2:
	var p := Vector2(point.x, point.z)
	var normalized := (p - WORLD_MIN) / (WORLD_MAX - WORLD_MIN)
	return Vector2(normalized.x * size.x, (1.0 - normalized.y) * size.y)
