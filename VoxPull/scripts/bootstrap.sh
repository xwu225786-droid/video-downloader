#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
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

echo "初始化完成。可用命令："
echo "  vox start"
echo "  vox restart"
echo "  vox status"
echo "  vox stop"
echo "  vox port"
echo "  vox unstall"
echo "  vox help"
