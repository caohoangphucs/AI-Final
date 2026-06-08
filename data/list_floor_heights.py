import bpy
from mathutils import Vector

blocks_to_replace = [
    ("Khoi_A.2_Phong_Hoc", 'S', 4),
    ("Khoi_A.3_Giang_Duong", 'S', 4),
    ("Khoi_A.4_Phong_Hoc", 'S', 4),
    ("Khoi_A.5_Giang_Duong", 'S', 4),
    ("Khoi_A_Day_Trai", 'E', 3),
    ("Khoi_A_Day_Phai", 'W', 3),
    ("Khoi_B_Ngang", 'S', 3),
    ("Khoi_C_Phong_Hoc_Dien", 'S', 2),
    ("Khoi_D_Phong_Hoc_Dien", 'S', 2),
    ("Khoi_E.0_Van_Phong_Co_Khi", 'S', 2),
    ("Khoi_E.1_Xuong_Chat_Luong_Cao", 'S', 2),
    ("Khoi_E.2_Can_Tin_Sieu_Thi", 'S', 2),
    ("Khoi_E.3_Xuong_Co_Khi", 'S', 2),
    ("Khoi_E.4_Lop_Hoc_Bat_Giac", 'S', 2),
    ("Khoi_F.1_Phong_Hoc_Xuong", 'S', 2),
    ("Khoi_G_Trung_Tam_Viet_Duc", 'S', 2),
    ("Khoi_Thu_Vien", 'S', 2),
    ("Hoi_Truong_Lon", 'S', 2),
    ("Xuong_Bien_O_To", 'S', 2),
    ("Xuong_Chung_Gam", 'S', 2),
    ("Xuong_Dong_Co", 'S', 2),
    ("Xuong_Nhiet_Dien_Lanh", 'S', 2),
    ("Xuong_Thuc_Tap_Go", 'S', 2)
]

for name, side, fl in blocks_to_replace:
    obj = bpy.data.objects.get(name)
    if obj:
        bb = obj.bound_box
        wc = [obj.matrix_world @ Vector(c) for c in bb]
        zs = [c.z for c in wc]
        z_min, z_max = min(zs), max(zs)
        h = z_max - z_min
        fh = h / fl
        floors = [z_min + fh * i for i in range(fl + 1)]
        floors_str = ", ".join(f"{f:.1f}" for f in floors)
        print(f"{name:30} H:{h:4.1f} Fl:{fl} Floor levels: [{floors_str}]")
