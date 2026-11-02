"""FitDogs als Tracing-3D: Die Teilebilder der Zeichnung (dist/2d/<skin>/parts) werden zu aufgeblasenen 3D-Volumen.

Aufruf (Blender 4.0, Cycles CPU, Ausgabe wie render_2d.py: PNG RGBA je Frame):
  blender -b -P brand/fitdogs/3d/build_traced.py -- --skin shiba|dobermann|all --out brand/fitdogs/dist/3d_traced \
      [--render none|preview|all] [--samples N] [--depth 0.25] [--size 768] [--cam front,q30,q-30,side,back,turntable,turntable360] \
      [--action idle,hop,wave,flex,talk|all] [--action-stride N] [--frames 36] [--shade 0..1]
  blender -b <skin>.blend -P brand/fitdogs/3d/build_traced.py -- --check     # gibt Mesh-Kennzahlen als JSON aus

Ansatz je Teil: Alpha -> Kontur (cv2, vereinfacht) -> gefuelltes Dreiecksnetz (Delaunay mit Randringen) -> Tiefe aus der
geglaetteten Distanz zum Rand (runde Form, am Rand z=0) -> Rueckseite gespiegelt, am Rand verschweisst. Die Vorderseite
bekommt das Teilebild planar von vorn (UV = Bildkoordinaten). Teile liegen in Zeichenreihenfolge auf der Oberflaeche der
darunterliegenden Teile (Arme ueber Torso), damit die Ueberlappungen von vorn wie in der Zeichnung aussehen.
Rueckseite und Tiefe sind ERFUNDEN (Rueckseite = verwischte, abgedunkelte Vorderseite)."""
import argparse
import importlib.util
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
import cv2
import numpy as np
from scipy import ndimage
from scipy.spatial import Delaunay, cKDTree

try:
    HERE = Path(__file__).resolve().parent
except NameError:  # pragma: no cover
    HERE = Path(sys.argv[sys.argv.index("-P") + 1]).resolve().parent if "-P" in sys.argv else Path.cwd()
ROOT = HERE.parent  # brand/fitdogs
SKINS = ("shiba", "dobermann")
FIG_H = 1.8  # Figurenhoehe in Metern (Freisteller-Hoehe)
PAD = 4
EPS = 4.0  # Abstand eines Teils zur Oberflaeche darunter (px)
ALL_CAMS = ("front", "q30", "q-30", "side", "turntable")
ALL_ACTIONS = ("idle", "hop", "wave", "flex", "talk")
BACK_DARK = 0.55
CAM_ANGLES = {"q30": 30.0, "q-30": -30.0, "side": 90.0, "back": 180.0}


def load_module(name, path):
    sys.path.insert(0, str(ROOT / "tools"))
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def parse():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--skin", default="all")
    ap.add_argument("--out", default=str(ROOT / "dist" / "3d_traced"))
    ap.add_argument("--parts", default=str(ROOT / "dist" / "2d"), help="Ordner mit <skin>/parts (split_parts.py)")
    ap.add_argument("--render", choices=("none", "preview", "all"), default="none")
    ap.add_argument("--samples", type=int, default=16)
    ap.add_argument("--depth", type=float, default=0.25, help="Halbdicke eines Teils = depth * Teilbreite (0.25 = rund wie ein Zylinder)")
    ap.add_argument("--size", type=int, default=768)
    ap.add_argument("--cam", default="", help="Komma-Liste: front,q30,q-30,side,back,turntable,turntable360")
    ap.add_argument("--action", default="", help="Komma-Liste oder all: rendert Frames der Aktion (Frontansicht)")
    ap.add_argument("--action-stride", type=int, default=1)
    ap.add_argument("--frames", type=int, default=36, help="Frames der Turntables")
    ap.add_argument("--turn", type=float, default=35.0, help="Winkelbereich des Turntables (Grad, +-)")
    ap.add_argument("--shade", type=float, default=0.0, help="0 = unshaded (exakte Farben); >0 dunkelt schraege Flaechen")
    ap.add_argument("--check", action="store_true")
    return ap.parse_args(argv)


# ---------------------------------------------------------------- Geometrie (numpy/cv2)
def resample_closed(poly, spacing):
    pts = []
    n = len(poly)
    for i in range(n):
        a, b = poly[i], poly[(i + 1) % n]
        seg = float(np.hypot(*(b - a)))
        k = max(1, int(math.ceil(seg / spacing)))
        for j in range(k):
            pts.append(a + (b - a) * (j / k))
    return np.array(pts, np.float64)


def contour_points(mask, spacing, eps, min_area=40):
    cnts, _ = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    out = []
    for c in cnts:
        if cv2.contourArea(c) < min_area:
            continue
        poly = cv2.approxPolyDP(c, eps, True)[:, 0, :].astype(np.float64)
        if len(poly) < 3:
            continue
        out.append(resample_closed(poly, spacing) + 0.5)  # Pixelmitte -> Bildkoordinate
    return out


def sample(arr, xs, ys):
    return ndimage.map_coordinates(arr, [np.clip(ys - 0.5, 0, arr.shape[0] - 1), np.clip(xs - 0.5, 0, arr.shape[1] - 1)],
                                   order=1, mode="nearest")


def load_part(skin, p, parts_root, tex_dir):
    img = cv2.imread(str(parts_root / skin / p["file"]), cv2.IMREAD_UNCHANGED)
    img = cv2.copyMakeBorder(img, PAD, PAD, PAD, PAD, cv2.BORDER_CONSTANT, value=(0, 0, 0, 0))
    alpha = img[..., 3]
    # Farben unter transparenten Pixeln auffuellen (keine dunklen Saeume bei linearer Filterung in fremden Viewern)
    idx = ndimage.distance_transform_edt(alpha == 0, return_distances=False, return_indices=True)
    bgr = img[..., :3][idx[0], idx[1]]
    front = np.dstack([bgr, alpha])
    # Rueckseite: verwischt (vereinfacht) und abgedunkelt
    f = bgr.astype(np.float32) * (alpha[..., None] / 255.0)
    a = alpha.astype(np.float32) / 255.0
    fb = cv2.GaussianBlur(f, (0, 0), 9)
    ab = cv2.GaussianBlur(a, (0, 0), 9)
    back_bgr = np.clip(fb / np.maximum(ab[..., None], 1e-3), 0, 255) * BACK_DARK
    back_bgr = np.where(ab[..., None] > 1e-3, back_bgr, bgr * BACK_DARK)
    back = np.dstack([back_bgr.astype(np.uint8), alpha])
    tex_dir.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(tex_dir / f"{p['name']}.png"), front)
    cv2.imwrite(str(tex_dir / f"{p['name']}_back.png"), back)
    off = (p["offset"][0] - PAD, p["offset"][1] - PAD)
    return alpha, off


def profile(t):
    return np.sin(t * math.pi / 2)


def build_surface(alpha, off, base_global, depth):
    """Netz fuer ein Teil in Bildkoordinaten des Teils."""
    h, w = alpha.shape
    mask = (alpha >= 10).astype(np.uint8)
    mask = cv2.dilate(mask, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    filled = np.zeros_like(mask)
    for c in cnts:
        if cv2.contourArea(c) >= 40:
            cv2.drawContours(filled, [c], -1, 1, -1)
    dt = cv2.distanceTransform(filled, cv2.DIST_L2, 5)
    dmax = float(dt.max())
    sig = max(3.0, 0.12 * dmax)
    num = ndimage.gaussian_filter(dt * filled, sig)
    den = ndimage.gaussian_filter(filled.astype(np.float32), sig)
    dts = (num / np.maximum(den, 1e-3)) * filled
    dsmax = float(dts.max())

    pts = list(contour_points(filled, 4.0, 0.6))
    for r, sp in ((2.0, 5.0), (5.0, 7.0), (10.0, 10.0)):
        if dmax > r + 2:
            pts += contour_points(dt > r, sp, 0.8)
    g = 14
    gy, gx = np.mgrid[g // 2:h:g, g // 2:w:g]
    sel = dt[gy, gx] > 15.0
    pts.append(np.stack([gx[sel] + 0.5, gy[sel] + 0.5], 1).astype(np.float64))
    P = np.concatenate(pts)
    keep = np.ones(len(P), bool)
    for i, j in cKDTree(P).query_pairs(1.2):
        keep[max(i, j)] = False
    P = P[keep]

    def inside(q):
        xi = np.clip(np.floor(q[:, 0]).astype(int), 0, w - 1)
        yi = np.clip(np.floor(q[:, 1]).astype(int), 0, h - 1)
        return filled[yi, xi] > 0

    for it in range(20):
        tri = Delaunay(P).simplices
        A, B, C = P[tri[:, 0]], P[tri[:, 1]], P[tri[:, 2]]
        ok = inside((A + B + C) / 3) & inside((A + B) / 2) & inside((B + C) / 2) & inside((C + A) / 2)
        tri = tri[ok]
        used = np.unique(tri)
        remap = -np.ones(len(P), int)
        remap[used] = np.arange(len(used))
        P = P[used]
        tri = remap[tri]
        e = np.sort(np.concatenate([tri[:, [0, 1]], tri[:, [1, 2]], tri[:, [2, 0]]]), axis=1)
        keys, cnt = np.unique(e, axis=0, return_counts=True)
        boundary = np.zeros(len(P), bool)
        boundary[keys[cnt == 1].ravel()] = True
        # Sehnen: Innenkante zwischen zwei Randvertices wuerde Vorder- und Rueckseite 4-fach verbinden -> Mittelpunkt einfuegen
        chord = keys[(cnt == 2) & boundary[keys[:, 0]] & boundary[keys[:, 1]]]
        if len(chord) == 0 or it == 19:
            break
        P = np.concatenate([P, (P[chord[:, 0]] + P[chord[:, 1]]) / 2])

    t = np.clip(sample(dts, P[:, 0], P[:, 1]) / max(dsmax, 1e-6), 0, 1)
    zmax = depth * 4.0 * dsmax
    zf = zmax * profile(t)
    zf[boundary] = 0.0
    rim = sample(base_global, P[:, 0] + off[0], P[:, 1] + off[1]) + EPS
    stats = {"verts": int(len(P)), "tris": int(len(tri)), "boundary_verts": int(boundary.sum()),
             "dmax_px": round(dmax, 1), "zmax_px": round(zmax, 1)}
    return P, tri, boundary, zf, rim, filled, dts, dsmax, zmax, stats


def paste_max(H, field, off):
    ox, oy = off
    h, w = field.shape
    x0, y0 = max(ox, 0), max(oy, 0)
    x1, y1 = min(ox + w, H.shape[1]), min(oy + h, H.shape[0])
    if x1 <= x0 or y1 <= y0:
        return
    H[y0:y1, x0:x1] = np.maximum(H[y0:y1, x0:x1], field[y0 - oy:y1 - oy, x0 - ox:x1 - ox])


def base_field(H):
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (85, 85))
    return cv2.GaussianBlur(cv2.dilate(H, k), (0, 0), 14)


# ---------------------------------------------------------------- Blender: Material, Mesh, Rig
def make_materials(name, front_png, back_png, shade):
    mats = {}
    for side, png in (("front", front_png), ("back", back_png)):
        img = bpy.data.images.load(str(png), check_existing=True)
        img.colorspace_settings.name = "sRGB"
        img.alpha_mode = "STRAIGHT"
        m = bpy.data.materials.new(f"{name}_{side}")  # Render: Emission, unshaded
        m.use_nodes = True
        nt = m.node_tree
        nt.nodes.clear()
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = img
        tex.interpolation = "Linear"
        tex.extension = "EXTEND"
        emi = nt.nodes.new("ShaderNodeEmission")
        tr = nt.nodes.new("ShaderNodeBsdfTransparent")
        mix = nt.nodes.new("ShaderNodeMixShader")
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        col = tex.outputs["Color"]
        if shade > 0:  # 1 - shade*(1-|n.front|)^2
            geo = nt.nodes.new("ShaderNodeNewGeometry")
            dot = nt.nodes.new("ShaderNodeVectorMath")
            dot.operation = "DOT_PRODUCT"
            dot.inputs[1].default_value = (0, -1, 0)
            ab = nt.nodes.new("ShaderNodeMath")
            ab.operation = "ABSOLUTE"
            inv = nt.nodes.new("ShaderNodeMath")
            inv.operation = "SUBTRACT"
            inv.inputs[0].default_value = 1.0
            sq = nt.nodes.new("ShaderNodeMath")
            sq.operation = "POWER"
            sq.inputs[1].default_value = 2.0
            fac = nt.nodes.new("ShaderNodeMath")
            fac.operation = "MULTIPLY_ADD"
            fac.inputs[1].default_value = -shade
            fac.inputs[2].default_value = 1.0
            mul = nt.nodes.new("ShaderNodeMixRGB")
            mul.blend_type = "MULTIPLY"
            mul.inputs[0].default_value = 1.0
            nt.links.new(geo.outputs["Normal"], dot.inputs[0])
            nt.links.new(dot.outputs["Value"], ab.inputs[0])
            nt.links.new(ab.outputs[0], inv.inputs[1])
            nt.links.new(inv.outputs[0], sq.inputs[0])
            nt.links.new(sq.outputs[0], fac.inputs[0])
            nt.links.new(tex.outputs["Color"], mul.inputs[1])
            nt.links.new(fac.outputs[0], mul.inputs[2])
            col = mul.outputs[0]
        nt.links.new(col, emi.inputs["Color"])
        nt.links.new(tr.outputs[0], mix.inputs[1])
        nt.links.new(emi.outputs[0], mix.inputs[2])
        nt.links.new(tex.outputs["Alpha"], mix.inputs[0])
        nt.links.new(mix.outputs[0], out.inputs["Surface"])
        p = bpy.data.materials.new(f"{name}_{side}_pbr")  # Export: PBR, roughness 1, kein Specular
        p.use_nodes = True
        pn = p.node_tree
        pn.nodes.clear()
        pt = pn.nodes.new("ShaderNodeTexImage")
        pt.image = img
        pt.extension = "EXTEND"
        bsdf = pn.nodes.new("ShaderNodeBsdfPrincipled")
        bsdf.inputs["Roughness"].default_value = 1.0
        bsdf.inputs["Metallic"].default_value = 0.0
        bsdf.inputs["Specular IOR Level"].default_value = 0.0
        po = pn.nodes.new("ShaderNodeOutputMaterial")
        pn.links.new(pt.outputs["Color"], bsdf.inputs["Base Color"])
        pn.links.new(pt.outputs["Alpha"], bsdf.inputs["Alpha"])
        pn.links.new(bsdf.outputs[0], po.inputs["Surface"])
        p.blend_method = "CLIP"
        p.alpha_threshold = 0.5
        p.use_fake_user = True
        mats[side] = (m, p)
    return mats


def to_world(px, py, s, root_x, cut_h):
    return (px - root_x) * s, (cut_h - py) * s


def build_skin(skin, args, anims_mod, anims, out_dir):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    parts_root = Path(args.parts)
    meta = json.loads((parts_root / skin / "parts.json").read_text())
    cut_w, cut_h = meta["size"]
    s = FIG_H / cut_h
    root_x = meta["root"]["pivot"][0]
    tex_dir = out_dir / skin / "tex"
    H = np.zeros((cut_h, cut_w), np.float32)
    coll = bpy.context.scene.collection

    arm_data = bpy.data.armatures.new(f"{skin}_rig")
    arm_obj = bpy.data.objects.new(f"{skin}_armature", arm_data)
    coll.objects.link(arm_obj)
    bpy.context.view_layer.objects.active = arm_obj
    arm_obj.select_set(True)
    bpy.ops.object.mode_set(mode="EDIT")
    for name, parent, pv in [("root", None, meta["root"]["pivot"])] + [(p["name"], p["parent"], p["pivot"]) for p in meta["parts"]]:
        eb = arm_data.edit_bones.new(name)
        x, z = to_world(pv[0], pv[1], s, root_x, cut_h)
        eb.head = (x, 0.0, z)
        eb.tail = (x, 0.05, z)  # Bone zeigt entlang +Y (Tiefe): lokale Y-Rotation = Drehung der Ansicht
        eb.roll = 0.0
        if parent:
            eb.parent = arm_data.edit_bones[parent]
    bpy.ops.object.mode_set(mode="OBJECT")

    objs, part_stats = [], {}
    for p in sorted(meta["parts"], key=lambda q: q["order"]):
        alpha, off = load_part(skin, p, parts_root, tex_dir)
        base = base_field(H)
        P, tri, boundary, zf, rim, filled, dts, dsmax, zmax, st = build_surface(alpha, off, base, args.depth)
        h, w = alpha.shape
        gy, gx = np.mgrid[0:h, 0:w]
        base_img = ndimage.map_coordinates(base, [np.clip(gy + off[1], 0, cut_h - 1), np.clip(gx + off[0], 0, cut_w - 1)],
                                           order=1, mode="nearest")
        field = np.where(filled > 0, base_img + EPS + zmax * profile(np.clip(dts / max(dsmax, 1e-6), 0, 1)), 0).astype(np.float32)
        paste_max(H, field, off)  # Hoehenfeld fuer die naechsten Teile

        n = len(P)
        X, Z = to_world(P[:, 0] + off[0], P[:, 1] + off[1], s, root_x, cut_h)
        inner = ~boundary
        back_idx = np.arange(n)
        back_idx[inner] = n + np.arange(int(inner.sum()))
        verts = np.zeros((n + int(inner.sum()), 3))
        verts[:n] = np.stack([X, -(rim + zf) * s, Z], 1)
        verts[back_idx[inner]] = np.stack([X, -(rim - zf) * s, Z], 1)[inner]
        a, b, c = verts[tri[:, 0]], verts[tri[:, 1]], verts[tri[:, 2]]
        flip = np.cross(b - a, c - a)[:, 1] > 0  # Vorderseite: Normale zur Kamera (-Y)
        tf = tri.copy()
        tf[flip] = tf[flip][:, ::-1]
        tb = back_idx[tf][:, ::-1]
        faces = np.concatenate([tf, tb]).tolist()
        mesh = bpy.data.meshes.new(f"{skin}_{p['name']}")
        mesh.from_pydata(verts.tolist(), [], faces)
        mesh.update()
        invalid = mesh.validate(verbose=False)
        uv_xy = np.zeros((len(verts), 2))
        uv_xy[:n] = np.stack([P[:, 0] / w, 1 - P[:, 1] / h], 1)
        uv_xy[back_idx[inner]] = uv_xy[:n][inner]
        uvl = mesh.uv_layers.new(name="UVMap")
        loop_v = np.array([l.vertex_index for l in mesh.loops])
        uvl.data.foreach_set("uv", uv_xy[loop_v].ravel())
        nf = len(tf)
        mesh.polygons.foreach_set("material_index", np.concatenate([np.zeros(nf, int), np.ones(nf, int)]))
        mesh.polygons.foreach_set("use_smooth", np.ones(len(faces), bool))
        mats = make_materials(f"{skin}_{p['name']}", tex_dir / f"{p['name']}.png", tex_dir / f"{p['name']}_back.png", args.shade)
        mesh.materials.append(mats["front"][0])
        mesh.materials.append(mats["back"][0])
        obj = bpy.data.objects.new(f"{skin}_{p['name']}", mesh)
        coll.objects.link(obj)
        obj.parent = arm_obj
        obj.vertex_groups.new(name=p["name"]).add(list(range(len(verts))), 1.0, "REPLACE")
        obj.modifiers.new("Armature", "ARMATURE").object = arm_obj
        obj["part"] = p["name"]
        obj["render_front"], obj["render_back"] = mats["front"][0].name, mats["back"][0].name
        obj["pbr_front"], obj["pbr_back"] = mats["front"][1].name, mats["back"][1].name
        objs.append(obj)
        bm = bmesh.new()
        bm.from_mesh(mesh)
        part_stats[p["name"]] = {**st, "validate_changed": bool(invalid), "edges": len(bm.edges), "faces": len(faces), "verts_total": len(verts),
                                 "boundary_edges": sum(1 for e in bm.edges if len(e.link_faces) == 1),
                                 "nonmanifold_edges": sum(1 for e in bm.edges if len(e.link_faces) > 2)}
        bm.free()
    make_actions(arm_obj, anims_mod, anims)
    return arm_obj, objs, part_stats, dict(s=s, root_x=root_x, cut_w=cut_w, cut_h=cut_h)


def make_actions(arm_obj, mod, anims):
    fps = anims["fps"]
    bpy.context.scene.render.fps = fps
    bpy.context.view_layer.objects.active = arm_obj
    arm_obj.animation_data_create()
    for aname, act in anims["actions"].items():
        n = max(1, round(act["duration"] * fps))
        action = bpy.data.actions.new(aname)
        action.use_fake_user = True
        arm_obj.animation_data.action = action
        for i in range(n + 1):
            t, frame = i / fps, 1 + i
            for part, chans in act["tracks"].items():
                pb = arm_obj.pose.bones[part]
                pb.rotation_mode = "XYZ"
                for ch, keys in chans.items():
                    v = mod.eval_track(keys, t)
                    if ch == "rot":
                        pb.rotation_euler[1] = math.radians(v)
                        pb.keyframe_insert("rotation_euler", index=1, frame=frame)
                    elif ch == "tx":
                        pb.location[0] = v * FIG_H
                        pb.keyframe_insert("location", index=0, frame=frame)
                    elif ch == "ty":
                        pb.location[2] = -v * FIG_H
                        pb.keyframe_insert("location", index=2, frame=frame)
                    elif ch == "sx":
                        pb.scale[0] = v
                        pb.keyframe_insert("scale", index=0, frame=frame)
                    elif ch == "sy":
                        pb.scale[2] = v
                        pb.keyframe_insert("scale", index=2, frame=frame)
        for fc in action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"
        action.use_frame_range = True
        action.frame_start, action.frame_end = 1, n + 1
        action["loop"] = bool(act.get("loop"))
        action["duration"] = act["duration"]
        for pb in arm_obj.pose.bones:
            pb.rotation_euler, pb.location, pb.scale = (0, 0, 0), (0, 0, 0), (1, 1, 1)
    arm_obj.animation_data.action = None


def nla_tracks(arm_obj, on):
    """NLA-Spuren nur waehrend des glTF-Exports (sonst ueberlagern sich alle Aktionen beim Rendern)."""
    ad = arm_obj.animation_data
    if on:
        for a in bpy.data.actions:
            tr = ad.nla_tracks.new()
            tr.name = a.name
            tr.strips.new(a.name, 1, a).name = a.name
    else:
        for tr in list(ad.nla_tracks):
            ad.nla_tracks.remove(tr)


# ---------------------------------------------------------------- Render
def setup_render(size_xy, samples):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = False
    sc.cycles.max_bounces = 2
    sc.cycles.transparent_max_bounces = 64
    sc.cycles.filter_width = 1.0
    sc.render.film_transparent = True
    sc.render.resolution_x, sc.render.resolution_y = size_xy
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.render.image_settings.color_depth = "8"
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.view_settings.exposure = 0
    sc.view_settings.gamma = 1
    sc.display_settings.display_device = "sRGB"
    sc.render.dither_intensity = 0
    if sc.world is None:
        sc.world = bpy.data.worlds.new("w")
    sc.world.use_nodes = False
    sc.world.color = (0, 0, 0)


def get_camera():
    cam = bpy.data.objects.get("cam")
    if cam is None:
        cd = bpy.data.cameras.new("cam")
        cd.type = "ORTHO"
        cd.sensor_fit = "VERTICAL"
        cd.clip_start, cd.clip_end = 0.01, 100
        cam = bpy.data.objects.new("cam", cd)
        bpy.context.scene.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    return cam


def place_cam(cam, cx, cz, ortho, azimuth_deg=0.0, dist=8.0):
    a = math.radians(azimuth_deg)
    cam.data.ortho_scale = ortho
    cam.location = (cx + math.sin(a) * dist, -math.cos(a) * dist, cz)
    cam.rotation_euler = (math.pi / 2, 0, a)


def render_to(path):
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)


def set_pose(arm_obj, action, frame):
    arm_obj.animation_data.action = bpy.data.actions[action] if action else None
    if action is None:
        for pb in arm_obj.pose.bones:
            pb.rotation_euler, pb.location, pb.scale = (0, 0, 0), (0, 0, 0), (1, 1, 1)
    bpy.context.scene.frame_set(frame)
    bpy.context.view_layer.update()


def use_render_materials(objs, on=True):
    for ob in objs:
        k = "render" if on else "pbr"
        ob.data.materials[0] = bpy.data.materials[ob[f"{k}_front"]]
        ob.data.materials[1] = bpy.data.materials[ob[f"{k}_back"]]


def label(img, text):
    cv2.putText(img, text, (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (40, 40, 40), 2, cv2.LINE_AA)
    return img


def over_checker(png):
    h, w = png.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    bg = np.where((((yy // 16 + xx // 16) % 2) == 0)[..., None], 250.0, 228.0) * np.ones((h, w, 3))
    a = png[..., 3:4].astype(np.float32) / 255
    return (png[..., :3] * a + bg * (1 - a)).astype(np.uint8)


def render_skin(skin, args, arm_obj, info, anims_mod, anims, out_dir, cams, actions):
    s, root_x, cut_w, cut_h = info["s"], info["root_x"], info["cut_w"], info["cut_h"]
    size = args.size
    cam = get_camera()
    base = out_dir / skin
    fig_cx, fig_cz = (cut_w / 2 - root_x) * s, cut_h / 2 * s
    ortho_sq = 1.12 * max(cut_w, cut_h) * s
    for cname in cams:
        d = base / cname
        d.mkdir(parents=True, exist_ok=True)
        for old in d.glob("frame_*.png"):
            old.unlink()
        set_pose(arm_obj, None, 1)
        if cname == "front":  # exakt der Freisteller, gleiche Proportionen
            setup_render((max(1, round(size * cut_w / cut_h)), size), args.samples)
            place_cam(cam, fig_cx, fig_cz, cut_h * s)
            render_to(d / "frame_0001.png")
        elif cname in CAM_ANGLES:
            setup_render((size, size), args.samples)
            place_cam(cam, fig_cx, fig_cz, ortho_sq, CAM_ANGLES[cname])
            render_to(d / "frame_0001.png")
        elif cname in ("turntable", "turntable360"):
            setup_render((size, size), args.samples)
            n = args.frames
            for i in range(n):
                ang = args.turn * math.sin(2 * math.pi * i / n) if cname == "turntable" else 360.0 * i / n
                place_cam(cam, fig_cx, fig_cz, ortho_sq, ang)
                render_to(d / f"frame_{i + 1:04d}.png")
    if actions:  # Frontansicht, Einpassung wie render_2d.py (Vereinigung aller Posen, quadratisch)
        rig = anims_mod.Rig(skin, Path(args.parts))
        fr = anims_mod.framing(rig, anims, anims["fps"], size)
        k = fr["scale"]
        cpx, cpy = (size / 2 - fr["ox"]) / k, (size / 2 - fr["oy"]) / k
        for aname in actions:
            d = base / f"{aname}_front"
            d.mkdir(parents=True, exist_ok=True)
            for old in d.glob("frame_*.png"):
                old.unlink()
            setup_render((size, size), args.samples)
            place_cam(cam, (cpx - root_x) * s, (cut_h - cpy) * s, size / k * s)
            n = max(1, round(anims["actions"][aname]["duration"] * anims["fps"]))
            for i in range(0, n, max(1, args.action_stride)):
                set_pose(arm_obj, aname, 1 + i)
                render_to(d / f"frame_{i + 1:04d}.png")
            files = sorted(d.glob("frame_*.png"))
            pick = [files[j] for j in np.linspace(0, len(files) - 1, min(12, len(files))).round().astype(int)]
            tiles = [cv2.resize(label(over_checker(cv2.imread(str(f), cv2.IMREAD_UNCHANGED)), f"{aname} {f.stem[-4:]}"),
                                (256, 256), interpolation=cv2.INTER_AREA) for f in pick]
            while len(tiles) % 6:
                tiles.append(np.full_like(tiles[0], 235))
            cv2.imwrite(str(base / f"{skin}-{aname}-sheet.png"), np.vstack([np.hstack(tiles[r:r + 6]) for r in range(0, len(tiles), 6)]))
        set_pose(arm_obj, None, 1)


def overview(skin, base, names):
    tiles = []
    for n in names:
        f = base / n / "frame_0001.png"
        if not f.exists():
            continue
        im = cv2.imread(str(f), cv2.IMREAD_UNCHANGED)
        th = 420
        im = cv2.resize(im, (round(im.shape[1] * th / im.shape[0]), th), interpolation=cv2.INTER_AREA)
        t = label(over_checker(im), n + (" (erfunden)" if n == "back" else ""))
        tiles.append(t)
    if tiles:
        wmax = max(t.shape[1] for t in tiles)
        tiles = [cv2.copyMakeBorder(t, 0, 0, (wmax - t.shape[1]) // 2, wmax - t.shape[1] - (wmax - t.shape[1]) // 2, cv2.BORDER_CONSTANT, value=(235, 235, 235)) for t in tiles]
        cv2.imwrite(str(base / f"{skin}-overview.png"), np.hstack(tiles))


# ---------------------------------------------------------------- Export & Check
def mesh_report():
    rep = {}
    for ob in bpy.data.objects:
        if ob.type == "MESH":
            bm = bmesh.new()
            bm.from_mesh(ob.data)
            rep[ob.name] = {"edges": len(bm.edges), "faces": len(bm.faces),
                            "boundary_edges": sum(1 for e in bm.edges if len(e.link_faces) == 1),
                            "nonmanifold_edges": sum(1 for e in bm.edges if len(e.link_faces) > 2)}
            bm.free()
    return rep


def check():
    arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
    out = {"meshes": mesh_report(),
           "bones": [(b.name, b.parent.name if b.parent else None) for b in arm.data.bones],
           "actions": {a.name: {"frames": [a.frame_start, a.frame_end],
                                "fcurves": sorted(f"{f.data_path}[{f.array_index}]" for f in a.fcurves)} for a in bpy.data.actions}}
    print("TRACED_CHECK " + json.dumps(out))


def export(skin, args, arm_obj, objs, out_dir, info, part_stats):
    out_dir.mkdir(parents=True, exist_ok=True)
    blend = out_dir / f"{skin}.blend"
    use_render_materials(objs, True)
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    use_render_materials(objs, False)
    arm_obj.animation_data.action = None
    nla_tracks(arm_obj, True)
    bpy.ops.object.select_all(action="DESELECT")
    glb = out_dir / f"{skin}.glb"
    bpy.ops.export_scene.gltf(filepath=str(glb), export_format="GLB", export_animations=True,
                              export_animation_mode="NLA_TRACKS", export_yup=True, export_cameras=False, export_lights=False)
    nla_tracks(arm_obj, False)
    use_render_materials(objs, True)
    manifest = {
        "skin": skin, "method": "tracing-3d", "depth": args.depth, "fig_h_m": FIG_H, "px_to_m": info["s"],
        "back_side": "erfunden: verwischte, abgedunkelte Vorderseite",
        "depth_profile": "erfunden: aufgeblasen nach Distanz zum Rand",
        "bones": [{"name": b.name, "parent": b.parent.name if b.parent else None, "head": [round(v, 5) for v in b.head_local]}
                  for b in arm_obj.data.bones],
        "actions": {a.name: {"frames": [int(a.frame_start), int(a.frame_end)], "fps": bpy.context.scene.render.fps,
                             "loop": bool(a.get("loop")), "fcurves": len(a.fcurves)} for a in bpy.data.actions},
        "parts": part_stats, "mesh_check": mesh_report(), "glb": glb.name, "blend": blend.name,
    }
    (out_dir / f"{skin}.manifest.json").write_text(json.dumps(manifest, indent=1))
    return glb


def main():
    args = parse()
    if args.check:
        return check()
    anims_mod = load_module("render_2d", ROOT / "2d" / "render_2d.py")
    anims = json.loads((ROOT / "2d" / "anims.json").read_text())
    skins = SKINS if args.skin == "all" else (args.skin,)
    top = Path(args.out)
    if args.render == "all":
        cams_default, actions_default = ALL_CAMS, ALL_ACTIONS
    elif args.render == "preview":
        cams_default, actions_default = ("front", "q30", "q-30", "side"), ()
    else:
        cams_default, actions_default = (), ()
    cams = tuple(c for c in args.cam.split(",") if c) or cams_default
    actions = ALL_ACTIONS if args.action == "all" else (tuple(a for a in args.action.split(",") if a) or actions_default)
    for skin in skins:
        out_dir = top
        arm_obj, objs, stats, info = build_skin(skin, args, anims_mod, anims, out_dir)
        if cams or actions:
            render_skin(skin, args, arm_obj, info, anims_mod, anims, out_dir, cams, actions)
            if not args.cam and args.render != "none":
                if args.render == "all" and "back" not in cams:
                    render_skin(skin, args, arm_obj, info, anims_mod, anims, out_dir, ("back",), ())
                overview(skin, out_dir / skin, ["front", "q-30", "q30", "side"] + (["back"] if args.render == "all" else []))
        glb = export(skin, args, arm_obj, objs, out_dir, info, stats)
        print(f"{skin}: {glb}")


main()
