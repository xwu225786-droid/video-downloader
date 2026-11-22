#!/bin/bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
"$ROOT/VoxPull/.venv/bin/python" "$ROOT/scripts/docker_app.py" stop
