# 3d-editor v0.1 verification

12 November 2026. Ledger: `20261112-160731-ab4c`.

This report records the initial 14-test milestone. The subsequent [iteration 0002](iterations/0002/VERIFICATION.md) expands the editor to 39 distinct Rust tests plus new modeling GUI checks and records the executed source handover.

## Automated source checks

- `cargo test --locked --no-default-features`: 14 tests pass, comprising 12 engine and 2 real-process CLI tests. Headless CLI runs with DISPLAY removed.
- `cargo test --locked`: the same 14 tests pass with the desktop target compiled. These are 14 distinct tests, not 28.
- `cargo clippy --locked --all-targets -- -D warnings`: passes with no warnings.
- `cargo fmt --all -- --check`: passes.
- `./3d-editor/start.sh --help`: executable launcher finds the desktop testbinary and exposes the documented commands.

Checks use the existing Rust 1.98.1 toolchain explicitly. Dependencies are pinned in Cargo.lock; no global toolchain setting changed. No release/package build was performed.

## Engine evidence

Solid cube/sphere/cylinder fixtures have outward-facing polygons and exactly two oppositely directed uses of each edge. Face extrusion retains a closed cube-derived surface and generates 12 vertices/10 faces from 8/6. Undo restores exact geometry and IDs; redo restores the edit and advances revision.

Invalid/stale groups, invalid transforms, missing IDs, invalid indices and failed mesh edits preserve scene and history. Concave, nonplanar and self-intersecting star polygons are rejected. OBJ negative indices and baked world transforms tested. Atomic scene writes reload editable meshes, undo state and journal; unsupported schemas leave existing files unchanged. Picking respects geometry, world transforms, nearest hit and visibility. CPU frustum clipping prevents behind-eye grid artifacts found during actual GPU review.

Headless CLI tested across actual processes: create → grouped edit → inspect full scene/history → reject stale overwrite → undo → redo → OBJ export. No display or external media engine is needed.

## Native interaction evidence

`scripts/gui_smoke.py` drives the real desktop app with xdotool in an isolated Xvfb display. It captures unmodified screenshots and parses the scene saved by the GUI:

1. Neutral startup renders; New Scene creates a real cube.
2. A separate saved fixture is opened; the name becomes `Testkoerper` and X position becomes 0.6 via inspector inputs and Apply.
3. Viewport focus, face mode and actual pointer ray selection; Extrude adds real topology.
4. Ctrl+Z/Ctrl+Shift+Z, new-document unsaved modal, Escape cancellation and Ctrl+S.
5. Saved file independently confirms revision 5, 12 vertices, 10 faces and undo/redo journal entries; separate process reopens it.
6. 960×640 workspace reviewed; toolbars wrap and inspector/history remain scrollable.
7. A test-only alternate brand changes startup identity, title, UI selection/viewport accent and workspace signature; original scene bytes remain identical.

Final successful run: `artifacts/gui-smoke/run-637bef6dca/result.json`. Screenshots include startup-neutral, workspace-neutral, workspace-compact, unsaved-dialog, reopened, startup-branded and workspace-branded. Test branding is an illustration, not a selected product brand. The embedded default remains exactly `3d-editor`.

Visual checks led to fixes for startup layout overflow, software-GPU grid clipping, true modal input blocking and selected-row text contrast. Neutral profile contrast measured independently from RGB: 9.93:1 selected text/background and 15.85:1 startup text/background. This is not a full screen-reader or target-platform accessibility certification.

## Measured limits

Verified Linux/X11 with Xvfb and software GPU. macOS/Windows/iPad, real GPU performance, platform-native file dialogs and accessibility hardware/services remain unverified. The smoke uses saving to an existing scene path; it does not claim native dialog coverage.

Application code is Rust with WGSL shaders; OS/GPU libraries and dependencies remain native platform components. Python/Pillow/xdotool are test tools only. No Blender/Python/JS process is used by the editor runtime.

No Blender parity, .blend importer, robust general topology solver, UV/texturing, rigging, animation, physics, CAD/print guarantees, plugin host, model-provider UI, distributed merge or live Suite graph adapter is implemented. History is persisted but neither cryptographically authenticated nor append-only on disk; checkpoints and geometry still reside in bounded JSON. Actor is local metadata. Inspector edits require Apply. Detailed capabilities and next milestones are in README.md and ROADMAP.md.

## Acceptance and handover

G1–G4 are met for this first usable milestone. The subsequent iteration committed this source and Suite foundation via K-Dev as `f8dc0f7547b7900a97714a83719e777be1371f7a`, signed and pushed to `kdev`; 122 foreign staged paths retained. Release packaging remains separate. See HANDOVER.md. No complete Blender replacement or published download is claimed.
