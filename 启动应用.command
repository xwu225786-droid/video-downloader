#!/bin/bash
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/scripts/runtime.sh"
"$TASK_PYTHON" "$TASK_ROOT/scripts/app_entry.py" start
open "http://127.0.0.1:$VOXPULL_PORT"
