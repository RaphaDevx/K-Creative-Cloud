use editor_3d::{
    camera::Camera,
    manipulation::{axis_handle, pick_axis, selection_pivot, snap_delta, Axis, AxisDrag},
    mesh::{Mesh, Primitive},
    scene::{new_id, Object, Scene, Transform},
};
use glam::{Vec2, Vec3};

const VIEWPORT: [f32; 2] = [1000., 800.];

fn camera_front() -> Camera {
    Camera {
        yaw: 0.,
        pitch: 0.,
        distance: 6.,
        target: Vec3::ZERO,
    }
}

// Independent projection through the renderer's actual camera matrix.
fn pixel(camera: &Camera, point: Vec3) -> [f32; 2] {
    let clip = camera.matrix(VIEWPORT[0] / VIEWPORT[1]) * point.extend(1.);
    let ndc = clip.truncate() / clip.w;
    [
        (ndc.x + 1.) * 0.5 * VIEWPORT[0],
        (1. - ndc.y) * 0.5 * VIEWPORT[1],
    ]
}

fn near(actual: Vec3, expected: Vec3, tolerance: f32) {
    assert!(
        actual.distance(expected) <= tolerance,
        "actual={actual:?} expected={expected:?}"
    );
}

#[test]
fn axis_identity_is_world_aligned() {
    assert_eq!((Axis::X.vector(), Axis::X.label()), (Vec3::X, "X"));
    assert_eq!((Axis::Y.vector(), Axis::Y.label()), (Vec3::Y, "Y"));
    assert_eq!((Axis::Z.vector(), Axis::Z.label()), (Vec3::Z, "Z"));
}

#[test]
fn handles_keep_screen_size_across_zoom_angles_and_aspect_ratios() {
    for distance in [0.15, 1., 6., 2000.] {
        for (yaw, pitch) in [(0.72, 0.48), (-0.6, -0.4), (2.4, 1.0)] {
            let camera = Camera {
                yaw,
                pitch,
                distance,
                target: Vec3::ZERO,
            };
            for viewport in [VIEWPORT, [800., 1000.], [1600., 600.]] {
                for axis in [Axis::X, Axis::Y, Axis::Z] {
                    let handle = axis_handle(&camera, Vec3::ZERO, axis, viewport).unwrap();
                    let length = Vec2::from(handle.start).distance(Vec2::from(handle.end));
                    assert!(
                        (length - 80.).abs() < 0.001,
                        "{distance} {axis:?}: {length}"
                    );
                    assert!(handle.world_length.is_finite() && handle.world_length > 0.);
                    let clip = camera.matrix(viewport[0] / viewport[1])
                        * (axis.vector() * handle.world_length).extend(1.);
                    let ndc = clip.truncate() / clip.w;
                    let expected = Vec2::new(
                        (ndc.x + 1.) * 0.5 * viewport[0],
                        (1. - ndc.y) * 0.5 * viewport[1],
                    );
                    assert!(expected.distance(Vec2::from(handle.end)) < 0.002);
                }
            }
        }
    }
    let mut camera = camera_front();
    let close = axis_handle(&camera, Vec3::ZERO, Axis::X, VIEWPORT).unwrap();
    camera.distance *= 10.;
    let far = axis_handle(&camera, Vec3::ZERO, Axis::X, VIEWPORT).unwrap();
    assert!((far.world_length / close.world_length - 10.).abs() < 1e-5);
}

#[test]
fn picking_excludes_center_offscreen_handles_and_near_parallel_axes() {
    let camera = camera_front();
    let center = pixel(&camera, Vec3::ZERO);
    assert_eq!(pick_axis(&camera, Vec3::ZERO, center, VIEWPORT, 6.), None);
    assert_eq!(
        pick_axis(
            &camera,
            Vec3::ZERO,
            [center[0] + 9., center[1]],
            VIEWPORT,
            6.
        ),
        None
    );
    assert_eq!(
        pick_axis(
            &camera,
            Vec3::ZERO,
            [center[0] + 50., center[1] + 3.],
            VIEWPORT,
            6.
        ),
        Some(Axis::X)
    );
    assert_eq!(
        pick_axis(
            &camera,
            Vec3::ZERO,
            [center[0], center[1] - 50.],
            VIEWPORT,
            6.
        ),
        Some(Axis::Y)
    );
    assert_eq!(
        pick_axis(
            &camera,
            Vec3::ZERO,
            [center[0] + 50., center[1] + 9.],
            VIEWPORT,
            6.
        ),
        None
    );
    assert!(axis_handle(&camera, Vec3::ZERO, Axis::Z, VIEWPORT).is_none());
    assert!(AxisDrag::new(&camera, Vec3::ZERO, Axis::Z, center, VIEWPORT).is_none());
    let almost_parallel = Camera {
        yaw: 0.02,
        ..camera.clone()
    };
    assert!(axis_handle(&almost_parallel, Vec3::ZERO, Axis::Z, VIEWPORT).is_none());
    // This pivot is visible, but its +X endpoint would fall outside the viewport.
    let edge_pivot = Vec3::new(3., 0., 0.);
    assert!(pixel(&camera, edge_pivot)[0] < VIEWPORT[0]);
    assert!(axis_handle(&camera, edge_pivot, Axis::X, VIEWPORT).is_none());
    assert!(axis_handle(&camera, Vec3::new(20., 0., 0.), Axis::X, VIEWPORT).is_none());
    assert!(axis_handle(&camera, Vec3::new(0., 0., 7.), Axis::X, VIEWPORT).is_none());
    assert_eq!(
        pick_axis(&camera, Vec3::ZERO, [-1., 400.], VIEWPORT, 6.),
        None
    );
}

#[test]
fn ray_drag_follows_world_axes_at_different_camera_angles_and_zoom() {
    for distance in [0.15, 6., 2000.] {
        for (yaw, pitch) in [(0.72, 0.48), (-0.6, -0.4), (2.4, 1.0)] {
            let camera = Camera {
                yaw,
                pitch,
                distance,
                target: Vec3::new(1., 2., 3.),
            };
            let pivot = camera.target;
            for axis in [Axis::X, Axis::Y, Axis::Z] {
                let handle = axis_handle(&camera, pivot, axis, VIEWPORT).unwrap();
                let start = handle.world_length * 0.4;
                let initial = pixel(&camera, pivot + axis.vector() * start);
                let drag = AxisDrag::new(&camera, pivot, axis, initial, VIEWPORT).unwrap();
                assert_eq!(drag.delta(initial, None), Some([0.; 3]));
                for movement in [-0.15, 0.3] {
                    let displacement = handle.world_length * movement;
                    let pointer = pixel(&camera, pivot + axis.vector() * (start + displacement));
                    let actual = Vec3::from(drag.delta(pointer, None).unwrap());
                    near(
                        actual,
                        axis.vector() * displacement,
                        (distance * 0.000002).max(0.000002),
                    );
                }
            }
        }
    }
}

#[test]
fn off_center_grabs_start_at_zero_and_camera_changes_do_not_change_snapshot() {
    let mut camera = camera_front();
    let start = [540., 405.];
    let drag = AxisDrag::new(&camera, Vec3::ZERO, Axis::X, start, VIEWPORT).unwrap();
    assert_eq!(drag.delta(start, None), Some([0.; 3]));
    let pointer = [580., 405.];
    let displacement = drag.delta(pointer, None).unwrap();
    assert!(displacement[0] > 0.);
    assert_eq!(displacement[1..], [0., 0.]);
    camera.orbit(200., 100.);
    camera.zoom(-50.);
    camera.pan(100., 100.);
    assert_eq!(drag.delta(pointer, None), Some(displacement));
    assert_eq!(drag.delta(start, Some(0.25)), Some([0.; 3]));
    // Captured dragging remains usable beyond the viewport rather than freezing.
    assert!(drag.delta([1200., 405.], None).unwrap()[0] > displacement[0]);
}

#[test]
fn snapping_rounds_relative_displacement_symmetrically_without_accumulation() {
    assert_eq!(
        snap_delta([0.24, -0.24, 0.], Some(0.5)).unwrap(),
        [0., 0., 0.]
    );
    assert_eq!(
        snap_delta([0.25, -0.25, 0.76], Some(0.5)).unwrap(),
        [0.5, -0.5, 1.]
    );
    assert_eq!(
        snap_delta([0.31, -1.7, 2.], None).unwrap(),
        [0.31, -1.7, 2.]
    );
    assert_eq!(
        snap_delta([500., -500., 0.], Some(1000.)).unwrap(),
        [1000., -1000., 0.]
    );
    // Positive subnormal steps remain finite: intermediate division uses f64.
    assert!(snap_delta([1., -1., f32::MAX], Some(f32::from_bits(1)))
        .unwrap()
        .iter()
        .all(|v| v.is_finite()));
    let camera = camera_front();
    let initial = pixel(&camera, Vec3::new(0.2, 0., 0.));
    let drag = AxisDrag::new(&camera, Vec3::ZERO, Axis::X, initial, VIEWPORT).unwrap();
    let pointer = pixel(&camera, Vec3::new(0.56, 0., 0.));
    assert_eq!(drag.delta(pointer, Some(0.25)).unwrap(), [0.25, 0., 0.]);
    near(
        Vec3::from(drag.delta(pointer, None).unwrap()),
        Vec3::new(0.36, 0., 0.),
        1e-5,
    );
    assert_eq!(drag.delta(pointer, Some(0.25)).unwrap(), [0.25, 0., 0.]);
    assert_eq!(drag.delta(initial, Some(0.25)).unwrap(), [0.; 3]);
}

#[test]
fn invalid_inputs_fail_without_nonfinite_output() {
    let camera = camera_front();
    for step in [0., -1., 1001., f32::NAN, f32::INFINITY] {
        assert!(snap_delta([1., 2., 3.], Some(step)).is_err());
    }
    for invalid in [f32::NAN, f32::INFINITY, f32::NEG_INFINITY] {
        assert!(snap_delta([invalid, 0., 0.], None).is_err());
        assert!(axis_handle(&camera, Vec3::new(invalid, 0., 0.), Axis::X, VIEWPORT).is_none());
        assert!(pick_axis(&camera, Vec3::ZERO, [550., 400.], VIEWPORT, invalid).is_none());
    }
    for viewport in [
        [0., 800.],
        [-1., 800.],
        [800., f32::NAN],
        [f32::INFINITY, 800.],
        [1., 800.],
    ] {
        assert!(axis_handle(&camera, Vec3::ZERO, Axis::X, viewport).is_none());
        assert!(AxisDrag::new(&camera, Vec3::ZERO, Axis::X, [500., 400.], viewport).is_none());
    }
    for invalid_camera in [
        Camera {
            distance: 0.,
            ..camera.clone()
        },
        Camera {
            distance: -1.,
            ..camera.clone()
        },
        Camera {
            distance: f32::NAN,
            ..camera.clone()
        },
        Camera {
            yaw: f32::INFINITY,
            ..camera.clone()
        },
        Camera {
            pitch: std::f32::consts::FRAC_PI_2,
            ..camera.clone()
        },
        Camera {
            target: Vec3::splat(f32::NAN),
            ..camera.clone()
        },
        Camera {
            distance: 20000.,
            ..camera.clone()
        },
    ] {
        assert!(axis_handle(&invalid_camera, Vec3::ZERO, Axis::X, VIEWPORT).is_none());
    }
    assert!(pick_axis(&camera, Vec3::ZERO, [550., 400.], VIEWPORT, -1.).is_none());
    assert!(AxisDrag::new(&camera, Vec3::ZERO, Axis::X, [f32::NAN, 400.], VIEWPORT).is_none());
    let drag = AxisDrag::new(&camera, Vec3::ZERO, Axis::X, [540., 400.], VIEWPORT).unwrap();
    assert!(drag.delta([f32::NAN, 400.], None).is_none());
    assert!(drag.delta([580., 400.], Some(0.)).is_none());
    assert!(drag.delta([f32::MAX, 400.], None).is_none());
}

fn object(translation: [f32; 3], scale: [f32; 3]) -> Object {
    Object {
        id: new_id(),
        name: "Bounds fixture".into(),
        transform: Transform {
            translation,
            scale,
            ..Transform::default()
        },
        color: [0.5; 3],
        visible: true,
        mesh: Mesh::primitive(Primitive::Cube),
    }
}

#[test]
fn selection_pivot_uses_rotated_scaled_world_bounds_and_ignores_hidden_objects() {
    let mut rotated = object([3., 4., 0.], [2., 1., 1.]);
    rotated.transform.rotation_degrees[2] = 90.;
    for position in &mut rotated.mesh.positions {
        position[0] += 1.;
    }
    let second = object([-2., 1., 0.], [2.; 3]);
    let mut hidden = object([1000.; 3], [10.; 3]);
    hidden.visible = false;
    let ids = vec![
        rotated.id.clone(),
        second.id.clone(),
        hidden.id.clone(),
        rotated.id.clone(),
        "missing".into(),
    ];
    let scene = Scene {
        objects: vec![rotated, second, hidden],
        ..Scene::default()
    };
    let before = scene.clone();
    near(
        selection_pivot(&scene, &ids).unwrap(),
        Vec3::new(0.25, 3.5, 0.),
        1e-5,
    );
    near(
        selection_pivot(&scene, &ids[..1]).unwrap(),
        Vec3::new(3., 6., 0.),
        1e-5,
    );
    assert_eq!(selection_pivot(&scene, &[]), None);
    assert_eq!(selection_pivot(&scene, &["missing".into()]), None);
    assert_eq!(selection_pivot(&scene, &[ids[2].clone()]), None);
    assert_eq!(scene, before);
}

#[test]
fn selection_pivot_rejects_invalid_selected_geometry() {
    let selected = object([0.; 3], [1.; 3]);
    let ids = vec![selected.id.clone()];
    let mut scene = Scene {
        objects: vec![selected],
        ..Scene::default()
    };
    scene.objects[0].transform.translation[0] = f32::INFINITY;
    assert!(selection_pivot(&scene, &ids).is_none());
    scene.objects[0].transform = Transform::default();
    scene.objects[0].mesh.positions[0][0] = f32::NAN;
    assert!(selection_pivot(&scene, &ids).is_none());
    scene.objects[0].mesh.positions.clear();
    assert!(selection_pivot(&scene, &ids).is_none());
}
