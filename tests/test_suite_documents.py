"""Exercise suite graph actions through the real HTTP -> Rust transport."""
import asyncio
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "studio"))
import creative_api as api


class SuiteDocumentsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = patch.object(api, "STORE", Path(self.temp.name) / "projects")
        self.store.start()
        api._lock = asyncio.Lock()
        app = FastAPI()
        app.include_router(api.router)
        self.client = TestClient(app)
        self.pid = self.command("project.create", {"name": "Suite HTTP"})["id"]

    def tearDown(self):
        self.client.close()
        self.store.stop()
        self.temp.cleanup()

    def request(self, action, params):
        body = {"action": action, "params": params}
        if hasattr(self, "pid"):
            body["project_id"] = self.pid
        return self.client.post("/api/creative/action", json=body)

    def command(self, action, params):
        response = self.request(action, params)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["result"]

    def document(self, name, kind):
        result = self.command("document.create", {"name": name, "kind": kind, "content": {}})
        return result["document_graph"]["documents"][-1]["id"]

    def test_preserve_archive_and_undo_use_the_same_http_state(self):
        source = self.document("Sketch", "sketch")
        dependent = self.document("Extrusion", "cad")
        before = self.command("document.link", {"dependent_id": dependent, "source_id": source})
        preview = self.command("document.archive_preview", {"id": source, "mode": "preserve_dependents"})
        self.assertEqual(self.command("project.get", {}), before)
        self.assertEqual(preview["preserve_for"], [dependent])
        result = self.command("document.archive", {
            "id": source, "mode": "preserve_dependents", "expected_revision": preview["expected_revision"]})
        graph = result["document_graph"]
        copied = graph["last_archive"]["replacements"][0]["copy_id"]
        self.assertIn({"dependent_id": dependent, "source_id": copied}, graph["links"])
        self.assertEqual(self.command("history.undo", {})["document_graph"], before["document_graph"])

    def test_stale_preview_is_422_and_keeps_intervening_edit(self):
        source = self.document("Music", "music")
        preview = self.command("document.archive_preview", {"id": source, "mode": "cascade_dependents"})
        latest = self.command("note.add", {"pitch": 60, "start": 0, "duration": 1})
        response = self.request("document.archive", {
            "id": source, "mode": "cascade_dependents", "expected_revision": preview["expected_revision"]})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(self.command("project.get", {}), latest)

    def test_mcp_catalog_and_execution_share_graph(self):
        import creative_mcp
        def request(endpoint, payload=None):
            if payload is None:
                return self.client.get(endpoint).json()
            return self.client.post(endpoint, json=payload).json()
        with patch.object(creative_mcp, "request", side_effect=request):
            names = {entry["name"] for entry in creative_mcp.creative_actions()["result"]}
            self.assertIn("document.archive", names)
            created = creative_mcp.creative_execute("document.create", {
                "name": "MCP document", "kind": "notes", "content": {}}, self.pid)["result"]
            self.assertEqual(self.command("project.get", {}), created)

    def test_cross_project_link_is_rejected(self):
        foreign = self.command("project.create", {"name": "Other project"})
        other = self.client.post("/api/creative/action", json={
            "action": "document.create", "project_id": foreign["id"],
            "params": {"name": "Foreign", "kind": "notes", "content": {}}}).json()["result"]
        foreign_doc = other["document_graph"]["documents"][0]["id"]
        local = self.document("Local", "notes")
        before = self.command("project.get", {})
        self.assertEqual(self.request("document.link", {
            "dependent_id": local, "source_id": foreign_doc}).status_code, 422)
        self.assertEqual(self.command("project.get", {}), before)
