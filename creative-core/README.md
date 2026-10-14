# Creative Core

Rust authority for the Creative Native v1 contract. Build with `cargo build --release --locked`, test with `cargo test --locked`.

Invoke `creative-core --store DIRECTORY` with one JSON command on stdin. Stdout contains one response object. Errors return nonzero status and `{ "ok": false, "error": "..." }`. `system.actions` returns canonical parameter JSON Schemas; its result is an array. GUI and MCP use these same actions through the Python bridge.

Projects use UUID filenames. Each JSON file stores the current canonical project plus persisted undo/redo snapshots. Changes are validated before persistence. Writes use a unique temporary file, file sync, atomic rename, and directory sync. Revisions increase monotonically, including undo/redo. Undo history retains 100 mutations. A new edit clears redo.

The host bridge must serialize invocations against each store; this CLI intentionally does not act as a concurrent server. Asset filesystem access/confinement belongs to the host bridge. The core stores asset references and verifies clip references; it never opens imported media.

Clip splits accept absolute timeline time strictly inside the clip. The left clip retains its ID. The right clip gets a new ID and advances its source offset by the left segment's duration.
