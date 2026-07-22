"""
Template: Low-poly forest clearing with campfire and tent
"""
import bpy, math, random

random.seed(42)

# --- Ground ---
bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=5, depth=0.2, location=(0, 0, -0.1))
ground = bpy.context.active_object
ground.name = "Ground"
ground_mat = bpy.data.materials.new("Ground")
ground_mat.use_nodes = True
ground_mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.2, 0.5, 0.1, 1)
ground.data.materials.append(ground_mat)

# --- Trees ---
def make_tree(x, z, scale=1):
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.15*scale, depth=1.5*scale, location=(x, z, 0.75*scale))
    trunk = bpy.context.active_object
    trunk.name = f"Trunk_{x}_{z}"
    trunk_mat = bpy.data.materials.new(f"TrunkMat_{x}_{z}")
    trunk_mat.use_nodes = True
    trunk_mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.4, 0.25, 0.1, 1)
    trunk.data.materials.append(trunk_mat)

    bpy.ops.mesh.primitive_cone_add(vertices=6, radius1=0.8*scale, depth=1.2*scale, location=(x, z, 1.7*scale))
    crown = bpy.context.active_object
    crown.name = f"Crown_{x}_{z}"
    crown_mat = bpy.data.materials.new(f"CrownMat_{x}_{z}")
    crown_mat.use_nodes = True
    crown_mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.1, 0.4, 0.05, 1)
    crown.data.materials.append(crown_mat)

for angle in range(0, 360, 45):
    rad = math.radians(angle)
    r = random.uniform(2.5, 4)
    x = math.cos(rad) * r
    z = math.sin(rad) * r
    make_tree(x, z, random.uniform(0.6, 1.2))

# --- Campfire ---
bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.5, depth=0.1, location=(0, 0, 0.1))
fire_base = bpy.context.active_object
fire_base.name = "FireBase"
stone_mat = bpy.data.materials.new("Stone")
stone_mat.use_nodes = True
stone_mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.3, 0.3, 0.3, 1)
fire_base.data.materials.append(stone_mat)

for i in range(6):
    a = math.radians(i * 60 + random.uniform(-10, 10))
    r = 0.3
    x = math.cos(a) * r
    z = math.sin(a) * r
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.08, location=(x, 0.15, z))
    stone = bpy.context.active_object
    stone.name = f"FireStone_{i}"
    stone.data.materials.append(stone_mat)

# Fire glow (emissive sphere)
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.15, location=(0, 0.2, 0))
fire = bpy.context.active_object
fire.name = "FireGlow"
fire_mat = bpy.data.materials.new("FireGlow")
fire_mat.use_nodes = True
fire_mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (1, 0.5, 0, 1)
fire_mat.node_tree.nodes["Principled BSDF"].inputs[29].default_value = 5
fire.data.materials.append(fire_mat)

# --- Tent ---
tent_x, tent_z = 1.8, 1.8
bpy.ops.mesh.primitive_cone_add(vertices=3, radius1=0.8, depth=0.8, location=(tent_x, tent_z, 0.4))
tent = bpy.context.active_object
tent.name = "Tent"
tent.rotation_euler = (0, 0, math.radians(45))
tent_mat = bpy.data.materials.new("Tent")
tent_mat.use_nodes = True
tent_mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.6, 0.3, 0.1, 1)
tent.data.materials.append(tent_mat)

# --- Camera ---
cam = bpy.data.objects["Camera"]
cam.location = (6, -5, 4)
cam.rotation_euler = (1.2, 0, 0.9)
