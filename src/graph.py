"""Итеративный DFS и загрузка тестового репозитория."""

import re
from pathlib import Path

from config import ConfigError, local_path, read_json


class GraphError(ValueError):
    """Ошибка структуры графа или корневого пакета."""


def build_graph(root, children):
    """Построить достижимый граф DFS со стеком, сохраняя ребра циклов."""
    graph = {}
    stack = [root]
    while stack:
        node = stack.pop()
        if node in graph:
            continue
        neighbors = list(dict.fromkeys(children(node)))
        graph[node] = neighbors
        stack.extend(reversed(neighbors))
    return graph


def validate_test_graph(graph):
    """Проверить имена пакетов и ссылки в тестовом репозитории."""
    for name, children in graph.items():
        if not re.fullmatch(r"[A-Z]+", name):
            raise GraphError("Имена тестовых пакетов: только A-Z.")
        if not isinstance(children, list):
            raise GraphError(f"{name}: ожидается список зависимостей.")
        for child in children:
            if not isinstance(child, str) or child not in graph:
                raise GraphError(f"{name}: неизвестная зависимость {child}.")
    return graph


def read_test_repository(config, filename):
    """Прочитать и проверить весь тестовый репозиторий."""
    path = local_path(config["repository"], Path(filename).parent)
    try:
        graph = validate_test_graph(read_json(path))
    except ConfigError as error:
        raise GraphError(str(error)) from error
    return graph


def load_test_graph(config, filename):
    """Построить достижимый граф тестового репозитория."""
    graph = read_test_repository(config, filename)
    root = config["package"]
    if root not in graph:
        raise GraphError(f"Корневой пакет {root} отсутствует в репозитории.")
    return build_graph(root, graph.__getitem__)
