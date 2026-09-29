"""
Piggy 3D-Maskottchen — reproduzierbar aus Tokens.

Aufruf (headless):
  blender -b -P brand/piggy/3d/build_piggy.py -- \
      --tokens brand/piggy/dist/tokens/piggy.resolved.json \
      --out    brand/piggy/dist/3d \
      --render all            # none | preview | sprites | anim | all
      [--samples 96] [--size 768] [--anim-size 384] [--quick]

Erzeugt:
  piggy.blend, piggy.glb                      Modell + Rig + Shape Keys + Aktionen
  sprites/piggy-mascot-<pose>-<expr>@{1,2,3}x.png   transparente Sprites (Basis 256 pt)
  anim/idle_####.png  (+ piggy-idle.webm/.mp4/.gif via build.sh)
  preview/*.png                                Kontrollbilder

Alle Farben kommen aus component.mascot der aufgelösten Tokens (keine Hex-Werte hier).
"""
import bpy, bmesh, sys, os, json, math, argparse
from mathutils import Vector, Matrix, Quaternion

# ----------------------------------------------------------------- args
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--tokens", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--render", default="preview")
ap.add_argument("--samples", type=int, default=96)
ap.add_argument("--size", type=int, default=768)
ap.add_argument("--anim-size", type=int, default=384)
ap.add_argument("--anim-samples", type=int, default=40)
ap.add_argument("--quick", action="store_true")
args = ap.parse_args(argv)

OUT = os.path.abspath(args.out)
os.makedirs(OUT, exist_ok=True)
T = json.load(open(args.tokens))
MC = T["component"]["mascot"]


def lin(hexstr):
    """sRGB-Hex -> linear RGBA für Blender."""
    h = hexstr.lstrip("#")[:6]
    rgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple((c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4) for c in rgb) + (1.0,)


def mixhex(a, b, t):
    A = [int(a.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    B = [int(b.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    return "#" + "".join("%02x" % round(A[i] + (B[i] - A[i]) * t) for i in range(3))


# ----------------------------------------------------------------- scene reset
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version = 0
scene = bpy.context.scene
scene.name = "Piggy"
world = bpy.data.worlds.new("PiggyWorld")
scene.world = world
coll = scene.collection

# ----------------------------------------------------------------- materials
def material(name, color, rough=0.45, metal=0.0, coat=0.0, coat_rough=0.12, sss=0.0, emission=None, sheen=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    b = nt.nodes.new("ShaderNodeBsdfPrincipled")
    o = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(b.outputs[0], o.inputs[0])
    b.inputs["Base Color"].default_value = lin(color)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    b.inputs["Coat Weight"].default_value = coat
    b.inputs["Coat Roughness"].default_value = coat_rough
    if sss:
        b.inputs["Subsurface Weight"].default_value = sss
        b.inputs["Subsurface Radius"].default_value = (1.0, 0.35, 0.3)
        b.inputs["Subsurface Scale"].default_value = 0.08
    if sheen:
        b.inputs["Sheen Weight"].default_value = sheen
        b.inputs["Sheen Tint"].default_value = lin("#FFFFFF")
    if emission:
        b.inputs["Emission Color"].default_value = lin(emission[0])
        b.inputs["Emission Strength"].default_value = emission[1]
    m.diffuse_color = lin(color)  # Viewport + glTF-Fallback
    return m


MAT = {
    "skin":     material("skin", MC["skin"], rough=0.42, coat=0.45, coat_rough=0.07, sss=0.08),
    "belly":    material("belly", mixhex(MC["skinLight"], MC["skin"], 0.45), rough=0.45, coat=0.25, sss=0.06),
    "snout":    material("snout", MC["snout"], rough=0.35, coat=0.35, sss=0.1),
    "nostril":  material("nostril", MC["nostril"], rough=0.6),
    "earInner": material("earInner", MC["earInner"], rough=0.5, sss=0.1),
    "cheek":    material("cheek", mixhex(MC["cheek"], MC["skin"], 0.35), rough=0.55),
    "hoof":     material("hoof", MC["hoof"], rough=0.3, coat=0.5),
    "eye":      material("eye", MC["eye"], rough=0.08, coat=1.0, coat_rough=0.03),
    "shine":    material("shine", MC["eyeHighlight"], rough=0.2, emission=(MC["eyeHighlight"], 1.6)),
    "mouth":    material("mouth", MC["mouth"], rough=0.5),
    "tongue":   material("tongue", MC["tongue"], rough=0.4),
    "slot":     material("slot", MC["slot"], rough=0.7),
    "coin":     material("coin", MC["coin"], rough=0.22, metal=1.0),
    "coinRim":  material("coinRim", MC["coinShade"], rough=0.28, metal=1.0),
}

# ----------------------------------------------------------------- geometry helpers
HEAD_C = Vector((0.0, 0.0, 1.36))
HEAD_R = Vector((0.86, 0.80, 0.76))  # a (x), b (y, Tiefe), c (z)


def head_surface(x, z, grow=0.0):
    """Punkt auf der Kopf-Vorderseite (-Y) für gegebenes x/z + Normalenvektor."""
    a, b, c = HEAD_R
    zz = z - HEAD_C.z
    k = 1 - (x / a) ** 2 - (zz / c) ** 2
    y = -b * math.sqrt(max(k, 0.0))
    p = Vector((x, y, z))
    n = Vector((x / a ** 2, y / b ** 2, zz / c ** 2)).normalized()
    return p + n * grow, n


def face_frame(x0, z0):
    p, n = head_surface(x0, z0)
    tz = (Vector((0, 0, 1)) - n * n.z).normalized()
    tx = tz.cross(n).normalized()
    return p, n, tx, tz


def new_obj(name, mesh, mats, parent_bone=None):
    ob = bpy.data.objects.new(name, mesh)
    coll.objects.link(ob)
    for m in mats:
        ob.data.materials.append(m)
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob


def ellipsoid_mesh(name, center, radii, segs=(32, 16), taper_top=0.0, mat_index=0):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segs[0], v_segments=segs[1], radius=1.0)
    for v in bm.verts:
        x, y, z = v.co
        if taper_top and z > 0:
            f = 1 - taper_top * z
            x *= f
            y *= f
        v.co = Vector((x * radii[0], y * radii[1], z * radii[2])) + Vector(center)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    return me


def add_subsurf(ob, levels=1, render=2):
    m = ob.modifiers.new("Subsurf", "SUBSURF")
    m.levels = levels
    m.render_levels = render
    return m


def build_mesh(name, verts, faces):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.update()
    return me


def add_shape_keys(ob, keys):
    """keys: dict name -> list[Vector] (gleiche Länge wie Mesh-Vertices)."""
    if not ob.data.shape_keys:
        ob.shape_key_add(name="Basis", from_mix=False)
    for kname, coords in keys.items():
        sk = ob.shape_key_add(name=kname, from_mix=False)
        for i, co in enumerate(coords):
            sk.data[i].co = co


# ----------------------------------------------------------------- face decals (Augen, Mund, Brauen)
def decal_ellipsoid_verts(x0, z0, rx, rz, depth, lift, segs=(24, 12), shape=None):
    """Ellipsoid, das der Kopf-Krümmung folgt. shape(u,v)->(u,v) verformt den Umriss."""
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=segs[0], v_segments=segs[1], radius=1.0)
    bm.verts.ensure_lookup_table()
    unit = [v.co.copy() for v in bm.verts]
    faces = [[v.index for v in f.verts] for f in bm.faces]
    bm.free()

    def verts_for(fn):
        out = []
        for co in unit:
            u, v, w = co.x * rx, co.z * rz, co.y  # y der Kugel = Tiefe (-1 vorne .. 1 hinten)
            if fn:
                u, v = fn(u, v, co)
            p, n = head_surface(x0 + u, z0 + v)
            out.append(p + n * (lift - w * depth))
        return out

    return unit, faces, verts_for


def build_eye(side):
    s = 1 if side == "L" else -1
    x0, z0 = 0.30 * s, 1.47
    rx, rz, depth = 0.118, 0.15, 0.05
    unit, faces, vf = decal_ellipsoid_verts(x0, z0, rx, rz, depth, lift=0.012)
    # Glanzlichter (zweiter/dritter Ellipsoid im selben Objekt)
    hl = []
    for (du, dv, r) in ((-0.035 * s + 0.0, 0.05, 0.034), (0.03 * s, -0.055, 0.016)):
        u2, f2, vf2 = decal_ellipsoid_verts(x0 + du, z0 + dv, r, r, 0.01, lift=0.045, segs=(12, 6))
        hl.append((u2, f2, vf2, du, dv))

    def assemble(eye_fn, hl_mode):
        verts = list(vf(eye_fn))
        for (u2, f2, vf2, du, dv) in hl:
            if hl_mode == "hide":
                p, n = head_surface(x0, z0)
                verts += [p - n * 0.02 for _ in u2]
            elif hl_mode == "low":
                verts += list(vf2(lambda u, v, co: (u * 0.8 + du * 0.1, v * 0.8 - (0.08 if dv > 0 else 0.0))))
            elif hl_mode == "wide":
                verts += list(vf2(lambda u, v, co: (u * 1.15 + du * 0.18, v * 1.15 + dv * 0.18)))
            else:
                verts += list(vf2(None))
        return verts

    all_faces = list(faces)
    off = len(unit)
    for (u2, f2, _, _, _) in hl:
        all_faces += [[i + off for i in f] for f in f2]
        off += len(u2)

    base = assemble(None, "normal")
    me = build_mesh("eye." + side, base, all_faces)
    ob = new_obj("eye." + side, me, [MAT["eye"], MAT["shine"]])
    # Materialindex für Glanzlichter
    n_eye = len(faces)
    for i, p in enumerate(me.polygons):
        p.material_index = 0 if i < n_eye else 1

    def closed(u, v, co):  # Happy-closed ^-Bogen
        t = max(0.0, 1 - (u / rx) ** 2)
        return u * 1.05, v * 0.16 + 0.06 * t - 0.02

    def wide(u, v, co):
        return u * 1.15, v * 1.18

    def sad(u, v, co):  # Oberlid abgeschnitten, nach aussen abfallend
        top = 0.35 * rz - 0.35 * rz * (u * s / rx)
        return u, min(v, top) if v > 0 else v * 0.95

    add_shape_keys(ob, {
        "closed": assemble(closed, "hide"),
        "wide": assemble(wide, "wide"),
        "sad": assemble(sad, "low"),
    })
    return ob


def tube_verts(points, radius, ring=10, profile=0.45):
    """Röhre entlang einer Punktliste, runde Enden über Radius-Profil."""
    verts = []
    n = len(points)
    for i, p in enumerate(points):
        t = i / (n - 1)
        a = points[min(i + 1, n - 1)] - points[max(i - 1, 0)]
        T_ = a.normalized() if a.length > 1e-6 else Vector((1, 0, 0))
        up = Vector((0, -1, 0)) if abs(T_.y) < 0.9 else Vector((0, 0, 1))
        N = T_.cross(up).normalized()
        B = T_.cross(N).normalized()
        r = radius * (math.sin(math.pi * t) ** profile if 0 < t < 1 else 0.0)
        for j in range(ring):
            ang = 2 * math.pi * j / ring
            verts.append(p + (N * math.cos(ang) + B * math.sin(ang)) * r)
    return verts


def tube_faces(n, ring=10):
    faces = []
    for i in range(n - 1):
        for j in range(ring):
            a = i * ring + j
            b = i * ring + (j + 1) % ring
            faces.append([a, b, b + ring, a + ring])
    return faces


def surf_curve(fn, n=24, lift=0.02):
    pts = []
    for i in range(n):
        t = i / (n - 1)
        x, z = fn(t)
        p, nrm = head_surface(x, z)
        pts.append(p + nrm * lift)
    return pts


def build_brow(side):
    s = 1 if side == "L" else -1
    N = 16
    cx, cz = 0.30 * s, 1.66

    def curve(dz_in, dz_out, arch, lift=0.02):
        def f(t):
            u = (t - 0.5) * 0.2  # Breite 0.2
            inner = (u * s) < 0
            tilt = (dz_in if inner else dz_out) * abs(u) / 0.1
            return cx + u, cz + tilt + arch * (1 - (u / 0.1) ** 2)
        return surf_curve(f, N, lift)

    hidden_pts = [head_surface(cx, cz)[0] - head_surface(cx, cz)[1] * 0.06 for _ in range(N)]
    base = tube_verts(hidden_pts, 0.0)
    faces = tube_faces(N)
    me = build_mesh("brow." + side, base, faces)
    ob = new_obj("brow." + side, me, [MAT["mouth"]])
    add_shape_keys(ob, {
        "up":    tube_verts(curve(0.0, 0.0, 0.035), 0.022),
        "sad":   tube_verts(curve(0.05, -0.04, 0.0), 0.022),
        "happy": tube_verts(curve(-0.01, -0.01, 0.03), 0.02),
        "angry": tube_verts(curve(-0.045, 0.03, 0.0), 0.022),
    })
    return ob


MOUTH_Z = 0.93
MOUTH_N = 48


def mouth_outline(kind):
    """48 Umrisspunkte (u,v): erste Hälfte obere Kante links->rechts, zweite Hälfte untere Kante rechts->links."""
    half = MOUTH_N // 2
    pts = []
    w = 0.15
    for i in range(half):
        t = i / (half - 1)
        u = -w + 2 * w * t
        q = (u / w) ** 2
        if kind == "smile":
            v = 0.035 * q
        elif kind == "open":
            v = 0.03 * q + 0.004
        elif kind == "O":
            ang = math.pi - math.pi * t
            u, v = 0.055 * math.cos(ang), 0.055 * math.sin(ang) - 0.03
        elif kind == "frown":
            v = -0.04 * q + 0.01
        elif kind == "smirk":
            v = 0.02 * q + 0.03 * (u / w + 1) * 0.5 * q
        pts.append((u, v))
    for i in range(half):
        t = i / (half - 1)
        u = w - 2 * w * t
        q = (u / w) ** 2
        if kind == "smile":
            v = 0.035 * q - 0.03 * math.sqrt(max(0, 1 - q)) - 0.006
        elif kind == "open":
            v = 0.03 * q + 0.004 - 0.15 * math.sqrt(max(0, 1 - q)) ** 0.8
        elif kind == "O":
            ang = -math.pi * t
            u, v = 0.055 * math.cos(ang), 0.07 * math.sin(ang) - 0.03
        elif kind == "frown":
            v = -0.04 * q + 0.01 - 0.022 * math.sqrt(max(0, 1 - q)) - 0.004
        elif kind == "smirk":
            v = 0.02 * q + 0.03 * (u / w + 1) * 0.5 * q - 0.02 * math.sqrt(max(0, 1 - q)) - 0.004
        pts.append((u, v))
    return pts


def mouth_mesh_verts(kind, lift=0.006, thick=0.02):
    outline = mouth_outline(kind)
    front, back = [], []
    for (u, v) in outline:
        p, n = head_surface(u, MOUTH_Z + v)
        front.append(p + n * lift)
        back.append(p - n * thick)
    cu = sum(o[0] for o in outline) / len(outline)
    cv = sum(o[1] for o in outline) / len(outline)
    pc, nc = head_surface(cu, MOUTH_Z + cv)
    return front + back + [pc + nc * (lift - 0.004)]


def mouth_faces():
    N = MOUTH_N
    c = 2 * N
    faces = [[i, (i + 1) % N, c] for i in range(N)]
    faces += [[i, i + N, (i + 1) % N + N, (i + 1) % N] for i in range(N)]
    return faces


def build_mouth():
    me = build_mesh("mouth", mouth_mesh_verts("smile"), mouth_faces())
    ob = new_obj("mouth", me, [MAT["mouth"]])
    add_shape_keys(ob, {k: mouth_mesh_verts(k) for k in ("open", "O", "frown", "smirk")})
    # Zunge: sichtbar nur bei "open"
    tb = ellipsoid_mesh("_tongue_tmp", (0, 0, 0), (1, 1, 1), segs=(16, 8))
    unit = [v.co.copy() for v in tb.vertices]
    faces = [list(p.vertices) for p in tb.polygons]
    bpy.data.meshes.remove(tb)

    def tongue(scale, dz):
        out = []
        for co in unit:
            p, n = head_surface(co.x * 0.075 * scale, MOUTH_Z - 0.105 + dz + co.z * 0.04 * scale)
            out.append(p + n * (0.008 - co.y * 0.012 * scale) if scale > 0 else p - n * 0.05)
        return out

    tme = build_mesh("tongue", tongue(0, 0), faces)
    tob = new_obj("tongue", tme, [MAT["tongue"]])
    add_shape_keys(tob, {"open": tongue(1.0, 0.0), "O": tongue(0.55, 0.035)})
    return ob, tob


# ----------------------------------------------------------------- body parts
def build_parts():
    P = {}
    head = new_obj("head", ellipsoid_mesh("head", HEAD_C, HEAD_R, segs=(40, 20)), [MAT["skin"]])
    add_subsurf(head)
    P["head"] = head

    body = new_obj("body", ellipsoid_mesh("body", (0, 0.03, 0.56), (0.56, 0.5, 0.52), segs=(32, 16)), [MAT["skin"]])
    add_subsurf(body)
    P["body"] = body
    belly = new_obj("belly", ellipsoid_mesh("belly", (0, -0.21, 0.52), (0.32, 0.3, 0.3), segs=(24, 12)), [MAT["belly"]])
    add_subsurf(belly)
    P["belly"] = belly

    # Schnauze: abgerundeter Puck
    bpy.ops.mesh.primitive_cylinder_add(vertices=40, radius=0.26, depth=0.26, location=(0, -0.73, 1.22), rotation=(math.radians(90), 0, 0))
    sn = bpy.context.active_object
    sn.name = "snout"
    sn.scale = (1.0, 0.76, 1.0)  # (lokal: x, y->Höhe nach Rotation, z Tiefe)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    bev = sn.modifiers.new("Bevel", "BEVEL")
    bev.width = 0.09
    bev.segments = 5
    add_subsurf(sn)
    sn.data.materials.append(MAT["snout"])
    for p in sn.data.polygons:
        p.use_smooth = True
    P["snout"] = sn
    for s in (1, -1):
        nm = "nostril." + ("L" if s > 0 else "R")
        no = new_obj(nm, ellipsoid_mesh(nm, (0.085 * s, -0.858, 1.22), (0.042, 0.03, 0.068), segs=(16, 8)), [MAT["nostril"]])
        P[nm] = no

    # Ohren (abgerundete Dreiecke) + Innenohr
    for s, side in ((1, "L"), (-1, "R")):
        ear = new_obj("ear." + side, ellipsoid_mesh("ear." + side, (0, 0, 0), (0.27, 0.085, 0.34), segs=(24, 12), taper_top=0.62), [MAT["skin"]])
        inner = new_obj("earInner." + side, ellipsoid_mesh("earInner." + side, (0, -0.05, -0.02), (0.17, 0.05, 0.23), segs=(20, 10), taper_top=0.6), [MAT["earInner"]])
        for ob in (ear, inner):
            add_subsurf(ob)
            ob.location = (0.5 * s, -0.08, 2.0)
            ob.rotation_euler = (math.radians(-22), math.radians(28 * s), math.radians(-12 * s))
        P["ear." + side] = ear
        P["earInner." + side] = inner

    # Wangen (Decal)
    for s, side in ((1, "L"), (-1, "R")):
        unit, faces, vf = decal_ellipsoid_verts(0.5 * s, 1.2, 0.115, 0.07, 0.02, lift=0.006, segs=(20, 10))
        me = build_mesh("cheek." + side, vf(None), faces)
        P["cheek." + side] = new_obj("cheek." + side, me, [MAT["cheek"]])

    # Münzschlitz oben auf dem Kopf
    sy = -0.2  # leicht nach vorne, damit der Schlitz in der 3/4-Ansicht sichtbar ist
    top = HEAD_C.z + HEAD_R.z * math.sqrt(1 - (sy / HEAD_R.y) ** 2)
    tilt = math.atan2(-sy / HEAD_R.y ** 2, (top - HEAD_C.z) / HEAD_R.z ** 2)
    slot = new_obj("slot", ellipsoid_mesh("slot", (0, 0, 0), (0.23, 0.065, 0.04), segs=(32, 8)), [MAT["slot"]])
    rim = new_obj("slotRim", ellipsoid_mesh("slotRim", (0, 0, -0.03), (0.3, 0.11, 0.045), segs=(32, 8)), [MAT["hoof"]])
    add_subsurf(rim)
    for ob, dz in ((slot, 0.022), (rim, 0.0)):
        ob.location = (0, sy, top + dz)
        ob.rotation_euler = (-tilt, 0, 0)
    P["slot"], P["slotRim"] = slot, rim

    # Beine + Hufe
    for s, side in ((1, "L"), (-1, "R")):
        leg = new_obj("leg." + side, ellipsoid_mesh("leg." + side, (0.25 * s, -0.02, 0.17), (0.16, 0.16, 0.2), segs=(20, 10)), [MAT["skin"]])
        hoof = new_obj("hoof." + side, ellipsoid_mesh("hoof." + side, (0.25 * s, -0.03, 0.045), (0.165, 0.165, 0.07), segs=(20, 10)), [MAT["hoof"]])
        add_subsurf(leg)
        P["leg." + side], P["hoof." + side] = leg, hoof
    # Arme (Stummel) + Hufspitze
    for s, side in ((1, "L"), (-1, "R")):
        arm = new_obj("arm." + side, ellipsoid_mesh("arm." + side, (0.0, 0, -0.17), (0.125, 0.125, 0.23), segs=(20, 10)), [MAT["skin"]])
        tip = new_obj("hand." + side, ellipsoid_mesh("hand." + side, (0.0, 0, -0.36), (0.12, 0.12, 0.075), segs=(16, 8)), [MAT["hoof"]])
        for ob in (arm, tip):
            ob.location = (0.5 * s, -0.02, 0.8)
            ob.rotation_euler = (0, math.radians(-28 * s), 0)
        add_subsurf(arm)
        P["arm." + side], P["hand." + side] = arm, tip

    # Ringelschwanz
    pts = []
    for i in range(40):
        t = i / 39
        a = t * math.pi * 3.2
        r = 0.1 * (1 - 0.45 * t)
        pts.append(Vector((r * math.cos(a), 0.55 + 0.12 * t, 0.62 + r * math.sin(a) + 0.08 * t)))
    tail = new_obj("tail", build_mesh("tail", tube_verts(pts, 0.04, ring=8, profile=0.2), tube_faces(40, 8)), [MAT["skin"]])
    P["tail"] = tail

    # Münze
    bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=0.2, depth=0.055, location=(0, -0.12, 2.52), rotation=(math.radians(90), 0, math.radians(35)))
    coin = bpy.context.active_object
    coin.name = "coin"
    b2 = coin.modifiers.new("Bevel", "BEVEL")
    b2.width = 0.02
    b2.segments = 3
    coin.data.materials.append(MAT["coin"])
    for p in coin.data.polygons:
        p.use_smooth = True
    bpy.ops.mesh.primitive_torus_add(major_radius=0.145, minor_radius=0.014, location=(0, -0.12, 2.52), rotation=(math.radians(90), 0, math.radians(35)))
    ring = bpy.context.active_object
    ring.name = "coinRing"
    ring.data.materials.append(MAT["coinRim"])
    for p in ring.data.polygons:
        p.use_smooth = True
    P["coin"], P["coinRing"] = coin, ring

    for side in ("L", "R"):
        P["eye." + side] = build_eye(side)
        P["brow." + side] = build_brow(side)
    P["mouth"], P["tongue"] = build_mouth()
    return P


# ----------------------------------------------------------------- rig
BONES = {
    # name: (head, tail, parent)
    "root":   ((0, 0, 0), (0, 0, 0.3), None),
    "body":   ((0, 0, 0.35), (0, 0, 0.8), "root"),
    "head":   ((0, 0, 0.82), (0, 0, 1.7), "body"),
    "ear.L":  ((0.42, -0.05, 1.9), (0.6, -0.1, 2.25), "head"),
    "ear.R":  ((-0.42, -0.05, 1.9), (-0.6, -0.1, 2.25), "head"),
    "arm.L":  ((0.5, -0.02, 0.8), (0.64, -0.02, 0.54), "body"),
    "arm.R":  ((-0.5, -0.02, 0.8), (-0.64, -0.02, 0.54), "body"),
    "leg.L":  ((0.25, -0.02, 0.32), (0.25, -0.02, 0.02), "root"),
    "leg.R":  ((-0.25, -0.02, 0.32), (-0.25, -0.02, 0.02), "root"),
    "tail":   ((0, 0.5, 0.62), (0, 0.72, 0.7), "body"),
    "coin":   ((0, -0.12, 2.35), (0, -0.12, 2.65), "root"),
}
PARENT = {
    "head": "head", "snout": "head", "nostril.L": "head", "nostril.R": "head",
    "eye.L": "head", "eye.R": "head", "brow.L": "head", "brow.R": "head", "mouth": "head", "tongue": "head",
    "cheek.L": "head", "cheek.R": "head", "slot": "head", "slotRim": "head",
    "ear.L": "ear.L", "earInner.L": "ear.L", "ear.R": "ear.R", "earInner.R": "ear.R",
    "body": "body", "belly": "body", "tail": "tail",
    "arm.L": "arm.L", "hand.L": "arm.L", "arm.R": "arm.R", "hand.R": "arm.R",
    "leg.L": "leg.L", "hoof.L": "leg.L", "leg.R": "leg.R", "hoof.R": "leg.R",
    "coin": "coin", "coinRing": "coin",
}


def build_rig(P):
    arm_data = bpy.data.armatures.new("PiggyRig")
    rig = bpy.data.objects.new("PiggyRig", arm_data)
    coll.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    for name, (h, t, par) in BONES.items():
        b = arm_data.edit_bones.new(name)
        b.head, b.tail = Vector(h), Vector(t)
        b.roll = 0
        if par:
            b.parent = arm_data.edit_bones[par]
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.context.view_layer.update()
    for obname, bone in PARENT.items():
        ob = P[obname]
        mw = ob.matrix_world.copy()
        ob.parent = rig
        ob.parent_type = "BONE"
        ob.parent_bone = bone
        bpy.context.view_layer.update()
        ob.matrix_world = mw
    bpy.context.view_layer.update()
    return rig


def rot_world(rig, bone, axis, deg):
    """Rotation um eine Welt-Achse (im Ruhezustand) als Bone-lokales Quaternion."""
    pb = rig.pose.bones[bone]
    rest = (rig.matrix_world @ pb.bone.matrix_local).to_3x3().normalized()
    q_world = Quaternion(Vector(axis), math.radians(deg))
    q_local = (rest.inverted() @ q_world.to_matrix() @ rest).to_quaternion()
    return q_local


POSES = {
    "idle": {
        "arm.L": [((0, 1, 0), -8)], "arm.R": [((0, 1, 0), 8)],
        "ear.L": [((1, 0, 0), 0)],
    },
    "cheer": {
        "root": {"loc": (0, 0, 0.22)},
        "arm.L": {"aim": (0.82, -0.42, 0.42)}, "arm.R": {"aim": (-0.82, -0.42, 0.42)},
        "head": [((1, 0, 0), -6)],
        "leg.L": [((1, 0, 0), -25), ((0, 1, 0), -12)], "leg.R": [((1, 0, 0), 20), ((0, 1, 0), 12)],
        "ear.L": [((0, 1, 0), -18)], "ear.R": [((0, 1, 0), 18)],
        "body": {"scale": (1.0, 1.0, 1.04)},
    },
    "catch": {
        "arm.L": {"aim": (0.55, -0.75, 0.42)}, "arm.R": {"aim": (-0.55, -0.75, 0.42)},
        "head": [((1, 0, 0), -14)],
        "coin": {"loc": (0, 0, 0.08)},
        "ear.L": [((1, 0, 0), 12)], "ear.R": [((1, 0, 0), 12)],
    },
}
EXPRESSIONS = {
    "neutral":   {},
    "happy":     {"mouth": {"open": 1}, "tongue": {"open": 1}, "brow.L": {"happy": 1}, "brow.R": {"happy": 1}},
    "surprised": {"mouth": {"O": 1}, "tongue": {"O": 1}, "eye.L": {"wide": 1}, "eye.R": {"wide": 1}, "brow.L": {"up": 1}, "brow.R": {"up": 1}},
    "sad":       {"mouth": {"frown": 1}, "eye.L": {"sad": 1}, "eye.R": {"sad": 1}, "brow.L": {"sad": 1}, "brow.R": {"sad": 1}},
    "wink":      {"mouth": {"smirk": 1}, "eye.R": {"closed": 1}, "brow.L": {"up": 0.6}},
}
POSE_DEFAULT_EXPR = {"idle": "neutral", "cheer": "happy", "catch": "surprised"}


def reset_pose(rig):
    for pb in rig.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = Quaternion()
        pb.location = (0, 0, 0)
        pb.scale = (1, 1, 1)


def apply_pose(rig, P, pose):
    reset_pose(rig)
    for bone, spec in POSES[pose].items():
        pb = rig.pose.bones[bone]
        if isinstance(spec, dict):
            if "aim" in spec:
                rest = (rig.matrix_world @ pb.bone.matrix_local).to_3x3().normalized()
                rest_dir = (pb.bone.tail_local - pb.bone.head_local).normalized()
                qw = rest_dir.rotation_difference(Vector(spec["aim"]).normalized())
                pb.rotation_quaternion = (rest.inverted() @ qw.to_matrix() @ rest).to_quaternion()
            if "loc" in spec:
                # Weltverschiebung -> Bone-lokal
                rest = (rig.matrix_world @ pb.bone.matrix_local).to_3x3().normalized()
                pb.location = rest.inverted() @ Vector(spec["loc"])
            if "scale" in spec:
                pb.scale = spec["scale"]
            continue
        q = Quaternion()
        for axis, deg in spec:
            q = rot_world(rig, bone, axis, deg) @ q
        pb.rotation_quaternion = q
    # Münze nur bei catch sichtbar
    for n in ("coin", "coinRing"):
        P[n].hide_render = pose != "catch"
        P[n].hide_viewport = pose != "catch"
    bpy.context.view_layer.update()


def apply_expression(P, expr):
    for ob in P.values():
        if ob.type == "MESH" and ob.data.shape_keys:
            for kb in ob.data.shape_keys.key_blocks[1:]:
                kb.value = 0.0
    for obname, keys in EXPRESSIONS[expr].items():
        for k, v in keys.items():
            P[obname].data.shape_keys.key_blocks[k].value = v


# ----------------------------------------------------------------- actions (für .blend + glTF)
def key_pose_action(rig, P, pose, name, frame=1):
    apply_pose(rig, P, pose)
    rig.animation_data_create()
    act = bpy.data.actions.new(name)
    act.use_fake_user = True
    rig.animation_data.action = act
    for pb in rig.pose.bones:
        pb.keyframe_insert("rotation_quaternion", frame=frame)
        pb.keyframe_insert("location", frame=frame)
        pb.keyframe_insert("scale", frame=frame)
    return act


IDLE_FRAMES = 48
BLINK = {}


def build_idle_action(rig, P):
    reset_pose(rig)
    rig.animation_data_create()
    act = bpy.data.actions.new("anim_idle")
    act.use_fake_user = True
    rig.animation_data.action = act
    for f in range(1, IDLE_FRAMES + 1):
        ph = 2 * math.pi * (f - 1) / IDLE_FRAMES
        reset_pose(rig)
        body = rig.pose.bones["body"]
        body.rotation_quaternion = rot_world(rig, "body", (0, 1, 0), 4.0 * math.sin(ph))
        s = 1.0 + 0.025 * math.sin(2 * ph)
        body.scale = (1.0 + (1 - s) * 0.5, 1.0 + (1 - s) * 0.5, s)
        head = rig.pose.bones["head"]
        head.rotation_quaternion = rot_world(rig, "head", (0, 1, 0), -5.0 * math.sin(ph - 0.5)) @ rot_world(rig, "head", (1, 0, 0), 2.0 * math.sin(2 * ph))
        for side, sg in (("L", 1), ("R", -1)):
            e = rig.pose.bones["ear." + side]
            e.rotation_quaternion = rot_world(rig, "ear." + side, (1, 0, 0), 7.0 * math.sin(2 * ph - 0.9 * sg))
            a = rig.pose.bones["arm." + side]
            a.rotation_quaternion = rot_world(rig, "arm." + side, (0, 1, 0), -sg * (8 + 5 * math.sin(2 * ph + 0.6)))
        tail = rig.pose.bones["tail"]
        tail.rotation_quaternion = rot_world(rig, "tail", (0, 1, 0), 18 * math.sin(3 * ph))
        root = rig.pose.bones["root"]
        root.location = (0, 0, 0)
        for pb in rig.pose.bones:
            pb.keyframe_insert("rotation_quaternion", frame=f)
            pb.keyframe_insert("scale", frame=f)
            pb.keyframe_insert("location", frame=f)
    # Blinzeln über Shape Keys (Frames 30-34)
    for side in ("L", "R"):
        kb = P["eye." + side].data.shape_keys.key_blocks["closed"]
        for f, v in ((1, 0), (29, 0), (31, 1), (33, 0), (IDLE_FRAMES, 0)):
            kb.value = v
            kb.keyframe_insert("value", frame=f)
    # Blinzel-Aktionen parken, damit sie Standbild-Ausdrücke nicht überschreiben
    for side in ("L", "R"):
        sk = P["eye." + side].data.shape_keys
        sk.animation_data.action.name = "blink_" + side
        sk.animation_data.action.use_fake_user = True
        BLINK[side] = sk.animation_data.action
        sk.animation_data.action = None
    return act


# ----------------------------------------------------------------- lights, camera, render
def setup_stage():
    w = scene.world
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs[0].default_value = lin("#FFF6EE")
    bg.inputs[1].default_value = 0.3

    def area(name, loc, rot, size, energy, color="#FFFFFF", shadow=True):
        ld = bpy.data.lights.new(name, "AREA")
        ld.cycles.cast_shadow = shadow
        ld.size = size
        ld.energy = energy
        ld.color = lin(color)[:3]
        ob = bpy.data.objects.new(name, ld)
        coll.objects.link(ob)
        ob.location = loc
        ob.rotation_euler = [math.radians(a) for a in rot]
        return ob

    area("Key", (-2.4, -3.6, 5.4), (38, 0, -32), 4.5, 380, "#FFF4EA")
    gl = area("Gloss", (-2.0, -4.5, 3.8), (55, 0, -24), 0.8, 260, "#FFFFFF", shadow=False)
    gl.visible_diffuse = False
    area("Fill", (4.2, -3.2, 2.0), (70, 0, 52), 5.0, 110, "#FFE9F0", shadow=False)
    area("Rim", (1.5, 4.0, 4.2), (-50, 0, 160), 2.5, 450, "#FFFFFF", shadow=False)
    area("Top", (0, 0, 6), (0, 0, 0), 3.0, 70, "#FFFFFF", shadow=False)

    # Kontaktschatten
    bpy.ops.mesh.primitive_plane_add(size=12, location=(0, 0, 0))
    ground = bpy.context.active_object
    ground.name = "ShadowCatcher"
    ground.is_shadow_catcher = True

    cam_d = bpy.data.cameras.new("Cam")
    cam_d.lens = 85
    cam = bpy.data.objects.new("Cam", cam_d)
    coll.objects.link(cam)
    scene.camera = cam
    az, el, dist = math.radians(16), math.radians(19), 8.6
    target = Vector((0, 0, 1.3))
    cam.location = target + Vector((math.sin(az) * dist * math.cos(el), -math.cos(az) * dist * math.cos(el), math.sin(el) * dist))
    d = target - cam.location
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()

    r = scene.render
    r.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.use_denoising = False
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = 0.02
    scene.cycles.max_bounces = 6
    scene.cycles.transparent_max_bounces = 4
    scene.cycles.sample_clamp_indirect = 4.0
    r.film_transparent = True
    r.image_settings.file_format = "PNG"
    r.image_settings.color_mode = "RGBA"
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0.0
    return cam, ground


def render_to(path, size, samples):
    scene.render.resolution_x = size
    scene.render.resolution_y = size
    scene.render.resolution_percentage = 100
    scene.cycles.samples = samples
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)


# ----------------------------------------------------------------- main
P = build_parts()
rig = build_rig(P)
cam, ground = setup_stage()

pose_actions = {p: key_pose_action(rig, P, p, "pose_" + p) for p in POSES}
idle_act = build_idle_action(rig, P)
scene.frame_start, scene.frame_end, scene.render.fps = 1, IDLE_FRAMES, 24

# Standard-Zustand im .blend: idle + neutral
rig.animation_data.action = pose_actions["idle"]
apply_pose(rig, P, "idle")
apply_expression(P, "neutral")
for n in ("coin", "coinRing"):
    P[n].hide_render = False
    P[n].hide_viewport = False

bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "piggy.blend"))
print("[piggy] saved", os.path.join(OUT, "piggy.blend"))

# --------------------------------------------------------------- glTF export
def export_glb():
    ground.hide_set(True)
    for ob in scene.objects:
        ob.select_set(ob.type in ("MESH", "ARMATURE") and ob.name != "ShadowCatcher")
    # Pose-Aktionen in NLA-Spuren, damit alle exportiert werden
    rig.animation_data.action = None
    for act in list(pose_actions.values()) + [idle_act]:
        tr = rig.animation_data.nla_tracks.new()
        tr.name = act.name
        tr.strips.new(act.name, 1, act)
    path = os.path.join(OUT, "piggy.glb")
    bpy.ops.export_scene.gltf(
        filepath=path, export_format="GLB", use_selection=True,
        export_apply=True, export_animations=True, export_animation_mode="NLA_TRACKS",
        export_morph=True, export_morph_normal=False, export_skins=True,
        export_yup=True, export_texcoords=False, export_normals=True,
        export_draco_mesh_compression_enable=False,
    )
    for tr in list(rig.animation_data.nla_tracks):
        rig.animation_data.nla_tracks.remove(tr)
    ground.hide_set(False)
    print("[piggy] glb", path, os.path.getsize(path))


mode = args.render
if mode in ("all", "glb", "sprites", "anim") or mode == "all":
    # Subsurf für Export reduzieren (Grösse < 1 MB), danach zurück
    saved = {}
    for ob in scene.objects:
        for m in ob.modifiers:
            if m.type == "SUBSURF":
                saved[(ob.name, m.name)] = m.levels
                m.levels = 1
    export_glb()

rig.animation_data.action = None
samples = 16 if args.quick else args.samples


def sprite_name(pose, expr):
    return "piggy-mascot-%s-%s" % (pose, expr)


if mode in ("preview", "previewall", "all", "sprites"):
    os.makedirs(os.path.join(OUT, "preview"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "sprites", "_master"), exist_ok=True)
    jobs = []
    if mode == "preview":
        jobs = [("idle", "neutral")]
    else:
        jobs = [(p, POSE_DEFAULT_EXPR[p]) for p in POSES] + [("idle", e) for e in EXPRESSIONS if e != "neutral"]
    for pose, expr in jobs:
        apply_pose(rig, P, pose)
        apply_expression(P, expr)
        size = 384 if mode.startswith("preview") else args.size * 2  # 2x rendern, später herunterskalieren (Rausch-Reduktion)
        out = os.path.join(OUT, "preview" if mode.startswith("preview") else "sprites/_master", sprite_name(pose, expr) + ".png")
        render_to(out, size, samples)
        print("[piggy] render", out)

if mode in ("anim", "all"):
    os.makedirs(os.path.join(OUT, "anim"), exist_ok=True)
    apply_expression(P, "neutral")
    for n in ("coin", "coinRing"):
        P[n].hide_render = True
    rig.animation_data.action = idle_act
    for side in ("L", "R"):
        P["eye." + side].data.shape_keys.animation_data.action = BLINK[side]
    step = 2 if args.quick else 1
    for f in range(1, IDLE_FRAMES + 1, step):
        scene.frame_set(f)
        render_to(os.path.join(OUT, "anim", "idle_%04d.png" % f), args.anim_size, 16 if args.quick else args.anim_samples)
    print("[piggy] anim done")
print("[piggy] done")
