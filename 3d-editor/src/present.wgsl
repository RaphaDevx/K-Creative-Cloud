@group(0) @binding(0) var image:texture_2d<f32>;
@group(0) @binding(1) var image_sampler:sampler;
struct ImageVertex { @builtin(position) position:vec4<f32>, @location(0) uv:vec2<f32> };
@vertex fn vs_present(@builtin(vertex_index) index:u32)->ImageVertex {
    let p=vec2<f32>(f32((index<<1u)&2u),f32(index&2u));
    var out:ImageVertex;out.position=vec4<f32>(p*2.0-1.0,0.0,1.0);out.uv=vec2<f32>(p.x,1.0-p.y);return out;
}
@fragment fn fs_present(in:ImageVertex)->@location(0) vec4<f32> {return textureSample(image,image_sampler,in.uv);}
