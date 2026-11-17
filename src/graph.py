"""Итеративный DFS и загрузка тестового репозитория."""

import re
from pathlib import Path

from config import ConfigError, local_path, read_json


class GraphError(ValueError):
    """Ошибка структуры графа или корневого пакета."""


class DependencyGraph(dict):
    """Список смежности с отметкой нераскрытых граничных узлов."""

    def __init__(self):
        """Создать пустой граф и набор граничных узлов."""
        super().__init__()
        self.truncated = set()


def build_graph(root, children, max_depth=None):
    """Выполнить DFS без рекурсии с ограничением расстояния от корня."""
    graph = DependencyGraph()
    depths, expanded = {}, set()
    stack = [(root, 0)]
    while stack:
        node, depth = stack.pop()
        if node in depths and depth >= depths[node]:
            continue
        depths[node] = depth
        graph.setdefault(node, [])
        if max_depth is not None and depth >= max_depth:
            if node not in expanded:
                graph.truncated.add(node)
            continue
        graph.truncated.discard(node)
        if node not in expanded:
            graph[node] = list(dict.fromkeys(children(node)))
            expanded.add(node)
        stack.extend((child, depth + 1) for child in reversed(graph[node]))
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
    return build_graph(root, graph.__getitem__, config.get("max_depth"))
