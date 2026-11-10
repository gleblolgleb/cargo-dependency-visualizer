"""Интеграционные проверки графа Cargo через локальный HTTP-индекс."""

import json
import os
import subprocess
import sys
import tempfile
import threading
import unittest
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from cargo import CargoSource, parse_index
from graph import build_graph
from registry import RegistryError, download_index, index_path
from versions import VersionError


class QuietHandler(SimpleHTTPRequestHandler):
    """HTTP-обработчик без сообщений тестового сервера."""

    def log_message(self, format, *args):
        """Подавить журнал запросов."""


class CargoTests(unittest.TestCase):
    """Проверить HTTP, транзитивность, версии, переименования и циклы."""

    def setUp(self):
        """Создать индекс, запускаемый без доступа к внешней сети."""
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.write_package("demo", [self.record("1.0.0", [
            {"name": "alias", "package": "mid", "req": "^1"},
            {"name": "leaf", "req": "=2.0.0", "kind": "dev"},
        ])])
        self.write_package("mid", [
            self.record("1.1.0", [{"name": "leaf", "req": "^0.1"}]),
            self.record("1.9.0", [], yanked=True),
            self.record("2.0.0", []),
        ])
        self.write_package("leaf", [
            self.record("0.1.2", [{"name": "demo", "req": "=1.0.0"}]),
            self.record("2.0.0", []),
        ])
        handler = partial(QuietHandler, directory=str(self.base))
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=self.server.serve_forever)
        thread.start()
        self.addCleanup(thread.join)
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.url = f"http://127.0.0.1:{self.server.server_port}"
        self.source = CargoSource(self.url)

    def record(self, version, deps, yanked=False):
        """Создать запись индекса Cargo для тестовой версии."""
        return dict(vers=version, deps=deps, yanked=yanked)

    def write_package(self, name, records):
        """Записать построчный JSON по правилам пути Cargo."""
        path = self.base / index_path(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        text = "\n".join(json.dumps(dict(row, name=name)) for row in records)
        path.write_text(text, "utf-8")

    def test_transitive_cycle_versions_and_cache(self):
        """Сохранить цикл и разные версии пакета, не повторяя HTTP-запрос."""
        with patch("cargo.download_index", wraps=download_index) as fetch:
            graph = build_graph(("demo", "1.0.0"), self.source.children)
        expected = {
            ("demo", "1.0.0"): [("mid", "1.1.0"), ("leaf", "2.0.0")],
            ("mid", "1.1.0"): [("leaf", "0.1.2")],
            ("leaf", "0.1.2"): [("demo", "1.0.0")],
            ("leaf", "2.0.0"): [],
        }
        self.assertEqual(graph, expected)
        self.assertEqual(fetch.call_count, 3)

    def test_missing_version_and_package(self):
        """Отсутствующие узлы и неподходящие диапазоны дают ошибку."""
        with self.assertRaises(RegistryError):
            self.source.entry(("demo", "9.0.0"))
        with self.assertRaises(RegistryError):
            self.source.records("missing")
        with self.assertRaises(VersionError):
            self.source.resolve({"name": "mid", "req": "^8"})

    def test_foreign_registry(self):
        """Не искать зависимость другого индекса в текущем репозитории."""
        dependency = dict(name="mid", req="^1", registry="https://other")
        with self.assertRaises(RegistryError):
            self.source.resolve(dependency)

    def test_invalid_index(self):
        """Поврежденные записи индекса превращаются в штатные ошибки."""
        for text in ("{", "[]", '{"name":"other","vers":"1.0.0"}',
                     '{"name":"demo","vers":null}'):
            with self.subTest(text=text):
                with self.assertRaises(RegistryError):
                    parse_index(text, "demo")

    def test_cli(self):
        """Построить полный граф через CLI без создания SVG."""
        path = self.base / "config.json"
        config = dict(package="demo", repository=self.url, test_mode=False,
                      version="1.0.0", output="graph.svg")
        path.write_text(json.dumps(config), "utf-8")
        result = subprocess.run(
            [sys.executable, str(ROOT / "src/main.py"), str(path)],
            capture_output=True, text=True, encoding="utf-8",
            env=dict(os.environ, PYTHONIOENCODING="utf-8"),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), [
            "demo@1.0.0 -> mid@1.1.0, leaf@2.0.0",
            "mid@1.1.0 -> leaf@0.1.2",
            "leaf@0.1.2 -> demo@1.0.0",
            "leaf@2.0.0 -> (нет зависимостей)",
        ])
        self.assertFalse((self.base / "graph.svg").exists())


    def test_reverse_cli(self):
        """Построить полный граф через CLI без создания SVG."""
        path = self.base / "config.json"
        config = dict(package="demo", repository=self.url, test_mode=False,
                      version="1.0.0", output="graph.svg")
        config["reverse_package"] = "leaf@0.1.2"
        path.write_text(json.dumps(config), "utf-8")
        result = subprocess.run(
            [sys.executable, str(ROOT / "src/main.py"), str(path)],
            capture_output=True, text=True, encoding="utf-8",
            env=dict(os.environ, PYTHONIOENCODING="utf-8"),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), [
            "Обратные зависимости leaf@0.1.2:", "mid@1.1.0", "demo@1.0.0",
        ])
        self.assertFalse((self.base / "graph.svg").exists())


if __name__ == "__main__":
    unittest.main()
