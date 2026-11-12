//! Viewport-local, depth-aware picking for mesh vertices and polygon edges.
use crate::{
    camera::{clip_segment, Camera},
    scene::Scene,
};
use glam::{Mat4, Vec2, Vec3};
use std::collections::BTreeSet;

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Element {
    Vertex(usize),
    Edge([u32; 2]),
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ElementHit {
    pub object_id: String,
    pub element: Element,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum ElementMode {
    Vertex,
    Edge,
}

fn viewport_valid(viewport: [f32; 2]) -> bool {
    viewport.iter().all(|v| v.is_finite() && *v > 0.)
}

fn project(matrix: Mat4, point: Vec3, viewport: [f32; 2]) -> Option<(Vec2, f32)> {
    let clip = matrix * point.extend(1.);
    // Clipping and reprojecting a world endpoint can round just outside a
    // depth plane, especially close to the eye.
    let depth_tolerance = 8. * f32::EPSILON * clip.w.abs().max(1.);
    if !clip.is_finite()
        || clip.w <= 0.
        || clip.z < -depth_tolerance
        || clip.z > clip.w + depth_tolerance
    {
        return None;
    }
    let ndc = clip.truncate() / clip.w;
    let pixel = Vec2::new(
        (ndc.x + 1.) * viewport[0] * 0.5,
        (1. - ndc.y) * viewport[1] * 0.5,
    );
    pixel.is_finite().then_some((pixel, clip.w))
}

/// Project a world point to logical pixels with a top-left viewport origin.
/// Points outside the near/far planes, behind the eye, and invalid input return
/// `None`. Coordinates may be outside the viewport's horizontal/vertical bounds.
pub fn project_point(camera: &Camera, point: Vec3, viewport: [f32; 2]) -> Option<[f32; 2]> {
    if !viewport_valid(viewport) {
        return None;
    }
    project(camera.matrix(viewport[0] / viewport[1]), point, viewport)
        .map(|(pixel, _)| pixel.to_array())
}

struct Candidate {
    object: usize,
    element: Element,
    point: Vec3,
    screen_distance: f32,
    depth: f32,
}

/// Pick the closest visible element within `threshold` logical pixels.
/// Equal screen distances prefer the nearer element, then stable scene/index
/// order. Only polygon boundary edges participate (no triangulation diagonals).
pub fn pick_element(
    scene: &Scene,
    camera: &Camera,
    pointer: [f32; 2],
    viewport: [f32; 2],
    mode: ElementMode,
    threshold: f32,
) -> Option<ElementHit> {
    if !viewport_valid(viewport)
        || pointer.iter().any(|v| !v.is_finite())
        || !threshold.is_finite()
        || threshold < 0.
        || pointer[0] < 0.
        || pointer[0] > viewport[0]
        || pointer[1] < 0.
        || pointer[1] > viewport[1]
    {
        return None;
    }
    let matrix = camera.matrix(viewport[0] / viewport[1]);
    let eye = camera.eye();
    if !matrix.is_finite() || !eye.is_finite() {
        return None;
    }
    let pointer = Vec2::from(pointer);
    let mut candidates = Vec::new();
    let mut surfaces = Vec::new();
    for (object_index, object) in scene.objects.iter().enumerate().filter(|(_, o)| o.visible) {
        let transform = object.transform.matrix();
        let positions: Vec<_> = object
            .mesh
            .positions
            .iter()
            .map(|p| transform.transform_point3(Vec3::from(*p)))
            .collect();
        // Defensive indexing also keeps picking safe for an in-progress mesh.
        for face in &object.mesh.faces {
            for i in 1..face.len().saturating_sub(1) {
                if let (Some(a), Some(b), Some(c)) = (
                    positions.get(face[0] as usize),
                    positions.get(face[i] as usize),
                    positions.get(face[i + 1] as usize),
                ) {
                    if a.is_finite() && b.is_finite() && c.is_finite() {
                        surfaces.push([*a, *b, *c]);
                    }
                }
            }
        }
        let mut add = |element, point: Vec3, pixel: Vec2| {
            let screen_distance = pixel.distance(pointer);
            let depth = point.distance(eye);
            if screen_distance <= threshold && depth.is_finite() && depth > 0. {
                candidates.push(Candidate {
                    object: object_index,
                    element,
                    point,
                    screen_distance,
                    depth,
                });
            }
        };
        match mode {
            ElementMode::Vertex => {
                for (index, point) in positions.iter().enumerate() {
                    if let Some((pixel, _)) = project(matrix, *point, viewport) {
                        if pixel.x >= 0.
                            && pixel.x <= viewport[0]
                            && pixel.y >= 0.
                            && pixel.y <= viewport[1]
                        {
                            add(Element::Vertex(index), *point, pixel);
                        }
                    }
                }
            }
            ElementMode::Edge => {
                let mut edges = BTreeSet::new();
                for face in &object.mesh.faces {
                    for i in 0..face.len() {
                        let a = face[i];
                        let b = face[(i + 1) % face.len()];
                        if a != b {
                            edges.insert([a.min(b), a.max(b)]);
                        }
                    }
                }
                for edge in edges {
                    let (Some(a), Some(b)) = (
                        positions.get(edge[0] as usize),
                        positions.get(edge[1] as usize),
                    ) else {
                        continue;
                    };
                    if !a.is_finite() || !b.is_finite() {
                        continue;
                    }
                    let Some((a, b)) = clip_segment(*a, *b, matrix) else {
                        continue;
                    };
                    let (Some((pa, wa)), Some((pb, wb))) =
                        (project(matrix, a, viewport), project(matrix, b, viewport))
                    else {
                        continue;
                    };
                    let segment = pb - pa;
                    let length_squared = segment.length_squared();
                    let fraction = if length_squared > 0. {
                        ((pointer - pa).dot(segment) / length_squared).clamp(0., 1.)
                    } else {
                        0.
                    };
                    // Screen interpolation is not linear in world space.
                    let world_fraction = fraction * wa / ((1. - fraction) * wb + fraction * wa);
                    add(
                        Element::Edge(edge),
                        a.lerp(b, world_fraction),
                        pa.lerp(pb, fraction),
                    );
                }
            }
        }
    }
    candidates.sort_by(|a, b| {
        a.screen_distance
            .total_cmp(&b.screen_distance)
            .then_with(|| a.depth.total_cmp(&b.depth))
    });
    for candidate in candidates {
        if !surfaces
            .iter()
            .any(|triangle| occludes(eye, candidate.point, *triangle))
        {
            return Some(ElementHit {
                object_id: scene.objects[candidate.object].id.clone(),
                element: candidate.element,
            });
        }
    }
    None
}

fn occludes(eye: Vec3, point: Vec3, triangle: [Vec3; 3]) -> bool {
    // Double precision and a small barycentric tolerance keep rays on shared
    // boundaries stable. Parameter t=1 is the selected point itself.
    let origin = eye.as_dvec3();
    let direction = point.as_dvec3() - origin;
    let [a, b, c] = triangle.map(|point| point.as_dvec3());
    let e1 = b - a;
    let e2 = c - a;
    let h = direction.cross(e2);
    let det = e1.dot(h);
    if det.abs() <= f64::EPSILON * e1.length() * h.length() {
        return false;
    }
    let s = origin - a;
    let u = s.dot(h) / det;
    const BARYCENTRIC_EPSILON: f64 = 1e-7;
    if !(-BARYCENTRIC_EPSILON..=1. + BARYCENTRIC_EPSILON).contains(&u) {
        return false;
    }
    let q = s.cross(e1);
    let v = direction.dot(q) / det;
    if v < -BARYCENTRIC_EPSILON || u + v > 1. + BARYCENTRIC_EPSILON {
        return false;
    }
    let t = e2.dot(q) / det;
    const DEPTH_EPSILON: f64 = 1e-6;
    t > 0. && t < 1. - DEPTH_EPSILON
}
