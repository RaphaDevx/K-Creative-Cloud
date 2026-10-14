# Integrated Creative Assistant

The assistant is directly integrated into the Electron/web workspace, Python adapters and Rust action core. It is not an all-Rust/Swift native UI. Provider choice is separate from the local editing engine.

Open Creative Assistant, create a project and choose a provider. Codex/Claude use installed CLIs and existing account access; Qwen CLI currently supports text only. API accepts OpenAI-compatible structured chat-completion/vision endpoints; Ollama accepts a configured local chat model. Other online protocols can be added as planner adapters; arbitrary endpoints are not automatically compatible. No tools/shell are exposed to the language planner. Provider labels distinguish installed/configured from access tested on request.

Text requests produce an edit plan, material clarification or help. Clear reversible edits apply automatically; Entwurf vor dem Anwenden prüfen allows review first. Native project.batch is guarded by expected_revision and is one Undo step. Plans expire after 15 minutes and cannot be applied twice. Project switches isolate conversation context and references. Help and clarification never mutate projects.

Draw a sketch or attach PNG/JPEG/WebP, then describe the desired result. Vision-capable providers see the explicitly attached reference. Native polygon/ellipse/text layers remain editable. Raster brightness/contrast/saturation are non-destructive layer values. Sphere/cube/cylinder are trusted Blender recipes producing .blend source and PNG preview; arbitrary mesh edits, full raster retouching or unlimited external-program parity are not implemented.

Microphone recording is explicit, visibly stopped and bounded to 90 seconds. Local Whisper transcribes, the recording is removed after inference and recognized text remains editable before sending. Real microphone/device permission behavior must be checked on target hardware; file-based speech inference and browser wiring are separately testable. Recognition can be wrong, especially synthetic speech, accents and noise; review the text.

## Local speech resources

Install studio/creative-speech-requirements.txt in the backend build environment. Provision an approved multilingual faster-whisper model directory separately; default development path is workspace/models/whisper-base, packaged default is K_CREATIVE_MODELS/whisper-base. K_CREATIVE_WHISPER_MODEL overrides either. Model weights never download during an audio request. PyInstaller optionally includes installed speech libraries; provision model files outside the onefile executable to avoid large extraction at every startup. The running backend reports unavailable when libraries/model are absent.

## Assistant skill

candidates/creative-assistant/SKILL.md is the project-specific skill and is included in planner instructions and the packaged backend. It covers interpretation, sketch editability, clarification, help, supported boundaries and the brand/social-media handoff. It remains a candidate for the global K-AI skill catalog until its normal review/promotion; no global skill files are overwritten.
