# Native test matrix

This matrix separates checks that can run on a Linux developer host from checks
that need a registered macOS build/test route. The editor is a Rust desktop
application; the runtime does not require Python, Blender, Electron, or
JavaScript.

## Linux local checks

Run `./scripts/check-native.sh` from any working directory. It uses `CARGO` if
set, otherwise `cargo` from `PATH`, and runs these commands in order:

1. `cargo fmt --all -- --check` — formatting, no platform dependencies.
2. `cargo test --locked --no-default-features` — headless engine and CLI tests;
   excludes the desktop dependencies.
3. `cargo clippy --locked --all-targets -- -D warnings` — lint all default
   (desktop) targets and tests.
4. `cargo test --locked` — desktop-feature tests, last so the
   `target/debug/3d-editor` test binary remains available to the launcher.

This is a source/build check. It does not produce a release package, sign an
application, contact a builder, or claim that a real display/GPU was exercised.
Use a Rust toolchain compatible with the lockfile (Rust 1.88 or newer) and the
Linux X11/Wayland development libraries required by `eframe`/`wgpu`.

### Linux GUI interaction

With the desktop test binary built, run the separate interactive smoke test:

```bash
xvfb-run -a -s "-screen 0 1440x900x24" ../.venv/bin/python scripts/gui_smoke.py
```

It needs Xvfb, xdotool, Pillow in the project's `.venv`, and a software OpenGL
stack. It drives actual mouse and keyboard events and writes screenshots and
fixtures under `artifacts/gui-smoke/`. This validates the Linux window and
interaction flow under a virtual display, not the native OS file chooser or
physical GPU drivers. `scripts/gui_modeling_smoke.py` additionally checks vertex/edge editing, inset and subdivision. `scripts/gui_translation_smoke.py` checks Shift multiselection, shared numeric translation, Undo/Redo, Escape cancellation, a released axis drag producing exactly one revision and group Undo/Redo. Run these after the source checks have finished: headless test compilation replaces the shared debug binary. On a desktop session it can also be run directly with the
same Python script and a valid `DISPLAY`.

## macOS checks still requiring builder registration

The currently visible K-Dev build registry has a production DMG script route
for `kcreative`; it does not expose a dedicated Rust 3d-editor test job. The
macOS rows below therefore remain pending until K-Dev registers a non-release
test route for this crate. Do not infer that a production DMG build is a test
run or trigger one to verify source changes.

| Check | Linux local | macOS builder route needed |
|---|---|---|
| Rust formatting, headless tests, Clippy | Yes | No |
| Desktop-feature compile and tests | Yes | Yes, to validate macOS target compilation |
| GUI startup and basic editor interactions | Xvfb software-GPU smoke | Native macOS window/event loop on the registered runner |
| Native open/save dialogs and app integration | No | Yes, with native dialog interaction |
| Metal-backed rendering / real Mac GPU behavior | No | Yes, on supported Mac hardware |
| Signing, notarization, DMG packaging, production release | No | K-Dev release pipeline only, when explicitly requested |

Once a dedicated route exists, capture its toolchain/OS version, command, exit
status, logs, and GUI evidence in the handover. Source checks and a passing
Linux virtual-display smoke are not evidence of native macOS dialog, Metal, or
hardware behavior.
