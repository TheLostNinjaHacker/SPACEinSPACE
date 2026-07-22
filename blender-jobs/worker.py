#!/usr/bin/env python3
"""
Blender Autonomous Worker
Picks pending jobs from blender-jobs/queue/pending/, sends them to Blender
via MCP socket, captures screenshot, and moves to done/failed.
"""

import json
import os
import socket
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "blender-jobs" / "config.json"
QUEUE_DIR = ROOT / "blender-jobs" / "queue"
SCREENSHOTS_DIR = ROOT / "blender-jobs" / "screenshots"
GALLERY_PATH = ROOT / "blender-jobs" / "gallery.md"

with open(CONFIG_PATH) as f:
    CONFIG = json.load(f)

SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)


def send_to_blender(cmd: dict) -> dict:
    """Send a command to the Blender MCP addon via TCP socket."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(30)
    s.connect((CONFIG["blender_host"], CONFIG["blender_port"]))
    s.sendall(json.dumps(cmd).encode() + b"\n")
    resp = b""
    while True:
        try:
            chunk = s.recv(4096)
            if not chunk:
                break
            resp += chunk
            json.loads(resp)
            break
        except json.JSONDecodeError:
            continue
        except socket.timeout:
            break
    s.close()
    return json.loads(resp) if resp else {"status": "error", "message": "no response"}


def execute_code(code: str) -> dict:
    return send_to_blender({"type": "execute_code", "params": {"code": code}})


def get_screenshot(job_name: str) -> bool:
    """Save viewport screenshot to disk."""
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    screenshot_path = str((SCREENSHOTS_DIR / f"{job_name}.png").resolve())
    result = send_to_blender({
        "type": "get_viewport_screenshot",
        "params": {"filepath": screenshot_path}
    })
    ok = result.get("status") == "success" and result.get("result", {}).get("success")
    if ok:
        print(f"Screenshot saved: {screenshot_path}")
    else:
        print(f"Screenshot result: {result}")
    return ok


def scene_setup_code():
    """Code that runs before every job: clean scene, set up render engine."""
    return """
import bpy
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
for mat in bpy.data.materials:
    bpy.data.materials.remove(mat)
bpy.context.scene.render.engine = 'CYCLES'
bpy.context.scene.render.resolution_x = 1920
bpy.context.scene.render.resolution_y = 1080
bpy.ops.object.light_add(type='SUN', location=(10, -10, 15))
bpy.ops.object.light_add(type='AREA', location=(-5, 5, 8))
bpy.data.objects['Area'].data.energy = 200
bpy.ops.object.camera_add(location=(8, -8, 6))
cam = bpy.context.active_object
cam.rotation_euler = (1.1, 0, 0.8)
bpy.context.scene.camera = cam
"""


def parse_job(filepath: Path) -> dict:
    """Parse a .md job file into a dict."""
    text = filepath.read_text()
    lines = text.strip().split("\n")
    prompt = lines[0] if lines else ""
    return {"prompt": prompt, "full_text": text, "filepath": filepath}


def create_job_file(prompt: str):
    """Write a new pending job."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = "".join(c if c.isalnum() or c in " -_" else "" for c in prompt.lower())[:40]
    slug = slug.strip().replace(" ", "-")
    filename = f"{timestamp}_{slug}.md"
    filepath = QUEUE_DIR / "pending" / filename
    filepath.write_text(f"{prompt}\n\n---\nCreated: {datetime.now().isoformat()}\n")
    return filepath


TEMPLATES_DIR = ROOT / "blender-jobs" / "templates"

TEMPLATE_MAP = [
    (["forest", "campfire", "tent"], "forest_campfire.py"),
    (["cabin", "fireplace", "cozy", "interior", "fireplace", "bookshelf"], "cabin_interior.py"),
    (["chess", "marble", "obsidian", "board", "pawn"], "chessboard.py"),
    (["zen", "garden", "bonsai", "sand", "rock"], "zen_garden.py"),
    (["floating", "island", "waterfall", "ancient"], "floating_island.py"),
]


def build_prompt_code(job: dict) -> str:
    """Match prompt to a template and return executable bpy code."""
    prompt = job["prompt"].lower()

    for keywords, template_file in TEMPLATE_MAP:
        if any(k in prompt for k in keywords):
            tmpl_path = TEMPLATES_DIR / template_file
            if tmpl_path.exists():
                code = tmpl_path.read_text()
                if "import bpy" not in code:
                    code = "import bpy, math, random\n" + code
                return code

    # Fallback: simple scene
    return """import bpy, math, random

bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 1))
cube = bpy.context.active_object
mat = bpy.data.materials.new("Default")
mat.use_nodes = True
mat.node_tree.nodes["Principled BSDF"].inputs[0].default_value = (0.2, 0.4, 0.8, 1)
cube.data.materials.append(mat)

bpy.ops.object.text_add(location=(0, 0, 2.2))
text = bpy.context.active_object
text.data.body = "SUPARAYS"
text.data.size = 0.5
text.data.align_x = "CENTER"
"""


def run_job(job: dict) -> bool:
    """Execute a single job. Returns True on success."""
    job_name = job["filepath"].stem
    print(f"\n--- Running: {job['prompt']} ---")

    # Move to active
    active_path = QUEUE_DIR / "active" / job["filepath"].name
    shutil.move(str(job["filepath"]), str(active_path))

    # Reset scene
    result = execute_code(scene_setup_code())
    if result["status"] != "success":
        print(f"Scene reset failed: {result}")
        shutil.move(str(active_path), str(QUEUE_DIR / "failed" / job["filepath"].name))
        return False

    # Build the scene
    code = build_prompt_code(job)
    result = execute_code(code)
    if result["status"] != "success":
        print(f"Job execution failed: {result}")
        # Save error
        err_path = QUEUE_DIR / "failed" / job["filepath"].name
        active_path.read_text()
        shutil.move(str(active_path), str(err_path))
        return False

        # Take screenshot
        try:
            get_screenshot(job_name)
        except Exception as e:
            print(f"Screenshot failed: {e}")

    # Move to done
    done_path = QUEUE_DIR / "done" / job["filepath"].name
    shutil.move(str(active_path), str(done_path))

    # Update gallery
    append_gallery(job, done_path)
    print(f"Done: {job['prompt']}")
    return True


def append_gallery(job: dict, done_path: Path):
    """Append to the gallery index."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    screenshot_name = done_path.stem + ".png"
    entry = (
        f"- **{job['prompt']}**  \n"
        f"  *Completed {timestamp}*  \n"
        f"  ![screenshot](../blender-jobs/screenshots/{screenshot_name})\n"
    )
    GALLERY_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not GALLERY_PATH.exists():
        GALLERY_PATH.write_text("# Blender Gallery\n\nAutonomously generated scenes.\n\n")
    with open(GALLERY_PATH, "a") as f:
        f.write(entry)


def refill_queue():
    """Generate new ideas from seed file when queue runs low."""
    pending_count = len(list(QUEUE_DIR.glob("pending/*.md")))
    if pending_count >= CONFIG["min_pending_for_refill"]:
        return

    seed_path = ROOT / CONFIG["seed_file"]
    if not seed_path.exists():
        return

    seeds = seed_path.read_text().strip().split("\n## ")
    used = set()

    for done in QUEUE_DIR.glob("done/*.md"):
        used.add(done.read_text().split("\n")[0].strip())

    new_count = 0
    for section in seeds:
        lines = section.strip().split("\n")
        for line in lines:
            if line.startswith("- "):
                idea = line[2:].strip()
                if idea not in used and not (QUEUE_DIR / "pending").glob(f"*{idea[:20]}*"):
                    create_job_file(idea)
                    new_count += 1
                    if new_count >= 3:
                        return


def main():
    print(f"=== Blender Worker @ {datetime.now().isoformat()} ===")

    # Refill queue if needed
    refill_queue()

    # Get pending jobs
    pending = sorted(QUEUE_DIR.glob("pending/*.md"))
    if not pending:
        print("No pending jobs. Add some to blender-jobs/queue/pending/")
        return

    jobs_run = 0
    for p in pending:
        if jobs_run >= CONFIG["max_jobs_per_run"]:
            break
        job = parse_job(p)
        run_job(job)
        jobs_run += 1

    print(f"\n=== Done: {jobs_run} job(s) processed ===")


if __name__ == "__main__":
    main()
