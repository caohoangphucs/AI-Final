extends Node3D

@onready var campus: Node = $Campus
@onready var spawn: Marker3D = $Spawn
@onready var sun: DirectionalLight3D = $Sun
@onready var world_environment: WorldEnvironment = $WorldEnvironment

const NON_COLLIDABLE_PREFIXES := [
	"StairEntry_",
	"BridgeEntry_",
	"Cut_",
]

const NON_COLLIDABLE_NAME_PARTS := [
	"_Stair_Wall_",
	"A1_Tower_Canopy_Col",
]


func _ready() -> void:
	_configure_lighting()
	_build_collisions(campus)
	_place_player()
	print("Main: press X to toggle campus model visibility")


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo and event.keycode == KEY_X:
		campus.visible = not campus.visible
		print("Main: campus model %s" % ("visible" if campus.visible else "hidden"))


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
