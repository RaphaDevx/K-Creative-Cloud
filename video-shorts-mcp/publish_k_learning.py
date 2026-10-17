#!/usr/bin/env python3
"""
Upload + Registrierung eines Reels im K-Learning-Katalog (Supabase), aktueller Weg:

  1. MP4 -> Storage-Bucket `videos` (anon key, x-upsert)
  2. Eintrag -> RPC public.k_import_content(p_kind='video') mit Import-Token

Ersetzt die alten Skripte (K-Learning/tools/reels/*_deploy.py): die schrieben data/feed-data.js unter dem
alten Pfad /home/raphael/K-Learning und pushten per git — beides existiert so nicht mehr.

Umgebung (nie ausgeben/loggen):
  SUPABASE_URL, SUPABASE_ANON_KEY   -> source /home/claude/.keys/tokens.env
  SUPABASE_SERVICE_ROLE_KEY         -> nur für den Upload: seit 2026-10-17 dürfen nur Content-Admins
                                       (private.content_admins) oder der Service-Key in den Bucket schreiben
  K_IMPORT_TOKEN oder K_IMPORT_TOKEN_FILE (Pfad zu Datei mit dem Token)

Aufruf:
  python3 publish_k_learning.py --mp4 x.mp4 --meta-module reels/om/om_xyz.py [--register-only] [--dry-run]
Oder als Modul: publish(mp4, meta) / register_existing(meta, filename, duration_s=None)
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

BUCKET = "videos"
# Kurs-Defaults (course_color der bestehenden Kurse: ESF #7c3aed, Statistik #0ea5e9, MakroII #059669)
COURSES = {"OM": "#ea580c"}
# Der Feed-Fallback (js/screens/feed.js) filtert type === 'localvideo'; alle bestehenden Zeilen nutzen das.
DEFAULT_TYPE = "localvideo"


def _env(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        sys.exit(f"{name} fehlt (source /home/claude/.keys/tokens.env)")
    return v


def _token() -> str:
    t = os.environ.get("K_IMPORT_TOKEN")
    if not t and os.environ.get("K_IMPORT_TOKEN_FILE"):
        t = Path(os.environ["K_IMPORT_TOKEN_FILE"]).read_text().strip()
    if not t:
        sys.exit("K_IMPORT_TOKEN oder K_IMPORT_TOKEN_FILE fehlt")
    return t


def duration_str(mp4: str) -> str:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of",
                          "default=noprint_wrappers=1:nokey=1", mp4], capture_output=True, text=True).stdout
    secs = round(float(out.strip()))
    return f"{secs // 60}:{secs % 60:02d}"


def public_url(filename: str) -> str:
    return f"{_env('SUPABASE_URL')}/storage/v1/object/public/{BUCKET}/{filename}"


def upload(mp4: str, filename: str | None = None, upsert: bool = False) -> str:
    """Upload in den Bucket. Der anon key darf seit 2026-10-17 nicht mehr schreiben (RLS);
    erlaubt sind Content-Admins oder der Service-Key (SUPABASE_SERVICE_ROLE_KEY, nie loggen)."""
    filename = filename or Path(mp4).name
    url, anon = _env("SUPABASE_URL"), _env("SUPABASE_ANON_KEY")
    service = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not service:
        sys.exit("SUPABASE_SERVICE_ROLE_KEY fehlt: Upload in den videos-Bucket ist nur noch für Admins erlaubt "
                 "(Key aus Supabase Dashboard > Settings > API in /home/claude/.keys/tokens.env eintragen).")
    headers = {"apikey": anon, "Authorization": f"Bearer {service}", "Content-Type": "video/mp4"}
    if upsert:
        headers["x-upsert"] = "true"
    req = urllib.request.Request(f"{url}/storage/v1/object/{BUCKET}/{filename}",
                                 data=Path(mp4).read_bytes(), method="POST", headers=headers)
    try:
        urllib.request.urlopen(req, timeout=300).read()
    except urllib.error.HTTPError as e:
        body = e.read()[:300]
        if b"already exists" in body or b"Duplicate" in body:
            sys.exit(f"{filename} existiert schon im Bucket (anon darf nicht ueberschreiben) -> anderen Dateinamen waehlen "
                     f"oder --register-only")
        sys.exit(f"Upload fehlgeschlagen: HTTP {e.code} {body!r}")
    return public_url(filename)


def register(payload: dict) -> str:
    url, key = _env("SUPABASE_URL"), _env("SUPABASE_ANON_KEY")
    body = json.dumps({"p_token": _token(), "p_kind": "video", "p_payload": payload}).encode()
    req = urllib.request.Request(f"{url}/rest/v1/rpc/k_import_content", data=body, method="POST",
                                 headers={"apikey": key, "Authorization": f"Bearer {key}",
                                          "Content-Type": "application/json"})
    try:
        return urllib.request.urlopen(req, timeout=60).read().decode()
    except urllib.error.HTTPError as e:  # Fehlertext enthaelt den Token nicht
        sys.exit(f"Registrierung fehlgeschlagen: HTTP {e.code} {e.read()[:300]!r}")


def build_payload(meta: dict, video_src: str, duration: str, course: str = "OM") -> dict:
    p = dict(meta)
    p.update(course=course, course_color=COURSES.get(course, "#7c3aed"), duration=duration,
             type=p.get("type", DEFAULT_TYPE), video_src=video_src)
    p.setdefault("level", "Prüfungsrelevant ⚡")
    return p


def publish(mp4: str, meta: dict, course: str = "OM", register_only: bool = False, dry_run: bool = False) -> dict:
    src = public_url(Path(mp4).name) if (register_only or dry_run) else upload(mp4)
    payload = build_payload(meta, src, duration_str(mp4), course)
    if dry_run:
        return dict(payload=payload)
    return dict(video_src=src, duration=payload["duration"], result=register(payload))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mp4", required=True)
    ap.add_argument("--meta-module", required=True, help="Python-Datei mit META-Dict")
    ap.add_argument("--course", default="OM")
    ap.add_argument("--register-only", action="store_true", help="MP4 liegt schon im Bucket")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    sys.path.insert(0, os.path.dirname(os.path.abspath(a.meta_module)))   # fuer "from _common import *"
    spec = importlib.util.spec_from_file_location("m", a.meta_module)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    print(json.dumps(publish(a.mp4, m.META, a.course, a.register_only, a.dry_run), ensure_ascii=False, indent=2))
