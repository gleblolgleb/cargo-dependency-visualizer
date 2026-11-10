"""Визуализация графа зависимостей Cargo: вариант 27, этап 5."""

from pathlib import Path

import argparse
import sys

from cargo import CargoSource
from config import ConfigError, load_config, local_path
from graph import (
    GraphError, build_graph, load_test_graph,
)
from registry import RegistryError
from versions import VersionError
from visualize import VisualizationError, save_graph


def node_label(node):
    """Вернуть имя тестового узла или имя и версию Cargo-пакета."""
    if isinstance(node, tuple):
        return f"{node[0]}@{node[1]}"
    return node


def get_graph(config, filename):
    """Выбрать источник и область поиска для текущего режима."""
    if config["test_mode"]:
        return load_test_graph(config, filename)
    source = CargoSource(config["repository"])
    root = config["package"].lower(), config["version"]
    return build_graph(root, source.children)


def format_result(config, graph):
    """Подготовить текстовый список смежности визуализируемого графа."""
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
        output = local_path(config["output"], Path(args.config).parent)
        save_graph(graph, output)
    except (ConfigError, GraphError, RegistryError, VersionError,
            VisualizationError) as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 2
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
