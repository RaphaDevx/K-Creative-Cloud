# K-Dev handover — independent Rust 3d-editor v0.1

## Review scope

- All non-ignored sources/docs under `3d-editor/`, including Cargo.lock, neutral brand profile, launcher and test helper. Never stage `target/` or `artifacts/`.
- `docs/adr/0007-independent-rust-3d-editor.md`.
- Additive native-editor sections in root `ARCHITECTURE.md` and `README.md`.
- Direction-change notes in `docs/suite/MASTERPLAN.md` and `docs/suite/plans/05-cad-3d.md`.

The Suite masterplan/docs and some architecture additions originated in the previous local P0 foundation, also pending handover. Coordinate with `docs/suite/HANDOVER.md`; do not silently commit a partial dependency set or unrelated Brand changes.

## Status

Source implementation and local verification complete. No release build, commit, push or handover API was triggered. The shared Git index already contains unrelated Brand moves; the inspected handover route has no file-selection argument. Existing index entries and user work remain unchanged. The builder session must isolate the review scope before invoking the mandatory K-Dev `POST /api/handover` for project `kcreative`.

Suggested message: `Start independent Rust 3d-editor with editable meshes and brand profiles`.

## Build inputs

Rust >=1.88 for locked dependencies; verified toolchain on this host is 1.98.1 under `/home/raphael/.rustup/toolchains/stable-x86_64-unknown-linux-gnu/bin`. Do not silently use system Rust 1.75 or change global toolchain settings. Native default features include desktop; a `--no-default-features` binary is headless only. GPU/window-system and platform file-dialog dependencies are required by the desktop package.

Release packaging is a new native Rust app target, not the existing Electron wrapper. Register its signing/package identity and neutral app icon in K-Dev before distribution. No iPad/macOS/Windows runtime verification or OAuth/provider setup is implied. See VERIFICATION.md and ROADMAP.md.
