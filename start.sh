#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIRECTORY="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_EXECUTABLE="$PROJECT_DIRECTORY/.venv/bin/python"

if [[ ! -x "$PYTHON_EXECUTABLE" ]]; then
    printf 'Run bash install.sh first.\n' >&2
    exit 1
fi

exec "$PYTHON_EXECUTABLE" "$PROJECT_DIRECTORY/start.py" "$@"
