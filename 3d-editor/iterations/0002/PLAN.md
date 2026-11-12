# Iteration 0002 — modeling, selection and repeatable delivery

User authorizes ongoing scoped K-Dev commits and parallel agents. Goal of this iteration is a small usable modeling increment, not the entire Blender roadmap.

## Work ownership

| Leaf | Owns | Agent | Needs | Acceptance |
|---|---|---|---|---|
| mesh | src/mesh.rs; tests/modeling.rs | mesh_tools | existing validated mesh | atomic centroid-factor inset and shared-edge linear subdivision, topology fixtures |
| selection | src/selection.rs; tests/selection.rs | element_selection | existing camera/scene | pixel-space vertex/edge picks, visibility/occlusion/transforms, invalid-input fixtures |
| test contract | docs/TEST-MATRIX.md; scripts/check-native.sh | test_matrix | existing scripts and read-only builder config | portable sequential checks, failure propagation; no false Mac result |
| integration | commands.rs; lib.rs; ui.rs; renderer.rs; CLI tests and GUI smoke | root | mesh/selection returned | commands and usable controls share history/undo; existing files load |
| delivery | iteration docs; docs/NEXT-STEPS.md; scripts/scoped_handover.py | root | all verified | only owned source files committed via K-Dev; preserve pre-existing staging |

No agent stages, commits, pushes, changes worker configuration or writes outside its declared files. Root reviews returned code and reruns integration checks. All use the existing modern Rust toolchain; shared Cargo builds are serialized where possible. The runtime-selection policy was consulted; two geometry/picking leaves use high-effort judgment agents, the bounded matrix task a small research agent.

## Current acceptance inventory

- Executed K-Dev commit of our verified work, with foreign Stage entries preserved.
- Written next-step list and iterative verification/delivery loop.
- Actual delegated implementation, not merely a proposed team.
- Inset/subdivide commands with UI controls, journal and Undo.
- Vertex/edge selection and point-position editing, with actual viewport feedback.
- Linux checks and real native GUI smoke evidence.
- macOS builder readiness reported honestly; no production build/publication used as a substitute for an editor test.
