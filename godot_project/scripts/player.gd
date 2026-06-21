extends CharacterBody3D

const WALK_SPEED := 8.0
const SPRINT_SPEED := 14.0
const JUMP_VELOCITY := 6.5
const GRAVITY := 18.0
const MOUSE_SENS := 0.0025
const FLY_SPEED := 14.0
const FLY_SPRINT_SPEED := 24.0
const FLY_ACCEL := 18.0

@onready var pivot: Node3D = $Pivot
@onready var camera: Camera3D = $Pivot/Camera3D

var _pitch := 0.0
var _fly_mode := true
var _capture_resume_at_msec := 0


func _ready() -> void:
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	print("Player: fly mode ON | F toggle fly | X toggle campus model | click game view to capture mouse")


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		rotate_y(-event.relative.x * MOUSE_SENS)
		_pitch = clamp(_pitch - event.relative.y * MOUSE_SENS, deg_to_rad(-89.0), deg_to_rad(89.0))
		pivot.rotation.x = _pitch

	if event.is_action_pressed("ui_cancel"):
		Input.mouse_mode = Input.MOUSE_MODE_VISIBLE

	if event is InputEventMouseButton and event.pressed and event.button_index == MOUSE_BUTTON_LEFT and Input.mouse_mode != Input.MOUSE_MODE_CAPTURED:
		if Time.get_ticks_msec() < _capture_resume_at_msec:
			return
		if get_viewport().gui_get_hovered_control() != null:
			return
		Input.mouse_mode = Input.MOUSE_MODE_CAPTURED

	if event is InputEventKey and event.pressed and not event.echo and event.keycode == KEY_F:
		_fly_mode = not _fly_mode
		velocity = Vector3.ZERO
		print("Player: fly mode %s" % ("ON" if _fly_mode else "OFF"))


func suspend_mouse_capture(duration_sec := 0.25) -> void:
	_capture_resume_at_msec = Time.get_ticks_msec() + int(duration_sec * 1000.0)


func _physics_process(delta: float) -> void:
	var input_vec := Vector2.ZERO
	input_vec.x = float(Input.is_physical_key_pressed(KEY_D)) - float(Input.is_physical_key_pressed(KEY_A))
	input_vec.y = float(Input.is_physical_key_pressed(KEY_S)) - float(Input.is_physical_key_pressed(KEY_W))
	input_vec = input_vec.normalized()
	var speed := SPRINT_SPEED if Input.is_physical_key_pressed(KEY_SHIFT) else WALK_SPEED

	if _fly_mode:
		_process_fly_movement(delta, input_vec)
		return

	if not is_on_floor():
		velocity.y -= GRAVITY * delta

	if Input.is_physical_key_pressed(KEY_SPACE) and is_on_floor():
		velocity.y = JUMP_VELOCITY

	var move_dir := (transform.basis * Vector3(input_vec.x, 0.0, input_vec.y)).normalized()

	if move_dir != Vector3.ZERO:
		velocity.x = move_toward(velocity.x, move_dir.x * speed, speed)
		velocity.z = move_toward(velocity.z, move_dir.z * speed, speed)
	else:
		velocity.x = move_toward(velocity.x, 0.0, speed)
		velocity.z = move_toward(velocity.z, 0.0, speed)

	move_and_slide()


func _process_fly_movement(delta: float, input_vec: Vector2) -> void:
	var vertical_input := float(Input.is_physical_key_pressed(KEY_SPACE)) - float(Input.is_physical_key_pressed(KEY_CTRL))
	var move_dir := Vector3.ZERO
	move_dir += transform.basis.z * input_vec.y
	move_dir += transform.basis.x * input_vec.x
	move_dir += Vector3.UP * vertical_input
	move_dir = move_dir.normalized()

	var speed := FLY_SPRINT_SPEED if Input.is_physical_key_pressed(KEY_SHIFT) else FLY_SPEED
	if move_dir != Vector3.ZERO:
		velocity = velocity.move_toward(move_dir * speed, FLY_ACCEL * delta)
	else:
		velocity = velocity.move_toward(Vector3.ZERO, FLY_ACCEL * delta)

	global_position += velocity * delta
