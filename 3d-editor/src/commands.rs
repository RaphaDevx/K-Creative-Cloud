use crate::{
    mesh::{Mesh, Primitive},
    scene::{new_id, Object, Scene, Transform},
    Result,
};
use serde::{Deserialize, Serialize};
use std::time::{SystemTime, UNIX_EPOCH};

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(tag = "action", rename_all = "snake_case", deny_unknown_fields)]
pub enum Command {
    Add {
        primitive: Primitive,
    },
    ImportMesh {
        name: String,
        mesh: Mesh,
    },
    Transform {
        id: String,
        transform: Transform,
    },
    Rename {
        id: String,
        name: String,
    },
    Color {
        id: String,
        color: [f32; 3],
    },
    Visibility {
        id: String,
        visible: bool,
    },
    Duplicate {
        id: String,
    },
    Remove {
        id: String,
    },
    Extrude {
        id: String,
        face: usize,
        distance: f32,
    },
    Inset {
        id: String,
        face: usize,
        factor: f32,
    },
    Subdivide {
        id: String,
    },
    MoveVertex {
        id: String,
        vertex: usize,
        position: [f32; 3],
    },
    MoveEdge {
        id: String,
        edge: [u32; 2],
        offset: [f32; 3],
    },
}
impl Command {
    pub fn label(&self) -> &'static str {
        match self {
            Self::Add { .. } => "Objekt hinzufügen",
            Self::ImportMesh { .. } => "Mesh importieren",
            Self::Transform { .. } => "Transformieren",
            Self::Rename { .. } => "Umbenennen",
            Self::Color { .. } => "Materialfarbe ändern",
            Self::Visibility { .. } => "Sichtbarkeit ändern",
            Self::Duplicate { .. } => "Duplizieren",
            Self::Remove { .. } => "Objekt entfernen",
            Self::Extrude { .. } => "Fläche extrudieren",
            Self::Inset { .. } => "Fläche einrücken",
            Self::Subdivide { .. } => "Mesh linear unterteilen",
            Self::MoveVertex { .. } => "Punkt verschieben",
            Self::MoveEdge { .. } => "Kante verschieben",
        }
    }
    fn apply(&self, scene: &mut Scene) -> Result<()> {
        match self {
            Self::Add { primitive } => {
                let mut transform = Transform::default();
                transform.translation[1] = 0.5;
                scene.objects.push(Object {
                    id: new_id(),
                    name: primitive.label().into(),
                    transform,
                    color: [0.62, 0.66, 0.72],
                    visible: true,
                    mesh: Mesh::primitive(*primitive),
                });
            }
            Self::ImportMesh { name, mesh } => scene.objects.push(Object {
                id: new_id(),
                name: name.clone(),
                transform: Transform::default(),
                color: [0.62, 0.66, 0.72],
                visible: true,
                mesh: mesh.clone(),
            }),
            Self::Transform { id, transform } => {
                scene.object_mut(id)?.transform = transform.clone()
            }
            Self::Rename { id, name } => scene.object_mut(id)?.name = name.clone(),
            Self::Color { id, color } => scene.object_mut(id)?.color = *color,
            Self::Visibility { id, visible } => scene.object_mut(id)?.visible = *visible,
            Self::Duplicate { id } => {
                let mut copy = scene.object(id)?.clone();
                copy.id = new_id();
                copy.name = format!("{} Kopie", copy.name);
                copy.transform.translation[0] += 1.25;
                scene.objects.push(copy);
            }
            Self::Remove { id } => {
                scene.object(id)?;
                scene.objects.retain(|o| o.id != *id);
            }
            Self::Extrude { id, face, distance } => {
                scene.object_mut(id)?.mesh.extrude(*face, *distance)?
            }
            Self::Inset { id, face, factor } => {
                scene.object_mut(id)?.mesh.inset_face(*face, *factor)?
            }
            Self::Subdivide { id } => scene.object_mut(id)?.mesh.subdivide()?,
            Self::MoveVertex {
                id,
                vertex,
                position,
            } => {
                set_positions(&mut scene.object_mut(id)?.mesh, &[(*vertex, *position)])?;
            }
            Self::MoveEdge { id, edge, offset } => {
                let mesh = &mut scene.object_mut(id)?.mesh;
                if edge[0] == edge[1]
                    || !mesh.faces.iter().any(|face| {
                        (0..face.len()).any(|i| {
                            let a = face[i];
                            let b = face[(i + 1) % face.len()];
                            (a == edge[0] && b == edge[1]) || (a == edge[1] && b == edge[0])
                        })
                    })
                {
                    return Err("Kante nicht gefunden.".into());
                }
                let mut changes = Vec::new();
                for index in edge {
                    let point = mesh
                        .positions
                        .get(*index as usize)
                        .ok_or("Punkt nicht gefunden.")?;
                    changes.push((
                        *index as usize,
                        std::array::from_fn(|i| point[i] + offset[i]),
                    ));
                }
                set_positions(mesh, &changes)?;
            }
        }
        scene.validate()
    }
}

// Moving polygon vertices can make adjacent quads non-planar. Preserve an
// explicit valid polygon representation by triangulating affected faces in the
// same atomic edit; the journal records the resulting topology difference.
fn set_positions(mesh: &mut Mesh, changes: &[(usize, [f32; 3])]) -> Result<()> {
    for (index, _) in changes {
        if *index >= mesh.positions.len() {
            return Err("Punkt nicht gefunden.".into());
        }
    }
    let mut triangles = Vec::new();
    for face in &mut mesh.faces {
        if face.len() > 3
            && changes
                .iter()
                .any(|(index, _)| face.contains(&(*index as u32)))
        {
            for i in 2..face.len() - 1 {
                triangles.push(vec![face[0], face[i], face[i + 1]]);
            }
            *face = vec![face[0], face[1], face[2]];
        }
    }
    mesh.faces.extend(triangles);
    for (index, position) in changes {
        mesh.positions[*index] = *position;
    }
    mesh.validate()
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CommandGroup {
    pub expected_revision: u64,
    pub actor: String,
    pub task_path: Vec<String>,
    pub label: String,
    pub commands: Vec<Command>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct ObjectChange {
    pub object_id: String,
    pub before: Option<Object>,
    pub after: Option<Object>,
}
#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct HistoryEntry {
    pub id: String,
    pub revision: u64,
    pub timestamp_ms: u64,
    pub actor: String,
    pub task_path: Vec<String>,
    pub label: String,
    pub kind: String,
    pub commands: Vec<Command>,
    pub changes: Vec<ObjectChange>,
}
#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
struct Checkpoint {
    scene: Scene,
    label: String,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Document {
    pub schema_version: u32,
    pub revision: u64,
    pub scene: Scene,
    pub history: Vec<HistoryEntry>,
    undo: Vec<Checkpoint>,
    redo: Vec<Checkpoint>,
}
impl Default for Document {
    fn default() -> Self {
        Self {
            schema_version: 1,
            revision: 0,
            scene: Scene::default(),
            history: Vec::new(),
            undo: Vec::new(),
            redo: Vec::new(),
        }
    }
}
fn diff(before: &Scene, after: &Scene) -> Vec<ObjectChange> {
    let mut changes = Vec::new();
    for old in &before.objects {
        let new = after.objects.iter().find(|o| o.id == old.id);
        if Some(old) != new {
            changes.push(ObjectChange {
                object_id: old.id.clone(),
                before: Some(old.clone()),
                after: new.cloned(),
            });
        }
    }
    for new in &after.objects {
        if !before.objects.iter().any(|o| o.id == new.id) {
            changes.push(ObjectChange {
                object_id: new.id.clone(),
                before: None,
                after: Some(new.clone()),
            });
        }
    }
    changes
}
impl Document {
    pub fn validate(&self) -> Result<()> {
        if self.schema_version != 1 {
            return Err("Nicht unterstützte scene3d-Version.".into());
        }
        if self.undo.len() > 100 || self.redo.len() > 100 || self.history.len() > 10000 {
            return Err("Dokumenthistorie überschreitet die Grenze.".into());
        }
        self.scene.validate()?;
        for checkpoint in self.undo.iter().chain(&self.redo) {
            checkpoint.scene.validate()?;
        }
        let mut last = 0;
        for entry in &self.history {
            if entry.revision <= last || entry.revision > self.revision {
                return Err("Ungültige Historienrevision.".into());
            }
            last = entry.revision;
            for change in &entry.changes {
                for object in change.before.iter().chain(&change.after) {
                    Scene {
                        id: self.scene.id.clone(),
                        name: self.scene.name.clone(),
                        objects: vec![object.clone()],
                    }
                    .validate()?;
                }
            }
        }
        Ok(())
    }
    pub fn can_undo(&self) -> bool {
        !self.undo.is_empty()
    }
    pub fn can_redo(&self) -> bool {
        !self.redo.is_empty()
    }
    fn next_revision(&self) -> Result<u64> {
        if self.history.len() >= 10000 {
            return Err("Historiengrenze erreicht. Neues Dokument anlegen.".into());
        }
        self.revision
            .checked_add(1)
            .ok_or_else(|| "Revision erschöpft.".into())
    }
    fn record(&mut self, before: &Scene, kind: &str, group: CommandGroup, revision: u64) {
        self.history.push(HistoryEntry {
            id: new_id(),
            revision,
            timestamp_ms: SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .unwrap_or_default()
                .as_millis() as u64,
            actor: group.actor,
            task_path: group.task_path,
            label: group.label,
            kind: kind.into(),
            commands: group.commands,
            changes: diff(before, &self.scene),
        });
        self.revision = revision;
    }
    pub fn apply(&mut self, group: CommandGroup) -> Result<()> {
        if group.expected_revision != self.revision {
            return Err("Szene wurde geändert. Aktuellen Stand neu einlesen.".into());
        }
        if group.actor.trim().is_empty()
            || group.actor.len() > 128
            || group.label.trim().is_empty()
            || group.label.len() > 256
            || group.task_path.len() > 8
            || group
                .task_path
                .iter()
                .any(|s| s.trim().is_empty() || s.len() > 128)
            || !(1..=64).contains(&group.commands.len())
        {
            return Err("Ungültige Befehlsgruppe.".into());
        }
        let revision = self.next_revision()?;
        let mut candidate = self.scene.clone();
        for command in &group.commands {
            command.apply(&mut candidate)?;
        }
        if candidate == self.scene {
            return Err("Keine Änderung.".into());
        }
        let before = std::mem::replace(&mut self.scene, candidate);
        self.undo.push(Checkpoint {
            scene: before.clone(),
            label: group.label.clone(),
        });
        if self.undo.len() > 100 {
            self.undo.remove(0);
        }
        self.redo.clear();
        self.record(&before, "edit", group, revision);
        Ok(())
    }
    pub fn undo(&mut self) -> Result<()> {
        self.travel(false)
    }
    pub fn redo(&mut self) -> Result<()> {
        self.travel(true)
    }
    fn travel(&mut self, redo: bool) -> Result<()> {
        let revision = self.next_revision()?;
        let checkpoint = if redo {
            self.redo.pop()
        } else {
            self.undo.pop()
        }
        .ok_or("Keine weitere Änderung verfügbar.")?;
        let before = std::mem::replace(&mut self.scene, checkpoint.scene);
        let reverse = Checkpoint {
            scene: before.clone(),
            label: checkpoint.label.clone(),
        };
        if redo {
            self.undo.push(reverse)
        } else {
            self.redo.push(reverse)
        }
        let kind = if redo { "redo" } else { "undo" };
        self.record(
            &before,
            kind,
            CommandGroup {
                expected_revision: self.revision,
                actor: "local-user".into(),
                task_path: vec!["Verlauf".into()],
                label: checkpoint.label,
                commands: Vec::new(),
            },
            revision,
        );
        Ok(())
    }
}
