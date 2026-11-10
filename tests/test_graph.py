"""Проверки итеративного DFS, тестовых файлов и CLI этапа 3."""

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

from graph import GraphError, build_graph, validate_test_graph


class GraphTests(unittest.TestCase):
    """Проверить транзитивность, циклы и однократную обработку узлов."""

    def test_dfs_order(self):
        """Ветвь DFS должна посещаться до соседнего потомка корня."""
        source = {"A": ["B", "C"], "B": ["D"], "C": [], "D": []}
        result = build_graph("A", source.__getitem__)
        self.assertEqual(list(result), ["A", "B", "D", "C"])
        self.assertEqual(result, source)

    def test_cycles_and_shared_dependency(self):
        """Сохранить все ребра и обработать каждый узел только один раз."""
        source = {"A": ["B", "C"], "B": ["D"],
                  "C": ["D"], "D": ["A", "D"]}
        calls = []

        def children(node):
            """Записать обращения к поставщику зависимостей."""
            calls.append(node)
            return source[node]

        self.assertEqual(build_graph("A", children), source)
        self.assertEqual(len(calls), len(source))
        self.assertEqual(len(set(calls)), len(source))

    def test_deep_chain(self):
        """Пройти цепочку глубже лимита рекурсии Python без рекурсии."""
        count = sys.getrecursionlimit() + 100
        source = {i: [i + 1] for i in range(count)}
        source[count] = []
        self.assertEqual(build_graph(0, source.__getitem__), source)

    def test_bad_graphs(self):
        """Отклонить неверные имена, типы и отсутствующие зависимости."""
        cases = ({"a": []}, {"A1": []}, {"А": []}, {"A": "B"},
                 {"A": ["B"]}, {"A": [1]}, {"A": [[]]})
        for source in cases:
            with self.subTest(source=source):
                with self.assertRaises(GraphError):
                    validate_test_graph(source)


class ExampleTests(unittest.TestCase):
    """Проверить примеры через CLI и относительные пути конфигурации."""

    def run_config(self, path, directory):
        """Запустить приложение из произвольного рабочего каталога."""
        return run_app(
            [sys.executable, str(ROOT / "src/main.py"), str(path)],
            cwd=directory, capture_output=True, text=True, encoding="utf-8",
            env=dict(os.environ, PYTHONIOENCODING="utf-8"),
        )

    def test_examples(self):
        """Все пять случаев дают ожидаемые списки смежности."""
        cases = {
            "chain": ["A -> B", "B -> C", "C -> (нет зависимостей)"],
            "diamond": ["A -> B, C", "B -> D",
                        "D -> (нет зависимостей)", "C -> D"],
            "cycle": ["A -> B", "B -> C", "C -> A"],
            "self-loop": ["A -> A"],
            "isolated": ["A -> (нет зависимостей)"],
        }
        with tempfile.TemporaryDirectory() as directory:
            for name, expected in cases.items():
                with self.subTest(name=name):
                    path = ROOT / "examples" / f"{name}-config.json"
                    result = self.run_config(path, directory)
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stdout.splitlines(), expected)

    def test_missing_root_and_broken_file(self):
        """Ошибки тестового файла не дают частичный граф и traceback."""
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            path = base / "config.json"
            config = dict(package="A", repository="repo.json",
                          test_mode=True, version="1.0.0", output="a.svg")
            path.write_text(json.dumps(config), "utf-8")
            for content in ('{"B": []}', '{"A": ["B"]}', '{'):
                with self.subTest(content=content):
                    (base / "repo.json").write_text(content, "utf-8")
                    result = self.run_config(path, directory)
                    self.assertEqual(result.returncode, 2)
                    self.assertEqual(result.stdout, "")
                    self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
