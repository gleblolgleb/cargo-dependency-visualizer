"""Минимальное CLI-приложение: практическая работа № 2, вариант 27."""

import argparse
import sys

from config import ConfigError, PARAMETERS, load_config


def main():
    """Прочитать JSON и вывести параметры либо сообщение об ошибке."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("config", help="путь к конфигурационному файлу JSON")
    args = parser.parse_args()
    try:
        data = load_config(args.config)
    except ConfigError as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 2
    for name in PARAMETERS:
        value = data[name]
        if isinstance(value, bool):
            value = str(value).lower()
        print(f"{name}={value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
