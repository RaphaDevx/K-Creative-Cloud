use editor_3d::{
    camera::Camera,
    mesh::{Mesh, Primitive},
    scene::{Object, Scene, Transform},
    selection::{pick_element, project_point, Element, ElementMode},
};
use glam::Vec3;

const VIEWPORT: [f32; 2] = [800., 600.];

fn camera() -> Camera {
    Camera {
        yaw: 0.,
        pitch: 0.,
        distance: 5.,
        target: Vec3::ZERO,
    }
}

fn object(id: &str, mesh: Mesh) -> Object {
    Object {
        id: id.into(),
        name: id.into(),
        transform: Transform::default(),
        color: [0.5; 3],
        visible: true,
        mesh,
    }
}

fn quad(z: f32, size: f32) -> Mesh {
    Mesh {
        positions: vec![
            [-size, -size, z],
            [size, -size, z],
            [size, size, z],
            [-size, size, z],
        ],
        faces: vec![vec![0, 1, 2, 3]],
    }
}

fn scene(objects: Vec<Object>) -> Scene {
    Scene {
        objects,
        ..Scene::default()
    }
}

fn pixel(point: [f32; 3]) -> [f32; 2] {
    project_point(&camera(), Vec3::from(point), VIEWPORT).unwrap()
}

#[test]
fn projection_uses_top_left_logical_pixels() {
    assert_eq!(pixel([0., 0., 0.]), [400., 300.]);
    let projected = pixel([1., 1., 0.]);
    assert!((projected[0] - 544.8528).abs() < 0.001);
    assert!((projected[1] - 155.1472).abs() < 0.001);
    assert_eq!(
        project_point(&camera(), Vec3::new(0., 0., 6.), VIEWPORT),
        None
    );
    assert_eq!(project_point(&camera(), camera().eye(), VIEWPORT), None);
}

#[test]
fn picks_vertices_with_pixel_threshold_at_silhouette() {
    let scene = scene(vec![object("quad", quad(0., 1.))]);
    let p = pixel([-1., -1., 0.]);
    let hit = pick_element(
        &scene,
        &camera(),
        [p[0] - 4., p[1] + 3.],
        VIEWPORT,
        ElementMode::Vertex,
        6.,
    )
    .unwrap();
    assert_eq!(hit.object_id, "quad");
    assert_eq!(hit.element, Element::Vertex(0));
    assert!(pick_element(
        &scene,
        &camera(),
        [p[0] - 4., p[1] + 3.],
        VIEWPORT,
        ElementMode::Vertex,
        4.
    )
    .is_none());
}

#[test]
fn picks_sorted_polygon_edges_without_fan_diagonals() {
    let mut mesh = quad(0., 1.);
    mesh.faces.push(vec![3, 2, 1, 0]);
    let scene = scene(vec![object("quad", mesh)]);
    let hit = pick_element(
        &scene,
        &camera(),
        pixel([-1., 0., 0.]),
        VIEWPORT,
        ElementMode::Edge,
        2.,
    )
    .unwrap();
    assert_eq!(hit.element, Element::Edge([0, 3]));
    assert!(pick_element(
        &scene,
        &camera(),
        [400., 300.],
        VIEWPORT,
        ElementMode::Edge,
        5.
    )
    .is_none());
}

#[test]
fn nearer_surfaces_hide_vertices_and_edges_even_without_nearby_elements() {
    let scene = scene(vec![
        object("rear", quad(0., 0.4)),
        object("cover", quad(1., 2.)),
    ]);
    assert!(pick_element(
        &scene,
        &camera(),
        pixel([-0.4, -0.4, 0.]),
        VIEWPORT,
        ElementMode::Vertex,
        2.
    )
    .is_none());
    assert!(pick_element(
        &scene,
        &camera(),
        pixel([0., -0.4, 0.]),
        VIEWPORT,
        ElementMode::Edge,
        2.
    )
    .is_none());
}

#[test]
fn hidden_objects_neither_pick_nor_occlude() {
    let mut cover = object("cover", quad(1., 2.));
    cover.visible = false;
    let scene = scene(vec![object("rear", quad(0., 0.4)), cover]);
    assert_eq!(
        pick_element(
            &scene,
            &camera(),
            pixel([-0.4, -0.4, 0.]),
            VIEWPORT,
            ElementMode::Vertex,
            2.
        )
        .unwrap()
        .object_id,
        "rear"
    );
    assert!(pick_element(
        &scene,
        &camera(),
        pixel([-2., -2., 1.]),
        VIEWPORT,
        ElementMode::Vertex,
        2.
    )
    .is_none());
}

#[test]
fn cube_back_vertices_and_edges_are_occluded_by_its_own_front_faces() {
    let scene = scene(vec![object("cube", Mesh::primitive(Primitive::Cube))]);
    assert!(pick_element(
        &scene,
        &camera(),
        pixel([-0.5, -0.5, -0.5]),
        VIEWPORT,
        ElementMode::Vertex,
        1.
    )
    .is_none());
    assert!(pick_element(
        &scene,
        &camera(),
        pixel([0., -0.5, -0.5]),
        VIEWPORT,
        ElementMode::Edge,
        1.
    )
    .is_none());
    assert_eq!(
        pick_element(
            &scene,
            &camera(),
            pixel([-0.5, -0.5, 0.5]),
            VIEWPORT,
            ElementMode::Vertex,
            1.
        )
        .unwrap()
        .element,
        Element::Vertex(4)
    );
}

#[test]
fn transformed_vertices_and_edges_use_world_space() {
    let mut mesh_object = object("transformed", quad(0., 0.5));
    mesh_object.transform.translation = [0.6, 0.4, 0.3];
    mesh_object.transform.rotation_degrees = [0., 35., 40.];
    mesh_object.transform.scale = [1.5, 0.8, 2.];
    let matrix = mesh_object.transform.matrix();
    let vertex = matrix.transform_point3(Vec3::from(mesh_object.mesh.positions[2]));
    let edge = matrix.transform_point3(Vec3::new(0.5, 0., 0.));
    let scene = scene(vec![mesh_object]);
    assert_eq!(
        pick_element(
            &scene,
            &camera(),
            project_point(&camera(), vertex, VIEWPORT).unwrap(),
            VIEWPORT,
            ElementMode::Vertex,
            2.
        )
        .unwrap()
        .element,
        Element::Vertex(2)
    );
    assert_eq!(
        pick_element(
            &scene,
            &camera(),
            project_point(&camera(), edge, VIEWPORT).unwrap(),
            VIEWPORT,
            ElementMode::Edge,
            2.
        )
        .unwrap()
        .element,
        Element::Edge([1, 2])
    );
}

#[test]
fn overlapping_elements_prefer_nearer_depth_independent_of_scene_order() {
    let rear = object("rear", quad(0., 1.));
    let front = object("front", quad(1., 0.8));
    let scene = scene(vec![rear, front]);
    assert_eq!(
        pick_element(
            &scene,
            &camera(),
            pixel([-1., -1., 0.]),
            VIEWPORT,
            ElementMode::Vertex,
            1.
        )
        .unwrap()
        .object_id,
        "front"
    );
}

#[test]
fn an_edge_crossing_viewport_boundary_remains_pickable() {
    let scene = scene(vec![object("large", quad(0., 4.))]);
    // Vertical edges are offscreen; this horizontal edge lies across the view.
    let mut scene = scene;
    scene.objects[0].mesh.positions[0][1] = -0.5;
    scene.objects[0].mesh.positions[1][1] = -0.5;
    let hit = pick_element(
        &scene,
        &camera(),
        pixel([0., -0.5, 0.]),
        VIEWPORT,
        ElementMode::Edge,
        2.,
    )
    .unwrap();
    assert_eq!(hit.element, Element::Edge([0, 1]));
}

#[test]
fn edge_occlusion_uses_perspective_correct_world_position() {
    let slanted = Mesh {
        positions: vec![[-1., -0.5, 0.], [1., -0.5, 3.], [1., 1., 3.]],
        faces: vec![vec![0, 1, 2]],
    };
    let mut cover = object("cover", quad(2., 0.3));
    cover.transform.translation[1] = -0.5;
    let mut scene = scene(vec![object("slanted", slanted), cover]);
    let pointer = pixel([0., -0.5, 1.5]);
    assert!(pick_element(&scene, &camera(), pointer, VIEWPORT, ElementMode::Edge, 1.).is_none());
    scene.objects[1].visible = false;
    assert_eq!(
        pick_element(&scene, &camera(), pointer, VIEWPORT, ElementMode::Edge, 1.)
            .unwrap()
            .element,
        Element::Edge([0, 1])
    );
}

#[test]
fn edge_crossing_near_plane_can_be_picked_on_visible_portion() {
    let mesh = Mesh {
        positions: vec![[-0.2, 0., 4.995], [1., 0., 0.], [0., 1., 0.]],
        faces: vec![vec![0, 1, 2]],
    };
    let midpoint = (Vec3::from(mesh.positions[0]) + Vec3::from(mesh.positions[1])) * 0.5;
    let scene = scene(vec![object("clipped", mesh)]);
    assert_eq!(
        pick_element(
            &scene,
            &camera(),
            project_point(&camera(), midpoint, VIEWPORT).unwrap(),
            VIEWPORT,
            ElementMode::Edge,
            1.
        )
        .unwrap()
        .element,
        Element::Edge([0, 1])
    );
}

#[test]
fn invalid_inputs_and_behind_camera_geometry_return_none() {
    let scene = scene(vec![object("behind", quad(6., 1.))]);
    for mode in [ElementMode::Vertex, ElementMode::Edge] {
        assert!(pick_element(&scene, &camera(), [400., 300.], VIEWPORT, mode, 1000.).is_none());
        for viewport in [
            [0., 600.],
            [-1., 600.],
            [800., f32::NAN],
            [f32::INFINITY, 600.],
        ] {
            assert!(pick_element(&scene, &camera(), [0., 0.], viewport, mode, 10.).is_none());
            assert!(project_point(&camera(), Vec3::ZERO, viewport).is_none());
        }
        for threshold in [-1., f32::NAN, f32::INFINITY] {
            assert!(
                pick_element(&scene, &camera(), [400., 300.], VIEWPORT, mode, threshold).is_none()
            );
        }
        assert!(pick_element(&scene, &camera(), [f32::NAN, 0.], VIEWPORT, mode, 10.).is_none());
        assert!(pick_element(&scene, &camera(), [-1., 300.], VIEWPORT, mode, 10.).is_none());
    }
    let mut invalid_camera = camera();
    invalid_camera.distance = 0.;
    assert!(project_point(&invalid_camera, Vec3::ZERO, VIEWPORT).is_none());
    assert!(pick_element(
        &scene,
        &invalid_camera,
        [400., 300.],
        VIEWPORT,
        ElementMode::Vertex,
        10.
    )
    .is_none());
}
