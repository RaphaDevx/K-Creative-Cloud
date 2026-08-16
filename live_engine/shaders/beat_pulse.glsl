// K-Creative Beat Pulse — WebGL Fragment Shader
// Used as animated background in the live performance interface.
// Uniforms injected from JavaScript:
//   u_time      float  — elapsed time in seconds
//   u_beat      float  — 0.0→1.0 impulse on kick, decays over ~0.3s
//   u_bpm       float  — current BPM (default 128.0)
//   u_resolution vec2  — canvas size in pixels
//   u_xfader    float  — crossfader position (0=A, 1=B), affects hue shift

precision mediump float;

uniform float u_time;
uniform float u_beat;
uniform float u_bpm;
uniform vec2  u_resolution;
uniform float u_xfader;

// K-Creative palette
#define K_VIOLET  vec3(0.424, 0.278, 1.0)   // #6C47FF
#define K_PURPLE  vec3(0.659, 0.333, 0.969) // #A855F7
#define K_DARK    vec3(0.027, 0.024, 0.063) // #07060F
#define K_CYAN    vec3(0.376, 0.647, 0.98)  // #60A5FA

float hash(vec2 p) {
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453123);
}

float noise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    return mix(
        mix(hash(i), hash(i + vec2(1,0)), f.x),
        mix(hash(i + vec2(0,1)), hash(i + vec2(1,1)), f.x),
        f.y
    );
}

// Glowing point
float point_glow(vec2 uv, vec2 pos, float radius) {
    float d = length(uv - pos);
    return radius / (d * d + 0.001);
}

void main() {
    vec2 uv = (gl_FragCoord.xy - 0.5 * u_resolution) / min(u_resolution.x, u_resolution.y);

    float beat_phase = mod(u_time * u_bpm / 60.0, 1.0);   // 0→1 per beat
    float beat_pulse = u_beat * exp(-u_beat * 3.0);        // sharp attack, fast decay
    float t = u_time * 0.3;

    // ── Background gradient ─────────────────────────────────────
    vec3 bg = K_DARK;

    // Slow breathing glow in center
    float breath = 0.5 + 0.5 * sin(t * 0.7);
    float center_glow = exp(-length(uv) * (2.5 - breath));
    bg += K_VIOLET * center_glow * (0.08 + beat_pulse * 0.3);

    // ── Particle field ─────────────────────────────────────────
    vec3 particles = vec3(0.0);
    const int N = 24;
    for (int i = 0; i < N; i++) {
        float fi = float(i) / float(N);

        // Orbit radius varies with beat
        float orbit = 0.25 + fi * 0.5 + beat_pulse * 0.1;

        // Each particle has its own angular speed and phase offset
        float speed    = 0.15 + fi * 0.08;
        float angle    = t * speed + fi * 6.283185 + beat_pulse * 0.5;
        float wobble   = noise(vec2(fi * 5.3, t * 0.4)) * 0.08;

        vec2 pos = vec2(cos(angle), sin(angle) * 0.6) * (orbit + wobble);

        // Particle glow size pulses with beat
        float size = (0.002 + fi * 0.001) * (1.0 + beat_pulse * 2.0);
        float glow = point_glow(uv, pos, size);
        glow = clamp(glow, 0.0, 0.8);

        // Color: alternate K-Violet and K-Purple, shift with xfader
        vec3 col = mix(K_VIOLET, K_PURPLE, fi + u_xfader * 0.3);
        col = mix(col, K_CYAN, beat_pulse * 0.4 * (fi > 0.5 ? 1.0 : 0.0));

        particles += col * glow * (0.6 + 0.4 * sin(fi * 12.566 + t));
    }

    // ── Spectrum bars (bottom, simulate spectrum) ────────────────
    float bar_y  = uv.y + 0.48;          // bottom strip
    vec3 spectrum = vec3(0.0);
    if (bar_y > 0.0 && bar_y < 0.06) {
        float bar_x = uv.x * 0.5 + 0.5; // 0→1 left to right
        int bin = int(bar_x * 32.0);
        float bin_f = float(bin) / 32.0;

        // Synthetic spectrum from noise + beat
        float level = noise(vec2(bin_f * 4.0, t * 2.0 + bin_f));
        level = pow(level, 1.5) * (0.6 + beat_pulse * 0.5);
        level += (1.0 - abs(bin_f - 0.15) * 8.0) * beat_pulse; // kick bump at low freq

        float bar_h = level * 0.055;
        if (bar_y < bar_h) {
            float brightness = 1.0 - bar_y / bar_h;
            vec3 bar_col = mix(K_VIOLET, K_CYAN, bin_f);
            spectrum = bar_col * brightness * (0.7 + beat_pulse * 0.5);
        }
    }

    // ── Scanline effect (subtle, retro CRT feel) ─────────────────
    float scanline = 0.97 + 0.03 * sin(gl_FragCoord.y * 2.0);

    // ── Compose ──────────────────────────────────────────────────
    vec3 col = bg + particles + spectrum;

    // Beat flash: brief white/violet bloom on kick
    col += K_VIOLET * beat_pulse * 0.15;

    // Vignette
    float vig = 1.0 - dot(uv * 0.7, uv * 0.7);
    col *= clamp(vig, 0.2, 1.0);

    col *= scanline;
    col = clamp(col, 0.0, 1.0);

    // Gamma
    col = pow(col, vec3(0.9));

    gl_FragColor = vec4(col, 1.0);
}
