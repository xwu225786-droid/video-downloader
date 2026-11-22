#!/bin/bash
TASK_DIR="$(cd "$(dirname "$0")" && pwd)"
source "$TASK_DIR/scripts/runtime.sh"
"$TASK_PYTHON" "$TASK_DIR/scripts/download_internal_video.py" "$@"
read -r -p "按回车关闭窗口……"
