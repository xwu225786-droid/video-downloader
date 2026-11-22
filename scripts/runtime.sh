#!/bin/bash
# All runtime files and credentials stay under this project.
TASK_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PATH="$TASK_ROOT/.local-tools/bin:$PATH"
export PLAYWRIGHT_BROWSERS_PATH="$TASK_ROOT/.local-tools/browsers"
export VOXPULL_HOST=127.0.0.1
export VOXPULL_PORT=18765
export VOXPULL_STATE_DIR="$TASK_ROOT/.local-tools/state"
export VOXPULL_DATA_DIR="$TASK_ROOT/VoxPull/data"
export VOXPULL_MODEL_PATH="$TASK_ROOT/VoxPull/models/ggml-medium-q5_0.bin"
export VOXPULL_VAD_MODEL_PATH="$TASK_ROOT/VoxPull/models/ggml-silero-v6.2.0.bin"
export VOXPULL_FFMPEG_BIN="$TASK_ROOT/.local-tools/bin/ffmpeg"
export VOXPULL_WHISPER_BIN="$TASK_ROOT/.local-tools/whisper.cpp/build/bin/whisper-cli"
export VOXPULL_WHISPER_CONCURRENCY=1
export VOXPULL_MAX_CONCURRENCY=2
TASK_PYTHON="$TASK_ROOT/VoxPull/.venv/bin/python"
