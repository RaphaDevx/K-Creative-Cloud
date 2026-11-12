"""Native GUI verification helper; application runtime itself does not use Python.

Run inside an isolated 1440x900 Xvfb display with Pillow and xdotool installed.
Only fixtures in a fresh artifact directory are modified.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
import time
import uuid

from PIL import ImageGrab

parser = argparse.ArgumentParser()
parser.add_argument("--binary", type=Path, default=Path("target/debug/3d-editor"))
parser.add_argument("--output", type=Path, default=Path("artifacts/gui-smoke"))
args = parser.parse_args()
binary = args.binary.resolve()
output = args.output.resolve() / ("run-" + uuid.uuid4().hex[:10])
output.mkdir(parents=True)
display = os.environ["DISPLAY"]
runtime = tempfile.TemporaryDirectory(prefix="3d-editor-runtime-")
env = {**os.environ, "LIBGL_ALWAYS_SOFTWARE": "1", "XDG_RUNTIME_DIR": runtime.name}
processes = []
logs = []


def x(*arguments):
    result = subprocess.run(["xdotool", *map(str, arguments)], env=env,
                            check=True, text=True, capture_output=True)
    time.sleep(0.18)
    return result.stdout.strip()


def capture(name, width=1440, height=900):
    image = ImageGrab.grab(bbox=(0, 0, width, height), xdisplay=display)
    image.save(output / name)
    assert len(image.getcolors(image.width * image.height) or []) > 50


def start(label, *arguments):
    log = (output / (label + ".log")).open("w")
    logs.append(log)
    process = subprocess.Popen([str(binary), *map(str, arguments)], env=env,
                               stdout=log, stderr=log)
    processes.append(process)
    for _ in range(100):
        if process.poll() is not None:
            raise AssertionError(f"GUI exited: {(output / (label + '.log')).read_text()}")
        found = subprocess.run(["xdotool", "search", "--onlyvisible", "--pid", str(process.pid)],
                               env=env, capture_output=True, text=True)
        if found.returncode == 0:
            window = found.stdout.splitlines()[-1]
            x("windowsize", window, 1440, 900)
            x("windowfocus", "--sync", window)
            time.sleep(0.8)
            return process, window
        time.sleep(0.1)
    raise AssertionError("No visible editor window")


def stop(process):
    process.terminate()
    process.wait(timeout=5)


try:
    startup, _ = start("startup")
    capture("startup-neutral.png")
    x("mousemove", 345, 440, "click", 1)
    capture("new-scene.png")
    stop(startup)

    scene = output / "fixture.scene3d"
    batch = output / "fixture.commands.json"
    subprocess.run([str(binary), "new", str(scene)], check=True, env=env)
    batch.write_text(json.dumps({
        "expected_revision": 0, "actor": "gui-fixture", "task_path": ["Scene"],
        "label": "Wuerfel erstellen", "commands": [{"action": "add", "primitive": "cube"}]
    }))
    subprocess.run([str(binary), "apply", str(scene), str(batch), str(scene)], check=True, env=env)
    editor, window = start("workspace", "--scene", scene)
    x("mousemove", 1270, 118, "click", 1, "key", "ctrl+a")
    # xdotool type consumes remaining arguments; run it as a separate invocation.
    x("type", "--clearmodifiers", "Testkoerper")
    x("mousemove", 1210, 221, "click", "--repeat", 2, "--delay", 100, 1, "key", "ctrl+a")
    x("type", "--clearmodifiers", "0.6")
    x("key", "Return")
    x("mousemove", 1290, 491, "click", 1)
    x("mousemove", 1200, 161, "click", 1)  # Collapse properties.
    x("mousemove", 395, 53, "click", 1)  # Focus selection.
    x("mousemove", 300, 53, "click", 1)  # Face mode.
    x("mousemove", 680, 415, "click", 1)  # Actual ray selection.
    x("mousemove", 1290, 527, "click", 1)  # Extrude.
    x("key", "ctrl+z")
    x("key", "ctrl+shift+z")
    x("key", "ctrl+n")
    capture("unsaved-dialog.png")
    x("key", "Escape")
    assert json.loads(scene.read_text())["revision"] == 1
    x("key", "ctrl+s")
    document = json.loads(scene.read_text())
    obj = document["scene"]["objects"][0]
    assert document["revision"] == 5, document["revision"]
    assert obj["name"] == "Testkoerper"
    assert abs(obj["transform"]["translation"][0] - 0.6) < 0.001
    assert (len(obj["mesh"]["positions"]), len(obj["mesh"]["faces"])) == (12, 10)
    assert [entry["kind"] for entry in document["history"]][-2:] == ["undo", "redo"]
    capture("workspace-neutral.png")
    x("windowsize", window, 960, 640)
    capture("workspace-compact.png", 960, 640)
    stop(editor)

    before = scene.read_bytes()
    reopened, _ = start("reopened", "--scene", scene)
    capture("reopened.png")
    stop(reopened)
    assert scene.read_bytes() == before

    brand = json.loads((Path(__file__).resolve().parents[1] / "branding/neutral.json").read_text())
    brand.update(app_name="Branding-Test", wordmark="STUDIO", monogram="ST",
                 launch_line="Deine Marke. Deine Werkzeuge.", workspace_signature="STUDIO / 3d-editor",
                 accent=[211, 176, 130], launch_background=[29, 27, 30])
    profile = output / "branding-test.json"
    profile.write_text(json.dumps(brand))
    branded, _ = start("branded-startup", "--brand", profile)
    capture("startup-branded.png")
    stop(branded)
    branded_editor, _ = start("branded-workspace", "--brand", profile, "--scene", scene)
    capture("workspace-branded.png")
    stop(branded_editor)
    assert scene.read_bytes() == before

    for log in logs:
        log.flush()
        text = Path(log.name).read_text()
        assert "panicked at" not in text and "Validation Error" not in text, text
    result = {"ok": True, "revision": 5, "vertices": 12, "faces": 10,
              "scene_bytes_unchanged_by_brand": True, "artifacts": str(output)}
    (output / "result.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result))
finally:
    for process in processes:
        if process.poll() is None:
            stop(process)
    for log in logs:
        log.close()
    runtime.cleanup()
