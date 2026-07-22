"""
Template: Floating island with ancient tree and waterfall
"""
import bpy, math, random

random.seed(42)

# --- Island ---
bpy.ops.mesh.primitive_uv_sphere_add(radius=2, location=(0, 0, 0))
island = bpy.context.active_object
island.name = "Island"
island.scale = (1.5, 1.5, 0.3)
island_mat = bpy.data.materials.new("Island")
island_mat.use_nodes = True
island_mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.3, 0.2, 0.1, 1)
island.data.materials.append(island_mat)

# Grass top
bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=1.8, depth=0.05, location=(0, 0, 0.3))
grass = bpy.context.active_object
grass.name = "GrassTop"
grass_mat = bpy.data.materials.new("Grass")
grass_mat.use_nodes = True
grass_mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.1, 0.5, 0.05, 1)
grass.data.materials.append(grass_mat)

# --- Ancient tree ---
# Trunk
bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=0.25, depth=2, location=(0, 0, 1.3))
trunk = bpy.context.active_object
trunk.name = "TreeTrunk"
trunk_mat = bpy.data.materials.new("Trunk")
trunk_mat.use_nodes = True
trunk_mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.35, 0.2, 0.08, 1)
trunk.data.materials.append(trunk_mat)

# Roots
for i in range(5):
    a = math.radians(i * 72)
    x = math.cos(a) * 0.3
    y = math.sin(a) * 0.3
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.05, depth=0.4, location=(x, y, 0.25))
    root = bpy.context.active_object
    root.name = f"Root_{i}"
    root.rotation_euler = (math.radians(30), 0, a)
    root.data.materials.append(trunk_mat)

# Canopy
for i in range(12):
    a = math.radians(i * 30 + random.uniform(-5, 5))
    r = 0.5 + random.uniform(0, 0.5)
    x = math.cos(a) * r
    y = math.sin(a) * r
    z = 1.8 + random.uniform(0, 0.5)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.25 + random.uniform(0, 0.15), location=(x, y, z))
    leaf = bpy.context.active_object
    leaf.name = f"Leaf_{i}"
    leaf_mat = bpy.data.materials.new(f"LeafMat_{i}")
    leaf_mat.use_nodes = True
    leaf_mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (
        0.05, 0.3 + random.uniform(0, 0.15), 0.05, 1
    )
    leaf.data.materials.append(leaf_mat)

# --- Waterfall ---
# Water stream
for i in range(5):
    z = 0.5 + i * 0.3
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.04, depth=0.05, location=(1.2, 0, z))
    drop = bpy.context.active_object
    drop.name = f"WaterDrop_{i}"
    drop_mat = bpy.data.materials.new(f"WaterMat_{i}")
    drop_mat.use_nodes = True
    drop_mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.5, 0.7, 0.9, 0.6)
    drop_mat.node_tree.nodes["Principled BSDF"].inputs[9].default_value = 0.0
    drop.data.materials.append(drop_mat)

# Water pool below
bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.4, depth=0.05, location=(1.2, 0, -0.3))
pool = bpy.context.active_object
pool.name = "WaterPool"
pool.data.materials.append(drop_mat)

# --- Floating rocks ---
for i in range(4):
    a = math.radians(random.uniform(0, 360))
    r = 2.5 + random.uniform(0, 1)
    x = math.cos(a) * r
    y = math.sin(a) * r
    z = random.uniform(-1, 0)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.15 + random.uniform(0, 0.1), location=(x, y, z))
    rock = bpy.context.active_object
    rock.name = f"FloatRock_{i}"
    rock.data.materials.append(island_mat)

# --- Background glow ---
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.5, location=(0, 0, 3.5))
glow = bpy.context.active_object
glow.name = "BackgroundGlow"
glow_mat = bpy.data.materials.new("Glow")
glow_mat.use_nodes = True
glow_mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.6, 0.8, 1, 1)
glow_mat.node_tree.nodes["Principled BSDF"].inputs[29].default_value = 3
glow.data.materials.append(glow_mat)
glow.scale = (4, 4, 0.5)

# --- Camera ---
cam = bpy.data.objects["Camera"]
cam.location = (5, -3, 2.5)
cam.rotation_euler = (1.0, 0, 0.9)
