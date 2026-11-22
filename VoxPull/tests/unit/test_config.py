from voxpull.config import Settings


def test_parallelism_defaults_and_minimums(monkeypatch) -> None:
    names = (
        "VOXPULL_MAX_CONCURRENCY",
        "VOXPULL_DOWNLOAD_CONCURRENCY",
        "VOXPULL_FFMPEG_CONCURRENCY",
        "VOXPULL_WHISPER_CONCURRENCY",
        "VOXPULL_VAD_MODEL_PATH",
        "VOXPULL_SUMMARY_CONCURRENCY",
        "VOXPULL_SUMMARY_MAX_INPUT_CHARS",
    )
    for name in names:
        monkeypatch.delenv(name, raising=False)

    settings = Settings.from_env()
    assert settings.max_concurrency == 5
    assert settings.download_concurrency == 5
    assert settings.ffmpeg_concurrency == 2
    assert settings.whisper_concurrency == 2
    assert settings.vad_model_path == settings.model_path.parent / "ggml-silero-v6.2.0.bin"
    assert settings.summary_timeout_seconds == 180
    assert settings.summary_concurrency == 2
    assert settings.summary_max_input_chars == 200_000
    assert settings.deepseek_auth_path == settings.auth_dir / "deepseek-auth.json"
    assert settings.summary_auth_path == settings.auth_dir / "summary-auth.json"

    for name in names:
        monkeypatch.setenv(name, "0")

    settings = Settings.from_env()
    assert settings.max_concurrency == 1
    assert settings.download_concurrency == 1
    assert settings.ffmpeg_concurrency == 1
    assert settings.whisper_concurrency == 1
    assert settings.summary_concurrency == 1
    assert settings.summary_max_input_chars == 1
