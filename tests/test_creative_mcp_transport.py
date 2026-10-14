import asyncio
import os
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch

from fastapi import FastAPI
import uvicorn
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'studio'))
import creative_api as api
from creative_security import LocalSecurity


class MCPTransport(unittest.TestCase):
    def test_actual_stdio_tools_edit_http_state(self):
        async def run():
            with tempfile.TemporaryDirectory() as directory, patch.object(api, 'STORE', Path(directory)):
                api._lock = asyncio.Lock()
                app = FastAPI(); app.add_middleware(LocalSecurity); app.include_router(api.router)
                sock = socket.socket(); sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
                server = uvicorn.Server(uvicorn.Config(app, log_level='error'))
                task = asyncio.create_task(server.serve(sockets=[sock]))
                try:
                    for _ in range(100):
                        if server.started: break
                        await asyncio.sleep(.02)
                    params = StdioServerParameters(command=sys.executable, args=[str(ROOT/'studio/creative_mcp.py')], env={**os.environ, 'K_CREATIVE_URL': f'http://127.0.0.1:{port}'})
                    async with stdio_client(params) as (read, write):
                        async with ClientSession(read, write) as session:
                            await session.initialize()
                            catalog = await session.list_tools()
                            self.assertIn('creative_execute', [tool.name for tool in catalog.tools])
                            import json
                            created = await session.call_tool('creative_execute', {'action': 'project.create', 'params': {'name': 'Actual MCP'}, 'project_id': ''})
                            project = json.loads(created.content[0].text)['result']
                            updated = await session.call_tool('creative_execute', {'action': 'note.add', 'params': {'pitch': 69, 'start': 0, 'duration': 1}, 'project_id': project['id']})
                            self.assertFalse(updated.isError)
                            state = await api.execute({'action': 'project.get', 'project_id': project['id'], 'params': {}})
                            self.assertEqual(len(state['result']['notes']), 1)
                            undone = await session.call_tool('creative_execute', {'action': 'history.undo', 'params': {}, 'project_id': project['id']})
                            self.assertFalse(undone.isError)
                            state = await api.execute({'action': 'project.get', 'project_id': project['id'], 'params': {}})
                            self.assertEqual(len(state['result']['notes']), 0)
                finally:
                    server.should_exit = True
                    await task
        asyncio.run(run())
