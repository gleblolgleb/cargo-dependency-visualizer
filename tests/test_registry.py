"""Проверки сбора данных Cargo и полного запуска через локальный HTTP."""

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
from urllib.error import URLError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from registry import (
    RegistryError, download_index, get_dependencies, index_path,
    select_version, validate_dependencies,
)


class QuietHandler(SimpleHTTPRequestHandler):
    """HTTP-обработчик без служебного вывода при тестах."""

    def log_message(self, format, *args):
        """Подавить журнал запросов тестового сервера."""


class RegistryTests(unittest.TestCase):
    """Проверить формат индекса, выбор версии и ошибки данных."""

    def test_paths(self):
        """Проверить все четыре варианта пути индекса Cargo."""
        cases = {"A": "1/a", "ab": "2/ab", "AbC": "3/a/abc",
                 "serde": "se/rd/serde"}
        for name, expected in cases.items():
            with self.subTest(name=name):
                self.assertEqual(index_path(name), expected)

    def test_exact_version(self):
        """Не подменять запрошенную версию последней опубликованной."""
        entries = [
            {"name": "serde", "vers": "1.0.0", "deps": []},
            {"name": "serde", "vers": "2.0.0", "deps": []},
        ]
        text = "\n".join(json.dumps(entry) for entry in entries)
        self.assertEqual(select_version(text, "serde", "1.0.0"), entries[0])
        with self.assertRaisesRegex(RegistryError, "не найдена"):
            select_version(text, "serde", "3.0.0")

    def test_bad_index(self):
        """Отклонить поврежденный JSON и несовпадение имени пакета."""
        wrong = json.dumps({"name": "other", "vers": "1.0.0"})
        for text in ("{", "[]", wrong):
            with self.subTest(text=text):
                with self.assertRaises(RegistryError):
                    select_version(text, "serde", "1.0.0")

    def test_all_categories(self):
        """Сохранить optional, dev, build, target и переименование."""
        deps = [
            {"name": "alias", "package": "actual", "req": "^1",
             "kind": "normal", "optional": True, "target": "cfg(unix)"},
            {"name": "build", "req": "^2", "kind": "build"},
            {"name": "test", "req": "^3", "kind": "dev"},
        ]
        self.assertEqual(validate_dependencies({"deps": deps}), deps)
        self.assertEqual(validate_dependencies({"deps": []}), [])

    def test_bad_dependencies(self):
        """Обработать отсутствующий список и неверные записи deps."""
        values = (None, {}, [None], [{}], [{"name": "a", "req": 1}])
        for value in values:
            with self.subTest(value=value):
                with self.assertRaises(RegistryError):
                    validate_dependencies({"deps": value})

    def test_network_errors(self):
        """Преобразовать сетевую ошибку и тайм-аут в ошибку приложения."""
        for error in (URLError("unavailable"), TimeoutError("timeout")):
            with self.subTest(error=error):
                with patch("registry.urlopen", side_effect=error):
                    with self.assertRaises(RegistryError):
                        download_index("https://index.crates.io", "serde")

    def test_test_mode(self):
        """Не добавлять операции тестового графа из следующего этапа."""
        with self.assertRaisesRegex(RegistryError, "этапу 3"):
            get_dependencies({"test_mode": True})


class HttpTests(unittest.TestCase):
    """Проверить настоящий HTTP-запрос и CLI без внешней сети."""

    def setUp(self):
        """Запустить локальный индекс с двумя версиями пакета."""
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.deps = [{"name": "child", "req": "^1", "kind": "normal"}]
        entries = [
            {"name": "demo", "vers": "1.0.0", "deps": self.deps},
            {"name": "demo", "vers": "2.0.0", "deps": []},
        ]
        index = self.base / "de/mo/demo"
        index.parent.mkdir(parents=True)
        index.write_text("\n".join(map(json.dumps, entries)), "utf-8")
        handler = partial(QuietHandler, directory=str(self.base))
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=self.server.serve_forever)
        thread.start()
        self.addCleanup(thread.join)
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        port = self.server.server_port
        self.data = dict(package="demo", version="1.0.0", test_mode=False,
                         repository=f"http://127.0.0.1:{port}",
                         output="graph.svg")

    def cli(self):
        """Запустить CLI с конфигурацией локального HTTP-репозитория."""
        path = self.base / "config.json"
        path.write_text(json.dumps(self.data), "utf-8")
        return subprocess.run(
            [sys.executable, str(ROOT / "src/main.py"), str(path)],
            capture_output=True, text=True, encoding="utf-8",
            env=dict(os.environ, PYTHONIOENCODING="utf-8"),
        )

    def test_cli_dependencies(self):
        """CLI выводит зависимости выбранной версии без настроек этапа 1."""
        result = self.cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        lines = result.stdout.splitlines()
        self.assertIn("demo@1.0.0", lines[0])
        self.assertEqual(json.loads(lines[1]), self.deps[0])
        self.assertEqual(len(lines), 2)
        self.assertFalse((self.base / "graph.svg").exists())

    def test_empty(self):
        """Пакет без зависимостей дает успешный пустой результат."""
        self.data["version"] = "2.0.0"
        result = self.cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Прямых зависимостей нет", result.stdout)

    def test_http_missing_package(self):
        """HTTP 404 отображается как ошибка отсутствующего пакета."""
        self.data["package"] = "missing"
        result = self.cli()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertIn("не найден", result.stderr)
        self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
