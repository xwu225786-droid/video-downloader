import sys
from pathlib import Path

from voxpull.infrastructure.cookies import write_netscape_cookie_file


def test_writes_netscape_cookie_file(tmp_path: Path) -> None:
    destination = tmp_path / "cookies.txt"
    write_netscape_cookie_file(
        [
            {
                "name": "sessionid",
                "value": "secret",
                "domain": ".douyin.com",
                "path": "/",
                "expires": 2_000_000_000,
                "httpOnly": True,
                "secure": True,
            }
        ],
        destination,
    )
    text = destination.read_text()
    assert text.startswith("# Netscape HTTP Cookie File")
    assert "#HttpOnly_.douyin.com\tTRUE\t/\tTRUE\t2000000000\tsessionid\tsecret" in text
    if sys.platform != "win32":
        assert destination.stat().st_mode & 0o077 == 0
