from __future__ import annotations


class VoxPullError(Exception):
    code = "internal_error"
    default_message = "发生内部错误"
    retryable = False

    def __init__(self, message: str | None = None, *, detail: str | None = None) -> None:
        super().__init__(message or self.default_message)
        self.message = message or self.default_message
        self.detail = detail


class InvalidInputError(VoxPullError):
    code = "invalid_input"
    default_message = "请输入有效的抖音分享内容"


class UnsupportedUrlError(VoxPullError):
    code = "unsupported_url"
    default_message = "链接不受支持"


class CookieMissingError(VoxPullError):
    code = "cookie_missing"
    default_message = "请先初始化抖音 Cookie"
    retryable = True


class CookieRefreshRequiredError(VoxPullError):
    code = "cookie_refresh_required"
    default_message = "抖音登录状态需要更新，请重新登录后重试"
    retryable = True


class CookieCheckRequiredError(VoxPullError):
    code = "cookie_check_required"
    default_message = "下载器要求检查登录信息，请同步登录状态后重试；这不一定表示 Cookie 过期"
    retryable = True


class PlatformVerificationRequiredError(VoxPullError):
    code = "platform_verification_required"
    default_message = "抖音要求完成验证，请在登录浏览器中完成验证后重试"
    retryable = True


class PlatformAccessRestrictedError(VoxPullError):
    code = "platform_access_restricted"
    default_message = "抖音暂时拒绝此下载请求，请稍后重试；不能据此判断登录已过期"
    retryable = True


class BrowserFailedError(VoxPullError):
    code = "browser_failed"
    default_message = "浏览器访问抖音失败"
    retryable = True


class DownloadFailedError(VoxPullError):
    code = "download_failed"
    default_message = "视频下载失败"
    retryable = True


class AudioExtractionFailedError(VoxPullError):
    code = "audio_extraction_failed"
    default_message = "音频提取失败"
    retryable = True


class CoverExtractionFailedError(VoxPullError):
    code = "cover_extraction_failed"
    default_message = "无法提取视频第一帧，请确认视频文件完整且包含画面"
    retryable = True


class TranscriptionFailedError(VoxPullError):
    code = "transcription_failed"
    default_message = "语音识别失败"
    retryable = True


class DependencyMissingError(VoxPullError):
    code = "dependency_missing"
    default_message = "缺少运行依赖，请先完成初始化"


class TaskTimeoutError(VoxPullError):
    code = "task_timeout"
    default_message = "任务执行超时"
    retryable = True


class QueueFullError(VoxPullError):
    code = "queue_full"
    default_message = "任务队列已满，请稍后重试"
    retryable = True


class StorageLocationError(VoxPullError):
    code = "storage_location_failed"
    default_message = "无法更改保存位置"
    retryable = True


class MediaLocationError(VoxPullError):
    code = "media_location_failed"
    default_message = "无法打开文件夹"
    retryable = True


class SummaryUnavailableError(VoxPullError):
    code = "ai_summary_unavailable"
    default_message = "AI 总结服务未配置或暂不可用"


class SummaryConfigBusyError(VoxPullError):
    code = "ai_summary_config_busy"
    default_message = "AI 总结正在生成，请完成后再修改配置"
    retryable = True


class SummaryNotAvailableError(VoxPullError):
    code = "ai_summary_not_available"
    default_message = "该任务暂不支持生成 AI 总结"


class SummaryInvalidInputError(VoxPullError):
    code = "ai_summary_invalid_input"
    default_message = "AI 总结请求参数无效"


class SummaryRateLimitedError(VoxPullError):
    code = "ai_summary_rate_limited"
    default_message = "AI 总结请求过于频繁，请稍后重试"
    retryable = True


class SummaryProviderFailedError(VoxPullError):
    code = "ai_summary_provider_failed"
    default_message = "AI 总结服务调用失败"
    retryable = True


class SummaryTimeoutError(VoxPullError):
    code = "ai_summary_timeout"
    default_message = "AI 总结请求超时"
    retryable = True


class SummaryInvalidResponseError(VoxPullError):
    code = "ai_summary_invalid_response"
    default_message = "AI 总结服务返回了无效结果"
    retryable = True
