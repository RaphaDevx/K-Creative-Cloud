"""Exercise multi-object translation, undo/redo, and cancelled gizmo drag on Linux/Xvfb."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import uuid

from PIL import ImageGrab

ROOT = Path(__file__).resolve().parents[1]
BINARY = ROOT / "target/debug/3d-editor"
if not BINARY.is_file():
    raise SystemExit(f"Editor test binary is not ready: {BINARY}")
OUTPUT = ROOT / "artifacts/gui-translation" / ("run-" + uuid.uuid4().hex[:10])
OUTPUT.mkdir(parents=True)
runtime = tempfile.TemporaryDirectory(prefix="3d-translation-runtime-")
env = {**os.environ, "XDG_RUNTIME_DIR": runtime.name, "LIBGL_ALWAYS_SOFTWARE": "1"}
display = env["DISPLAY"]
processes = []
logs = []


def x(*args):
    result = subprocess.run(["xdotool", *map(str, args)], env=env, check=True,
                            capture_output=True, text=True)
    time.sleep(.2)
    return result.stdout.strip()


def capture(name):
    image = ImageGrab.grab(xdisplay=display)
    image.save(OUTPUT / name)
    return image


def make_fixture():
    scene = OUTPUT / "two-cubes.scene3d"
    commands = OUTPUT / "two-cubes.commands.json"
    subprocess.run([BINARY, "new", scene], env=env, check=True)
    # IDs are assigned by the add commands, so make two groups: add, inspect IDs,
    # then set their initial positions in a second atomic CLI apply.
    commands.write_text(json.dumps({
        "expected_revision": 0, "actor": "gui-translation-smoke",
        "task_path": ["Scene"], "label": "Zwei Würfel erstellen",
        "commands": [{"action": "add", "primitive": "cube"},
                     {"action": "add", "primitive": "cube"}]
    }))
    subprocess.run([BINARY, "apply", scene, commands, scene], env=env, check=True)
    inspect = subprocess.run([BINARY, "inspect", scene], env=env, check=True,
                             capture_output=True, text=True)
    document = json.loads(inspect.stdout)
    ids = [obj["id"] for obj in document["scene"]["objects"]]
    positions = OUTPUT / "positions.commands.json"
    positions.write_text(json.dumps({
        "expected_revision": document["revision"],
        "actor": "gui-translation-smoke", "task_path": ["Scene"],
        "label": "Würfel auseinanderstellen",
        "commands": [
            {"action": "transform", "id": ids[0], "transform": {
                "translation": [-1.5, 0.0, 0.0], "rotation_degrees": [0, 0, 0], "scale": [1, 1, 1]}},
            {"action": "transform", "id": ids[1], "transform": {
                "translation": [1.5, 0.0, 0.0], "rotation_degrees": [0, 0, 0], "scale": [1, 1, 1]}}
        ]
    }))
    subprocess.run([BINARY, "apply", scene, positions, scene], env=env, check=True)
    return scene, ids


def launch(scene):
    log = (OUTPUT / "editor.log").open("w")
    logs.append(log)
    process = subprocess.Popen([BINARY, "--scene", scene], env=env,
                               stdout=log, stderr=log)
    processes.append(process)
    for _ in range(100):
        if process.poll() is not None:
            raise AssertionError(Path(log.name).read_text())
        result = subprocess.run(["xdotool", "search", "--onlyvisible", "--pid",
                                 str(process.pid)], env=env, capture_output=True,
                                text=True)
        if result.returncode == 0:
            window = result.stdout.splitlines()[-1]
            x("windowsize", window, 1440, 900)
            x("windowfocus", "--sync", window)
            time.sleep(1.)
            return process
        time.sleep(.1)
    raise AssertionError("Editor window did not appear")


def saved(scene):
    x("key", "ctrl+s")
    return json.loads(scene.read_text())


def group_positions(document):
    return [obj["transform"]["translation"] for obj in document["scene"]["objects"]]


def find_red_gizmo(image):
    # The X handle is the dominant red horizontal segment. Choose an interior
    # point on its longest row segment to avoid both the pivot and arrow tip.
    best = None
    for y in range(130, min(810, image.height)):
        runs = []
        start = None
        for px in range(260, min(1120, image.width)):
            r, g, b = image.getpixel((px, y))[:3]
            match = r > 190 and 35 < g < 155 and 35 < b < 170 and r - g > 70
            if match and start is None:
                start = px
            elif not match and start is not None:
                runs.append((start, px - 1, y))
                start = None
        if start is not None:
            runs.append((start, min(1119, image.width - 1), y))
        for run in runs:
            if best is None or run[1] - run[0] > best[1] - best[0]:
                best = run
    if best is None or best[1] - best[0] < 18:
        raise AssertionError("Could not locate the rendered red X gizmo; inspect gizmo-before-cancel.png")
    left, right, y = best
    return (left + right) // 2, y


try:
    scene, ids = make_fixture()
    process = launch(scene)
    # Outliner rows begin below the scene header and add-object button. Select
    # the second row, then Shift-click the first to exercise additive selection.
    x("mousemove", 90, 220, "click", 1)
    x("keydown", "shift")
    x("mousemove", 90, 190, "click", 1)
    x("keyup", "shift")
    capture("outliner-multiselection.png")

    # Multi-selection inspector controls: X/Y/Z DragValues and apply button.
    x("mousemove", 1198, 147, "click", "--repeat", 2, "--delay", 100, 1,
      "key", "ctrl+a")
    x("type", "--clearmodifiers", "0.5")
    x("key", "Return")
    x("mousemove", 1235, 255, "click", 1)
    document = saved(scene)
    assert document["revision"] == 3, document["revision"]
    translated = group_positions(document)
    assert len(translated) == 2
    assert all(abs(p[0] - initial) < .002
               for p, initial in zip(translated, [-1.0, 2.0])), translated
    capture("group-translated.png")

    x("key", "ctrl+z")
    undone = saved(scene)
    assert undone["revision"] == 4, undone["revision"]
    assert all(abs(p[0] - initial) < .002
               for p, initial in zip(group_positions(undone), [-1.5, 1.5]))
    x("key", "ctrl+shift+z")
    redone = saved(scene)
    assert redone["revision"] == 5, redone["revision"]
    assert all(abs(p[0] - initial) < .002
               for p, initial in zip(group_positions(redone), [-1.0, 2.0]))

    # Front camera makes X horizontal. Drag the detected X shaft, then Escape
    # while held and release; cancellation must leave the revision unchanged.
    x("mousemove", 478, 53, "click", 1)
    image = capture("gizmo-before-cancel.png")
    start_x, start_y = find_red_gizmo(image)
    x("mousemove", start_x, start_y, "mousedown", 1)
    x("mousemove", start_x + 36, start_y)
    time.sleep(.3)
    capture("gizmo-active.png")
    x("key", "Escape")
    time.sleep(.3)
    x("mouseup", 1)
    cancelled = saved(scene)
    assert cancelled["revision"] == 5, cancelled["revision"]
    assert all(abs(p[0] - initial) < .002
               for p, initial in zip(group_positions(cancelled), [-1.0, 2.0]))

    # The next gesture is released normally: exactly one revision and two
    # object diffs, independent of the number of intermediate motion events.
    start_x, start_y = find_red_gizmo(capture("gizmo-before-commit.png"))
    x("mousemove", start_x, start_y, "mousedown", 1)
    for displacement in (12, 24, 48):
        x("mousemove", start_x + displacement, start_y)
    assert json.loads(scene.read_text())["revision"] == 5
    capture("gizmo-preview.png")
    x("mouseup", 1)
    committed = saved(scene)
    assert committed["revision"] == 6, committed["revision"]
    positions = group_positions(committed)
    delta = positions[0][0] + 1.0
    assert delta > .1, positions
    assert abs(positions[1][0] - 2.0 - delta) < .0001, positions
    assert positions[0][1:] == positions[1][1:] == [0., 0.]
    entry = committed["history"][-1]
    assert len(entry["commands"]) == 1 and len(entry["changes"]) == 2
    assert entry["commands"][0]["action"] == "translate_objects"
    capture("gizmo-committed.png")
    x("key", "ctrl+z")
    restored = saved(scene)
    assert restored["revision"] == 7
    assert group_positions(restored) == group_positions(cancelled)
    x("key", "ctrl+shift+z")
    final = saved(scene)
    assert final["revision"] == 8
    assert group_positions(final) == positions

    for log in logs:
        log.flush()
        text = Path(log.name).read_text()
        assert "panicked at" not in text and "Validation Error" not in text, text
    result = {
        "ok": True, "objects": ids, "group_revision": 3,
        "undo_revision": 4, "redo_revision": 5,
        "escape_cancel_revision": cancelled["revision"],
        "gizmo_commit_revision": committed["revision"],
        "final_revision": final["revision"], "final_positions": group_positions(final),
        "gizmo_drag_start": [start_x, start_y], "artifacts": str(OUTPUT)
    }
    (OUTPUT / "result.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result))
finally:
    for process in processes:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=5)
    for log in logs:
        log.close()
    runtime.cleanup()
