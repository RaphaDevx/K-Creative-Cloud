use editor_3d::{
    commands::{Command, CommandGroup, Document},
    mesh::{Mesh, Primitive},
    scene::{new_id, Object, Transform},
};

fn document(count: usize) -> Document {
    let mut document = Document::default();
    document.scene.objects = (0..count)
        .map(|index| Object {
            id: new_id(),
            name: format!("Object {index}"),
            transform: Transform {
                translation: [index as f32 * 1.25 + 0.125, -0.375, 0.625],
                rotation_degrees: [15., 25., 35.],
                scale: [1., 2., 0.5],
            },
            color: [0.3, 0.5, 0.7],
            visible: true,
            mesh: Mesh::primitive(Primitive::Cube),
        })
        .collect();
    document.validate().unwrap();
    document
}

fn ids(document: &Document) -> Vec<String> {
    document
        .scene
        .objects
        .iter()
        .map(|object| object.id.clone())
        .collect()
}

fn group(document: &Document, commands: Vec<Command>) -> CommandGroup {
    CommandGroup {
        expected_revision: document.revision,
        actor: "group-test".into(),
        task_path: vec!["iteration-0003".into(), "group-edit".into()],
        label: "Edit selection".into(),
        commands,
    }
}

fn apply(document: &mut Document, command: Command) {
    document.apply(group(document, vec![command])).unwrap();
}

fn rejected_atomically(document: &mut Document, commands: Vec<Command>) {
    let before = serde_json::to_value(&*document).unwrap();
    let result = document.apply(group(document, commands));
    assert!(result.is_err(), "Invalid group unexpectedly succeeded");
    assert_eq!(serde_json::to_value(&*document).unwrap(), before);
    document.validate().unwrap();
}

#[test]
fn snapped_translation_preserves_relative_spacing_and_records_one_edit() {
    let mut document = document(3);
    let before = document.scene.clone();
    let ids = ids(&document);
    apply(
        &mut document,
        Command::TranslateObjects {
            ids: vec![ids[1].clone(), ids[0].clone()],
            offset: [0.74, -0.75, 0.24],
            snap: Some(0.5),
        },
    );
    for index in 0..2 {
        let mut expected = before.objects[index].clone();
        expected.transform.translation[0] += 0.5;
        expected.transform.translation[1] -= 1.;
        assert_eq!(document.scene.objects[index], expected);
    }
    assert_eq!(document.scene.objects[2], before.objects[2]);
    // Objects started off-grid: relative snapping must not quantize positions.
    assert_eq!(document.scene.objects[0].transform.translation[0], 0.625);
    assert_eq!(
        document.scene.objects[1].transform.translation[0]
            - document.scene.objects[0].transform.translation[0],
        1.25
    );
    assert_eq!(document.revision, 1);
    assert_eq!(document.history.len(), 1);
    let entry = &document.history[0];
    assert_eq!(entry.actor, "group-test");
    assert_eq!(entry.task_path, ["iteration-0003", "group-edit"]);
    assert_eq!(entry.kind, "edit");
    assert_eq!(entry.commands.len(), 1);
    assert_eq!(entry.changes.len(), 2);
    for change in &entry.changes {
        assert_eq!(
            change.before.as_ref().unwrap(),
            before.object(&change.object_id).unwrap()
        );
        assert_eq!(
            change.after.as_ref().unwrap(),
            document.scene.object(&change.object_id).unwrap()
        );
    }
    let after = document.scene.clone();
    document.undo().unwrap();
    assert_eq!(document.scene, before);
    assert_eq!(document.revision, 2);
    assert_eq!(document.history[1].kind, "undo");
    assert_eq!(document.history[1].changes.len(), 2);
    document.redo().unwrap();
    assert_eq!(document.scene, after);
    assert_eq!(document.revision, 3);
    assert_eq!(document.history[2].kind, "redo");
    document.validate().unwrap();
}

#[test]
fn unsnapped_translation_keeps_exact_requested_delta() {
    let mut document = document(2);
    let before = document.scene.clone();
    let ids = ids(&document);
    apply(
        &mut document,
        Command::TranslateObjects {
            ids,
            offset: [0.125, -0.0625, 0.375],
            snap: None,
        },
    );
    for (old, new) in before.objects.iter().zip(&document.scene.objects) {
        for (axis, delta) in [0.125, -0.0625, 0.375].into_iter().enumerate() {
            assert_eq!(
                new.transform.translation[axis] - old.transform.translation[axis],
                delta
            );
        }
    }
}

#[test]
fn duplicate_and_remove_groups_restore_identical_ids_through_undo_redo() {
    let mut document = document(3);
    let original = document.scene.clone();
    let original_ids = ids(&document);
    let requested = vec![original_ids[2].clone(), original_ids[0].clone()];
    apply(
        &mut document,
        Command::DuplicateObjects {
            ids: requested.clone(),
        },
    );
    assert_eq!(document.scene.objects.len(), 5);
    assert_eq!(&document.scene.objects[..3], &original.objects);
    for (copy, source_id) in document.scene.objects[3..].iter().zip(requested) {
        let source = original.object(&source_id).unwrap();
        let mut expected = source.clone();
        expected.id = copy.id.clone();
        expected.name = format!("{} Kopie", source.name);
        expected.transform.translation[0] += 1.25;
        assert_eq!(copy, &expected);
        assert!(!original_ids.contains(&copy.id));
    }
    assert_ne!(document.scene.objects[3].id, document.scene.objects[4].id);
    assert_eq!(document.history[0].changes.len(), 2);
    assert!(document.history[0]
        .changes
        .iter()
        .all(|change| change.before.is_none() && change.after.is_some()));
    let duplicated = document.scene.clone();
    document.undo().unwrap();
    assert_eq!(document.scene, original);
    document.redo().unwrap();
    assert_eq!(document.scene, duplicated);
    let copies = document.scene.objects[3..]
        .iter()
        .map(|object| object.id.clone())
        .collect();
    apply(&mut document, Command::RemoveObjects { ids: copies });
    assert_eq!(document.scene, original);
    let removal = document.history.last().unwrap();
    assert_eq!(removal.changes.len(), 2);
    assert!(removal
        .changes
        .iter()
        .all(|change| change.before.is_some() && change.after.is_none()));
    document.undo().unwrap();
    assert_eq!(document.scene, duplicated);
    document.redo().unwrap();
    assert_eq!(document.scene, original);
    document.validate().unwrap();
}

#[test]
fn invalid_group_ids_roll_back_prior_commands_and_preserve_redo_history() {
    let mut document = document(2);
    let valid = ids(&document);
    apply(
        &mut document,
        Command::Rename {
            id: valid[0].clone(),
            name: "Temporary".into(),
        },
    );
    document.undo().unwrap();
    assert!(document.can_redo());
    let mut oversized = valid.clone();
    oversized.extend((2..257).map(|_| new_id()));
    for invalid in [
        vec![],
        vec![valid[0].clone(), new_id()],
        vec![valid[0].clone(), valid[0].clone()],
        oversized,
    ] {
        for command in [
            Command::TranslateObjects {
                ids: invalid.clone(),
                offset: [1., 0., 0.],
                snap: None,
            },
            Command::DuplicateObjects {
                ids: invalid.clone(),
            },
            Command::RemoveObjects {
                ids: invalid.clone(),
            },
        ] {
            rejected_atomically(
                &mut document,
                vec![
                    Command::Rename {
                        id: valid[1].clone(),
                        name: "Must roll back".into(),
                    },
                    command,
                ],
            );
            assert!(document.can_redo());
        }
    }
}

#[test]
fn invalid_snap_offsets_and_noop_snap_leave_document_unchanged() {
    let mut document = document(2);
    let ids = ids(&document);
    for snap in [0., -0.5, 1000.5, f32::INFINITY, f32::NAN] {
        rejected_atomically(
            &mut document,
            vec![Command::TranslateObjects {
                ids: ids.clone(),
                offset: [1., 0., 0.],
                snap: Some(snap),
            }],
        );
    }
    for value in [f32::NAN, f32::INFINITY, f32::NEG_INFINITY, 1_000_001.] {
        rejected_atomically(
            &mut document,
            vec![Command::TranslateObjects {
                ids: ids.clone(),
                offset: [value, 0., 0.],
                snap: None,
            }],
        );
    }
    rejected_atomically(
        &mut document,
        vec![Command::TranslateObjects {
            ids,
            offset: [0.01, -0.01, 0.],
            snap: Some(0.5),
        }],
    );
}

#[test]
fn one_command_can_translate_and_remove_all_256_objects() {
    let mut document = document(256);
    let ids = ids(&document);
    let original = document.scene.clone();
    apply(
        &mut document,
        Command::TranslateObjects {
            ids: ids.clone(),
            offset: [0.25, 0., 0.],
            snap: Some(0.25),
        },
    );
    assert_eq!(document.history[0].changes.len(), 256);
    assert_eq!(document.history[0].commands.len(), 1);
    for (old, new) in original.objects.iter().zip(&document.scene.objects) {
        assert_eq!(
            new.transform.translation[0],
            old.transform.translation[0] + 0.25
        );
    }
    let moved = document.scene.clone();
    apply(&mut document, Command::RemoveObjects { ids });
    assert!(document.scene.objects.is_empty());
    assert_eq!(document.history[1].changes.len(), 256);
    document.undo().unwrap();
    assert_eq!(document.scene, moved);
    document.undo().unwrap();
    assert_eq!(document.scene, original);
    document.validate().unwrap();
}

#[test]
fn duplication_accepts_exact_capacity_and_rejects_overflow_atomically() {
    let mut document = document(128);
    let ids = ids(&document);
    apply(
        &mut document,
        Command::DuplicateObjects { ids: ids.clone() },
    );
    assert_eq!(document.scene.objects.len(), 256);
    assert_eq!(document.history[0].changes.len(), 128);
    rejected_atomically(
        &mut document,
        vec![Command::DuplicateObjects {
            ids: vec![ids[0].clone()],
        }],
    );
    document.undo().unwrap();
    assert_eq!(document.scene.objects.len(), 128);
    document.redo().unwrap();
    assert_eq!(document.scene.objects.len(), 256);
}
