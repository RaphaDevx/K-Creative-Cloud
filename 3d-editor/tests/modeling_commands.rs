use editor_3d::{
    commands::{Command, CommandGroup, Document},
    mesh::Primitive,
};
use std::collections::BTreeMap;

fn apply(document: &mut Document, commands: Vec<Command>) -> editor_3d::Result<()> {
    document.apply(CommandGroup {
        expected_revision: document.revision,
        actor: "modeling-test".into(),
        task_path: vec!["Modell".into(), "Topologie".into()],
        label: "Modellieren".into(),
        commands,
    })
}
fn cube() -> Document {
    let mut d = Document::default();
    apply(
        &mut d,
        vec![Command::Add {
            primitive: Primitive::Cube,
        }],
    )
    .unwrap();
    d
}
fn manifold(document: &Document) {
    let mut edges = BTreeMap::new();
    for face in &document.scene.objects[0].mesh.faces {
        for i in 0..face.len() {
            let a = face[i];
            let b = face[(i + 1) % face.len()];
            let counts = edges.entry((a.min(b), a.max(b))).or_insert((0, 0));
            counts.0 += 1;
            counts.1 += if a < b { 1 } else { -1 };
        }
    }
    assert!(edges.values().all(|&(n, d)| n == 2 && d == 0));
}
#[test]
fn inset_and_subdivision_are_real_commands_with_roundtrip_history() {
    let mut d = cube();
    let before = d.scene.clone();
    let id = d.scene.objects[0].id.clone();
    let command: Command = serde_json::from_str(&format!(
        "{{\"action\":\"inset\",\"id\":\"{id}\",\"face\":3,\"factor\":0.2}}"
    ))
    .unwrap();
    apply(&mut d, vec![command]).unwrap();
    manifold(&d);
    assert_eq!(d.scene.objects[0].mesh.faces.len(), 10);
    d.undo().unwrap();
    assert_eq!(d.scene, before);
    apply(&mut d, vec![Command::Subdivide { id }]).unwrap();
    manifold(&d);
    assert_eq!(
        (
            d.scene.objects[0].mesh.positions.len(),
            d.scene.objects[0].mesh.faces.len()
        ),
        (26, 24)
    );
    let restored: Document = serde_json::from_slice(&serde_json::to_vec(&d).unwrap()).unwrap();
    restored.validate().unwrap();
    assert_eq!(
        restored.history.last().unwrap().changes[0]
            .before
            .as_ref()
            .unwrap()
            .mesh
            .positions
            .len(),
        8
    );
}
#[test]
fn invalid_inset_in_a_batch_rolls_back_earlier_changes() {
    let mut d = cube();
    let id = d.scene.objects[0].id.clone();
    let before = serde_json::to_vec(&d).unwrap();
    assert!(apply(
        &mut d,
        vec![
            Command::Subdivide { id: id.clone() },
            Command::Inset {
                id,
                face: 0,
                factor: 1.0
            }
        ]
    )
    .is_err());
    assert_eq!(serde_json::to_vec(&d).unwrap(), before);
}
#[test]
fn moving_a_vertex_triangulates_adjacent_faces_and_undo_restores_quads() {
    let mut d = cube();
    let before = d.scene.clone();
    let id = d.scene.objects[0].id.clone();
    apply(
        &mut d,
        vec![Command::MoveVertex {
            id,
            vertex: 6,
            position: [0.7, 0.8, 0.6],
        }],
    )
    .unwrap();
    manifold(&d);
    assert_eq!(d.scene.objects[0].mesh.positions[6], [0.7, 0.8, 0.6]);
    assert_eq!(d.scene.objects[0].mesh.faces.len(), 9);
    d.undo().unwrap();
    assert_eq!(d.scene, before);
}
#[test]
fn moving_an_edge_moves_both_endpoints_atomically() {
    let mut d = cube();
    let before = d.scene.clone();
    let id = d.scene.objects[0].id.clone();
    apply(
        &mut d,
        vec![Command::MoveEdge {
            id: id.clone(),
            edge: [6, 7],
            offset: [0., 0.25, 0.],
        }],
    )
    .unwrap();
    manifold(&d);
    assert_eq!(d.scene.objects[0].mesh.positions[6][1], 0.75);
    assert_eq!(d.scene.objects[0].mesh.positions[7][1], 0.75);
    let saved = serde_json::to_vec(&d).unwrap();
    assert!(apply(
        &mut d,
        vec![Command::MoveEdge {
            id,
            edge: [0, 6],
            offset: [1., 0., 0.]
        }]
    )
    .is_err());
    assert_eq!(serde_json::to_vec(&d).unwrap(), saved);
    d.undo().unwrap();
    assert_eq!(d.scene, before);
}
