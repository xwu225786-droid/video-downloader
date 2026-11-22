"""Show the current idle browser and run a bounded slider-operation test."""
import argparse
import json
import time
import urllib.parse
import urllib.request
import webbrowser


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="打开当前滑块界面并测试，失败后刷新重试")
    parser.add_argument('--attempts', type=int, choices=(1, 2, 3), default=3)
    parser.add_argument('--no-open', action='store_true', help='不再打开测试界面')
    args = parser.parse_args()
    base = "http://127.0.0.1:18765/api/auth/douyin"
    if not args.no_open:
        with urllib.request.urlopen(base + '/capabilities', timeout=5) as response:
            console = json.load(response).get('browser_console_url')
        if console and urllib.parse.urlsplit(console).hostname in {'127.0.0.1', 'localhost'}:
            webbrowser.open(console)
            print('测试界面：' + console, flush=True)
    for _ in range(30):
        with urllib.request.urlopen(base + "/status", timeout=5) as response:
            status = json.load(response)
        if status.get("status") != "checking":
            break
        time.sleep(.5)
    if status.get("status") != "verification_required" or not status.get("target_url"):
        raise SystemExit("当前页面没有待处理滑块，未执行操作")
    request = urllib.request.Request(
        base + "/operate-current", data=json.dumps({"target_url": status["target_url"],
                                                    "max_attempts": args.attempts}).encode(),
        headers={"Content-Type": "application/json", "Origin": "http://127.0.0.1:18765"},
    )
    with urllib.request.urlopen(request, timeout=240) as response:
        report = json.load(response)
        keys = ('status', 'message', 'directory', 'motion_algorithm', 'drag_duration_seconds',
                'attempt_count', 'attempts', 'retry_stop_reason')
        print(json.dumps({key: report[key] for key in keys if key in report},
                         ensure_ascii=False, indent=2))
