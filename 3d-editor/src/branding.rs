use crate::Result;
use serde::{Deserialize, Serialize};
use std::path::Path;

#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Brand {
    pub schema_version: u32,
    pub app_name: String,
    pub wordmark: String,
    pub monogram: String,
    pub launch_line: String,
    pub workspace_signature: String,
    pub accent: [u8; 3],
    pub launch_background: [u8; 3],
    pub show_workspace_signature: bool,
}
impl Default for Brand {
    fn default() -> Self {
        serde_json::from_str(include_str!("../branding/neutral.json"))
            .expect("embedded neutral brand is valid JSON")
    }
}
impl Brand {
    pub fn validate(&self) -> Result<()> {
        if self.schema_version != 1 {
            return Err("Nicht unterstützte Branding-Version.".into());
        }
        for text in [
            &self.app_name,
            &self.wordmark,
            &self.monogram,
            &self.launch_line,
            &self.workspace_signature,
        ] {
            if text.trim().is_empty()
                || text.chars().count() > 120
                || text.chars().any(char::is_control)
            {
                return Err("Brandingtexte müssen 1–120 druckbare Zeichen enthalten.".into());
            }
        }
        if self.monogram.chars().count() > 4 {
            return Err("Das Markenzeichen darf höchstens vier Zeichen enthalten.".into());
        }
        if contrast(self.accent, self.launch_background) < 3.0 {
            return Err(
                "Markenfarbe benötigt mindestens 3:1 Kontrast zum Starthintergrund.".into(),
            );
        }
        Ok(())
    }
    pub fn load(path: &Path) -> Result<Self> {
        let bytes = crate::persistence::read_bounded(path, 16384)?;
        let brand: Self = serde_json::from_slice(&bytes)
            .map_err(|e| format!("Branding konnte nicht gelesen werden: {e}"))?;
        brand.validate()?;
        Ok(brand)
    }
    pub fn ink_on(background: [u8; 3]) -> [u8; 3] {
        if contrast([245; 3], background) >= contrast([15; 3], background) {
            [245; 3]
        } else {
            [15; 3]
        }
    }
}
pub fn contrast(a: [u8; 3], b: [u8; 3]) -> f32 {
    fn luminance(rgb: [u8; 3]) -> f32 {
        let c = rgb.map(|v| {
            let s = v as f32 / 255.;
            if s <= 0.04045 {
                s / 12.92
            } else {
                ((s + 0.055) / 1.055).powf(2.4)
            }
        });
        c[0] * 0.2126 + c[1] * 0.7152 + c[2] * 0.0722
    }
    let x = luminance(a);
    let y = luminance(b);
    (x.max(y) + 0.05) / (x.min(y) + 0.05)
}
