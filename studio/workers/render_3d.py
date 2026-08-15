#!/usr/bin/env python3
"""
K-Creative render_3d.py — Headless Blender Worker

Runs as: blender -b [file.blend] -P render_3d.py -- [args]
Or called via: python3 render_3d.py --help (shows arg info)

Env vars:
  K_PROJECT   path to project.json
  K_OUTPUT    output directory (default: project renders_dir)
  K_CHAPTER   chapter id to render
  DISPLAY     X display (default :99)
"""
import sys
import os
import json
from pathlib import Path

# ── Detect if running inside Blender ──────────────────────────
INSIDE_BLENDER = False
try:
    import bpy
    INSIDE_BLENDER = True
except ImportError:
    pass

# ── Config ────────────────────────────────────────────────────
PROJECT_JSON = os.environ.get("K_PROJECT", "")
OUTPUT_DIR   = os.environ.get("K_OUTPUT", "/home/raphael/K-Creative-Cloud/renders")
CHAPTER_ID   = os.environ.get("K_CHAPTER", "")


def load_project(path: str) -> dict:
    if path and Path(path).exists():
        return json.loads(Path(path).read_text())
    return {}


def setup_scene(width=1024, height=1024, samples=64, engine="CYCLES"):
    scene = bpy.context.scene
    scene.render.engine = engine
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(Path(OUTPUT_DIR) / "frame_####")
    if engine == "CYCLES":
        scene.cycles.samples = samples
        scene.cycles.device = "CPU"
    elif engine == "BLENDER_EEVEE":
        scene.eevee.taa_render_samples = samples


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def add_world_light(color=(0.8, 0.85, 1.0), strength=1.0):
    world = bpy.data.worlds.new("KWorld")
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (*color, 1.0)
    bg.inputs["Strength"].default_value = strength


def add_camera(loc=(0, -6, 2.5), target=(0, 0, 0)):
    import mathutils
    bpy.ops.object.camera_add(location=loc)
    cam = bpy.context.active_object
    bpy.context.scene.camera = cam
    direction = mathutils.Vector(target) - mathutils.Vector(loc)
    cam.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    return cam


def k_violet_material(name="K_Violet"):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.424, 0.278, 1.0, 1.0)  # #6C47FF
    bsdf.inputs["Roughness"].default_value = 0.25
    bsdf.inputs["Metallic"].default_value = 0.05
    return mat


def export_glb(output_path: str):
    bpy.ops.export_scene.gltf(
        filepath=output_path,
        export_format="GLB",
        export_apply=True,
        export_materials="EXPORT",
    )
    print(f"[render_3d] GLB → {output_path}")


def render_still(output_path: str = None):
    if output_path:
        bpy.context.scene.render.filepath = output_path
    bpy.ops.render.render(write_still=True)
    print(f"[render_3d] Render → {bpy.context.scene.render.filepath}")


# ── Chapter renderers ─────────────────────────────────────────

def render_app_icon():
    """
    Renders a 3D K-Learning app icon (rounded square + K-Violet material).
    Outputs: icon_1024.png + icon.glb
    """
    clear_scene()
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    setup_scene(1024, 1024, samples=64, engine="BLENDER_EEVEE")
    add_world_light(color=(0.05, 0.03, 0.1), strength=0.3)
    add_camera(loc=(0, -5, 1.5), target=(0, 0, 0))

    # Rounded cube base (icon shape)
    bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 0))
    obj = bpy.context.active_object
    obj.name = "AppIcon"
    mod = obj.modifiers.new("Bevel", "BEVEL")
    mod.width = 0.35
    mod.segments = 6
    obj.data.materials.append(k_violet_material("K_Violet_Icon"))

    # Area light for drama
    bpy.ops.object.light_add(type="AREA", location=(3, -3, 4))
    light = bpy.context.active_object
    light.data.energy = 200
    light.data.color = (0.6, 0.4, 1.0)

    # Render PNG
    render_still(str(Path(OUTPUT_DIR) / "icon_1024.png"))
    # Export GLB
    export_glb(str(Path(OUTPUT_DIR) / "icon.glb"))


def render_logo_3d():
    """
    3D version of K-Learning logo — abstract K shape extrusion.
    """
    clear_scene()
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    setup_scene(2048, 1024, samples=128, engine="CYCLES")
    add_world_light(color=(0.03, 0.02, 0.08), strength=0.2)
    add_camera(loc=(0, -8, 1), target=(0, 0, 0))

    # Placeholder cube — replace with actual K-shape curve import
    bpy.ops.mesh.primitive_cube_add(size=1.5, location=(0, 0, 0))
    obj = bpy.context.active_object
    obj.name = "Logo_K"
    mod = obj.modifiers.new("Bevel", "BEVEL")
    mod.width = 0.1
    mod.segments = 3
    obj.data.materials.append(k_violet_material("K_Violet_Logo"))

    render_still(str(Path(OUTPUT_DIR) / "logo_3d.png"))
    export_glb(str(Path(OUTPUT_DIR) / "logo.glb"))


CHAPTER_MAP = {
    "02_icons":   render_app_icon,
    "01_logo":    render_logo_3d,
}


# ── Entry point (when run inside Blender) ─────────────────────
if INSIDE_BLENDER:
    project = load_project(PROJECT_JSON)
    chapter = CHAPTER_ID or "02_icons"

    if chapter in CHAPTER_MAP:
        print(f"[render_3d] Running chapter: {chapter}")
        CHAPTER_MAP[chapter]()
    else:
        print(f"[render_3d] Unknown chapter: {chapter}. Available: {list(CHAPTER_MAP.keys())}")
        render_app_icon()

    print("[render_3d] Done.")

else:
    print("render_3d.py — must be run inside Blender:")
    print("  blender -b -P render_3d.py")
    print("  K_CHAPTER=02_icons K_OUTPUT=/tmp/renders blender -b -P render_3d.py")
