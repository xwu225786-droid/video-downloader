"""Selectable local or OpenAI-compatible multipart audio transcription."""
from __future__ import annotations

import asyncio
import io
import json
import math
import wave
from dataclasses import asdict, dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from voxpull.domain.errors import InvalidInputError, TranscriptionFailedError
from voxpull.domain.models import Transcript, TranscriptSegment
from voxpull.infrastructure.cookies import save_storage_state
from voxpull.infrastructure.transcriber import _to_simplified_chinese

SILICONFLOW_BASE = "https://api.siliconflow.cn/v1"
SILICONFLOW_MODEL = "FunAudioLLM/SenseVoiceSmall"
CHUNK_SECONDS = 300  # 16 kHz mono PCM: ~9.6 MB, below common API upload limits.


@dataclass(frozen=True)
class SpeechConfig:
    provider: str = "local"
    base_url: str = SILICONFLOW_BASE
    model: str = SILICONFLOW_MODEL
    api_key: str = field(default="", repr=False)


class SelectableTranscriber:
    def __init__(self, local, config_path: Path, *, transport=None, timeout=180):
        self.local = local
        self.config_path = config_path
        self.config = SpeechConfig()
        self.transport = transport
        self.timeout = timeout
        self._active = 0

    def status(self):
        config = self.config
        return {"provider": config.provider, "base_url": config.base_url, "model": config.model,
                "has_api_key": bool(config.api_key), "cloud": config.provider != "local"}

    def load(self):
        if self.config_path.exists():
            try:
                config = SpeechConfig(**json.loads(self.config_path.read_text(encoding="utf-8")))
                self._validate(config)
            except (OSError, TypeError, ValueError, InvalidInputError) as exc:
                raise RuntimeError("语音识别配置损坏，请检查本机配置文件") from exc
            self.config = config

    @staticmethod
    def _validate(config):
        if not all(isinstance(value, str) for value in asdict(config).values()):
            raise InvalidInputError("语音识别配置格式无效")
        if config.provider not in {"local", "siliconflow", "compatible"}:
            raise InvalidInputError("不支持的语音识别方式")
        if config.provider == "local":
            return
        try:
            parsed = urlsplit(config.base_url)
            _ = parsed.port
        except ValueError as exc:
            raise InvalidInputError("语音识别接口地址无效") from exc
        if (parsed.scheme not in {"https", "http"} or not parsed.hostname
                or parsed.username or parsed.password or parsed.query or parsed.fragment
                or len(config.base_url) > 512):
            raise InvalidInputError("语音识别接口地址须为不含凭据、查询参数的 HTTP(S) 地址")
        if not config.model.strip() or len(config.model) > 256:
            raise InvalidInputError("请填写有效的语音识别模型名称")
        if not config.api_key.strip() or len(config.api_key) > 2048:
            raise InvalidInputError("请填写语音识别 API Key")
        if not config.api_key.isascii() or any(c in config.api_key for c in '\r\n'):
            raise InvalidInputError("API Key 需要使用不含换行的英文字符")

    def configure(self, provider, base_url, model, api_key):
        if self._active:
            raise InvalidInputError("语音识别正在进行，请完成后再修改配置")
        base_url = base_url.strip().rstrip('/')
        # Accept either a /v1 base or the full transcription endpoint.
        if base_url.endswith('/audio/transcriptions'):
            base_url = base_url[:-len('/audio/transcriptions')]
        previous = self.config
        same_service = base_url == previous.base_url
        key = api_key.strip() or (previous.api_key if same_service else "")
        config = SpeechConfig(provider, base_url, model.strip(), key)
        self._validate(config)
        save_storage_state(self.config_path, asdict(config))
        self.config = config
        return self.status()

    def clear(self):
        if self._active:
            raise InvalidInputError("语音识别正在进行，请完成后再清除配置")
        self.config_path.unlink(missing_ok=True)
        self.config = SpeechConfig()

    async def transcribe(self, audio_path, language, work_dir, progress):
        config = self.config
        self._active += 1
        try:
            if config.provider == 'local':
                return await self.local.transcribe(audio_path, language, work_dir, progress)
            self._validate(config)
            progress(0, "正在准备云端语音识别")
            return await self._cloud(config, audio_path, language, progress)
        finally:
            self._active -= 1

    async def _cloud(self, config, audio_path, language, progress):
        texts, segments, languages = [], [], []
        try:
            with wave.open(str(audio_path), 'rb') as source:
                rate, channels, width = source.getframerate(), source.getnchannels(), source.getsampwidth()
                if rate != 16000 or channels != 1 or width != 2 or not source.getnframes():
                    raise TranscriptionFailedError("云端识别需要非空的 16 kHz 单声道 PCM 音频")
                frames_per_chunk = CHUNK_SECONDS * rate
                total = math.ceil(source.getnframes() / frames_per_chunk)
                async with httpx.AsyncClient(timeout=self.timeout, transport=self.transport,
                                             trust_env=False, follow_redirects=False) as client:
                    for index in range(total):
                        frames = await asyncio.to_thread(source.readframes, frames_per_chunk)
                        buffer = io.BytesIO()
                        with wave.open(buffer, 'wb') as target:
                            target.setparams((channels, width, rate, 0, 'NONE', 'not compressed'))
                            target.writeframes(frames)
                        progress(int(index * 100 / total), f"正在云端识别音频（{index + 1}/{total}）")
                        data = {"model": config.model}
                        if config.provider == 'compatible' and language != 'auto':
                            data['language'] = language
                        response = await client.post(config.base_url + '/audio/transcriptions',
                            headers={"Authorization": f"Bearer {config.api_key}"}, data=data,
                            files={"file": ("audio.wav", buffer.getvalue(), "audio/wav")})
                        if response.is_error or response.is_redirect:
                            hints = {401: "API Key 无效", 403: "接口无访问权限", 404: "请检查接口地址和模型名称",
                                     413: "音频超过接口上传限制", 429: "接口限流或额度不足，请稍后重试"}
                            raise TranscriptionFailedError(
                                f"云端语音识别失败（HTTP {response.status_code}）：" + hints.get(response.status_code, "服务暂时不可用"))
                        try:
                            payload = response.json()
                        except ValueError as exc:
                            raise TranscriptionFailedError("语音识别接口没有返回有效 JSON") from exc
                        if not isinstance(payload, dict) or not isinstance(payload.get('text'), str):
                            raise TranscriptionFailedError("语音识别接口返回内容缺少 text 文本")
                        text = _to_simplified_chinese(payload['text'].strip())
                        if text:
                            texts.append(text)
                        languages.append(payload.get('language', 'unknown'))
                        # Retain only real provider timestamps; never invent word timings.
                        offset = index * CHUNK_SECONDS * 1000
                        duration_ms = len(frames) * 1000 / (rate * channels * width)
                        raw_segments = payload.get('segments')
                        for item in raw_segments if isinstance(raw_segments, list) else []:
                            if not isinstance(item, dict):
                                continue
                            try:
                                start, end = float(item['start']) * 1000, float(item['end']) * 1000
                                value = _to_simplified_chinese(str(item['text']).strip())
                                if value and 0 <= start < end <= duration_ms + 1000:
                                    segments.append(TranscriptSegment(offset + int(start), offset + int(end), value))
                            except (KeyError, TypeError, ValueError, OverflowError):
                                continue
                        progress(int((index + 1) * 100 / total), "云端语音识别已完成" if index + 1 == total else "继续识别后续音频")
        except httpx.TimeoutException as exc:
            raise TranscriptionFailedError("云端语音识别超时，请稍后重试") from exc
        except httpx.HTTPError as exc:
            raise TranscriptionFailedError("无法连接语音识别服务，请检查接口地址和网络") from exc
        except (wave.Error, EOFError) as exc:
            raise TranscriptionFailedError("音频文件无效，无法进行云端识别") from exc
        if not texts:
            raise TranscriptionFailedError("接口未识别到有效语音，请检查视频音轨")
        detected = next((value for value in languages if isinstance(value, str) and value != 'auto'), 'unknown')
        return Transcript('\n'.join(texts), tuple(segments), detected)
