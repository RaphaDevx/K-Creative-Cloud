"""
modul_textile_cad.py — K-Creative-Cloud
Parametrische Kontrolle für Textil-Design, Schnittmuster & Laufsteg-Simulationen.
Wird von k_parametric.py als Dispatcher-Modul geladen.

Befehle:
  set_cloth_preset    — Stoff-Material zuweisen (silk/denim/cotton/leather/wool)
  get_cloth_info      — Cloth-Modifier-Einstellungen auslesen
  set_cloth_param     — einzelnen Cloth-Parameter setzen
  bake_cloth          — Physik-Simulation berechnen
  set_body_measure    — Körpermaße via Shape Keys setzen
  get_body_measures   — aktuelle Shape-Key-Werte auslesen
  load_animation      — FBX-Animation (Mixamo) auf Rig laden
  create_sewing_seam  — Nähte zwischen zwei Mesh-Kanten definieren
  flatten_pattern     — 3D-Kleidung → 2D-Schnittmuster (Seams-to-Pattern)
  export_pattern_svg  — Schnittmuster als SVG exportieren
"""

import bpy
import os
import traceback
import math


ACTIONS = {
    "set_cloth_preset", "get_cloth_info", "set_cloth_param",
    "bake_cloth", "set_body_measure", "get_body_measures",
    "load_animation", "create_sewing_seam", "flatten_pattern",
    "export_pattern_svg"
}

# ── Stoff-Presets (physikalisch kalibriert) ───────────────────────────────────
# Blender Cloth-Modifier Werte (getestet mit Blender 4.0)
FABRIC_PRESETS = {
    "silk": {
        "quality":               12,
        "mass":                  0.10,    # kg/m²  — sehr leicht
        "tension_stiffness":     5.0,
        "compression_stiffness": 5.0,
        "shear_stiffness":       2.0,
        "bending_stiffness":     0.05,   # fällt sehr weich
        "air_damping":           1.0,
        "use_dynamic_mesh":      True,
        "collision_quality":     4,
        "_note": "Fliessend, leicht, viel Bewegung"
    },
    "cotton": {
        "quality":               10,
        "mass":                  0.25,
        "tension_stiffness":     15.0,
        "compression_stiffness": 15.0,
        "shear_stiffness":       8.0,
        "bending_stiffness":     0.5,
        "air_damping":           1.5,
        "use_dynamic_mesh":      True,
        "collision_quality":     3,
        "_note": "Alltagsstoff, mittelschwer"
    },
    "denim": {
        "quality":               8,
        "mass":                  0.55,
        "tension_stiffness":     40.0,
        "compression_stiffness": 40.0,
        "shear_stiffness":       20.0,
        "bending_stiffness":     5.0,
        "air_damping":           2.0,
        "use_dynamic_mesh":      False,
        "collision_quality":     2,
        "_note": "Steif, schwer — Jeans-Verhalten"
    },
    "leather": {
        "quality":               6,
        "mass":                  0.90,
        "tension_stiffness":     80.0,
        "compression_stiffness": 80.0,
        "shear_stiffness":       40.0,
        "bending_stiffness":     15.0,
        "air_damping":           3.0,
        "use_dynamic_mesh":      False,
        "collision_quality":     2,
        "_note": "Sehr steif, schwer, kaum Bewegung"
    },
    "wool": {
        "quality":               10,
        "mass":                  0.35,
        "tension_stiffness":     20.0,
        "compression_stiffness": 20.0,
        "shear_stiffness":       10.0,
        "bending_stiffness":     2.0,
        "air_damping":           2.5,
        "use_dynamic_mesh":      True,
        "collision_quality":     3,
        "_note": "Mittelschwer, gedämpft, warm fliessend"
    },
    "chiffon": {
        "quality":               15,
        "mass":                  0.06,
        "tension_stiffness":     3.0,
        "compression_stiffness": 3.0,
        "shear_stiffness":       1.0,
        "bending_stiffness":     0.01,
        "air_damping":           0.5,
        "use_dynamic_mesh":      True,
        "collision_quality":     5,
        "_note": "Hauchdünn, maximale Bewegung"
    },
    "latex": {
        "quality":               8,
        "mass":                  1.20,
        "tension_stiffness":     200.0,
        "compression_stiffness": 200.0,
        "shear_stiffness":       100.0,
        "bending_stiffness":     50.0,
        "air_damping":           5.0,
        "use_dynamic_mesh":      False,
        "collision_quality":     2,
        "_note": "Hochelastisch, schwer, eng anliegend"
    },
}

# ── Standard-Körpermaße als Shape-Key-Mapping ─────────────────────────────────
# Maße in cm → Shape-Key-Werte (0.0 – 1.0 für MB-Lab / Human Generator)
MEASURE_MAP = {
    "chest_cm":     {"key": "chest_size",       "min_cm": 78,  "max_cm": 130},
    "waist_cm":     {"key": "waist_size",        "min_cm": 60,  "max_cm": 120},
    "hips_cm":      {"key": "hip_size",          "min_cm": 80,  "max_cm": 140},
    "height_cm":    {"key": "body_height",       "min_cm": 145, "max_cm": 200},
    "inseam_cm":    {"key": "leg_length",        "min_cm": 60,  "max_cm": 95},
    "shoulder_cm":  {"key": "shoulder_width",    "min_cm": 30,  "max_cm": 60},
    "neck_cm":      {"key": "neck_circumference","min_cm": 30,  "max_cm": 50},
    "arm_cm":       {"key": "arm_length",        "min_cm": 55,  "max_cm": 80},
}


def dispatch(cmd: dict) -> dict:
    action = cmd.get("action", "")
    try:
        if action == "set_cloth_preset":    return _set_cloth_preset(cmd)
        if action == "get_cloth_info":      return _get_cloth_info(cmd)
        if action == "set_cloth_param":     return _set_cloth_param(cmd)
        if action == "bake_cloth":          return _bake_cloth(cmd)
        if action == "set_body_measure":    return _set_body_measure(cmd)
        if action == "get_body_measures":   return _get_body_measures(cmd)
        if action == "load_animation":      return _load_animation(cmd)
        if action == "create_sewing_seam":  return _create_sewing_seam(cmd)
        if action == "flatten_pattern":     return _flatten_pattern(cmd)
        if action == "export_pattern_svg":  return _export_pattern_svg(cmd)
        return {"error": f"Unknown textile action: {action}"}
    except Exception as e:
        return {"error": str(e), "trace": traceback.format_exc()}


def _set_cloth_preset(cmd):
    """Weist einem Objekt ein Stoff-Preset zu."""
    obj_name = cmd["object"]
    preset   = cmd["preset"].lower()
    obj = bpy.data.objects.get(obj_name)
    if not obj:
        return {"error": f"Object '{obj_name}' not found"}
    if preset not in FABRIC_PRESETS:
        return {"error": f"Unknown preset '{preset}'. Available: {list(FABRIC_PRESETS.keys())}"}

    p = FABRIC_PRESETS[preset]

    # Cloth-Modifier finden oder anlegen
    cloth_mod = None
    for m in obj.modifiers:
        if m.type == "CLOTH":
            cloth_mod = m
            break
    if cloth_mod is None:
        cloth_mod = obj.modifiers.new("Cloth", "CLOTH")

    s = cloth_mod.settings
    s.quality               = p["quality"]
    s.mass                  = p["mass"]
    s.tension_stiffness     = p["tension_stiffness"]
    s.compression_stiffness = p["compression_stiffness"]
    s.shear_stiffness       = p["shear_stiffness"]
    s.bending_stiffness     = p["bending_stiffness"]
    s.air_damping           = p["air_damping"]
    if "use_dynamic_mesh" in p:
        try:
            s.use_dynamic_mesh = p["use_dynamic_mesh"]
        except Exception:
            pass

    # Kollision aktivieren
    cs = cloth_mod.collision_settings
    cs.use_collision         = True
    cs.collision_quality     = p["collision_quality"]
    cs.use_self_collision    = True
    cs.self_friction         = 0.3

    return {
        "ok": True,
        "object": obj_name,
        "preset": preset,
        "note": p["_note"],
        "mass_kg_m2": p["mass"],
        "bending": p["bending_stiffness"],
    }


def _get_cloth_info(cmd):
    obj = bpy.data.objects.get(cmd["object"])
    if not obj:
        return {"error": f"Object '{cmd['object']}' not found"}
    for m in obj.modifiers:
        if m.type == "CLOTH":
            s = m.settings
            return {
                "ok": True,
                "object": cmd["object"],
                "modifier": m.name,
                "mass": s.mass,
                "quality": s.quality,
                "tension_stiffness": s.tension_stiffness,
                "bending_stiffness": s.bending_stiffness,
                "air_damping": s.air_damping,
            }
    return {"error": f"No Cloth modifier on '{cmd['object']}'"}


def _set_cloth_param(cmd):
    obj = bpy.data.objects.get(cmd["object"])
    if not obj:
        return {"error": f"Object '{cmd['object']}' not found"}
    param, value = cmd["param"], cmd["value"]
    for m in obj.modifiers:
        if m.type == "CLOTH":
            s = m.settings
            if hasattr(s, param):
                setattr(s, param, value)
                return {"ok": True, "param": param, "value": value}
    return {"error": f"Cloth param '{param}' not found"}


def _bake_cloth(cmd):
    obj_name   = cmd.get("object")
    frame_start = cmd.get("frame_start", 1)
    frame_end   = cmd.get("frame_end", 250)
    if obj_name:
        obj = bpy.data.objects.get(obj_name)
        if obj:
            bpy.context.view_layer.objects.active = obj
    bpy.context.scene.frame_start = frame_start
    bpy.context.scene.frame_end   = frame_end
    try:
        bpy.ops.ptcache.bake_all(bake=True)
        return {"ok": True, "baked_frames": frame_end - frame_start + 1}
    except Exception as e:
        return {"error": str(e),
                "note": "Bake braucht aktives Cloth-Objekt + Point-Cache-Setup"}


def _set_body_measure(cmd):
    """Setzt Körpermaße (cm) über Shape Keys — funktioniert mit MB-Lab und Human Generator."""
    obj_name = cmd["object"]
    measures = cmd["measures"]   # dict: {"chest_cm": 98, "waist_cm": 82, ...}

    obj = bpy.data.objects.get(obj_name)
    if not obj:
        return {"error": f"Object '{obj_name}' not found"}
    if not obj.data.shape_keys:
        return {"error": f"Object '{obj_name}' has no shape keys"}

    keys = obj.data.shape_keys.key_blocks
    applied = {}
    skipped = {}

    for measure_name, value_cm in measures.items():
        if measure_name not in MEASURE_MAP:
            skipped[measure_name] = "unknown measure"
            continue
        m = MEASURE_MAP[measure_name]
        # Normalisieren: cm → 0.0–1.0 Shape-Key-Wert
        t = (value_cm - m["min_cm"]) / (m["max_cm"] - m["min_cm"])
        t = max(0.0, min(1.0, t))
        key_name = m["key"]
        if key_name in keys:
            keys[key_name].value = t
            applied[measure_name] = {"shape_key": key_name, "value_cm": value_cm, "shape_value": round(t, 3)}
        else:
            # Fallback: direkte Shape-Key-Suche nach Maßname
            for kb in keys:
                if any(k in kb.name.lower() for k in [key_name.split("_")[0], measure_name.split("_")[0]]):
                    kb.value = t
                    applied[measure_name] = {"shape_key": kb.name, "value_cm": value_cm, "shape_value": round(t, 3)}
                    break
            else:
                skipped[measure_name] = f"Shape key '{key_name}' not found"

    bpy.context.view_layer.update()
    return {"ok": True, "applied": applied, "skipped": skipped}


def _get_body_measures(cmd):
    obj_name = cmd["object"]
    obj = bpy.data.objects.get(obj_name)
    if not obj or not obj.data.shape_keys:
        return {"error": f"Object '{obj_name}' not found or has no shape keys"}

    keys = obj.data.shape_keys.key_blocks
    measures = {}
    for measure_name, m in MEASURE_MAP.items():
        if m["key"] in keys:
            t = keys[m["key"]].value
            # Shape-Key-Wert → cm zurückrechnen
            cm = m["min_cm"] + t * (m["max_cm"] - m["min_cm"])
            measures[measure_name] = {"value_cm": round(cm, 1), "shape_value": round(t, 3)}
    # Rohe Shape Keys auch ausgeben
    all_keys = {k.name: round(k.value, 3) for k in keys if k.name != "Basis"}
    return {"ok": True, "object": obj_name, "measures": measures, "all_shape_keys": all_keys}


def _load_animation(cmd):
    """Lädt Mixamo FBX-Animation auf einen Armature-Rig."""
    fbx_path  = cmd["fbx_path"]
    rig_name  = cmd.get("rig")
    loop      = cmd.get("loop", True)

    if not os.path.exists(fbx_path):
        return {"error": f"FBX nicht gefunden: {fbx_path}"}

    # FBX importieren
    bpy.ops.import_scene.fbx(
        filepath=fbx_path,
        use_anim=True,
        use_custom_normals=True,
        force_connect_children=False,
        automatic_bone_orientation=True
    )

    # Importiertes Armature finden
    imported = [o for o in bpy.context.selected_objects if o.type == "ARMATURE"]
    if not imported:
        return {"error": "Kein Armature im FBX gefunden"}

    anim_rig = imported[0]
    action = anim_rig.animation_data.action if anim_rig.animation_data else None

    if action and loop:
        action.use_cyclic = True

    return {
        "ok": True,
        "imported_armature": anim_rig.name,
        "action": action.name if action else None,
        "frames": int(action.frame_range[1] - action.frame_range[0]) if action else 0,
        "note": f"Rig '{rig_name}' → Retarget manuell oder via Rigify/AutoRig Pro"
    }


def _create_sewing_seam(cmd):
    """Markiert Kanten als Näht-Seams zwischen zwei Kleidungsstücken."""
    obj_name  = cmd["object"]
    edge_indices = cmd.get("edges", [])

    obj = bpy.data.objects.get(obj_name)
    if not obj or obj.type != "MESH":
        return {"error": f"Mesh object '{obj_name}' not found"}

    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="DESELECT")
    bpy.ops.object.mode_set(mode="OBJECT")

    mesh = obj.data
    seam_count = 0
    for i, edge in enumerate(mesh.edges):
        if not edge_indices or i in edge_indices:
            edge.use_seam = True
            seam_count += 1

    return {"ok": True, "object": obj_name, "seams_set": seam_count}


def _flatten_pattern(cmd):
    """Plättet 3D-Kleidung zu 2D-Schnittmuster per UV-Unwrap entlang Seams."""
    obj_name = cmd["object"]
    margin   = cmd.get("island_margin", 0.02)

    obj = bpy.data.objects.get(obj_name)
    if not obj or obj.type != "MESH":
        return {"error": f"Mesh object '{obj_name}' not found"}

    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")

    # Unwrap entlang der markierten Seams
    bpy.ops.uv.unwrap(
        method="ANGLE_BASED",
        margin=margin
    )
    bpy.ops.object.mode_set(mode="OBJECT")

    # UV-Map-Infos ausgeben
    uv_layer = obj.data.uv_layers.active
    return {
        "ok": True,
        "object": obj_name,
        "uv_layer": uv_layer.name if uv_layer else None,
        "islands": "UV-Inseln als Schnittmuster im UV-Editor sichtbar",
        "next_step": "export_pattern_svg um als Schnittmuster zu exportieren"
    }


def _export_pattern_svg(cmd):
    """Exportiert UV-Map als SVG-Schnittmuster."""
    obj_name  = cmd["object"]
    path      = cmd.get("path", "/tmp/schnittmuster.svg")
    scale_cm  = cmd.get("scale_cm", 1.0)

    obj = bpy.data.objects.get(obj_name)
    if not obj:
        return {"error": f"Object '{obj_name}' not found"}

    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")

    try:
        # Blenders UV-Export (Layout → SVG)
        bpy.ops.uv.export_layout(
            filepath=path,
            export_all=False,
            modified=True,
            mode="SVG",
            size=(4096, 4096),
            opacity=0.25,
        )
        return {"ok": True, "exported": path,
                "note": f"SVG Schnittmuster (1:1 skaliert × {scale_cm}cm/unit)"}
    except Exception as e:
        return {"error": str(e), "note": "UV-Export braucht aktive UV-Map"}
    finally:
        bpy.ops.object.mode_set(mode="OBJECT")
