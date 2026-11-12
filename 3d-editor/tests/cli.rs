use serde_json::{json, Value};
use std::{fs, process::Command};

#[test]
fn real_cli_edits_without_display_and_keeps_failed_output_unchanged() {
    let dir = std::env::temp_dir().join(format!("editor-3d-cli-{}", uuid::Uuid::new_v4()));
    fs::create_dir(&dir).unwrap();
    let scene = dir.join("scene.scene3d");
    let batch = dir.join("commands.json");
    let output = dir.join("output.scene3d");
    let call = |args: &[&std::ffi::OsStr]| {
        Command::new(env!("CARGO_BIN_EXE_3d-editor"))
            .env_remove("DISPLAY")
            .args(args)
            .output()
            .unwrap()
    };
    assert!(call(&["new".as_ref(), scene.as_os_str()]).status.success());
    fs::write(&batch,serde_json::to_vec(&json!({"expected_revision":0,"actor":"headless-fixture","task_path":["Modell","Grundkörper"],"label":"Grundkörper erstellen","commands":[{"action":"add","primitive":"cube"},{"action":"add","primitive":"sphere"}]})).unwrap()).unwrap();
    let edited = call(&[
        "apply".as_ref(),
        scene.as_os_str(),
        batch.as_os_str(),
        output.as_os_str(),
    ]);
    assert!(
        edited.status.success(),
        "{}",
        String::from_utf8_lossy(&edited.stderr)
    );
    let inspection = call(&["inspect".as_ref(), output.as_os_str()]);
    let inspected: Value = serde_json::from_slice(&inspection.stdout).unwrap();
    assert_eq!(inspected["objects"], 2);
    assert_eq!(inspected["scene"]["objects"].as_array().unwrap().len(), 2);
    assert_eq!(inspected["revision"], 1);
    assert_eq!(
        inspected["history"][0]["changes"].as_array().unwrap().len(),
        2
    );
    let before = fs::read(&output).unwrap();
    let stale = call(&[
        "apply".as_ref(),
        output.as_os_str(),
        batch.as_os_str(),
        output.as_os_str(),
    ]);
    assert!(!stale.status.success());
    assert_eq!(fs::read(&output).unwrap(), before);
    let error: Value = serde_json::from_slice(&stale.stderr).unwrap();
    assert_eq!(error["ok"], false);
    let obj = dir.join("scene.obj");
    assert!(
        call(&["undo".as_ref(), output.as_os_str(), output.as_os_str()])
            .status
            .success()
    );
    assert_eq!(
        editor_3d::persistence::load(&output)
            .unwrap()
            .scene
            .objects
            .len(),
        0
    );
    assert!(
        call(&["redo".as_ref(), output.as_os_str(), output.as_os_str()])
            .status
            .success()
    );
    assert_eq!(editor_3d::persistence::load(&output).unwrap().revision, 3);
    assert!(
        call(&["export-obj".as_ref(), output.as_os_str(), obj.as_os_str()])
            .status
            .success()
    );
    assert!(fs::read_to_string(obj).unwrap().contains("f "));
    fs::remove_dir_all(dir).unwrap();
}

#[test]
fn unknown_commands_and_future_scene_versions_fail_clearly() {
    let result = Command::new(env!("CARGO_BIN_EXE_3d-editor"))
        .arg("unknown")
        .output()
        .unwrap();
    assert!(!result.status.success());
    assert!(
        serde_json::from_slice::<Value>(&result.stderr).unwrap()["error"]
            .as_str()
            .unwrap()
            .contains("--help")
    );
}
