from __future__ import annotations

import asyncio
import shutil
import subprocess
import sys
from pathlib import Path


class DirectoryPickerError(RuntimeError):
    pass


class NativeDirectoryPicker:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()

    async def choose(self, initial_directory: Path) -> Path | None:
        async with self._lock:
            from voxpull.infrastructure.host_bridge import bridge_configured, request_host, HostBridgeError
            if bridge_configured():
                try:
                    result = await request_host("choose", {"path": str(initial_directory)})
                    return Path(result["path"]) if result.get("path") else None
                except HostBridgeError as exc:
                    raise DirectoryPickerError(str(exc)) from exc
            return await asyncio.to_thread(self._choose_sync, initial_directory)

    def _choose_sync(self, initial_directory: Path) -> Path | None:
        if sys.platform == "darwin":
            return _choose_macos(initial_directory)
        if sys.platform == "win32":
            return _choose_windows(initial_directory)
        return _choose_linux(initial_directory)


def _choose_macos(initial_directory: Path) -> Path | None:
    script = """
on run argv
    set initialFolder to POSIX file (item 1 of argv)
    set chosenFolder to choose folder with prompt "选择 VoxPull 保存文件的位置" default location initialFolder
    return POSIX path of chosenFolder
end run
"""
    result = subprocess.run(
        ["osascript", "-e", script, "--", str(initial_directory)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return Path(result.stdout.strip()).resolve()
    if "User canceled" in result.stderr or "-128" in result.stderr:
        return None
    raise DirectoryPickerError(result.stderr.strip() or "无法打开文件夹选择器")


def _choose_windows(initial_directory: Path) -> Path | None:
    escaped_initial = str(initial_directory).replace("'", "''")
    command = (
        "[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new(); "
        "Add-Type -AssemblyName System.Windows.Forms; "
        "$dialog = New-Object System.Windows.Forms.FolderBrowserDialog; "
        f"$dialog.SelectedPath = '{escaped_initial}'; "
        "$dialog.Description = '选择 VoxPull 保存文件的位置'; "
        "if ($dialog.ShowDialog() -eq 'OK') { $dialog.SelectedPath }"
    )
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-STA", "-Command", command],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        raise DirectoryPickerError(result.stderr.strip() or "无法打开文件夹选择器")
    selected = result.stdout.strip()
    return Path(selected).resolve() if selected else None


def _choose_linux(initial_directory: Path) -> Path | None:
    if executable := shutil.which("zenity"):
        command = [
            executable,
            "--file-selection",
            "--directory",
            "--title=选择 VoxPull 保存文件的位置",
            f"--filename={initial_directory}/",
        ]
    elif executable := shutil.which("kdialog"):
        command = [executable, "--getexistingdirectory", str(initial_directory)]
    else:
        raise DirectoryPickerError("系统未安装可用的文件夹选择器")
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode == 0:
        return Path(result.stdout.strip()).resolve()
    if result.returncode == 1:
        return None
    raise DirectoryPickerError(result.stderr.strip() or "无法打开文件夹选择器")
