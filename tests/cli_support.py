"""Запуск CLI в тестах с отдельной подменой внешнего рендерера."""

import contextlib
import io
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import main


def run_app(command, cwd=None, **options):
    """Проверить CLI без Java; рендерер проверяется отдельными тестами."""
    stdout, stderr = io.StringIO(), io.StringIO()
    previous = Path.cwd()
    try:
        if cwd:
            os.chdir(cwd)
        with patch.object(sys, "argv", command[1:]):
            with patch("main.save_graph"):
                with contextlib.redirect_stdout(stdout):
                    with contextlib.redirect_stderr(stderr):
                        code = main.main()
    finally:
        os.chdir(previous)
    return subprocess.CompletedProcess(command, code, stdout.getvalue(),
                                       stderr.getvalue())
