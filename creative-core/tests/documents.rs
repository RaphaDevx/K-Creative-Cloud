use serde_json::{json, Value};
use std::{
    io::Write,
    path::PathBuf,
    process::{Command, Stdio},
};

struct Workspace {
    store: PathBuf,
    pid: String,
}
impl Workspace {
    fn new() -> Self {
        let store = std::env::temp_dir().join(format!("suite-documents-{}", uuid::Uuid::new_v4()));
        let mut work = Self {
            store,
            pid: String::new(),
        };
        let project = work.ok("project.create", json!({"name":"Suite fixture"}));
        work.pid = project["id"].as_str().unwrap().into();
        work
    }
    fn call(&self, action: &str, params: Value) -> (bool, Value) {
        let mut payload = json!({"action":action,"params":params});
        if !self.pid.is_empty() {
            payload["project_id"] = json!(self.pid);
        }
        let mut child = Command::new(env!("CARGO_BIN_EXE_creative-core"))
            .arg("--store")
            .arg(&self.store)
            .stdin(Stdio::piped())
            .stdout(Stdio::piped())
            .spawn()
            .unwrap();
        child
            .stdin
            .take()
            .unwrap()
            .write_all(payload.to_string().as_bytes())
            .unwrap();
        let output = child.wait_with_output().unwrap();
        (
            output.status.success(),
            serde_json::from_slice(&output.stdout).unwrap(),
        )
    }
    fn ok(&self, action: &str, params: Value) -> Value {
        let (success, response) = self.call(action, params);
        assert!(success, "{action}: {response}");
        response["result"].clone()
    }
    fn get(&self) -> Value {
        self.ok("project.get", json!({}))
    }
    fn doc(&self, name: &str, kind: &str) -> String {
        let project = self.ok("document.create", json!({
            "name":name,"kind":kind,"content":{"asset_ref":"immutable-example-reference","unit":"mm"}
        }));
        project["document_graph"]["documents"]
            .as_array()
            .unwrap()
            .last()
            .unwrap()["id"]
            .as_str()
            .unwrap()
            .into()
    }
    fn link(&self, dependent: &str, source: &str) {
        self.ok(
            "document.link",
            json!({"dependent_id":dependent,"source_id":source}),
        );
    }
    fn bytes(&self) -> Vec<u8> {
        std::fs::read(self.store.join(format!("{}.json", self.pid))).unwrap()
    }
    fn archive(&self, target: &str, mode: &str) -> Value {
        let preview = self.ok("document.archive_preview", json!({"id":target,"mode":mode}));
        self.ok(
            "document.archive",
            json!({"id":target,"mode":mode,"expected_revision":preview["expected_revision"]}),
        )
    }
}
impl Drop for Workspace {
    fn drop(&mut self) {
        std::fs::remove_dir_all(&self.store).unwrap();
    }
}
fn doc<'a>(project: &'a Value, id: &str) -> &'a Value {
    project["document_graph"]["documents"]
        .as_array()
        .unwrap()
        .iter()
        .find(|d| d["id"] == id)
        .unwrap()
}
fn linked(project: &Value, dependent: &str, source: &str) -> bool {
    project["document_graph"]["links"]
        .as_array()
        .unwrap()
        .iter()
        .any(|link| link["dependent_id"] == dependent && link["source_id"] == source)
}

#[test]
fn preserving_source_rehomes_copy_and_keeps_upstream_and_downstream_links() {
    let work = Workspace::new();
    let reference = work.doc("Measurements", "notes");
    let sketch = work.doc("Sketch", "sketch");
    let extrusion = work.doc("Extrusion", "cad");
    let render = work.doc("Render", "scene");
    work.link(&sketch, &reference);
    work.link(&extrusion, &sketch);
    work.link(&render, &extrusion);
    let before = work.get();
    let project = work.archive(&sketch, "preserve_dependents");
    let replacements = &project["document_graph"]["last_archive"]["replacements"];
    let copy = replacements[0]["copy_id"].as_str().unwrap();
    assert_eq!(doc(&project, &sketch)["archived"], true);
    assert_eq!(
        doc(&project, copy)["content"],
        doc(&before, &sketch)["content"]
    );
    assert_eq!(doc(&project, copy)["owner_id"], extrusion);
    assert_eq!(doc(&project, copy)["origin_id"], sketch);
    assert!(linked(&project, &extrusion, copy));
    assert!(!linked(&project, &extrusion, &sketch));
    assert!(linked(&project, copy, &reference));
    assert!(linked(&project, &render, &extrusion));
    assert_eq!(doc(&project, &render)["archived"], false);
    assert_eq!(work.get(), project); // Separate process reload.
    let undone = work.ok("history.undo", json!({}));
    assert_eq!(undone["document_graph"], before["document_graph"]);
    let redone = work.ok("history.redo", json!({}));
    assert_eq!(redone["document_graph"], project["document_graph"]);
}

#[test]
fn each_direct_user_gets_an_independent_manifest_identity() {
    let work = Workspace::new();
    let music = work.doc("Song", "music");
    let video = work.doc("Video", "video");
    let notes = work.doc("Notes", "notes");
    work.link(&video, &music);
    work.link(&notes, &music);
    let project = work.archive(&music, "preserve_dependents");
    let replacements = project["document_graph"]["last_archive"]["replacements"]
        .as_array()
        .unwrap();
    assert_eq!(replacements.len(), 2);
    assert_ne!(replacements[0]["copy_id"], replacements[1]["copy_id"]);
    for replacement in replacements {
        assert!(linked(
            &project,
            replacement["dependent_id"].as_str().unwrap(),
            replacement["copy_id"].as_str().unwrap()
        ));
    }
}

#[test]
fn cascade_visits_diamond_once_and_preserves_shared_inputs_and_unrelated_users() {
    let work = Workspace::new();
    let shared = work.doc("Shared input", "photo");
    let root = work.doc("Root", "sketch");
    let left = work.doc("Left", "cad");
    let right = work.doc("Right", "cad");
    let tip = work.doc("Final", "scene");
    let unrelated = work.doc("Other", "video");
    work.link(&root, &shared);
    work.link(&unrelated, &shared);
    work.link(&left, &root);
    work.link(&right, &root);
    work.link(&tip, &left);
    work.link(&tip, &right);
    let project = work.archive(&root, "cascade_dependents");
    assert_eq!(
        project["document_graph"]["last_archive"]["preview"]["archive"]
            .as_array()
            .unwrap()
            .len(),
        4
    );
    for target in [&root, &left, &right, &tip] {
        assert_eq!(doc(&project, target)["archived"], true);
    }
    for target in [&shared, &unrelated] {
        assert_eq!(doc(&project, target)["archived"], false);
    }
    assert!(linked(&project, &unrelated, &shared));
}

#[test]
fn preview_is_read_only_and_stale_archive_does_not_write() {
    let work = Workspace::new();
    let target = work.doc("Source", "sketch");
    let bytes = work.bytes();
    let preview = work.ok(
        "document.archive_preview",
        json!({"id":target,"mode":"preserve_dependents"}),
    );
    assert_eq!(work.bytes(), bytes);
    assert_eq!(preview["physical_files_deleted"], false);
    work.doc("Intervening change", "notes");
    let bytes = work.bytes();
    let (ok, error) = work.call("document.archive", json!({"id":target,"mode":"preserve_dependents","expected_revision":preview["expected_revision"]}));
    assert!(!ok);
    assert!(error["error"].as_str().unwrap().contains("changed"));
    assert_eq!(work.bytes(), bytes);
}

#[test]
fn cycles_duplicates_missing_and_archived_targets_are_rejected_without_writes() {
    let work = Workspace::new();
    let a = work.doc("A", "sketch");
    let b = work.doc("B", "cad");
    let c = work.doc("C", "scene");
    work.link(&b, &a);
    work.link(&c, &b);
    for (dependent, source) in [(&a, &c), (&a, &a), (&b, &a), (&c, &"missing".to_string())] {
        let bytes = work.bytes();
        assert!(
            !work
                .call(
                    "document.link",
                    json!({"dependent_id":dependent,"source_id":source})
                )
                .0
        );
        assert_eq!(work.bytes(), bytes);
    }
    work.archive(&c, "cascade_dependents");
    let bytes = work.bytes();
    assert!(
        !work
            .call("document.link", json!({"dependent_id":b,"source_id":c}))
            .0
    );
    assert!(
        !work
            .call(
                "document.archive_preview",
                json!({"id":c,"mode":"cascade_dependents"})
            )
            .0
    );
    assert_eq!(work.bytes(), bytes);
}

#[test]
fn failed_batch_is_atomic_and_archive_cannot_hide_inside_batch() {
    let work = Workspace::new();
    let target = work.doc("Root", "sketch");
    let before = work.get();
    let bytes = work.bytes();
    let (_, error) = work.call(
        "project.batch",
        json!({"expected_revision":before["revision"],"commands":[
            {"action":"document.create","params":{"name":"Temporary","kind":"notes","content":{}}},
            {"action":"document.link","params":{"dependent_id":target,"source_id":"missing"}}
        ]}),
    );
    assert_eq!(error["ok"], false);
    assert_eq!(work.bytes(), bytes);
    for action in ["document.archive", "document.archive_preview"] {
        let mut params = json!({"id":target,"mode":"cascade_dependents"});
        if action == "document.archive" {
            params["expected_revision"] = before["revision"].clone();
        }
        assert!(!work.call("project.batch", json!({"expected_revision":before["revision"],"commands":[{"action":action,"params":params}]})).0);
    }
    assert_eq!(work.bytes(), bytes);
}

#[test]
fn legacy_project_gains_graph_lazily_and_undo_restores_legacy_shape() {
    let work = Workspace::new();
    assert!(work.get().get("document_graph").is_none());
    work.doc("First", "notes");
    assert!(work.get().get("document_graph").is_some());
    let undone = work.ok("history.undo", json!({}));
    assert!(undone.get("document_graph").is_none());
    assert!(work
        .ok("history.redo", json!({}))
        .get("document_graph")
        .is_some());
}

#[test]
fn invalid_kinds_modes_revisions_and_oversized_manifests_are_rejected() {
    let work = Workspace::new();
    let target = work.doc("Valid", "notes");
    let bytes = work.bytes();
    assert!(
        !work
            .call(
                "document.create",
                json!({"name":"Bad","kind":"unknown","content":{}})
            )
            .0
    );
    assert!(
        !work
            .call(
                "document.create",
                json!({"name":"Huge","kind":"notes","content":{"data":"x".repeat(262144)}})
            )
            .0
    );
    assert!(
        !work
            .call(
                "document.archive_preview",
                json!({"id":target,"mode":"delete_everything"})
            )
            .0
    );
    assert!(
        !work
            .call(
                "document.archive",
                json!({"id":target,"mode":"preserve_dependents","expected_revision":-1})
            )
            .0
    );
    assert_eq!(work.bytes(), bytes);
    let catalog = work.ok("system.actions", json!({}));
    assert!(catalog
        .as_array()
        .unwrap()
        .iter()
        .any(|entry| entry["name"] == "document.archive_preview"));
}
