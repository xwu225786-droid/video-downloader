#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
MODEL_DIR="$ROOT_DIR/models"
MODEL_PATH="$MODEL_DIR/ggml-medium-q5_0.bin"
MODEL_TMP="$MODEL_PATH.part"
MODEL_REVISION="362722b3fdcd2300b58a8286933ead1c48619667"
MODEL_REPOSITORY="ggerganov/whisper.cpp"
MODEL_FILENAME="ggml-medium-q5_0.bin"
MODEL_SHA256="19fea4b380c3a618ec4723c3eef2eb785ffba0d0538cf43f8f235e7b3b34220f"
VAD_MODEL_PATH="$MODEL_DIR/ggml-silero-v6.2.0.bin"
VAD_MODEL_TMP="$VAD_MODEL_PATH.part"
VAD_MODEL_REPOSITORY="ggml-org/whisper-vad"
VAD_MODEL_FILENAME="ggml-silero-v6.2.0.bin"
VAD_MODEL_SHA256="2aa269b785eeb53a82983a20501ddf7c1d9c48e33ab63a41391ac6c9f7fb6987"

download_model() {
  local url
  local -a urls

  if [[ -n "${VOXPULL_MODEL_URL:-}" ]]; then
    urls=("$VOXPULL_MODEL_URL")
  else
    local mirror="${VOXPULL_HF_ENDPOINT:-https://hf-mirror.com}"
    local path="$MODEL_REPOSITORY/resolve/$MODEL_REVISION/$MODEL_FILENAME?download=true"
    urls=("${mirror%/}/$path" "https://huggingface.co/$path")
  fi

  for url in "${urls[@]}"; do
    echo "正在从 $url 下载…"
    if curl \
      --location \
      --fail \
      --progress-bar \
      --continue-at - \
      --connect-timeout 15 \
      --retry 3 \
      --retry-delay 2 \
      --retry-all-errors \
      "$url" \
      --output "$MODEL_TMP"; then
      return 0
    fi
    echo "当前下载源不可用，尝试下一个下载源…" >&2
  done

  echo "模型下载失败。可通过 VOXPULL_MODEL_URL 指定可访问的直链后重试。" >&2
  return 1
}

download_vad_model() {
  local url
  local -a urls

  if [[ -n "${VOXPULL_VAD_MODEL_URL:-}" ]]; then
    urls=("$VOXPULL_VAD_MODEL_URL")
  else
    local mirror="${VOXPULL_HF_ENDPOINT:-https://hf-mirror.com}"
    local path="$VAD_MODEL_REPOSITORY/resolve/main/$VAD_MODEL_FILENAME?download=true"
    urls=("${mirror%/}/$path" "https://huggingface.co/$path")
  fi

  for url in "${urls[@]}"; do
    echo "正在从 $url 下载…"
    if curl \
      --location \
      --fail \
      --progress-bar \
      --continue-at - \
      --connect-timeout 15 \
      --retry 3 \
      --retry-delay 2 \
      --retry-all-errors \
      "$url" \
      --output "$VAD_MODEL_TMP"; then
      return 0
    fi
    echo "当前下载源不可用，尝试下一个下载源…" >&2
  done

  echo "VAD 模型下载失败。可通过 VOXPULL_VAD_MODEL_URL 指定可访问的直链后重试。" >&2
  return 1
}

cd "$ROOT_DIR"

if ! command -v uv >/dev/null 2>&1; then
  echo "未找到 uv。请先执行：brew install uv"
  exit 1
fi

echo "同步 Python 依赖…"
uv sync --extra dev

echo "安装全局 vox 命令…"
uv tool install --editable "$ROOT_DIR" --force

echo "安装 Playwright Chromium…"
uv run playwright install chromium

missing_formulae=()
command -v ffmpeg >/dev/null 2>&1 || missing_formulae+=(ffmpeg)
command -v whisper-cli >/dev/null 2>&1 || missing_formulae+=(whisper-cpp)

if ((${#missing_formulae[@]})); then
  if ! command -v brew >/dev/null 2>&1; then
    echo "缺少 Homebrew，无法安装：${missing_formulae[*]}"
    exit 1
  fi
  answer="${VOXPULL_INSTALL_SYSTEM:-}"
  if [[ "$answer" != "1" ]]; then
    read -r -p "需要通过 Homebrew 安装 ${missing_formulae[*]}，继续吗？[y/N] " answer
  fi
  if [[ "$answer" == "1" || "$answer" =~ ^[Yy]$ ]]; then
    brew install "${missing_formulae[@]}"
  else
    echo "已跳过系统依赖安装。之后可执行：brew install ${missing_formulae[*]}"
  fi
fi

mkdir -p "$MODEL_DIR"
if [[ -f "$MODEL_PATH" ]] && echo "$MODEL_SHA256  $MODEL_PATH" | shasum -a 256 -c - >/dev/null 2>&1; then
  echo "Whisper 模型已存在且校验通过。"
else
  answer="${VOXPULL_DOWNLOAD_MODEL:-}"
  if [[ "$answer" != "1" ]]; then
    read -r -p "下载约 514 MiB 的 medium-q5_0 模型吗？[y/N] " answer
  fi
  if [[ "$answer" == "1" || "$answer" =~ ^[Yy]$ ]]; then
    download_model
    echo "$MODEL_SHA256  $MODEL_TMP" | shasum -a 256 -c -
    mv "$MODEL_TMP" "$MODEL_PATH"
  else
    echo "已跳过模型下载。应用会在系统状态中显示模型缺失。"
  fi
fi

if [[ -f "$VAD_MODEL_PATH" ]] && echo "$VAD_MODEL_SHA256  $VAD_MODEL_PATH" | shasum -a 256 -c - >/dev/null 2>&1; then
  echo "VAD 模型已存在且校验通过。"
else
  answer="${VOXPULL_DOWNLOAD_MODEL:-}"
  if [[ "$answer" != "1" ]]; then
    read -r -p "下载约 0.9 MiB 的 Silero VAD 模型吗？[y/N] " answer
  fi
  if [[ "$answer" == "1" || "$answer" =~ ^[Yy]$ ]]; then
    download_vad_model
    echo "$VAD_MODEL_SHA256  $VAD_MODEL_TMP" | shasum -a 256 -c -
    mv "$VAD_MODEL_TMP" "$VAD_MODEL_PATH"
  else
    echo "已跳过 VAD 模型下载。语音识别功能将不可用。"
  fi
fi

echo
echo "初始化完成。可用命令："
echo "  vox start"
echo "  vox restart"
echo "  vox status"
echo "  vox stop"
echo "  vox port"
echo "  vox unstall"
echo "  vox help"
