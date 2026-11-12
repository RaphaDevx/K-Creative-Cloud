use crate::{
    mesh::{Mesh, MAX_FACES, MAX_VERTICES},
    scene::Scene,
    Result,
};
use glam::Vec3;
use std::fmt::Write;

pub fn parse(text: &str) -> Result<Mesh> {
    if text.len() as u64 > crate::persistence::MAX_FILE_BYTES {
        return Err("OBJ-Datei ist zu groß.".into());
    }
    let mut mesh = Mesh {
        positions: Vec::new(),
        faces: Vec::new(),
    };
    for (line_index, line) in text.lines().enumerate() {
        let line = line.split('#').next().unwrap_or("");
        let mut words = line.split_whitespace();
        match words.next() {
            Some("v") => {
                let values: Vec<f32> = words
                    .map(str::parse)
                    .collect::<std::result::Result<_, _>>()
                    .map_err(|_| format!("OBJ Zeile {}: ungültiger Punkt.", line_index + 1))?;
                if values.len() != 3 || mesh.positions.len() >= MAX_VERTICES {
                    return Err(
                        "OBJ: nur dreidimensionale Punkte bis 100000 werden unterstützt.".into(),
                    );
                }
                mesh.positions.push([values[0], values[1], values[2]]);
            }
            Some("f") => {
                let mut face = Vec::new();
                for word in words {
                    let raw: i64 = word
                        .split('/')
                        .next()
                        .unwrap_or("")
                        .parse()
                        .map_err(|_| "OBJ: ungültiger Flächenindex.")?;
                    let index = if raw > 0 {
                        raw - 1
                    } else if raw < 0 {
                        mesh.positions.len() as i64 + raw
                    } else {
                        -1
                    };
                    if index < 0 || index as usize >= mesh.positions.len() || face.len() >= 256 {
                        return Err("OBJ: Punktreferenz außerhalb des gültigen Bereichs.".into());
                    }
                    face.push(index as u32);
                }
                if mesh.faces.len() >= MAX_FACES {
                    return Err("OBJ: zu viele Flächen.".into());
                }
                mesh.faces.push(face);
            }
            _ => {} // Object groups, UVs, normals and external materials are not imported in v0.1.
        }
    }
    mesh.validate()?;
    Ok(mesh)
}
pub fn export(scene: &Scene) -> Result<String> {
    scene.validate()?;
    let mut text = String::from("# 3d-editor OBJ; metres; visible polygon geometry only\n");
    let mut offset = 1u32;
    for object in scene.objects.iter().filter(|o| o.visible) {
        writeln!(
            text,
            "o {}",
            object
                .name
                .chars()
                .map(|c| if c.is_whitespace() || c == '#' {
                    '_'
                } else {
                    c
                })
                .collect::<String>()
        )
        .unwrap();
        for position in &object.mesh.positions {
            let p = object
                .transform
                .matrix()
                .transform_point3(Vec3::from(*position));
            writeln!(text, "v {} {} {}", p.x, p.y, p.z).unwrap();
        }
        for face in &object.mesh.faces {
            text.push('f');
            for i in face {
                write!(text, " {}", i + offset).unwrap();
            }
            text.push('\n');
        }
        offset += object.mesh.positions.len() as u32;
    }
    Ok(text)
}
