# Campus Runner

Godot project để chạy/jump thử trên scene campus 3D export từ Blender.

## Cấu trúc

- `assets/campus.glb`: scene 3D export từ Blender
- `scenes/Main.tscn`: scene chính
- `scripts/player.gd`: FPS controller
- `scripts/main.gd`: sinh collision từ mesh import
- `bin/`: Godot editor binary

## Cách chạy

```bash
cd /home/phuchoangsrc/AI/final/godot_project
./run_godot.sh
```

## Điều khiển

- Khi vào scene: hiện bảng chọn thuật toán, có thêm mục `Tất cả` để chạy và so sánh toàn bộ thuật toán
- `WASD`: di chuyển
- `Shift`: chạy nhanh
- `Space`: nhảy
- `Esc`: nhả chuột
- Click chuột trái vào cửa sổ: bắt lại chuột
- `0`: chạy `Tất cả` thuật toán và hiện bảng so sánh
- `1`: đổi PathBot sang `A*`
- `2`: đổi PathBot sang `BFS`
- `3`: đổi PathBot sang `DFS`
- `4`: đổi PathBot sang `UCS`
- `5`: đổi PathBot sang `Greedy`
- `6`: đổi PathBot sang `HillClimbing`
- `7`: giảm tốc độ duyệt của PathBot
- `8`: tăng tốc độ duyệt của PathBot
- `F3`: bật/tắt overlay debug của PathBot
- `H`: highlight toàn bộ node điều hướng

## Pathfinding

`PathBot` chạy trực tiếp các thuật toán tìm đường bằng GDScript trong Godot, không cần gọi Python service hay HTTP server. Mỗi thuật toán dùng một màu riêng khi chạy và chế độ `Tất cả` sẽ hiện bảng so sánh sau khi hoàn tất.
