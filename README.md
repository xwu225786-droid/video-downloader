# 视频下载器

在本地保存分享链接中的视频、图文素材，提取字幕，并按需生成 AI 总结。基于 [VoxPull](https://github.com/memorate/VoxPull) 定制开发。

## 功能

- 支持抖音、小红书、Bilibili 等分享链接；实际可用性取决于平台访问权限、作品状态与下载器支持情况。
- 支持单条和批量处理、历史任务、素材标签、搜索和本地视频预览。
- 视频下载完成即可先预览，字幕识别和可选的 AI 总结在后续阶段继续处理。
- 本地 Whisper 语音识别，支持编辑、复制以及 TXT、SRT、时间轴导出。
- 可配置兼容 OpenAI 接口的 AI 总结服务；首次生成和重新生成均提供确认。
- 提供飞书机器人接入模块，默认关闭，需自行配置应用凭证与权限。

## 当前发布范围

这是当前应用的**源码版本**，主要在 Apple Silicon Mac 上验证。尚未提供通用安装包，也未完成 Windows 的安装适配验证。

仓库不包含下载视频、登录 Cookie、接口密钥、历史任务、运行环境和模型权重。首次使用仍需准备依赖与语音识别模型。

## 快速开始：macOS 原生运行

先安装 [Homebrew](https://brew.sh/) 并确保网络可用。通过 GitHub 下载 ZIP 并解压，或者克隆本仓库，然后进入其中的 `VoxPull` 目录：

```bash
cd VoxPull
brew install uv
bash scripts/bootstrap.sh
uv run vox start
```

初始化脚本会准备 Python 依赖、Chromium，并提示安装 FFmpeg、whisper.cpp 和下载 Whisper/VAD 模型。Whisper 模型约 514 MiB，完整安装所需空间会大于源码包。

启动后查看终端提供的地址，默认网页入口为 <http://127.0.0.1:18765/>。

停止服务：

```bash
uv run vox stop
```

需要登录或平台验证时，请在应用提供的浏览器窗口完成。AI 总结需在页面设置中填写你自己的接口地址、模型和 API Key；语音识别本身在本地运行。

## 使用流程

1. 粘贴分享链接，选择是否保留视频、提取字幕以及自动总结。
2. 点击开始处理，在任务卡片查看下载和后续处理状态。
3. 展开卡片后，可播放视频，在“字幕 / AI总结”之间切换。
4. 没有字幕时，默认折叠内容区；点击“字幕”后显示提取入口。
5. 没有总结时，在总结页生成；生成前会要求确认。

## Docker 与原开发环境入口

仓库保留 `Dockerfile`、`compose.yaml` 和 `scripts/` 中的维护工具，详见 [Docker 部署说明](docs/Docker部署.md)。

原双击 `.command` 入口依赖开发机的 `.local-tools` 布局，不是已经打包好的通用安装程序。首次在新电脑使用时，优先采用上面的原生初始化流程。

Docker 构建还需要准备 `docker/vendor/whisper-source.tar`，该生成文件不随源码上传，见 [依赖来源说明](docker/vendor/README.md)。

## 目录结构

```text
VoxPull/              主应用源码、测试、原生初始化脚本及依赖锁定文件
scripts/              原开发环境启动与维护工具
docker/               容器配置与依赖说明
docs/                 使用说明
captcha-recognizer/   第三方可选组件源码与许可，不含模型及本地测试数据
```

## 测试

在 `VoxPull` 目录中准备开发依赖后：

```bash
uv sync --extra dev
uv run pytest tests/unit/test_summarizer.py tests/unit/test_summary_service.py tests/integration/test_progressive_results.py tests/integration/test_card_transcript.py
```

部分浏览器、系统工具或原机器相关测试需要额外环境；本仓库没有打包开发机的运行环境和真实测试素材。

## 隐私与数据

下载素材、浏览器登录态和配置默认保存在本机。手动或自动生成总结时，相关文案会发送至你配置的 AI 接口；启用飞书机器人后，结果可能回传至飞书。

请仅处理你有权访问和保存的内容。

## 联系方式

邮箱：[2365120775@qq.com](mailto:2365120775@qq.com)

## 免责声明

本项目仅供个人使用、学习与交流。请遵守相关法律法规及平台规则，尊重他人的知识产权和隐私，不得用于违法违规用途。


## 上游项目与许可

本项目保留上游 MIT 许可及版权声明：

- [VoxPull](https://github.com/memorate/VoxPull)：应用基础，见 [LICENSE](LICENSE) 与 [VoxPull/LICENSE](VoxPull/LICENSE)。
- [captcha-recognizer](https://github.com/chenwei-zhao/captcha-recognizer)：可选第三方组件，见 [其许可文件](captcha-recognizer/LICENSE)。
- whisper.cpp、FFmpeg、Chromium 等运行依赖按各自许可证分发，本仓库不捆绑这些运行时和模型权重。
