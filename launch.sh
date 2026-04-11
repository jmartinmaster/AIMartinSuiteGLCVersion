#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -f ".venv/bin/activate" ]; then
	source ".venv/bin/activate"
elif [ -f "venv/bin/activate" ]; then
	source "venv/bin/activate"
fi

PYTHON_BIN="${PYTHON:-python3}"
if [ -x ".venv/bin/python" ]; then
	PYTHON_BIN=".venv/bin/python"
elif [ -x "venv/bin/python" ]; then
	PYTHON_BIN="venv/bin/python"
fi

nohup "$PYTHON_BIN" main.py > /dev/null 2>&1 &