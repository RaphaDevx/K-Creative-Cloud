# Iteration 0003 verification

13 November 2026. Three agents implemented independent selection/math/test leaves; root integrated and reviewed the result. A read-only review identified focus-loss drag cancellation and hidden-object reselection, both corrected before final checks.

- `scripts/check-native.sh`: formatting, headless tests, desktop Clippy with warnings denied, desktop tests all pass. **60 distinct Rust fixtures**, executed with and without the desktop feature (not counted twice). Includes 5 selection, 9 manipulation and 7 atomic group-command fixtures added this iteration.
- `python3 -m unittest discover -s 3d-editor/scripts -p test_scoped_handover.py`: **6 passed**.
- `git diff --check` and Python translation-test compilation pass.
- Final existing GUI smoke: `artifacts/gui-smoke/run-abddf393f8/result.json`; revision 5, renamed/transformed/extruded mesh, Undo/Redo, unsaved dialog, compact mode and branding preserve scene bytes.
- Modeling GUI: `artifacts/gui-modeling/run-a41ff03d68/result.json`; vertex/edge positions, inset, shared subdivision and Undo/Redo preserved. Additional instrumented debug run `gui-modeling/run-e7fa50b778` also passed.
- Translation GUI: `artifacts/gui-translation/run-e54c3ad287/result.json`. Shift-outliner selection moves two spaced cubes by X=+0.5 at revision 3; Undo/Redo revisions 4/5. Escape cancels a real axis drag at revision 5 with unchanged positions. A released drag with three mouse movements produces revision 6, exactly one `translate_objects` command and two object diffs. Shared delta approximately +0.358275 m preserves 3 m spacing. Undo/Redo revisions 7/8 reproduce exact positions. Root visually inspected the active preview screenshot.

Early GUI attempts overlapped headless/desktop debug-binary replacement; final GUI runs use the completed desktop binary. Linux Xvfb/software-GPU evidence does not establish macOS Metal, native file-dialog or iPad behavior. Dedicated Mac editor test route remains pending. No production build or publication triggered.

Source delivery uses the explicit `3d-editor` manifest and mandatory K-Dev API. Initial dry run independently retained all 122 foreign staged paths and prepared only this iteration. Actual signed receipt and final staging/remote verification follow delivery.
