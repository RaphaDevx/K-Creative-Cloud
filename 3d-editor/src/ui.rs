use crate::{
    branding::Brand,
    camera::Camera,
    commands::{Command, CommandGroup, Document},
    mesh::Primitive,
    obj, persistence, renderer,
    scene::Object,
    selection::{self, Element, ElementMode},
    Result,
};
use eframe::egui::{self, Color32, RichText};
use std::path::PathBuf;

pub fn launch(brand: Brand, path: Option<PathBuf>) -> Result<()> {
    let document = match &path {
        Some(path) => persistence::load(path)?,
        None => Document::default(),
    };
    let title = brand.app_name.clone();
    let options = eframe::NativeOptions {
        viewport: egui::ViewportBuilder::default()
            .with_title(&title)
            .with_inner_size([1440., 900.])
            .with_min_inner_size([960., 640.]),
        renderer: eframe::Renderer::Wgpu,
        ..Default::default()
    };
    eframe::run_native(
        &title,
        options,
        Box::new(move |cc| {
            let state = cc
                .wgpu_render_state
                .as_ref()
                .ok_or("GPU-Renderer nicht verfügbar")?;
            renderer::install(state);
            let mut style = (*cc.egui_ctx.style()).clone();
            style.spacing.item_spacing = egui::vec2(8., 8.);
            style.spacing.button_padding = egui::vec2(10., 6.);
            style.spacing.interact_size = egui::vec2(28., 28.);
            style
                .text_styles
                .insert(egui::TextStyle::Body, egui::FontId::proportional(14.));
            style
                .text_styles
                .insert(egui::TextStyle::Button, egui::FontId::proportional(13.));
            style
                .text_styles
                .insert(egui::TextStyle::Small, egui::FontId::proportional(12.));
            cc.egui_ctx.set_style(style);
            apply_identity(&cc.egui_ctx, &brand);
            Ok(Box::new(Editor::new(brand, document, path)))
        }),
    )
    .map_err(|e| e.to_string())
}

enum Pending {
    New,
    Open(PathBuf),
    Close,
}
#[derive(Clone, Copy, PartialEq, Eq)]
enum SelectionMode {
    Object,
    Face,
    Vertex,
    Edge,
}
impl SelectionMode {
    fn label(self) -> &'static str {
        match self {
            Self::Object => "Objektmodus",
            Self::Face => "Flächenmodus",
            Self::Vertex => "Punktmodus",
            Self::Edge => "Kantenmodus",
        }
    }
}
pub struct Editor {
    brand: Brand,
    document: Document,
    path: Option<PathBuf>,
    dirty: bool,
    start: bool,
    selected: Option<String>,
    face: Option<usize>,
    draft: Option<Object>,
    camera: Camera,
    mode: SelectionMode,
    element: Option<Element>,
    point_draft: Option<[f32; 3]>,
    edge_offset: [f32; 3],
    wireframe: bool,
    extrusion: f32,
    inset_factor: f32,
    error: Option<String>,
    status: String,
    pending: Option<Pending>,
    allow_close: bool,
    about: bool,
}
fn rgb(v: [u8; 3]) -> Color32 {
    Color32::from_rgb(v[0], v[1], v[2])
}
fn apply_identity(ctx: &egui::Context, brand: &Brand) {
    ctx.style_mut(|style| {
        let content = if style.visuals.dark_mode {
            Color32::from_gray(216)
        } else {
            Color32::from_gray(40)
        };
        style.visuals.widgets.inactive.fg_stroke.color = content;
        style.visuals.widgets.hovered.fg_stroke.color = content;
        style.visuals.widgets.active.fg_stroke.color = content;
        style.visuals.selection.bg_fill = rgb(brand.accent);
        style.visuals.selection.stroke.color = rgb(Brand::ink_on(brand.accent));
    });
}
impl Editor {
    fn new(brand: Brand, document: Document, path: Option<PathBuf>) -> Self {
        let start = path.is_none();
        let selected = document.scene.objects.first().map(|o| o.id.clone());
        let draft = selected
            .as_deref()
            .and_then(|id| document.scene.object(id).ok())
            .cloned();
        Self {
            brand,
            document,
            path,
            dirty: false,
            start,
            selected,
            face: None,
            draft,
            camera: Camera::default(),
            mode: SelectionMode::Object,
            element: None,
            point_draft: None,
            edge_offset: [0.; 3],
            wireframe: false,
            extrusion: 0.35,
            inset_factor: 0.2,
            error: None,
            status: "Bereit".into(),
            pending: None,
            allow_close: false,
            about: false,
        }
    }
    fn refresh(&mut self) {
        if self
            .selected
            .as_deref()
            .is_some_and(|id| self.document.scene.object(id).is_err())
        {
            self.selected = None;
            self.face = None;
            self.element = None;
        }
        self.draft = self
            .selected
            .as_deref()
            .and_then(|id| self.document.scene.object(id).ok())
            .cloned();
        if self.face.is_some_and(|face| {
            self.draft
                .as_ref()
                .is_none_or(|o| face >= o.mesh.faces.len())
        }) {
            self.face = None;
        }
        self.point_draft = match (self.draft.as_ref(), self.element) {
            (Some(object), Some(Element::Vertex(index))) => {
                object.mesh.positions.get(index).copied()
            }
            _ => None,
        };
        if matches!(self.element, Some(Element::Vertex(_))) && self.point_draft.is_none() {
            self.element = None;
        }
    }
    fn select(&mut self, id: Option<String>, face: Option<usize>) {
        self.selected = id;
        self.face = face;
        self.element = None;
        self.edge_offset = [0.; 3];
        self.refresh();
    }
    fn set_mode(&mut self, mode: SelectionMode) {
        self.mode = mode;
        self.face = None;
        self.element = None;
        self.point_draft = None;
        self.edge_offset = [0.; 3];
    }
    fn execute(&mut self, label: &str, commands: Vec<Command>) {
        let replace_topology = commands
            .iter()
            .any(|command| matches!(command, Command::Subdivide { .. }));
        let group = CommandGroup {
            expected_revision: self.document.revision,
            actor: "local-user".into(),
            task_path: vec!["Szene".into(), label.into()],
            label: label.into(),
            commands,
        };
        match self.document.apply(group) {
            Ok(()) => {
                self.dirty = true;
                self.status = label.into();
                self.error = None;
                if replace_topology {
                    self.face = None;
                    self.element = None;
                }
                self.refresh();
            }
            Err(error) => self.error = Some(error),
        }
    }
    fn add(&mut self, primitive: Primitive) {
        let revision = self.document.revision;
        self.execute(primitive.label(), vec![Command::Add { primitive }]);
        if self.document.revision != revision {
            self.select(
                self.document.scene.objects.last().map(|o| o.id.clone()),
                None,
            );
        }
    }
    fn travel(&mut self, redo: bool) {
        let result = if redo {
            self.document.redo()
        } else {
            self.document.undo()
        };
        match result {
            Ok(()) => {
                self.dirty = true;
                self.refresh();
                self.status = if redo {
                    "Wiederhergestellt"
                } else {
                    "Rückgängig gemacht"
                }
                .into();
            }
            Err(error) => self.error = Some(error),
        }
    }
    fn save(&mut self, save_as: bool) -> bool {
        let path = if save_as || self.path.is_none() {
            rfd::FileDialog::new()
                .add_filter("3d-editor Szene", &["scene3d"])
                .set_file_name("Szene.scene3d")
                .save_file()
        } else {
            self.path.clone()
        };
        let Some(mut path) = path else {
            return false;
        };
        if path.extension().is_none() {
            path.set_extension("scene3d");
        }
        match persistence::save(&path, &self.document) {
            Ok(()) => {
                self.status = format!("Gespeichert: {}", path.display());
                self.path = Some(path);
                self.dirty = false;
                self.error = None;
                true
            }
            Err(error) => {
                self.error = Some(error);
                false
            }
        }
    }
    fn request(&mut self, pending: Pending, ctx: &egui::Context) {
        if self.dirty {
            self.pending = Some(pending);
        } else {
            self.proceed(pending, ctx);
        }
    }
    fn proceed(&mut self, pending: Pending, ctx: &egui::Context) {
        match pending {
            Pending::New => {
                self.document = Document::default();
                self.path = None;
                self.dirty = false;
                self.start = false;
                self.camera = Camera::default();
                self.face = None;
                self.error = None;
                self.add(Primitive::Cube);
            }
            Pending::Open(path) => match persistence::load(&path) {
                Ok(document) => {
                    self.document = document;
                    self.path = Some(path);
                    self.dirty = false;
                    self.start = false;
                    self.camera = Camera::default();
                    self.selected = self.document.scene.objects.first().map(|o| o.id.clone());
                    self.face = None;
                    self.error = None;
                    self.refresh();
                    self.status = "Szene geöffnet".into();
                }
                Err(error) => self.error = Some(error),
            },
            Pending::Close => {
                self.allow_close = true;
                ctx.send_viewport_cmd(egui::ViewportCommand::Close);
            }
        }
    }
    fn open(&mut self, ctx: &egui::Context) {
        if let Some(path) = rfd::FileDialog::new()
            .add_filter("3d-editor Szene", &["scene3d"])
            .pick_file()
        {
            self.request(Pending::Open(path), ctx);
        }
    }
    fn import(&mut self) {
        let Some(path) = rfd::FileDialog::new()
            .add_filter("Wavefront OBJ", &["obj"])
            .pick_file()
        else {
            return;
        };
        let result = persistence::read_bounded(&path, persistence::MAX_FILE_BYTES)
            .and_then(|bytes| String::from_utf8(bytes).map_err(|e| e.to_string()))
            .and_then(|text| obj::parse(&text));
        match result {
            Ok(mesh) => {
                let revision = self.document.revision;
                self.execute(
                    "OBJ importieren",
                    vec![Command::ImportMesh {
                        name: path
                            .file_stem()
                            .unwrap_or_default()
                            .to_string_lossy()
                            .into(),
                        mesh,
                    }],
                );
                if revision != self.document.revision {
                    self.select(
                        self.document.scene.objects.last().map(|o| o.id.clone()),
                        None,
                    );
                    self.focus();
                    self.status="OBJ-Geometrie importiert. UVs und Fremdmaterialien werden nicht übernommen.".into();
                }
            }
            Err(error) => self.error = Some(error),
        }
    }
    fn export(&mut self) {
        let Some(path) = rfd::FileDialog::new()
            .add_filter("Wavefront OBJ", &["obj"])
            .set_file_name("Szene.obj")
            .save_file()
        else {
            return;
        };
        match obj::export(&self.document.scene)
            .and_then(|text| persistence::write_atomic(&path, text.as_bytes()))
        {
            Ok(()) => {
                self.status =
                    "Sichtbare Geometrie als OBJ exportiert; ohne Materialien und Verlauf.".into()
            }
            Err(error) => self.error = Some(error),
        }
    }
    fn focus(&mut self) {
        if let Some(object) = self
            .selected
            .as_deref()
            .and_then(|id| self.document.scene.object(id).ok())
        {
            self.camera.focus(object);
        }
    }
    fn duplicate(&mut self) {
        if let Some(id) = self.selected.clone() {
            let revision = self.document.revision;
            self.execute("Objekt duplizieren", vec![Command::Duplicate { id }]);
            if revision != self.document.revision {
                self.select(
                    self.document.scene.objects.last().map(|o| o.id.clone()),
                    None,
                );
            }
        }
    }
    fn remove(&mut self) {
        if let Some(id) = self.selected.clone() {
            self.execute("Objekt entfernen", vec![Command::Remove { id }]);
        }
    }
    fn shortcuts(&mut self, ctx: &egui::Context) {
        if self.pending.is_some() {
            return;
        }
        let consume = |key, shift| {
            ctx.input_mut(|input| {
                input.consume_key(
                    egui::Modifiers {
                        command: true,
                        shift,
                        ..Default::default()
                    },
                    key,
                )
            })
        };
        if consume(egui::Key::N, false) {
            self.request(Pending::New, ctx);
        }
        if consume(egui::Key::O, false) {
            self.open(ctx);
        }
        if consume(egui::Key::S, true) {
            self.save(true);
        } else if consume(egui::Key::S, false) {
            self.save(false);
        }
        if !ctx.wants_keyboard_input() && !self.start {
            if consume(egui::Key::Z, true) || consume(egui::Key::Y, false) {
                self.travel(true);
            } else if consume(egui::Key::Z, false) {
                self.travel(false);
            }
            if consume(egui::Key::D, false) {
                self.duplicate();
            }
            if ctx.input(|input| input.key_pressed(egui::Key::Delete)) {
                self.remove();
            }
            if ctx.input(|input| input.key_pressed(egui::Key::F)) {
                self.focus();
            }
        }
    }
    fn header(&mut self, ctx: &egui::Context) {
        egui::TopBottomPanel::top("application-header").show(ctx, |ui| {
            egui::menu::bar(ui, |ui| {
                ui.label(RichText::new(&self.brand.app_name).strong());
                ui.separator();
                ui.menu_button("Datei", |ui| {
                    if ui.button("Neue Szene     Ctrl/Cmd+N").clicked() {
                        self.request(Pending::New, ctx);
                        ui.close_menu();
                    }
                    if ui.button("Öffnen …          Ctrl/Cmd+O").clicked() {
                        self.open(ctx);
                        ui.close_menu();
                    }
                    if ui
                        .add_enabled(
                            !self.start,
                            egui::Button::new("Speichern         Ctrl/Cmd+S"),
                        )
                        .clicked()
                    {
                        self.save(false);
                        ui.close_menu();
                    }
                    if ui
                        .add_enabled(!self.start, egui::Button::new("Speichern unter …"))
                        .clicked()
                    {
                        self.save(true);
                        ui.close_menu();
                    }
                    ui.separator();
                    if ui
                        .add_enabled(!self.start, egui::Button::new("OBJ importieren …"))
                        .clicked()
                    {
                        self.import();
                        ui.close_menu();
                    }
                    if ui
                        .add_enabled(!self.start, egui::Button::new("OBJ exportieren …"))
                        .clicked()
                    {
                        self.export();
                        ui.close_menu();
                    }
                    ui.separator();
                    if ui.button("Schliessen").clicked() {
                        self.request(Pending::Close, ctx);
                        ui.close_menu();
                    }
                });
                ui.menu_button("Bearbeiten", |ui| {
                    if ui
                        .add_enabled(
                            self.document.can_undo(),
                            egui::Button::new("Rückgängig     Ctrl/Cmd+Z"),
                        )
                        .clicked()
                    {
                        self.travel(false);
                        ui.close_menu();
                    }
                    if ui
                        .add_enabled(
                            self.document.can_redo(),
                            egui::Button::new("Wiederholen    Ctrl/Cmd+Shift+Z"),
                        )
                        .clicked()
                    {
                        self.travel(true);
                        ui.close_menu();
                    }
                    ui.separator();
                    if ui
                        .add_enabled(
                            self.selected.is_some(),
                            egui::Button::new("Duplizieren     Ctrl/Cmd+D"),
                        )
                        .clicked()
                    {
                        self.duplicate();
                        ui.close_menu();
                    }
                    if ui
                        .add_enabled(
                            self.selected.is_some(),
                            egui::Button::new("Entfernen       Delete"),
                        )
                        .clicked()
                    {
                        self.remove();
                        ui.close_menu();
                    }
                });
                ui.menu_button("Modellieren", |ui| {
                    let face_selection = self.selected.clone().zip(self.face);
                    if ui
                        .add_enabled(
                            face_selection.is_some(),
                            egui::Button::new("Fläche extrudieren"),
                        )
                        .clicked()
                    {
                        if let Some((id, face)) = face_selection.clone() {
                            self.execute(
                                "Fläche extrudieren",
                                vec![Command::Extrude {
                                    id,
                                    face,
                                    distance: self.extrusion,
                                }],
                            );
                        }
                        ui.close_menu();
                    }
                    if ui
                        .add_enabled(
                            face_selection.is_some(),
                            egui::Button::new("Fläche einrücken"),
                        )
                        .clicked()
                    {
                        if let Some((id, face)) = face_selection {
                            self.execute(
                                "Fläche einrücken",
                                vec![Command::Inset {
                                    id,
                                    face,
                                    factor: self.inset_factor,
                                }],
                            );
                        }
                        ui.close_menu();
                    }
                    if ui
                        .add_enabled(
                            self.selected.is_some(),
                            egui::Button::new("Mesh linear unterteilen"),
                        )
                        .clicked()
                    {
                        if let Some(id) = self.selected.clone() {
                            self.execute("Mesh unterteilen", vec![Command::Subdivide { id }]);
                        }
                        ui.close_menu();
                    }
                });
                ui.menu_button("Ansicht", |ui| {
                    if ui.button("Auswahl fokussieren     F").clicked() {
                        self.focus();
                        ui.close_menu();
                    }
                    if ui.button("Kamera zurücksetzen").clicked() {
                        self.camera = Camera::default();
                        ui.close_menu();
                    }
                    ui.checkbox(&mut self.wireframe, "Polygonkanten anzeigen");
                    if ui.button("Startseite").clicked() {
                        self.start = true;
                        ui.close_menu();
                    }
                });
                ui.menu_button("Programm", |ui| {
                    if ui.button("Markenprofil laden …").clicked() {
                        if let Some(path) = rfd::FileDialog::new()
                            .add_filter("Markenprofil", &["json"])
                            .pick_file()
                        {
                            match Brand::load(&path) {
                                Ok(brand) => {
                                    self.brand = brand;
                                    apply_identity(ctx, &self.brand);
                                    ctx.send_viewport_cmd(egui::ViewportCommand::Title(
                                        self.brand.app_name.clone(),
                                    ));
                                }
                                Err(error) => self.error = Some(error),
                            }
                        }
                        ui.close_menu();
                    }
                    if ui.button("Über 3d-editor").clicked() {
                        self.about = true;
                        ui.close_menu();
                    }
                });
            });
        });
        if let Some(error) = self.error.clone() {
            egui::TopBottomPanel::top("error-message").show(ctx, |ui| {
                ui.horizontal_wrapped(|ui| {
                    ui.colored_label(ui.visuals().error_fg_color, error);
                    if ui.button("Schliessen").clicked() {
                        self.error = None;
                    }
                });
            });
        }
    }
    fn startup(&mut self, ctx: &egui::Context) {
        egui::CentralPanel::default().show(ctx,|ui| {
            let width=ui.available_width();let height=ui.available_height();
            ui.add_space((height*0.12).max(28.));
            let hero_width=(width-80.).min(1000.);
            ui.horizontal(|ui|{ui.add_space(((width-hero_width)*0.5).max(12.));
                egui::Frame::new().fill(rgb(self.brand.launch_background)).corner_radius(16.).inner_margin(40.).show(ui,|ui| {ui.vertical(|ui| {
                    ui.set_width((hero_width-80.).max(500.));
                    let ink=rgb(Brand::ink_on(self.brand.launch_background));let accent=rgb(self.brand.accent);
                    ui.horizontal(|ui| {
                        let (rect,_)=ui.allocate_exact_size(egui::vec2(92.,92.),egui::Sense::hover());
                        let painter=ui.painter();let center=rect.center();
                        painter.rect_filled(rect,18.,accent);
                        painter.text(center,egui::Align2::CENTER_CENTER,&self.brand.monogram,egui::FontId::proportional(29.),rgb(Brand::ink_on(self.brand.accent)));
                        ui.add_space(24.);ui.vertical(|ui|{ui.label(RichText::new(&self.brand.wordmark).size(48.).strong().color(ink));ui.label(RichText::new(&self.brand.launch_line).size(20.).color(ink));});
                    });
                    ui.add_space(40.);
                    ui.label(RichText::new("Form geben. Raum schaffen.").size(28.).color(ink));
                    ui.add_space(8.);ui.label(RichText::new("Eine eigene Arbeitsfläche für deine dreidimensionalen Ideen.").size(15.).color(ink));
                    ui.add_space(28.);
                    ui.horizontal(|ui| {
                        if ui.add_sized([170.,42.],egui::Button::new(RichText::new("Neue Szene").color(rgb(Brand::ink_on(self.brand.accent)))).fill(accent)).clicked(){self.request(Pending::New,ctx);}
                        if ui.add_sized([170.,42.],egui::Button::new("Szene öffnen …")).clicked(){self.open(ctx);}
                        if !self.document.scene.objects.is_empty()&&ui.add_sized([170.,42.],egui::Button::new("Weiterarbeiten")).clicked(){self.start=false;}
                    });
                    ui.add_space(22.);ui.label(RichText::new("Lokal arbeiten · Eigene Szenendateien · Jeder Schritt bleibt nachvollziehbar").size(13.).color(ink));
                });});
            });
        });
    }
    fn scene_tree(&mut self, ctx: &egui::Context) {
        egui::SidePanel::left("scene-tree")
            .default_width(195.)
            .width_range(165.0..=320.0)
            .resizable(true)
            .show(ctx, |ui| {
                ui.add_space(10.);
                ui.heading("Szene");
                ui.label(RichText::new(&self.document.scene.name).small());
                ui.add_space(12.);
                ui.menu_button("+ Objekt hinzufügen", |ui| {
                    for kind in [
                        Primitive::Cube,
                        Primitive::Sphere,
                        Primitive::Cylinder,
                        Primitive::Plane,
                    ] {
                        if ui.button(kind.label()).clicked() {
                            self.add(kind);
                            ui.close_menu();
                        }
                    }
                });
                ui.add_space(12.);
                ui.separator();
                let rows: Vec<_> = self
                    .document
                    .scene
                    .objects
                    .iter()
                    .map(|o| (o.id.clone(), o.name.clone(), o.visible))
                    .collect();
                egui::ScrollArea::vertical().show(ui, |ui| {
                    for (id, name, visible) in rows {
                        let text = if visible {
                            name
                        } else {
                            format!("{name} (verborgen)")
                        };
                        let selected = self.selected.as_deref() == Some(&id);
                        let text = RichText::new(text).color(if selected {
                            rgb(Brand::ink_on(self.brand.accent))
                        } else {
                            ui.visuals().text_color()
                        });
                        if ui
                            .add_sized(
                                [ui.available_width(), 30.],
                                egui::Button::new(text).selected(selected),
                            )
                            .clicked()
                        {
                            self.select(Some(id), None);
                        }
                    }
                });
            });
    }
    fn inspector(&mut self, ctx: &egui::Context) {
        egui::SidePanel::right("object-inspector")
            .default_width(280.)
            .width_range(250.0..=400.0)
            .resizable(true)
            .show(ctx, |ui| {
                ui.add_space(10.);
                ui.heading("Eigenschaften");
                ui.add_space(12.);
                egui::ScrollArea::vertical().show(ui, |ui| {
                    let mut apply = false;
                    if let Some(draft) = &mut self.draft {
                        ui.label("Objektname");
                        ui.text_edit_singleline(&mut draft.name);
                        ui.add_space(10.);
                        egui::CollapsingHeader::new("Transformation")
                            .default_open(true)
                            .show(ui, |ui| {
                                for (label, values, speed) in [
                                    ("Position · m", &mut draft.transform.translation, 0.01),
                                    ("Rotation · °", &mut draft.transform.rotation_degrees, 0.5),
                                    ("Skalierung", &mut draft.transform.scale, 0.01),
                                ] {
                                    ui.label(label);
                                    ui.horizontal(|ui| {
                                        for (axis, value) in
                                            ["X", "Y", "Z"].into_iter().zip(values.iter_mut())
                                        {
                                            ui.add(
                                                egui::DragValue::new(value)
                                                    .prefix(format!("{axis} "))
                                                    .speed(speed)
                                                    .max_decimals(3),
                                            );
                                        }
                                    });
                                }
                            });
                        ui.add_space(8.);
                        ui.label("Materialfarbe");
                        ui.color_edit_button_rgb(&mut draft.color);
                        ui.checkbox(&mut draft.visible, "Sichtbar");
                        ui.add_space(8.);
                        apply = ui
                            .add_sized(
                                [ui.available_width(), 32.],
                                egui::Button::new("Änderungen anwenden"),
                            )
                            .clicked();
                        ui.add_space(14.);
                        ui.separator();
                        ui.label(format!(
                            "{} Punkte · {} Flächen",
                            draft.mesh.positions.len(),
                            draft.mesh.faces.len()
                        ));
                    } else {
                        ui.label("Wähle ein Objekt in der Szene oder der 3D-Ansicht.");
                    }
                    if apply {
                        if let Some(draft) = self.draft.clone() {
                            if let Ok(original) = self.document.scene.object(&draft.id) {
                                let mut commands = Vec::new();
                                if draft.name != original.name {
                                    commands.push(Command::Rename {
                                        id: draft.id.clone(),
                                        name: draft.name,
                                    });
                                }
                                if draft.transform != original.transform {
                                    commands.push(Command::Transform {
                                        id: draft.id.clone(),
                                        transform: draft.transform,
                                    });
                                }
                                if draft.color != original.color {
                                    commands.push(Command::Color {
                                        id: draft.id.clone(),
                                        color: draft.color,
                                    });
                                }
                                if draft.visible != original.visible {
                                    commands.push(Command::Visibility {
                                        id: draft.id.clone(),
                                        visible: draft.visible,
                                    });
                                }
                                if !commands.is_empty() {
                                    self.execute("Objekteigenschaften", commands);
                                }
                            }
                        }
                    }
                    if let (Some(id), Some(face)) = (self.selected.clone(), self.face) {
                        ui.add_space(12.);
                        ui.heading("Fläche");
                        ui.label(format!("Ausgewählt: {}", face + 1));
                        ui.label("Extrusion · lokale Meter");
                        ui.add(
                            egui::DragValue::new(&mut self.extrusion)
                                .speed(0.01)
                                .range(0.0001..=1000.)
                                .max_decimals(3),
                        );
                        if ui
                            .add_sized(
                                [ui.available_width(), 32.],
                                egui::Button::new("Fläche extrudieren"),
                            )
                            .clicked()
                        {
                            self.execute(
                                "Fläche extrudieren",
                                vec![Command::Extrude {
                                    id: id.clone(),
                                    face,
                                    distance: self.extrusion,
                                }],
                            );
                        }
                        ui.add_space(10.);
                        ui.label("Einrücken · Anteil zur Flächenmitte");
                        ui.add(
                            egui::DragValue::new(&mut self.inset_factor)
                                .range(0.01..=0.95)
                                .speed(0.01)
                                .max_decimals(2),
                        );
                        if ui
                            .add_sized(
                                [ui.available_width(), 32.],
                                egui::Button::new("Fläche einrücken"),
                            )
                            .clicked()
                        {
                            self.execute(
                                "Fläche einrücken",
                                vec![Command::Inset {
                                    id,
                                    face,
                                    factor: self.inset_factor,
                                }],
                            );
                        }
                    } else if self.selected.is_some() && self.mode == SelectionMode::Face {
                        ui.add_space(12.);
                        ui.label("Im Flächenmodus eine Fläche anklicken, um sie zu extrudieren.");
                    }
                    if let (Some(id), Some(Element::Vertex(vertex))) =
                        (self.selected.clone(), self.element)
                    {
                        ui.add_space(12.);
                        ui.heading(format!("Punkt {}", vertex + 1));
                        ui.label("Lokale Position · m");
                        if let Some(position) = &mut self.point_draft {
                            ui.horizontal(|ui| {
                                for (axis, value) in
                                    ["X", "Y", "Z"].into_iter().zip(position.iter_mut())
                                {
                                    ui.add(
                                        egui::DragValue::new(value)
                                            .prefix(format!("{axis} "))
                                            .speed(0.01)
                                            .max_decimals(3),
                                    );
                                }
                            });
                        }
                        ui.small("Angrenzende Polygone werden dabei trianguliert.");
                        if ui
                            .add_sized(
                                [ui.available_width(), 32.],
                                egui::Button::new("Punktposition anwenden"),
                            )
                            .clicked()
                        {
                            if let Some(position) = self.point_draft {
                                self.execute(
                                    "Punkt verschieben",
                                    vec![Command::MoveVertex {
                                        id,
                                        vertex,
                                        position,
                                    }],
                                );
                            }
                        }
                    }
                    if let (Some(id), Some(Element::Edge(edge))) =
                        (self.selected.clone(), self.element)
                    {
                        ui.add_space(12.);
                        ui.heading("Kante");
                        ui.label(format!("Punkte {} und {}", edge[0] + 1, edge[1] + 1));
                        ui.label("Lokal verschieben · m");
                        ui.horizontal(|ui| {
                            for (axis, value) in
                                ["X", "Y", "Z"].into_iter().zip(self.edge_offset.iter_mut())
                            {
                                ui.add(
                                    egui::DragValue::new(value)
                                        .prefix(format!("{axis} "))
                                        .speed(0.01)
                                        .max_decimals(3),
                                );
                            }
                        });
                        ui.small("Beide Punkte bewegen; angrenzende Polygone triangulieren.");
                        if ui
                            .add_enabled(
                                self.edge_offset != [0.; 3],
                                egui::Button::new("Kante verschieben"),
                            )
                            .clicked()
                        {
                            let revision = self.document.revision;
                            self.execute(
                                "Kante verschieben",
                                vec![Command::MoveEdge {
                                    id,
                                    edge,
                                    offset: self.edge_offset,
                                }],
                            );
                            if self.document.revision != revision {
                                self.edge_offset = [0.; 3];
                            }
                        }
                    }
                    if self.selected.is_some()
                        && self.element.is_none()
                        && matches!(self.mode, SelectionMode::Vertex | SelectionMode::Edge)
                    {
                        ui.add_space(12.);
                        ui.label(if self.mode == SelectionMode::Vertex {
                            "Einen sichtbaren Punkt in der 3D-Ansicht anklicken."
                        } else {
                            "Eine sichtbare Kante in der 3D-Ansicht anklicken."
                        });
                    }
                    if self.selected.is_some() {
                        ui.add_space(12.);
                        ui.collapsing("Mesh-Werkzeuge", |ui| {
                            ui.label("Linear unterteilen: gemeinsame Kantenpunkte, ohne Glättung.");
                            if ui.button("Mesh linear unterteilen").clicked() {
                                if let Some(id) = self.selected.clone() {
                                    self.execute(
                                        "Mesh unterteilen",
                                        vec![Command::Subdivide { id }],
                                    );
                                }
                            }
                        });
                        ui.add_space(20.);
                        ui.horizontal(|ui| {
                            if ui.button("Duplizieren").clicked() {
                                self.duplicate();
                            }
                            if ui.button("Entfernen").clicked() {
                                self.remove();
                            }
                        });
                    }
                });
            });
    }
    fn history(&mut self, ctx: &egui::Context) {
        egui::TopBottomPanel::bottom("history").default_height(175.).height_range(90.0..=400.0).resizable(true).show(ctx,|ui| {
            ui.horizontal(|ui|{ui.strong("Verlauf");ui.label(format!("{} Bearbeitungsgruppen",self.document.history.len()));
                if ui.add_enabled(self.document.can_undo(),egui::Button::new("Rückgängig")).clicked(){self.travel(false);}
                if ui.add_enabled(self.document.can_redo(),egui::Button::new("Wiederholen")).clicked(){self.travel(true);}
            });ui.separator();
            egui::ScrollArea::vertical().show(ui,|ui| {
                for entry in self.document.history.iter().rev() {
                    egui::CollapsingHeader::new(format!("r{}  {}  ·  {}",entry.revision,entry.label,entry.actor)).id_salt(&entry.id).show(ui,|ui| {
                        ui.label(entry.task_path.join("  /  "));ui.small(format!("{} · {} betroffene Objekte",entry.kind,entry.changes.len()));
                        for (index,command) in entry.commands.iter().enumerate() {
                            egui::CollapsingHeader::new(format!("{}. {}",index+1,command.label())).id_salt((&entry.id,index)).show(ui,|ui| {ui.monospace(serde_json::to_string_pretty(command).unwrap_or_default().chars().take(16000).collect::<String>());});
                        }
                        for change in &entry.changes {
                            let name=change.after.as_ref().or(change.before.as_ref()).map(|o|o.name.as_str()).unwrap_or("Objekt");
                            egui::CollapsingHeader::new(format!("Änderung: {name}")).id_salt((&entry.id,&change.object_id)).show(ui,|ui| {
                                for (label,object) in [("Vorher",&change.before),("Nachher",&change.after)] {
                                    if let Some(object)=object {ui.label(format!("{label}: {} · {} Punkte · {} Flächen",object.name,object.mesh.positions.len(),object.mesh.faces.len()));ui.monospace(format!("Position {:?}\nRotation {:?}\nSkalierung {:?}\nFarbe {:?} · Sichtbar {}",object.transform.translation,object.transform.rotation_degrees,object.transform.scale,object.color,object.visible));}
                                    else {ui.label(format!("{label}: nicht vorhanden"));}
                                }
                            });
                        }
                    });
                }
            });
        });
    }
    fn viewport(&mut self, ctx: &egui::Context) {
        egui::CentralPanel::default()
            .frame(egui::Frame::new())
            .show(ctx, |ui| {
                egui::Frame::new().inner_margin(8.).show(ui, |ui| {
                    ui.horizontal_wrapped(|ui| {
                        if ui
                            .selectable_label(self.mode == SelectionMode::Object, "Objekt")
                            .clicked()
                        {
                            self.set_mode(SelectionMode::Object);
                        }
                        if ui
                            .selectable_label(self.mode == SelectionMode::Face, "Fläche")
                            .clicked()
                        {
                            self.set_mode(SelectionMode::Face);
                        }
                        ui.separator();
                        if ui.button("Fokussieren").clicked() {
                            self.focus();
                        }
                        if ui.button("Front").clicked() {
                            self.camera.yaw = 0.;
                            self.camera.pitch = 0.;
                        }
                        if ui.button("Oben").clicked() {
                            self.camera.yaw = 0.;
                            self.camera.pitch = 1.5;
                        }
                        if ui.button("Perspektive").clicked() {
                            self.camera = Camera::default();
                        }
                        if ui
                            .selectable_label(self.mode == SelectionMode::Vertex, "Punkt")
                            .clicked()
                        {
                            self.set_mode(SelectionMode::Vertex);
                        }
                        if ui
                            .selectable_label(self.mode == SelectionMode::Edge, "Kante")
                            .clicked()
                        {
                            self.set_mode(SelectionMode::Edge);
                        }
                        ui.checkbox(&mut self.wireframe, "Kanten");
                    });
                });
                let size = ui.available_size();
                let (rect, response) = ui.allocate_exact_size(size, egui::Sense::click_and_drag());
                if response.dragged_by(egui::PointerButton::Secondary) {
                    let delta = response.drag_motion();
                    self.camera.orbit(delta.x, delta.y);
                }
                if response.dragged_by(egui::PointerButton::Middle) {
                    let delta = response.drag_motion();
                    self.camera.pan(delta.x, delta.y);
                }
                if response.hovered() {
                    self.camera
                        .zoom(ctx.input(|input| input.smooth_scroll_delta.y));
                }
                if response.clicked_by(egui::PointerButton::Primary) {
                    if let Some(pos) = response.interact_pointer_pos() {
                        let ndc = [
                            (pos.x - rect.left()) / rect.width() * 2. - 1.,
                            1. - (pos.y - rect.top()) / rect.height() * 2.,
                        ];
                        let hit = self.camera.pick(
                            &self.document.scene,
                            ndc,
                            rect.width() / rect.height().max(1.),
                        );
                        if matches!(self.mode, SelectionMode::Vertex | SelectionMode::Edge) {
                            let mode = if self.mode == SelectionMode::Vertex {
                                ElementMode::Vertex
                            } else {
                                ElementMode::Edge
                            };
                            let picked = selection::pick_element(
                                &self.document.scene,
                                &self.camera,
                                [pos.x - rect.left(), pos.y - rect.top()],
                                [rect.width(), rect.height()],
                                mode,
                                10.,
                            );
                            if let Some(picked) = picked {
                                self.selected = Some(picked.object_id);
                                self.face = None;
                                self.element = Some(picked.element);
                                self.edge_offset = [0.; 3];
                                self.refresh();
                            } else {
                                self.element = None;
                                self.point_draft = None;
                            }
                        } else {
                            match hit {
                                Some((id, face)) => self.select(
                                    Some(id),
                                    (self.mode == SelectionMode::Face).then_some(face),
                                ),
                                None => self.select(None, None),
                            }
                        }
                    }
                }
                let scale = ctx.pixels_per_point();
                let callback = renderer::Viewport::new(
                    &self.document.scene,
                    &self.camera,
                    self.selected.as_deref(),
                    renderer::ViewSelection {
                        face: self.face,
                        element: self.element,
                        element_mode: match self.mode {
                            SelectionMode::Vertex => Some(ElementMode::Vertex),
                            SelectionMode::Edge => Some(ElementMode::Edge),
                            _ => None,
                        },
                    },
                    self.wireframe,
                    self.brand.accent,
                    [
                        (rect.width() * scale).max(1.) as u32,
                        (rect.height() * scale).max(1.) as u32,
                    ],
                );
                ui.painter()
                    .add(eframe::egui_wgpu::Callback::new_paint_callback(
                        rect, callback,
                    ));
                let painter = ui.painter_at(rect);
                let muted = Color32::from_rgb(190, 199, 212);
                painter.text(
                    rect.left_top() + egui::vec2(18., 16.),
                    egui::Align2::LEFT_TOP,
                    self.mode.label(),
                    egui::FontId::proportional(13.),
                    muted,
                );
                painter.text(
                    rect.left_bottom() + egui::vec2(18., -18.),
                    egui::Align2::LEFT_BOTTOM,
                    "Rechts ziehen: drehen    Mitte ziehen: verschieben    Scrollen: zoomen",
                    egui::FontId::proportional(12.),
                    muted,
                );
                if self.brand.show_workspace_signature {
                    painter.text(
                        rect.right_top() + egui::vec2(-18., 16.),
                        egui::Align2::RIGHT_TOP,
                        &self.brand.workspace_signature,
                        egui::FontId::proportional(15.),
                        rgb(self.brand.accent),
                    );
                }
            });
    }
    fn dialogs(&mut self, ctx: &egui::Context) {
        if self.pending.is_some() {
            let mut decision = 0;
            let modal = egui::Modal::new(egui::Id::new("unsaved-changes")).show(ctx, |ui| {
                ui.heading("Ungespeicherte Änderungen");
                ui.label("Die Szene enthält ungespeicherte Änderungen.");
                ui.horizontal(|ui| {
                    if ui.button("Abbrechen").clicked() {
                        decision = 1;
                    }
                    if ui.button("Verwerfen und fortfahren").clicked() {
                        decision = 2;
                    }
                    if ui.button("Speichern und fortfahren").clicked() {
                        decision = 3;
                    }
                });
            });
            if modal.should_close() {
                decision = 1;
            }
            if decision == 1 {
                self.pending = None;
            }
            if decision == 2 || (decision == 3 && self.save(false)) {
                if let Some(pending) = self.pending.take() {
                    self.proceed(pending, ctx);
                }
            }
        }
        egui::Window::new("Über 3d-editor").open(&mut self.about).collapsible(false).show(ctx,|ui| {
            ui.heading(&self.brand.wordmark);ui.label("Version 0.1 · Eigenständiger Rust-3D-Editor");ui.label("Szenen, Polygon-Meshes, Transformationen und Flächenextrusion.");ui.label("Materialfarbe, OBJ-Geometrie, speicherbarer Verlauf und Headless-Befehle.");ui.separator();ui.label("Noch nicht enthalten: UVs, Rigging, Animation, Physik, CAD, Pluginhost oder verteilte Zusammenarbeit.");
        });
    }
}
impl eframe::App for Editor {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        if ctx.input(|input| input.viewport().close_requested()) && !self.allow_close && self.dirty
        {
            ctx.send_viewport_cmd(egui::ViewportCommand::CancelClose);
            self.pending = Some(Pending::Close);
        }
        self.shortcuts(ctx);
        self.header(ctx);
        egui::TopBottomPanel::bottom("status").show(ctx, |ui| {
            ui.horizontal_wrapped(|ui| {
                ui.label(&self.status);
                ui.separator();
                ui.small(format!(
                    "Revision {} · {} Objekte{}",
                    self.document.revision,
                    self.document.scene.objects.len(),
                    if self.dirty { " · Ungespeichert" } else { "" }
                ));
            });
        });
        if self.start {
            self.startup(ctx);
        } else {
            self.history(ctx);
            self.scene_tree(ctx);
            self.inspector(ctx);
            self.viewport(ctx);
        }
        self.dialogs(ctx);
    }
}
