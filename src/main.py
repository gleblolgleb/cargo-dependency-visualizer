"""Сбор прямых зависимостей Cargo: практическая работа № 2, вариант 27."""

import argparse
import json
import sys

from config import ConfigError, load_config
from registry import RegistryError, get_dependencies


def main():
    """Загрузить зависимости указанной версии и вывести их на экран."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", help="путь к конфигурационному файлу JSON")
    args = parser.parse_args()
    try:
        config = load_config(args.config)
        dependencies = get_dependencies(config)
    except (ConfigError, RegistryError) as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 2
    print(f"Прямые зависимости {config['package']}@{config['version']}:")
    if not dependencies:
        print("Прямых зависимостей нет.")
    for dependency in dependencies:
        print(json.dumps(dependency, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
