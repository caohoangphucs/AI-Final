# Tài liệu hoạt động toàn bộ project

## 1. Mục tiêu project

Project mô phỏng tìm đường trong không gian 3D của khuôn viên trường học. Hệ thống gồm 3 phần:

- `godot_project/`: ứng dụng mô phỏng 3D chạy trong Godot.
- `data/`: bộ script Blender/Python để dựng mô hình, sinh và hậu xử lý navigation graph.
- `python_nav_service/`: service FastAPI cài các thuật toán tìm đường bằng Python để test hoặc benchmark độc lập.

Lưu ý quan trọng: ở trạng thái code hiện tại, `Godot` đang chạy pathfinding trực tiếp bằng `GDScript` trong `path_bot.gd`, không gọi HTTP sang `python_nav_service`.

## 2. Luồng hoạt động tổng thể

### 2.1 Luồng dữ liệu

1. Dựng hoặc mở mô hình kiến trúc trong Blender từ các file ở `data/`.
2. Chạy `data/generate_navigation_graph.py` để sinh `navigation_graph.json`.
3. Chạy các bước hậu xử lý trong `data/` để vá, nối và kiểm tra graph.
4. Copy hoặc dùng trực tiếp graph tại `godot_project/assets/navigation_graph.json`.
5. Godot nạp graph, cho người dùng chọn thuật toán, chọn điểm đầu/cuối, sau đó `PathBot` tìm đường và hiển thị trực quan.

### 2.2 Luồng chạy Godot

1. `Main.tscn` nạp scene campus và các node điều khiển.
2. `main.gd`:
   - cấu hình ánh sáng,
   - sinh collision từ mesh,
   - đặt vị trí player,
   - tạo HUD,
   - mở menu chọn thuật toán.
3. `path_bot.gd`:
   - nạp `navigation_graph.json`,
   - snap marker `start` và `goal` vào node gần nhất,
   - chờ người dùng chọn thuật toán,
   - chạy A*, BFS, DFS, UCS, Greedy hoặc Hill Climbing,
   - vẽ frontier, closed set, đường đi, overlay thống kê.
4. `player.gd` điều khiển camera/player để bay hoặc đi bộ quan sát scene.

## 3. Cấu trúc thư mục chính

- `README.md`: ghi chú tổng quan repo.
- `godot_project/README.md`: hướng dẫn chạy phần Godot.
- `godot_project/scenes/Main.tscn`: scene chính.
- `godot_project/scripts/main.gd`: bootstrap scene, HUD, menu, overlay kết quả.
- `godot_project/scripts/player.gd`: điều khiển người chơi/camera.
- `godot_project/scripts/path_bot.gd`: lõi pathfinding và trực quan hóa.
- `godot_project/assets/navigation_graph.json`: graph điều hướng cho Godot.
- `data/navigation_graph.json`: graph nguồn/đầu ra của pipeline dữ liệu.
- `python_nav_service/graph_search.py`: cài đặt thuật toán pathfinding bằng Python.
- `python_nav_service/server.py`: API FastAPI cho solve path và benchmark.

## 4. Chức năng các module runtime chính

### 4.1 `godot_project/scripts/main.gd`

Vai trò: điều phối scene chính, tạo menu chọn thuật toán, nhận thao tác chọn điểm bắt đầu/kết thúc, hiển thị kết quả.

Các hàm:

- `_ready()`: khởi tạo scene, ánh sáng, collision, player, signal từ `PathBot`, HUD và menu chính.
- `_setup_hud()`: tạo lớp HUD ở cuối màn hình để hướng dẫn thao tác.
- `_unhandled_input(event)`: xử lý click chọn start/goal bằng raycast và phím `X`, `ESC`.
- `_get_camera_center_raycast()`: bắn tia từ tâm camera để lấy vị trí click trong không gian 3D.
- `_place_player()`: đặt player tại `Spawn`.
- `_build_collisions(node)`: duyệt đệ quy toàn cây node và sinh collision cho mesh hợp lệ.
- `_should_create_collision(node)`: lọc các mesh không nên tạo va chạm như cầu thang phụ trợ, cutter, canopy.
- `_configure_lighting()`: chỉnh môi trường, ambient light và mặt trời.
- `_show_algorithm_menu()`: dựng menu chính để chọn thuật toán hoặc vào chế độ chọn điểm.
- `_on_set_start_from_menu()`: đóng menu và chuyển sang chế độ click chọn điểm bắt đầu.
- `_on_set_goal_from_menu()`: đóng menu và chuyển sang chế độ click chọn điểm kết thúc.
- `_on_set_point_from_menu()`: đóng menu và cho phép click trái chọn start, click phải chọn goal.
- `_on_algorithm_selected(algorithm_id)`: gọi `PathBot` chạy một thuật toán hoặc chạy toàn bộ để so sánh.
- `_update_hud_text()`: đổi nội dung HUD theo trạng thái hiện tại.
- `_make_text_label(...)`: helper tạo `Label` dùng chung.
- `_make_algorithm_header_row()`: tạo dòng tiêu đề cho bảng thuật toán trong menu.
- `_make_algorithm_row(row_data)`: tạo một dòng thuật toán kèm nút `Chạy`.
- `_make_column_label(...)`: helper tạo label theo cột.
- `_on_comparison_ready(rows)`: nhận signal khi `PathBot` chạy xong chế độ so sánh.
- `_on_search_result_ready(result)`: nhận signal khi `PathBot` chạy xong một thuật toán.
- `_show_comparison_overlay(rows)`: hiển thị popup so sánh nhiều thuật toán.
- `_make_comparison_chart(rows)`: tạo biểu đồ cột thời gian chạy.
- `_find_best_comparison_row(rows)`: tìm thuật toán nhanh nhất trong bảng so sánh.
- `_make_comparison_summary_card(best_row)`: tạo thẻ tóm tắt thuật toán tốt nhất.
- `_make_comparison_header_row()`: tạo header bảng so sánh.
- `_make_comparison_row(row_data, best_row)`: tạo từng dòng dữ liệu so sánh.
- `_make_metric_label(...)`: helper tạo label cho các cột thống kê.
- `_make_result_stat_row(label_text, value_text)`: tạo một dòng thông tin trong popup kết quả.
- `_close_comparison_overlay()`: đóng overlay kết quả/so sánh.
- `_show_search_result_overlay(result)`: hiển thị popup kết quả cho một lần chạy thuật toán.
- `_rerun_all_algorithms()`: đóng overlay và yêu cầu `PathBot` chạy lại toàn bộ thuật toán.

### 4.2 `godot_project/scripts/player.gd`

Vai trò: điều khiển góc nhìn first-person, hỗ trợ bay và đi bộ.

Các hàm:

- `_ready()`: đặt chuột ở chế độ hiển thị và in hướng dẫn điều khiển.
- `_unhandled_input(event)`: xử lý xoay camera theo chuột, bắt/nhả chuột và bật/tắt fly mode.
- `_physics_process(delta)`: xử lý di chuyển khi đi bộ, nhảy, gravity và sprint.
- `_process_fly_movement(delta, input_vec)`: xử lý chuyển động tự do theo 3 trục khi bật fly mode.

### 4.3 `godot_project/scripts/path_bot.gd`

Vai trò: nạp graph, chạy thuật toán tìm đường, cập nhật thống kê và trực quan hóa quá trình duyệt.

#### Nhóm khởi tạo

- `_ready()`: khởi tạo toàn bộ `PathBot`, nạp graph, mesh debug, overlay, marker start/goal.
- `_init_goal_marker()`: snap goal marker về node gần nhất lúc bắt đầu.
- `_setup_debug_meshes()`: tạo `MultiMesh` và vật liệu cho node, frontier, closed, path.
- `_setup_debug_overlay()`: dựng panel debug nổi trên màn hình.
- `_update_debug_overlay_layout()`: đặt vị trí panel debug theo viewport.
- `_create_multimesh(mesh, capacity)`: tạo `MultiMesh` với sức chứa cố định.
- `_load_navigation_graph()`: đọc file JSON và nạp node/neighbor vào dictionary nội bộ.
- `_snap_to_start()`: snap start marker, đặt `PathBot` tại node start đầu tiên.
- `_update_highlight_positions()`: cập nhật trụ highlight ở start và goal.

#### Nhóm nhập liệu và điều khiển

- `_unhandled_input(event)`: nhận hotkey đổi thuật toán, bật/tắt debug, highlight và chỉnh tốc độ.
- `_physics_process(delta)`: vòng lặp chính, quyết định đang chờ chọn thuật toán, đang duyệt hay đang đi theo đường.
- `set_custom_start(pos)`: đổi điểm bắt đầu theo vị trí người dùng click.
- `set_custom_goal(pos)`: đổi điểm kết thúc theo vị trí người dùng click.
- `_set_search_algorithm(next_algorithm)`: đổi thuật toán hiện hành và bắt đầu tìm lại.
- `start_search_with_algorithm(next_algorithm)`: wrapper public để `main.gd` gọi.
- `return_to_menu_state()`: reset bot về trạng thái chờ ở menu.
- `start_search_with_all()`: chạy lần lượt toàn bộ thuật toán để benchmark trực tiếp trong Godot.
- `get_algorithm_menu_rows()`: trả về dữ liệu hiển thị menu thuật toán.
- `_adjust_search_speed(delta_steps)`: tăng/giảm số bước duyệt mỗi tick.

#### Nhóm quản lý tiến trình tìm kiếm

- `_begin_search()`: xác định node start/goal hiện tại, reset trạng thái và khởi động lần tìm mới.
- `_reset_search_state()`: xóa toàn bộ frontier, closed set, path, thống kê và timer.
- `_start_local_search()`: khởi tạo frontier ban đầu hoặc chuyển sang Hill Climbing.
- `_snap_marker_to_nearest_node(marker, label)`: đưa marker về node gần nhất.
- `_step_search()`: thực hiện một lô bước tìm kiếm cho A*, BFS, DFS, UCS, Greedy.
- `_run_hill_climbing_search()`: cài đặt Hill Climbing có restart để giảm nguy cơ kẹt local optimum.
- `_push_frontier(node_id)`: thêm node vào frontier.
- `_pop_frontier_node()`: lấy node kế tiếp ra khỏi frontier theo chiến lược thuật toán.
- `_finalize_path()`: đánh dấu thành công, dựng path, tính cost và phát signal kết quả.
- `_reconstruct_path(goal_id)`: dựng lại đường đi từ `came_from`.
- `_follow_path(delta)`: cho `PathBot` di chuyển theo các waypoint trên đường tìm được.
- `_record_travel_point(point)`: lưu lại quỹ đạo bot đã đi để vẽ.
- `_find_nearest_node_id(world_pos)`: tìm node graph gần một vị trí 3D nhất.

#### Nhóm heuristic và cost

- `_heuristic(a, b)`: heuristic khoảng cách Euclid cho Greedy/A*.
- `_frontier_priority(node_id, g_cost)`: tính khóa ưu tiên tùy thuật toán.
- `_distance_between(a, b)`: tính cost cạnh gồm độ dài cộng phạt leo cao.

#### Nhóm trực quan hóa

- `_refresh_debug_visuals()`: cập nhật toàn bộ marker, line và overlay.
- `_refresh_all_nodes_visual()`: vẽ tất cả node của graph.
- `_refresh_frontier_markers()`: vẽ frontier hiện tại.
- `_refresh_closed_markers()`: vẽ tập closed.
- `_refresh_path_visuals()`: vẽ node đường đi và line path.
- `_refresh_traveled_visual()`: vẽ quỹ đạo bot đã di chuyển.
- `_refresh_search_lines()`: vẽ các đoạn từ cha tới node đang được khám phá.
- `_apply_marker_instances(multimesh, node_ids, marker_scale)`: đặt transform cho các marker theo danh sách node.
- `_build_line_mesh(points, color)`: tạo line mesh từ danh sách điểm.
- `_make_unshaded_material(color, transparent)`: tạo vật liệu không chịu shading để debug rõ hơn.
- `_apply_algorithm_visual_theme(algorithm_id)`: đổi màu bot, marker và path theo thuật toán.

#### Nhóm cấu trúc dữ liệu hỗ trợ

- `_uses_priority_frontier()`: cho biết frontier hiện tại có dùng heap ưu tiên không.
- `_heap_push(priority, node_id)`: chèn phần tử vào min-heap tự cài.
- `_heap_pop()`: lấy phần tử ưu tiên nhỏ nhất khỏi heap.
- `_frontier_node_ids()`: lấy danh sách node đang có trong frontier.
- `_sample_node_ids(node_ids, max_count)`: lấy mẫu node để tránh vẽ quá nhiều marker.

#### Nhóm debug, báo cáo và so sánh

- `_request_debug_overlay_refresh()`: đánh dấu overlay cần render lại.
- `_refresh_debug_overlay_if_needed(delta, force)`: chỉ refresh overlay theo chu kỳ để tiết kiệm chi phí.
- `_get_algorithm_name()`: đổi `enum` thuật toán sang tên hiển thị.
- `_get_algorithm_color(algorithm_id)`: trả màu đại diện cho từng thuật toán.
- `_start_next_algorithm_in_queue()`: chạy tiếp thuật toán kế tiếp trong chế độ `run all`.
- `_on_search_complete()`: gom kết quả của một thuật toán vào bảng so sánh.
- `_emit_single_search_result()`: phát signal kết quả cho một lần chạy đơn.
- `_get_search_status()`: trả trạng thái text của bot.
- `_update_debug_overlay()`: render nội dung thống kê trong panel debug.

## 5. Thuật toán đang hỗ trợ trong Godot

- `A*`: cân bằng giữa chi phí đã đi và heuristic đến đích.
- `BFS`: duyệt theo lớp, tốt khi ưu tiên số cạnh ít.
- `DFS`: đi sâu theo nhánh, dễ minh họa nhưng không tối ưu.
- `UCS`: mở rộng node có chi phí đường đi nhỏ nhất.
- `Greedy`: chỉ nhìn heuristic, thường nhanh nhưng có thể lệch.
- `Hill Climbing`: chọn hàng xóm tốt nhất, có restart để giảm kẹt cục bộ.

Cost cạnh trong Godot:

- `edge_length * EDGE_LENGTH_WEIGHT`
- `+ ascent * ASCENT_COST_WEIGHT`

Nghĩa là cạnh càng dài và leo cao càng nhiều thì càng đắt.

## 6. Python navigation service

### 6.1 `python_nav_service/graph_search.py`

Vai trò: cài đặt thuật toán tìm đường và chuẩn hóa kết quả trả về.

Class/chức năng:

- `GraphSearchResult`: dataclass chứa kết quả chuẩn của một lần solve path.
- `NavigationGraph`: class nạp graph và chạy thuật toán trên graph đó.

Hàm/phương thức chính của `NavigationGraph`:

- `__init__(graph_path)`: nạp JSON graph thành `nodes`, `positions`, `neighbors`.
- `ensure_node(node_id)`: kiểm tra node có tồn tại không.
- `heuristic(a, b)`: heuristic Euclid.
- `traversal_cost(a, b)`: cost cạnh có cộng phạt độ cao.
- `solve(start_id, goal_id, algorithm)`: router chọn thuật toán phù hợp.
- `_solve_uninformed(...)`: cài đặt BFS/DFS.
- `_solve_priority(...)`: cài đặt UCS/Greedy/A* dùng heapq.
- `_priority_for(...)`: tính priority tương ứng từng thuật toán.
- `_solve_iddfs(...)`: cài đặt Iterative Deepening DFS.
- `_depth_limited_dfs(...)`: DFS giới hạn độ sâu cho từng vòng IDDFS.
- `_build_found_result(...)`: dựng object kết quả khi tìm thấy đường.
- `_build_not_found_result(...)`: dựng object kết quả khi không tìm thấy đường.
- `_reconstruct_path(goal_id, came_from)`: tái tạo chuỗi node của đường đi.

### 6.2 `python_nav_service/server.py`

Vai trò: cung cấp API HTTP để truy vấn graph và solve path.

Model:

- `SolvePathRequest`: request cho một lần tìm đường.
- `BenchmarkPathRequest`: request chạy benchmark nhiều thuật toán.
- `NodeSummary`: response tóm tắt một node.
- `SolvePathResponse`: response đầy đủ của `/solve-path`.
- `BenchmarkRow`: một dòng benchmark.
- `BenchmarkPathResponse`: response tổng hợp của `/benchmark-path`.

API:

- `health()`: trả trạng thái service, đường dẫn graph và danh sách thuật toán.
- `get_node(node_id)`: trả thông tin một node.
- `solve_path(request)`: chạy một thuật toán pathfinding.
- `benchmark_path(request)`: chạy nhiều thuật toán và so sánh thời gian/chỉ số.

## 7. Các module thuật toán demo nâng cao

Các file trong `python_nav_service/complex_search/` không tham gia runtime Godot chính, chủ yếu dùng minh họa học thuật.

### `and_or_queens.py`

- `QueenState`: biểu diễn trạng thái đặt quân hậu.
- `and_or_search_queens(n)`: giải bài toán n-queens bằng AND-OR search.
- `render_state(state, n)`: dựng bàn cờ dạng text.
- `main()`: chạy demo từ command line.

### `sensorless_search.py`

- `GridWorld`: mô tả môi trường lưới cho sensorless search.
- `sensorless_bfs(world, goal)`: BFS trên belief state.
- `belief_update_with_observation(...)`: cập nhật belief state khi có quan sát.
- `main()`: chạy demo.

### `online_search.py`

- `OnlineGraph`: mô hình graph nhỏ cho online search.
- `OnlineDFSAgent`: agent DFS ra quyết định từng bước.
- `run_online_dfs(graph, start)`: chạy agent trên graph.
- `main()`: chạy demo.

## 8. Pipeline dữ liệu trong `data/`

### 8.1 Nhóm dựng mô hình kiến trúc

#### `data/build_architectural.py`

Vai trò: dựng campus kiến trúc chi tiết trong Blender.

Hàm chính:

- `make_material(...)`: tạo material Blender.
- `assign_mat(obj, mat)`: gán material cho object.
- `add_box(...)`: tạo khối hộp cơ sở.
- `get_block_profile(prefix)`: trả cấu hình hành lang/phòng theo loại khối nhà.
- `build_staircase(...)`: dựng cầu thang trong nhà.
- `add_internal_stair_cutters(...)`: tạo cutter mở lối trong lõi thang.
- `build_detailed_block(...)`: dựng chi tiết một khối nhà.
- `add_cutter(...)`: tạo hộp cắt boolean.
- `add_rotated_cutter(...)`: tạo cutter có xoay.
- `add_rotated_box(...)`: tạo khối hộp xoay.
- `build_skybridge(...)`: dựng cầu nối giữa hai khối.
- `build_path_segment(...)`: dựng một đoạn lối đi.
- `build_polyline_path(...)`: dựng lối đi theo polyline.
- `build_terrain_terrace(...)`: dựng nền/sân theo bậc.
- `build_campus_expansion()`: dựng các khối mở rộng.
- `build_field_fence(...)`: dựng hàng rào sân.
- `relocate_field_clear_of_buildings(...)`: dời sân tránh đè vào công trình.
- `build_outdoor_stair(...)`: dựng cầu thang ngoài trời.
- `build_a1_tower(...)`: dựng tháp A1.
- `world_bounds(obj)`: lấy bounding box thế giới.
- `bounds_overlap(a, b, padding)`: kiểm tra giao nhau giữa hai bounding box.

#### `data/detail_khu_a.py`

Vai trò: thêm chi tiết riêng cho khu A.

Hàm chính:

- `new_mesh_obj(name, collection)`: tạo object mesh mới.
- `make_material(...)`: tạo material.
- `assign_mat(obj, mat)`: gán material.
- `box_bmesh(...)`: tạo hình hộp bằng `bmesh`.
- `add_box(...)`: tạo object box.
- `apply_existing_materials()`: áp vật liệu sẵn có cho nhóm object.
- `add_stair_set(...)`: dựng một cụm cầu thang.
- `add_windows_on_face(...)`: thêm dãy cửa sổ cho một mặt tường.

#### `data/export_godot_scene.py`

Vai trò: xuất scene Blender sang asset Godot.

- `ensure_dir(path)`: đảm bảo thư mục đích tồn tại.
- `is_exportable(obj)`: kiểm tra object có nên export không.
- `main()`: chạy quy trình export.

### 8.2 Nhóm sinh graph điều hướng

#### `data/generate_navigation_graph.py`

Vai trò: script cốt lõi sinh `navigation_graph.json` từ mô hình kiến trúc.

Thành phần chính:

- `get_block_profile(prefix)`: lấy profile sinh node cho từng loại khối nhà.
- `ensure_collection(name)`: tạo collection riêng cho graph trong Blender.
- `ensure_red_material()`: tạo material đỏ cho overlay graph.
- `assign_material(obj, mat)`: gán material cho object graph.
- `add_box(...)`: thêm box debug/overlay.
- `mathutils_matrix_scale(...)`: helper scale matrix.
- `get_bounds(obj)`: lấy bounds của object.
- `GraphBuilder`: class quản lý node, edge, merge node gần nhau và export graph.
- `add_corridor_graph(...)`: sinh node hành lang.
- `add_internal_stair_graph(...)`: sinh node cho cầu thang trong nhà.
- `add_a1_front_stair_graph(...)`: sinh node khu cầu thang phía trước A1.
- `add_outdoor_stair_graph(...)`: sinh node cầu thang ngoài trời.
- `add_skybridge_graph(...)`: sinh node cầu nối.
- `add_a1_internal_graph(graph)`: sinh graph riêng cho nội bộ A1.
- `subdivide_polyline(points, max_segment_length)`: chia nhỏ polyline để tạo nhiều node trung gian.
- `add_ground_paths(graph)`: thêm node cho đường đi mặt đất.
- `ccw(a, b, c)`: helper hình học xác định chiều quay.
- `segments_intersect(a, b, c, d)`: kiểm tra giao cắt đoạn thẳng.
- `point_in_rect(p, rect)`: kiểm tra điểm nằm trong hình chữ nhật.
- `segment_intersects_rect(p1, p2, rect)`: kiểm tra đoạn thẳng cắt obstacle hình chữ nhật.
- `segment_blocked_by_obstacles(...)`: kiểm tra đoạn nối bị cản bởi chướng ngại.
- `connect_access_points(graph, block_bounds)`: nối các điểm truy cập với graph xung quanh.
- `compute_connected_components(graph)`: tính số thành phần liên thông.
- `build_obstacle_rects(block_bounds)`: sinh danh sách obstacle dạng rect.
- `connect_ground_path_network(graph, block_bounds)`: nối mạng đường đất.
- `connect_ground_path_junctions(graph, block_bounds)`: nối các nút giao của đường đất.
- `compute_flat_ground_components(graph)`: tính component trên mặt đất phẳng.
- `stitch_flat_ground_components(graph)`: nối các component mặt đất gần nhau.
- `is_building_access_anchor(node)`: nhận diện node mỏ neo truy cập công trình.
- `building_access_z_tolerance(node_a, node_b)`: xác định ngưỡng cao độ cho nối access.
- `stitch_building_access_components(graph, block_bounds)`: nối graph công trình với graph đất.
- `is_connector_kind(node)`: nhận diện node loại connector.
- `can_stitch_pair(node_a, node_b, obstacles)`: kiểm tra hai node có thể nối không.
- `stitch_graph_components(graph, block_bounds)`: nối component rời tổng quát.
- `export_graph_text(graph)`: xuất file adjacency text.
- `build_visual_overlay(graph)`: tạo overlay trực quan graph trong Blender.
- `main()`: chạy toàn bộ quy trình sinh graph.

### 8.3 Nhóm vá và nối graph sau khi sinh

#### `data/apply_navigation_pipeline.py`

- `main()`: chạy tuần tự các bước vá và stitch graph.

#### `data/patch_ground_paths.py`

- `node_key(position)`: tạo khóa node theo vị trí.
- `subdivide_polyline(points)`: chia nhỏ polyline đường đất.
- `load_graph()`: đọc graph JSON.
- `save_graph(data)`: ghi graph JSON.
- `patch_graph(data)`: chèn/sửa node và cạnh cho đường đất.
- `main()`: chạy script.

#### `data/stitch_path_junctions.py`

- `load_graph()`: đọc graph.
- `write_outputs(data)`: ghi JSON và text.
- `add_edge(...)`: thêm cạnh nếu chưa tồn tại.
- `stitch_path_junctions(data)`: nối các nút giao đường đi gần nhau.
- `main()`: chạy script.

#### `data/stitch_flat_ground_paths.py`

- `load_graph()`: đọc graph.
- `write_outputs(data)`: ghi graph sau xử lý.
- `flat_ground_components(data)`: tìm component trên mặt đất.
- `add_edge(...)`: thêm cạnh nối.
- `stitch_flat_ground_components(data)`: nối các component mặt đất.
- `main()`: chạy script.

#### `data/stitch_building_access_paths.py`

- `load_graph()`: đọc graph.
- `write_outputs(data)`: ghi graph.
- `add_edge(...)`: thêm cạnh giữa hai node.
- `compute_components(data)`: tính component hiện tại.
- `is_building_access_anchor(node)`: nhận diện node access của tòa nhà.
- `building_access_z_tolerance(node_a, node_b)`: lấy ngưỡng chênh cao để nối.
- `stitch_building_access_components(data)`: nối graph tòa nhà với graph ngoài trời.
- `main()`: chạy script.

#### `data/stitch_navigation_graph.py`

- `load_graph()`: đọc graph tổng.
- `connected_components(nodes_by_id)`: tìm các component liên thông.
- `build_spatial_buckets(nodes_by_id, cell_size)`: chia node vào bucket không gian để tìm láng giềng nhanh hơn.
- `is_local(node)`: kiểm tra node có thuộc khu cục bộ không.
- `is_connector(node)`: kiểm tra node có thể dùng làm đầu nối không.
- `add_edge(...)`: thêm cạnh stitch.
- `stitch_graph(data)`: nối các component gần nhau thành graph lớn hơn.
- `write_outputs(data)`: ghi lại JSON và file adjacency.
- `main()`: chạy script.

### 8.4 Nhóm kiểm tra và tái sinh nhanh

#### `data/validate_navigation_graph.py`

- `load_graph()`: đọc graph.
- `is_helper_object(obj)`: nhận diện object phụ trợ.
- `is_ignored_hit_object(obj)`: lọc object không cần tính là vật cản.
- `make_side_vector(start, end)`: tạo vector lệch ngang cho ray kiểm tra.
- `edge_samples(start, end)`: sinh nhiều ray mẫu trên một cạnh.
- `cast_until_blocked(...)`: raycast liên tục cho tới khi gặp blocker thực sự.
- `validate_graph(graph)`: kiểm tra toàn bộ cạnh xem có bị mesh chắn không.
- `write_reports(graph, checked_edges, blocked)`: ghi báo cáo JSON/TXT các cạnh bị chặn.
- `main()`: chạy toàn bộ quá trình kiểm tra.

#### `data/regenerate_navigation_graph_quick.py`

- `main()`: chạy bản tái sinh graph nhanh.

#### `data/regenerate_navigation_graph_fast.py`

- `main()`: chạy bản tái sinh graph nhanh/tối giản khác.

### 8.5 Nhóm render và tiện ích khảo sát

Các file như `render_*.py`, `get_*.py`, `list_*.py`, `check_positions.py`, `list_floor_heights.py` chủ yếu là script phụ để:

- render ảnh campus hoặc từng khối,
- truy vấn tọa độ/biên của object trong Blender,
- liệt kê mesh đang hiển thị,
- kiểm tra nhanh dữ liệu mô hình.

Những script này không nằm trong luồng runtime chính của Godot.

## 9. File dữ liệu đầu ra quan trọng

- `data/navigation_graph.json`: graph điều hướng nguồn.
- `godot_project/assets/navigation_graph.json`: graph mà Godot dùng để chạy.
- `data/navigation_graph_adjacency.txt`: bản text của graph để đọc tay/debug.
- `data/navigation_blockers_report.json`: báo cáo cạnh bị chắn.
- `data/navigation_blockers_report.txt`: báo cáo text dễ xem nhanh.
- `godot_project/assets/campus.glb`: mô hình 3D dùng trong Godot.

## 10. Điều khiển trong Godot

- `WASD`: di chuyển.
- `Shift`: tăng tốc.
- `Space`: bay lên hoặc nhảy.
- `Ctrl`: hạ xuống khi ở fly mode.
- `F`: bật/tắt fly mode.
- `ESC`: hiện chuột hoặc quay về menu chính.
- `X`: ẩn/hiện campus model.
- `0`: chạy tất cả thuật toán.
- `1..6`: chọn nhanh thuật toán.
- `7/8`: giảm/tăng tốc độ duyệt của `PathBot`.
- `F3`: bật/tắt debug overlay.
- `H`: bật/tắt highlight toàn bộ node.
- `Click trái`: chọn điểm start khi đang ở chế độ chọn điểm.
- `Click phải`: chọn điểm goal khi đang ở chế độ chọn điểm.

## 11. Gợi ý thuyết trình/nghiệm thu

- Nhấn mạnh pipeline gồm `Blender -> navigation_graph.json -> Godot PathBot`.
- Giải thích rõ `PathBot` hiện chạy local bằng GDScript, không phụ thuộc server.
- Khi demo nên dùng chế độ `0 = Tất cả` để hiện bảng so sánh thuật toán.
- Nếu cần báo cáo kỹ thuật, có thể dùng `data/validate_navigation_graph.py` để chứng minh graph đã được kiểm tra va chạm.
