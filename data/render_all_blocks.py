import bpy, math

scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 16
scene.cycles.use_denoising = True
scene.render.resolution_x = 1024
scene.render.resolution_y = 768
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'

world = scene.world
world.use_nodes = True
tree = world.node_tree
for node in tree.nodes: tree.nodes.remove(node)
sky = tree.nodes.new(type="ShaderNodeTexSky")
sky.sky_type = 'PREETHAM'
bg = tree.nodes.new(type="ShaderNodeBackground")
out = tree.nodes.new(type="ShaderNodeOutputWorld")
tree.links.new(sky.outputs['Color'], bg.inputs['Color'])
tree.links.new(bg.outputs['Background'], out.inputs['Surface'])

cam_data = bpy.data.cameras.new("Cam_All")
cam_data.type = 'PERSP'
cam_data.lens = 35
cam_obj = bpy.data.objects.new("Cam_All", cam_data)
scene.collection.objects.link(cam_obj)
cam_obj.location = (0, 0, 300)
cam_obj.rotation_euler = (0, 0, math.radians(90))
scene.camera = cam_obj

scene.render.filepath = "/home/phuchoangsrc/AI/final/data/render_all_blocks_preview.png"
bpy.ops.render.render(write_still=True)
