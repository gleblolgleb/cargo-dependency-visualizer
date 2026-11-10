"""Проверки текста PlantUML, ошибок рендерера и сохранения SVG."""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from visualize import VisualizationError, plantuml_text, render_svg, save_graph

SVG = b'<svg xmlns="http://www.w3.org/2000/svg"><text>A</text></svg>'


class VisualizationTests(unittest.TestCase):
    """Проверить структуру диаграммы и обработку результатов PlantUML."""

    def test_graph_text(self):
        """Сохранить изолированный узел, цикл и версии в PlantUML."""
        graph = {"A": ["B"], "B": ["A"], "C": []}
        text = plantuml_text(graph)
        self.assertIn('rectangle "C" as n2', text)
        self.assertIn("n0 --> n1", text)
        self.assertIn("n1 --> n0", text)
        self.assertTrue(text.startswith("@startuml\n"))
        self.assertTrue(text.endswith("@enduml\n"))
        text = plantuml_text({("a", "1.0.0"): [], ("a", "2.0.0"): []})
        self.assertIn('"a@1.0.0"', text)
        self.assertIn('"a@2.0.0"', text)

    def test_save(self):
        """Сохранить согласованную пару PUML/SVG в заданный каталог."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "graph.svg"
            with patch("visualize.render_svg", return_value=SVG) as render:
                self.assertEqual(save_graph({"A": []}, path), path)
            self.assertEqual(path.read_bytes(), SVG)
            self.assertEqual(path.with_suffix(".puml").read_text("utf-8"),
                             render.call_args.args[0])

    def test_renderer_results(self):
        """Отклонить не-SVG, ошибку Java и поврежденный XML."""
        with tempfile.TemporaryDirectory() as directory:
            jar = Path(directory) / "plantuml.jar"
            jar.touch()
            with patch.dict(os.environ, PLANTUML_JAR=str(jar)):
                for code, data in ((0, b"bad"), (0, b"<html/>"), (1, SVG)):
                    with self.subTest(code=code, data=data):
                        result = subprocess.CompletedProcess([], code, data)
                        with patch("visualize.subprocess.run",
                                   return_value=result):
                            with self.assertRaises(VisualizationError):
                                render_svg("@startuml\n@enduml\n")
                result = subprocess.CompletedProcess([], 0, SVG)
                with patch("visualize.subprocess.run", return_value=result):
                    self.assertEqual(render_svg("text"), SVG)

    def test_missing_jar(self):
        """Сообщить о необходимости настроить PlantUML."""
        with patch.dict(os.environ, PLANTUML_JAR="missing-plantuml.jar"):
            with self.assertRaises(VisualizationError):
                render_svg("text")


if __name__ == "__main__":
    unittest.main()
