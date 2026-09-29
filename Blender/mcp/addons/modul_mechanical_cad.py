"""
modul_mechanical_cad.py — K-Creative-Cloud
Parametrische Kontrolle für Maschinenbau / Hardware-Prototypen.
Wird von k_parametric.py als Dispatcher-Modul geladen.

Befehle:
  set_geonode     — Geometry-Nodes-Input setzen
  get_geonode     — alle GeoNode-Inputs auslesen
  set_constraint  — CAD-Sketcher-Constraint ändern
  get_scene_info  — Szenenstruktur + Modifier-Infos
  print3d_check   — 3D-Print-Toolbox Mesh-Analyse
  export_stl      — STL-Export für Slicer
"""

import bpy
import traceback
import os


ACTIONS = {
    "set_geonode", "get_geonode", "set_constraint",
    "get_scene_info", "print3d_check", "export_stl"
}


def dispatch(cmd: dict) -> dict:
    action = cmd.get("action", "")
    try:
        if action == "set_geonode":     return _set_geonode(cmd)
        if action == "get_geonode":     return _get_geonode(cmd)
        if action == "set_constraint":  return _set_constraint(cmd)
        if action == "get_scene_info":  return _get_scene_info()
        if action == "print3d_check":   return _print3d_check(cmd)
        if action == "export_stl":      return _export_stl(cmd)
        return {"error": f"Unknown mechanical action: {action}"}
    except Exception as e:
        return {"error": str(e), "trace": traceback.format_exc()}


def _set_geonode(cmd):
    obj = bpy.data.objects.get(cmd["object"])
    if not obj:
        return {"error": f"Object '{cmd['object']}' not found"}
    param, value = cmd["param"], cmd["value"]
    for mod in obj.modifiers:
        if mod.type == "NODES" and mod.node_group:
            for inp in mod.node_group.interface.items_tree:
                if inp.item_type == "SOCKET" and inp.in_out == "INPUT":
                    if inp.name == param or inp.identifier == param:
                        mod[inp.identifier] = value
                        bpy.context.view_layer.update()
                        return {"ok": True, "object": cmd["object"],
                                "param": param, "value": value, "modifier": mod.name}
    return {"error": f"GeoNode param '{param}' not found on '{cmd['object']}'"}


def _get_geonode(cmd):
    obj = bpy.data.objects.get(cmd["object"])
    if not obj:
        return {"error": f"Object '{cmd['object']}' not found"}
    params = {}
    for mod in obj.modifiers:
        if mod.type == "NODES" and mod.node_group:
            for inp in mod.node_group.interface.items_tree:
                if inp.item_type == "SOCKET" and inp.in_out == "INPUT":
                    try:
                        params[inp.name] = {
                            "id": inp.identifier,
                            "type": inp.bl_socket_idname.replace("NodeSocket", ""),
                            "value": mod.get(inp.identifier)
                        }
                    except Exception:
                        pass
    return {"ok": True, "object": cmd["object"], "params": params}


def _set_constraint(cmd):
    scene = bpy.context.scene
    if not hasattr(scene, "sketcher"):
        return {"error": "CAD Sketcher nicht installiert"}
    name, value = cmd["constraint"], cmd["value"]
    for con in scene.sketcher.constraints.all:
        label = getattr(con, "name", "") or getattr(con, "label", "")
        if label == name:
            con.value = value
            try:
                bpy.ops.view3d.slvs_solve()
            except Exception:
                pass
            bpy.context.view_layer.update()
            return {"ok": True, "constraint": name, "value": value}
    return {"error": f"Constraint '{name}' not found"}


def _get_scene_info():
    info = {}
    for obj in bpy.context.scene.objects:
        mods = []
        for m in obj.modifiers:
            md = {"name": m.name, "type": m.type}
            if m.type == "NODES" and m.node_group:
                inputs = {}
                for inp in m.node_group.interface.items_tree:
                    if inp.item_type == "SOCKET" and inp.in_out == "INPUT":
                        inputs[inp.name] = m.get(inp.identifier)
                md["geonode_inputs"] = inputs
            mods.append(md)
        info[obj.name] = {
            "type": obj.type,
            "location": list(obj.location),
            "modifiers": mods
        }
    return {"ok": True, "objects": info}


def _print3d_check(cmd):
    obj_name = cmd.get("object")
    if obj_name:
        obj = bpy.data.objects.get(obj_name)
        if obj:
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)
    try:
        bpy.ops.mesh.print3d_check_all()
        return {"ok": True, "note": "3D-Print Checks ausgeführt — Ergebnisse im Info-Panel"}
    except Exception as e:
        return {"error": str(e), "note": "object_print3d_utils aktiviert?"}


def _export_stl(cmd):
    obj_name = cmd.get("object")
    path = cmd.get("path", "/tmp/export.stl")
    if obj_name:
        obj = bpy.data.objects.get(obj_name)
        if obj:
            bpy.ops.object.select_all(action="DESELECT")
            obj.select_set(True)
    bpy.ops.export_mesh.stl(filepath=path, use_selection=bool(obj_name))
    return {"ok": True, "exported": path}
