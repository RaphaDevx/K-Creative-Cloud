# 3d-editor roadmap

The direction is a Rust-native replacement. Milestones are capabilities to prove, not a claim that all Blender features can be recreated in one session.

Iteration 0002 adds single vertex/edge picking with occlusion, point/edge position editing, proportional face inset and shared-edge linear subdivision. Multi-selection, drag gizmos and smoothing remain future modeling work. Ordered working plan: [NEXT-STEPS](docs/NEXT-STEPS.md).

1. **v0.1 — scene and polygon foundation:** independent desktop GPU viewport; orbit/pan/zoom; selectable mesh primitives; transforms/material color/visibility; face extrusion; grouped journal and undo/redo; atomic scene files; OBJ; headless command groups; configurable startup/workspace branding.
2. **Modeling:** robust editable topology, vertex/edge/face multi-selection, interactive axis gizmos, snapping, bevel/inset/loop cut, normals, subdivision and modifier stack. Acceptance: saved edit histories plus manifold reference fixtures; no degenerate results silently saved.
3. **Surface and output:** UV editor, textures, PBR materials, glTF interchange, color management, GPU/CPU rendering and cameras/lights. Acceptance: reference roundtrips with explicit loss reports.
4. **Motion:** timeline only inside animation workspace, keyframes/curves, skeletons, skinning and constrained animation. Acceptance: deterministic sampled poses and imported/exported animation fixtures.
5. **Physics/textiles:** collisions, cloth data/solver interfaces, measured materials, pattern editing and manufacturing exports. Acceptance: calibrated dimensional fixtures and physical prototypes, not visually plausible drapes alone.
6. **CAD/print:** constraint solver and B-Rep integration evaluated separately from the mesh model. Preserve units, tolerances and precise source geometry; tested print/export pipeline.
7. **Collaboration and suite:** immutable scene artifacts in Suite graph, operation-level actor IDs, semantic merges, selective undo and optional visual agent cursors. Current single-user journal is not a distributed CRDT.
8. **Platforms and extension SDK:** Google/Apple identity, device sync, signed plugins, native iPad input/renderer bindings and package variants. Desktop operation is verified first; no implied iPad compatibility from Rust UI libraries alone.

Branding stays independent across all milestones: replace profile first; later add licensed fonts/marks/start artwork, app icon and signed package identity. Preserve neutral mode and document-content colors. Strong launch identity and one recognizable workspace anchor; no repetitive logos over the viewport.
