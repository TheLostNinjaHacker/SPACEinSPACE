import asyncio
import json
import subprocess
import tempfile
import base64
import os

from mcp_servers.base_mcp_server import BaseMCPServer


class BlenderMCPServer(BaseMCPServer):
    def __init__(self, blender_path: str = "blender"):
        super().__init__("blender")
        self.blender_path = blender_path
        self._setup_tools()

    def _setup_tools(self):
        @self.register("blender.get_scene_info")
        async def get_scene_info():
            script = """
import bpy, json
scene = bpy.context.scene
objects = []
for obj in bpy.data.objects:
    objects.append({
        "name": obj.name,
        "type": obj.type,
        "location": list(obj.location),
        "vertices": len(obj.data.vertices) if hasattr(obj.data, 'vertices') else 0,
    })
print(json.dumps({"objects": objects, "mode": bpy.context.mode}))
"""
            return await self._run_blender_script(script)

        @self.register("blender.create_object")
        async def create_object(type: str = "cube", location: list = None, name: str = None, size: float = 2.0):
            if location is None:
                location = [0, 0, 0]
            loc_str = json.dumps(location)
            name_str = json.dumps(name) if name else "None"
            script = f"""
import bpy, json
bpy.ops.object.select_all(action='DESELECT')
bpy.ops.object.mode_set(mode='OBJECT')
loc = {loc_str}
if "{type}" == "cube":
    bpy.ops.mesh.primitive_cube_add(size={size}, location=loc)
elif "{type}" == "sphere":
    bpy.ops.mesh.primitive_uv_sphere_add(radius={size/2}, location=loc)
elif "{type}" == "cylinder":
    bpy.ops.mesh.primitive_cylinder_add(radius={size/2}, depth={size}, location=loc)
elif "{type}" == "plane":
    bpy.ops.mesh.primitive_plane_add(size={size}, location=loc)
elif "{type}" == "monkey":
    bpy.ops.mesh.primitive_monkey_add(size={size}, location=loc)
obj = bpy.context.active_object
if {name_str}:
    obj.name = {name_str}
print(json.dumps({{"name": obj.name, "vertices": len(obj.data.vertices)}}))
"""
            return await self._run_blender_script(script)

        @self.register("blender.modify_object")
        async def modify_object(object: str, operation: str, value: list):
            val_str = json.dumps(value)
            script = f"""
import bpy, json
obj = bpy.data.objects.get("{object}")
if not obj:
    print(json.dumps({{"error": "Object not found: {object}"}}))
else:
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    if "{operation}" == "extrude":
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.extrude_region_move(TRANSFORM_OT_translate={{'value': {val_str}}})
        bpy.ops.object.mode_set(mode='OBJECT')
    elif "{operation}" == "scale":
        bpy.ops.transform.resize(value={val_str})
    elif "{operation}" == "rotate":
        bpy.ops.transform.rotate(value={val_str[2]})
    elif "{operation}" == "translate":
        bpy.ops.transform.translate(value={val_str})
    elif "{operation}" == "delete":
        bpy.ops.object.delete()
    elif "{operation}" == "duplicate":
        bpy.ops.object.duplicate()
    print(json.dumps({{"object": obj.name, "vertices": len(obj.data.vertices) if hasattr(obj.data, 'vertices') else 0}}))
"""
            return await self._run_blender_script(script)

        @self.register("blender.set_material")
        async def set_material(object: str, color: list, material_name: str = None):
            col_str = json.dumps(color)
            mat_str = json.dumps(material_name) if material_name else "None"
            script = f"""
import bpy, json
obj = bpy.data.objects.get("{object}")
if not obj:
    print(json.dumps({{"error": "Object not found"}}))
else:
    mat = bpy.data.materials.new(name={mat_str} or f"mat_{{obj.name}}")
    mat.use_nodes = False
    mat.diffuse_color = {col_str}
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)
    print(json.dumps({{"material": mat.name, "color": {col_str}}}))
"""
            return await self._run_blender_script(script)

        @self.register("blender.render")
        async def render(output_path: str = "/tmp/render.png", resolution_x: int = 1920, resolution_y: int = 1080):
            script = f"""
import bpy
bpy.context.scene.render.resolution_x = {resolution_x}
bpy.context.scene.render.resolution_y = {resolution_y}
bpy.context.scene.render.filepath = "{output_path}"
bpy.ops.render.render(write_still=True)
print('{{"output": "{output_path}"}}')
"""
            return await self._run_blender_script(script)

        @self.register("blender.get_viewport")
        async def get_viewport():
            script = """
import bpy, base64, tempfile, os
with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
    path = f.name
bpy.context.scene.render.filepath = path
bpy.ops.render.opengl(write_still=True, view_context=True)
with open(path, 'rb') as f:
    data = base64.b64encode(f.read()).decode()
os.unlink(path)
print('{"screenshot": "' + data[:100] + '...", "format": "png"}')
"""
            return await self._run_blender_script(script)

        @self.register("blender.undo")
        async def undo():
            script = """
import bpy
bpy.ops.ed.undo()
print('{"status": "undone"}')
"""
            return await self._run_blender_script(script)

        @self.register("blender.execute_script")
        async def execute_script(script: str):
            escaped = script.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
            wrapped = f"""
import json
try:
    {script}
    print('{{"status": "ok"}}')
except Exception as e:
    print(json.dumps({{"error": str(e)}}))
"""
            return await self._run_blender_script(wrapped)

    async def _run_blender_script(self, script: str) -> dict:
        try:
            proc = await asyncio.create_subprocess_exec(
                self.blender_path, "--background", "--python-expr", script,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
            if proc.returncode != 0:
                return {"success": False, "error": stderr.decode()[:500]}
            output = stdout.decode().strip().split("\n")[-1]
            try:
                result = json.loads(output)
                result["success"] = True
                return result
            except json.JSONDecodeError:
                return {"success": True, "raw_output": output[:500]}
        except asyncio.TimeoutError:
            return {"success": False, "error": "Blender timeout (30s)"}
        except FileNotFoundError:
            return {"success": False, "error": "Blender not found. Install or set blender_path."}


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO)
    server = BlenderMCPServer()
    asyncio.run(server.run_stdio())
