use crate::{commands::Document, Result};
use std::{
    fs,
    io::{Read, Write},
    path::Path,
};

pub const MAX_FILE_BYTES: u64 = 64 * 1024 * 1024;
pub fn read_bounded(path: &Path, limit: u64) -> Result<Vec<u8>> {
    let file = fs::File::open(path).map_err(|e| format!("{}: {e}", path.display()))?;
    if file.metadata().map_err(|e| e.to_string())?.len() > limit {
        return Err("Datei überschreitet die Größengrenze.".into());
    }
    let mut bytes = Vec::new();
    file.take(limit + 1)
        .read_to_end(&mut bytes)
        .map_err(|e| e.to_string())?;
    if bytes.len() as u64 > limit {
        return Err("Datei überschreitet die Größengrenze.".into());
    }
    Ok(bytes)
}
pub fn load(path: &Path) -> Result<Document> {
    let bytes = read_bounded(path, MAX_FILE_BYTES)?;
    let document: Document =
        serde_json::from_slice(&bytes).map_err(|e| format!("Ungültige scene3d-Datei: {e}"))?;
    document.validate()?;
    Ok(document)
}
pub fn save(path: &Path, document: &Document) -> Result<()> {
    document.validate()?;
    let bytes = serde_json::to_vec(document).map_err(|e| e.to_string())?;
    write_atomic(path, &bytes)
}
pub fn write_atomic(path: &Path, bytes: &[u8]) -> Result<()> {
    if bytes.len() as u64 > MAX_FILE_BYTES {
        return Err("Datei überschreitet 64 MiB. In kleinere Szenen aufteilen.".into());
    }
    let parent = path
        .parent()
        .filter(|p| !p.as_os_str().is_empty())
        .unwrap_or(Path::new("."));
    let temp = parent.join(format!(".3d-editor-{}.tmp", uuid::Uuid::new_v4()));
    let result = (|| -> std::io::Result<()> {
        let mut file = fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&temp)?;
        file.write_all(bytes)?;
        file.sync_all()?;
        fs::rename(&temp, path)?;
        #[cfg(unix)]
        fs::File::open(parent)?.sync_all()?;
        Ok(())
    })();
    if result.is_err() {
        let _ = fs::remove_file(&temp);
    }
    result.map_err(|e| format!("Speichern fehlgeschlagen: {e}"))
}
