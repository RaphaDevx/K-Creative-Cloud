#!/usr/bin/env python3
"""Read-only local capability discovery. Never install/execute manifest commands."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'studio'))
from creative_discovery import BUILTINS, KINDS, ROOT, discover

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--kind',choices=sorted(KINDS));p.add_argument('--output',type=Path)
    a=p.parse_args();result=discover(a.kind);text=json.dumps(result,ensure_ascii=False,indent=2)
    if a.output:
        with a.output.open('x') as f:f.write(text+'\n')
    else:print(text)
