"""Gemeinsame Helfer fuer die OM-Reels (Pfad, Zahlenformat, Plot-Farben)."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "video-shorts-mcp"))
from beat_reel import *   # noqa: F401,F403

def de(v, nd=1):
    """Dezimalkomma wie in der Pruefung/Excel (de-CH/de-DE)."""
    return f"{v:.{nd}f}".replace(".", ",")

LEVEL = "Prüfungsrelevant ⚡"
