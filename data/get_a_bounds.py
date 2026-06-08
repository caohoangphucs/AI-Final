import bpy
from mathutils import Vector
for name in ["Khoi_A.2_Phong_Hoc", "Khoi_A.3_Giang_Duong", "Khoi_A.4_Phong_Hoc", "Khoi_A.5_Giang_Duong"]:
    obj = bpy.data.objects.get(name)
    if obj:
        bb = obj.bound_box
        wc = [obj.matrix_world @ Vector(c) for c in bb]
        xs = [c.x for c in wc]
        print(f"{name}_X: min={min(xs):.1f}, max={max(xs):.1f}")
