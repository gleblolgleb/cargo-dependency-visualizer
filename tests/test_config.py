"""Проверки конфигурации и демонстрация ошибок параметров этапа 1."""

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from config import ConfigError, PARAMETERS, load_config


class ConfigTests(unittest.TestCase):
    """Проверить допустимые настройки и ошибки каждого параметра."""

    def setUp(self):
        """Создать независимый временный каталог конфигурации."""
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.path = self.base / "config.json"
        self.data = json.loads((ROOT / "config.json").read_text("utf-8"))

    def save(self, data):
        """Записать конфигурацию для проверки."""
        self.path.write_text(json.dumps(data), encoding="utf-8")

    def run_cli(self):
        """Вызвать приложение из другого рабочего каталога."""
        return subprocess.run(
            [sys.executable, str(ROOT / "src/main.py"), str(self.path)],
            cwd=self.base, capture_output=True, text=True, encoding="utf-8",
            env=self.cli_environment(),
        )

    def cli_environment(self):
        """Обеспечить UTF-8 для захвата русских сообщений в Windows."""
        import os
        return dict(os.environ, PYTHONIOENCODING="utf-8")

    def test_valid_configuration(self):
        """Корректная конфигурация загружается без изменения значений."""
        self.save(self.data)
        self.assertEqual(load_config(self.path), self.data)

    def test_missing_parameters(self):
        """Отсутствие каждого обязательного параметра вызывает ошибку."""
        for name in PARAMETERS:
            with self.subTest(parameter=name):
                data = copy.copy(self.data)
                del data[name]
                self.save(data)
                with self.assertRaisesRegex(ConfigError, name):
                    load_config(self.path)

    def test_invalid_parameters(self):
        """Неверные значения всех пяти параметров отклоняются."""
        cases = {
            "package": ["", None, 27, "bad name", "../serde"],
            "repository": ["", 27, "not-a-url", "https://", "http://a:x"],
            "test_mode": ["false", 0, 1, None],
            "version": ["", 1, "1.0", "v1.2.3", "1.2.3-01"],
            "output": ["", 27, "graph.png", "missing/graph.svg", "?.svg"],
        }
        for name, values in cases.items():
            for value in values:
                with self.subTest(parameter=name, value=value):
                    data = dict(self.data, **{name: value})
                    self.save(data)
                    with self.assertRaisesRegex(ConfigError, name):
                        load_config(self.path)

    def test_test_repository(self):
        """В тестовом режиме путь отсчитывается от файла JSON."""
        repository = self.base / "repository.json"
        repository.write_text("{}", encoding="utf-8")
        self.data.update(test_mode=True, repository=repository.name)
        self.save(self.data)
        self.assertTrue(load_config(self.path)["test_mode"])
        repository.unlink()
        with self.assertRaisesRegex(ConfigError, "repository"):
            load_config(self.path)

    def test_file_errors(self):
        """Обработать отсутствующий файл, неверный JSON и кодировку."""
        with self.assertRaises(ConfigError):
            load_config(self.path)
        for content in (b"{", b"[]", b"null", b"\xff"):
            with self.subTest(content=content):
                self.path.write_bytes(content)
                with self.assertRaises(ConfigError):
                    load_config(self.path)

    def test_unknown_parameter(self):
        """Опечатка в имени настройки не должна остаться незамеченной."""
        self.save(dict(self.data, extra=True))
        with self.assertRaises(ConfigError):
            load_config(self.path)

    def test_cli_parameter_errors(self):
        """CLI демонстрирует ошибку каждого параметра без traceback."""
        for name in PARAMETERS:
            with self.subTest(parameter=name):
                self.save(dict(self.data, **{name: None}))
                result = self.run_cli()
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, "")
                self.assertIn(name, result.stderr)
                self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
