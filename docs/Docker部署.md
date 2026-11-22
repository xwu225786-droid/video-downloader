# 本机 Docker 部署

主应用、Python依赖、FFmpeg、Linux ARM版whisper.cpp与浏览器运行在Docker。素材、任务记录、标签、登录快照和模型使用本机持久化目录，不打入镜像；原素材绝对路径保持一致，容器重建后仍可查看历史任务。Mac原生浏览器配置在容器内只读，容器使用单独的持久浏览器卷。

启动和停止：

```bash
VoxPull/.venv/bin/python scripts/docker_app.py start
VoxPull/.venv/bin/python scripts/docker_app.py stop
VoxPull/.venv/bin/python scripts/docker_app.py status
```

初次构建：

```bash
VoxPull/.venv/bin/python scripts/docker_app.py build
```

日常可继续双击原来的“启动应用.command”和“停止应用.command”，当前会自动使用Docker；也可使用“Docker启动.command”和“Docker停止.command”。请先确保Docker Desktop已启动。应用地址为 <http://127.0.0.1:18765/>；验证窗口为 <http://127.0.0.1:6080/vnc.html?autoconnect=1&resize=scale>，也可在设置或卡片“继续验证”进入。两端口均只绑定本机，原始VNC端口不向宿主机发布。

容器首次启动是新的Linux浏览器环境，可能需要在网页验证窗口扫码登录或完成平台验证。登录、验证与抖音解析继续使用同一份容器浏览器配置。界面已移除“从Chrome同步”，统一通过“抖音登陆与验证窗口”登录。

“抖音登陆与验证窗口”会唤起当前浏览器页面；已有页面不重复加载，以保留正在进行的验证。原重复的“打开验证窗口”按钮已移除。容器桌面已关闭自动黑屏并固定为单桌面，解析完成后保持浏览器可见，避免打开验证窗口只看到空白黑屏。

Finder定位、Mac文件夹选择和Chrome同步通过一个轻量本机伴随进程完成。它使用权限为700的私有共享目录传递请求，不监听网络端口，也不挂载Docker控制套接字。路径操作仅允许已挂载的素材目录；请求过期后不会执行。模型、Cookie和素材不会进入构建上下文或镜像层。新选择的保存目录须位于已有挂载中，扩展保存目录前先修改Compose挂载。

`compose.yaml`定义持久化和本机端口；`docker/supervisord.conf`管理应用、虚拟显示器、窗口管理器和验证窗口。依赖版本与当前原生应用一致，见`docker/requirements.txt`。whisper.cpp源码来自本机已安装的上游提交727d3e7666485e12450746b523bfb4e7f057cc5e，含MIT许可证，构建归档不包含用户模型或素材。

Docker中使用CPU转写，无法沿用本机Metal加速，速度可能慢于Mac原生版。默认转写并发1、容器CPU上限4核、内存上限3GB，不调整其他现有容器。

2026年11月8日已完成本机部署，容器为`voxpull-app-1`，健康检查正常。切换及容器重建后核对了145份任务与批次记录、296个素材与索引文件以及全部标签，均保持不变；独立浏览器卷通过重建持久化检查。另在隔离实例中完成了历史视频预览、真实音频转写，以及通过网页验证窗口输入文字的实际测试。相关自动化测试126项通过。核对结果见`验证样例/Docker部署/正式部署验证.json`。

切换前会确认没有运行中的任务，备份任务和登录等小文件，停止原生服务，再启动容器；不会同时运行两个写入同一任务目录的实例。备份位于`.local-tools/state/docker-backups/`。旧素材不会复制进镜像或重新下载。

需要回到原生运行时：

```bash
VoxPull/.venv/bin/python scripts/docker_app.py rollback
```

回退停止容器并恢复切换前的Mac登录快照，保留最新任务和素材；原生浏览器配置保留在原位置。`docker compose down`不会删除浏览器卷；不要额外使用`down -v`，除非明确要清除容器浏览器状态。

实现参考：[Playwright Docker说明](https://playwright.dev/python/docs/docker)、[Docker Compose绑定挂载](https://docs.docker.com/reference/compose-file/services/#volumes)、[noVNC项目](https://github.com/novnc/noVNC)。
