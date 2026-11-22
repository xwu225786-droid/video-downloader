"""Fixed host-side model invocation; no caller-controlled executable or URL."""
import base64
import json
import subprocess
from pathlib import Path


def recognize(payload: dict) -> dict:
    encoded = payload.get("image", "")
    if not isinstance(encoded, str) or len(encoded) > 4 * 1024 * 1024:
        raise ValueError("图片数据无效")
    pixels = base64.b64decode(encoded, validate=True)
    if not pixels.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("仅支持PNG截图")
    root = Path(__file__).resolve().parents[4]
    result = subprocess.run(
        [str(root / "captcha-recognizer/.venv/bin/python"), str(root / "scripts/识别滑块.py")],
        input=pixels, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        timeout=20, check=True, cwd=root,
    )
    return json.loads(result.stdout)
