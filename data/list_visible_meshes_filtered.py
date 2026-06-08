import bpy
for obj in bpy.data.objects:
    if obj.type == 'MESH' and not obj.hide_viewport:
        if ("Thu_Vien" in obj.name or "A1" in obj.name) and not "Stair" in obj.name:
            print(f"{obj.name:35} hide_render: {obj.hide_render} location: {obj.location}")
