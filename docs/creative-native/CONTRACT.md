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

## Assistant/native additions

layer.add/update kinds also include ellipse and polygon. Polygon points are 3..256 normalized [x,y] pairs in 0..1. Image layers accept brightness,contrast,saturation in 0..4; sources remain unchanged. project.batch {expected_revision:integer,commands:[{action,params}]} permits 1..64 catalogued project mutations, no nested batches/history/read/create commands or nested project_id. Native validation/mutation/persistence is atomic; one batch is one undo revision. HTTP revalidates asset paths inside batches.

Assistant plan/apply, explicit sketch references and local transcription are documented in ASSISTANT.md. Project brand identity validation and portable social-media handoff are documented in BRANDING.md.

## Suite document graph (P0)

Optional `project.document_graph` contains `documents`, `links` and optional `last_archive`. Legacy projects gain the field only on their first graph mutation. A document has generated `id`, `name`, `kind`, bounded JSON `content`, `archived`, optional `owner_id` and `origin_id`. Kinds: sketch/cad/scene/photo/vector/music/video/notes/textile. `content` is inert manifest data, not code, not a verified media snapshot. Limit: 4096 document records (including archived copies), 16384 links and 256 KiB content per manifest.

Actions:
- `document.create {name,kind,content:object}` adds a manifest; returns the updated project.
- `document.link {dependent_id,source_id}` adds an active project-local dependency. Missing/archived targets, duplicate links and cycles are rejected.
- `document.archive_preview {id,mode}` reads affected documents and direct users without writing history/revision. Returns `{expected_revision,id,mode,archive:[{id,name,kind}],preserve_for:[dependent_id],physical_files_deleted:false,scope:"project_manifest_only"}`.
- `document.archive {id,mode,expected_revision}` is one atomic, undoable mutation and returns the updated project. `preserve_dependents` creates one local manifest copy per direct dependent, rewires its link, retains the source's upstream links, and archives the original. `cascade_dependents` archives the original and transitive active users, preserving unrelated/shared inputs. `last_archive` records preview and replacement IDs. Changed revision rejects the operation.

Archive is soft deletion; neither files nor historical links are physically removed. `owner_id` is logical placement/provenance, not filesystem ownership or an authorization boundary. Copies share manifest references but are not guaranteed durable binary versions. Native program adapters, blob storage/GC, cross-project references and distributed merge are outside P0. Archive and preview are forbidden inside `project.batch`; create/link may be batched. The integrated language planner allowlist is unchanged. Generic HTTP/MCP action transport exposes the new catalog without a second state store. UI for archive choices follows P1.
