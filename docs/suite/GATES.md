# Suite foundation acceptance — 2026-11-12

This session delivers a masterplan and one implemented foundation, not the complete suite.

- [x] G1: Masterplan and subplans cover every requested domain and distinguish implemented, planned and unverified capabilities.
  CHECK: Manual review of MASTERPLAN.md, plans/*.md and SOURCES.md against the current user request.
  EXPECT: Deletion, dependencies, history, concurrency, headless actions, optional cursor, music/plugins, photo/video, CAD/print, textile/Unreal, identity and mobile are assigned milestones and acceptance examples.
- [x] G2: Rust document dependencies reject cycles and unsafe stale archive requests; preserve and cascade modes persist atomically and undo/redo correctly.
  CHECK: cd creative-core && cargo test --locked
  EXPECT: All existing and new tests pass, including archive preservation, shared inputs, legacy project migration and CLI persistence.
- [x] G3: The shared HTTP action bridge exposes the new core actions and rejects invalid operations without modifying saved state.
  CHECK: .venv/bin/python -m pytest tests/test_suite_documents.py -q
  EXPECT: Integration tests pass through the actual Rust subprocess and HTTP transport.
- [x] G4: Contract, ADR, architecture and verification report accurately describe the implemented limits; pre-existing work is preserved.
  CHECK: Manual review of scoped git diff and VERIFICATION.md.
  EXPECT: No claim of live native-app sync, CAS binary storage, real-time merge, OAuth or plug-in hosting from this first foundation.

Evidence is recorded in VERIFICATION.md and K-Harness run 20261112-153952-b8e8.
The installed unlazy skill exposes no template/checker resources in this environment; the explicit commands above and K-Harness ledger are used directly.
