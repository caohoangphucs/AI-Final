import bpy
a1 = bpy.data.objects.get("Khoi_A.1_Trung_Tam_Hanh_Chinh")
if a1:
    from mathutils import Vector
    bb = a1.bound_box
    wc = [a1.matrix_world @ Vector(c) for c in bb]
    xs = [c.x for c in wc]
    ys = [c.y for c in wc]
    zs = [c.z for c in wc]
    print(f"A1_BOUNDS: x({min(xs):.1f}, {max(xs):.1f}), y({min(ys):.1f}, {max(ys):.1f}), z({min(zs):.1f}, {max(zs):.1f})")
    print(f"A1_LOC: {a1.location}")
