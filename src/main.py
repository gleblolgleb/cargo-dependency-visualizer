"""Граф зависимостей Cargo: практическая работа № 2, вариант 27."""

import argparse
import sys

from cargo import CargoSource
from config import ConfigError, load_config
from graph import GraphError, build_graph, load_test_graph
from registry import RegistryError
from versions import VersionError


def node_label(node):
    """Вернуть имя тестового узла или имя и версию Cargo-пакета."""
    if isinstance(node, tuple):
        return f"{node[0]}@{node[1]}"
    return node


def get_graph(config, filename):
    """Выбрать тестовый файл или HTTP-индекс и выполнить DFS."""
    if config["test_mode"]:
        return load_test_graph(config, filename)
    source = CargoSource(config["repository"])
    root = config["package"].lower(), config["version"]
    return build_graph(root, source.children)


def main():
    """Построить и вывести граф без операций последующих этапов."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", help="путь к конфигурационному файлу JSON")
    args = parser.parse_args()
    try:
        config = load_config(args.config)
        graph = get_graph(config, args.config)
    except (ConfigError, GraphError, RegistryError, VersionError) as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 2
    for node, children in graph.items():
        targets = ", ".join(map(node_label, children)) or "(нет зависимостей)"
        print(f"{node_label(node)} -> {targets}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
