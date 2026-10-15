#!/usr/bin/env python3
"""Baut ein OM-Reel: build.py <modulname> [--frames]. Interpreter: /storage/projekte/ki_pipeline_env_312/bin/python3"""
import importlib.util, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "video-shorts-mcp"))
from beat_reel import build

name = sys.argv[1]
spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, f"{name}.py"))
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
out = os.environ.get("REEL_OUT", os.path.expanduser("~/renders/om"))
res = build(mod.REEL, out, keep_frames="--frames" in sys.argv)
print(json.dumps(res, indent=2))
