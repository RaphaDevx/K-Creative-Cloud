# 3d-editor initial implementation gates

Scope: a native Rust editor with real editable meshes, not Blender feature parity.

- [x] G1 Architecture: independent Rust scene engine, no Blender/Python/JS runtime, neutral branding slots and explicit migration direction documented.
  CHECK: Manual review of ARCHITECTURE.md, branding/neutral.json and ADR 0007.
  EXPECT: Existing engines retained as optional compatibility paths; branding changes no scene data.
- [x] G2 Headless engine: grouped commands, persistent journal, mesh extrusion, picking, import/export, validation and undo/redo work.
  CHECK: cargo test --locked --no-default-features
  EXPECT: All core and CLI integration tests pass including invalid input/no writes and geometric fixtures.
- [x] G3 Desktop: native GPU-backed editor compiles and runs; startup, scene selection, transforms, extrusion, save/reopen and neutral/alternate identity are exercised.
  CHECK: cargo test --locked
  EXPECT: Desktop target and integration tests pass. Manual GUI smoke uses Xvfb and actual pointer/keyboard events with screenshots.
- [x] G4 Review: tests, screenshots, supported features, limits and isolated handover recorded.
  CHECK: Manual review of VERIFICATION.md, README.md, ROADMAP.md and scoped diff.
  EXPECT: No claim of full Blender replacement, mobile readiness or distributed merge; foreign staged work preserved.

Use the available Rust 1.98 toolchain for checks; system Rust 1.75 is too old for the native UI dependencies. No global toolchain is changed. Release packaging/build/signing remain K-Dev-owned.
