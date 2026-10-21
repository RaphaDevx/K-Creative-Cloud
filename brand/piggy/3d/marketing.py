"""
Piggy 3D-Maskottchen — Marketing-Clips (Zusatzschicht, build_piggy.py bleibt unberührt).

Aufruf (headless, im fertigen Modell):
  blender -b brand/piggy/dist/3d/piggy.blend -P brand/piggy/3d/marketing.py -- \
      --action hop --format 9x16 --size 1080 --samples 64 --fps 24 --out /tmp/clips
  blender -b ... -P marketing.py -- --list [--json]
  blender -b ... -P marketing.py -- --format icon --still --out /tmp/clips   # icon-1024.png

Optionen:
  --action <name>       hop | wave | cheer_jump | coin_drop | turntable | talk_loop | idle   (siehe --list)
  --format 9x16|1x1|16x9|icon
  --size <px Breite>    Standard 1080 (16x9: 1920); icon ist immer 1024
  --samples N           Cycles-Samples (Standard 64)
  --fps 24|30           30 fps tastet dieselbe Animation (24-fps-Zeit) mit Zwischenbildern ab
  --frames a-b          Teilbereich der Ausgabe-Frames; auch Liste "1,13,20-22"
  --alpha               transparenter Hintergrund (RGBA); sonst voller Hintergrund aus --bg
  --bg <hex|brand|pfad> Hintergrund: Token-Pfad in piggy.resolved.json (brand, canvas, appIcon.bgFrom,
                        primitive.color.pink.100 ...) oder ein #hex als CLI-Argument
  --expr <name>         statischer Ausdruck (neutral|happy|surprised|sad|wink) statt Clip-Ausdruck
  --visemes <json>      Lip-Sync-Liste [{t_start,t_end,viseme}] -> Mund-Shape-Keys
  --still               ein Frame (Poster); bei icon: <out>/icon-1024.png
  --out <dir>           Ausgabe: <out>/<action>/frame_####.png + meta.json

Die Aktionen werden zur Laufzeit als echte Keyframe-Actions (mk_<name>) gebaut und NICHT in piggy.blend
zurückgespeichert. Alle Farben kommen aus den aufgelösten Tokens; Hex nur als CLI-Argument.

Engine: Cycles CPU. EEVEE läuft headless nur über Software-EGL, ist dort langsamer als Cycles und kennt den
Shadow Catcher nicht (grauer Boden statt Kontaktschatten) -> bewusst nicht verwendet.
"""
import bpy, sys, os, json, math, time, argparse, ast, traceback
from mathutils import Vector, Quaternion, Euler

HERE = os.path.dirname(os.path.abspath(__file__))
FPS_BASE = 24  # Animationen sind in 24-fps-Frames gebaut
EXPR_KEYS = ("mouth", "tongue", "brow.L", "brow.R", "eye.L", "eye.R")


# ----------------------------------------------------------------- Hilfen: Easing + Kurven
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def lin_(u):
    return u


def smooth(u):
    return u * u * (3 - 2 * u)


def in_quad(u):
    return u * u


def out_quad(u):
    return 1 - (1 - u) ** 2


def out_back(u, s=1.9):
    """Überschwingen (Overshoot) und Einpendeln."""
    return 1 + (s + 1) * (u - 1) ** 3 + s * (u - 1) ** 2


def K(f, keys):
    """Wert zur Zeit f aus Schlüsselliste [(t, wert[, easing])]; Easing gehört zum Segment VOR dem Schlüssel."""
    if f <= keys[0][0]:
        return keys[0][1]
    for a, b in zip(keys, keys[1:]):
        if f <= b[0]:
            e = b[2] if len(b) > 2 else smooth
            u = (f - a[0]) / (b[0] - a[0])
            return a[1] + (b[1] - a[1]) * e(u)
    return keys[-1][1]


def pulse(f, c, half=2.0):
    """Dreieckspuls (Blinzeln) um Frame c."""
    return clamp(1 - abs(f - c) / half)


def arc(f, f0, f1, h):
    """Wurfparabel: 0 ausserhalb [f0,f1], Scheitel h in der Mitte."""
    if f < f0 or f > f1:
        return 0.0
    u = (f - f0) / (f1 - f0)
    return h * 4 * u * (1 - u)


# ----------------------------------------------------------------- Posen/Ausdrücke aus build_piggy.py lesen
def literal_from_build(name):
    """Liest POSES/EXPRESSIONS per ast aus build_piggy.py (kein Import: das Skript würde alles neu bauen)."""
    src = open(os.path.join(HERE, "build_piggy.py"), encoding="utf-8").read()
    for node in ast.parse(src).body:
        if isinstance(node, ast.Assign) and any(getattr(t, "id", None) == name for t in node.targets):
            return ast.literal_eval(node.value)
    raise RuntimeError("%s nicht in build_piggy.py gefunden" % name)


EXPRESSIONS = literal_from_build("EXPRESSIONS")
POSES = literal_from_build("POSES")


# ----------------------------------------------------------------- Zustand pro Frame
class St:
    """Ein Frame der Figur in Welt-Achsen (Grad bzw. Meter). Vor dem Keyen entstehen Ohren/Schwanz per Nachschwingen."""

    def __init__(s):
        s.root = [0.0, 0.0, 0.0]
        s.yaw = 0.0
        s.sq = 1.0  # Squash&Stretch auf Z, Volumen erhalten (X/Y = 1/sqrt)
        s.body = [0.0, 0.0, 0.0]
        s.head = [0.0, 0.0, 0.0]
        s.ear = {"L": [0.0, 0.0], "R": [0.0, 0.0]}
        s.arm = {"L": dict(rx=0.0, ry=-8.0, aim=None, w=0.0), "R": dict(rx=0.0, ry=8.0, aim=None, w=0.0)}
        s.leg = {"L": [0.0, 0.0], "R": [0.0, 0.0]}
        s.tail = [0.0, 0.0, 0.0]
        s.coin = None  # None = versteckt, sonst dict(z, y, rz)
        s.shape = {}  # (objekt, key) -> Wert


def mouth(st, open=0.0, O=0.0, frown=0.0, smirk=0.0):
    for k, v in (("open", open), ("O", O), ("frown", frown), ("smirk", smirk)):
        if v:
            st.shape[("mouth", k)] = v
    if open:
        st.shape[("tongue", "open")] = open
    if O:
        st.shape[("tongue", "O")] = O


def brows(st, up=0.0, happy=0.0, sad=0.0):
    for s in ("L", "R"):
        for k, v in (("up", up), ("happy", happy), ("sad", sad)):
            if v:
                st.shape[("brow." + s, k)] = v


def eyes(st, closed=0.0, wide=0.0, sad=0.0):
    for s in ("L", "R"):
        for k, v in (("closed", closed), ("wide", wide), ("sad", sad)):
            if v:
                st.shape[("eye." + s, k)] = v


# ----------------------------------------------------------------- Clips
AIM_L = Vector((0.82, -0.42, 0.42))  # Jubel-Arme wie POSES["cheer"]
AIM_R = Vector((-0.82, -0.42, 0.42))


def clip_hop(n=24):
    """Hüpfer: Anticipation (Ducken, Arme zurück) -> Absprung-Stretch -> Flug -> Landung-Squash -> Overshoot."""
    sq_k = [(1, 1.0), (5, 0.80), (6.6, 1.15, out_quad), (10, 1.05), (12, 0.99), (15, 1.07), (17, 1.10),
            (18.5, 0.76), (21, 1.06), (23, 0.985), (24, 1.0)]
    pitch_k = [(1, 0), (5, 6), (7.5, -7), (12, -2), (16, 4), (18.5, 10), (21, -3), (24, 0)]
    aim_k = [(1, 0), (7, 0), (10.5, 1.12, out_quad), (12, 1.0), (16, 1.0), (18, 0.5), (19.5, -0.12), (22, 0.06), (24, 0)]
    arm_back = [(1, 0), (5, 26), (7.5, 8), (9, 0)]
    leg_k = [(1, 0), (6, 0), (8, -14), (12, -22), (16, -8), (17.5, 0)]
    S = []
    for f in range(1, n + 1):
        st = St()
        st.sq = K(f, sq_k)
        st.root[2] = arc(f, 7, 17, 0.6)
        st.body[0] = K(f, pitch_k)
        st.head[0] = -0.7 * K(f - 2, pitch_k) + 4 * K(f, [(1, 0), (5, 1), (6, 0), (18, 0), (19, 1), (21, 0)])
        for side, aim in (("L", AIM_L), ("R", AIM_R)):
            a = st.arm[side]
            a["rx"] = K(f, arm_back)
            a["aim"], a["w"] = aim * 0.85, K(f, aim_k)
        st.leg["L"] = [K(f, leg_k), -4 * K(f, leg_k) / 22]
        st.leg["R"] = [K(f, leg_k), 4 * K(f, leg_k) / 22]
        st.tail[2] = 14 * math.sin(f * 0.9) * K(f, [(6, 0), (9, 1), (19, 1), (23, 0)])
        mo = K(f, [(1, 0), (7, 0), (9, 0.9), (16, 0.9), (19, 0.5), (24, 0.25)])
        mouth(st, open=mo)
        brows(st, happy=mo)
        eyes(st, closed=pulse(f, 22.5))
        S.append(st)
    return S


def clip_wave(n=48):
    """Winken mit dem rechten Arm (arm.R): leichtes Ducken, Arm schwingt mit Overshoot hoch, 3 Wellen, weich zurück."""
    sq_k = [(1, 1.0), (6, 0.955), (10, 1.03, out_quad), (14, 1.0), (38, 1.0), (41, 0.985), (44, 1.01), (48, 1.0)]
    raise_k = [(1, 0), (7, 0), (14, 1.0, out_back), (38, 1.0), (45, 0, smooth), (48, 0)]
    env_k = [(14, 0), (17, 1), (33, 0.9), (40, 0)]
    S = []
    for f in range(1, n + 1):
        st = St()
        st.sq = K(f, sq_k)
        st.body[1] = K(f, [(1, 0), (9, -3), (14, 2.5), (38, 2.0), (46, -0.5), (48, 0)])  # Gewichtsverlagerung
        st.body[2] = K(f, [(1, 0), (12, 34, out_back), (38, 34), (46, 0)])  # Körper dreht die Winkehand (arm.R) zur Kamera
        st.head[1] = K(f, [(1, 0), (9, 0), (16, -10, out_back), (38, -9), (45, 0.5), (48, 0)])  # Kopf neigt
        st.head[2] = K(f, [(1, 0), (12, -26, out_back), (38, -26), (46, 0)])  # Kopf dreht gegen und schaut zur Kamera
        st.head[0] = K(f, [(1, 0), (6, 4), (12, -4), (38, -3), (46, 0)])
        phi = 2 * math.pi * (f - 14) / 8.0 + 0.6
        env = K(f, env_k)
        a = st.arm["R"]
        d = Vector((-0.80 + 0.06 * math.cos(phi) * env, -0.45, 0.50 + 0.30 * math.sin(phi) * env))
        d.rotate(Euler((0, 0, -math.radians(st.body[2]))))  # Körperdrehung herausrechnen: Zielrichtung in Weltachsen
        a["aim"], a["w"] = d, K(f, raise_k)
        a["rx"] = K(f, [(1, 0), (6, 18), (10, 0)])  # Arm holt kurz aus
        st.arm["L"]["ry"] = -8 - 3 * K(f, [(1, 0), (14, 1), (38, 1), (46, 0)]) * math.sin(phi * 0.5)
        st.tail[2] = 16 * math.sin(f * 0.55) * K(f, [(1, 0.2), (14, 1), (40, 0.4), (48, 0.2)])
        mo = K(f, [(1, 0), (5, 0), (11, 0.4), (40, 0.4), (47, 0.05)])
        mouth(st, open=mo)
        brows(st, happy=K(f, [(1, 0), (8, 1.0), (42, 1.0), (48, 0.2)]))
        eyes(st, closed=0.55 * K(f, [(12, 0), (16, 1), (24, 1), (28, 0)]) + pulse(f, 33.5))
        S.append(st)
    return S


def clip_cheer_jump(n=36):
    """Jubelsprung: tiefes Ducken, kräftiger Stretch, V-Arme, Beine gespreizt, Landung mit Squash und Nachwippen."""
    sq_k = [(1, 1.0), (7, 0.73), (9.4, 1.20, out_quad), (12, 1.10), (16, 1.0), (20, 1.05), (23, 1.12), (25, 0.72),
            (28, 1.07), (31, 0.985), (34, 1.0), (36, 1.0)]
    pitch_k = [(1, 0), (7, 8), (10, -9), (16, -10), (21, -2), (25, 10), (28, -3), (32, 0)]
    aim_k = [(1, 0), (6, 0), (11, 1.10, out_back), (16, 1.0), (23, 1.0), (25, 0.35), (27, -0.12), (30, 0.1), (34, 0.0)]
    leg_k = [(1, 0), (8, 0), (12, 1.0), (21, 1.0), (24, 0.0)]
    S = []
    for f in range(1, n + 1):
        st = St()
        st.sq = K(f, sq_k)
        st.root[2] = arc(f, 9, 23, 0.95)
        st.body[0] = K(f, pitch_k)
        st.head[0] = -0.8 * K(f - 2, pitch_k) - 10 * K(f, [(8, 0), (13, 1), (21, 1), (25, 0)])
        st.head[1] = 4 * math.sin(f * 0.45) * K(f, [(10, 0), (13, 1), (24, 1), (30, 0)])
        for side, aim in (("L", AIM_L), ("R", AIM_R)):
            a = st.arm[side]
            a["rx"] = K(f, [(1, 0), (6, 30), (9, 0)])
            a["aim"], a["w"] = aim, K(f, aim_k)
        lk = K(f, leg_k)
        st.leg["L"] = [-25 * lk, -12 * lk]
        st.leg["R"] = [20 * lk, 12 * lk]
        st.tail[2] = 22 * math.sin(f * 0.8) * K(f, [(8, 0), (12, 1), (30, 0.4), (36, 0)])
        mo = K(f, [(1, 0), (8, 0), (10, 1.0), (24, 1.0), (30, 0.55), (36, 0.3)])
        mouth(st, open=mo)
        brows(st, happy=K(f, [(1, 0), (8, 1), (32, 1), (36, 0.5)]))
        eyes(st, closed=0.9 * K(f, [(10, 0), (13, 1), (22, 1), (26, 0)]) + pulse(f, 32.5))
        S.append(st)
    return S


SLOT_Z, COIN_Z0 = 2.34, 3.4  # Münzmitte beim Eintauchen in den Schlitz / Starthöhe


def clip_coin_drop(n=72):
    """Münze fällt (drehend) in den Schlitz; Schwein schaut hoch, reagiert mit Wackeln/Staunen, dann Freude."""
    S = []
    for f in range(1, n + 1):
        st = St()
        # --- Münze: Fall mit Beschleunigung, Drehung um die Hochachse läuft in Schlitzrichtung aus
        if f <= 24:
            u = (f - 1) / 24.0
            z = COIN_Z0 - 1.55 * u * u
            rz = -35 + 720 * (1 - out_quad(u))
            st.coin = dict(z=z, y=-0.2, rz=rz)
        # --- Schwein
        look = K(f, [(1, 0), (9, 1), (22, 1), (25, 0)])  # schaut der Münze nach
        imp = max(0.0, f - 24)  # Zeit seit dem Einwurf
        shake = math.exp(-imp / 9.0) * math.sin(2 * math.pi * imp / 4.2) if f >= 24 else 0.0
        st.sq = (1.03 * look + (1 - look)) * 1.0
        st.sq *= K(f, [(1, 1), (24, 1), (27.5, 0.84), (31, 1.06), (34, 0.99), (36, 1.0)])
        st.head[0] = -15 * look + 12 * K(f, [(24, 0), (28, 1), (34, 0)])
        st.body[2] = 11 * shake
        st.head[1] = -7 * shake
        st.head[2] = 5 * math.sin(2 * math.pi * imp / 4.2 + 1.0) * math.exp(-imp / 10.0) if f >= 24 else 0.0
        st.body[1] = 3 * shake
        st.ear["L"][0] = -10 * look
        st.ear["R"][0] = -10 * look
        # Freudenhüpfer (zwei kleine Sprünge)
        st.root[2] = arc(f, 46, 54, 0.2) + arc(f, 56, 63, 0.13)
        st.sq *= K(f, [(44, 1), (46, 0.88), (47.5, 1.07, out_quad), (54, 1.04), (55, 0.9), (56.5, 1.06), (63, 1.03),
                       (64.5, 0.93), (67, 1.02), (70, 1.0)])
        joy = K(f, [(40, 0), (47, 1), (66, 1), (72, 0.7)])
        for side, aim in (("L", AIM_L), ("R", AIM_R)):
            a = st.arm[side]
            a["aim"], a["w"] = aim, 0.75 * K(f, [(42, 0), (48, 1.1, out_back), (62, 1.0), (68, 0.0)])
        # Ausdruck: Staunen (Augen weit, O-Mund, Brauen hoch) -> Freude
        stau = K(f, [(3, 0), (9, 0.6), (22, 0.6), (26, 1.0), (38, 1.0), (45, 0.0)])
        mouth(st, O=stau * (1 if f < 44 else 0) * (1 - K(f, [(38, 0), (44, 1)])), open=joy)
        brows(st, up=stau, happy=joy)
        eyes(st, wide=stau * (1 - K(f, [(38, 0), (44, 1)])), closed=0.85 * K(f, [(48, 0), (52, 1), (66, 1), (71, 0.2)]))
        st.tail[2] = 20 * math.sin(f * 0.85) * K(f, [(26, 0), (30, 1), (40, 0.4), (48, 1), (68, 0.3)])
        S.append(st)
    return S


def clip_turntable(n=72):
    """Kamera-Umlauf 360° (siehe Orbit-Leer-Objekt); Figur atmet im 36-Frame-Takt, damit der Loop nahtlos ist."""
    S = []
    for f in range(1, n + 1):
        ph = 2 * math.pi * (f - 1) / 36.0  # zwei volle Zyklen auf 72 Frames
        st = St()
        st.sq = 1 + 0.018 * math.sin(2 * ph)
        st.body[1] = 3.0 * math.sin(ph)
        st.head[1] = -3.5 * math.sin(ph - 0.5)
        st.head[0] = 1.6 * math.sin(2 * ph)
        for side, sg in (("L", 1), ("R", -1)):
            st.ear[side][0] = 5.0 * math.sin(2 * ph - 0.9 * sg)
            st.arm[side]["ry"] = -sg * (8 + 4 * math.sin(2 * ph + 0.6))
        st.tail[2] = 16 * math.sin(2 * ph)
        mouth(st, open=0.3)
        brows(st, happy=0.5)
        eyes(st, closed=pulse(f, 31.5))
        S.append(st)
    return S


def clip_talk_loop(n=48):
    """Sprechen: Kopf/Ohren leicht in Beat-Takt; der Mund bleibt frei für --visemes (Lip-Sync)."""
    S = []
    for f in range(1, n + 1):
        th = 2 * math.pi * (f - 1) / n
        st = St()
        st.sq = 1 + 0.012 * math.sin(2 * th)
        st.head[0] = 2.6 * math.sin(4 * th) + 1.4 * math.sin(6 * th + 1.0)
        st.head[1] = 3.0 * math.sin(2 * th)
        st.head[2] = 4.0 * math.sin(2 * th + 0.5) + 1.5 * math.sin(3 * th)
        st.body[1] = 1.5 * math.sin(2 * th - 0.4)
        for side, sg in (("L", 1), ("R", -1)):
            st.ear[side][0] = 3.0 * math.sin(4 * th - 0.8 * sg)
            st.arm[side]["ry"] = -sg * (8 + 3 * math.sin(4 * th + 0.4 * sg))
        st.tail[2] = 9 * math.sin(2 * th)
        brows(st, up=0.45 * max(0.0, math.sin(4 * th + 0.5)), happy=0.35)
        eyes(st, closed=pulse((f - 1) % n + 1, 21.5))
        S.append(st)
    return S


# Kamera-Rahmen je Clip: (Zielhöhe z, benötigte Breite, benötigte Höhe) in Weltmetern
CLIPS = {
    "hop":        dict(n=24, loop=False, poster=12, frame=(1.55, 2.6, 3.2), build=clip_hop,
                       desc="Hüpfer mit Anticipation, Squash&Stretch und Landung"),
    "wave":       dict(n=48, loop=False, poster=24, frame=(1.3, 2.7, 2.7), build=clip_wave,
                       desc="rechter Arm winkt, Kopf neigt, Lächeln"),
    "cheer_jump": dict(n=36, loop=False, poster=16, frame=(1.8, 3.1, 3.8), build=clip_cheer_jump,
                       desc="Jubelsprung mit Landung"),
    "coin_drop":  dict(n=72, loop=False, poster=30, frame=(1.85, 2.7, 3.9), build=clip_coin_drop,
                       desc="Münze fällt in den Schlitz, Staunen, dann Freude"),
    "turntable":  dict(n=72, loop=True, poster=1, frame=(1.3, 2.4, 2.8), build=clip_turntable, orbit=True,
                       desc="Kamera umkreist die Figur 360°, nahtlos loopbar"),
    "talk_loop":  dict(n=48, loop=True, poster=12, frame=(1.35, 2.2, 2.6), build=clip_talk_loop,
                       desc="Sprechbewegung für Lip-Sync (Mund frei)"),
    "idle":       dict(n=48, loop=True, poster=1, frame=(1.3, 2.4, 2.7), build=None, builtin="anim_idle",
                       desc="Wippen/Ohren/Blinzeln aus piggy.blend (anim_idle)"),
}


# ----------------------------------------------------------------- Szene
def objs():
    return {ob.name: ob for ob in bpy.data.objects}


def lin(hexstr):
    """sRGB-Hex -> linear RGBA (wie build_piggy.py)."""
    h = hexstr.lstrip("#")[:6]
    rgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple((c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4) for c in rgb) + (1.0,)


def resolve_bg(tokens, spec):
    """--bg: #hex (CLI-Argument) oder Token-Pfad; 'brand' = semantic.color.bg.brand."""
    if spec.startswith("#"):
        v = spec
    else:
        path = {"brand": "semantic.color.bg.brand"}.get(spec, spec)
        v = None
        for prefix in ("", "semantic.color.bg.", "component."):
            node = tokens
            try:
                for part in (prefix + path).strip(".").split("."):
                    node = node[part]
            except (KeyError, TypeError):
                continue
            if isinstance(node, str) and node.startswith("#"):
                v = node
                break
        if v is None:
            raise SystemExit("--bg: Token '%s' nicht in den Tokens gefunden (oder kein Hex-Wert)" % spec)
    h = v.lstrip("#")
    if len(h) not in (6, 8) or any(c not in "0123456789abcdefABCDEF" for c in h):
        raise SystemExit("--bg: ungültiger Hex-Wert '%s'" % v)
    return "#" + h[:6].upper()


def reset_animation(P):
    """Alle Animationsdaten, die Clips setzen, lösen (Blinzel-Aktionen bleiben in bpy.data erhalten)."""
    for ob in P.values():
        if ob.animation_data and ob.type != "LIGHT":
            ob.animation_data.action = None
        if ob.type == "MESH" and ob.data.shape_keys:
            sk = ob.data.shape_keys
            if sk.animation_data:
                sk.animation_data.action = None
            for kb in sk.key_blocks[1:]:
                kb.value = 0.0
    for a in [a for a in bpy.data.actions if a.name.startswith("mk_")]:
        a.user_clear()
        bpy.data.actions.remove(a)


def rest_basis(rig, bone):
    pb = rig.pose.bones[bone]
    return (rig.matrix_world @ pb.bone.matrix_local).to_3x3().normalized()


def rotq(rig, bone, rots):
    """Folge von (Weltachse, Grad) im Ruhezustand -> Bone-lokales Quaternion (wie rot_world in build_piggy.py)."""
    rest = rest_basis(rig, bone)
    q = Quaternion()
    for axis, deg in rots:
        qw = Quaternion(Vector(axis), math.radians(deg))
        q = (rest.inverted() @ qw.to_matrix() @ rest).to_quaternion() @ q
    return q


def aimq(rig, bone, vec):
    """Bone so drehen, dass seine Achse in Richtung vec zeigt (wie 'aim' in apply_pose)."""
    pb = rig.pose.bones[bone]
    rest = rest_basis(rig, bone)
    rest_dir = (pb.bone.tail_local - pb.bone.head_local).normalized()
    qw = rest_dir.rotation_difference(Vector(vec).normalized())
    return (rest.inverted() @ qw.to_matrix() @ rest).to_quaternion()


def blend_q(q0, q1, w):
    """Quaternion-Mischung mit Extrapolation (w<0 oder >1 erlaubt -> Overshoot der Arme)."""
    d = q0.inverted() @ q1
    if d.w < 0:
        d.negate()
    axis, ang = d.to_axis_angle()
    return q0 @ Quaternion(axis, ang * w)


def loc_scale(rig, bone, ws):
    """Welt-Skalierung (x,y,z) auf die lokalen Achsen des Knochens abbilden."""
    r = rest_basis(rig, bone)
    return tuple(sum(abs(r[j][i]) * ws[j] for j in range(3)) for i in range(3))


def reset_pose(rig):
    for pb in rig.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = Quaternion()
        pb.location = (0, 0, 0)
        pb.scale = (1, 1, 1)


def pose_from_state(rig, st):
    reset_pose(rig)
    pb = rig.pose.bones
    k = 1.0 / math.sqrt(max(st.sq, 1e-3))
    pb["root"].location = rest_basis(rig, "root").inverted() @ Vector(st.root)
    pb["root"].scale = loc_scale(rig, "root", (k, k, st.sq))
    pb["root"].rotation_quaternion = rotq(rig, "root", [((0, 0, 1), st.yaw)])
    xyz = ((1, 0, 0), (0, 1, 0), (0, 0, 1))
    pb["body"].rotation_quaternion = rotq(rig, "body", list(zip(xyz, st.body)))
    pb["head"].rotation_quaternion = rotq(rig, "head", list(zip(xyz, st.head)))
    for s in ("L", "R"):
        pb["ear." + s].rotation_quaternion = rotq(rig, "ear." + s, [(xyz[0], st.ear[s][0]), (xyz[1], st.ear[s][1])])
        pb["leg." + s].rotation_quaternion = rotq(rig, "leg." + s, [(xyz[0], st.leg[s][0]), (xyz[1], st.leg[s][1])])
        a = st.arm[s]
        q = rotq(rig, "arm." + s, [(xyz[0], a["rx"]), (xyz[1], a["ry"])])
        if a["aim"] is not None and abs(a["w"]) > 1e-4:
            q = blend_q(q, aimq(rig, "arm." + s, a["aim"]), a["w"])
        pb["arm." + s].rotation_quaternion = q
    pb["tail"].rotation_quaternion = rotq(rig, "tail", list(zip(xyz, st.tail)))
    if st.coin:
        pb["coin"].location = rest_basis(rig, "coin").inverted() @ Vector((0, st.coin["y"] + 0.12, st.coin["z"] - 2.52))
        pb["coin"].rotation_quaternion = rotq(rig, "coin", [((0, 0, 1), st.coin["rz"])])
    bpy.context.view_layer.update()


# ----------------------------------------------------------------- Nachschwingen (Follow-through)
def spring(sig, w, z, loop):
    """Gedämpfte Feder x'' = d - 2zw x' - w²x, getrieben vom Signal d; bei Loops eingeschwungen (3 Durchläufe)."""
    n = len(sig)
    seq = sig * 3 if loop else sig
    x = v = 0.0
    out = []
    sub = 4
    for d in seq:
        for _ in range(sub):
            v += (d - 2 * z * w * v - w * w * x) / sub
            x += v / sub
        out.append(x)
    return out[n:2 * n] if loop else out


def second_diff(vals, loop):
    n = len(vals)
    g = (lambda i: vals[i % n]) if loop else (lambda i: vals[min(max(i, 0), n - 1)])
    return [g(i + 1) - 2 * g(i) + g(i - 1) for i in range(n)]


def add_follow(S, loop):
    """Ohren und Schwanz schwingen der Kopf-/Körperbewegung träge nach (Trägheit gegen die Beschleunigung)."""
    head_h = [st.root[2] + 1.36 * st.sq for st in S]
    az = second_diff(head_h, loop)
    ap = second_diff([st.body[0] + st.head[0] for st in S], loop)
    ayaw = second_diff([st.body[2] for st in S], loop)
    ear_up = spring(az, 2 * math.pi / 8.5, 0.20, loop)
    ear_pitch = spring([0.015 * x for x in ap], 2 * math.pi / 8.5, 0.22, loop)
    ear_yaw = spring([0.015 * x for x in ayaw], 2 * math.pi / 8.5, 0.22, loop)
    tail_up = spring(az, 2 * math.pi / 6.5, 0.16, loop)
    tail_yaw = spring([0.02 * x for x in ayaw], 2 * math.pi / 6.5, 0.16, loop)
    for i, st in enumerate(S):
        for s, sg in (("L", 1), ("R", -1)):
            st.ear[s][0] = clamp(st.ear[s][0] + 90 * ear_pitch[i] - 25 * ear_yaw[i] * sg, -45, 45)
            st.ear[s][1] = clamp(st.ear[s][1] + sg * (230 * ear_up[i] + 60 * ear_yaw[i]), -45, 45)
        st.tail[0] = clamp(st.tail[0] - 260 * tail_up[i], -50, 50)
        st.tail[2] = clamp(st.tail[2] + 180 * tail_yaw[i], -60, 60)


# ----------------------------------------------------------------- Keyframes schreiben
def key_pose_frames(rig, S, name, tile_to=None, loop=False):
    rig.animation_data_create()
    act = bpy.data.actions.new("mk_" + name)
    rig.animation_data.action = act
    total = tile_to or len(S)
    seq = [S[i % len(S)] for i in range(total)] + ([S[0]] if loop else [])
    for i, st in enumerate(seq):
        pose_from_state(rig, st)
        for pb in rig.pose.bones:
            pb.keyframe_insert("rotation_quaternion", frame=i + 1)
            pb.keyframe_insert("location", frame=i + 1)
            pb.keyframe_insert("scale", frame=i + 1)
    return act, seq


def key_shapes(P, seq, name, skip=()):
    """Alle in irgendeinem Frame benutzten Shape Keys über alle Frames keyen (fehlend = 0)."""
    used = sorted({k for st in seq for k in st.shape if k[0] not in skip})
    for obname, key in used:
        kb = P[obname].data.shape_keys.key_blocks[key]
        for i, st in enumerate(seq):
            kb.value = st.shape.get((obname, key), 0.0)
            kb.keyframe_insert("value", frame=i + 1)
    for obname in {k[0] for k in used}:
        sk = P[obname].data.shape_keys
        if sk.animation_data and sk.animation_data.action:
            sk.animation_data.action.name = "mk_%s_%s" % (name, obname)


def key_coin(P, seq, name):
    """Münze nur bei coin_drop sichtbar: hide_render pro Frame keyen."""
    for n in ("coin", "coinRing"):
        ob = P[n]
        ob.animation_data_create()
        for i, st in enumerate(seq):
            ob.hide_render = st.coin is None
            ob.keyframe_insert("hide_render", frame=i + 1)
        ob.animation_data.action.name = "mk_%s_%s" % (name, n)


# ----------------------------------------------------------------- Lip-Sync
VISEMES = ("rest", "open", "O", "smile")
# Visem -> Shape-Key-Gewichte. smile = Basis-Form des Mundes (Lächeln), rest = leicht entspannt (kleines frown),
# open/O mit passender Zunge. smirk bleibt ungenutzt (asymmetrisch, nur für Ausdrücke sinnvoll).
VISEME_SHAPES = {
    "rest":  {("mouth", "frown"): 0.12},
    "open":  {("mouth", "open"): 0.9, ("tongue", "open"): 0.9},
    "O":     {("mouth", "O"): 1.0, ("tongue", "O"): 1.0},
    "smile": {},
}
MOUTH_KEYS = [("mouth", "open"), ("mouth", "O"), ("mouth", "frown"), ("tongue", "open"), ("tongue", "O")]


def load_visemes(path):
    data = json.load(open(path, encoding="utf-8"))
    items = data["visemes"] if isinstance(data, dict) else data
    out = []
    for i, it in enumerate(items):
        try:
            t0, t1, v = float(it["t_start"]), float(it["t_end"]), str(it["viseme"])
        except (KeyError, TypeError, ValueError):
            raise SystemExit("--visemes: Eintrag %d braucht t_start, t_end, viseme" % i)
        if v not in VISEMES:
            raise SystemExit("--visemes: Eintrag %d: unbekanntes Visem '%s' (erlaubt: %s)" % (i, v, ", ".join(VISEMES)))
        if t1 < t0 or t0 < 0:
            raise SystemExit("--visemes: Eintrag %d: ungültiger Zeitbereich" % i)
        out.append((t0, t1, v))
    return sorted(out)


def visemes_to_weights(visemes, fps, n_frames, smooth_ms=70.0, lead_ms=0.0):
    """Visem-Liste [(t_start,t_end,viseme)] -> pro Frame {(objekt,key): gewicht}.
    Treppenfunktion je Shape Key (spätere Einträge gewinnen, Lücken = rest), dann Hann-Glättung
    (smooth_ms, symmetrisch) für Übergänge ohne Zucken; lead_ms lässt den Mund dem Ton minimal voraus."""
    rate = 240.0
    total = n_frames / fps + 0.5
    m = int(total * rate) + 2
    base = VISEME_SHAPES["rest"]
    tracks = {k: [base.get(k, 0.0)] * m for k in MOUTH_KEYS}
    for t0, t1, v in visemes:
        a, b = max(0, int((t0 - lead_ms / 1000.0) * rate)), min(m, int((t1 - lead_ms / 1000.0) * rate))
        shape = VISEME_SHAPES[v]
        for k in MOUTH_KEYS:
            val = shape.get(k, 0.0)
            tr = tracks[k]
            for i in range(a, b):
                tr[i] = val
    w = max(1, int(smooth_ms / 1000.0 * rate)) | 1  # ungerade Fensterbreite
    win = [0.5 - 0.5 * math.cos(2 * math.pi * (i + 1) / (w + 1)) for i in range(w)]
    norm = sum(win)
    out = []
    for f in range(n_frames):
        c = int(round(f / fps * rate))
        row = {}
        for k in MOUTH_KEYS:
            tr = tracks[k]
            s = 0.0
            for j in range(w):
                idx = min(max(c + j - w // 2, 0), m - 1)
                s += tr[idx] * win[j]
            row[k] = s / norm
        out.append(row)
    return out


# ----------------------------------------------------------------- Kamera / Bühne
LIGHTS = ("Key", "Gloss", "Fill", "Rim", "Top")


def camera_angles(cam, target=Vector((0, 0, 1.3))):
    """Azimut/Elevation der Kamera aus piggy.blend lesen (3/4-Ansicht)."""
    v = cam.location - target
    return math.atan2(v.x, -v.y), math.asin(v.z / v.length)


def frame_camera(cam, az, el, zc, w_need, h_need, W, H):
    """85-mm-Kamera mit fester 3/4-Richtung so weit zurück, dass ein Rahmen w_need x h_need (m) um (0,0,zc) passt."""
    cam.data.sensor_fit = "HORIZONTAL"
    cam.data.sensor_width = 36
    d = max(w_need, h_need * W / H) * cam.data.lens / cam.data.sensor_width
    target = Vector((0, 0, zc))
    cam.location = target + Vector((math.sin(az) * d * math.cos(el), -math.cos(az) * d * math.cos(el), math.sin(el) * d))
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.view_layer.update()


def projected_bbox(cam, obs):
    """NDC-Bounding-Box (x0,x1,y0,y1) der ausgewerteten Meshes in Kamerasicht."""
    from bpy_extras.object_utils import world_to_camera_view
    dg = bpy.context.evaluated_depsgraph_get()
    scene = bpy.context.scene
    xs, ys = [], []
    for ob in obs:
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        for v in me.vertices:
            c = world_to_camera_view(scene, cam, ev.matrix_world @ v.co)
            xs.append(c.x)
            ys.append(c.y)
        ev.to_mesh_clear()
    return min(xs), max(xs), min(ys), max(ys)


def fit_icon_camera(cam, obs, fill=0.70):
    """Kopf-Close-up: Kamera so einstellen, dass die Figur (Box) mittig sitzt und ~fill der Seite einnimmt."""
    az, el = math.radians(12), math.radians(15)
    target = Vector((0, 0, 1.45))
    dist = 6.0
    cam.data.sensor_fit = "HORIZONTAL"
    cam.data.sensor_width = 36
    for _ in range(6):
        cam.location = target + Vector((math.sin(az) * dist * math.cos(el), -math.cos(az) * dist * math.cos(el), math.sin(el) * dist))
        cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
        bpy.context.view_layer.update()
        x0, x1, y0, y1 = projected_bbox(cam, obs)
        size = max(x1 - x0, y1 - y0)
        dist *= size / fill
        # Mittelpunkt der Box auf Bildmitte schieben (entlang Kamera-Rechts/Oben)
        view_w = dist * cam.data.sensor_width / cam.data.lens
        cx, cy = (x0 + x1) / 2 - 0.5, (y0 + y1) / 2 - 0.5
        right = cam.matrix_world.to_3x3() @ Vector((1, 0, 0))
        up = cam.matrix_world.to_3x3() @ Vector((0, 1, 0))
        target = target + right * cx * view_w + up * cy * view_w
    cam.location = target + Vector((math.sin(az) * dist * math.cos(el), -math.cos(az) * dist * math.cos(el), math.sin(el) * dist))
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
    bpy.context.view_layer.update()
    return projected_bbox(cam, obs)


def setup_orbit(P, cam, n):
    """Orbit-Leer-Objekt in der Figurmitte; Kamera + Lichter hängen daran (Studio-Drehteller-Look) und drehen 360°."""
    orbit = bpy.data.objects.new("MK_CamOrbit", None)
    bpy.context.scene.collection.objects.link(orbit)
    bpy.context.view_layer.update()
    for ob in [cam] + [P[l] for l in LIGHTS if l in P]:
        mw = ob.matrix_world.copy()
        ob.parent = orbit
        ob.matrix_parent_inverse = orbit.matrix_world.inverted()
        ob.matrix_world = mw
    orbit.animation_data_create()
    act = bpy.data.actions.new("mk_turntable_orbit")
    orbit.animation_data.action = act
    for f, ang in ((1, 0.0), (n + 1, 2 * math.pi)):  # Frame n+1 == Frame 1 (wird nicht gerendert)
        orbit.rotation_euler = (0, 0, ang)
        orbit.keyframe_insert("rotation_euler", index=2, frame=f)
    for fc in act.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"
    return orbit


def setup_render(scene, W, H, samples, fps, bg_hex, alpha, no_shadow=False):
    r = scene.render
    r.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = False
    scene.cycles.use_animated_seed = True
    r.use_persistent_data = True
    r.dither_intensity = 0.0  # exakte Token-Farbe, kein ±1-Rauschen
    r.resolution_x, r.resolution_y, r.resolution_percentage = W, H, 100
    r.fps, r.fps_base = fps, 1.0
    r.film_transparent = True
    r.image_settings.file_format = "PNG"
    r.image_settings.color_depth = "8"
    scene.view_settings.view_transform = "Standard"
    if alpha:
        r.image_settings.color_mode = "RGBA"
        scene.use_nodes = False
        return
    r.image_settings.color_mode = "RGB"
    # Voller Hintergrund per Compositor: Render (Alpha inkl. Schattenfänger) über Token-Farbe legen.
    scene.use_nodes = True
    nt = scene.node_tree
    nt.nodes.clear()
    rl = nt.nodes.new("CompositorNodeRLayers")
    conv = nt.nodes.new("CompositorNodePremulKey")
    conv.mapping = "PREMUL_TO_STRAIGHT"
    rgb = nt.nodes.new("CompositorNodeRGB")
    rgb.outputs[0].default_value = lin(bg_hex)
    over = nt.nodes.new("CompositorNodeAlphaOver")
    over.inputs[0].default_value = 1.0
    comp = nt.nodes.new("CompositorNodeComposite")
    comp.use_alpha = False
    nt.links.new(rl.outputs["Image"], conv.inputs[0])
    nt.links.new(rgb.outputs[0], over.inputs[1])
    nt.links.new(conv.outputs[0], over.inputs[2])
    nt.links.new(over.outputs[0], comp.inputs[0])


def render_frame(scene, path):
    scene.render.filepath = path
    t = time.perf_counter()
    bpy.ops.render.render(write_still=True)
    return time.perf_counter() - t


# ----------------------------------------------------------------- CLI
def parse_frames(spec, total):
    out = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            out += list(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    bad = [f for f in out if f < 1 or f > total]
    if bad:
        raise SystemExit("--frames: %s ausserhalb 1-%d" % (bad, total))
    return sorted(set(out))


def parse_args(argv):
    ap = argparse.ArgumentParser(prog="marketing.py")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--json", action="store_true", help="mit --list: maschinenlesbar")
    ap.add_argument("--action", default=None)
    ap.add_argument("--format", default="9x16", choices=["9x16", "1x1", "16x9", "icon"])
    ap.add_argument("--size", type=int, default=None)
    ap.add_argument("--samples", type=int, default=64)
    ap.add_argument("--fps", type=int, default=24, choices=[24, 30])
    ap.add_argument("--frames", default=None)
    ap.add_argument("--alpha", action="store_true")
    ap.add_argument("--bg", default=None)
    ap.add_argument("--expr", default=None, choices=sorted(EXPRESSIONS))
    ap.add_argument("--visemes", default=None)
    ap.add_argument("--still", action="store_true")
    ap.add_argument("--out", default=None)
    ap.add_argument("--tokens", default=os.path.join(HERE, "..", "dist", "tokens", "piggy.resolved.json"))
    return ap.parse_args(argv)


def print_list(as_json):
    rows = [dict(name=k, frames=c["n"], loop=c["loop"], poster=c["poster"], fps=FPS_BASE, description=c["desc"])
            for k, c in CLIPS.items()]
    if as_json:
        print("MK_LIST_JSON " + json.dumps(rows))
    else:
        print("Aktionen:")
        for r in rows:
            print("  %-11s %3d Frames @%d fps  %s  %s" % (r["name"], r["frames"], r["fps"],
                                                         "loop" if r["loop"] else "once", r["description"]))
        print("Formate: 9x16 1x1 16x9 icon (1024x1024, ohne Alpha, nur --still)")


def main(argv):
    a = parse_args(argv)
    if a.list:
        print_list(a.json)
        return
    if not a.out:
        raise SystemExit("--out fehlt")
    icon = a.format == "icon"
    if icon and a.alpha:
        raise SystemExit("--format icon rendert ohne Alpha; --alpha nicht möglich")
    action = a.action or ("idle" if icon else None)
    if action is None:
        raise SystemExit("--action fehlt (siehe --list)")
    if action not in CLIPS:
        raise SystemExit("unbekannte Aktion '%s' (siehe --list)" % action)
    clip = CLIPS[action]
    tokens = json.load(open(a.tokens, encoding="utf-8"))
    bg_spec = a.bg or ("component.appIcon.bgFrom" if icon else "brand")
    bg_hex = resolve_bg(tokens, bg_spec)

    P = objs()
    rig, cam = P["PiggyRig"], P["Cam"]
    scene = bpy.context.scene
    reset_animation(P)
    az, el = camera_angles(cam)

    # --- Format / Auflösung
    if icon:
        W = H = 1024
        if a.size and a.size != 1024:
            print("[marketing] --size wird für icon ignoriert (immer 1024)")
    else:
        W = a.size or (1920 if a.format == "16x9" else 1080)
        ratio = {"9x16": 16 / 9, "1x1": 1.0, "16x9": 9 / 16}[a.format]
        H = int(round(W * ratio / 2.0)) * 2
        W = W + (W % 2)

    # --- Clip bauen (zur Laufzeit, Aktionen mk_*; idempotent durch reset_animation)
    n24 = clip["n"]
    vis = load_visemes(a.visemes) if a.visemes else None
    if vis and action == "talk_loop":
        n24 = max(n24, int(math.ceil(max(v[1] for v in vis) * FPS_BASE)))
    static = icon and not a.action  # Icon ohne Clip: statische Pose
    seq = None
    if static:
        st = St()
        mouth(st, open=0.0)
        S = [st]
    elif clip.get("builtin"):
        rig.animation_data_create()
        rig.animation_data.action = bpy.data.actions[clip["builtin"]]
        for side in ("L", "R"):
            sk = P["eye." + side].data.shape_keys
            sk.animation_data_create()
            sk.animation_data.action = bpy.data.actions["blink_" + side]
        S = None
    else:
        S = clip["build"](clip["n"])
        add_follow(S, clip["loop"])

    for n_ in ("coin", "coinRing"):
        P[n_].hide_render = True
    if S is not None:
        if a.expr:
            for st in S:
                st.shape = {(o, k): v for o, ks in EXPRESSIONS[a.expr].items() for k, v in ks.items()}
        elif static:
            S[0].shape = {(o, k): v for o, ks in EXPRESSIONS["happy"].items() for k, v in ks.items()}
        if vis:
            for st in S:
                st.shape = {k: v for k, v in st.shape.items() if k[0] not in ("mouth", "tongue")}
        if static:
            pose_from_state(rig, S[0])
            for (o, k), v in S[0].shape.items():
                P[o].data.shape_keys.key_blocks[k].value = v
            seq = S
        else:
            act, seq = key_pose_frames(rig, S, action, tile_to=n24, loop=clip["loop"])
            if any(st.coin for st in seq):
                key_coin(P, seq, action)
            key_shapes(P, seq, action)
    if vis:
        wts = visemes_to_weights(vis, FPS_BASE, n24 + (1 if clip["loop"] else 0))
        vseq = []
        for w in wts:
            st = St()
            st.shape = dict(w)
            vseq.append(st)
        key_shapes(P, vseq, action + "_visemes")

    if clip.get("orbit"):
        setup_orbit(P, cam, n24)

    # Auflösung zuerst: die Icon-Kamera misst im NDC-Raum des Renderformats
    setup_render(scene, W, H, a.samples, a.fps, bg_hex, a.alpha)

    # --- Kamera
    ground = P["ShadowCatcher"]
    if icon:
        head_set = ("head", "ear.L", "ear.R", "earInner.L", "earInner.R", "snout")
        for nm in ("body", "belly", "arm.L", "arm.R", "hand.L", "hand.R", "leg.L", "leg.R", "hoof.L", "hoof.R", "tail"):
            P[nm].hide_render = True
        ground.hide_render = True
        bbox = fit_icon_camera(cam, [P[nm] for nm in head_set])
    else:
        zc, wn, hn = clip["frame"]
        frame_camera(cam, az, el, zc, wn, hn, W, H)
        bbox = None
        if clip.get("orbit"):  # Eltern-Transform nach neuer Platzierung nachziehen
            orbit = bpy.data.objects["MK_CamOrbit"]
            for ob in [cam] + [P[l] for l in LIGHTS]:
                mw = ob.matrix_world.copy()
                ob.matrix_parent_inverse = orbit.matrix_world.inverted()
                ob.matrix_world = mw


    # --- Ausgabe-Frames (bei 30 fps dichter abgetastet: gleiche Dauer)
    n_out = int(round(n24 * a.fps / FPS_BASE))
    scene.frame_start, scene.frame_end = 1, max(1, n_out)
    if a.still:
        sel = parse_frames(a.frames, n_out)[:1] if a.frames else [max(1, int(round((clip["poster"] - 1) * a.fps / FPS_BASE)) + 1)]
    else:
        sel = parse_frames(a.frames, n_out) if a.frames else list(range(1, n_out + 1))
    if icon or static:
        sel = [1]

    out_dir = os.path.abspath(a.out)
    if icon:
        os.makedirs(out_dir, exist_ok=True)
        targets = {1: os.path.join(out_dir, "icon-1024.png")}
        meta_path = os.path.join(out_dir, "icon-1024.meta.json")
    else:
        clip_dir = os.path.join(out_dir, action)
        os.makedirs(clip_dir, exist_ok=True)
        meta_path = os.path.join(clip_dir, "meta.json")
        if a.still:
            targets = {sel[0]: os.path.join(clip_dir, "poster.png")}
        else:
            targets = {i: os.path.join(clip_dir, "frame_%04d.png" % i) for i in sel}

    times = []
    for i in sel:
        t_act = 1 + (i - 1) * FPS_BASE / a.fps
        fl = int(math.floor(t_act + 1e-9))
        scene.frame_set(fl, subframe=max(0.0, t_act - fl))
        dt = render_frame(scene, targets[i])
        times.append(dt)
        print("[marketing] %s frame %d/%d  %.1f s" % (action, i, n_out, dt))

    meta = dict(
        action=action, format=a.format, size=[W, H], fps=a.fps, frames=n_out, rendered=sel,
        source_fps=FPS_BASE, source_frames=n24, loop=clip["loop"],
        engine="CYCLES", device="CPU", samples=a.samples, alpha=bool(a.alpha), background=None if a.alpha else bg_hex,
        bg_token=None if a.alpha else bg_spec, expr=a.expr, visemes=bool(vis), still=bool(a.still or icon),
        render_seconds_per_frame=[round(t, 3) for t in times],
        render_seconds_mean=round(sum(times) / len(times), 3) if times else None,
        blender=bpy.app.version_string, files=[os.path.basename(targets[i]) for i in sel],
    )
    if bbox:
        meta["figure_bbox_ndc"] = [round(v, 4) for v in bbox]
    json.dump(meta, open(meta_path, "w"), indent=2)
    print("[marketing] meta", meta_path)


if __name__ == "__main__":
    try:
        main(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else [])
    except SystemExit as e:
        if e.code not in (None, 0):
            print("[marketing] FEHLER:", e.code)
        raise
    except Exception:
        traceback.print_exc()
        sys.exit(1)
