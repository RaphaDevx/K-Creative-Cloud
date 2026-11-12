import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("scoped_handover", Path(__file__).with_name("scoped_handover.py"))
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


class ScopeChecks(unittest.TestCase):
    def test_path_scope_has_directory_boundaries(self):
        self.assertTrue(helper.allowed("3d-editor/src/a.rs", ["3d-editor"]))
        self.assertFalse(helper.allowed("3d-editor-other/file", ["3d-editor"]))
        self.assertFalse(helper.allowed("07_Brands/file", ["3d-editor"]))

    def test_success_needs_signed_structured_receipt(self):
        body = {"handedOver": True, "signed": True, "project": "kcreative", "commit": "a"*40, "pushed": ["kdev"]}
        self.assertTrue(helper.terminal_response(200, body))
        for field in body:
            changed = dict(body)
            del changed[field]
            self.assertFalse(helper.terminal_response(200, changed))
        self.assertFalse(helper.terminal_response(200, ["not a receipt"]))

    def test_timeouts_and_live_signer_conflicts_remain_unknown(self):
        for status in (503, 409, 504):
            self.assertFalse(helper.terminal_response(status, {"stage": "commit", "error": "still running"}))
        self.assertTrue(helper.terminal_response(422, {"stage": "commit", "error": "gitleaks rejected"}))

    def test_install_does_not_remove_a_later_writers_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            index = Path(directory)/"index"
            index.write_bytes(b"old")
            real_replace = helper.os.replace
            def replace_and_race(source, destination):
                real_replace(source, destination)
                Path(source).write_bytes(b"another writer")
            with patch.object(helper.os, "replace", side_effect=replace_and_race):
                helper.install_index(index, b"new", 0o600, lambda: None)
            self.assertEqual(index.read_bytes(), b"new")
            self.assertEqual(index.with_name("index.lock").read_bytes(), b"another writer")

    def test_failed_verification_preserves_index_and_cleans_only_own_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            index = Path(directory)/"index"
            index.write_bytes(b"old")
            def reject():
                raise RuntimeError("concurrent update")
            with self.assertRaises(RuntimeError):
                helper.install_index(index, b"new", 0o600, reject)
            self.assertEqual(index.read_bytes(), b"old")
            self.assertFalse(index.with_name("index.lock").exists())

    def test_existing_lock_is_never_removed(self):
        with tempfile.TemporaryDirectory() as directory:
            index = Path(directory)/"index"
            lock = index.with_name("index.lock")
            index.write_bytes(b"old")
            lock.write_bytes(b"busy")
            with self.assertRaises(FileExistsError):
                helper.install_index(index, b"new", 0o600, lambda: None)
            self.assertEqual(lock.read_bytes(), b"busy")


if __name__ == "__main__":
    unittest.main()
