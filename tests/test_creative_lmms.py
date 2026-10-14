import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import wave
import xml.etree.ElementTree as ET
import numpy as np
from studio.creative_lmms import export_lmms
from studio.creative_automation import capabilities


class LmmsTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.folder=Path(self.tmp.name)
        self.project={'name':'Notes & <Synth>','bpm':120,'notes':[
            {'pitch':69,'start':1,'duration':1,'velocity':.8,'track':0},
            {'pitch':72,'start':2,'duration':1,'velocity':.5,'track':1}], 'clips':[]}
    def tearDown(self):self.tmp.cleanup()

    def test_editable_xml_beat_ticks_tracks_and_velocity(self):
        result=export_lmms(self.project,self.folder,render=False)
        tree=ET.parse(result['source'])
        tracks=tree.findall('.//track')
        self.assertEqual(len(tracks),2)
        notes=tree.findall('.//note')
        self.assertEqual(notes[0].get('pos'),'48')
        self.assertEqual(notes[0].get('len'),'48')
        self.assertEqual(notes[0].get('key'),'69')
        self.assertEqual(notes[1].get('vol'),'50')
        self.assertEqual(tree.find('.//pattern').get('name'),'Notes & <Synth>')
        self.assertEqual(float(tree.find('head').get('bpm')),120)
        self.assertEqual(result['duration'],1.5)

    def test_invalid_and_unsupported_input(self):
        for bpm in (0,float('nan'),301):
            with self.assertRaises(ValueError): export_lmms(dict(self.project,bpm=bpm),self.folder,False)
        with self.assertRaises(ValueError):export_lmms(dict(self.project,clips=[{}]),self.folder,False)
        with self.assertRaises(ValueError):export_lmms(dict(self.project,notes=[]),self.folder,False)
        with self.assertRaises(ValueError):export_lmms(dict(self.project,notes=[dict(pitch=-1,start=0,duration=1)]),self.folder,False)

    def test_missing_native_engine_explicit(self):
        with patch.dict(os.environ,{'K_CREATIVE_LMMS':'/missing/lmms'}):
            with self.assertRaisesRegex(RuntimeError,'unavailable'):export_lmms(self.project,self.folder)

    @unittest.skipUnless(capabilities()['tools']['lmms']['available'],'LMMS unavailable')
    def test_real_native_audio_pitch_onset_and_tempo(self):
        self.project['notes']=self.project['notes'][:1]
        outputs=[]
        for bpm in (120,60):
            self.project['bpm']=bpm
            result=export_lmms(self.project,self.folder)
            with wave.open(result['path']) as handle:
                self.assertEqual(handle.getframerate(),44100)
                samples=np.frombuffer(handle.readframes(handle.getnframes()),dtype='<i2').reshape(-1,handle.getnchannels())[:,0]
            outputs.append(samples)
            self.assertTrue(Path(result['source']).is_file())
        self.assertEqual(len(outputs[0]),44100)
        self.assertEqual(len(outputs[1]),88200)
        self.assertFalse(outputs[0][:20000].any())
        self.assertGreater(np.max(abs(outputs[0].astype(np.int32))),1000)
        segment=outputs[0][25000:40000]
        spectrum=abs(np.fft.rfft(segment))
        frequency=np.fft.rfftfreq(len(segment),1/44100)[np.argmax(spectrum)]
        self.assertAlmostEqual(frequency,440,delta=4)

if __name__=='__main__':unittest.main()
