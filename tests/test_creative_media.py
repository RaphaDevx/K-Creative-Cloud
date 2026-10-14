import json
from pathlib import Path
import subprocess
import tempfile
import unittest
import wave
import numpy as np
from PIL import Image
from studio.creative_media import export_project, synthesize_speech, capabilities


class MediaTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)
        self.project = dict(width=64, height=48, fps=10, bpm=60, layers=[], clips=[], notes=[], assets=[])

    def tearDown(self):
        self.tmp.cleanup()

    def test_layers_have_real_alpha_and_preserve_source(self):
        source = self.folder / 'source.png'
        Image.new('RGB', (8, 8), 'blue').save(source)
        original = source.read_bytes()
        self.project['layers'] = [dict(kind='rect', x=0,y=0,width=64,height=48,color='#ff0000'),dict(kind='image',path=str(source),x=0,y=0,width=8,height=8,opacity=.5)]
        output = export_project(self.project, 'photo', self.folder)
        with Image.open(output) as image:
            self.assertEqual(image.getpixel((20,20)), (255,0,0,255))
            self.assertEqual(image.getpixel((2,2)), (127,0,128,255))
        self.assertEqual(source.read_bytes(), original)

    def test_synth_duration_frequency_and_polyphony(self):
        self.project['notes'] = [dict(pitch=69,start=.1,duration=.4,velocity=.8),dict(pitch=81,start=.1,duration=.4,velocity=.8)]
        output = export_project(self.project, 'audio', self.folder)
        with wave.open(output) as handle:
            self.assertEqual(handle.getnframes(), 24000)
            data = np.frombuffer(handle.readframes(handle.getnframes()), dtype='<i2').reshape(-1,2)
        self.assertFalse(data[:4800].any())
        signal = data[6000:18000,0]
        frequencies = np.fft.rfftfreq(len(signal), 1/48000)
        spectrum = abs(np.fft.rfft(signal))
        for frequency in (440,880):
            self.assertGreater(spectrum[np.argmin(abs(frequencies-frequency))], spectrum.max()*.5)

    def test_note_beats_follow_tempo_but_clip_seconds_do_not(self):
        self.project['notes'] = [dict(pitch=69,start=1,duration=1,velocity=.8)]
        outputs = []
        for bpm in (60,120):
            self.project['bpm'] = bpm
            output = export_project(self.project,'audio',self.folder)
            with wave.open(output) as handle:
                outputs.append(np.frombuffer(handle.readframes(handle.getnframes()),dtype='<i2').reshape(-1,2))
        self.assertEqual(len(outputs[0]),96000)
        self.assertEqual(len(outputs[1]),48000)
        self.assertFalse(outputs[0][:48000].any())
        self.assertFalse(outputs[1][:24000].any())
        self.assertTrue(outputs[1][25000:30000].any())
        self.project['assets'] = [dict(id='image',kind='image',path='unused-for-audio')]
        self.project['clips'] = [dict(asset_id='image',start=2,duration=1)]
        output = export_project(self.project,'audio',self.folder)
        with wave.open(output) as handle:
            self.assertEqual(handle.getnframes(),144000)

    def test_invalid_tempo_rejected(self):
        for bpm in (0,float('nan'),19,301):
            self.project['bpm'] = bpm
            with self.assertRaises(ValueError): export_project(self.project,'audio',self.folder)

    def test_invalid_input(self):
        with self.assertRaises(ValueError): export_project(self.project,'gif',self.folder)
        self.project['notes'] = [dict(pitch=200,start=0,duration=1)]
        with self.assertRaises(ValueError): export_project(self.project,'audio',self.folder)
        with self.assertRaises(ValueError): synthesize_speech('', self.folder/'speech.wav')

    @unittest.skipUnless(capabilities()['video'], 'FFmpeg unavailable')
    def test_imported_audio_source_offset(self):
        source = self.folder/'input.wav'
        signal = np.concatenate([np.zeros(4800),np.full(4800,.3)]).astype(np.float32)
        with wave.open(str(source),'wb') as handle:
            handle.setnchannels(1); handle.setsampwidth(2); handle.setframerate(48000)
            handle.writeframes((signal*32767).astype('<i2').tobytes())
        self.project['assets']=[dict(id='a',kind='audio',path=str(source))]
        self.project['clips']=[dict(asset_id='a',start=.1,duration=.1,source_start=.1,volume=.5)]
        output=export_project(self.project,'audio',self.folder)
        with wave.open(output) as handle:
            data=np.frombuffer(handle.readframes(handle.getnframes()),dtype='<i2').reshape(-1,2)
        self.assertFalse(data[:4800].any())
        self.assertTrue(np.all(abs(data[5000:,0]-3475)<10))

    @unittest.skipUnless(capabilities()['video'], 'FFmpeg unavailable')
    def test_video_timeline_pixels_and_duration(self):
        source=self.folder/'red.png'; Image.new('RGB',(64,48),'red').save(source)
        self.project['assets']=[dict(id='v',kind='image',path=str(source))]
        self.project['clips']=[dict(asset_id='v',track=0,start=.2,duration=.3)]
        output=export_project(self.project,'video',self.folder)
        probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-of','json',output]))
        self.assertAlmostEqual(float(probe['format']['duration']),.5,delta=.11)
        pixels=subprocess.check_output(['ffmpeg','-v','error','-i',output,'-f','rawvideo','-pix_fmt','rgb24','-'])
        frames=np.frombuffer(pixels,dtype=np.uint8).reshape(-1,48,64,3)
        self.assertLess(frames[0,20,20,0],50)
        self.assertGreater(frames[3,20,20,0],220)

    @unittest.skipUnless(capabilities()['video'], 'FFmpeg unavailable')
    def test_imported_video_trim_and_silent_track(self):
        source=self.folder/'source.mp4'
        subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=red:s=64x48:r=10:d=0.2','-f','lavfi','-i','color=blue:s=64x48:r=10:d=0.3','-filter_complex','[0:v][1:v]concat=n=2:v=1:a=0[v]','-map','[v]','-c:v','libx264',str(source)],check=True)
        original=source.read_bytes()
        self.project['assets']=[dict(id='v',kind='video',path=str(source))]
        self.project['clips']=[dict(asset_id='v',track=0,start=.1,duration=.3,source_start=.2)]
        output=export_project(self.project,'video',self.folder)
        pixels=subprocess.check_output(['ffmpeg','-v','error','-i',output,'-f','rawvideo','-pix_fmt','rgb24','-'])
        frames=np.frombuffer(pixels,dtype=np.uint8).reshape(-1,48,64,3)
        self.assertEqual(len(frames),4)
        self.assertGreater(frames[2,20,20,2],220)
        self.assertLess(frames[2,20,20,0],30)
        self.assertEqual(source.read_bytes(),original)

if __name__ == '__main__': unittest.main()
