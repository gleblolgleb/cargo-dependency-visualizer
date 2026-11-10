"""Прямые и обратные зависимости Cargo: вариант 27, этап 4."""

import argparse
import sys

from cargo import CargoSource
from config import ConfigError, load_config
from graph import (
    GraphError, build_graph, load_test_graph, read_test_repository,
)
from registry import RegistryError
from reverse import find_target, reverse_dependencies
from versions import VersionError


def node_label(node):
    """Вернуть имя тестового узла или имя и версию Cargo-пакета."""
    if isinstance(node, tuple):
        return f"{node[0]}@{node[1]}"
    return node


def get_graph(config, filename):
    """Выбрать источник и область поиска для текущего режима."""
    if config["test_mode"]:
        if "reverse_package" in config:
            return read_test_repository(config, filename)
        return load_test_graph(config, filename)
    source = CargoSource(config["repository"])
    root = config["package"].lower(), config["version"]
    return build_graph(root, source.children)


def format_result(config, graph):
    """Подготовить прямой граф или результат обратного обхода."""
    if "reverse_package" in config:
        target = find_target(
            graph, config["reverse_package"], config["test_mode"])
        nodes = reverse_dependencies(graph, target)
        header = f"Обратные зависимости {node_label(target)}:"
        return [header] + ([node_label(n) for n in nodes] or ["Нет."])
    lines = []
    for node, children in graph.items():
        targets = ", ".join(map(node_label, children)) or "(нет зависимостей)"
        lines.append(f"{node_label(node)} -> {targets}")
    return lines


def main():
    """Вывести результат выбранного режима или сообщение об ошибке."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", help="путь к конфигурационному файлу JSON")
    args = parser.parse_args()
    try:
        config = load_config(args.config)
        graph = get_graph(config, args.config)
        lines = format_result(config, graph)
    except (ConfigError, GraphError, RegistryError, VersionError) as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 2
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
