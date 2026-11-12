use editor_3d::{
    commands::{Command, CommandGroup, Document},
    mesh::{Mesh, Primitive},
    object_selection::ObjectSelection,
    scene::{new_id, Object, Scene, Transform},
};

fn object(id: &str, visible: bool) -> Object {
    Object {
        id: id.into(),
        name: "Object".into(),
        transform: Transform::default(),
        color: [0.5; 3],
        visible,
        mesh: Mesh::primitive(Primitive::Cube),
    }
}

fn apply(document: &mut Document, commands: Vec<Command>) {
    document
        .apply(CommandGroup {
            expected_revision: document.revision,
            actor: "selection-test".into(),
            task_path: vec!["selection".into()],
            label: "Selection scene change".into(),
            commands,
        })
        .unwrap();
}

#[test]
fn shift_toggle_keeps_order_and_promotes_last_retained_object() {
    let mut selection = ObjectSelection::default();
    assert!(selection.is_empty());
    assert_eq!(selection.active(), None);
    selection.select_only("a".into());
    selection.toggle("b".into());
    selection.toggle("c".into());
    assert_eq!(selection.ids(), &["a", "b", "c"]);
    assert_eq!(selection.active(), Some("c"));
    selection.toggle("b".into());
    assert_eq!(selection.ids(), &["a", "c"]);
    assert_eq!(selection.active(), Some("c"));
    assert!(!selection.contains("b"));
    selection.toggle("c".into());
    assert_eq!(selection.active(), Some("a"));
    selection.toggle("b".into());
    assert_eq!(selection.ids(), &["a", "b"]);
    assert_eq!(selection.active(), Some("b"));
    selection.toggle("b".into());
    selection.toggle("a".into());
    assert!(selection.is_empty());
    assert_eq!(selection.len(), 0);
    assert_eq!(selection.active(), None);
}

#[test]
fn select_only_replaces_multiselection_and_empty_ids_are_noops() {
    let mut selection = ObjectSelection::default();
    selection.select_only("a".into());
    selection.toggle("b".into());
    selection.select_only("a".into());
    selection.select_only("a".into());
    assert_eq!(selection.ids(), &["a"]);
    assert_eq!(selection.len(), 1);
    selection.select_only(String::new());
    selection.toggle(String::new());
    assert_eq!(selection.ids(), &["a"]);
    let cloned = selection.clone();
    selection.clear();
    assert!(selection.is_empty());
    assert_eq!(selection.active(), None);
    assert_eq!(cloned.active(), Some("a"));
}

#[test]
fn select_all_uses_visible_scene_order_without_duplicates() {
    let scene = Scene {
        objects: vec![
            object("b", true),
            object("hidden", false),
            object("a", true),
            object("b", true),
            object("", true),
            object("c", true),
        ],
        ..Scene::default()
    };
    let mut selection = ObjectSelection::default();
    selection.select_only("stale".into());
    selection.select_all(&scene);
    assert_eq!(selection.ids(), &["b", "a", "c"]);
    assert_eq!(selection.active(), Some("c"));
    assert_eq!(selection.len(), 3);
    selection.select_all(&scene);
    assert_eq!(selection.ids(), &["b", "a", "c"]);
    selection.select_all(&Scene::default());
    assert!(selection.is_empty());
}

#[test]
fn prune_preserves_selection_order_independent_of_scene_order() {
    let scene = Scene {
        objects: vec![object("c", true), object("b", false), object("a", true)],
        ..Scene::default()
    };
    let mut selection = ObjectSelection::default();
    for id in ["a", "missing", "c", "b"] {
        selection.toggle(id.into());
    }
    selection.prune(&scene);
    assert_eq!(selection.ids(), &["a", "c"]);
    assert_eq!(selection.active(), Some("c"));
    selection.prune(&scene);
    assert_eq!(selection.ids(), &["a", "c"]);
    selection.prune(&Scene::default());
    assert!(selection.is_empty());
}

#[test]
fn hide_delete_and_undo_prune_without_restoring_transient_selection() {
    let ids = [new_id(), new_id(), new_id()];
    let mut document = Document::default();
    document.scene.objects = ids.iter().map(|id| object(id, true)).collect();
    let mut selection = ObjectSelection::default();
    selection.select_all(&document.scene);
    let serialized_before = serde_json::to_value(&document).unwrap();
    selection.toggle(ids[0].clone());
    selection.toggle(ids[0].clone());
    assert_eq!(serde_json::to_value(&document).unwrap(), serialized_before);
    apply(
        &mut document,
        vec![
            Command::Visibility {
                id: ids[2].clone(),
                visible: false,
            },
            Command::Remove { id: ids[0].clone() },
        ],
    );
    selection.prune(&document.scene);
    assert_eq!(selection.ids(), &[ids[1].clone()]);
    assert_eq!(selection.active(), Some(ids[1].as_str()));
    document.undo().unwrap();
    selection.prune(&document.scene);
    assert_eq!(selection.ids(), &[ids[1].clone()]);
    selection.select_all(&document.scene);
    assert_eq!(selection.ids(), &ids);
    document.redo().unwrap();
    selection.prune(&document.scene);
    assert_eq!(selection.ids(), &[ids[1].clone()]);
    apply(&mut document, vec![Command::Remove { id: ids[1].clone() }]);
    selection.prune(&document.scene);
    assert!(selection.is_empty());
    assert_eq!(selection.active(), None);
}
