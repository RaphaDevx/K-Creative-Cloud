# ADR 0007 — Independent Rust 3d-editor

## Status

Accepted. Supersedes ADR 0006's engine-retention direction specifically for the newly requested long-term 3D replacement; existing Blender/FreeCAD workflows remain available.

## Context

The user now explicitly requests native Rust rewrites, starting with a Blender replacement named `3d-editor`, neutral today and prepared for strong recognizable branding later. Existing primitive recipes do not satisfy an independent editable 3D application.

## Decision

Create `3d-editor/` as a separate Rust crate with an egui/eframe desktop surface, wgpu viewport, typed scene commands and headless access. Start with polygon meshes, object transforms, triangle/face picking, face extrusion, file persistence, OBJ interchange and grouped history. Build application branding as a versioned JSON profile affecting startup and a persistent workspace identity slot, separate from document data.

## Consequences

This is the beginning of an engine, not a complete port of Blender. Sculpture, UV/texturing, rigging, animation, path tracing, physics, CAD kernels, textiles, plugin compatibility and native mobile hosting require separately accepted milestones. Reuse Rust libraries with pinned dependencies rather than translating millions of lines of upstream engine code. CAD precision and manufacturing guarantees must not be inferred from a polygon mesh.

Existing Suite Rust project and graph remain intact. This application's native document becomes an artifact/source for a future Suite adapter; no duplicate synchronized scene store is introduced today. Rust-only application code does not imply absence of native OS/GPU dependencies. No proprietary .blend reader or lossless .blend conversion is promised.

## Replacement

The scene/command layer stays UI-independent. A future renderer or shell can be replaced without altering command history semantics or branding contracts. Any Suite adapter must declare import/export/link/roundtrip capabilities and remain explicit about native feature losses.
