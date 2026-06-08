import bpy
col = bpy.data.collections.get("KhuA_Architectural")
if col:
    print(f"Total objects in KhuA_Architectural: {len(col.objects)}")
    for obj in sorted(col.objects, key=lambda o: o.name):
        if "Lib" in obj.name or "stair" in obj.name.lower() or "bridge" in obj.name.lower():
            bb = obj.bound_box
            from mathutils import Vector
            wc = [obj.matrix_world @ Vector(c) for c in bb]
            xs, ys, zs = [c.x for c in wc], [c.y for c in wc], [c.z for c in wc]
            print(f"  {obj.name:30} X:({min(xs):.2f}, {max(xs):.2f}) Y:({min(ys):.2f}, {max(ys):.2f}) Z:({min(zs):.2f}, {max(zs):.2f})")
else:
    print("Collection KhuA_Architectural not found")
