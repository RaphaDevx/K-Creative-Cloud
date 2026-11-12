use editor_3d::{
    branding::{contrast, Brand},
    camera::{ray_triangle, Camera},
    commands::{Command, CommandGroup, Document},
    mesh::{Mesh, Primitive},
    obj, persistence,
    scene::Transform,
};
use glam::Vec3;
use std::collections::BTreeMap;

fn group(document: &Document, label: &str, commands: Vec<Command>) -> CommandGroup {
    CommandGroup {
        expected_revision: document.revision,
        actor: "fixture-agent".into(),
        task_path: vec!["Modell".into(), "Grundform".into()],
        label: label.into(),
        commands,
    }
}
fn cube() -> Document {
    let mut document = Document::default();
    document
        .apply(group(
            &document,
            "Würfel",
            vec![Command::Add {
                primitive: Primitive::Cube,
            }],
        ))
        .unwrap();
    document
}
fn closed(mesh: &Mesh) {
    let mut edges = BTreeMap::new();
    for face in &mesh.faces {
        for i in 0..face.len() {
            let a = face[i];
            let b = face[(i + 1) % face.len()];
            let entry = edges.entry((a.min(b), a.max(b))).or_insert((0, 0));
            entry.0 += 1;
            entry.1 += if a < b { 1 } else { -1 };
        }
    }
    assert!(
        edges
            .values()
            .all(|&(count, balance)| count == 2 && balance == 0),
        "mesh edge orientation/manifold mismatch: {edges:?}"
    );
}

#[test]
fn solid_primitives_are_closed_and_outward_facing() {
    for primitive in [Primitive::Cube, Primitive::Sphere, Primitive::Cylinder] {
        let mesh = Mesh::primitive(primitive);
        mesh.validate().unwrap();
        closed(&mesh);
        for (index, face) in mesh.faces.iter().enumerate() {
            let centroid = face
                .iter()
                .map(|i| Vec3::from(mesh.positions[*i as usize]))
                .sum::<Vec3>()
                / face.len() as f32;
            assert!(
                centroid.dot(mesh.normal(index)) > 0.,
                "inward face {primitive:?}/{index}"
            );
        }
    }
    Mesh::primitive(Primitive::Plane).validate().unwrap();
}

#[test]
fn face_extrusion_changes_geometry_and_preserves_closed_surface() {
    let mut document = cube();
    let before = document.scene.clone();
    let id = before.objects[0].id.clone();
    document
        .apply(group(
            &document,
            "Extrusion",
            vec![Command::Extrude {
                id,
                face: 3,
                distance: 0.75,
            }],
        ))
        .unwrap();
    let mesh = &document.scene.objects[0].mesh;
    assert_eq!((mesh.positions.len(), mesh.faces.len()), (12, 10));
    closed(mesh);
    assert!(
        (mesh
            .positions
            .iter()
            .map(|p| p[1])
            .fold(f32::NEG_INFINITY, f32::max)
            - 1.25)
            .abs()
            < 1e-6
    );
    assert_eq!(
        document.history.last().unwrap().changes[0]
            .before
            .as_ref()
            .unwrap()
            .mesh
            .positions
            .len(),
        8
    );
    let extruded = document.scene.clone();
    document.undo().unwrap();
    assert_eq!(document.scene, before);
    document.redo().unwrap();
    assert_eq!(document.scene, extruded);
    assert_eq!(document.revision, 4);
}

#[test]
fn invalid_group_and_stale_revision_do_not_change_scene_or_history() {
    let mut document = cube();
    let bytes = serde_json::to_vec(&document).unwrap();
    let invalid = group(
        &document,
        "Atomic",
        vec![
            Command::Add {
                primitive: Primitive::Sphere,
            },
            Command::Remove {
                id: "missing".into(),
            },
        ],
    );
    assert!(document.apply(invalid).is_err());
    assert_eq!(serde_json::to_vec(&document).unwrap(), bytes);
    let mut stale = group(
        &document,
        "Stale",
        vec![Command::Add {
            primitive: Primitive::Cube,
        }],
    );
    stale.expected_revision = 0;
    assert!(document.apply(stale).is_err());
    assert_eq!(serde_json::to_vec(&document).unwrap(), bytes);
}

#[test]
fn invalid_transforms_and_mesh_edits_are_atomic() {
    let mut document = cube();
    let id = document.scene.objects[0].id.clone();
    let before = serde_json::to_vec(&document).unwrap();
    let commands = vec![
        Command::Transform {
            id: id.clone(),
            transform: Transform {
                scale: [0., 1., 1.],
                ..Default::default()
            },
        },
        Command::Extrude {
            id: id.clone(),
            face: 999,
            distance: 1.,
        },
        Command::Extrude {
            id: id.clone(),
            face: 0,
            distance: -1.,
        },
        Command::MoveVertex {
            id: id.clone(),
            vertex: 0,
            position: [f32::NAN, 0., 0.],
        },
        Command::Color {
            id,
            color: [2., 0., 0.],
        },
    ];
    for command in commands {
        assert!(document
            .apply(group(&document, "Invalid", vec![command]))
            .is_err());
        assert_eq!(serde_json::to_vec(&document).unwrap(), before);
    }
}

#[test]
fn undo_after_new_edit_clears_redo_and_preserves_operation_journal() {
    let mut document = cube();
    document.undo().unwrap();
    assert!(document.can_redo());
    document
        .apply(group(
            &document,
            "Kugel",
            vec![Command::Add {
                primitive: Primitive::Sphere,
            }],
        ))
        .unwrap();
    assert!(!document.can_redo());
    assert_eq!(document.history.len(), 3);
    assert_eq!(document.history[1].kind, "undo");
    assert_eq!(document.history[2].actor, "fixture-agent");
    assert_eq!(document.history[2].task_path, vec!["Modell", "Grundform"]);
    document.validate().unwrap();
}

#[test]
fn duplicate_has_independent_identity_and_remove_is_reversible() {
    let mut document = cube();
    let original = document.scene.objects[0].clone();
    document
        .apply(group(
            &document,
            "Duplikat",
            vec![Command::Duplicate {
                id: original.id.clone(),
            }],
        ))
        .unwrap();
    let copy = document.scene.objects[1].clone();
    assert_ne!(original.id, copy.id);
    assert_eq!(original.mesh, copy.mesh);
    document
        .apply(group(
            &document,
            "Entfernen",
            vec![Command::Remove {
                id: original.id.clone(),
            }],
        ))
        .unwrap();
    assert_eq!(document.scene.objects.len(), 1);
    assert_eq!(document.scene.objects[0].id, copy.id);
    document.undo().unwrap();
    assert_eq!(document.scene.objects[0], original);
}

#[test]
fn camera_picks_nearest_visible_surface_and_uses_actual_transform() {
    let mut document = cube();
    let id = document.scene.objects[0].id.clone();
    let camera = Camera {
        yaw: 0.,
        pitch: 0.,
        distance: 5.,
        target: Vec3::new(0., 0.5, 0.),
    };
    assert_eq!(
        camera.pick(&document.scene, [0., 0.], 1.).unwrap(),
        (id.clone(), 1)
    );
    document
        .apply(group(
            &document,
            "Move",
            vec![Command::Transform {
                id: id.clone(),
                transform: Transform {
                    translation: [3., 0.5, 0.],
                    ..Default::default()
                },
            }],
        ))
        .unwrap();
    assert!(camera.pick(&document.scene, [0., 0.], 1.).is_none());
    document
        .apply(group(
            &document,
            "Kopie",
            vec![Command::Add {
                primitive: Primitive::Cube,
            }],
        ))
        .unwrap();
    let near = document.scene.objects[1].id.clone();
    assert_eq!(camera.pick(&document.scene, [0., 0.], 1.).unwrap().0, near);
    document
        .apply(group(
            &document,
            "Hide",
            vec![Command::Visibility {
                id: near,
                visible: false,
            }],
        ))
        .unwrap();
    assert!(camera.pick(&document.scene, [0., 0.], 1.).is_none());
    assert!(ray_triangle(
        Vec3::ZERO,
        Vec3::Z,
        [
            Vec3::new(0., 0., -2.),
            Vec3::new(1., 0., -2.),
            Vec3::new(0., 1., -2.)
        ]
    )
    .is_none());
}

#[test]
fn obj_supports_negative_indices_and_bakes_world_transforms() {
    let mesh = obj::parse("v 0 0 0\nv 1 0 0\nv 1 1 0\nv 0 1 0\nf -4/1 -3/2 -2/3 -1/4\n").unwrap();
    assert_eq!(mesh.faces[0], vec![0, 1, 2, 3]);
    let mut document = cube();
    let id = document.scene.objects[0].id.clone();
    document
        .apply(group(
            &document,
            "Move",
            vec![Command::Transform {
                id,
                transform: Transform {
                    translation: [2., 3., 4.],
                    scale: [2., 2., 2.],
                    ..Default::default()
                },
            }],
        ))
        .unwrap();
    let exported = obj::export(&document.scene).unwrap();
    let imported = obj::parse(&exported).unwrap();
    assert_eq!(imported.positions[0], [1., 2., 3.]);
    closed(&imported);
    for bad in ["v 0 0 0\nf 0 1 1", "v 0 0 0\nf 1 2 3", "v NaN 0 0\nf 1 1 1"] {
        assert!(obj::parse(bad).is_err());
    }
}

#[test]
fn file_roundtrip_restores_editable_mesh_and_history_and_refuses_bad_schema() {
    let dir = std::env::temp_dir().join(format!("editor-3d-test-{}", uuid::Uuid::new_v4()));
    std::fs::create_dir(&dir).unwrap();
    let path = dir.join("scene.scene3d");
    let mut document = cube();
    document.undo().unwrap();
    persistence::save(&path, &document).unwrap();
    let mut restored = persistence::load(&path).unwrap();
    restored.redo().unwrap();
    assert_eq!(restored.scene.objects.len(), 1);
    persistence::save(&path, &restored).unwrap();
    assert_eq!(persistence::load(&path).unwrap().revision, 3);
    let before = std::fs::read(&path).unwrap();
    restored.schema_version = 99;
    assert!(persistence::save(&path, &restored).is_err());
    assert_eq!(std::fs::read(&path).unwrap(), before);
    assert!(std::fs::read_dir(&dir).unwrap().all(|entry| !entry
        .unwrap()
        .path()
        .extension()
        .is_some_and(|x| x == "tmp")));
    std::fs::remove_dir_all(dir).unwrap();
}

#[test]
fn branding_is_validated_and_independent_from_document_data() {
    let mut brand = Brand::default();
    brand.validate().unwrap();
    assert_eq!(brand.app_name, "3d-editor");
    assert!(
        contrast(
            Brand::ink_on(brand.launch_background),
            brand.launch_background
        ) > 4.5
    );
    let document = cube();
    let before = serde_json::to_vec(&document).unwrap();
    brand.app_name = "Atelier".into();
    brand.wordmark = "Atelier".into();
    brand.monogram = "AT".into();
    brand.accent = [225, 181, 135];
    brand.validate().unwrap();
    assert_eq!(serde_json::to_vec(&document).unwrap(), before);
    brand.accent = brand.launch_background;
    assert!(brand.validate().is_err());
    assert!(serde_json::from_str::<Brand>("{\"schema_version\":1}").is_err());
}

#[test]
fn mesh_rejects_nonplanar_and_concave_polygons_instead_of_silent_bad_triangulation() {
    let nonplanar = Mesh {
        positions: vec![[0., 0., 0.], [1., 0., 0.], [1., 1., 0.], [0., 1., 1.]],
        faces: vec![vec![0, 1, 2, 3]],
    };
    assert!(nonplanar.validate().is_err());
    let concave = Mesh {
        positions: vec![
            [0., 0., 0.],
            [2., 0., 0.],
            [1., 0.5, 0.],
            [2., 2., 0.],
            [0., 2., 0.],
        ],
        faces: vec![vec![0, 1, 2, 3, 4]],
    };
    assert!(concave.validate().is_err());
    let ring: Vec<_> = (0..5)
        .map(|i| {
            let a = i as f32 * std::f32::consts::TAU / 5.;
            [a.cos(), a.sin(), 0.]
        })
        .collect();
    let star = Mesh {
        positions: ring,
        faces: vec![vec![0, 2, 4, 1, 3]],
    };
    assert!(
        star.validate().is_err(),
        "Self-intersecting star is not a convex face"
    );
}

#[test]
fn grid_segments_are_clipped_to_the_visible_frustum_before_gpu_upload() {
    let camera = Camera::default();
    let matrix = camera.matrix(1.4);
    for x in -20..=20 {
        if let Some((a, b)) = editor_3d::camera::clip_segment(
            Vec3::new(x as f32, 0., -20.),
            Vec3::new(x as f32, 0., 20.),
            matrix,
        ) {
            for p in [a, b] {
                let clip = matrix * p.extend(1.);
                assert!(clip.w > 0.);
                let ndc = clip.truncate() / clip.w;
                assert!(
                    ndc.x.abs() <= 1.001
                        && ndc.y.abs() <= 1.001
                        && ndc.z >= -0.001
                        && ndc.z <= 1.001,
                    "{ndc:?}"
                );
            }
        }
    }
    assert!(editor_3d::camera::clip_segment(
        camera.eye() + Vec3::Y * 100.,
        camera.eye() + Vec3::Y * 101.,
        matrix
    )
    .is_none());
}
