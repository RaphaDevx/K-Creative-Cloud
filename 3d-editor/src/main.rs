use editor_3d::{
    branding::Brand,
    commands::{CommandGroup, Document},
    obj, persistence, Result,
};
use std::path::Path;

fn run() -> Result<()> {
    let args: Vec<String> = std::env::args().skip(1).collect();
    match args.first().map(String::as_str) {
        Some("new") if args.len() == 2 => {
            persistence::save(Path::new(&args[1]), &Document::default())
        }
        Some("inspect") if args.len() == 2 => {
            let document = persistence::load(Path::new(&args[1]))?;
            println!(
                "{}",
                serde_json::json!({"schema_version":document.schema_version,"revision":document.revision,"scene_id":document.scene.id,"objects":document.scene.objects.len(),"scene":document.scene,"history":document.history})
            );
            Ok(())
        }
        Some("apply") if args.len() == 4 => {
            let mut document = persistence::load(Path::new(&args[1]))?;
            let bytes =
                persistence::read_bounded(Path::new(&args[2]), persistence::MAX_FILE_BYTES)?;
            let group: CommandGroup = serde_json::from_slice(&bytes).map_err(|e| e.to_string())?;
            document.apply(group)?;
            persistence::save(Path::new(&args[3]), &document)
        }
        Some("export-obj") if args.len() == 3 => {
            let document = persistence::load(Path::new(&args[1]))?;
            persistence::write_atomic(
                Path::new(&args[2]),
                obj::export(&document.scene)?.as_bytes(),
            )
        }
        Some(action @ ("undo" | "redo")) if args.len() == 3 => {
            let mut document = persistence::load(Path::new(&args[1]))?;
            if action == "undo" {
                document.undo()?;
            } else {
                document.redo()?;
            }
            persistence::save(Path::new(&args[2]), &document)
        }
        Some("--help") => {
            println!("3d-editor [--scene FILE] [--brand PROFILE]\n3d-editor new FILE\n3d-editor inspect FILE\n3d-editor apply INPUT GROUP_JSON OUTPUT\n3d-editor undo INPUT OUTPUT\n3d-editor redo INPUT OUTPUT\n3d-editor export-obj INPUT OUTPUT");
            Ok(())
        }
        Some(command) if !command.starts_with("--") => {
            Err("Unbekannter oder unvollständiger Befehl. Siehe --help.".into())
        }
        _ => {
            let mut brand = Brand::default();
            let mut scene = None;
            let mut i = 0;
            while i < args.len() {
                let value = args.get(i + 1).ok_or("Fehlender Optionswert.")?;
                match args[i].as_str() {
                    "--brand" => brand = Brand::load(Path::new(value))?,
                    "--scene" => scene = Some(std::path::PathBuf::from(value)),
                    _ => return Err("Unbekannte Option. Siehe --help.".into()),
                }
                i += 2;
            }
            brand.validate()?;
            #[cfg(feature = "desktop")]
            {
                editor_3d::ui::launch(brand, scene)
            }
            #[cfg(not(feature = "desktop"))]
            {
                let _ = (brand, scene);
                Err("Desktop-Unterstützung ist in diesem Build deaktiviert.".into())
            }
        }
    }
}
fn main() {
    if let Err(error) = run() {
        eprintln!("{}", serde_json::json!({"ok":false,"error":error}));
        std::process::exit(1);
    }
}
