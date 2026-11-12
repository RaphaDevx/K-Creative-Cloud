use crate::{mesh::Mesh, Result};
use glam::{EulerRot, Mat4, Quat, Vec3};
use serde::{Deserialize, Serialize};
use std::collections::BTreeSet;
use uuid::Uuid;

pub fn new_id() -> String {
    Uuid::new_v4().to_string()
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Transform {
    pub translation: [f32; 3],
    pub rotation_degrees: [f32; 3],
    pub scale: [f32; 3],
}
impl Default for Transform {
    fn default() -> Self {
        Self {
            translation: [0.; 3],
            rotation_degrees: [0.; 3],
            scale: [1.; 3],
        }
    }
}
impl Transform {
    pub fn matrix(&self) -> Mat4 {
        let r = self.rotation_degrees.map(f32::to_radians);
        Mat4::from_scale_rotation_translation(
            Vec3::from(self.scale),
            Quat::from_euler(EulerRot::XYZ, r[0], r[1], r[2]),
            Vec3::from(self.translation),
        )
    }
    pub fn validate(&self) -> Result<()> {
        if self
            .translation
            .iter()
            .any(|v| !v.is_finite() || v.abs() > 1e6)
            || self
                .rotation_degrees
                .iter()
                .any(|v| !v.is_finite() || v.abs() > 360_000.)
            || self
                .scale
                .iter()
                .any(|v| !v.is_finite() || !(0.001..=10000.).contains(v))
        {
            return Err("Ungültige Transformation; Skalierung muss positiv sein.".into());
        }
        Ok(())
    }
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Object {
    pub id: String,
    pub name: String,
    pub transform: Transform,
    pub color: [f32; 3],
    pub visible: bool,
    pub mesh: Mesh,
}

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Scene {
    pub id: String,
    pub name: String,
    pub objects: Vec<Object>,
}
impl Default for Scene {
    fn default() -> Self {
        Self {
            id: new_id(),
            name: "Unbenannte Szene".into(),
            objects: Vec::new(),
        }
    }
}
impl Scene {
    pub fn validate(&self) -> Result<()> {
        if Uuid::parse_str(&self.id).is_err()
            || self.name.trim().is_empty()
            || self.name.len() > 256
            || self.objects.len() > 256
        {
            return Err("Ungültige Szene oder mehr als 256 Objekte.".into());
        }
        let mut ids = BTreeSet::new();
        let mut total = 0;
        for object in &self.objects {
            if Uuid::parse_str(&object.id).is_err()
                || !ids.insert(&object.id)
                || object.name.trim().is_empty()
                || object.name.len() > 256
            {
                return Err("Ungültige oder doppelte Objektidentität.".into());
            }
            object.transform.validate()?;
            if object
                .color
                .iter()
                .any(|v| !v.is_finite() || !(0.0..=1.0).contains(v))
            {
                return Err("Ungültige Materialfarbe.".into());
            }
            object.mesh.validate()?;
            total += object.mesh.positions.len();
        }
        if total > 500_000 {
            return Err("Die Szene überschreitet 500000 Punkte.".into());
        }
        Ok(())
    }
    pub fn object(&self, id: &str) -> Result<&Object> {
        self.objects
            .iter()
            .find(|o| o.id == id)
            .ok_or_else(|| "Objekt nicht gefunden.".into())
    }
    pub fn object_mut(&mut self, id: &str) -> Result<&mut Object> {
        self.objects
            .iter_mut()
            .find(|o| o.id == id)
            .ok_or_else(|| "Objekt nicht gefunden.".into())
    }
}
