"""Чтение и проверка конфигурации первого этапа."""

import json
import re
from pathlib import Path
from urllib.parse import urlsplit

MAX_CONTROL_CODE = 32
MIN_PADDED_LENGTH = 2
PARAMETERS = ("package", "repository", "test_mode", "version", "output")
PACKAGE_PATTERN = r"[A-Za-z][A-Za-z0-9_-]*"
VERSION_PATTERN = (
    r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
)


class ConfigError(ValueError):
    """Ошибка файла конфигурации или его параметров."""


def read_json(path):
    """Прочитать объект JSON из файла UTF-8."""
    try:
        with path.open(encoding="utf-8") as source:
            data = json.load(source)
    except (OSError, UnicodeError, ValueError) as error:
        raise ConfigError(f"Не удалось прочитать JSON: {error}") from error
    if not isinstance(data, dict):
        raise ConfigError("Конфигурация должна быть объектом JSON.")
    return data


def check_field(name, value):
    """Проверить тип и базовые ограничения одного параметра."""
    if name == "test_mode":
        if not isinstance(value, bool):
            raise ConfigError("test_mode: ожидается true или false.")
        return
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{name}: ожидается непустая строка.")
    if value != value.strip() or any(ord(c) < MAX_CONTROL_CODE for c in value):
        raise ConfigError(f"{name}: недопустимые пробелы или символы.")


def check_fields(data):
    """Проверить наличие и типы пяти параметров."""
    for name in PARAMETERS:
        if name not in data:
            raise ConfigError(f"Отсутствует параметр: {name}.")
        check_field(name, data[name])
    if "reverse_package" in data:
        check_field("reverse_package", data["reverse_package"])
    unknown = set(data) - set(PARAMETERS) - {"reverse_package"}
    if unknown:
        names = ", ".join(sorted(unknown))
        raise ConfigError(f"Неизвестные параметры: {names}.")


def local_path(value, base):
    """Определить путь относительно каталога конфигурации."""
    path = Path(value)
    return path if path.is_absolute() else base / path


def check_repository(data, base):
    """Проверить URL или наличие файла тестового репозитория."""
    value = data["repository"]
    if data["test_mode"]:
        if not local_path(value, base).is_file():
            raise ConfigError("repository: тестовый файл не найден.")
        return
    try:
        address = urlsplit(value)
        valid = address.scheme in ("http", "https") and address.hostname
        if not valid or any(char.isspace() for char in value):
            raise ValueError("ожидается URL HTTP(S)")
        address.port
    except ValueError as error:
        raise ConfigError(f"repository: неверный URL ({error}).") from error


def check_output(value, base):
    """Проверить имя будущего изображения, не создавая файл."""
    path = local_path(value, base)
    if path.suffix.lower() != ".svg":
        raise ConfigError("output: требуется имя файла с расширением .svg.")
    if any(char in path.name for char in '<>:"|?*'):
        raise ConfigError("output: недопустимые символы в имени файла.")
    if not path.parent.is_dir() or path.is_dir():
        raise ConfigError("output: неверный путь к файлу изображения.")


def check_version(value):
    """Проверить формат версии пакета Cargo (SemVer)."""
    if not re.fullmatch(VERSION_PATTERN, value):
        raise ConfigError("version: ожидается версия вида 1.2.3.")
    prerelease = value.split("+", maxsplit=1)[0].partition("-")[2]
    for part in prerelease.split("."):
        padded = len(part) >= MIN_PADDED_LENGTH and part.startswith("0")
        if part.isdigit() and padded:
            raise ConfigError("version: ведущие нули в prerelease.")


def load_config(filename):
    """Загрузить и проверить все параметры без обращения к сети."""
    path = Path(filename)
    data = read_json(path)
    check_fields(data)
    if not re.fullmatch(PACKAGE_PATTERN, data["package"]):
        raise ConfigError("package: недопустимое имя пакета.")
    check_version(data["version"])
    try:
        check_repository(data, path.parent)
        check_output(data["output"], path.parent)
    except (OSError, ValueError) as error:
        if isinstance(error, ConfigError):
            raise
        raise ConfigError(f"Ошибка пути в конфигурации: {error}") from error
    return data
