"""Проверки HTTP-слоя и формата прямых зависимостей Cargo."""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from registry import (
    RegistryError, download_index, index_path, validate_dependencies,
)


class RegistryTests(unittest.TestCase):
    """Проверить HTTP-ошибки, пути и категории зависимостей."""

    def test_paths(self):
        """Проверить все четыре варианта пути индекса Cargo."""
        cases = {"A": "1/a", "ab": "2/ab", "AbC": "3/a/abc",
                 "serde": "se/rd/serde"}
        for name, expected in cases.items():
            with self.subTest(name=name):
                self.assertEqual(index_path(name), expected)

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


if __name__ == "__main__":
    unittest.main()
