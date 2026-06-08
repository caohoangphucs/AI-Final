import bpy
from mathutils import Vector

names = [
    "Khoi_A_Day_Trai",
    "Khoi_A_Day_Phai",
    "Khoi_B_Ngang",
    "Khoi_Thu_Vien",
    "Khoi_A.1_Trung_Tam_Hanh_Chinh",
    "Khoi_A.2_Phong_Hoc",
    "Khoi_A.3_Giang_Duong",
    "Khoi_A.4_Phong_Hoc",
    "Khoi_A.5_Giang_Duong"
]

for name in names:
    obj = bpy.data.objects.get(name)
    if obj:
        bb = obj.bound_box
        wc = [obj.matrix_world @ Vector(c) for c in bb]
        xs = [c.x for c in wc]
        ys = [c.y for c in wc]
        zs = [c.z for c in wc]
        print(f"{name:30} X:({min(xs):7.2f}, {max(xs):7.2f}) Y:({min(ys):7.2f}, {max(ys):7.2f}) Z:({min(zs):7.2f}, {max(zs):7.2f})")
