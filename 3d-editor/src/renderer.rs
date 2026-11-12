use crate::{
    camera::Camera,
    scene::Scene,
    selection::{Element, ElementMode},
};
use eframe::{
    egui,
    egui_wgpu::{self, wgpu},
};
use glam::Vec3;
use std::sync::Arc;
use wgpu::util::DeviceExt;

#[derive(Clone, Copy, bytemuck::Pod, bytemuck::Zeroable)]
#[repr(C)]
struct Vertex {
    position: [f32; 3],
    normal: [f32; 3],
    color: [f32; 4],
}
#[derive(Clone, Copy, bytemuck::Pod, bytemuck::Zeroable)]
#[repr(C)]
struct Uniform {
    matrix: [[f32; 4]; 4],
    eye: [f32; 4],
}

pub struct Viewport {
    vertices: Arc<[Vertex]>,
    lines: Arc<[Vertex]>,
    uniform: Uniform,
    size: [u32; 2],
}
#[derive(Clone, Copy, Default)]
pub struct ViewSelection {
    pub face: Option<usize>,
    pub element: Option<Element>,
    pub element_mode: Option<ElementMode>,
}
struct Targets {
    _color: wgpu::Texture,
    _depth: wgpu::Texture,
    color_view: wgpu::TextureView,
    depth_view: wgpu::TextureView,
    bind: wgpu::BindGroup,
    size: [u32; 2],
}
struct Resources {
    mesh: wgpu::RenderPipeline,
    line: wgpu::RenderPipeline,
    blit: wgpu::RenderPipeline,
    camera: wgpu::Buffer,
    camera_bind: wgpu::BindGroup,
    image_layout: wgpu::BindGroupLayout,
    sampler: wgpu::Sampler,
    format: wgpu::TextureFormat,
    targets: Option<Targets>,
}

pub fn install(state: &egui_wgpu::RenderState) {
    let device = &state.device;
    let shader = device.create_shader_module(wgpu::ShaderModuleDescriptor {
        label: Some("3d-editor scene"),
        source: wgpu::ShaderSource::Wgsl(include_str!("viewport.wgsl").into()),
    });
    let camera_layout = device.create_bind_group_layout(&wgpu::BindGroupLayoutDescriptor {
        label: Some("scene camera"),
        entries: &[wgpu::BindGroupLayoutEntry {
            binding: 0,
            visibility: wgpu::ShaderStages::VERTEX_FRAGMENT,
            ty: wgpu::BindingType::Buffer {
                ty: wgpu::BufferBindingType::Uniform,
                has_dynamic_offset: false,
                min_binding_size: None,
            },
            count: None,
        }],
    });
    let camera = device.create_buffer(&wgpu::BufferDescriptor {
        label: Some("camera uniform"),
        size: std::mem::size_of::<Uniform>() as u64,
        usage: wgpu::BufferUsages::UNIFORM | wgpu::BufferUsages::COPY_DST,
        mapped_at_creation: false,
    });
    let camera_bind = device.create_bind_group(&wgpu::BindGroupDescriptor {
        label: Some("camera"),
        layout: &camera_layout,
        entries: &[wgpu::BindGroupEntry {
            binding: 0,
            resource: camera.as_entire_binding(),
        }],
    });
    let layout = device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor {
        label: Some("scene layout"),
        bind_group_layouts: &[&camera_layout],
        push_constant_ranges: &[],
    });
    let pipeline = |lines: bool| {
        device.create_render_pipeline(&wgpu::RenderPipelineDescriptor {
            label: Some(if lines {
                "scene lines"
            } else {
                "scene polygons"
            }),
            layout: Some(&layout),
            vertex: wgpu::VertexState {
                module: &shader,
                entry_point: Some("vs_mesh"),
                buffers: &[wgpu::VertexBufferLayout {
                    array_stride: std::mem::size_of::<Vertex>() as u64,
                    step_mode: wgpu::VertexStepMode::Vertex,
                    attributes: &wgpu::vertex_attr_array![0=>Float32x3,1=>Float32x3,2=>Float32x4],
                }],
                compilation_options: Default::default(),
            },
            fragment: Some(wgpu::FragmentState {
                module: &shader,
                entry_point: Some(if lines { "fs_line" } else { "fs_mesh" }),
                targets: &[Some(state.target_format.into())],
                compilation_options: Default::default(),
            }),
            primitive: wgpu::PrimitiveState {
                topology: if lines {
                    wgpu::PrimitiveTopology::LineList
                } else {
                    wgpu::PrimitiveTopology::TriangleList
                },
                cull_mode: None,
                ..Default::default()
            },
            depth_stencil: Some(wgpu::DepthStencilState {
                format: wgpu::TextureFormat::Depth32Float,
                depth_write_enabled: !lines,
                depth_compare: wgpu::CompareFunction::LessEqual,
                stencil: Default::default(),
                bias: Default::default(),
            }),
            multisample: Default::default(),
            multiview: None,
            cache: None,
        })
    };
    let mesh = pipeline(false);
    let line = pipeline(true);
    let image_layout = device.create_bind_group_layout(&wgpu::BindGroupLayoutDescriptor {
        label: Some("viewport texture"),
        entries: &[
            wgpu::BindGroupLayoutEntry {
                binding: 0,
                visibility: wgpu::ShaderStages::FRAGMENT,
                ty: wgpu::BindingType::Texture {
                    sample_type: wgpu::TextureSampleType::Float { filterable: true },
                    view_dimension: wgpu::TextureViewDimension::D2,
                    multisampled: false,
                },
                count: None,
            },
            wgpu::BindGroupLayoutEntry {
                binding: 1,
                visibility: wgpu::ShaderStages::FRAGMENT,
                ty: wgpu::BindingType::Sampler(wgpu::SamplerBindingType::Filtering),
                count: None,
            },
        ],
    });
    let blit_layout = device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor {
        label: Some("viewport image layout"),
        bind_group_layouts: &[&image_layout],
        push_constant_ranges: &[],
    });
    let blit_shader = device.create_shader_module(wgpu::ShaderModuleDescriptor {
        label: Some("viewport presentation"),
        source: wgpu::ShaderSource::Wgsl(include_str!("present.wgsl").into()),
    });
    let blit = device.create_render_pipeline(&wgpu::RenderPipelineDescriptor {
        label: Some("viewport presentation"),
        layout: Some(&blit_layout),
        vertex: wgpu::VertexState {
            module: &blit_shader,
            entry_point: Some("vs_present"),
            buffers: &[],
            compilation_options: Default::default(),
        },
        fragment: Some(wgpu::FragmentState {
            module: &blit_shader,
            entry_point: Some("fs_present"),
            targets: &[Some(state.target_format.into())],
            compilation_options: Default::default(),
        }),
        primitive: Default::default(),
        depth_stencil: None,
        multisample: Default::default(),
        multiview: None,
        cache: None,
    });
    let sampler = device.create_sampler(&wgpu::SamplerDescriptor {
        label: Some("viewport sampler"),
        mag_filter: wgpu::FilterMode::Linear,
        min_filter: wgpu::FilterMode::Linear,
        ..Default::default()
    });
    state.renderer.write().callback_resources.insert(Resources {
        mesh,
        line,
        blit,
        camera,
        camera_bind,
        image_layout,
        sampler,
        format: state.target_format,
        targets: None,
    });
}

impl Viewport {
    pub fn new(
        scene: &Scene,
        camera: &Camera,
        selected: &[String],
        selection: ViewSelection,
        wireframe: bool,
        accent: [u8; 3],
        size: [u32; 2],
    ) -> Self {
        let mut vertices = Vec::new();
        let mut lines = Vec::new();
        let highlight = accent.map(|x| x as f32 / 255.);
        let projection = camera.matrix(size[0] as f32 / size[1].max(1) as f32);
        let mut line = |a: Vec3, b: Vec3, color: [f32; 3]| {
            let Some((a, b)) = crate::camera::clip_segment(a, b, projection) else {
                return;
            };
            for p in [a, b] {
                lines.push(Vertex {
                    position: p.to_array(),
                    normal: [0., 1., 0.],
                    color: [color[0], color[1], color[2], 1.],
                });
            }
        };
        for i in -40..=40 {
            let t = i as f32 * 0.5;
            let tone = if i % 4 == 0 { 0.19 } else { 0.125 };
            line(
                Vec3::new(t, 0., -20.),
                Vec3::new(t, 0., 20.),
                if i == 0 {
                    [0.26, 0.30, 0.35]
                } else {
                    [tone; 3]
                },
            );
            line(
                Vec3::new(-20., 0., t),
                Vec3::new(20., 0., t),
                if i == 0 {
                    [0.34, 0.25, 0.25]
                } else {
                    [tone; 3]
                },
            );
        }
        for object in scene.objects.iter().filter(|o| o.visible) {
            let matrix = object.transform.matrix();
            let chosen = selected.contains(&object.id);
            for (index, tri) in object.mesh.triangles() {
                let p = tri.map(|v| {
                    matrix.transform_point3(Vec3::from(object.mesh.positions[v as usize]))
                });
                let normal = (p[1] - p[0]).cross(p[2] - p[0]).normalize_or_zero();
                let color = if chosen && selection.face == Some(index) {
                    std::array::from_fn(|i| object.color[i] * 0.5 + highlight[i] * 0.5)
                } else {
                    object.color
                };
                for position in p {
                    vertices.push(Vertex {
                        position: position.to_array(),
                        normal: normal.to_array(),
                        color: [color[0], color[1], color[2], 1.],
                    });
                }
            }
            if chosen || wireframe {
                for (index, polygon) in object.mesh.faces.iter().enumerate() {
                    let n = matrix
                        .transform_vector3(object.mesh.normal(index))
                        .normalize_or_zero()
                        * 0.001;
                    for i in 0..polygon.len() {
                        let a = matrix.transform_point3(Vec3::from(
                            object.mesh.positions[polygon[i] as usize],
                        )) + n;
                        let b = matrix.transform_point3(Vec3::from(
                            object.mesh.positions[polygon[(i + 1) % polygon.len()] as usize],
                        )) + n;
                        line(
                            a,
                            b,
                            if chosen && selection.element_mode.is_none() {
                                highlight
                            } else {
                                [0.38; 3]
                            },
                        );
                    }
                }
            }
            if chosen {
                let forward = (camera.target - camera.eye()).normalize();
                let right = forward.cross(Vec3::Y).normalize();
                let up = right.cross(forward);
                if matches!(selection.element_mode, Some(ElementMode::Vertex)) {
                    for (index, point) in object.mesh.positions.iter().enumerate() {
                        let world = matrix.transform_point3(Vec3::from(*point));
                        let point = world + (camera.eye() - world).normalize() * 0.001;
                        let active = selection.element == Some(Element::Vertex(index));
                        let radius =
                            point.distance(camera.eye()) * if active { 0.006 } else { 0.003 };
                        let color = if active { highlight } else { [0.66; 3] };
                        line(point - right * radius, point + right * radius, color);
                        line(point - up * radius, point + up * radius, color);
                    }
                }
                if let Some(Element::Edge(edge)) = selection.element {
                    if let (Some(a), Some(b)) = (
                        object.mesh.positions.get(edge[0] as usize),
                        object.mesh.positions.get(edge[1] as usize),
                    ) {
                        let a = matrix.transform_point3(Vec3::from(*a));
                        let b = matrix.transform_point3(Vec3::from(*b));
                        let offset = (camera.eye() - (a + b) * 0.5).normalize() * 0.002;
                        for shift in [-1., 0., 1.] {
                            let shift = up * camera.distance * 0.0008 * shift;
                            line(a + offset + shift, b + offset + shift, highlight);
                        }
                    }
                }
            }
        }
        Self {
            vertices: vertices.into(),
            lines: lines.into(),
            uniform: Uniform {
                matrix: camera
                    .matrix(size[0] as f32 / size[1].max(1) as f32)
                    .to_cols_array_2d(),
                eye: camera.eye().extend(1.).to_array(),
            },
            size,
        }
    }
}

impl Resources {
    fn resize(&mut self, device: &wgpu::Device, size: [u32; 2]) {
        if self.targets.as_ref().is_some_and(|t| t.size == size) {
            return;
        }
        let create = |format, usage, label| {
            device.create_texture(&wgpu::TextureDescriptor {
                label: Some(label),
                size: wgpu::Extent3d {
                    width: size[0],
                    height: size[1],
                    depth_or_array_layers: 1,
                },
                mip_level_count: 1,
                sample_count: 1,
                dimension: wgpu::TextureDimension::D2,
                format,
                usage,
                view_formats: &[],
            })
        };
        let color = create(
            self.format,
            wgpu::TextureUsages::RENDER_ATTACHMENT | wgpu::TextureUsages::TEXTURE_BINDING,
            "3d color",
        );
        let depth = create(
            wgpu::TextureFormat::Depth32Float,
            wgpu::TextureUsages::RENDER_ATTACHMENT,
            "3d depth",
        );
        let color_view = color.create_view(&Default::default());
        let depth_view = depth.create_view(&Default::default());
        let bind = device.create_bind_group(&wgpu::BindGroupDescriptor {
            label: Some("3d viewport image"),
            layout: &self.image_layout,
            entries: &[
                wgpu::BindGroupEntry {
                    binding: 0,
                    resource: wgpu::BindingResource::TextureView(&color_view),
                },
                wgpu::BindGroupEntry {
                    binding: 1,
                    resource: wgpu::BindingResource::Sampler(&self.sampler),
                },
            ],
        });
        self.targets = Some(Targets {
            _color: color,
            _depth: depth,
            color_view,
            depth_view,
            bind,
            size,
        });
    }
}

impl egui_wgpu::CallbackTrait for Viewport {
    fn prepare(
        &self,
        device: &wgpu::Device,
        queue: &wgpu::Queue,
        _screen: &egui_wgpu::ScreenDescriptor,
        encoder: &mut wgpu::CommandEncoder,
        resources: &mut egui_wgpu::CallbackResources,
    ) -> Vec<wgpu::CommandBuffer> {
        let resources = resources
            .get_mut::<Resources>()
            .expect("viewport renderer installed");
        let max = device.limits().max_texture_dimension_2d;
        resources.resize(
            device,
            [self.size[0].clamp(1, max), self.size[1].clamp(1, max)],
        );
        queue.write_buffer(&resources.camera, 0, bytemuck::bytes_of(&self.uniform));
        let buffer = |vertices: &[Vertex], label| {
            let empty = Vertex::zeroed();
            device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
                label: Some(label),
                contents: if vertices.is_empty() {
                    bytemuck::bytes_of(&empty)
                } else {
                    bytemuck::cast_slice(vertices)
                },
                usage: wgpu::BufferUsages::VERTEX,
            })
        };
        let meshes = buffer(&self.vertices, "mesh vertices");
        let lines = buffer(&self.lines, "grid and selection edges");
        let targets = resources.targets.as_ref().unwrap();
        let mut pass = encoder.begin_render_pass(&wgpu::RenderPassDescriptor {
            label: Some("3d-editor viewport"),
            color_attachments: &[Some(wgpu::RenderPassColorAttachment {
                view: &targets.color_view,
                resolve_target: None,
                ops: wgpu::Operations {
                    load: wgpu::LoadOp::Clear(wgpu::Color {
                        r: 0.065,
                        g: 0.075,
                        b: 0.09,
                        a: 1.,
                    }),
                    store: wgpu::StoreOp::Store,
                },
            })],
            depth_stencil_attachment: Some(wgpu::RenderPassDepthStencilAttachment {
                view: &targets.depth_view,
                depth_ops: Some(wgpu::Operations {
                    load: wgpu::LoadOp::Clear(1.),
                    store: wgpu::StoreOp::Discard,
                }),
                stencil_ops: None,
            }),
            timestamp_writes: None,
            occlusion_query_set: None,
        });
        pass.set_bind_group(0, &resources.camera_bind, &[]);
        pass.set_pipeline(&resources.mesh);
        pass.set_vertex_buffer(0, meshes.slice(..));
        pass.draw(0..self.vertices.len() as u32, 0..1);
        pass.set_pipeline(&resources.line);
        pass.set_vertex_buffer(0, lines.slice(..));
        pass.draw(0..self.lines.len() as u32, 0..1);
        Vec::new()
    }
    fn paint(
        &self,
        _info: egui::PaintCallbackInfo,
        pass: &mut wgpu::RenderPass<'static>,
        resources: &egui_wgpu::CallbackResources,
    ) {
        let resources = resources.get::<Resources>().unwrap();
        pass.set_pipeline(&resources.blit);
        pass.set_bind_group(0, &resources.targets.as_ref().unwrap().bind, &[]);
        pass.draw(0..3, 0..1);
    }
}
use bytemuck::Zeroable;
