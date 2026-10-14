"""Launch installed LLM CLIs with per-session MCP, without global config edits."""
import json
import os
from pathlib import Path
import shutil
import sys


def capabilities():
    return {'shell': True, 'codex': bool(shutil.which('codex')), 'claude': bool(shutil.which('claude'))}


def command(provider):
    executable = shutil.which(provider)
    if provider not in ('codex', 'claude') or not executable:
        raise ValueError('Selected LLM CLI is not installed')
    if getattr(sys, 'frozen', False):
        mcp_command, args = sys.executable, ['--mcp']
    else:
        mcp_command, args = sys.executable, [str(Path(__file__).with_name('creative_mcp.py'))]
    if provider == 'codex':
        return [executable, '-c', 'mcp_servers.k_creative.command=' + json.dumps(mcp_command),
                '-c', 'mcp_servers.k_creative.args=' + json.dumps(args),
                '-c', 'mcp_servers.k_creative.env_vars=["K_CREATIVE_URL","K_CREATIVE_TOKEN"]']
    config = {'mcpServers': {'k_creative': {'command': mcp_command, 'args': args}}}
    return [executable, '--mcp-config', json.dumps(config)]
