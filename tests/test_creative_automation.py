import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from studio import creative_automation as automation


class AutomationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.folder=Path(self.tmp.name)
    def tearDown(self): self.tmp.cleanup()

    def test_unavailable_is_explicit(self):
        with patch.dict(os.environ, {'K_CREATIVE_BLENDER': '/missing/blender'}):
            self.assertFalse(automation.capabilities()['tools']['blender']['available'])
            with self.assertRaisesRegex(RuntimeError,'unavailable'): automation.launch_editor('blender')

    def test_launch_allowlist_and_literal_path(self):
        source=self.folder/'hello ; $x.png'; source.write_bytes(b'image')
        with patch.object(automation,'_required',return_value='/fake/gimp'), patch.object(automation.subprocess,'Popen') as launch:
            launch.return_value.pid=42
            self.assertEqual(automation.launch_editor('gimp',source)['pid'],42)
            self.assertEqual(launch.call_args.args[0],['/fake/gimp',str(source)])
            self.assertNotIn('shell',launch.call_args.kwargs)
        with self.assertRaises(ValueError): automation.launch_editor('sh')

    def test_invalid_parameters(self):
        for threshold in (-1,1.1,float('nan')):
            with self.assertRaises(ValueError): automation.auto_cut('/missing',self.folder,threshold)
        source=self.folder/'source.blend';source.touch()
        for start,end in ((2,1),(1,601),(1.5,3)):
            with self.assertRaises(ValueError): automation.render_blender(source,self.folder,start,end)
        with self.assertRaises(ValueError): automation.render_blender(source,self.folder,1,2,fps=0)

    @unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),'FFmpeg unavailable')
    def test_actual_scene_changes_and_source_preserved(self):
        source=self.folder/'scenes.mp4'
        subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=red:s=64x48:r=10:d=0.5',
            '-f','lavfi','-i','color=blue:s=64x48:r=10:d=0.5','-filter_complex',
            '[0:v][1:v]concat=n=2:v=1:a=0[v]','-map','[v]','-c:v','libx264',str(source)],check=True)
        original=source.read_bytes()
        result=automation.auto_cut(source,self.folder,.1)
        self.assertEqual(len(result['segments']),2)
        self.assertAlmostEqual(result['segments'][1]['source_start'],.5,delta=.01)
        self.assertAlmostEqual(sum(s['duration'] for s in result['segments']),1,delta=.01)
        self.assertEqual(source.read_bytes(),original)
        self.assertEqual(json.loads(Path(result['path']).read_text())['method'],'ffmpeg-scene-detection')

    @unittest.skipUnless(shutil.which('blender') and shutil.which('ffmpeg') and shutil.which('ffprobe'),'Blender unavailable')
    def test_real_blender_cpu_render_and_source_preserved(self):
        source=self.folder/'cube.blend'
        expression=('import bpy; bpy.context.scene.render.resolution_x=64; '
                    'bpy.context.scene.render.resolution_y=48; bpy.context.scene.render.resolution_percentage=100; '
                    'bpy.context.scene.cycles.samples=2; bpy.ops.wm.save_as_mainfile(filepath='+repr(str(source))+')')
        subprocess.run(['blender','--background','--factory-startup','--python-expr',expression],
                       capture_output=True,check=True,timeout=120)
        original=source.read_bytes()
        result=automation.render_blender(source,self.folder/'renders',1,2,10)
        probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-of','json',result['path']]))
        self.assertAlmostEqual(float(probe['format']['duration']),.2,delta=.01)
        self.assertEqual(len(list(Path(result['frames_dir']).glob('*.png'))),2)
        self.assertEqual(source.read_bytes(),original)

if __name__=='__main__': unittest.main()
