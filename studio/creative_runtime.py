"""Portable resource locations shared by packaged adapters."""
import os
from pathlib import Path
import sys

RESOURCES = Path(os.environ.get('K_CREATIVE_RESOURCES', Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parents[1]))
DATA = Path(os.environ.get('K_CREATIVE_DIR', Path.home() / 'Documents/K-Creative'))
