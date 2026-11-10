"""Поставщик транзитивных зависимостей реального индекса Cargo."""

import json
import re

from config import PACKAGE_PATTERN
from registry import RegistryError, download_index, validate_dependencies
from versions import VersionError, matches_requirement, version_key

CRATES_GIT = "https://github.com/rust-lang/crates.io-index"
CRATES_HTTP = "https://index.crates.io"


def parse_index(text, package):
    """Прочитать и проверить записи версий одного пакета."""
    records = []
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
            if not isinstance(entry, dict):
                raise ValueError("запись не является объектом")
            if str(entry.get("name", "")).lower() != package.lower():
                raise ValueError("имя пакета не совпадает")
            version_key(entry.get("vers"))
        except (ValueError, TypeError) as error:
            raise RegistryError(f"Некорректный индекс {package}.") from error
        records.append(entry)
    return records


def dependency_name(dependency):
    """Получить реальное имя пакета с учетом переименования."""
    name = dependency.get("package") or dependency["name"]
    if not isinstance(name, str) or not re.fullmatch(PACKAGE_PATTERN, name):
        raise RegistryError("Неверное имя зависимого пакета.")
    return name.lower()


def check_registry(dependency, repository):
    """Проверить, что зависимость принадлежит выбранному индексу."""
    registry = dependency.get("registry")
    if registry is None:
        return
    if not isinstance(registry, str):
        raise RegistryError("Неверный registry у зависимости.")
    registry = registry.removeprefix("sparse+").rstrip("/")
    if registry == CRATES_GIT:
        registry = CRATES_HTTP
    if registry != repository.rstrip("/"):
        raise RegistryError("Зависимость из другого индекса не поддержана.")


class CargoSource:
    """Загрузить каждый индекс один раз и выбрать версии зависимостей."""

    def __init__(self, repository):
        """Запомнить URL индекса и создать кеш на время одного запуска."""
        self.repository = repository
        self.cache = {}

    def records(self, package):
        """Получить все версии пакета с кешированием HTTP-ответа."""
        if package not in self.cache:
            text = download_index(self.repository, package)
            self.cache[package] = parse_index(text, package)
        return self.cache[package]

    def entry(self, node):
        """Найти точную версию узла в индексе пакета."""
        package, version = node
        for entry in self.records(package):
            if entry["vers"] == version:
                return entry
        raise RegistryError(f"Версия {package}@{version} не найдена.")

    def resolve(self, dependency):
        """Выбрать максимальную неотозванную подходящую версию ребра."""
        check_registry(dependency, self.repository)
        name = dependency_name(dependency)
        matches = [
            entry for entry in self.records(name)
            if not entry.get("yanked", False)
            and matches_requirement(entry["vers"], dependency["req"])
        ]
        if not matches:
            raise VersionError(f"Нет версии {name} для {dependency['req']}.")
        chosen = max(matches, key=lambda entry: version_key(entry["vers"]))
        return name, chosen["vers"]

    def children(self, node):
        """Получить узлы всех прямых зависимостей конкретной версии."""
        dependencies = validate_dependencies(self.entry(node))
        return [self.resolve(dependency) for dependency in dependencies]
