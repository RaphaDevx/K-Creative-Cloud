# Creative assistant acceptance gates

- G1: Existing layer actions remain compatible; ellipse/polygon geometry and atomic revision-guarded batches validate, persist and undo in Rust.
  CHECK: cargo test --manifest-path creative-core/Cargo.toml --locked
  EXPECT: test result: ok
- G2: Planner contracts reject unsupported commands, stale plans, path escapes and invalid geometry; clarification/help causes no mutation; sketch attachment and provider errors are explicit.
  CHECK: .venv/bin/python -m pytest -q tests
  EXPECT: passed
- G3: UI supports text, microphone/local transcription, drawn/uploaded sketch, clarification replies, help, apply and undo; actual sphere adapter writes .blend and render.
  MANUAL: Browser interaction plus actual model/sketch and Blender export fixture evidence. Hardware microphone and missing provider/model limits must be reported.
- G4: A separate skill teaches the real supported workflow, asks material clarification, distinguishes offline/integrated/native claims and does not fabricate readiness.
  MANUAL: Validate frontmatter and execute representative skill scenarios.
- G5: Sources are reviewed and checked without overwriting pre-existing dirty work; no release/readiness claim exceeds evidence.
  MANUAL: Scoped diff, regression results and final limitations reconciled.

- G6: Brand briefs/presets create validated editable identity; exports use portable semantic tokens/CSS/docs and the social-media template; imports are stale-safe and undoable; existing tool edits survive exports.
  CHECK: .venv/bin/python -m pytest -q tests/test_creative_brand.py
  EXPECT: passed
