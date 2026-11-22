"""Request bounded slider operations on the task's existing browser page."""
import json
import sys
import urllib.request


def main(event: dict) -> None:
    if event.get("auth_status") != "verification_required":
        print("需要本人处理：", event.get("message", ""), flush=True)
        return
    request = urllib.request.Request(
        "http://127.0.0.1:18765/api/auth/douyin/operate",
        data=json.dumps({"job_id": event["job_id"]}).encode(),
        headers={"Content-Type": "application/json", "Origin": "http://127.0.0.1:18765"},
    )
    with urllib.request.urlopen(request, timeout=240) as response:
        report = json.load(response)
        keys = ('status', 'message', 'directory', 'motion_algorithm', 'drag_duration_seconds',
                'attempt_count', 'attempts', 'retry_stop_reason')
        print(json.dumps({key: report[key] for key in keys if key in report},
                         ensure_ascii=False), flush=True)
    # 仍可在这里补充自己的提醒代码。


if __name__ == "__main__":
    main(json.load(sys.stdin))
