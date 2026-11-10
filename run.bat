@echo off
setlocal
if defined PYTHON_EXE (
    "%PYTHON_EXE%" "%~dp0src\main.py" %*
) else (
    py -3 "%~dp0src\main.py" %*
)
exit /b %errorlevel%
