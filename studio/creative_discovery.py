"""Shared read-only discovery for CLI, HTTP and MCP. No engine commands run."""
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(sys._MEIPASS) if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent.parent
BUILTINS=[
 ('studio','photo','studio/creative_media.py',None,10),
 ('studio','audio','studio/creative_media.py',None,10),
 ('ffmpeg','video',None,'ffmpeg',10),
 ('screen-recorder','screen','packages/screen-recording/tutorial.py','ffmpeg',10),
 ('pillow-scenes','reel','video-shorts-mcp/frame_render.py',None,10),
 ('stat-viz','statistics','video-shorts-mcp/stat_viz.py',None,10),
 ('gimp','photo','gimp-mcp','gimp',20),
 ('inkscape','vector','inkscape-mcp','inkscape',10),
 ('kdenlive','video','kdenlive-mcp','kdenlive',20),
 ('lmms','music','lmms-mcp','lmms',10),
 ('blender','3d','Blender','blender',10),
 ('freecad','cad','freecad-mcp','freecad',10),
 ('remotion','reel','remotion-mcp',None,20),
 ('tts','speech','video-shorts-mcp/tts_kokoro.py',None,10),
]
KINDS={x[1] for x in BUILTINS}

def discover(kind=None,root=ROOT,which=shutil.which):
    entries=[];errors=[]
    for name,k,adapter,exe,priority in BUILTINS:
        if kind and kind!=k:continue
        path=root/adapter if adapter else None
        binary=which(exe) if exe else None
        present=(path.exists() if path else True) and (bool(binary) if exe else True)
        entries.append({'id':name,'kind':k,'priority':priority,'adapter':str(path) if path else None,
                        'binary':binary,'status':'available_to_probe' if present else 'unavailable',
                        'verified_for_task':False})
    directory=root/'packages/integrations'
    for file in sorted(directory.glob('*.json')):
        try:
            item=json.loads(file.read_text())
            if not isinstance(item,dict) or not isinstance(item.get('id'),str):raise ValueError('invalid id')
            if item.get('kind') not in KINDS:raise ValueError('invalid kind')
            if not isinstance(item.get('adapter'),str):raise ValueError('adapter must be relative path')
            path=(root/item['adapter']).resolve()
            if not path.is_relative_to(root.resolve()):raise ValueError('adapter outside creative root')
            if kind and item['kind']!=kind:continue
            approved=item.get('review_status')=='accepted' and item.get('acceptance_evidence')
            entries.append({'id':item['id'],'kind':item['kind'],'priority':50,
                            'adapter':str(path),'status':'available_to_probe' if approved and path.is_file() else 'review_required',
                            'verified_for_task':False,'manifest':str(file)})
        except (ValueError,TypeError,OSError) as e:errors.append({'manifest':file.name,'error':str(e)})
    return {'root':str(root),'kind':kind,'tools':sorted(entries,key=lambda x:(x['priority'],x['id'])),
            'manifest_errors':errors,'note':'Discovery does not prove runtime readiness; probe required before use.'}
