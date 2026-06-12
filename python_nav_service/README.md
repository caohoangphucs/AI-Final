# Python Navigation Service

Host local cac thuat toan tim duong de Godot goi qua HTTP.

## Cai dat

```bash
cd /home/phuchoangsrc/AI/final/python_nav_service
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Chay service

```bash
cd /home/phuchoangsrc/AI/final
python3 -m uvicorn python_nav_service.server:app --host 127.0.0.1 --port 8000
```

## API

- `GET /health`
- `GET /nodes/{node_id}`
- `POST /solve-path`
- `POST /benchmark-path`

## Graph search algorithms

Service `solve-path` hiện hỗ trợ:

- `dfs`
- `bfs`
- `iddfs`
- `ucs`
- `greedy`
- `astar`

Payload mau:

```json
{
  "start_id": 0,
  "goal_id": 42,
  "algorithm": "astar"
}
```

Response cũng trả thêm:

- `closed_order`
- `came_from`
- `path_cost`
- `visited_vertices`
- `visited_edges`
- `discovered_vertices`

Benchmark payload mẫu:

```json
{
  "start_id": 0,
  "goal_id": 42
}
```

Benchmark response trả về bảng `rows` với:

- `algorithm`
- `elapsed_ms`
- `path_nodes`
- `path_cost`
- `visited_vertices`
- `visited_edges`
- `discovered_vertices`

## Complex-environment algorithms

Các thuật toán từ phần `Search in complex environments` được cài riêng thành module demo:

- `python -m python_nav_service.complex_search.and_or_queens`
- `python -m python_nav_service.complex_search.sensorless_search`
- `python -m python_nav_service.complex_search.online_search`

Ý nghĩa:

- `and_or_queens`: AND-OR search cho bài toán 8 queens
- `sensorless_search`: belief-state / sensorless search trên grid
- `online_search`: online DFS agent trên graph nhỏ
