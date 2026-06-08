import bpy
from mathutils import Vector

print("--- Generated Stairs ---")
for obj in bpy.data.objects:
    if "OutStair_AL_up" in obj.name and "S0" in obj.name:
        print(f"{obj.name} location: {obj.location}")

print("--- Generated Bridges ---")
for obj in bpy.data.objects:
    if "Bridge_A_L_Lib" in obj.name and "Slab" in obj.name:
        print(f"{obj.name} location: {obj.location}")

print("--- Original Objects in blend ---")
for name in ["Khoi_A_Day_Trai", "Khoi_A_Day_Phai", "Khoi_B_Ngang", "Khoi_Thu_Vien"]:
    obj = bpy.data.objects.get(name)
    if obj:
        print(f"{name} loc: {obj.location} scale: {obj.scale} hide: {obj.hide_viewport}")
