use crate::Result;
use glam::{DVec3, Vec3};
use serde::{Deserialize, Serialize};
use std::collections::{BTreeMap, BTreeSet};

pub const MAX_VERTICES: usize = 100_000;
pub const MAX_FACES: usize = 100_000;

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Mesh {
    pub positions: Vec<[f32; 3]>,
    pub faces: Vec<Vec<u32>>,
}

#[derive(Clone, Copy, Debug, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Primitive {
    Cube,
    Sphere,
    Cylinder,
    Plane,
}

impl Primitive {
    pub fn label(self) -> &'static str {
        match self {
            Self::Cube => "Würfel",
            Self::Sphere => "Kugel",
            Self::Cylinder => "Zylinder",
            Self::Plane => "Fläche",
        }
    }
}

impl Mesh {
    pub fn primitive(kind: Primitive) -> Self {
        match kind {
            Primitive::Cube => Self {
                positions: vec![
                    [-0.5, -0.5, -0.5],
                    [0.5, -0.5, -0.5],
                    [0.5, 0.5, -0.5],
                    [-0.5, 0.5, -0.5],
                    [-0.5, -0.5, 0.5],
                    [0.5, -0.5, 0.5],
                    [0.5, 0.5, 0.5],
                    [-0.5, 0.5, 0.5],
                ],
                faces: vec![
                    vec![0, 3, 2, 1],
                    vec![4, 5, 6, 7],
                    vec![0, 1, 5, 4],
                    vec![3, 7, 6, 2],
                    vec![0, 4, 7, 3],
                    vec![1, 2, 6, 5],
                ],
            },
            Primitive::Plane => Self {
                positions: vec![[-1., 0., -1.], [1., 0., -1.], [1., 0., 1.], [-1., 0., 1.]],
                faces: vec![vec![0, 3, 2, 1]],
            },
            Primitive::Cylinder => {
                let n = 32u32;
                let mut positions = Vec::new();
                for y in [-0.5, 0.5] {
                    for i in 0..n {
                        let a = i as f32 * std::f32::consts::TAU / n as f32;
                        positions.push([a.cos() * 0.5, y, a.sin() * 0.5]);
                    }
                }
                let mut faces = vec![(0..n).collect(), (n..2 * n).rev().collect()];
                for i in 0..n {
                    let j = (i + 1) % n;
                    faces.push(vec![n + i, n + j, j, i]);
                }
                Self { positions, faces }
            }
            Primitive::Sphere => {
                let slices = 24u32;
                let rings = 11u32;
                let mut positions = vec![[0., 0.5, 0.]];
                for r in 1..=rings {
                    let theta = r as f32 * std::f32::consts::PI / (rings + 1) as f32;
                    for i in 0..slices {
                        let a = i as f32 * std::f32::consts::TAU / slices as f32;
                        positions.push([
                            theta.sin() * a.cos() * 0.5,
                            theta.cos() * 0.5,
                            theta.sin() * a.sin() * 0.5,
                        ]);
                    }
                }
                let bottom = positions.len() as u32;
                positions.push([0., -0.5, 0.]);
                let mut faces = Vec::new();
                for i in 0..slices {
                    let j = (i + 1) % slices;
                    faces.push(vec![0, 1 + j, 1 + i]);
                    for r in 0..rings - 1 {
                        let a = 1 + r * slices;
                        let b = a + slices;
                        faces.push(vec![a + i, a + j, b + j, b + i]);
                    }
                    let a = 1 + (rings - 1) * slices;
                    faces.push(vec![a + i, a + j, bottom]);
                }
                Self { positions, faces }
            }
        }
    }

    pub fn normal(&self, face: usize) -> Vec3 {
        let f = &self.faces[face];
        let a = Vec3::from(self.positions[f[0] as usize]);
        let b = Vec3::from(self.positions[f[1] as usize]);
        let c = Vec3::from(self.positions[f[2] as usize]);
        (b - a).cross(c - a).normalize_or_zero()
    }

    pub fn triangles(&self) -> impl Iterator<Item = (usize, [u32; 3])> + '_ {
        self.faces.iter().enumerate().flat_map(|(index, face)| {
            (1..face.len() - 1).map(move |i| (index, [face[0], face[i], face[i + 1]]))
        })
    }

    pub fn validate(&self) -> Result<()> {
        if self.positions.is_empty()
            || self.positions.len() > MAX_VERTICES
            || self.faces.is_empty()
            || self.faces.len() > MAX_FACES
        {
            return Err("Mesh benötigt 1–100000 Punkte und Flächen.".into());
        }
        if self
            .positions
            .iter()
            .flatten()
            .any(|v| !v.is_finite() || v.abs() > 1_000_000.)
        {
            return Err("Ungültige Mesh-Koordinaten.".into());
        }
        for (index, face) in self.faces.iter().enumerate() {
            if !(3..=256).contains(&face.len())
                || face.iter().any(|i| *i as usize >= self.positions.len())
                || face.iter().collect::<BTreeSet<_>>().len() != face.len()
            {
                return Err(format!("Fläche {index} hat ungültige Punktreferenzen."));
            }
            let normal = self.normal(index);
            if normal.length_squared() < 0.5 {
                return Err(format!("Fläche {index} hat keine gültige Normale."));
            }
            let origin = Vec3::from(self.positions[face[0] as usize]);
            for i in 0..face.len() {
                let a = Vec3::from(self.positions[face[i] as usize]);
                let b = Vec3::from(self.positions[face[(i + 1) % face.len()] as usize]);
                let c = Vec3::from(self.positions[face[(i + 2) % face.len()] as usize]);
                if (a - origin).dot(normal).abs() > 0.001
                    || (b - a).cross(c - b).dot(normal) < -0.000001
                    || face.iter().any(|vertex| {
                        let point = Vec3::from(self.positions[*vertex as usize]);
                        (b - a).cross(point - a).dot(normal) < -0.000001
                    })
                {
                    return Err(format!(
                        "Fläche {index}: nur ebene, konvexe Polygone werden unterstützt."
                    ));
                }
            }
        }
        Ok(())
    }

    /// Moves each cap vertex `factor` of the way toward the vertex centroid.
    /// This is a proportional inset, not a constant-distance edge offset.
    /// The cap keeps its face index; the surrounding quads are appended.
    /// Any invalid input, collapsed geometry or exceeded budget leaves `self` unchanged.
    pub fn inset_face(&mut self, face_index: usize, factor: f32) -> Result<()> {
        if !factor.is_finite() || factor <= 0. || factor >= 1. {
            return Err("Inset-Faktor muss grösser als 0 und kleiner als 1 sein.".into());
        }
        let face = self.faces.get(face_index).ok_or("Fläche nicht gefunden.")?;
        if self.positions.len().saturating_add(face.len()) > MAX_VERTICES
            || self.faces.len().saturating_add(face.len()) > MAX_FACES
        {
            return Err("Inset überschreitet das Punkt- oder Flächenlimit.".into());
        }
        self.validate_modeling_geometry()?;
        let center = self.face_center(face);
        let mut candidate = self.clone();
        let base = candidate.positions.len() as u32;
        let cap: Vec<u32> = (0..face.len()).map(|i| base + i as u32).collect();
        for vertex in face {
            let point = Vec3::from(self.positions[*vertex as usize]).as_dvec3();
            candidate.positions.push(
                (point + (center - point) * f64::from(factor))
                    .as_vec3()
                    .to_array(),
            );
        }
        candidate.faces[face_index] = cap.clone();
        for i in 0..face.len() {
            let j = (i + 1) % face.len();
            candidate.faces.push(vec![face[i], face[j], cap[j], cap[i]]);
        }
        candidate.validate_modeling_geometry()?;
        *self = candidate;
        Ok(())
    }

    /// Splits every polygon into quads using shared edge midpoints and a face center.
    /// Original vertices remain fixed: this is linear subdivision without smoothing.
    /// Existing shared edges (including boundaries) retain their connectivity.
    /// Invalid input/output or exceeded budgets leave `self` unchanged.
    pub fn subdivide(&mut self) -> Result<()> {
        let mut face_count = 0usize;
        for face in &self.faces {
            face_count = face_count.saturating_add(face.len());
            if face_count > MAX_FACES {
                return Err("Unterteilung überschreitet das Flächenlimit.".into());
            }
        }
        if self.positions.len().saturating_add(self.faces.len()) > MAX_VERTICES {
            return Err("Unterteilung überschreitet das Punktlimit.".into());
        }
        self.validate_modeling_geometry()?;
        let mut midpoints = BTreeMap::new();
        for face in &self.faces {
            for i in 0..face.len() {
                let a = face[i];
                let b = face[(i + 1) % face.len()];
                let next = (self.positions.len() + midpoints.len()) as u32;
                midpoints.entry((a.min(b), a.max(b))).or_insert(next);
                if self.positions.len() + midpoints.len() + self.faces.len() > MAX_VERTICES {
                    return Err("Unterteilung überschreitet das Punktlimit.".into());
                }
            }
        }
        // Allocation and mutation start only after both output budgets are known.
        let mut candidate = Self {
            positions: self.positions.clone(),
            faces: Vec::with_capacity(face_count),
        };
        candidate.positions.resize(
            self.positions.len() + midpoints.len() + self.faces.len(),
            [0.; 3],
        );
        for (&(a, b), &index) in &midpoints {
            let a = Vec3::from(self.positions[a as usize]).as_dvec3();
            let b = Vec3::from(self.positions[b as usize]).as_dvec3();
            candidate.positions[index as usize] = ((a + b) * 0.5).as_vec3().to_array();
        }
        for (face_index, face) in self.faces.iter().enumerate() {
            let center = (self.positions.len() + midpoints.len() + face_index) as u32;
            candidate.positions[center as usize] = self.face_center(face).as_vec3().to_array();
            for i in 0..face.len() {
                let previous = face[(i + face.len() - 1) % face.len()];
                let current = face[i];
                let next = face[(i + 1) % face.len()];
                candidate.faces.push(vec![
                    current,
                    midpoints[&(current.min(next), current.max(next))],
                    center,
                    midpoints[&(previous.min(current), previous.max(current))],
                ]);
            }
        }
        candidate.validate_modeling_geometry()?;
        *self = candidate;
        Ok(())
    }

    fn face_center(&self, face: &[u32]) -> DVec3 {
        face.iter()
            .map(|vertex| Vec3::from(self.positions[*vertex as usize]).as_dvec3())
            .sum::<DVec3>()
            / face.len() as f64
    }

    fn validate_modeling_geometry(&self) -> Result<()> {
        self.validate()?;
        // The renderer fans each face. Reject zero-area fan triangles, including
        // those introduced by f32 rounding, before committing a modeling edit.
        for (face, triangle) in self.triangles() {
            let [a, b, c] = triangle.map(|index| Vec3::from(self.positions[index as usize]));
            let area = (b - a).cross(c - a).length_squared();
            if !area.is_finite() || area <= 0. {
                return Err(format!("Fläche {face} enthält ein degeneriertes Dreieck."));
            }
        }
        Ok(())
    }

    pub fn extrude(&mut self, face_index: usize, distance: f32) -> Result<()> {
        if !distance.is_finite() || !(0.0001..=1000.).contains(&distance) {
            return Err("Extrusion muss zwischen 0.0001 und 1000 m liegen.".into());
        }
        let face = self
            .faces
            .get(face_index)
            .ok_or("Fläche nicht gefunden.")?
            .clone();
        let offset = self.normal(face_index) * distance;
        let base = self.positions.len() as u32;
        let cap: Vec<u32> = (0..face.len()).map(|i| base + i as u32).collect();
        for vertex in &face {
            self.positions
                .push((Vec3::from(self.positions[*vertex as usize]) + offset).to_array());
        }
        self.faces[face_index] = cap.clone();
        for i in 0..face.len() {
            let j = (i + 1) % face.len();
            self.faces.push(vec![face[i], face[j], cap[j], cap[i]]);
        }
        self.validate()
    }
}
