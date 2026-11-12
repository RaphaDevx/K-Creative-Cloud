"""Pinned 1440x900 Linux/Xvfb interaction fixtures for iteration 0002."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import uuid

from PIL import ImageGrab

root = Path(__file__).resolve().parents[1]
binary = root / "target/debug/3d-editor"
output = root / "artifacts/gui-modeling" / ("run-" + uuid.uuid4().hex[:10])
output.mkdir(parents=True)
runtime = tempfile.TemporaryDirectory(prefix="3d-modeling-runtime-")
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
    image.save(output / name)
    return image


def fixture(name):
    path = output / (name + ".scene3d")
    group = output / (name + ".commands.json")
    subprocess.run([binary, "new", path], env=env, check=True)
    group.write_text(json.dumps({"expected_revision": 0, "actor": "gui-modeling",
                                "task_path": ["Scene"], "label": "Cube",
                                "commands": [{"action": "add", "primitive": "cube"}]}))
    subprocess.run([binary, "apply", path, group, path], env=env, check=True)
    return path


def launch(path):
    log = (output / (path.stem + ".log")).open("w")
    logs.append(log)
    process = subprocess.Popen([binary, "--scene", path], env=env, stdout=log, stderr=log)
    processes.append(process)
    for _ in range(100):
        if process.poll() is not None:
            raise AssertionError(Path(log.name).read_text())
        result = subprocess.run(["xdotool", "search", "--onlyvisible", "--pid", str(process.pid)],
                                env=env, capture_output=True, text=True)
        if result.returncode == 0:
            window = result.stdout.splitlines()[-1]
            x("windowsize", window, 1440, 900)
            x("windowfocus", "--sync", window)
            time.sleep(.8)
            x("mousemove", 1200, 161, "click", 1)  # Collapse transform fields.
            x("mousemove", 395, 53, "click", 1)  # Focus.
            x("mousemove", 478, 53, "click", 1)  # Front view.
            return process
        time.sleep(.1)
    raise AssertionError("Editor did not open")


def body_bounds():
    # Test-only screenshot measurement avoids assuming a fixed viewport height:
    # history groups can resize the bottom panel. The application uses no image
    # analysis for selection or editing; its picking is geometry-based Rust.
    image = ImageGrab.grab(xdisplay=display)
    rows = []
    for y in range(130, 720):
        run = None
        for x_pos in range(300, 1050):
            r, g, b = image.getpixel((x_pos, y))[:3]
            match = 50 < r < 160 and g > r and b > g and b-r > 4
            if match and run is None:
                run = x_pos
            if not match and run is not None:
                if x_pos-run > 100:
                    rows.append((run, x_pos-1, y))
                run = None
        if run is not None and 1050-run > 100:
            rows.append((run, 1049, y))
    assert rows, "No rendered fixture mesh found"
    return min(r[0] for r in rows), min(r[2] for r in rows), max(r[1] for r in rows), max(r[2] for r in rows)


def edit_number(x_pos, y_pos, value):
    x("mousemove", x_pos, y_pos, "click", "--repeat", 2, "--delay", 100, 1, "key", "ctrl+a")
    x("type", "--clearmodifiers", str(value))
    x("key", "Return")


def saved(path):
    x("key", "ctrl+s")
    return json.loads(path.read_text())


try:
    path = fixture("elements")
    process = launch(path)
    x("mousemove", 694, 53, "click", 1)  # Vertex mode.
    left, top, right, bottom = body_bounds()
    x("mousemove", left, top, "click", 1)
    capture("vertex-picked.png")
    edit_number(1265, 466, .7)
    x("mousemove", 1280, 527, "click", 1)
    document = saved(path)
    assert document["revision"] == 2, document["revision"]
    assert abs(document["scene"]["objects"][0]["mesh"]["positions"][7][1]-.7) < .001
    x("mousemove", 762, 53, "click", 1)  # Edge mode.
    left, top, right, bottom = body_bounds()
    x("mousemove", (left+right)//2, bottom, "click", 1)
    capture("edge-picked.png")
    edit_number(1265, 490, .1)
    x("mousemove", 1280, 557, "click", 1)
    document = saved(path)
    assert document["revision"] == 3, document["revision"]
    for index in (4, 5):
        assert abs(document["scene"]["objects"][0]["mesh"]["positions"][index][1]+.4) < .001
    capture("elements-edited.png")
    process.terminate()
    process.wait(timeout=5)

    path = fixture("faces")
    process = launch(path)
    x("mousemove", 300, 53, "click", 1)  # Face mode.
    left, top, right, bottom = body_bounds()
    x("mousemove", (left+right)//2, (top+bottom)//2, "click", 1)
    x("mousemove", 250, 15, "click", 1)
    capture("modeling-menu.png")
    x("mousemove", 292, 81, "click", 1)  # Inset via modeling menu.
    document = saved(path)
    assert document["revision"] == 2, document["revision"]
    assert len(document["scene"]["objects"][0]["mesh"]["positions"]) == 12
    assert document["history"][-1]["commands"][0]["action"] == "inset"
    capture("inset-applied.png")
    x("mousemove", 250, 15, "click", 1)
    x("mousemove", 292, 117, "click", 1)  # Whole-mesh linear subdivision.
    document = saved(path)
    assert document["revision"] == 3, document["revision"]
    assert document["history"][-1]["commands"][0]["action"] == "subdivide"
    assert len(document["scene"]["objects"][0]["mesh"]["faces"]) == 40
    capture("subdivision-applied.png")
    x("key", "ctrl+z")
    document = saved(path)
    assert len(document["scene"]["objects"][0]["mesh"]["faces"]) == 10
    x("key", "ctrl+shift+z")
    document = saved(path)
    assert len(document["scene"]["objects"][0]["mesh"]["faces"]) == 40
    result = {"ok": True, "element_revision": 3, "modeling_revision": 5,
              "subdivided_faces": 40, "artifacts": str(output)}
    (output / "result.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result))
finally:
    for process in processes:
        if process.poll() is None:
            process.terminate()
            process.wait(timeout=5)
    for log in logs:
        log.close()
    runtime.cleanup()
