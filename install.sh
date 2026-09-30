#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIRECTORY="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_EXECUTABLE="${COXERHUB_PYTHON:-python3.11}"

if ! command -v "$PYTHON_EXECUTABLE" >/dev/null 2>&1; then
    printf 'Python 3.11 is required. Install it or set COXERHUB_PYTHON to its executable.\n' >&2
    exit 1
fi

exec "$PYTHON_EXECUTABLE" "$PROJECT_DIRECTORY/setup.py" "$@"
