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

- `WASD`: di chuyển
- `Shift`: chạy nhanh
- `Space`: nhảy
- `Esc`: nhả chuột
- Click chuột trái vào cửa sổ: bắt lại chuột
- `1`: đổi PathBot sang `A*`
- `2`: đổi PathBot sang `BFS`
- `3`: đổi PathBot sang `DFS`
- `4`: đổi PathBot sang `UCS`
- `5`: đổi PathBot sang `Greedy`
- `6`: đổi PathBot sang `IDDFS`
- `P`: chạy benchmark toàn bộ thuật toán và hiện bảng so sánh
- `7`: giảm tốc độ duyệt của PathBot
- `8`: tăng tốc độ duyệt của PathBot
- `F3`: bật/tắt overlay debug của PathBot
- `H`: highlight toàn bộ node điều hướng

## Gọi thuật toán Python

`PathBot` hỗ trợ gọi service Python qua HTTP tại `http://127.0.0.1:8000/solve-path`.

Chạy service:

```bash
cd /home/phuchoangsrc/AI/final/python_nav_service
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd /home/phuchoangsrc/AI/final
python3 -m uvicorn python_nav_service.server:app --host 127.0.0.1 --port 8000
```

`PathBot` đang được khóa cứng để ưu tiên gọi Python service. Nếu service không phản hồi, bot sẽ tự fallback về thuật toán local trong GDScript.
