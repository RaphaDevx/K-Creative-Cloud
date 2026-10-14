# Creative Native v1 contract

The Rust CLI creative-core reads one JSON object from stdin and returns one JSON object stdout. Invoked with --store DIRECTORY. Errors: {ok:false,error:string}, nonzero exit. Success: {ok:true,result:...}.
Actions via {action:string,project_id?:string,params:object}. State authority is Rust; UI and MCP use same API POST /api/creative/action. GET /api/creative/actions returns schemas; GET /api/creative/projects lists projects. POST /api/creative/upload multipart file returns {ok:true,result:{path,name}}. POST /api/creative/export {project_id,kind:photo|video|audio} starts a job; GET /api/creative/jobs/{id} returns {id,status,output?,error?}. Asset URLs GET /api/creative/asset?path=...

Project shape: {id,name,revision,width:1280,height:720,fps:30,bpm:120,brand:{},assets:[],layers:[],clips:[],notes:[]}.
Actions and params:
project.create {name,width?,height?,fps?,bpm?}; project.list {}; project.get {}; project.rename {name}; project.settings {width?,height?,fps?,bpm?}; brand.update {brand:object};
asset.add {path,name,kind:image|video|audio|blender};
layer.add {name,kind:rect|text|image,x?,y?,width?,height?,opacity?,color?,text?,path?}; layer.update {id,...properties}; layer.remove {id};
clip.add {asset_id,track:integer,start:number,duration:number,source_start?:number,volume?:number}; clip.update {id,...properties}; clip.remove {id}; clip.split {id,at:number} (absolute timeline seconds);
Note start/duration use musical beats and convert using 60/bpm. Clip timing uses seconds.

note.add {pitch:integer,start:number,duration:number,velocity?:number,track?:integer}; note.update {id,...properties}; note.remove {id};
history.undo {}; history.redo {}.
Each entity receives id. Collections flat. Updates increment revision. Atomic persistence and serialized concurrent mutations. History persisted. No fake provider generation.

Media worker interface: studio/creative_media.py exposes capabilities()->dict and export_project(project,kind,output_dir)->path string. Takes canonical project above. Genuine PNG composition (Pillow), WAV synth/mix, MP4 timeline (FFmpeg). TTS separately synthesize_speech(text,output,provider='kokoro',voice='af_heart',speed=1.0,language='en-us')->dict with path/provider. Errors explicit, never pretend espeak equals neural TTS. All imported files confined by root bridge to workspace/media. Optional adapters honestly reported.

## Shared workflow discovery

GET /api/creative/workflows?kind=photo returns {ok:true,result:{root,kind,tools,manifest_errors,note}}. kind is optional, restricted to photo/vector/video/reel/screen/statistics/audio/music/speech/3d/cad; unknown values return 422. CLI scripts/creative_tools.py, GUI and MCP creative_workflows use studio/creative_discovery.py. available_to_probe means adapter/binary presence, never runtime readiness. unavailable means missing prerequisites. review_required means candidate or missing acceptance evidence/adapter. Discovery reads inert metadata, installs nothing and executes no manifest commands. The native-editor launch allowlist remains separate.
