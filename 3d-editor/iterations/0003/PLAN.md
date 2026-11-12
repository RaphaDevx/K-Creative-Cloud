# Iteration 0003 — object multiselection and translation

Goal: select multiple objects and translate them together using numeric offsets or a world-axis drag gizmo. Optional relative displacement snapping. One drag creates exactly one undoable command group; Escape cancels without changing the document.

## Ownership

| Leaf | Owns | Owner |
|---|---|---|
| gizmo math | src/manipulation.rs; tests/manipulation.rs | mesh_tools |
| selection state | src/object_selection.rs; tests/object_selection.rs | element_selection |
| integration | commands.rs; lib.rs; ui.rs; renderer.rs; group/GUI tests | root |
| delivery | iteration docs; NEXT-STEPS; reviewed scope manifest | root |

All agent work is on separate files. No agent stages or commits. Root integrates and checks returned code. Scene state is changed through validated commands only; transient drag preview is rendered from a candidate scene and not written to the document before commit.

## Included

- Shift-click adds/removes objects in outliner and viewport; active object remains explicit.
- All selected objects outlined; element modes keep a single active object.
- Shared translation command for up to all 256 scene objects, avoiding the 64-command group limit.
- World X/Y/Z gizmo; relative grid-step snapping; numeric group translation.
- Failed/stale operations leave every object/history unchanged; one Undo restores the group.

## Deferred

Rotation/scale gizmos, local axes, box selection and multi-element topology edits follow separately. No new macOS verification is inferred from Linux results. Existing neutral branding and native file format retained.
