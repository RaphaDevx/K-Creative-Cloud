use crate::scene::{Object, Scene};
use glam::{Mat4, Vec3, Vec4};

#[derive(Clone, Debug)]
pub struct Camera {
    pub yaw: f32,
    pub pitch: f32,
    pub distance: f32,
    pub target: Vec3,
}
impl Default for Camera {
    fn default() -> Self {
        Self {
            yaw: 0.72,
            pitch: 0.48,
            distance: 6.0,
            target: Vec3::new(0., 0.5, 0.),
        }
    }
}
impl Camera {
    pub fn eye(&self) -> Vec3 {
        self.target
            + Vec3::new(
                self.yaw.sin() * self.pitch.cos(),
                self.pitch.sin(),
                self.yaw.cos() * self.pitch.cos(),
            ) * self.distance
    }
    pub fn matrix(&self, aspect: f32) -> Mat4 {
        Mat4::perspective_rh(45f32.to_radians(), aspect.max(0.01), 0.01, 10000.)
            * Mat4::look_at_rh(self.eye(), self.target, Vec3::Y)
    }
    pub fn orbit(&mut self, x: f32, y: f32) {
        self.yaw -= x * 0.008;
        self.pitch = (self.pitch + y * 0.008).clamp(-1.5, 1.5);
    }
    pub fn pan(&mut self, x: f32, y: f32) {
        let forward = (self.target - self.eye()).normalize();
        let right = forward.cross(Vec3::Y).normalize();
        let up = right.cross(forward);
        self.target += (-right * x + up * y) * self.distance * 0.0015;
    }
    pub fn zoom(&mut self, amount: f32) {
        self.distance = (self.distance * (-amount * 0.002).exp()).clamp(0.15, 2000.);
    }
    pub fn focus(&mut self, object: &Object) {
        let points: Vec<_> = object
            .mesh
            .positions
            .iter()
            .map(|p| object.transform.matrix().transform_point3(Vec3::from(*p)))
            .collect();
        let min = points
            .iter()
            .fold(Vec3::splat(f32::INFINITY), |a, b| a.min(*b));
        let max = points
            .iter()
            .fold(Vec3::splat(f32::NEG_INFINITY), |a, b| a.max(*b));
        self.target = (min + max) * 0.5;
        self.distance = ((max - min).length() * 1.7).clamp(0.3, 2000.);
    }
    pub fn ray(&self, ndc: [f32; 2], aspect: f32) -> (Vec3, Vec3) {
        let inverse = self.matrix(aspect).inverse();
        let near = inverse * Vec4::new(ndc[0], ndc[1], 0., 1.);
        let near = near.truncate() / near.w;
        (self.eye(), (near - self.eye()).normalize())
    }
    pub fn pick(&self, scene: &Scene, ndc: [f32; 2], aspect: f32) -> Option<(String, usize)> {
        let (origin, direction) = self.ray(ndc, aspect);
        let mut closest = f32::INFINITY;
        let mut hit = None;
        for object in scene.objects.iter().filter(|o| o.visible) {
            let matrix = object.transform.matrix();
            for (face, indices) in object.mesh.triangles() {
                let p = indices.map(|i| {
                    matrix.transform_point3(Vec3::from(object.mesh.positions[i as usize]))
                });
                if let Some(distance) = ray_triangle(origin, direction, p) {
                    if distance < closest {
                        closest = distance;
                        hit = Some((object.id.clone(), face));
                    }
                }
            }
        }
        hit
    }
}
pub fn ray_triangle(origin: Vec3, direction: Vec3, p: [Vec3; 3]) -> Option<f32> {
    let e1 = p[1] - p[0];
    let e2 = p[2] - p[0];
    let h = direction.cross(e2);
    let det = e1.dot(h);
    if det.abs() < 1e-7 {
        return None;
    }
    let inv = 1. / det;
    let s = origin - p[0];
    let u = inv * s.dot(h);
    if !(0.0..=1.0).contains(&u) {
        return None;
    }
    let q = s.cross(e1);
    let v = inv * direction.dot(q);
    if v < 0. || u + v > 1. {
        return None;
    }
    let distance = inv * e2.dot(q);
    (distance > 0.00001).then_some(distance)
}

/// Clip line segments before upload. In particular, never rasterize a grid line
/// whose homogeneous endpoints straddle the eye on software GPU backends.
pub fn clip_segment(a: Vec3, b: Vec3, matrix: Mat4) -> Option<(Vec3, Vec3)> {
    let ca = matrix * a.extend(1.0);
    let cb = matrix * b.extend(1.0);
    let mut enter = 0.0f32;
    let mut exit = 1.0f32;
    for plane in [
        Vec4::new(1., 0., 0., 1.),
        Vec4::new(-1., 0., 0., 1.),
        Vec4::new(0., 1., 0., 1.),
        Vec4::new(0., -1., 0., 1.),
        Vec4::new(0., 0., 1., 0.),
        Vec4::new(0., 0., -1., 1.),
    ] {
        let da = plane.dot(ca);
        let db = plane.dot(cb);
        if da < 0.0 && db < 0.0 {
            return None;
        }
        if da < 0.0 {
            enter = enter.max(da / (da - db));
        }
        if db < 0.0 {
            exit = exit.min(da / (da - db));
        }
    }
    if enter > exit {
        None
    } else {
        Some((a.lerp(b, enter), a.lerp(b, exit)))
    }
}
