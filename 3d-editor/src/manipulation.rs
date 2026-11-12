//! Headless world-axis translation math. Gestures return relative displacement;
//! the caller applies one command group to the original selection on release.
use crate::{camera::Camera, scene::Scene, Result};
use glam::{DVec2, DVec3, Vec3};

const HANDLE_PIXELS: f64 = 80.;
const CENTER_PIXELS: f64 = 10.;
const MIN_AXIS_SINE_SQUARED: f64 = 0.01;
const NEAR: f64 = 0.01;
const FAR: f64 = 10000.;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Axis {
    X,
    Y,
    Z,
}

impl Axis {
    pub fn vector(self) -> Vec3 {
        match self {
            Self::X => Vec3::X,
            Self::Y => Vec3::Y,
            Self::Z => Vec3::Z,
        }
    }

    pub fn label(self) -> &'static str {
        match self {
            Self::X => "X",
            Self::Y => "Y",
            Self::Z => "Z",
        }
    }
}

#[derive(Clone, Copy, Debug)]
pub struct AxisHandle {
    pub start: [f32; 2],
    pub end: [f32; 2],
    pub world_length: f32,
}

// Analytic projection avoids inverse-matrix precision loss around the 0.01 m
// near plane at large camera distances. This matches Camera's 45° perspective.
#[derive(Clone, Debug)]
struct CameraFrame {
    eye: DVec3,
    forward: DVec3,
    right: DVec3,
    up: DVec3,
    viewport: DVec2,
    focal: f64,
}

impl CameraFrame {
    fn new(camera: &Camera, viewport: [f32; 2]) -> Option<Self> {
        if !camera.yaw.is_finite()
            || !camera.pitch.is_finite()
            || !camera.distance.is_finite()
            || camera.distance <= 0.
            || !camera.target.is_finite()
            || viewport.iter().any(|v| !v.is_finite() || *v <= 0.)
            // Camera::matrix clamps narrower aspect ratios to 0.01.
            || f64::from(viewport[0]) / f64::from(viewport[1]) < 0.01
        {
            return None;
        }
        let eye = camera.eye().as_dvec3();
        let forward = (camera.target.as_dvec3() - eye).try_normalize()?;
        let horizontal = forward.cross(DVec3::Y);
        if !eye.is_finite() || horizontal.length_squared() < 1e-8 {
            return None;
        }
        let right = horizontal.try_normalize()?;
        Some(Self {
            eye,
            forward,
            right,
            up: right.cross(forward),
            viewport: DVec2::from_array(viewport.map(f64::from)),
            focal: f64::from(viewport[1]) / (2. * (45f64.to_radians() * 0.5).tan()),
        })
    }

    fn contains(&self, point: DVec2) -> bool {
        point.is_finite()
            && point.x >= 0.
            && point.y >= 0.
            && point.x <= self.viewport.x
            && point.y <= self.viewport.y
    }

    fn project(&self, point: DVec3) -> Option<DVec2> {
        let relative = point - self.eye;
        let depth = relative.dot(self.forward);
        if !point.is_finite() || !(NEAR..=FAR).contains(&depth) {
            return None;
        }
        let pixel = self.viewport * 0.5
            + DVec2::new(relative.dot(self.right), -relative.dot(self.up)) * self.focal / depth;
        self.contains(pixel).then_some(pixel)
    }

    fn ray(&self, pointer: [f32; 2]) -> Option<DVec3> {
        let pointer = DVec2::from_array(pointer.map(f64::from));
        if !pointer.is_finite() {
            return None;
        }
        let offset = (pointer - self.viewport * 0.5) / self.focal;
        (self.forward + self.right * offset.x - self.up * offset.y).try_normalize()
    }

    fn handle(&self, pivot: Vec3, axis: Axis) -> Option<AxisHandle> {
        let pivot = pivot.as_dvec3();
        let start = self.project(pivot)?;
        let axis = axis.vector().as_dvec3();
        let relative = pivot - self.eye;
        let view = relative.try_normalize()?;
        if 1. - view.dot(axis).powi(2) < MIN_AXIS_SINE_SQUARED {
            return None;
        }
        let depth = relative.dot(self.forward);
        let axis_depth = axis.dot(self.forward);
        let derivative = DVec2::new(
            axis.dot(self.right) * depth - relative.dot(self.right) * axis_depth,
            -axis.dot(self.up) * depth + relative.dot(self.up) * axis_depth,
        ) * self.focal
            / depth.powi(2);
        // Solve the perspective projection for an exactly 80 px segment.
        let denominator = derivative.length() - HANDLE_PIXELS * axis_depth / depth;
        if !denominator.is_finite() || denominator <= 0. {
            return None;
        }
        let world_length = (HANDLE_PIXELS / denominator) as f32;
        if !world_length.is_finite() || world_length <= 0. {
            return None;
        }
        let end = self.project(pivot + axis * f64::from(world_length))?;
        Some(AxisHandle {
            start: start.as_vec2().to_array(),
            end: end.as_vec2().to_array(),
            world_length,
        })
    }

    fn axis_parameter(&self, pivot: DVec3, axis: DVec3, pointer: [f32; 2]) -> Option<f64> {
        let ray = self.ray(pointer)?;
        let alignment = ray.dot(axis);
        let denominator = 1. - alignment * alignment;
        if denominator < MIN_AXIS_SINE_SQUARED {
            return None;
        }
        let offset = self.eye - pivot;
        let parameter = (offset.dot(axis) - alignment * offset.dot(ray)) / denominator;
        let ray_distance = alignment * parameter - offset.dot(ray);
        (parameter.is_finite() && ray_distance > 0.).then_some(parameter)
    }
}

/// Viewport-local logical pixel coordinates; clipped and nearly end-on axes
/// have no handle. World length changes with zoom to keep the handle at 80 px.
pub fn axis_handle(
    camera: &Camera,
    pivot: Vec3,
    axis: Axis,
    viewport: [f32; 2],
) -> Option<AxisHandle> {
    CameraFrame::new(camera, viewport)?.handle(pivot, axis)
}

/// Picks the nearest visible segment, leaving a 10 px disc around the pivot
/// available for ordinary scene selection. Threshold is in logical pixels.
pub fn pick_axis(
    camera: &Camera,
    pivot: Vec3,
    pointer: [f32; 2],
    viewport: [f32; 2],
    threshold: f32,
) -> Option<Axis> {
    if !threshold.is_finite() || threshold < 0. {
        return None;
    }
    let frame = CameraFrame::new(camera, viewport)?;
    let pointer = DVec2::from_array(pointer.map(f64::from));
    let center = frame.project(pivot.as_dvec3())?;
    if !frame.contains(pointer) || pointer.distance(center) <= CENTER_PIXELS {
        return None;
    }
    let mut closest = f64::from(threshold);
    let mut hit = None;
    for axis in [Axis::X, Axis::Y, Axis::Z] {
        let Some(handle) = frame.handle(pivot, axis) else {
            continue;
        };
        let start = DVec2::from_array(handle.start.map(f64::from));
        let segment = DVec2::from_array(handle.end.map(f64::from)) - start;
        let fraction = ((pointer - start).dot(segment) / segment.length_squared()).clamp(0., 1.);
        let distance = pointer.distance(start + segment * fraction);
        if distance <= closest {
            closest = distance;
            hit = Some(axis);
        }
    }
    hit
}

/// Immutable camera/axis snapshot for a gesture. Deltas are always relative to
/// its initial pointer, so off-center grabs and snap toggles never accumulate.
#[derive(Clone, Debug)]
pub struct AxisDrag {
    frame: CameraFrame,
    pivot: DVec3,
    axis: DVec3,
    initial: f64,
}

impl AxisDrag {
    pub fn new(
        camera: &Camera,
        pivot: Vec3,
        axis: Axis,
        pointer: [f32; 2],
        viewport: [f32; 2],
    ) -> Option<Self> {
        let frame = CameraFrame::new(camera, viewport)?;
        frame.handle(pivot, axis)?;
        if !frame.contains(DVec2::from_array(pointer.map(f64::from))) {
            return None;
        }
        let pivot = pivot.as_dvec3();
        let axis = axis.vector().as_dvec3();
        let initial = frame.axis_parameter(pivot, axis, pointer)?;
        Some(Self {
            frame,
            pivot,
            axis,
            initial,
        })
    }

    /// Pointer may leave the viewport during a captured gesture. Near-parallel
    /// rays and invalid snapping return None, without changing the snapshot.
    pub fn delta(&self, pointer: [f32; 2], snap: Option<f32>) -> Option<[f32; 3]> {
        let parameter = self.frame.axis_parameter(self.pivot, self.axis, pointer)?;
        let delta = (self.axis * (parameter - self.initial))
            .as_vec3()
            .to_array();
        snap_delta(delta, snap).ok()
    }
}

/// Round relative displacement to a positive grid step (at most 1000 m).
/// Half steps round away from zero, including negative displacement.
pub fn snap_delta(delta: [f32; 3], step: Option<f32>) -> Result<[f32; 3]> {
    if delta.iter().any(|value| !value.is_finite()) {
        return Err("Verschiebung muss endlich sein.".into());
    }
    let Some(step) = step else {
        return Ok(delta);
    };
    if !step.is_finite() || step <= 0. || step > 1000. {
        return Err("Rasterschritt muss grösser als 0 und höchstens 1000 m sein.".into());
    }
    let snapped =
        delta.map(|value| ((f64::from(value) / f64::from(step)).round() * f64::from(step)) as f32);
    if snapped.iter().any(|value| !value.is_finite()) {
        return Err("Gerasterte Verschiebung ist nicht endlich.".into());
    }
    Ok(snapped)
}

/// Center of the combined world bounds of selected visible objects. Missing
/// IDs and hidden objects contribute nothing; invalid selected geometry fails.
pub fn selection_pivot(scene: &Scene, ids: &[String]) -> Option<Vec3> {
    let mut minimum = DVec3::splat(f64::INFINITY);
    let mut maximum = DVec3::splat(f64::NEG_INFINITY);
    for object in scene
        .objects
        .iter()
        .filter(|object| object.visible && ids.contains(&object.id))
    {
        object.transform.validate().ok()?;
        let matrix = object.transform.matrix();
        for position in &object.mesh.positions {
            let point = matrix.transform_point3(Vec3::from(*position));
            if !point.is_finite() {
                return None;
            }
            minimum = minimum.min(point.as_dvec3());
            maximum = maximum.max(point.as_dvec3());
        }
    }
    let center = ((minimum + maximum) * 0.5).as_vec3();
    center.is_finite().then_some(center)
}
