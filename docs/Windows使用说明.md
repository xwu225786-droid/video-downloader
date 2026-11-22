# Windows 使用说明

支持范围：Windows 11 x64（Intel / AMD），原生运行，不需要 WSL / Docker。安装脚本使用系统自带 Windows PowerShell；首次下载需要访问 GitHub、Python / PyPI、Chromium 分发站点及 Hugging Face。

## 安装和使用

1. 下载仓库 ZIP 并完整解压到当前用户可写目录。
2. 双击根目录 `Windows安装.bat`，等待依赖和模型安装完成。
3. 双击 `Windows启动.bat`，浏览器自动打开，默认地址 `http://127.0.0.1:18765/`。
4. 双击 `Windows停止.bat` 停止后台进程。下载或识别过程中停止，会中断当前任务，可在下次启动后重试。

不需要预先安装 Python、GitHub 客户端、FFmpeg 或显卡计算环境。默认使用 CPU 版 whisper.cpp。不要只复制 `whisper-cli.exe`，其配套 DLL 必须一起保留。

下载失败可重新运行安装程序。若移动了安装目录，也需重新运行安装程序以更新本地运行路径。需要保留原任务时，同时保留 `VoxPull/data`。

## 文件位置

| 内容 | 位置 |
| --- | --- |
| Python 环境 | `VoxPull/.venv` |
| 运行工具和下载缓存 | `.local-tools/windows` |
| 浏览器 | `.local-tools/browsers` |
| Whisper / VAD 模型 | `VoxPull/models` |
| 素材、任务、登录态、AI 设置 | `VoxPull/data`（素材目录可在页面设置中调整） |
| 服务状态和日志 | `.local-tools/state` |

这些目录均不提交到 GitHub。AI 总结需要在设置中填写自己的接口地址、模型、密钥，已有的首次生成 / 重新生成确认流程保持不变。

## PowerShell 用法

在仓库根目录运行：

```powershell
# 完整安装；加 -Dev 同时安装测试工具
powershell -NoProfile -ExecutionPolicy Bypass -File .\VoxPull\scripts\bootstrap-windows.ps1
# 启动 / 状态 / 重启 / 停止
powershell -NoProfile -ExecutionPolicy Bypass -File .\VoxPull\scripts\manage-windows.ps1 -Action start
powershell -NoProfile -ExecutionPolicy Bypass -File .\VoxPull\scripts\manage-windows.ps1 -Action status
powershell -NoProfile -ExecutionPolicy Bypass -File .\VoxPull\scripts\manage-windows.ps1 -Action restart
powershell -NoProfile -ExecutionPolicy Bypass -File .\VoxPull\scripts\manage-windows.ps1 -Action stop
```

`ExecutionPolicy Bypass` 只作用于当前启动的 PowerShell 进程，不更改系统策略。若单位设备禁止运行脚本，需按设备管理要求处理。

可在当前 PowerShell 进程先设置以下变量，再运行安装或启动命令：

- `VOXPULL_PORT`：服务端口，默认 18765。
- `VOXPULL_HF_ENDPOINT`：模型下载站点，默认先尝试 `https://hf-mirror.com`，失败后尝试 Hugging Face。
- `VOXPULL_MODEL_URL` / `VOXPULL_VAD_MODEL_URL`：模型直链，仍须通过固定 SHA-256 校验。
- `VOXPULL_FFMPEG_BIN` / `VOXPULL_WHISPER_BIN`：自行准备的工具完整路径。

`bootstrap-windows.ps1 -SkipModels` 仅适合不需要语音识别的安装；提取字幕前必须重新运行完整安装。脚本自身出错或运行工具版本不正确时会停止，不会显示安装成功。

## 兼容范围和验证

Whisper 的 Windows 官方程序存在非 ASCII 参数编码问题；应用在识别时使用临时相对路径和文件链接，完成后自动清理，不要求把素材标题或用户目录改为英文。模型同盘时使用硬链接，无法链接时退回复制。

Windows 适配包括文件锁、后台启停、子进程树清理、中文路径、保留设备名和原生文件夹选择器。自动测试覆盖依赖安装、任务与素材持久化、下载后的字幕 / 总结流程、桌面和窄屏卡片界面、真实 FFmpeg / Whisper / VAD 识别。

[Windows 自动测试记录](https://github.com/xwu225786-droid/video-downloader/actions/workflows/windows.yml) 由 GitHub Windows runner 执行。测试使用本地样例和模拟接口，不代表各平台的受限作品、登录或网络环境均可访问。系统 Chrome 登录态导入目前仅支持 macOS；Windows 请使用应用内的登录窗口。原 Docker 维护入口未做 Windows 迁移。

运行包来自 [uv](https://github.com/astral-sh/uv/releases)、[FFmpeg Windows 构建](https://www.gyan.dev/ffmpeg/builds/) 和 [whisper.cpp](https://github.com/ggml-org/whisper.cpp/releases)，固定下载链接与校验值见 `VoxPull/scripts/windows-runtime.json`。运行依赖适用各自许可证，项目不将这些二进制上传到源码仓库。
