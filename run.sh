#!/bin/sh
exec "${PYTHON_EXE:-python3}" "$(dirname "$0")/src/main.py" "$@"
