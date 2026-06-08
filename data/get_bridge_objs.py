import bpy
for obj in bpy.data.objects:
    if "Bridge" in obj.name and "Slab" in obj.name:
        bb = obj.bound_box
        from mathutils import Vector
        wc = [obj.matrix_world @ Vector(c) for c in bb]
        xs, ys, zs = [c.x for c in wc], [c.y for c in wc], [c.z for c in wc]
        print(f"{obj.name:30} X:({min(xs):.2f}, {max(xs):.2f}) Y:({min(ys):.2f}, {max(ys):.2f}) Z:({min(zs):.2f}, {max(zs):.2f})")
