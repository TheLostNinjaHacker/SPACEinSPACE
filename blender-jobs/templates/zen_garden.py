"""
Template: Zen garden with sand, rocks, and bonsai tree
"""
import bpy, math, random

random.seed(13)

# --- Sand ground ---
bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=3.5, depth=0.15, location=(0, 0, -0.05))
sand = bpy.context.active_object
sand.name = "Sand"
sand_mat = bpy.data.materials.new("Sand")
sand_mat.use_nodes = True
sand_mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.85, 0.8, 0.65, 1)
sand_mat.node_tree.nodes["Principled BSDF"].inputs[9].default_value = 0.8
sand.data.materials.append(sand_mat)

# --- Sand ripples (concentric rings) ---
for r in range(1, 6):
    radius = r * 0.6
    bpy.ops.mesh.primitive_torus_add(major_radius=radius, minor_radius=0.02, location=(0, 0, 0.02))
    ring = bpy.context.active_object
    ring.name = f"Ripple_{r}"
    ring.rotation_euler = (math.radians(90), 0, 0)
    ring_mat = bpy.data.materials.new(f"RippleMat_{r}")
    ring_mat.use_nodes = True
    ring_mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.75, 0.7, 0.55, 1)
    ring.data.materials.append(ring_mat)

# --- Rocks ---
def make_rock(x, y, scale):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=scale, location=(x, y, scale * 0.5))
    rock = bpy.context.active_object
    rock.name = f"Rock_{x}_{y}"
    rock_mat = bpy.data.materials.new(f"RockMat_{x}_{y}")
    rock_mat.use_nodes = True
    rock_mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (
        0.2 + random.uniform(-0.05, 0.05),
        0.2 + random.uniform(-0.05, 0.05),
        0.2 + random.uniform(-0.05, 0.05),
        1
    )
    rock_mat.node_tree.nodes["Principled BSDF"].inputs[9].default_value = 0.9
    rock.data.materials.append(rock_mat)
    rock.scale = (random.uniform(0.8, 1.2), random.uniform(0.8, 1.2), random.uniform(0.5, 0.8))

rocks = [(-1.5, 1.2, 0.4), (0.8, -1.5, 0.5), (-0.5, -1, 0.25), (2, 1.8, 0.3), (-2.2, -1.5, 0.35)]
for x, y, s in rocks:
    make_rock(x, y, s)

# --- Bonsai tree ---
# Trunk
bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=0.08, depth=0.6, location=(1.5, -0.8, 0.35))
trunk = bpy.context.active_object
trunk.name = "BonsaiTrunk"
trunk.rotation_euler = (0.3, 0, 0.7)
trunk_mat = bpy.data.materials.new("Trunk")
trunk_mat.use_nodes = True
trunk_mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.3, 0.15, 0.05, 1)
trunk.data.materials.append(trunk_mat)

# Foliage (clusters)
for i in range(7):
    a = math.radians(i * 51 + 10)
    r = 0.3 + random.uniform(0, 0.2)
    x = 1.5 + math.cos(a) * r
    z = -0.8 + math.sin(a) * r
    y = 0.5 + random.uniform(0, 0.2)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.12 + random.uniform(0, 0.08), location=(x, z, y))
    leaf = bpy.context.active_object
    leaf.name = f"Leaf_{i}"
    leaf_mat = bpy.data.materials.new(f"LeafMat_{i}")
    leaf_mat.use_nodes = True
    leaf_mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.05, 0.25 + random.uniform(0, 0.1), 0.05, 1)
    leaf.data.materials.append(leaf_mat)

# --- Small lantern ---
bpy.ops.mesh.primitive_cylinder_add(vertices=6, radius=0.05, depth=0.2, location=(-2, 2, 0.1))
pole = bpy.context.active_object
bpy.ops.mesh.primitive_cube_add(size=0.12, location=(-2, 2, 0.25))
lantern = bpy.context.active_object
lantern.name = "Lantern"
lantern_mat = bpy.data.materials.new("LanternGlow")
lantern_mat.use_nodes = True
lantern_mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (1, 0.4, 0, 1)
lantern_mat.node_tree.nodes["Principled BSDF"].inputs[29].default_value = 3
lantern.data.materials.append(lantern_mat)

# --- Camera ---
cam = bpy.data.objects["Camera"]
cam.location = (4, -3, 2.5)
cam.rotation_euler = (1.0, 0, 0.9)
