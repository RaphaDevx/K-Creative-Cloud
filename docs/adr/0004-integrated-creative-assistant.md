# ADR 0004 — Integrated Creative assistant

## Status
Accepted

## Context
The existing workspace exposes action JSON and a CLI terminal, but has no speech-to-command, sketch-aware conversation or native editable logo/3D creation flow. Electron is the current app shell; it is not SwiftUI/AppKit.

## Decision
Add a dedicated assistant panel using the shared HTTP/MCP contract. Models produce bounded typed plans, never executable Python/shell. The native Rust core validates and commits a batch as one undoable revision, guarded by the project revision seen by the planner. Ellipse/polygon layers remain editable. A trusted Blender primitive adapter produces an editable .blend and PNG preview. User drawings/images become explicit attachments, never instructions.

Speech uses a separately configured local faster-whisper model, with no model download during requests. Cloud planners are opt-in at provider selection; local inference remains separately selectable and unavailable states are explicit. Model output must distinguish edits, clarification and teaching. Pending plans and clarification never mutate state. The project stays the single authority; assistant conversations are project-scoped context, not a second editor state.

## Consequences
Integrated does not mean an all-Rust platform-native GUI or arbitrary tool parity. Existing editor/MCP/terminal flows remain available. Generated skills stay under candidates pending review/promotion. Existing providers retain normal account and permission boundaries. All changes are previewable, undoable and bounded by the action catalog.
