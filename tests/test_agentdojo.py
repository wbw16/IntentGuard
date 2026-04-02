from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from processors.agentdojo import AgentDojoProcessor


class FakeAgent:
    """Mock agent for testing."""

    def __init__(self):
        self.entropy_stats = {}
        self.entropies = []
        self.calls = []

    def agent_invoke(self, query="", available_tool_descriptions=None,
                     available_tool_params=None, known_actions=None,
                     injection_task=""):
        self.calls.append({
            "query": query,
            "tool_descriptions": available_tool_descriptions,
            "tool_params": available_tool_params,
        })
        return "fake logs", [{"role": "user", "content": query}], "fake_env_info"


class TestAgentDojoProcessor(unittest.TestCase):

    def _make_processor(self, suite="banking", attack_mode="benign", output_dir=None):
        agent = FakeAgent()
        out = output_dir or tempfile.mkdtemp()
        return AgentDojoProcessor(
            agent=agent, output_save_dir=out,
            suite=suite, attack_mode=attack_mode,
        ), agent

    def test_load_yaml_banking(self):
        proc, _ = self._make_processor(suite="banking")
        env = proc._load_environment()
        self.assertIn("bank_account", env)
        self.assertIn("filesystem", env)
        self.assertIn("user_account", env)

    def test_load_injection_vectors(self):
        proc, _ = self._make_processor(suite="banking")
        inj = proc._load_injection_vectors()
        self.assertIn("injection_bill_text", inj)
        self.assertIn("injection_incoming_transaction", inj)
        self.assertEqual(len(inj), 4)

    def test_resolve_env_data_benign(self):
        proc, _ = self._make_processor(suite="banking", attack_mode="benign")
        env = {"data": "value with {injection_bill_text} placeholder"}
        inj = {"injection_bill_text": {"description": "attack text", "default": "safe text"}}
        resolved = proc._resolve_env_data(env, inj)
        self.assertIn("safe text", resolved["data"])
        self.assertNotIn("{injection_bill_text}", resolved["data"])

    def test_resolve_env_data_injection(self):
        proc, _ = self._make_processor(suite="banking", attack_mode="injection")
        env = {"data": "value with {injection_bill_text} placeholder"}
        inj = {"injection_bill_text": {"description": "attack text", "default": "safe text"}}
        resolved = proc._resolve_env_data(env, inj)
        self.assertIn("attack text", resolved["data"])

    def test_resolve_env_data_special_chars(self):
        """特殊字符（tab, newline, quotes）不应破坏解析。"""
        proc, _ = self._make_processor(attack_mode="benign")
        env = {"file": "content: {injection_x}"}
        inj = {"injection_x": {"default": 'line1\tvalue\nline2 "quoted"'}}
        resolved = proc._resolve_env_data(env, inj)
        self.assertIn("line1\tvalue", resolved["file"])

    def test_build_tools_from_env(self):
        proc, _ = self._make_processor()
        env = {
            "bank_account": {"balance": 100, "iban": "DE123"},
            "filesystem": {"files": {"a.txt": "hello"}},
        }
        actions, descs, params = proc._build_tools_from_env(env)
        self.assertIn("get_bank_account", actions)
        self.assertIn("get_bank_account_balance", actions)
        self.assertIn("get_filesystem", actions)
        self.assertIn("get_filesystem_files", actions)
        self.assertEqual(len(descs), len(actions))

    def test_generate_tasks_benign(self):
        proc, _ = self._make_processor(attack_mode="benign")
        env = {"bank_account": {}, "filesystem": {}}
        inj = {"injection_x": {"description": "atk", "default": ""}}
        tasks = proc._generate_tasks(env, inj)
        self.assertEqual(len(tasks), 2)  # one per resource
        self.assertTrue(all(t["injection_name"] == "" for t in tasks))

    def test_generate_tasks_injection(self):
        proc, _ = self._make_processor(attack_mode="injection")
        env = {"bank_account": {}}
        inj = {
            "injection_a": {"description": "atk_a", "default": ""},
            "injection_b": {"description": "atk_b", "default": ""},
        }
        tasks = proc._generate_tasks(env, inj)
        self.assertEqual(len(tasks), 2)  # one per injection vector
        self.assertEqual(tasks[0]["injection_name"], "injection_a")

    def test_run_benign(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            proc, agent = self._make_processor(
                suite="banking", attack_mode="benign", output_dir=tmpdir,
            )
            results = proc.run()
            self.assertGreater(len(results), 0)
            self.assertEqual(len(agent.calls), len(results))
            # 检查输出文件
            meta_path = Path(tmpdir) / "meta_data.json"
            self.assertTrue(meta_path.exists())
            with open(meta_path) as f:
                saved = json.load(f)
            self.assertEqual(len(saved), len(results))

    def test_run_injection(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            proc, agent = self._make_processor(
                suite="banking", attack_mode="injection", output_dir=tmpdir,
            )
            results = proc.run()
            self.assertEqual(len(results), 4)  # banking has 4 injection vectors
            self.assertEqual(len(agent.calls), 4)

    def test_run_resume(self):
        """断点续跑：已有 meta_data.json 时跳过已完成的任务。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            proc, agent = self._make_processor(
                suite="banking", attack_mode="benign", output_dir=tmpdir,
            )
            # 第一次运行
            results1 = proc.run()
            call_count_1 = len(agent.calls)

            # 第二次运行（应跳过所有）
            proc2, agent2 = self._make_processor(
                suite="banking", attack_mode="benign", output_dir=tmpdir,
            )
            results2 = proc2.run()
            self.assertEqual(len(agent2.calls), 0)
            self.assertEqual(len(results2), len(results1))

    def test_workspace_include(self):
        """workspace suite 使用 !include 指令。"""
        proc, _ = self._make_processor(suite="workspace")
        env = proc._load_environment()
        # workspace 应该有 inbox, calendar, cloud_drive 等
        self.assertTrue(len(env) > 0)


if __name__ == "__main__":
    unittest.main()
