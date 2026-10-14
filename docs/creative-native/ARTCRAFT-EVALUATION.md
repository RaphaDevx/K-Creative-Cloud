# ArtCraft evaluation register

14 October 2026. Source review only; neither engine installed, compiled, benchmarked or accepted. Existing renderers and native editor allowlist remain the defaults.

| Candidate | Reviewed commit | Workspace version | Declared license | Minimum Rust |
| --- | --- | --- | --- | --- |
| PhotoCraft | ed7df56a2455375240959bae6e5273a71d858d84 | 0.8.2 | MIT OR Apache-2.0 | 1.95 |
| FilmCraft | cee1feb185e675a108f78067f71ad86a640ace3d | 0.7.2 | MIT OR Apache-2.0 | 1.95 |

Sources: [PhotoCraft Cargo.toml](https://github.com/storytold/photocraft/blob/ed7df56a2455375240959bae6e5273a71d858d84/Cargo.toml), [PhotoCraft README](https://github.com/storytold/photocraft/blob/ed7df56a2455375240959bae6e5273a71d858d84/README.md), [FilmCraft Cargo.toml](https://github.com/storytold/filmcraft/blob/cee1feb185e675a108f78067f71ad86a640ace3d/Cargo.toml), [FilmCraft README](https://github.com/storytold/filmcraft/blob/cee1feb185e675a108f78067f71ad86a640ace3d/README.md). These are upstream declarations, not an independent license or fidelity audit.

Both describe a CLI, MCP and a desktop control channel; PhotoCraft describes a headless MCP mode and FilmCraft documents filmcraft-cli mcp as headless. Linux support is documented. Both reference shared craft-libs git dependencies; native UI/GPU and codec dependencies must be reviewed per selected binary/target before any build. FilmCraft explicitly reports less real-world testing on Windows/Linux than macOS. No README commands were executed.

## Acceptance required before an adapter can be enabled

1. Lock the engine and dependency revisions, inspect binary/target dependencies and license notices. Verify CLI help and command schemas in an isolated workspace with timeouts.
2. Photo: copy layered PSDs and image fixtures; compare layers, masks, text, color profiles, PNG exports and PSD save/reopen against GIMP/Pillow, preserving source files. Record pixel/color differences and unsupported features.
3. Video: copy mixed audio/video fixtures; compare cuts, duration/frame count, subtitles, audio synchronization and playable MP4 against Kdenlive/FFmpeg. Verify outputs with ffprobe and decoded frames/audio.
4. Measure wall time, peak memory, stability and failure/timeout behavior on the same host and fixtures. Keep reports and checksums with engine revisions.
5. Only add a confined, typed adapter when a concrete advantage is demonstrated. Keep the established fallback. Add representative export tests and acceptance_evidence before changing review_status to accepted.

Runtime comparison, full voiceover reel and real Excel browser automation remain follow-up production tasks. Screen recording retains the canonical Calc/UNO adapter (never label Calc as Excel). No course publication or storage upload is included in this dashboard integration.
