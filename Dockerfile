# syntax=docker/dockerfile:1
ARG PYTHON_IMAGE=python:3.14.10-slim-bookworm
FROM ${PYTHON_IMAGE}
ARG APP_UID=1000
ARG APP_GID=1000
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 DISPLAY=:99 \
    PLAYWRIGHT_BROWSERS_PATH=/opt/playwright VOXPULL_BROWSER_DISPLAY_BACKEND=x11 VOXPULL_HOST=0.0.0.0 VOXPULL_PORT=18765 \
    VOXPULL_FFMPEG_BIN=/usr/bin/ffmpeg VOXPULL_MAX_CONCURRENCY=2 VOXPULL_TRANSCRIPTION_CONCURRENCY=1
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates ffmpeg xvfb x11vnc novnc websockify openbox \
    dbus-x11 fonts-noto-cjk supervisor tini x11-utils && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY docker/configure_desktop.py /tmp/configure_desktop.py
RUN python /tmp/configure_desktop.py && rm /tmp/configure_desktop.py
COPY VoxPull/pyproject.toml VoxPull/README.md VoxPull/LICENSE /app/
COPY docker/requirements.txt /app/docker-requirements.txt
RUN pip install --no-cache-dir -r /app/docker-requirements.txt && \
    python -m playwright install --with-deps chromium && chmod -R a+rX /opt/playwright
COPY VoxPull/src /app/src
RUN pip install --no-cache-dir --no-deps .
RUN (getent group "${APP_GID}" || groupadd -g "${APP_GID}" app) && \
    useradd --uid "${APP_UID}" --gid "${APP_GID}" --create-home --shell /bin/bash app && \
    mkdir -p /run/voxpull /data /home/app/.voxpull-browser && chown app:"${APP_GID}" /run/voxpull /data /home/app/.voxpull-browser
COPY docker/supervisord.conf /etc/voxpull-supervisord.conf
USER app
EXPOSE 18765 6080
HEALTHCHECK --interval=20s --timeout=5s --start-period=30s --retries=3 CMD python -c "import urllib.request,socket; urllib.request.urlopen('http://127.0.0.1:18765/api/jobs/capabilities',timeout=2); urllib.request.urlopen('http://127.0.0.1:6080/vnc.html',timeout=2); s=socket.create_connection(('127.0.0.1',5900),2); assert s.recv(12).startswith(b'RFB '); s.close()"
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["/usr/bin/supervisord", "-c", "/etc/voxpull-supervisord.conf"]
