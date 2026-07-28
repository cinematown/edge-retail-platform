from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


PUBLISHER_PATH = Path(__file__).resolve().parents[1] / "publisher.py"
SPEC = importlib.util.spec_from_file_location("mock_publisher", PUBLISHER_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("could not load publisher.py")
publisher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(publisher)


class ReplaceAutoTests(unittest.TestCase):
    def test_replaces_nested_auto_values_without_mutating_input(self) -> None:
        source = {"observedAt": "AUTO", "nested": ["AUTO", {"value": 1}]}
        timestamp = "2026-07-26T20:00:00.123+09:00"

        result = publisher.replace_auto(source, timestamp)

        self.assertEqual(result["observedAt"], timestamp)
        self.assertEqual(result["nested"][0], timestamp)
        self.assertEqual(source["observedAt"], "AUTO")


class LoadScenarioTests(unittest.TestCase):
    def write_scenario(self, value: object) -> Path:
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / "scenario.json"
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def test_accepts_valid_step(self) -> None:
        path = self.write_scenario(
            [{"delayMs": 0, "topic": "retail/test", "payload": {"value": 1}}]
        )

        steps = publisher.load_scenario(path)

        self.assertEqual(len(steps), 1)

    def test_rejects_empty_scenario(self) -> None:
        path = self.write_scenario([])

        with self.assertRaisesRegex(publisher.ScenarioError, "non-empty"):
            publisher.load_scenario(path)

    def test_rejects_negative_delay(self) -> None:
        path = self.write_scenario(
            [{"delayMs": -1, "topic": "retail/test", "payload": {}}]
        )

        with self.assertRaisesRegex(publisher.ScenarioError, "delayMs"):
            publisher.load_scenario(path)


if __name__ == "__main__":
    unittest.main()
