# Iteration 0002 acceptance

- [ ] G1 — Geometry: inset/subdivide validate and fail atomically, shared edges preserved.
  CHECK: cargo test --locked --no-default-features --test modeling
  EXPECT: All fixtures pass, including manifold and rejection cases.
- [ ] G2 — Selection: points/edges are picked in logical pixels with visibility, occlusion and transformed scene support.
  CHECK: cargo test --locked --no-default-features --test selection
  EXPECT: All selection fixtures pass.
- [ ] G3 — Integration: commands, persistence and GUI all use the same state/undo contract; previous flows retained.
  CHECK: scripts/check-native.sh
  EXPECT: fmt, headless tests, Clippy and desktop tests pass; separate GUI smoke verifies actual new controls.
- [ ] G4 — Delivery: own files committed via K-Dev, pre-existing foreign staged entries retained, no unintended release.
  CHECK: Manual verification of API response, commit file scope and before/after index entries.
  EXPECT: Commit ID and actual push result recorded; no direct git commit/push.
- [ ] G5 — Planning: NEXT-STEPS and test matrix show order, acceptance and real Mac prerequisites.
  CHECK: Manual review against current user request and live builder metadata.
  EXPECT: Source checks distinguished from native Metal/dialog/hardware tests.
