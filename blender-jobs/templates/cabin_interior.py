"""
Template: Cozy cabin interior with fireplace, rug, and bookshelf
"""
import bpy, math, random

random.seed(99)

# --- Room (walls + floor) ---
# Floor
bpy.ops.mesh.primitive_plane_add(size=5, location=(0, 0, 0))
floor = bpy.context.active_object
floor.name = "Floor"
floor_tex = bpy.data.materials.new("Floor")
floor_tex.use_nodes = True
floor_tex.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.35, 0.2, 0.1, 1)
floor_tex.node_tree.nodes["Principled BSDF"].inputs[9].default_value = 0.1
floor.data.materials.append(floor_tex)

# Walls
bpy.ops.mesh.primitive_cube_add(size=5, location=(0, 0, 2.5))
walls = bpy.context.active_object
walls.name = "Walls"
walls.scale = (1, 1, 1)
wall_mat = bpy.data.materials.new("Wall")
wall_mat.use_nodes = True
wall_mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.8, 0.75, 0.65, 1)
walls.data.materials.append(wall_mat)

# Ceiling light
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.1, location=(0, 0, 4.8))
light = bpy.context.active_object
light.name = "CeilingLight"
light_mat = bpy.data.materials.new("LightGlow")
light_mat.use_nodes = True
light_mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (1, 0.9, 0.6, 1)
light_mat.node_tree.nodes["Principled BSDF"].inputs[29].default_value = 10
light.data.materials.append(light_mat)

# --- Fireplace ---
bpy.ops.mesh.primitive_cube_add(size=1.2, location=(-2.3, 0, 0.6))
fireplace = bpy.context.active_object
fireplace.name = "Fireplace"
fireplace.scale = (0.4, 1, 0.8)
brick = bpy.data.materials.new("Brick")
brick.use_nodes = True
brick.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.5, 0.2, 0.1, 1)
fireplace.data.materials.append(brick)

# Fireplace hole (inner black)
bpy.ops.mesh.primitive_cube_add(size=0.6, location=(-2.3, 0, 0.4))
hole = bpy.context.active_object
hole.name = "FireplaceHole"
hole_mat = bpy.data.materials.new("Hole")
hole_mat.use_nodes = True
hole_mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.05, 0.05, 0.05, 1)
hole.data.materials.append(hole_mat)

# Fire glow
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.2, location=(-2.3, 0, 0.25))
glow = bpy.context.active_object
glow.name = "FireGlow"
glow_mat = bpy.data.materials.new("FireGlow")
glow_mat.use_nodes = True
glow_mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (1, 0.4, 0, 1)
glow_mat.node_tree.nodes["Principled BSDF"].inputs[29].default_value = 8
glow.data.materials.append(glow_mat)

# --- Rug ---
bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=1.2, depth=0.05, location=(0.5, 0, 0.025))
rug = bpy.context.active_object
rug.name = "Rug"
rug_mat = bpy.data.materials.new("Rug")
rug_mat.use_nodes = True
rug_mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.6, 0.1, 0.1, 1)
rug.data.materials.append(rug_mat)

# --- Bookshelf ---
bpy.ops.mesh.primitive_cube_add(size=1.5, location=(2.3, 0, 1))
shelf = bpy.context.active_object
shelf.name = "Bookshelf"
shelf.scale = (0.3, 1, 0.7)
wood = bpy.data.materials.new("Wood")
wood.use_nodes = True
wood.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.4, 0.25, 0.1, 1)
shelf.data.materials.append(wood)

# Books
for i in range(5):
    for j in range(3):
        x = 2.3 + random.uniform(-0.1, 0.1)
        y = -0.6 + j * 0.45
        z = 0.3 + i * 0.3
        bpy.ops.mesh.primitive_cube_add(size=0.15, location=(x, y, z))
        book = bpy.context.active_object
        book.name = f"Book_{i}_{j}"
        book.scale = (0.8, 0.2, 1.2)
        book_mat = bpy.data.materials.new(f"BookMat_{i}_{j}")
        book_mat.use_nodes = True
        r, g, b = random.random(), random.random(), random.random()
        book_mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (r, g, b, 1)
        book.data.materials.append(book_mat)

# --- Lamp ---
bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.03, depth=0.3, location=(1, 1.5, 0.15))
lamp_stand = bpy.context.active_object
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.12, location=(1, 1.5, 0.35))
lamp = bpy.context.active_object
lamp.name = "Lamp"
lamp_mat = bpy.data.materials.new("LampGlow")
lamp_mat.use_nodes = True
lamp_mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (1, 0.8, 0.4, 1)
lamp_mat.node_tree.nodes["Principled BSDF"].inputs[29].default_value = 15
lamp.data.materials.append(lamp_mat)

# --- Camera ---
cam = bpy.data.objects["Camera"]
cam.location = (-1.5, -3.5, 2)
cam.rotation_euler = (1.1, 0, -0.5)
