# Project Structure

## Main folders

- `godot_project/`: Godot game/project files.
- `python_nav_service/`: Python HTTP service for pathfinding.
- `data/`: Blender sources, exported navigation graph, and analysis scripts.
- `data/discovery/`: Generated discovery metadata for the panorama source site.
- `tools/panorama/`: Node.js tools for panorama discovery, download, build, and local viewer hosting.
- `viewer/`: Static panorama viewer client served by the panorama tool server.

## Common entry points

- `npm run panorama`
- `npm run build:panoramas`
- `npm run discover:assets`
- `npm run discover:map`
- `cd godot_project && ./run_godot.sh`
- `python3 -m uvicorn python_nav_service.server:app --host 127.0.0.1 --port 8000`
