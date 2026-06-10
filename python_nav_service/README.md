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

Payload mau:

```json
{
  "start_id": 0,
  "goal_id": 42,
  "algorithm": "astar"
}
```
