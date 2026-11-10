"""Обратные зависимости с использованием DFS предыдущего этапа."""

from graph import GraphError, build_graph


def reverse_dependencies(graph, target):
    """Найти все пакеты, зависящие от target прямо или транзитивно."""
    if target not in graph:
        raise GraphError("Запрошенный пакет отсутствует в графе.")
    reverse = {node: [] for node in graph}
    for node, children in graph.items():
        for child in children:
            reverse[child].append(node)
    visited = build_graph(target, reverse.__getitem__)
    return [node for node in visited if node != target]


def find_target(graph, value, test_mode):
    """Найти точный тестовый узел или Cargo-узел вида имя@версия."""
    if test_mode:
        if value not in graph:
            raise GraphError(f"Пакет {value} отсутствует в репозитории.")
        return value
    name, separator, version = value.partition("@")
    target = name.lower(), version
    if not separator or target not in graph:
        raise GraphError("reverse_package: ожидается имя@версия из графа.")
    return target
