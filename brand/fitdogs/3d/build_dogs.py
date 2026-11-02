"""
FitDogs 3D-Maskottchen: zwei Skins (Shiba, Dobermann) auf EINEM gemeinsamen Skelett ("fitdogs-v1").

Aufruf (headless):
  blender -b -P brand/fitdogs/3d/build_dogs.py -- --skin shiba|dobermann|all \
      --out brand/fitdogs/dist/3d [--render none|preview|all|icons] [--samples N] [--size 768]
      [--icon-size 1024] [--no-aura]

Erzeugt je Skin:
  <skin>.blend, <skin>.glb, <skin>.manifest.json      Modell + Rig + Shape Keys + Aktionen (+ Kontrolldatei)
  sprites/<skin>-mascot-<pose>-<expr>.png             Posen-Sprites mit Alpha (inkl. Aura-Ring)
  <skin>-overview.png                                 Uebersichtsblatt (Hintergrund aus der Skin-Datei)
  ../icons/<skin>-<icon-size>.png + .meta.json        App-Icon ohne Alpha (nur bei --render all|icons)
  preview/*.png                                       Kontrollbild (--render preview)

Ein Koerper-/Rig-Builder fuer beide Skins: skins/<skin>.json aendert nur das Aussehen (Farben, Ohren,
Schnauze, Markings, Accessoires, Outline-/Aura-Farbe, Hintergrund). Alle Farben stehen dort, nicht hier.

Look: Cel-Shading ueber Emission + Geometry-Normal/Licht-Richtung (Farbrampe ohne Interpolation), Outline als
Inverted Hull (Displace entlang der Normalen, nur Rueckseiten sichtbar), Aura-Ring als Alpha-Dilatation
(numpy) nach dem Render. Alles laeuft in Cycles CPU, ohne Lichter, ohne Rauschen.
"""
import bpy, bmesh, sys, os, json, math, argparse
import numpy as np
from mathutils import Vector, Matrix, Euler

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SKELETON = "fitdogs-v1"

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--skin", default="all")
ap.add_argument("--out", required=True)
ap.add_argument("--render", default="preview", choices=["none", "preview", "all", "icons"])
ap.add_argument("--samples", type=int, default=48)
ap.add_argument("--size", type=int, default=768, help="Sprite-Kantenlaenge in px (quadratisch)")
ap.add_argument("--icon-size", type=int, default=1024)
ap.add_argument("--skins-dir", default=os.path.join(ROOT, "skins"))
ap.add_argument("--no-aura", action="store_true")
ap.add_argument("--cam", default="", help="Debug: cx,cz,scale fuer preview")
args = ap.parse_args(argv)
OUT = os.path.abspath(args.out)
ICON_DIR = os.path.join(os.path.dirname(OUT), "icons")


# ----------------------------------------------------------------- Farben
def lin(hexstr):
    h = hexstr.lstrip("#")[:6]
    rgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple((c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4) for c in rgb) + (1.0,)


def srgb(hexstr):
    h = hexstr.lstrip("#")[:6]
    return np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)], dtype=np.float32)


def mixhex(a, b, t):
    A = [int(a.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    B = [int(b.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)]
    return "#" + "".join("%02x" % round(A[i] + (B[i] - A[i]) * t) for i in range(3))


# ----------------------------------------------------------------- globaler Zustand (pro Skin neu)
S = {}
PARTS = []
MATC = {}
PBR = {}   # Name des Toon-Materials -> PBR-Zwilling (fuer glTF)
LIGHT = Vector((-0.62, -0.40, 0.68)).normalized()


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    S["scene"] = bpy.context.scene
    S["coll"] = S["scene"].collection
    S["scene"].world = bpy.data.worlds.new("FitdogsWorld")
    PARTS.clear(); MATC.clear(); PBR.clear()


# ----------------------------------------------------------------- Materialien
def _out_node(nt):
    o = nt.nodes.new("ShaderNodeOutputMaterial")
    return o


def pbr_twin(name, hexc):
    m = bpy.data.materials.new(name + ".pbr")
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = lin(hexc)
    b.inputs["Roughness"].default_value = 0.7
    m.diffuse_color = lin(hexc)
    return m


def flat_mat(hexc):
    key = ("f", hexc)
    if key in MATC:
        return MATC[key]
    m = bpy.data.materials.new("flat_" + hexc.lstrip("#"))
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    e = nt.nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = lin(hexc)
    o = _out_node(nt)
    nt.links.new(e.outputs[0], o.inputs[0])
    m.diffuse_color = lin(hexc)
    PBR[m.name] = pbr_twin(m.name, hexc)
    MATC[key] = m
    return m


def toon_mat(hexc):
    key = ("t", hexc)
    if key in MATC:
        return MATC[key]
    T = S["skin"]["toon"]
    shade = mixhex(hexc, T["shade_tint"], T["shade_mix"])
    hi = mixhex(hexc, "#FFFFFF", T["highlight_mix"])
    m = bpy.data.materials.new("toon_" + hexc.lstrip("#"))
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    dot = nt.nodes.new("ShaderNodeVectorMath")
    dot.operation = "DOT_PRODUCT"
    dot.inputs[1].default_value = LIGHT
    mad = nt.nodes.new("ShaderNodeMath")
    mad.operation = "MULTIPLY_ADD"
    mad.inputs[1].default_value = 0.5
    mad.inputs[2].default_value = 0.5
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.interpolation = "CONSTANT"
    els = ramp.color_ramp.elements
    els[0].position, els[0].color = 0.0, lin(shade)
    els[1].position, els[1].color = 0.50, lin(hexc)
    e2 = els.new(0.97)
    e2.color = lin(hi)
    em = nt.nodes.new("ShaderNodeEmission")
    o = _out_node(nt)
    nt.links.new(geo.outputs["Normal"], dot.inputs[0])
    nt.links.new(dot.outputs["Value"], mad.inputs[0])
    nt.links.new(mad.outputs[0], ramp.inputs[0])
    nt.links.new(ramp.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs[0], o.inputs[0])
    m.diffuse_color = lin(hexc)
    PBR[m.name] = pbr_twin(m.name, hexc)
    MATC[key] = m
    return m


def outline_mat():
    key = ("o",)
    if key in MATC:
        return MATC[key]
    m = bpy.data.materials.new("outline")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = lin(S["skin"]["outline"]["color"])
    mix = nt.nodes.new("ShaderNodeMixShader")
    o = _out_node(nt)
    nt.links.new(geo.outputs["Backfacing"], mix.inputs[0])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], o.inputs[0])
    MATC[key] = m
    return m


def pal(key):
    """Palettenschluessel oder direkter Hex-Wert."""
    p = S["skin"]["palette"]
    return p[key] if key in p else key


def M(key):
    return toon_mat(pal(key))


def F(key):
    return flat_mat(pal(key))


def set_look(look):
    """'toon' (Render/.blend) oder 'pbr' (glTF)."""
    for ob in bpy.data.objects:
        if ob.type != "MESH":
            continue
        for slot in ob.material_slots:
            mat = slot.material
            if look == "pbr" and mat and mat.name in PBR:
                slot.material = PBR[mat.name]
            elif look == "toon" and mat and mat.name.endswith(".pbr"):
                slot.material = bpy.data.materials[mat.name[:-4]]


# ----------------------------------------------------------------- Geometrie-Helfer
def build_mesh(name, verts, faces):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.update()
    return me


def new_obj(name, mesh, mats):
    ob = bpy.data.objects.new(name, mesh)
    S["coll"].objects.link(ob)
    for m in mats:
        ob.data.materials.append(m)
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob


def add_subsurf(ob, levels=1, render=2):
    m = ob.modifiers.new("Subsurf", "SUBSURF")
    m.levels, m.render_levels = levels, render
    return m


_UNIT = {}


def unit_sphere(segs):
    if segs not in _UNIT:
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=segs[0], v_segments=segs[1], radius=1.0)
        bm.verts.index_update()
        _UNIT[segs] = ([v.co.copy() for v in bm.verts], [[v.index for v in f.verts] for f in bm.faces])
        bm.free()
    return _UNIT[segs]


def add_part(ob, bone, ol):
    PARTS.append({"ob": ob, "bone": bone, "ol": ol})
    return ob


def blob(name, center, radii, bone, mat, rot=(0, 0, 0), offset=(0, 0, 0), taper=None, segs=(24, 14), ol=0.03, sub=True):
    """Ellipsoid (optional verjuengt), in Weltkoordinaten eingebacken. taper=(achse, oben, unten)."""
    verts, faces = unit_sphere(segs)
    R = Euler([math.radians(a) for a in rot], "XYZ").to_matrix()
    out = []
    for co in verts:
        x, y, z = co
        if taper:
            ax, kt, kb = taper
            c = {"x": x, "y": y, "z": z, "-y": -y}[ax]
            f = 1 - kt * c if c > 0 else 1 + kb * c
            if ax == "z":
                x, y = x * f, y * f
            elif ax in ("y", "-y"):
                x, z = x * f, z * f
            else:
                y, z = y * f, z * f
        p = Vector((x * radii[0], y * radii[1], z * radii[2])) + Vector(offset)
        out.append(R @ p + Vector(center))
    ob = new_obj(name, build_mesh(name, out, faces), [mat])
    if sub:
        add_subsurf(ob)
    return add_part(ob, bone, ol * S["skin"]["outline"].get("thickness", 1.0))


def pair(name, center, radii, bone, mat, rot=(0, 0, 0), offset=(0, 0, 0), **kw):
    """Spiegelpaar .L/.R; bone enthaelt {s} fuer die Seite."""
    for side, sg in (("L", 1), ("R", -1)):
        blob("%s.%s" % (name, side), (center[0] * sg, center[1], center[2]), radii, bone.format(s=side), mat,
             rot=(rot[0], rot[1] * sg, rot[2] * sg), offset=(offset[0] * sg, offset[1], offset[2]), **kw)


def tube_verts(points, radius, ring=8, profile=0.45):
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


def tube_faces(n, ring=8):
    faces = []
    for i in range(n - 1):
        for j in range(ring):
            a = i * ring + j
            b = i * ring + (j + 1) % ring
            faces.append([a, b, b + ring, a + ring])
    return faces


def add_shape_keys(ob, keys):
    ob.shape_key_add(name="neutral", from_mix=False)
    for kname, coords in keys.items():
        sk = ob.shape_key_add(name=kname, from_mix=False)
        for i, co in enumerate(coords):
            sk.data[i].co = co


KEYS = ("happy", "angry", "surprised")


# ----------------------------------------------------------------- Oberflaechen-Projektion (Decals)
def surface(ob, x, z):
    dg = bpy.context.evaluated_depsgraph_get()
    hit, loc, nor, idx = ob.ray_cast(Vector((x, -9, z)), Vector((0, 1, 0)), depsgraph=dg)
    if not hit:
        return Vector((x, 0, z)), Vector((0, -1, 0))
    return loc, nor


def surf_pn(ob, x, z, e=0.035):
    p, _ = surface(ob, x, z)
    px = surface(ob, x + e, z)[0] - surface(ob, x - e, z)[0]
    pz = surface(ob, x, z + e)[0] - surface(ob, x, z - e)[0]
    n = px.cross(pz)
    n = n.normalized() if n.length > 1e-9 else Vector((0, -1, 0))
    if n.y > 0:
        n = -n
    return p, n


class Decal:
    """Mehrere flache Ellipsoide, die der Oberflaeche von 'surf' folgen (ein Mesh, mehrere Materialien)."""

    def __init__(self, surf, gx, gz, elems, segs=(16, 8)):
        self.surf, self.gx, self.gz, self.elems = surf, gx, gz, elems
        self.unit, self.faces = unit_sphere(segs)
        self.cache = {}

    def verts(self, warp=None):
        out = []
        for ei, e in enumerate(self.elems):
            for co in self.unit:
                u, v = e["dx"] + co.x * e["rx"], e["dz"] + co.z * e["rz"]
                w = warp(u, v, ei) if warp else (u, v)
                if w is None:
                    k = ("c", ei)
                    if k not in self.cache:
                        self.cache[k] = surf_pn(self.surf, self.gx + e["dx"], self.gz + e["dz"])
                    p, n = self.cache[k]
                    out.append(p - n * 0.04)
                    continue
                p, n = surf_pn(self.surf, self.gx + w[0], self.gz + w[1])
                out.append(p + n * (e["lift"] - co.y * e["depth"]))
        return out

    def faces_all(self):
        f, off = [], 0
        for _ in self.elems:
            f += [[i + off for i in fc] for fc in self.faces]
            off += len(self.unit)
        return f

    def normals(self):
        ns = []
        for e in self.elems:
            _, n = surf_pn(self.surf, self.gx + e["dx"], self.gz + e["dz"])
            ns += [n] * len(self.unit)
        return ns

    def make(self, name, mats, warp=None):
        me = build_mesh(name, self.verts(warp), self.faces_all())
        ob = new_obj(name, me, mats)
        nv = len(self.unit)
        for i, p in enumerate(me.polygons):
            p.material_index = i // len(self.faces)
        try:
            me.use_auto_smooth = True
            me.normals_split_custom_set_from_vertices([tuple(n) for n in self.normals()])
        except Exception as ex:  # nur Optik
            print("[fitdogs] custom normals skipped:", ex)
        return ob


# ----------------------------------------------------------------- Rig (identisch fuer alle Skins)
BONES = {
    "root":        ((0, 0, 0), (0, 0, 0.3), None),
    "pelvis":      ((0, 0, 0.95), (0, 0, 1.25), "root"),
    "torso":       ((0, 0, 1.15), (0, 0, 2.5), "pelvis"),
    "neck":        ((0, 0, 2.5), (0, -0.05, 2.85), "torso"),
    "head":        ((0, -0.05, 2.75), (0, -0.05, 3.6), "neck"),
    "jaw":         ((0, -0.2, 2.8), (0, -0.75, 2.7), "head"),
    "ear.L":       ((0.36, 0, 3.3), (0.5, 0, 3.7), "head"),
    "ear.R":       ((-0.36, 0, 3.3), (-0.5, 0, 3.7), "head"),
    "upper_arm.L": ((1.0, 0, 2.3), (1.22, 0, 1.55), "torso"),
    "upper_arm.R": ((-1.0, 0, 2.3), (-1.22, 0, 1.55), "torso"),
    "forearm.L":   ((1.22, 0, 1.55), (1.18, -0.1, 0.85), "upper_arm.L"),
    "forearm.R":   ((-1.22, 0, 1.55), (-1.18, -0.1, 0.85), "upper_arm.R"),
    "hand.L":      ((1.18, -0.1, 0.85), (1.16, -0.12, 0.55), "forearm.L"),
    "hand.R":      ((-1.18, -0.1, 0.85), (-1.16, -0.12, 0.55), "forearm.R"),
    "thigh.L":     ((0.4, 0, 1.0), (0.4, 0, 0.5), "pelvis"),
    "thigh.R":     ((-0.4, 0, 1.0), (-0.4, 0, 0.5), "pelvis"),
    "shin.L":      ((0.4, 0, 0.5), (0.4, -0.04, 0.08), "thigh.L"),
    "shin.R":      ((-0.4, 0, 0.5), (-0.4, -0.04, 0.08), "thigh.R"),
    "tail":        ((0, 0.35, 1.0), (0, 0.7, 1.3), "pelvis"),
}
LOWER_BONES = ("root", "pelvis", "thigh.L", "thigh.R", "shin.L", "shin.R", "tail")
REST = {}


def build_rig():
    arm_data = bpy.data.armatures.new("FitdogRig")
    rig = bpy.data.objects.new("FitdogRig", arm_data)
    S["coll"].objects.link(rig)
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
    for name in BONES:
        REST[name] = arm_data.bones[name].matrix_local.copy()
    for pt in PARTS:
        ob = pt["ob"]
        mw = ob.matrix_world.copy()
        ob.parent = rig
        ob.parent_type = "BONE"
        ob.parent_bone = pt["bone"]
        bpy.context.view_layer.update()
        ob.matrix_world = mw
    bpy.context.view_layer.update()
    for pb in rig.pose.bones:
        pb.rotation_mode = "QUATERNION"
    return rig


# ----------------------------------------------------------------- Pose-Solver (reine Mathematik, ohne Szenen-Update)
def solve(spec):
    """spec: Bone -> [("rot",achse,grad) | ("aim",richtung) | ("loc",vektor) | ("scale",vektor)] in WELT-Achsen.
    Liefert Bone -> (Quaternion, Location, Scale)."""
    pose, out = {}, {}
    for name, (_, _, par) in BONES.items():
        M0 = (pose[par] @ REST[par].inverted() @ REST[name]) if par else REST[name].copy()
        M0r = M0.to_quaternion().to_matrix()
        L = Matrix.Identity(3)
        loc, sc = Vector((0, 0, 0)), Vector((1, 1, 1))
        for op in spec.get(name, []):
            k = op[0]
            if k == "rot":
                R = Matrix.Rotation(math.radians(op[2]), 3, Vector(op[1]).normalized())
                L = M0r.inverted() @ R @ M0r @ L
            elif k == "aim":
                W = M0r @ L
                cur = (W @ Vector((0, 1, 0))).normalized()
                qw = cur.rotation_difference(Vector(op[1]).normalized()).to_matrix()
                L = M0r.inverted() @ qw @ W
            elif k == "loc":
                loc = M0r.inverted() @ Vector(op[1])
            elif k == "scale":
                sc = Vector(op[1])
        q = L.to_quaternion()
        pose[name] = M0 @ Matrix.LocRotScale(loc, q, sc)
        out[name] = (q, loc, sc)
    return out


def apply_spec(rig, spec, key_frame=None):
    for name, (q, loc, sc) in solve(spec).items():
        pb = rig.pose.bones[name]
        pb.rotation_quaternion, pb.location, pb.scale = q, loc, sc
        if key_frame is not None:
            pb.keyframe_insert("rotation_quaternion", frame=key_frame)
            pb.keyframe_insert("location", frame=key_frame)
            pb.keyframe_insert("scale", frame=key_frame)


def sgn(side):
    return 1 if side == "L" else -1


def idle_spec(ph):
    s = math.sin
    sp = {
        "root": [("loc", (0, 0, 0.012 * s(2 * ph)))],
        "torso": [("scale", (1 + 0.010 * s(2 * ph), 1 + 0.008 * s(2 * ph), 1 + 0.018 * s(2 * ph))),
                  ("rot", (0, 1, 0), 1.6 * s(ph))],
        "head": [("rot", (0, 1, 0), -2.5 * s(ph - 0.5)), ("rot", (1, 0, 0), 1.5 * s(2 * ph - 0.4))],
        "tail": [("rot", (0, 0, 1), 16 * s(3 * ph))],
    }
    for side in ("L", "R"):
        g = sgn(side)
        sp["ear." + side] = [("rot", (1, 0, 0), 5 * s(2 * ph - 0.9 * g))]
        sp["upper_arm." + side] = [("rot", (0, 1, 0), -g * (2.0 + 1.4 * s(2 * ph + 0.6)))]
        sp["forearm." + side] = [("rot", (0, 1, 0), g * 1.2 * s(2 * ph + 1.4))]
    return sp


def flex_spec(p=0.0, lean=0.0):
    sp = {"torso": [("scale", (1 + 0.035 * p, 1 + 0.02 * p, 1 + 0.01 * p)), ("rot", (1, 0, 0), -3 - 2 * p)],
          "head": [("rot", (1, 0, 0), 5 + 2 * p)], "pelvis": [("loc", (0, 0, -0.02 * p))]}
    for side in ("L", "R"):
        g = sgn(side)
        sp["upper_arm." + side] = [("aim", (g * 1.0, -0.10, 0.12 + 0.05 * p))]
        sp["forearm." + side] = [("aim", (g * 0.10, -0.32, 1.0))]
        sp["hand." + side] = [("aim", (g * 0.06, -0.50 - 0.1 * p, 1.0))]
        sp["thigh." + side] = [("rot", (0, 1, 0), g * -5)]
        sp["shin." + side] = [("rot", (0, 1, 0), g * 5)]
        sp["ear." + side] = [("rot", (0, 1, 0), g * 6)]
    return sp


def wave_spec(a=0.0, raise_=1.0):
    """Rechter Arm (-x) winkt, a in [-1,1] schwenkt den Unterarm."""
    sp = idle_spec(0.0)
    sp["upper_arm.R"] = [("aim", (-0.70 * raise_ - 0.22 * (1 - raise_), -0.22, 0.52 * raise_ - 0.75 * (1 - raise_)))]
    sp["forearm.R"] = [("aim", (-0.30 + 0.40 * a * raise_ - 0.0 * (1 - raise_), -0.22, 1.0 * raise_ - 0.9 * (1 - raise_)))]
    sp["hand.R"] = [("aim", (-0.30 + 0.55 * a * raise_, -0.22, 1.0 * raise_ - 0.9 * (1 - raise_)))]
    sp["torso"] = [("rot", (0, 1, 0), -3 * raise_)]
    sp["head"] = [("rot", (0, 1, 0), 6 * raise_), ("rot", (1, 0, 0), 2)]
    return sp


def hop_spec(k):
    """k: -1 = tiefe Hocke, 0 = Stand, 1 = Scheitelpunkt in der Luft."""
    sp = {"root": [("loc", (0, 0, (0.55 * k) if k > 0 else 0.16 * k))]}
    up = max(k, 0.0)
    cr = max(-k, 0.0)
    for side in ("L", "R"):
        g = sgn(side)
        sp["thigh." + side] = [("aim", (g * 0.06, -0.62 * up - 0.45 * cr, -1.0 + 0.45 * up - 0.2 * cr))]
        sp["shin." + side] = [("aim", (g * 0.04, 0.55 * up + 0.2 * cr, -1.0 + 0.3 * up))]
        sp["upper_arm." + side] = [("aim", (g * (0.22 + 0.9 * up - 0.15 * cr), -0.1 - 0.25 * up - 0.2 * cr, -0.75 + 0.9 * up - 0.1 * cr))]
        sp["forearm." + side] = [("aim", (g * (0.0 + 0.55 * up), -0.1 - 0.5 * up - 0.3 * cr, -1.0 + 1.7 * up))]
        sp["hand." + side] = [("aim", (g * (0.0 + 0.5 * up), -0.15 - 0.5 * up, -1.0 + 1.6 * up))]
        sp["ear." + side] = [("rot", (1, 0, 0), -14 * up + 8 * cr)]
    sp["torso"] = [("rot", (1, 0, 0), -4 * cr + 3 * up)]
    sp["head"] = [("rot", (1, 0, 0), -5 * up)]
    sp["tail"] = [("rot", (1, 0, 0), -18 * up)]
    sp["pelvis"] = [("rot", (1, 0, 0), -6 * cr)]
    return sp


def talk_spec(amp, nod=0.0):
    sp = idle_spec(0.4)
    sp["jaw"] = [("rot", (1, 0, 0), 24 * amp)]
    sp["head"] = [("rot", (1, 0, 0), -4 * amp + 2 * nod), ("rot", (0, 1, 0), 3 * nod)]
    return sp


POSES = {  # Standbild-Posen fuer Sprites
    "idle": lambda: idle_spec(0.0),
    "flex": lambda: flex_spec(1.0),
    "wave": lambda: wave_spec(0.5),
    "hop": lambda: hop_spec(1.0),
    "talk": lambda: talk_spec(0.85),
}
POSE_EXPR = {"idle": "neutral", "flex": "happy", "wave": "happy", "hop": "surprised", "talk": "neutral"}
SPRITES = [(p, POSE_EXPR[p]) for p in POSES] + [("idle", e) for e in ("happy", "angry", "surprised")]
EXPRESSIONS = ("neutral",) + KEYS
ACTION_FRAMES = {"idle": 48, "flex": 60, "wave": 60, "hop": 36, "talk": 48}


def build_actions(rig):
    rig.animation_data_create()
    acts = {}

    def new(name):
        a = bpy.data.actions.new(name)
        a.use_fake_user = True
        rig.animation_data.action = a
        acts[name] = a
        return a

    new("idle")
    for f in range(1, 49):
        apply_spec(rig, idle_spec(2 * math.pi * (f - 1) / 48), f)
    new("flex")
    for f, p in ((1, None), (14, 0.0), (24, 1.0), (34, 0.2), (44, 1.0), (52, 0.3), (60, None)):
        apply_spec(rig, idle_spec(0.0) if p is None else flex_spec(p), f)
    new("wave")
    keys = [(1, wave_spec(0, 0.0)), (10, wave_spec(0, 1.0))]
    for i, f in enumerate(range(16, 47, 6)):
        keys.append((f, wave_spec(1 if i % 2 == 0 else -1, 1.0)))
    keys += [(53, wave_spec(0, 0.6)), (60, wave_spec(0, 0.0))]
    for f, sp in keys:
        apply_spec(rig, sp, f)
    new("hop")
    for f, k in ((1, 0.0), (7, -1.0), (15, 1.0), (23, 0.0), (28, -0.5), (36, 0.0)):
        apply_spec(rig, hop_spec(k), f)
    new("talk")
    amps = [0, .8, .3, 1.0, .4, .9, .1, .7, .0, .6, .95, .2, 0, .85, .35, .6]
    for i, a in enumerate(amps):
        apply_spec(rig, talk_spec(a, math.sin(i * 0.8)), 1 + i * 3)
    apply_spec(rig, talk_spec(0, math.sin(len(amps) * 0.8)), 49)
    rig.animation_data.action = None
    return acts


def apply_expression(expr):
    for ob in S["face"]:
        for kb in ob.data.shape_keys.key_blocks[1:]:
            kb.value = 1.0 if kb.name == expr else 0.0


# ----------------------------------------------------------------- Skin -> Figur
def build_figure():
    sk = S["skin"]
    H = sk["head"]["radii"]
    HC = Vector((0.0, -0.05, 3.1))
    sn = sk["snout"]
    OL = 0.032  # Standard-Outline-Staerke (Welteinheiten)
    body = sk["body"]
    cs, ds, as_ = body["chest"], body["delt"], body["arm"]

    # --- Koerper
    blob("pelvis", (0, 0.0, 1.0), (0.64, 0.46, 0.36), "pelvis", M("fur"), ol=OL)
    blob("torso", (0, 0.05, 1.82), (0.98 * cs, 0.54, 0.95), "torso", M("fur"), taper=("z", 0.05, 0.38), segs=(28, 16), ol=OL)
    blob("front_plate", (0, -0.26, 1.86), (0.72 * cs, 0.32, 0.8), "torso", M("torso_front"), taper=("z", 0.0, 0.3), ol=0.02)
    pair("pec", (0.47 * cs, -0.50, 2.14), (0.48 * cs, 0.27, 0.33), "torso", M("torso_front"), rot=(8, 0, -10), ol=0.02)
    for row, z in enumerate((1.86, 1.62, 1.38)):
        pair("abs%d" % row, (0.20, -0.58 + 0.015 * row, z), (0.19, 0.11, 0.125), "torso", M("torso_front"), ol=0.014)
    pair("trap", (0.52, 0.0, 2.62), (0.56, 0.36, 0.28), "torso", M("fur"), rot=(0, -28, 0), ol=OL)
    pair("lat", (0.84, 0.0, 1.8), (0.28, 0.36, 0.62), "torso", M("fur"), rot=(0, 6, 0), ol=OL)
    blob("neck", (0, -0.02, 2.72), (0.46, 0.40, 0.34), "neck", M("neck"), ol=OL)

    # --- Arme
    pair("delt", (1.12, 0.0, 2.30), (0.46 * ds, 0.45 * ds, 0.46 * ds), "upper_arm.{s}", M("fur"), ol=OL)
    pair("uarm", (1.14, 0.0, 1.95), (0.36 * as_, 0.36 * as_, 0.62), "upper_arm.{s}", M("fur"), rot=(0, -16, 0), ol=OL)
    pair("biceps", (1.17, -0.20, 2.0), (0.27 * as_, 0.25 * as_, 0.40), "upper_arm.{s}", M("fur"), rot=(0, -16, 0), ol=0.02)
    pair("forearm", (1.20, -0.05, 1.2), (0.35 * as_, 0.35 * as_, 0.52), "forearm.{s}", M("fur"), ol=OL)
    pair("fist", (1.17, -0.12, 0.72), (0.33, 0.35, 0.31), "hand.{s}", M("paw"), ol=OL)
    pair("knuckle_a", (1.30, -0.40, 0.66), (0.10, 0.10, 0.12), "hand.{s}", M("paw"), ol=0.014, segs=(12, 8))
    pair("knuckle_b", (1.10, -0.42, 0.66), (0.10, 0.10, 0.12), "hand.{s}", M("paw"), ol=0.014, segs=(12, 8))

    # --- Beine
    pair("thigh", (0.40, 0.0, 0.78), (0.38, 0.40, 0.44), "thigh.{s}", M("fur"), ol=OL)
    pair("shin", (0.40, -0.02, 0.32), (0.27, 0.29, 0.28), "shin.{s}", M("fur"), ol=OL)
    pair("paw", (0.41, -0.20, 0.11), (0.30, 0.40, 0.13), "shin.{s}", M("paw"), ol=OL)

    # --- Schwanz (Shiba: eingerollt, Dobermann: Stummel)
    tl = sk["tail"]
    pts = []
    n = 28
    for i in range(n):
        t = i / (n - 1)
        a = t * math.pi * 1.9 * tl["curl"]
        r = 0.26 * tl["curl"] * (1 - 0.3 * t)
        L = tl["length"]
        pts.append(Vector((0.0 + 0.0, 0.34 + 0.34 * t * L + r * math.sin(a) * 0.9,
                           1.0 + 0.32 * t * L + 0.24 * tl["curl"] * t + r * (1 - math.cos(a)) * 0.9)))
    tail = new_obj("tail", build_mesh("tail", tube_verts(pts, tl["radius"], ring=10, profile=0.35), tube_faces(n, 10)), [M("fur")])
    add_part(tail, "tail", OL)

    # --- Kopf
    head = blob("head", HC, H, "head", M("head"), segs=(36, 20), ol=OL)
    S["head_ob"] = head
    snout_c = Vector((0, HC.y - H[1] * 0.42 - sn["l"] * 0.62, HC.z - 0.19 * H[2]))
    sw, sl, sh = sn["w"], sn["l"], sn["h"]
    snout = blob("snout", snout_c, (sw, sl, sh), "head", M("muzzle"), taper=("-y", sn["taper"], 0.0), segs=(24, 14), ol=0.026)
    S["snout_ob"] = snout
    S["snout_c"] = snout_c
    tip_y = snout_c.y - sl * 0.90
    blob("nose", (0, tip_y, snout_c.z + sh * 0.32), (sn["nose_w"], 0.11, 0.092), "head", M("nose"), ol=0.016, segs=(16, 10))
    jaw = blob("jaw", (0, snout_c.y + 0.02, snout_c.z - sh * 0.78), (sw * 0.86, sl * 0.84, 0.10), "jaw", M("muzzle"),
               taper=("-y", sn["taper"], 0.0), ol=0.02, segs=(20, 12))
    blob("mouth_inside", (0, snout_c.y + 0.05, snout_c.z - sh * 0.62), (sw * 0.78, sl * 0.72, 0.075), "head", F("mouth_inside"), ol=0, sub=False, segs=(16, 10))
    blob("tongue", (0, snout_c.y + 0.0, snout_c.z - sh * 0.62), (sw * 0.5, sl * 0.55, 0.05), "jaw", M("tongue"), ol=0, sub=False, segs=(16, 10))

    # --- Ohren
    ea = sk["ears"]
    for side, g in (("L", 1), ("R", -1)):
        base = Vector((ea["x"] * g, HC.y + 0.02, HC.z + ea["z"]))
        rot = (ea["tilt_back"], ea["tilt_out"] * g * -1, 0)
        blob("ear." + side, base, (ea["w"], ea["thick"], ea["h"]), "ear." + side, M("ear"), rot=(rot[0], rot[1], 0),
             offset=(0, 0, ea["h"] * 0.85), taper=("z", ea["taper"], 0.0), segs=(20, 14), ol=0.026)
        blob("ear_inner." + side, base, (ea["w"] * 0.58, ea["thick"] * 0.6, ea["h"] * 0.74), "ear." + side, M("ear_inner"),
             rot=(rot[0], rot[1], 0), offset=(0, -ea["thick"] * 0.95, ea["h"] * 0.78), taper=("z", ea["taper"], 0.0),
             segs=(16, 12), ol=0.0)

    # --- Decals (Auge, Brauen, Markings, Mund) brauchen ausgewertete Geometrie
    bpy.context.view_layer.update()
    S["face"] = []
    ey = sk["eyes"]
    for side, g in (("L", 1), ("R", -1)):
        gx, gz = ey["x"] * g, HC.z + ey["dz"]
        rx, rz = ey["rx"], ey["rz"]
        elems = [
            dict(dx=0, dz=0, rx=rx * 1.22, rz=rz * 1.26, depth=0.020, lift=0.008),
            dict(dx=0, dz=0, rx=rx, rz=rz, depth=0.020, lift=0.016),
            dict(dx=0, dz=0, rx=rx * ey["pupil"], rz=rz * ey["pupil"] * 1.15, depth=0.016, lift=0.026),
            dict(dx=-0.30 * rx * g, dz=0.38 * rz, rx=rx * 0.26, rz=rz * 0.26, depth=0.01, lift=0.040),
            dict(dx=0.30 * rx * g, dz=-0.40 * rz, rx=rx * 0.13, rz=rz * 0.13, depth=0.01, lift=0.040),
        ]
        dec = Decal(head, gx, gz, elems)

        def mk(mode, g=g, rx=rx, rz=rz, ey=ey):
            def lid(inner, outer, u, ring):
                t = max(-1.0, min(1.0, u * g / rx))
                return rz * ((inner + (outer - inner) * (t + 1) / 2) + (0.12 if ring else 0.0))

            def fn(u, v, ei):
                ring = ei == 0
                if mode == "neutral":
                    top = lid(ey["lid_in"], ey["lid_out"], u, ring)
                    return u, (min(v, top) if v > 0 else v)
                if mode == "angry":
                    top = lid(0.0, 0.5, u, ring)
                    return u, (min(v, top) if v > 0 else v)
                if mode == "surprised":
                    return u * 1.2, v * 1.25
                if mode == "happy":   # geschlossener ^-Bogen, nur der dunkle Ring bleibt sichtbar
                    if ei != 0:
                        return None
                    t = max(0.0, 1 - (u / (rx * 1.22)) ** 2)
                    return u * 1.05, v * 0.30 + 0.05 * t - 0.012
            return fn

        ob = dec.make("eye." + side, [F("eye_ring"), F("eye_iris"), F("pupil"), F("shine")], mk("neutral"))
        # Materialindex: Elemente 0..2 je eigenes Material, 3+4 = Glanzlicht
        nf = len(dec.faces)
        for i, p in enumerate(ob.data.polygons):
            p.material_index = min(i // nf, 3)
        add_shape_keys(ob, {"happy": dec.verts(mk("happy")), "angry": dec.verts(mk("angry")), "surprised": dec.verts(mk("surprised"))})
        add_part(ob, "head", 0)
        S["face"].append(ob)

        # Braue
        br = sk["brow"]
        cz = gz + rz * 1.35 + br["dz"]
        N = 14
        w = br["len"] / 2

        def curve(slope, dz, arch, g=g, gx=gx, cz=cz, w=w):
            pts = []
            for i in range(N):
                u = -w + 2 * w * i / (N - 1)
                q = u * g / w
                z = cz + dz + slope * q + arch * (1 - (u / w) ** 2)
                p, nn = surf_pn(head, gx + u, z)
                pts.append(p + nn * 0.02)
            return pts

        th = br["thick"]
        base = tube_verts(curve(br["slope"], 0.0, 0.015), th)
        bob = new_obj("brow." + side, build_mesh("brow." + side, base, tube_faces(N)), [F(br["color"])])
        add_shape_keys(bob, {
            "happy": tube_verts(curve(-0.01, 0.015, 0.045), th * 0.9),
            "angry": tube_verts(curve(0.085, -0.035, 0.0), th * 1.25),
            "surprised": tube_verts(curve(0.0, 0.09, 0.04), th * 0.9),
        })
        add_part(bob, "head", 0)
        S["face"].append(bob)

    # Markings
    for mk_ in sk["markings"]:
        surf = head if mk_["on"] == "head" else snout
        base_z = HC.z if mk_["on"] == "head" else snout_c.z
        for side, g in (("L", 1), ("R", -1)) if mk_.get("mirror") else (("C", 1),):
            elems = [dict(dx=0, dz=0, rx=mk_["rx"], rz=mk_["rz"], depth=0.01, lift=0.006)]
            dec = Decal(surf, mk_["x"] * g, base_z + mk_["dz"], elems, segs=(20, 10))
            ob = dec.make("mark.%s.%s" % (mk_["name"], side), [M(mk_["color"])])
            add_part(ob, "head", 0)

    # Mund (Linie auf der Schnauze, Shape Keys fuer Ausdruecke)
    mw_ = sw * 0.92
    mz0 = snout_c.z - sh * 0.46
    NM = 22

    def mouth_pts(mode):
        pts = []
        for i in range(NM):
            t = i / (NM - 1)
            u = (t - 0.5) * 2
            if mode == "neutral":
                x, z = u * mw_, mz0 - 0.03 * (1 - abs(u)) + 0.03 * u * u
            elif mode == "happy":
                x, z = u * mw_ * 1.1, mz0 - 0.045 + 0.14 * u * u
            elif mode == "angry":
                x, z = u * mw_, mz0 - 0.02 - 0.07 * u * u
            else:
                a = 2 * math.pi * t + math.pi / 2
                x, z = 0.075 * math.cos(a), mz0 - 0.06 + 0.085 * math.sin(a)
            p, nn = surf_pn(snout, x, z)
            pts.append(p + nn * 0.012)
        return pts

    mob = new_obj("mouth", build_mesh("mouth", tube_verts(mouth_pts("neutral"), 0.017, ring=6), tube_faces(NM, 6)), [F("mouth_line")])
    add_shape_keys(mob, {k: tube_verts(mouth_pts(k), 0.017 if k != "surprised" else 0.021, ring=6) for k in KEYS})
    add_part(mob, "head", 0)
    S["face"].append(mob)

    # --- Accessoire: Goldkette
    if sk["accessories"].get("chain"):
        build_chain()


def build_chain():
    targets = [pt["ob"] for pt in PARTS if pt["ob"].name.split(".")[0] in ("torso", "pec", "trap", "neck", "front_plate")]
    dg_ = bpy.context.evaluated_depsgraph_get()

    def hit(x, z):
        best = None
        for ob in targets:
            h, loc, nor, _ = ob.ray_cast(Vector((x, -9, z)), Vector((0, 1, 0)), depsgraph=dg_)
            if h and (best is None or loc.y < best.y):
                best = loc
        return best

    path = []
    NS = 60
    for i in range(NS):
        t = i / (NS - 1)
        x = -0.78 + 1.56 * t
        q = abs(x) / 0.78
        z = 2.0 + 0.82 * (q ** 1.5)
        p = hit(x, z)
        if p is None:
            p = Vector((x, -0.2, z))
        path.append(p + Vector((0, -0.05, 0)))
    # Kette entlang des Pfads, gleichmaessig nach Bogenlaenge
    seg = [(path[i + 1] - path[i]).length for i in range(NS - 1)]
    total = sum(seg)
    link = 0.115
    count = int(total / link)
    verts, faces = [], []

    def point_at(s):
        acc = 0.0
        for i, l in enumerate(seg):
            if acc + l >= s:
                f = (s - acc) / l
                return path[i].lerp(path[i + 1], f), (path[i + 1] - path[i]).normalized()
            acc += l
        return path[-1], (path[-1] - path[-2]).normalized()

    for k in range(count):
        p, tan = point_at((k + 0.5) * total / count)
        nrm = Vector((0, -1, 0))
        u2 = nrm if k % 2 == 0 else tan.cross(nrm).normalized()
        n1 = tan.cross(u2).normalized()
        A, B, minor = 0.074, 0.056, 0.022
        base = len(verts)
        U, V = 12, 6
        for a in range(U):
            ang = 2 * math.pi * a / U
            cpt = p + tan * math.cos(ang) * A + u2 * math.sin(ang) * B
            T = (-tan * math.sin(ang) * A + u2 * math.cos(ang) * B).normalized()
            n2 = T.cross(n1).normalized()
            for b in range(V):
                bb = 2 * math.pi * b / V
                verts.append(cpt + (n1 * math.cos(bb) + n2 * math.sin(bb)) * minor)
        for a in range(U):
            for b in range(V):
                a2, b2 = (a + 1) % U, (b + 1) % V
                faces.append([base + a * V + b, base + a2 * V + b, base + a2 * V + b2, base + a * V + b2])
    ch = new_obj("chain", build_mesh("chain", verts, faces), [M("chain")])
    add_part(ch, "neck", 0.016)


def finalize_outlines():
    """Inverted Hull: gleiche Mesh-Daten, Displace entlang der Normalen, nur Rueckseiten sichtbar."""
    om = outline_mat()
    for pt in list(PARTS):
        if pt["ol"] <= 0:
            continue
        src = pt["ob"]
        ob = bpy.data.objects.new(src.name + ".ol", src.data)
        S["coll"].objects.link(ob)
        for m in src.modifiers:
            if m.type == "SUBSURF":
                add_subsurf(ob, m.levels, m.render_levels)
        d = ob.modifiers.new("Outline", "DISPLACE")
        d.direction, d.strength, d.mid_level = "NORMAL", pt["ol"], 0.0
        for slot in ob.material_slots:
            slot.link = "OBJECT"
            slot.material = om
        PARTS.append({"ob": ob, "bone": pt["bone"], "ol": 0, "is_ol": True})


# ----------------------------------------------------------------- Szene, Render
def setup_stage():
    sc = S["scene"]
    w = sc.world
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[1].default_value = 0.0
    cam_d = bpy.data.cameras.new("Cam")
    cam_d.type = "ORTHO"
    cam_d.ortho_scale = 5.2
    cam_d.sensor_fit = "VERTICAL"
    cam = bpy.data.objects.new("Cam", cam_d)
    S["coll"].objects.link(cam)
    sc.camera = cam
    r = sc.render
    r.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.use_denoising = False
    sc.cycles.max_bounces = 2
    sc.cycles.transparent_max_bounces = 16
    sc.cycles.filter_width = 1.3
    r.film_transparent = True
    r.image_settings.file_format = "PNG"
    r.image_settings.color_mode = "RGBA"
    r.image_settings.color_depth = "8"
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    S["cam"] = cam


def aim_camera(cx, cz, scale, az=8, el=5, dist=30):
    cam = S["cam"]
    azr, elr = math.radians(az), math.radians(el)
    target = Vector((cx, 0, cz))
    cam.location = target + Vector((math.sin(azr) * dist * math.cos(elr), -math.cos(azr) * dist * math.cos(elr), math.sin(elr) * dist))
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam.data.ortho_scale = scale
    cam.data.clip_end = 200


def render_png(path, w, h, samples):
    sc = S["scene"]
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = w, h, 100
    sc.cycles.samples = samples
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


def load_rgba(path):
    img = bpy.data.images.load(path)
    img.colorspace_settings.name = "Non-Color"
    img.alpha_mode = "CHANNEL_PACKED"
    w, h = img.size
    a = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(a)
    bpy.data.images.remove(img)
    return a.reshape(h, w, 4)


def save_rgba(arr, path, alpha=True):
    h, w = arr.shape[:2]
    img = bpy.data.images.new("fd_out", w, h, alpha=alpha)
    img.colorspace_settings.name = "Non-Color"
    img.alpha_mode = "CHANNEL_PACKED"
    img.pixels.foreach_set(np.ascontiguousarray(arr, dtype=np.float32).ravel())
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)


def dilate(mask, r):
    m = mask.copy()
    for i in range(r):
        p = np.pad(m, 1)
        c = np.maximum.reduce([p[1:-1, 1:-1], p[:-2, 1:-1], p[2:, 1:-1], p[1:-1, :-2], p[1:-1, 2:]])
        if i % 2:
            c = np.maximum.reduce([c, p[:-2, :-2], p[:-2, 2:], p[2:, :-2], p[2:, 2:]])
        m = c
    return m


def boxblur(a, r):
    if r < 1:
        return a
    for axis in (0, 1):
        k = 2 * r + 1
        p = np.pad(a, [(r, r) if i == axis else (0, 0) for i in range(2)], mode="edge")
        cs = np.cumsum(p, axis=axis, dtype=np.float64)
        z = np.zeros_like(np.take(cs, [0], axis=axis))
        cs = np.concatenate([z, cs], axis=axis)
        n = a.shape[axis]
        a = (np.take(cs, range(k, k + n), axis=axis) - np.take(cs, range(0, n), axis=axis)) / k
    return a.astype(np.float32)


def add_aura(rgba, width_px, color):
    """Aura-Ring: dilatierte, leicht weichgezeichnete Alpha-Maske hinter der Figur."""
    a = rgba[..., 3]
    ring = boxblur(dilate((a > 0.02).astype(np.float32), width_px), max(1, width_px // 12))
    ring = np.clip(ring * 1.25, 0, 1)
    col = srgb(color)
    out_a = a + ring * (1 - a)
    out = np.zeros_like(rgba)
    safe = np.maximum(out_a, 1e-6)[..., None]
    out[..., :3] = (rgba[..., :3] * a[..., None] + col * (ring * (1 - a))[..., None]) / safe
    out[..., 3] = out_a
    return out


def background(w, h, bg):
    top, bot = srgb(bg["top"]), srgb(bg["bottom"])
    ty = np.linspace(0, 1, h, dtype=np.float32)[::-1][:, None, None]  # Bild ist unten-zuerst gespeichert
    img = top * (1 - ty) + bot * ty
    img = np.broadcast_to(img, (h, w, 3)).copy()
    gs = bg.get("glow_strength", 0.0)
    if gs > 0:
        cx, cy = bg["glow_center"]
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        d2 = ((xx / w - cx) ** 2 + ((h - 1 - yy) / h - cy) ** 2) / 0.12
        gl = np.exp(-d2)[..., None] * gs
        img = img * (1 - gl) + srgb(bg["glow"]) * gl
    rgba = np.ones((h, w, 4), dtype=np.float32)
    rgba[..., :3] = img
    return rgba


def over(fg, bg):
    a = fg[..., 3:4]
    out = bg.copy()
    out[..., :3] = fg[..., :3] * a + bg[..., :3] * (1 - a)
    out[..., 3] = 1.0
    return out


def shrink(a, f):
    h, w = a.shape[:2]
    h2, w2 = h // f, w // f
    return a[:h2 * f, :w2 * f].reshape(h2, f, w2, f, 4).mean(axis=(1, 3))


def render_sprite(rig, pose, expr, size, samples, path, aura=True):
    apply_spec(rig, POSES[pose]())
    apply_expression(expr)
    cx, cz, sc_ = (0.0, 2.3, 6.2) if not args.cam else [float(v) for v in args.cam.split(',')]
    aim_camera(cx, cz, sc_, az=14, el=6)
    w, h = size, size
    render_png(path, w, h, samples)
    if aura:
        arr = add_aura(load_rgba(path), max(2, int(args.size_ref * S["skin"]["aura"]["width"])), S["skin"]["aura"]["color"])
        save_rgba(arr, path)


def icon_spec():
    """Kompakte Bizeps-Pose: Ellbogen unten, Faeuste neben dem Kopf (Breite bleibt klein)."""
    sp = flex_spec(0.5)
    for side in ("L", "R"):
        g = sgn(side)
        sp["upper_arm." + side] = [("aim", (g * 0.55, -0.62, -0.40))]
        sp["forearm." + side] = [("aim", (g * 0.10, -0.55, 1.0))]
        sp["hand." + side] = [("aim", (g * 0.05, -0.75, 1.0))]
    return sp


def hide_for_icon(hide):
    for pt in PARTS:
        if pt["bone"] in ("root", "thigh.L", "thigh.R", "shin.L", "shin.R", "tail"):
            pt["ob"].hide_render = hide


def fit_camera(rig, az, el, margin=0.07):
    """Rendert klein, misst die Alpha-Huelle und zentriert/skaliert die Kamera so, dass nichts angeschnitten wird."""
    res, cx, cz, sc_ = 256, 0.0, 2.5, 8.0
    aim_camera(cx, cz, sc_, az=az, el=el)
    tmp = os.path.join(ICON_DIR, "_fit_%s.png" % S["skin"]["id"])
    render_png(tmp, res, res, 4)
    a = load_rgba(tmp)[..., 3] > 0.05
    os.remove(tmp)
    ys, xs = np.where(a)
    x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
    k = sc_ / res
    cx += ((x0 + x1) / 2 - res / 2) * k
    cz += ((y0 + y1) / 2 - res / 2) * k
    sc_ = max(x1 - x0, y1 - y0) * k / (1 - 2 * margin)
    return cx, cz, sc_


def render_icon(rig, size, samples):
    sk = S["skin"]
    fr = sk.get("icon", {})
    expr = fr.get("expr", "happy")
    apply_spec(rig, icon_spec())
    apply_expression(expr)
    hide_for_icon(True)
    az, el = 8, 4
    os.makedirs(ICON_DIR, exist_ok=True)
    cx, cz, sc_ = fit_camera(rig, az, el)
    aim_camera(cx, cz, sc_, az=az, el=el)
    tmp = os.path.join(ICON_DIR, "_tmp_%s.png" % sk["id"])
    render_png(tmp, size, size, samples)
    hide_for_icon(False)
    fg = add_aura(load_rgba(tmp), max(2, int(size * sk["aura"]["width"] * 0.6)), sk["aura"]["color"])
    os.remove(tmp)
    img = over(fg, background(size, size, sk["background"]))
    path = os.path.join(ICON_DIR, "%s-%d.png" % (sk["id"], size))
    save_rgba(img, path, alpha=False)
    meta = {"skin": sk["id"], "name": sk["name"], "placeholder_name": True, "size": size, "alpha": False,
            "pose": "icon (kompakte Bizeps-Pose, Beine ausgeblendet)", "expression": expr, "background": sk["background"],
            "aura": sk["aura"]["color"], "skeleton": SKELETON,
            "source": "brand/fitdogs/3d/build_dogs.py (Blender, Cycles CPU)",
            "framing": {"cx": round(cx, 4), "cz": round(cz, 4), "ortho_scale": round(sc_, 4), "auto_fit_margin": 0.07}}
    json.dump(meta, open(path[:-4] + ".meta.json", "w"), indent=2)
    print("[fitdogs] icon", path)
    return path


# ----------------------------------------------------------------- Export, Manifest
def export_glb(rig, acts, path):
    sc = S["scene"]
    set_look("pbr")
    for ob in sc.objects:
        ob.select_set(ob.type in ("MESH", "ARMATURE") and not ob.name.endswith(".ol"))
    rig.animation_data.action = None
    for name, act in acts.items():
        tr = rig.animation_data.nla_tracks.new()
        tr.name = name
        tr.strips.new(name, 1, act)
    bpy.ops.export_scene.gltf(
        filepath=path, export_format="GLB", use_selection=True,
        export_apply=True, export_animations=True, export_animation_mode="NLA_TRACKS",
        export_morph=True, export_morph_normal=False, export_skins=True,
        export_yup=True, export_texcoords=False, export_normals=True,
        export_draco_mesh_compression_enable=False,
    )
    for tr in list(rig.animation_data.nla_tracks):
        rig.animation_data.nla_tracks.remove(tr)
    set_look("toon")
    print("[fitdogs] glb", path, os.path.getsize(path))


def manifest(rig, acts):
    skin = S["skin"]
    bones = {n: {"parent": p, "head": [round(c, 5) for c in h], "tail": [round(c, 5) for c in t]} for n, (h, t, p) in BONES.items()}
    actions = {}
    for n, a in acts.items():
        actions[n] = {"frames": [int(a.frame_range[0]), int(a.frame_range[1])],
                      "fcurves": sorted("%s[%d]" % (fc.data_path, fc.array_index) for fc in a.fcurves)}
    shape = {}
    for ob in S["face"]:
        shape[ob.name] = [k.name for k in ob.data.shape_keys.key_blocks]
    mats = {}
    for m in bpy.data.materials:
        if m.name.startswith(("toon_", "flat_")):
            mats[m.name] = "#" + m.name.split("_", 1)[1]
    return {"skeleton": SKELETON, "skin": skin["id"], "name": skin["name"], "placeholder_name": True,
            "bones": bones, "actions": actions, "shape_keys": shape,
            "expressions": list(EXPRESSIONS), "palette": skin["palette"], "material_colors": mats,
            "objects": sorted(ob.name for ob in bpy.data.objects if ob.type == "MESH" and not ob.name.endswith(".ol"))}


# ----------------------------------------------------------------- main
def run_skin(skin_id):
    path = os.path.join(args.skins_dir, skin_id + ".json")
    S.clear()
    reset_scene()
    S["skin"] = json.load(open(path))
    assert S["skin"]["id"] == skin_id
    os.makedirs(OUT, exist_ok=True)
    build_figure()
    finalize_outlines()
    rig = build_rig()
    setup_stage()
    acts = build_actions(rig)
    # Standardzustand im .blend: idle + neutral
    rig.animation_data.action = acts["idle"]
    apply_spec(rig, idle_spec(0.0))
    apply_expression("neutral")
    sc = S["scene"]
    sc.frame_start, sc.frame_end, sc.render.fps = 1, 48, 24
    sid = skin_id
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, sid + ".blend"))
    print("[fitdogs] saved", sid + ".blend")
    export_glb(rig, acts, os.path.join(OUT, sid + ".glb"))
    json.dump(manifest(rig, acts), open(os.path.join(OUT, sid + ".manifest.json"), "w"), indent=1)
    rig.animation_data.action = None

    samples = args.samples
    aura = not args.no_aura
    if args.render == "preview":
        os.makedirs(os.path.join(OUT, "preview"), exist_ok=True)
        for pose, expr in (("idle", "neutral"), ("flex", "angry")):
            p = os.path.join(OUT, "preview", "%s-%s-%s.png" % (sid, pose, expr))
            render_sprite(rig, pose, expr, 512, samples, p, aura)
            print("[fitdogs] render", p)
    if args.render == "all":
        sd = os.path.join(OUT, "sprites")
        os.makedirs(sd, exist_ok=True)
        done = {}
        for pose, expr in SPRITES:
            p = os.path.join(sd, "%s-mascot-%s-%s.png" % (sid, pose, expr))
            render_sprite(rig, pose, expr, args.size, samples, p, aura)
            done[(pose, expr)] = p
            print("[fitdogs] sprite", p)
        build_overview(sid, done)
    if args.render in ("all", "icons"):
        os.makedirs(ICON_DIR, exist_ok=True)
        rig.pose.bones  # noqa
        render_icon(rig, args.icon_size, samples)


def build_overview(sid, done):
    bg_spec = S["skin"]["background"]
    thumbs = {k: load_rgba(p) for k, p in done.items()}
    h, w = next(iter(thumbs.values())).shape[:2]
    f = max(1, h // 384)
    thumbs = {k: shrink(v, f) for k, v in thumbs.items()}
    th, tw = next(iter(thumbs.values())).shape[:2]
    row1 = [(p, POSE_EXPR[p]) for p in POSES]
    row2 = [("idle", e) for e in EXPRESSIONS]
    W = tw * 5
    canvas = background(W, th * 2, bg_spec)
    for r, row in enumerate((row1, row2)):
        x0 = (W - tw * len(row)) // 2
        for i, key in enumerate(row):
            t = thumbs.get(key)
            if t is None:
                continue
            y1 = (1 - r) * th   # unten-zuerst: Zeile 0 (oben) liegt im oberen Bildteil = hohe y
            sub = canvas[y1:y1 + th, x0 + i * tw:x0 + (i + 1) * tw]
            canvas[y1:y1 + th, x0 + i * tw:x0 + (i + 1) * tw] = over(t, sub)
    p = os.path.join(OUT, "%s-overview.png" % sid)
    save_rgba(canvas, p, alpha=False)
    print("[fitdogs] overview", p)


args.size_ref = args.size
skins = sorted(f[:-5] for f in os.listdir(args.skins_dir) if f.endswith(".json")) if args.skin == "all" else [args.skin]
for sid in skins:
    run_skin(sid)
print("[fitdogs] done")
