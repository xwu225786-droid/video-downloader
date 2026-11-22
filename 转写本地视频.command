#!/bin/bash
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/scripts/runtime.sh"
if [ "$#" -eq 0 ]; then
    TASK_INPUT="$(osascript -e 'POSIX path of (choose file with prompt "请选择要生成逐字稿的视频或音频")')" || exit 0
    set -- "$TASK_INPUT"
fi
for TASK_INPUT in "$@"; do
    "$TASK_PYTHON" "$TASK_ROOT/scripts/transcribe_local.py" "$TASK_INPUT"
done
open "$TASK_ROOT/逐字稿"
