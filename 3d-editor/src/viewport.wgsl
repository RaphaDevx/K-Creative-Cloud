struct Camera { matrix:mat4x4<f32>, eye:vec4<f32> };
@group(0) @binding(0) var<uniform> camera:Camera;
struct Varying {
    @builtin(position) position:vec4<f32>,
    @location(0) normal:vec3<f32>,
    @location(1) color:vec4<f32>,
    @location(2) world:vec3<f32>,
};
@vertex fn vs_mesh(@location(0) position:vec3<f32>,@location(1) normal:vec3<f32>,@location(2) color:vec4<f32>)->Varying {
    var out:Varying;
    out.position=camera.matrix*vec4<f32>(position,1.0);
    out.normal=normal;out.color=color;out.world=position;
    return out;
}
@fragment fn fs_mesh(in:Varying,@builtin(front_facing) front:bool)->@location(0) vec4<f32> {
    let n=select(-normalize(in.normal),normalize(in.normal),front);
    let light=normalize(vec3<f32>(-0.4,0.85,0.55));
    let view=normalize(camera.eye.xyz-in.world);
    let diffuse=max(dot(n,light),0.0);
    let rim=pow(1.0-max(dot(n,view),0.0),3.0)*0.10;
    let spec=pow(max(dot(n,normalize(light+view)),0.0),40.0)*0.10;
    let color=in.color.rgb*(0.30+0.70*diffuse)+vec3<f32>(rim+spec);
    return vec4<f32>(color,1.0);
}
@fragment fn fs_line(in:Varying)->@location(0) vec4<f32> {return in.color;}
