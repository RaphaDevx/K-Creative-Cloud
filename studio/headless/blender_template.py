"""
K-Creative Headless Blender Template
Usage: blender -b [optional.blend] -P blender_template.py -- [args]

This script runs inside Blender's Python environment (bpy).
Customize the TASK section below, then POST to /api/exec/blender:
  { "script": "<contents of this file>", "render": true }
"""
import bpy
import sys
import os
from pathlib import Path

# ── Output config ──────────────────────────────────────────────
OUTPUT_DIR = os.environ.get("K_OUTPUT", "/home/raphael/K-Creative-Cloud/renders/headless")
Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)

# ── Scene setup ────────────────────────────────────────────────
def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)

def setup_render(width=1920, height=1080, samples=64, engine="CYCLES"):
    scene = bpy.context.scene
    scene.render.engine = engine
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(Path(OUTPUT_DIR) / "render_####")
    if engine == "CYCLES":
        scene.cycles.samples = samples
        scene.cycles.device = "CPU"  # change to GPU if available

def add_hdri_lighting(strength=1.0):
    world = bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Strength"].default_value = strength
    bg.inputs["Color"].default_value = (0.8, 0.85, 1.0, 1.0)

def add_camera(location=(5, -5, 3), look_at=(0, 0, 0)):
    bpy.ops.object.camera_add(location=location)
    cam = bpy.context.active_object
    bpy.context.scene.camera = cam
    # Point at target
    import mathutils
    target = mathutils.Vector(look_at)
    direction = target - cam.location
    rot = direction.to_track_quat('-Z', 'Y')
    cam.rotation_euler = rot.to_euler()
    return cam

# ── TASK: customize this section ──────────────────────────────
def create_asset():
    """
    Replace this with your actual asset creation logic.
    Example: create a K-Learning app icon in 3D.
    """
    clear_scene()
    setup_render(1024, 1024, samples=32, engine="EEVEE")
    add_hdri_lighting()
    add_camera(location=(0, -6, 2), look_at=(0, 0, 0))

    # Example: rounded cube (app icon base shape)
    bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 0))
    obj = bpy.context.active_object
    obj.name = "AppIcon"

    # Bevel for rounded corners
    bpy.ops.object.modifier_add(type='BEVEL')
    obj.modifiers["Bevel"].width = 0.3
    obj.modifiers["Bevel"].segments = 4

    # K-Violet material
    mat = bpy.data.materials.new("K_Violet")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.424, 0.278, 1.0, 1.0)  # #6C47FF
    bsdf.inputs["Roughness"].default_value = 0.3
    bsdf.inputs["Metallic"].default_value = 0.1
    obj.data.materials.append(mat)

    # Export as GLB for web viewer
    glb_path = str(Path(OUTPUT_DIR) / "asset.glb")
    bpy.ops.export_scene.gltf(
        filepath=glb_path,
        export_format="GLB",
        export_apply=True,
    )
    print(f"[K-Creative] GLB exported: {glb_path}")

    # Render frame 1
    bpy.ops.render.render(write_still=True)
    print(f"[K-Creative] Render saved to: {bpy.context.scene.render.filepath}")

# ── Run ────────────────────────────────────────────────────────
if __name__ == "__main__":
    create_asset()
    print("[K-Creative] Done.")
