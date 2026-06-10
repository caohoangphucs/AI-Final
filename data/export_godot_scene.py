"""
Export scene Blender sang GLB để import vào Godot.

Chạy:
  blender --background data/Untitled_arch.blend --python data/export_godot_scene.py
"""

import bpy
import os


OUT_PATH = "/home/phuchoangsrc/AI/final/godot_project/assets/campus.glb"
HELPER_PREFIXES = ("StairEntry_", "BridgeEntry_", "Cut_")


def ensure_dir(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)


def is_exportable(obj):
    if obj.type not in {"MESH", "EMPTY"}:
        return False
    if obj.name.startswith(HELPER_PREFIXES):
        return False
    if obj.hide_render or obj.hide_viewport:
        return False
    return True


def main():
    ensure_dir(OUT_PATH)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in bpy.data.objects:
        if is_exportable(obj):
            obj.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=OUT_PATH,
        export_format="GLB",
        use_selection=True,
        export_apply=True,
        export_yup=True,
    )
    print(f"[OK] exported {OUT_PATH}")


if __name__ == "__main__":
    main()
