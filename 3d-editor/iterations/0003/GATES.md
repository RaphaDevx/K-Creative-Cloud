# Iteration 0003 gates

- [x] G1 Selection: deterministic multiselection with active object, toggle and prune.
  CHECK: cargo test --locked --no-default-features --test object_selection
  EXPECT: All state/visibility/removal fixtures pass.
- [x] G2 Math: projected handles, ray-based axis drag and relative snapping are stable across views and zoom.
  CHECK: cargo test --locked --no-default-features --test manipulation
  EXPECT: Direction, zero-start, parallel/invalid cases and world bounds pass.
- [x] G3 Commands: group translation is atomic, bounded and persisted with one Undo.
  CHECK: cargo test --locked --no-default-features --test group_translation
  EXPECT: Relative spacing, snapping, stale/missing/duplicate IDs and limits tested.
- [x] G4 UI: shift selection, numeric movement, gizmo commit/cancel and previous modeling flows work in a real GPU window.
  CHECK: scripts/check-native.sh plus explicit GUI smoke runs.
  EXPECT: Rust tests, fmt, Clippy and real GUI evidence pass; no hidden document mutation during preview.
- [ ] G5 Delivery: reviewed source committed through K-Dev, foreign staging restored and remote verified.
  CHECK: Manual comparison of API receipt, tree/file scope, original staged blobs and remote HEAD.
  EXPECT: Signed commit(s) to kdev, own scope clean, no release publication.
