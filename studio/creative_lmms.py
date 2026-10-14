"""Export canonical beat notes to editable LMMS projects and its real synth engine."""
from __future__ import annotations
import math
import os
from pathlib import Path
import subprocess
import uuid
import wave
import xml.etree.ElementTree as ET

try:
    from .creative_automation import _required
except ImportError:
    from creative_automation import _required

TICKS_PER_BEAT = 48
MAX_SECONDS = 600


def _number(value, low, high):
    value = float(value)
    if not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f'Number must be {low}..{high}')
    return value


def export_lmms(project, output_dir, render=True) -> dict:
    bpm = _number(project.get('bpm', 120), 20, 300)
    if project.get('clips'):
        raise ValueError('LMMS export currently supports MIDI notes only; imported clips require the shared audio mixer')
    notes = project.get('notes', [])
    if not notes:
        raise ValueError('LMMS export requires at least one note')
    groups = {}
    duration = 0.
    for note in notes:
        pitch = _number(note['pitch'], 0, 127)
        track = _number(note.get('track', 0), 0, 255)
        if not pitch.is_integer() or not track.is_integer():
            raise ValueError('Note pitch and track must be integers')
        start = _number(note.get('start', 0), 0, MAX_SECONDS * bpm / 60)
        length = _number(note['duration'], .001, MAX_SECONDS * bpm / 60)
        velocity = _number(note.get('velocity', .8), 0, 1)
        duration = max(duration, (start+length)*60/bpm)
        if duration > MAX_SECONDS:
            raise ValueError('LMMS export exceeds 600 seconds')
        groups.setdefault(int(track), []).append(dict(key=str(int(pitch)),
            pos=str(round(start*TICKS_PER_BEAT)), len=str(max(1,round(length*TICKS_PER_BEAT))),
            vol=str(round(velocity*100)), pan='0'))
    root = ET.Element('lmms-project', {'creator':'K-Creative', 'version':'1.0', 'type':'song', 'creatorversion':'1.2.2'})
    ET.SubElement(root, 'head', {'bpm':str(bpm), 'mastervol':'80', 'masterpitch':'0', 'timesig_numerator':'4', 'timesig_denominator':'4'})
    container = ET.SubElement(ET.SubElement(root,'song'),'trackcontainer',{'type':'song'})
    for track_id, track_notes in sorted(groups.items()):
        track = ET.SubElement(container,'track',{'type':'0','name':f'Track {track_id+1}', 'muted':'0','solo':'0'})
        instrumenttrack = ET.SubElement(track,'instrumenttrack', {'vol':'60','pan':'0','pitch':'0','basenote':'57','fxch':'0','usemasterpitch':'1','pitchrange':'1'})
        instrument = ET.SubElement(instrumenttrack,'instrument',{'name':'tripleoscillator'})
        ET.SubElement(instrument,'tripleoscillator', {'vol0':'100','vol1':'0','vol2':'0','wavetype0':'0','coarse0':'-12','finel0':'0','finer0':'0','pan0':'0'})
        pattern_ticks = max(int(n['pos'])+int(n['len']) for n in track_notes)
        pattern = ET.SubElement(track,'pattern', {'type':'1','name':project.get('name','K-Creative melody'), 'pos':'0',
            'len':str(math.ceil(pattern_ticks/192)*192), 'steps':'16'})
        for note in track_notes:
            ET.SubElement(pattern,'note',note)
    folder = Path(output_dir); folder.mkdir(parents=True,exist_ok=True)
    source = folder / f'{uuid.uuid4().hex}.mmp'
    ET.ElementTree(root).write(source,encoding='utf-8',xml_declaration=True)
    result = {'path':str(source),'source':str(source),'engine':'lmms','bpm':bpm,
              'duration':duration,'ticks_per_beat':TICKS_PER_BEAT,
              'instrument':'tripleoscillator','limitations':['Notes quantized to 1/48 beat','Imported clips unsupported']}
    if not render:
        return result
    executable = _required('lmms')
    output = source.with_suffix('.wav')
    env = dict(os.environ,QT_QPA_PLATFORM='offscreen')
    process = subprocess.run([executable,'render',str(source),'-o',str(output),'-f','wav','-s','44100','-x','1'],
                             env=env,capture_output=True,text=True,timeout=600)
    if process.returncode or not output.is_file():
        raise RuntimeError('LMMS render failed: '+process.stderr[-2000:])
    # LMMS pads patterns to bars and adds release tails. Canonical exports end at
    # the last note; crop only the newly generated WAV, never imported material.
    with wave.open(str(output),'rb') as handle:
        params = handle.getparams()
        count = math.ceil(duration*params.framerate)
        samples = handle.readframes(count)
    frame_bytes = params.nchannels*params.sampwidth
    samples += b'\x00' * max(0,count*frame_bytes-len(samples))
    with wave.open(str(output),'wb') as handle:
        handle.setparams(params)
        handle.writeframes(samples)
    result['path'] = str(output)
    return result
