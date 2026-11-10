"""Формирование PlantUML и сохранение изображения графа в SVG."""

import os
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

RENDER_TIMEOUT = 60
SVG_TAG = "{http://www.w3.org/2000/svg}svg"


class VisualizationError(ValueError):
    """Ошибка запуска PlantUML или сохранения результата."""


def label(node):
    """Получить безопасную подпись узла графа."""
    value = f"{node[0]}@{node[1]}" if isinstance(node, tuple) else node
    return value.replace("\\", "\\\\").replace('"', '\\"')


def plantuml_text(graph):
    """Описать все вершины и ребра, включая циклы и изолированные узлы."""
    aliases = {node: f"n{index}" for index, node in enumerate(graph)}
    lines = ["@startuml", "!pragma layout smetana"]
    for node, alias in aliases.items():
        lines.append(f'rectangle "{label(node)}" as {alias}')
    for node, children in graph.items():
        for child in children:
            lines.append(f"{aliases[node]} --> {aliases[child]}")
    lines.append("@enduml")
    return "\n".join(lines) + "\n"


def render_svg(text):
    """Передать PlantUML локальному Java-процессу и проверить SVG."""
    default = Path(__file__).resolve().parents[1] / "tools/plantuml.jar"
    jar = Path(os.environ.get("PLANTUML_JAR", str(default)))
    if not jar.is_file():
        raise VisualizationError("Укажите путь к plantuml.jar в PLANTUML_JAR.")
    command = [os.environ.get("JAVA_EXE", "java"), "-Djava.awt.headless=true",
               "-jar", str(jar), "-pipe", "-tsvg", "-charset", "UTF-8"]
    try:
        result = subprocess.run(command, input=text.encode("utf-8"),
                                capture_output=True, timeout=RENDER_TIMEOUT)
    except (OSError, subprocess.TimeoutExpired) as error:
        raise VisualizationError(f"Не удалось запустить PlantUML: {error}")
    if result.returncode:
        raise VisualizationError("PlantUML завершился с ошибкой.")
    try:
        root = ET.fromstring(result.stdout)
    except ET.ParseError as error:
        raise VisualizationError("PlantUML вернул некорректный SVG.") from error
    if root.tag != SVG_TAG:
        raise VisualizationError("Результат PlantUML не является SVG.")
    return result.stdout


def save_graph(graph, output):
    """Сохранить описание .puml и SVG по заданному пути."""
    path = Path(output)
    text = plantuml_text(graph)
    try:
        svg = render_svg(text)
        path.with_suffix(".puml").write_text(text, encoding="utf-8")
        path.write_bytes(svg)
    except OSError as error:
        message = f"Не удалось сохранить граф: {error}"
        raise VisualizationError(message) from error
    return path
