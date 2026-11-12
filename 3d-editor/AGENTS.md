# 3d-editor development

Follow `/storage/Public/K-Dev/AGENTS.md`. Native application code lives here; existing Suite/Brand work elsewhere is not part of a default editor change.

- Read ARCHITECTURE.md and the root ADRs before changing scene/command/persistence contracts.
- User preference: continue in bounded, verified iterations and commit finished steps directly through the mandatory K-Dev handover. Never run direct git commit/push; no production release implied.
- Preserve unrelated staged work. `scripts/scoped_handover.py` preflights an alternate index and a two-tree merge, with private recovery snapshots and independent restoration checks. Use an explicit reviewed path manifest and `--exclusive-git-window` only after coordinating all project Git writers. Its guard serializes this helper, not arbitrary external Git operations; signer-side immutable-tree support would be required for a general concurrent-writer guarantee. Unknown/timeout signer outcomes keep staging isolated for recovery.
- Delegate independent tasks only when authorized, with exact file ownership; root integrates and verifies returned work. Never have subagents stage or commit.
- Run scripts/check-native.sh with the supported modern Rust toolchain, and GUI smoke for UI changes. Linux results do not establish macOS Metal/dialog/device behavior.
- A Mac builder test needs a specifically registered editor route. Do not use the existing production DMG path as an implicit test or publication.
- Keep default name/branding neutral; branding profiles change application identity, never user materials/geometry.
