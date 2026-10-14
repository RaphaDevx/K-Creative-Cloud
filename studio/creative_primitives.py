"""Trusted bounded Blender recipes; no model-generated scripts are executed."""
import json
from pathlib import Path
import re
import uuid

from creative_automation import _number, _required, _run

SCRIPT = '''import bpy, json, sys
from mathutils import Vector
cfg=json.loads(sys.argv[sys.argv.index('--')+1])
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
shape=cfg['primitive']; size=cfg['size']
if shape=='sphere': bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=size)
elif shape=='cube': bpy.ops.mesh.primitive_cube_add(size=2*size)
elif shape=='cylinder': bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=size, depth=2*size)
obj=bpy.context.object; obj.name=shape.title()
if shape=='sphere':
    for face in obj.data.polygons: face.use_smooth=True
mat=bpy.data.materials.new('Creative material'); mat.diffuse_color=tuple(int(cfg['color'][i:i+2],16)/255 for i in (1,3,5))+(1,)
obj.data.materials.append(mat)
bpy.ops.object.camera_add(location=(4*size,-6*size,3*size))
camera=bpy.context.object; camera.rotation_euler=(-camera.location).to_track_quat('-Z','Y').to_euler()
scene=bpy.context.scene; scene.camera=camera
bpy.ops.object.light_add(type='AREA', location=(2*size,-4*size,5*size))
bpy.context.object.data.energy=700; bpy.context.object.data.size=5*size
scene.world.color=(.15,.15,.15)
scene.render.engine='CYCLES'; scene.cycles.device='CPU'; scene.cycles.samples=16; scene.cycles.use_denoising=False
scene.render.resolution_x=512; scene.render.resolution_y=512; scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'; scene.render.filepath=cfg['preview']
bpy.ops.wm.save_as_mainfile(filepath=cfg['source'])
bpy.ops.render.render(write_still=True)
'''


def create_primitive(primitive, output_dir, color='#95dbb8', size=1):
    if primitive not in ('sphere', 'cube', 'cylinder'):
        raise ValueError('Unsupported primitive')
    if not isinstance(color, str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', color):
        raise ValueError('Color must be #RRGGBB')
    size = _number(size, .05, 10)
    folder = Path(output_dir) / uuid.uuid4().hex
    folder.mkdir(parents=True)
    source, preview = folder / 'source.blend', folder / 'preview.png'
    script = folder / 'recipe.py'
    script.write_text(SCRIPT)
    config = {'primitive': primitive, 'size': size, 'color': color,
              'source': str(source.resolve()), 'preview': str(preview.resolve())}
    _run([_required('blender'), '--background', '--disable-autoexec', '--python', str(script),
          '--', json.dumps(config)], timeout=300)
    if not source.is_file() or not preview.is_file():
        raise RuntimeError('Blender did not produce source and preview')
    return {'path': str(preview.resolve()), 'source': str(source.resolve()), 'primitive': primitive,
            'engine': 'blender-cycles-cpu', 'size': size, 'color': color}
