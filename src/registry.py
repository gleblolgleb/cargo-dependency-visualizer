"""Получение прямых зависимостей указанной версии из индекса Cargo."""

from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

TIMEOUT_SECONDS = 20
HTTP_NOT_FOUND = 404
SHORT_NAME_LENGTH = 3
PREFIX_LENGTH = 2
PREFIX_END = 4


class RegistryError(ValueError):
    """Ошибка загрузки или формата данных репозитория."""


def index_path(package):
    """Сформировать путь к файлу пакета по правилам индекса Cargo."""
    name = package.lower()
    length = len(name)
    if length < SHORT_NAME_LENGTH:
        return f"{length}/{name}"
    if length == SHORT_NAME_LENGTH:
        return f"3/{name[0]}/{name}"
    return f"{name[:PREFIX_LENGTH]}/{name[PREFIX_LENGTH:PREFIX_END]}/{name}"


def download_index(repository, package):
    """Загрузить индекс одного пакета по HTTP без вызова Cargo."""
    url = repository.rstrip("/") + "/" + index_path(package)
    request = Request(url, headers={"User-Agent": "Variant27-Stage3"})
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return response.read().decode("utf-8")
    except HTTPError as error:
        if error.code == HTTP_NOT_FOUND:
            raise RegistryError(f"Пакет {package} не найден.") from error
        raise RegistryError(f"Ошибка HTTP: {error.code}.") from error
    except (URLError, OSError, UnicodeError) as error:
        raise RegistryError(f"Не удалось прочитать индекс: {error}") from error


def validate_dependencies(entry):
    """Проверить прямые зависимости без исключения отдельных категорий."""
    dependencies = entry.get("deps")
    if not isinstance(dependencies, list):
        raise RegistryError("deps: ожидается список зависимостей.")
    for dependency in dependencies:
        if not isinstance(dependency, dict):
            raise RegistryError("Зависимость должна быть объектом JSON.")
        for field in ("name", "req"):
            value = dependency.get(field)
            if not isinstance(value, str) or not value.strip():
                raise RegistryError(f"Зависимость: неверное поле {field}.")
    return dependencies
