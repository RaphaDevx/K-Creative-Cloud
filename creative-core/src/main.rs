use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::{
    fs,
    io::{self, Read, Write},
    path::{Path, PathBuf},
};
use uuid::Uuid;
type Result<T> = std::result::Result<T, String>;
#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Command {
    action: String,
    project_id: Option<String>,
    #[serde(default = "empty")]
    params: Value,
}
fn empty() -> Value {
    json!({})
}
#[derive(Serialize, Deserialize)]
struct Record {
    project: Value,
    undo: Vec<Value>,
    redo: Vec<Value>,
}
fn id() -> String {
    Uuid::new_v4().to_string()
}
fn schema(action: &str) -> Value {
    let fields: Vec<(&str, &str, bool)> = match action {
        "project.create" => vec![
            ("name", "string", true),
            ("width", "integer", false),
            ("height", "integer", false),
            ("fps", "number", false),
            ("bpm", "number", false),
        ],
        "project.rename" => vec![("name", "string", true)],
        "project.settings" => vec![
            ("width", "integer", false),
            ("height", "integer", false),
            ("fps", "number", false),
            ("bpm", "number", false),
        ],
        "brand.update" => vec![("brand", "object", true)],
        "asset.add" => vec![
            ("path", "string", true),
            ("name", "string", true),
            ("kind", "string", true),
        ],
        "layer.add" | "layer.update" => vec![
            ("id", "string", action.ends_with("update")),
            ("name", "string", action.ends_with("add")),
            ("kind", "string", action.ends_with("add")),
            ("x", "number", false),
            ("y", "number", false),
            ("width", "number", false),
            ("height", "number", false),
            ("opacity", "number", false),
            ("color", "string", false),
            ("text", "string", false),
            ("path", "string", false),
        ],
        "clip.add" | "clip.update" => vec![
            ("id", "string", action.ends_with("update")),
            ("asset_id", "string", action.ends_with("add")),
            ("track", "integer", action.ends_with("add")),
            ("start", "number", action.ends_with("add")),
            ("duration", "number", action.ends_with("add")),
            ("source_start", "number", false),
            ("volume", "number", false),
        ],
        "note.add" | "note.update" => vec![
            ("id", "string", action.ends_with("update")),
            ("pitch", "integer", action.ends_with("add")),
            ("start", "number", action.ends_with("add")),
            ("duration", "number", action.ends_with("add")),
            ("velocity", "number", false),
            ("track", "integer", false),
        ],
        "layer.remove" | "clip.remove" | "note.remove" => vec![("id", "string", true)],
        "clip.split" => vec![("id", "string", true), ("at", "number", true)],
        _ => vec![],
    };
    let mut properties = serde_json::Map::new();
    let mut required = vec![];
    for (key, kind, req) in fields {
        if key == "id" && action.ends_with("add") {
            continue;
        }
        let mut s = json!({"type":kind});
        if key == "kind" {
            s["enum"] = if action.starts_with("asset") {
                json!(["image", "video", "audio", "blender"])
            } else {
                json!(["rect", "text", "image"])
            };
        }
        if kind == "string" && key != "text" {
            s["minLength"] = json!(1);
        }
        match key {
            "width" | "height" => {
                s["exclusiveMinimum"] = json!(0);
                s["maximum"] = json!(16384);
            }
            "fps" => {
                s["exclusiveMinimum"] = json!(0);
                s["maximum"] = json!(240);
            }
            "bpm" => {
                s["minimum"] = json!(20);
                s["maximum"] = json!(400);
            }
            "start" | "source_start" | "at" => {
                s["minimum"] = json!(0);
                s["maximum"] = json!(1_000_000_000);
            }
            "track" => {
                s["minimum"] = json!(0);
                s["maximum"] = json!(1024);
            }
            "duration" => {
                s["exclusiveMinimum"] = json!(0);
                s["maximum"] = json!(1_000_000_000);
            }
            "opacity" | "velocity" => {
                s["minimum"] = json!(0);
                s["maximum"] = json!(1);
            }
            "volume" => {
                s["minimum"] = json!(0);
                s["maximum"] = json!(4);
            }
            "pitch" => {
                s["minimum"] = json!(0);
                s["maximum"] = json!(127);
            }
            _ => {}
        }
        properties.insert(key.into(), s);
        if req {
            required.push(key);
        }
    }
    json!({"name":action,"action":action,"description":action.replace('.'," "),"requires_project":!matches!(action,"system.actions"|"project.create"|"project.list"),"inputSchema":{"type":"object","properties":properties,"required":required,"additionalProperties":false}})
}
const ACTIONS: &[&str] = &[
    "system.actions",
    "project.create",
    "project.list",
    "project.get",
    "project.rename",
    "project.settings",
    "brand.update",
    "asset.add",
    "layer.add",
    "layer.update",
    "layer.remove",
    "clip.add",
    "clip.update",
    "clip.remove",
    "clip.split",
    "note.add",
    "note.update",
    "note.remove",
    "history.undo",
    "history.redo",
];
fn validate(c: &Command) -> Result<()> {
    if !ACTIONS.contains(&c.action.as_str()) {
        return Err("Unknown action".into());
    }
    let p = c.params.as_object().ok_or("params must be an object")?;
    let catalog = schema(&c.action);
    let s = &catalog["inputSchema"];
    for key in s["required"].as_array().unwrap() {
        if !p.contains_key(key.as_str().unwrap()) {
            return Err(format!("Missing {}", key));
        }
    }
    for (key, v) in p {
        let spec = &s["properties"][key];
        if spec.is_null() {
            return Err(format!("Unknown parameter {key}"));
        }
        let valid = match spec["type"].as_str().unwrap() {
            "string" => v
                .as_str()
                .map(|x| !x.trim().is_empty() || key == "text")
                .unwrap_or(false),
            "integer" => v.as_i64().is_some(),
            "number" => v.as_f64().map(|x| x.is_finite()).unwrap_or(false),
            "object" => v.is_object(),
            _ => false,
        };
        if !valid {
            return Err(format!("Invalid {key}"));
        }
        if let Some(en) = spec["enum"].as_array() {
            if !en.contains(v) {
                return Err(format!("Invalid {key}"));
            }
        }
        if let Some(n) = v.as_f64() {
            let valid = match key.as_str() {
                "width" | "height" => n > 0.0 && n <= 16384.0,
                "fps" => n > 0.0 && n <= 240.0,
                "bpm" => n >= 20.0 && n <= 400.0,
                "start" | "source_start" | "at" => n >= 0.0 && n <= 1_000_000_000.0,
                "track" => n >= 0.0 && n <= 1024.0,
                "duration" => n > 0.0 && n <= 1_000_000_000.0,
                "opacity" | "velocity" => n >= 0.0 && n <= 1.0,
                "volume" => n >= 0.0 && n <= 4.0,
                "pitch" => n >= 0.0 && n <= 127.0,
                _ => true,
            };
            if !valid {
                return Err(format!("Out of range {key}"));
            }
        }
    }
    Ok(())
}
fn file(store: &Path, pid: &str) -> Result<PathBuf> {
    Uuid::parse_str(pid).map_err(|_| "Invalid project_id")?;
    Ok(store.join(format!("{pid}.json")))
}
fn save(path: &Path, r: &Record) -> Result<()> {
    let temp = path.with_extension(format!("{}.tmp", id()));
    let data = serde_json::to_vec(r).map_err(|e| e.to_string())?;
    let result = (|| {
        let mut f = fs::OpenOptions::new()
            .write(true)
            .create_new(true)
            .open(&temp)?;
        f.write_all(&data)?;
        f.sync_all()?;
        fs::rename(&temp, path)?;
        fs::File::open(path.parent().unwrap())?.sync_all()
    })()
    .map_err(|e: io::Error| e.to_string());
    if result.is_err() {
        let _ = fs::remove_file(temp);
    }
    result
}
fn execute(store: &Path, c: Command) -> Result<Value> {
    validate(&c)?;
    let a = c.action.as_str();
    let p = c.params;
    if a == "system.actions" {
        return Ok(json!(ACTIONS.iter().map(|a| schema(a)).collect::<Vec<_>>()));
    }
    fs::create_dir_all(store).map_err(|e| e.to_string())?;
    if a == "project.list" {
        let mut projects = vec![];
        for entry in fs::read_dir(store).map_err(|e| e.to_string())? {
            let path = entry.map_err(|e| e.to_string())?.path();
            if path.extension().and_then(|x| x.to_str()) == Some("json") {
                let r: Record = serde_json::from_slice(&fs::read(path).map_err(|e| e.to_string())?)
                    .map_err(|e| e.to_string())?;
                projects.push(r.project);
            }
        }
        projects.sort_by(|a, b| a["name"].as_str().cmp(&b["name"].as_str()));
        return Ok(json!(projects));
    }
    if a == "project.create" {
        let project = json!({"id":id(),"name":p["name"],"revision":0,"width":p.get("width").unwrap_or(&json!(1280)),"height":p.get("height").unwrap_or(&json!(720)),"fps":p.get("fps").unwrap_or(&json!(30)),"bpm":p.get("bpm").unwrap_or(&json!(120)),"brand":{},"assets":[],"layers":[],"clips":[],"notes":[]});
        save(
            &file(store, project["id"].as_str().unwrap())?,
            &Record {
                project: project.clone(),
                undo: vec![],
                redo: vec![],
            },
        )?;
        return Ok(project);
    }
    let path = file(store, c.project_id.as_deref().ok_or("project_id required")?)?;
    let mut r: Record = serde_json::from_slice(&fs::read(&path).map_err(|e| e.to_string())?)
        .map_err(|e| e.to_string())?;
    if a == "project.get" {
        return Ok(r.project);
    }
    let rev = r.project["revision"]
        .as_u64()
        .ok_or("Invalid revision")?
        .checked_add(1)
        .ok_or("Revision exhausted")?;
    if a == "history.undo" || a == "history.redo" {
        let (from, to) = if a == "history.undo" {
            (&mut r.undo, &mut r.redo)
        } else {
            (&mut r.redo, &mut r.undo)
        };
        let previous = from.pop().ok_or("History empty")?;
        to.push(r.project);
        r.project = previous;
    } else {
        let previous = r.project.clone();
        mutate(&mut r.project, a, &p)?;
        r.undo.push(previous);
        if r.undo.len() > 100 {
            r.undo.remove(0);
        }
        r.redo.clear();
    }
    r.project["revision"] = json!(rev);
    save(&path, &r)?;
    Ok(r.project)
}
fn mutate(project: &mut Value, a: &str, p: &Value) -> Result<()> {
    match a {
        "project.rename" => project["name"] = p["name"].clone(),
        "project.settings" => {
            for (k, v) in p.as_object().unwrap() {
                project[k] = v.clone();
            }
        }
        "brand.update" => project["brand"] = p["brand"].clone(),
        _ => {
            let collection = if a.starts_with("asset.") {
                "assets"
            } else if a.starts_with("layer.") {
                "layers"
            } else if a.starts_with("clip.") {
                "clips"
            } else {
                "notes"
            };
            if a.starts_with("clip.") && p.get("asset_id").is_some() {
                if !project["assets"].as_array().unwrap().iter().any(|x| {
                    x["id"] == p["asset_id"]
                        && matches!(x["kind"].as_str(), Some("video" | "audio" | "image"))
                }) {
                    return Err("Playable asset_id not found".into());
                }
            }
            let list = project[collection].as_array_mut().unwrap();
            if a.ends_with("add") {
                let mut entity = p.clone();
                entity["id"] = json!(id());
                if collection == "layers" {
                    for (key, value) in [
                        ("x", json!(0)),
                        ("y", json!(0)),
                        ("width", json!(320)),
                        ("height", json!(180)),
                        ("opacity", json!(1)),
                        ("color", json!("#7567ff")),
                    ] {
                        if entity.get(key).is_none() {
                            entity[key] = value;
                        }
                    }
                    if entity["kind"] == "image" && entity.get("path").is_none() {
                        return Err("Image layer needs path".into());
                    }
                }
                if collection == "clips" {
                    if entity.get("source_start").is_none() {
                        entity["source_start"] = json!(0)
                    }
                    if entity.get("volume").is_none() {
                        entity["volume"] = json!(1)
                    }
                }
                if collection == "notes" {
                    if entity.get("track").is_none() {
                        entity["track"] = json!(0)
                    }
                    if entity.get("velocity").is_none() {
                        entity["velocity"] = json!(0.8)
                    }
                }
                list.push(entity);
            } else {
                let index = list
                    .iter()
                    .position(|x| x["id"] == p["id"])
                    .ok_or("Entity not found")?;
                if a.ends_with("remove") {
                    list.remove(index);
                } else if a.ends_with("split") {
                    let clip = &mut list[index];
                    let start = clip["start"].as_f64().unwrap();
                    let duration = clip["duration"].as_f64().unwrap();
                    let at = p["at"].as_f64().unwrap();
                    if at <= start || at >= start + duration {
                        return Err("Split must be inside clip".into());
                    }
                    let mut right = clip.clone();
                    right["id"] = json!(id());
                    right["start"] = json!(at);
                    right["duration"] = json!(start + duration - at);
                    right["source_start"] =
                        json!(clip["source_start"].as_f64().unwrap_or(0.0) + at - start);
                    clip["duration"] = json!(at - start);
                    list.insert(index + 1, right);
                } else {
                    let entity = &mut list[index];
                    for (k, v) in p.as_object().unwrap() {
                        if k != "id" {
                            entity[k] = v.clone();
                        }
                    }
                    if collection == "layers"
                        && entity["kind"] == "image"
                        && entity.get("path").is_none()
                    {
                        return Err("Image layer needs path".into());
                    }
                }
            }
        }
    }
    Ok(())
}
fn main() {
    let args: Vec<String> = std::env::args().collect();
    let result = (|| {
        if args.len() != 3 || args[1] != "--store" {
            return Err("Usage: creative-core --store DIRECTORY".into());
        }
        let mut input = String::new();
        io::stdin()
            .take(2_000_001)
            .read_to_string(&mut input)
            .map_err(|e| e.to_string())?;
        if input.len() > 2_000_000 {
            return Err("Command too large".into());
        }
        let c = serde_json::from_str(&input).map_err(|e| e.to_string())?;
        execute(Path::new(&args[2]), c)
    })();
    match result {
        Ok(r) => println!("{}", json!({"ok":true,"result":r})),
        Err(e) => {
            println!("{}", json!({"ok":false,"error":e}));
            std::process::exit(1)
        }
    }
}
#[cfg(test)]
mod tests {
    use super::*;
    struct Store(PathBuf);
    impl Store {
        fn new() -> Self {
            Self(std::env::temp_dir().join(format!("creative-test-{}", id())))
        }
    }
    impl Drop for Store {
        fn drop(&mut self) {
            let _ = fs::remove_dir_all(&self.0);
        }
    }
    fn run(s: &Store, pid: Option<&str>, a: &str, p: Value) -> Result<Value> {
        execute(
            &s.0,
            Command {
                action: a.into(),
                project_id: pid.map(str::to_string),
                params: p,
            },
        )
    }
    fn create(s: &Store) -> Value {
        run(s, None, "project.create", json!({"name":"Demo"})).unwrap()
    }
    #[test]
    fn persists_and_undo_redo_revisions() {
        let s = Store::new();
        let p = create(&s);
        let pid = p["id"].as_str().unwrap();
        run(&s, Some(pid), "project.rename", json!({"name":"Renamed"})).unwrap();
        let undone = run(&s, Some(pid), "history.undo", json!({})).unwrap();
        assert_eq!(undone["name"], "Demo");
        assert_eq!(undone["revision"], 2);
        let restored = run(&s, Some(pid), "history.redo", json!({})).unwrap();
        assert_eq!(restored["name"], "Renamed");
        assert_eq!(restored["revision"], 3);
        assert_eq!(
            run(&s, Some(pid), "project.get", json!({})).unwrap(),
            restored
        );
    }
    #[test]
    fn new_edit_invalidates_redo() {
        let s = Store::new();
        let p = create(&s);
        let pid = p["id"].as_str().unwrap();
        run(&s, Some(pid), "project.rename", json!({"name":"A"})).unwrap();
        run(&s, Some(pid), "history.undo", json!({})).unwrap();
        run(
            &s,
            Some(pid),
            "brand.update",
            json!({"brand":{"color":"blue"}}),
        )
        .unwrap();
        assert!(run(&s, Some(pid), "history.redo", json!({})).is_err());
    }
    #[test]
    fn rejects_invalid_without_mutation() {
        let s = Store::new();
        let p = create(&s);
        let pid = p["id"].as_str().unwrap();
        for (a, v) in [
            ("project.settings", json!({"width":0})),
            ("note.add", json!({"pitch":128,"start":0,"duration":1})),
            (
                "clip.add",
                json!({"asset_id":"missing","track":0,"start":0,"duration":1}),
            ),
            ("project.rename", json!({"name":"","extra":1})),
            ("layer.remove", json!({"id":"missing"})),
        ] {
            assert!(run(&s, Some(pid), a, v).is_err());
            assert_eq!(run(&s, Some(pid), "project.get", json!({})).unwrap(), p);
        }
    }
    #[test]
    fn split_keeps_offsets_and_can_undo() {
        let s = Store::new();
        let p = create(&s);
        let pid = p["id"].as_str().unwrap();
        let p = run(
            &s,
            Some(pid),
            "asset.add",
            json!({"name":"Take","kind":"video","path":"/media/take.mp4"}),
        )
        .unwrap();
        let p=run(&s,Some(pid),"clip.add",json!({"asset_id":p["assets"][0]["id"],"track":1,"start":10,"duration":8,"source_start":5})).unwrap();
        let cid = &p["clips"][0]["id"];
        for at in [10, 18, 9] {
            assert!(run(&s, Some(pid), "clip.split", json!({"id":cid,"at":at})).is_err());
        }
        let split = run(&s, Some(pid), "clip.split", json!({"id":cid,"at":13})).unwrap();
        assert_eq!(split["clips"][0]["duration"], 3.0);
        assert_eq!(split["clips"][1]["start"], 13.0);
        assert_eq!(split["clips"][1]["source_start"], 8.0);
        assert_eq!(split["clips"][1]["duration"], 5.0);
        assert_ne!(split["clips"][0]["id"], split["clips"][1]["id"]);
        let undone = run(&s, Some(pid), "history.undo", json!({})).unwrap();
        assert_eq!(undone["clips"], p["clips"]);
    }
    #[test]
    fn entity_updates_removals_and_settings() {
        let s = Store::new();
        let p = create(&s);
        let pid = p["id"].as_str().unwrap();
        let p = run(
            &s,
            Some(pid),
            "note.add",
            json!({"pitch":60,"start":0,"duration":1}),
        )
        .unwrap();
        let nid = p["notes"][0]["id"].clone();
        let p = run(&s, Some(pid), "note.update", json!({"id":nid,"pitch":64})).unwrap();
        assert_eq!(p["notes"][0]["pitch"], 64);
        let p = run(&s, Some(pid), "note.remove", json!({"id":nid})).unwrap();
        assert!(p["notes"].as_array().unwrap().is_empty());
        let p = run(
            &s,
            Some(pid),
            "layer.add",
            json!({"name":"Title","kind":"text","text":"Hello"}),
        )
        .unwrap();
        let lid = p["layers"][0]["id"].clone();
        let p = run(
            &s,
            Some(pid),
            "layer.update",
            json!({"id":lid,"opacity":0.5}),
        )
        .unwrap();
        assert_eq!(p["layers"][0]["opacity"], 0.5);
        run(&s, Some(pid), "layer.remove", json!({"id":lid})).unwrap();
        let p = run(
            &s,
            Some(pid),
            "project.settings",
            json!({"fps":60,"bpm":140}),
        )
        .unwrap();
        assert_eq!(p["fps"], 60);
        assert_eq!(run(&s, None, "project.list", json!({})).unwrap()[0], p);
    }
    #[test]
    fn catalog_and_path_confinement() {
        let s = Store::new();
        let catalog = run(&s, None, "system.actions", json!({})).unwrap();
        assert_eq!(catalog.as_array().unwrap().len(), ACTIONS.len());
        assert_eq!(
            schema("clip.add")["inputSchema"]["additionalProperties"],
            false
        );
        assert!(run(&s, Some("../../bad"), "project.get", json!({})).is_err());
        assert!(run(&s, None, "bogus", json!({})).is_err());
    }
}
