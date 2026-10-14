import sys
from pathlib import Path
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'studio'))
import creative_agent

class AgentLaunch(unittest.TestCase):
    def test_codex_forwards_token_without_argv_secret(self):
        with patch('creative_agent.shutil.which', return_value='/bin/codex'), patch.dict('os.environ', {'K_CREATIVE_TOKEN': 'secret-test-value'}):
            command = creative_agent.command('codex')
            self.assertNotIn('secret-test-value', ' '.join(command))
            self.assertIn('mcp_servers.k_creative.env_vars=["K_CREATIVE_URL","K_CREATIVE_TOKEN"]', command)
            self.assertNotIn('--dangerously-bypass-approvals-and-sandbox', command)

    def test_claude_no_global_mutation(self):
        with patch('creative_agent.shutil.which', return_value='/bin/claude'):
            command = creative_agent.command('claude')
            self.assertIn('--mcp-config', command)
            self.assertNotIn('--dangerously-skip-permissions', command)

    def test_unavailable_rejected(self):
        with patch('creative_agent.shutil.which', return_value=None):
            with self.assertRaises(ValueError): creative_agent.command('codex')
