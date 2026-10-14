# K-Creative professional workflow

## Start
Development: `scripts/start-creative.sh`, then http://127.0.0.1:47200/creative.
Installed app: launch K-Creative Studio. The app starts its bundled backend on a free loopback port. No system Python or Rust toolchain is required. Data defaults to Documents/K-Creative; K_CREATIVE_DIR overrides the workspace. App resources are read-only and separate from data.

## Produce
Create a project, choose YouTube/Reel/square dimensions, set brand name/accent. Import originals to shared library. K-Photo uses rect/text/image layers, position, dimensions and opacity. K-DAW uses musical note timing in beats and imported clips in seconds. K-Video uses timeline tracks, source trims, splits and volume. Every edit saves via Rust and supports undo/redo.
Export creates real PNG/WAV/MP4 outputs. Video stage previews selected source; full composition is produced on export. Keep .blend sources, render clips and retain editable source. Auto scene cut detects visual transitions, not semantic highlights.

## AI and MCP
Choose Shell/Codex/Claude in the terminal panel. Installed CLIs use their own accounts and normal permission controls; K-Creative adds a session-scoped MCP server without changing global CLI configuration or persisting session tokens. The action console accepts canonical JSON. UI polls project revisions to display external edits.
Local Kokoro neural speech uses bundled weights; supported language availability is shown. German and ElevenLabs equivalence are not claimed.
Optional ComfyUI: start your own trusted local provider and configure K_CREATIVE_COMFY_URL and K_CREATIVE_COMFY_CHECKPOINT. Image generation discovers installed checkpoints. Model-specific image/video workflows are exposed via MCP. No model weights are silently downloaded or provider credentials fabricated.

## Native tools
LMMS export through MCP/API creates an editable .mmp project and real native oscillator render from the canonical notes. Imported audio clips use the shared mixer.

Installed LMMS/GIMP/Kdenlive/Blender/Inkscape are launched through allowlisted adapters. They are separate mature applications; the new editors do not embed their complete interfaces. Optional K_CREATIVE_LMMS/GIMP/KDENLIVE/BLENDER/INKSCAPE/ARDOUR executable variables configure discovery. Native tools are not required for basic PNG/WAV/MP4 editing.

## Release
Run tests and audit, then `bash desktop/scripts/build-dmg-mac.sh`. SSH host/key/build path are configurable; known-host verification stays enabled. Apple signing helper and notarization key remain on Builder Mac. Native FFmpeg can be built in the Builder-owned prefix with verified official source, without changing system Homebrew permissions. Bundled media resources include FFmpeg, ffprobe and model weights.
The release requires a signed/notarized DMG and stapled-app ZIP. SHA512/size/version checks run before publishing. `K_CREATIVE_PUBLISH=1` enables R2 publication, payloads first and manifests last. Cloudflare API token comes from the environment or `sudo bw-secret` using K_CREATIVE_CF_SECRET_ITEM. Public artifacts are downloaded and independently verified before publishing metadata. No token is written into source files.

## Current practical limits
Initial editor tools are intentionally smaller than full commercial suites. Advanced masks/retouching, instrument/plugin hosting, semantic automatic editing, full realtime composited video preview, default AI-video models and SSH compute-worker scheduling remain separate expansion work. Mac and Linux are the targets of this delivery; Windows runtime is not verified.

## Shared workflow inventory
Choose a medium under Creative workflows to see the same adapters used by creative skills. Found tools require a task-specific runtime check; candidates require evaluation. The selector does not install or launch tools. Native editor buttons remain the existing allowlisted launcher. CLI: python3 scripts/creative_tools.py --kind photo. MCP: creative_workflows(kind="photo"). PhotoCraft/FilmCraft remain candidates; see ARTCRAFT-EVALUATION.md for pinned source review and comparison gates.
