"""
Template: Chessboard with reflective marble and obsidian pieces
"""
import bpy, math, random

random.seed(7)

# --- Board ---
bpy.ops.mesh.primitive_cube_add(size=4, location=(0, 0, 0.1))
board = bpy.context.active_object
board.name = "Board"
board.scale = (1, 1, 0.05)
board_mat = bpy.data.materials.new("Board")
board_mat.use_nodes = True
board_mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.15, 0.1, 0.05, 1)
board_mat.node_tree.nodes["Principled BSDF"].inputs[9].default_value = 0.3
board.data.materials.append(board_mat)

# Squares
for x in range(8):
    for y in range(8):
        is_white = (x + y) % 2 == 0
        bx = -1.75 + x * 0.5
        by = -1.75 + y * 0.5
        bpy.ops.mesh.primitive_plane_add(size=0.48, location=(bx, by, 0.11))
        sq = bpy.context.active_object
        sq.name = f"Square_{x}_{y}"
        sq_mat = bpy.data.materials.new(f"SqMat_{x}_{y}")
        sq_mat.use_nodes = True
        if is_white:
            sq_mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.95, 0.93, 0.88, 1)
            sq_mat.node_tree.nodes["Principled BSDF"].inputs[9].default_value = 0.5
        else:
            sq_mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.05, 0.05, 0.05, 1)
            sq_mat.node_tree.nodes["Principled BSDF"].inputs[9].default_value = 0.3
        sq.data.materials.append(sq_mat)

# --- Pieces ---
def make_piece(name, x, y, is_white, type="pawn"):
    color = (0.95, 0.93, 0.88, 1) if is_white else (0.05, 0.05, 0.05, 1)
    roughness = 0.1 if is_white else 0.3
    px = -1.75 + x * 0.5
    py = -1.75 + y * 0.5

    if type == "pawn":
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.12, location=(px, py, 0.2))
        piece = bpy.context.active_object
        piece.scale = (1, 1, 0.8)
    elif type == "king":
        bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.08, depth=0.3, location=(px, py, 0.2))
        piece = bpy.context.active_object
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.1, location=(px, py, 0.4))
        top = bpy.context.active_object
        top.parent = piece
    else:  # knight/queen-like
        bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.08, depth=0.25, location=(px, py, 0.18))
        piece = bpy.context.active_object

    piece.name = f"{name}_{x}_{y}"
    piece_mat = bpy.data.materials.new(f"PieceMat_{x}_{y}")
    piece_mat.use_nodes = True
    piece_mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = color
    piece_mat.node_tree.nodes["Principled BSDF"].inputs[9].default_value = roughness
    piece.data.materials.append(piece_mat)

# Pawns
for i in range(8):
    make_piece("WPawn", i, 1, True, "pawn")
    make_piece("BPawn", i, 6, False, "pawn")

# Back row
back = ["rook", "knight", "bishop", "queen", "king", "bishop", "knight", "rook"]
for i, t in enumerate(back):
    make_piece(f"W{t}", i, 0, True, t)
    make_piece(f"B{t}", i, 7, False, t)

# --- Camera ---
cam = bpy.data.objects["Camera"]
cam.location = (3.5, -3.5, 3)
cam.rotation_euler = (1.0, 0, 0.8)
