import bpy

for obj in bpy.data.objects:
    if "F0_Slab" in obj.name and "Khoi" in obj.name:
        print(f"BldgSlab: {obj.name} loc={obj.location}")

