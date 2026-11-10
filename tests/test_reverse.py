"""Проверки обратных зависимостей и демонстрационных конфигураций."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from cli_support import run_app

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from config import ConfigError, check_fields
from graph import GraphError
from reverse import find_target, reverse_dependencies


class ReverseTests(unittest.TestCase):
    """Проверить транзитивность обратного обхода и особые случаи."""

    def test_transitive_and_disconnected(self):
        """Найти всех потребителей, включая другую компоненту корня."""
        graph = {"A": ["B"], "B": ["C"], "C": [], "D": ["C"], "E": []}
        self.assertEqual(reverse_dependencies(graph, "C"), ["B", "A", "D"])
        self.assertEqual(reverse_dependencies(graph, "A"), [])
        self.assertEqual(reverse_dependencies(graph, "E"), [])

    def test_cycles_and_duplicates(self):
        """Не включать искомый пакет в ответ и не повторять потребителей."""
        graph = {"A": ["B", "B", "A"], "B": ["C"], "C": ["A"]}
        self.assertEqual(reverse_dependencies(graph, "A"), ["C", "B"])
        self.assertEqual(reverse_dependencies({"A": ["A"]}, "A"), [])

    def test_versioned_nodes(self):
        """Различать обратные зависимости разных версий Cargo-пакета."""
        first, second = ("a", "1.0.0"), ("a", "2.0.0")
        parent = ("b", "1.0.0")
        graph = {parent: [first], first: [], second: []}
        self.assertEqual(reverse_dependencies(graph, first), [parent])
        self.assertEqual(reverse_dependencies(graph, second), [])
        self.assertEqual(find_target(graph, "a@1.0.0", False), first)
        with self.assertRaises(GraphError):
            find_target(graph, "a", False)

    def test_absent_target(self):
        """Отсутствующий пакет отличается от отсутствия потребителей."""
        with self.assertRaises(GraphError):
            reverse_dependencies({"A": []}, "B")
        with self.assertRaises(GraphError):
            find_target({"A": []}, "B", True)

    def test_invalid_option(self):
        """Отклонить неверный тип и пустое имя обратного запроса."""
        config = json.loads((ROOT / "config.json").read_text("utf-8"))
        for value in (None, 1, True, "", " A"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ConfigError, "reverse_package"):
                    check_fields(dict(config, reverse_package=value))

    def test_deep_reverse_chain(self):
        """Обратный обход не зависит от лимита рекурсии Python."""
        count = sys.getrecursionlimit() + 100
        graph = {i: [i + 1] for i in range(count)}
        graph[count] = []
        result = reverse_dependencies(graph, count)
        self.assertEqual(result, list(reversed(range(count))))

    def test_cli_examples(self):
        """Конфигурации режима только этапа 4 явно отклоняются."""
        cases = {"chain": ("C", ["B", "A"]),
                 "diamond": ("D", ["B", "A", "C"]),
                 "cycle": ("A", ["C", "B"]),
                 "self-loop": ("A", ["Нет."]),
                 "isolated": ("A", ["Нет."])}
        with tempfile.TemporaryDirectory() as directory:
            for name, (target, nodes) in cases.items():
                with self.subTest(name=name):
                    config = ROOT / "examples" / f"reverse-{name}-config.json"
                    result = run_app(
                        [sys.executable, str(ROOT / "src/main.py"),
                         str(config)], cwd=directory, capture_output=True,
                        text=True, encoding="utf-8",
                        env=dict(os.environ, PYTHONIOENCODING="utf-8"),
                    )
                    self.assertEqual(result.returncode, 2)
                    self.assertEqual(result.stdout, "")
                    self.assertIn("reverse_package", result.stderr)


if __name__ == "__main__":
    unittest.main()
