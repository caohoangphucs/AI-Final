"""
Chạy toàn bộ các bước nối graph đã có trong thư mục data theo một pipeline thống nhất.

Run:
  python3 data/apply_navigation_pipeline.py
"""

from __future__ import annotations

import importlib


STEPS = [
    ("patch_ground_paths", "main"),
    ("stitch_path_junctions", "main"),
    ("stitch_flat_ground_paths", "main"),
    ("stitch_building_access_paths", "main"),
    ("stitch_navigation_graph", "main"),
]


def main():
    for module_name, entrypoint in STEPS:
        module = importlib.import_module(module_name)
        print(f"[pipeline] running {module_name}.{entrypoint}()")
        getattr(module, entrypoint)()
    print("[OK] navigation pipeline complete")


if __name__ == "__main__":
    main()
