use serde_json::{json, Value};
use std::{
    io::Write,
    process::{Command, Stdio},
};
fn call(store: &std::path::Path, input: &str) -> (bool, Value) {
    let mut p = Command::new(env!("CARGO_BIN_EXE_creative-core"))
        .arg("--store")
        .arg(store)
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .spawn()
        .unwrap();
    p.stdin.take().unwrap().write_all(input.as_bytes()).unwrap();
    let out = p.wait_with_output().unwrap();
    (
        out.status.success(),
        serde_json::from_slice(&out.stdout).unwrap(),
    )
}
#[test]
fn cli_restarts_preserve_history_and_errors_are_json() {
    let store = std::env::temp_dir().join(format!("creative-cli-{}", uuid::Uuid::new_v4()));
    let (ok, r) = call(
        &store,
        &json!({"action":"project.create","params":{"name":"Persistent"}}).to_string(),
    );
    assert!(ok);
    let id = &r["result"]["id"];
    let (ok, _) = call(
        &store,
        &json!({"action":"project.rename","project_id":id,"params":{"name":"Changed"}}).to_string(),
    );
    assert!(ok);
    let (ok, r) = call(
        &store,
        &json!({"action":"history.undo","project_id":id,"params":{}}).to_string(),
    );
    assert!(ok);
    assert_eq!(r["result"]["name"], "Persistent");
    let (ok, r) = call(&store, "not json");
    assert!(!ok);
    assert_eq!(r["ok"], false);
    assert!(r["error"].is_string());
    std::fs::remove_dir_all(store).unwrap();
}
