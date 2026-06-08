import bpy
for obj in bpy.data.objects:
    if obj.type == 'MESH' and not obj.hide_viewport:
        if any(x in obj.name for x in ["Thu_Vien", "A1", "A_Day"]):
            print(f"{obj.name:35} hide_render: {obj.hide_render} location: {obj.location}")
