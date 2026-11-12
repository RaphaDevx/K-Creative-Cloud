use editor_3d::{
    mesh::{Mesh, Primitive, MAX_FACES, MAX_VERTICES},
    obj,
    scene::{new_id, Object, Scene, Transform},
};
use glam::Vec3;
use std::collections::BTreeMap;

fn edges(mesh: &Mesh) -> BTreeMap<(u32, u32), (usize, i32)> {
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
    edges
}

fn closed(mesh: &Mesh) {
    let edges = edges(mesh);
    assert!(edges
        .values()
        .all(|&(count, balance)| count == 2 && balance == 0));
    assert_eq!(mesh.positions.len() + mesh.faces.len(), edges.len() + 2);
}

fn unchanged(mesh: &Mesh, before: &Mesh) {
    assert_eq!(mesh.faces, before.faces);
    let bits = |mesh: &Mesh| {
        mesh.positions
            .iter()
            .map(|point| point.map(f32::to_bits))
            .collect::<Vec<_>>()
    };
    assert_eq!(bits(mesh), bits(before));
}

fn area(mesh: &Mesh) -> f32 {
    mesh.triangles()
        .map(|(_, triangle)| {
            let [a, b, c] = triangle.map(|i| Vec3::from(mesh.positions[i as usize]));
            (b - a).cross(c - a).length() * 0.5
        })
        .sum()
}

#[test]
fn inset_keeps_cap_index_and_moves_vertices_toward_centroid() {
    let mut mesh = Mesh::primitive(Primitive::Cube);
    let before = mesh.clone();
    mesh.inset_face(1, 0.2).unwrap();
    mesh.validate().unwrap();
    assert_eq!((mesh.positions.len(), mesh.faces.len()), (12, 10));
    assert_eq!(&mesh.positions[..8], &before.positions);
    assert_eq!(mesh.faces[1], vec![8, 9, 10, 11]);
    for (i, expected) in [
        [-0.4, -0.4, 0.5],
        [0.4, -0.4, 0.5],
        [0.4, 0.4, 0.5],
        [-0.4, 0.4, 0.5],
    ]
    .into_iter()
    .enumerate()
    {
        assert!((Vec3::from(mesh.positions[8 + i]) - Vec3::from(expected)).length() < 1e-6);
    }
    for index in [0, 2, 3, 4, 5] {
        assert_eq!(mesh.faces[index], before.faces[index]);
    }
    assert!((area(&mesh) - area(&before)).abs() < 1e-6);
    assert!((mesh.normal(1) - before.normal(1)).length() < 1e-6);
    closed(&mesh);
}

#[test]
fn inset_is_proportional_on_a_rectangle_and_preserves_plane_boundary() {
    let mut mesh = Mesh {
        positions: vec![[-2., -1., 0.], [2., -1., 0.], [2., 1., 0.], [-2., 1., 0.]],
        faces: vec![vec![0, 1, 2, 3]],
    };
    mesh.inset_face(0, 0.25).unwrap();
    assert_eq!(mesh.positions[4], [-1.5, -0.75, 0.]);
    assert_eq!(mesh.positions[6], [1.5, 0.75, 0.]);
    assert!((area(&mesh) - 8.).abs() < 1e-6);
    let edges = edges(&mesh);
    assert_eq!(edges.values().filter(|&&(count, _)| count == 1).count(), 4);
    assert!(edges
        .values()
        .all(|&(count, balance)| count == 1 || (count == 2 && balance == 0)));
}

#[test]
fn subdivision_preserves_cube_shape_and_closed_shared_topology() {
    let mut mesh = Mesh::primitive(Primitive::Cube);
    let before = mesh.clone();
    mesh.subdivide().unwrap();
    mesh.validate().unwrap();
    assert_eq!((mesh.positions.len(), mesh.faces.len()), (26, 24));
    assert_eq!(&mesh.positions[..8], &before.positions);
    assert!(mesh.faces.iter().all(|face| face.len() == 4));
    assert!((area(&mesh) - 6.).abs() < 1e-6);
    for face in 0..mesh.faces.len() {
        assert!((mesh.normal(face) - before.normal(face / 4)).length() < 1e-6);
    }
    closed(&mesh);
    mesh.subdivide().unwrap();
    assert_eq!((mesh.positions.len(), mesh.faces.len()), (98, 96));
    closed(&mesh);
}

#[test]
fn subdivision_plane_and_adjacent_faces_share_exact_midpoint_ids() {
    let mut plane = Mesh::primitive(Primitive::Plane);
    plane.subdivide().unwrap();
    assert_eq!((plane.positions.len(), plane.faces.len()), (9, 4));
    assert_eq!(
        edges(&plane)
            .values()
            .filter(|&&(count, _)| count == 1)
            .count(),
        8
    );
    assert!((area(&plane) - 4.).abs() < 1e-6);
    let mut neighbors = Mesh {
        positions: vec![
            [0., 0., 0.],
            [1., 0., 0.],
            [2., 0., 0.],
            [0., 1., 0.],
            [1., 1., 0.],
            [2., 1., 0.],
        ],
        faces: vec![vec![0, 1, 4, 3], vec![1, 2, 5, 4]],
    };
    neighbors.subdivide().unwrap();
    assert_eq!((neighbors.positions.len(), neighbors.faces.len()), (15, 8));
    let midpoint_ids: Vec<_> = neighbors
        .positions
        .iter()
        .enumerate()
        .filter(|(_, p)| **p == [1., 0.5, 0.])
        .map(|(i, _)| i as u32)
        .collect();
    assert_eq!(midpoint_ids.len(), 1);
    let midpoint = midpoint_ids[0];
    assert_eq!(
        neighbors
            .faces
            .iter()
            .filter(|face| face.contains(&midpoint))
            .count(),
        4
    );
    let edges = edges(&neighbors);
    assert_eq!(edges[&(1, midpoint)], (2, 0));
    assert_eq!(edges[&(4, midpoint)], (2, 0));
    assert_eq!(edges.values().filter(|&&(count, _)| count == 1).count(), 12);
}

#[test]
fn solid_primitives_support_inset_then_subdivision_without_cracks() {
    for primitive in [Primitive::Cube, Primitive::Sphere, Primitive::Cylinder] {
        let mut mesh = Mesh::primitive(primitive);
        mesh.inset_face(0, 0.2).unwrap();
        closed(&mesh);
        mesh.subdivide().unwrap();
        mesh.validate().unwrap();
        closed(&mesh);
    }
}

#[test]
fn invalid_factors_face_indices_and_precision_collapse_are_atomic() {
    let mut mesh = Mesh::primitive(Primitive::Cube);
    let before = mesh.clone();
    for factor in [
        f32::NAN,
        f32::INFINITY,
        f32::NEG_INFINITY,
        -0.2,
        0.,
        1.,
        1.2,
        f32::MIN_POSITIVE,
    ] {
        assert!(mesh.inset_face(0, factor).is_err(), "factor {factor}");
        unchanged(&mesh, &before);
    }
    assert!(mesh.inset_face(usize::MAX, 0.2).is_err());
    unchanged(&mesh, &before);
    // A legitimate input at this magnitude has no representable edge midpoints.
    let base = 999_999_f32;
    let adjacent = f32::from_bits(base.to_bits() + 1);
    let mut tiny = Mesh {
        positions: vec![
            [base, base, 0.],
            [adjacent, base, 0.],
            [adjacent, adjacent, 0.],
            [base, adjacent, 0.],
        ],
        faces: vec![vec![0, 1, 2, 3]],
    };
    tiny.validate().unwrap();
    let before = tiny.clone();
    assert!(tiny.subdivide().is_err());
    unchanged(&tiny, &before);
    assert!(tiny.inset_face(0, 0.9).is_err());
    unchanged(&tiny, &before);
}

#[test]
fn malformed_and_degenerate_meshes_are_rejected_without_panics_or_mutation() {
    let valid = Mesh::primitive(Primitive::Plane);
    let mut cases = Vec::new();
    for face in [vec![], vec![0, 1], vec![0, 1, 99], vec![0, 1, 1]] {
        let mut mesh = valid.clone();
        mesh.faces[0] = face;
        cases.push(mesh);
    }
    for point in [[f32::NAN, 0., 0.], [f32::INFINITY, 0., 0.], [2e6, 0., 0.]] {
        let mut mesh = valid.clone();
        mesh.positions[0] = point;
        cases.push(mesh);
    }
    cases.push(Mesh {
        positions: vec![[0.; 3]; 3],
        faces: vec![vec![0, 1, 2]],
    });
    // Valid first triangle, but a collapsed final edge hidden by distinct IDs.
    cases.push(Mesh {
        positions: vec![[0., 0., 0.], [1., 0., 0.], [0., 1., 0.], [0., 1., 0.]],
        faces: vec![vec![0, 1, 2, 3]],
    });
    for mut mesh in cases {
        let before = mesh.clone();
        assert!(mesh.inset_face(0, 0.2).is_err());
        unchanged(&mesh, &before);
        assert!(mesh.subdivide().is_err());
        unchanged(&mesh, &before);
    }
}

#[test]
fn output_limits_are_preflighted_and_atomic() {
    let mut vertex_limit = Mesh::primitive(Primitive::Cube);
    vertex_limit.positions.resize(MAX_VERTICES - 3, [0.; 3]);
    let before = vertex_limit.clone();
    assert!(vertex_limit
        .inset_face(0, 0.2)
        .unwrap_err()
        .contains("limit"));
    unchanged(&vertex_limit, &before);
    assert!(vertex_limit.subdivide().unwrap_err().contains("limit"));
    unchanged(&vertex_limit, &before);

    // Face centers alone fit, but adding the shared edge midpoints exceeds the budget.
    let mut edge_limit = Mesh::primitive(Primitive::Plane);
    edge_limit.positions.resize(MAX_VERTICES - 4, [0.; 3]);
    let before = edge_limit.clone();
    assert!(edge_limit.subdivide().unwrap_err().contains("limit"));
    unchanged(&edge_limit, &before);

    let mut face_limit = Mesh::primitive(Primitive::Plane);
    face_limit.faces.resize(MAX_FACES - 3, vec![0, 3, 2, 1]);
    let before = face_limit.clone();
    assert!(face_limit.inset_face(0, 0.2).unwrap_err().contains("limit"));
    unchanged(&face_limit, &before);
    assert!(face_limit.subdivide().unwrap_err().contains("limit"));
    unchanged(&face_limit, &before);
}

#[test]
fn edited_mesh_exports_and_reimports_with_topology_intact() {
    let mut mesh = Mesh::primitive(Primitive::Cube);
    mesh.inset_face(1, 0.2).unwrap();
    mesh.subdivide().unwrap();
    let scene = Scene {
        objects: vec![Object {
            id: new_id(),
            name: "Inset subdivision".into(),
            transform: Transform::default(),
            color: [0.5; 3],
            visible: true,
            mesh: mesh.clone(),
        }],
        ..Scene::default()
    };
    let restored = obj::parse(&obj::export(&scene).unwrap()).unwrap();
    assert_eq!(restored, mesh);
    closed(&restored);
}
