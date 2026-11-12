//! Transient object selection shared by editor controls and the viewport.
//! Selection is intentionally separate from document persistence and history.
use crate::scene::Scene;

/// Ordered unique object IDs. The last retained ID is the active object.
#[derive(Default, Clone, Debug)]
pub struct ObjectSelection {
    ids: Vec<String>,
}

impl ObjectSelection {
    pub fn ids(&self) -> &[String] {
        &self.ids
    }

    pub fn active(&self) -> Option<&str> {
        self.ids.last().map(String::as_str)
    }

    pub fn contains(&self, id: &str) -> bool {
        self.ids.iter().any(|selected| selected == id)
    }

    pub fn is_empty(&self) -> bool {
        self.ids.is_empty()
    }

    pub fn len(&self) -> usize {
        self.ids.len()
    }

    /// Replace the selection, ignoring empty IDs without clearing it.
    pub fn select_only(&mut self, id: String) {
        if !id.is_empty() {
            self.ids.clear();
            self.ids.push(id);
        }
    }

    /// Shift-click behavior: add as active, or remove without reordering others.
    pub fn toggle(&mut self, id: String) {
        if id.is_empty() {
            return;
        }
        if let Some(index) = self.ids.iter().position(|selected| selected == &id) {
            self.ids.remove(index);
        } else {
            self.ids.push(id);
        }
    }

    pub fn clear(&mut self) {
        self.ids.clear();
    }

    /// Drop hidden/deleted objects after scene changes, including undo/redo.
    /// Objects restored by undo are not automatically selected again.
    pub fn prune(&mut self, scene: &Scene) {
        self.ids.retain(|id| {
            scene
                .objects
                .iter()
                .any(|object| object.visible && object.id == *id)
        });
    }

    /// Replace the selection with visible objects in scene order.
    pub fn select_all(&mut self, scene: &Scene) {
        self.clear();
        for object in scene.objects.iter().filter(|object| object.visible) {
            if !object.id.is_empty() && !self.contains(&object.id) {
                self.ids.push(object.id.clone());
            }
        }
    }
}
