"""Adapt the separate browser worker's geometry and mouse steps to an owned page."""
from __future__ import annotations

import asyncio
import base64
import json
import math
import secrets
import struct
from pathlib import Path
from uuid import uuid4

from voxpull.infrastructure.mouse_trajectory import generate_trajectory


# Each group must identify exactly one visible scene, piece, handle and track.
# The first group is the supplied worker's local page; the others are candidates
# for the current site's slider. Unsupported or ambiguous layouts remain manual.
PROFILES = (
    (".captcha_verify_img--wrapper", "#captcha-verify_img_slide",
     ".captcha-slider .dragger-item", ".captcha-slider-box"),
    ("#scene", "#piece", '[role="slider"][aria-label="拖动滑块"]', "#track"),
    ("#captcha-verify-image", ".captcha_verify_img_slide", ".secsdk-captcha-drag-icon",
     ".secsdk-captcha-drag-wrapper"),
)


def motion_schedule(seed: int, distance: float = 1, start=(0, 0)) -> list[dict]:
    """Adapt the supplied algorithm's millisecond/CSS-pixel output without reshaping it."""
    trajectory = generate_trajectory(distance, start=start, seed=seed)
    return schedule_from_trajectory(trajectory)


def schedule_from_trajectory(trajectory: dict) -> list[dict]:
    return [{"time": point['时间（毫秒）'] / 1000,
             "x": point['鼠标横坐标（像素）'], "y": point['鼠标纵坐标（像素）'],
             "progress": progress['水平进度']}
            for point, progress in zip(trajectory['鼠标位置轨迹'], trajectory['水平进度随时间变化'])]


async def refresh_slider(page, still_active) -> dict:
    """Click the observed refresh control and require a stable replacement image."""
    try:
        scene, _, _, _ = await locate(page)
        before = await scene.screenshot(scale="css", timeout=2000)
        control = None
        for frame in page.frames:
            for selector in ('.vc-captcha-refresh', '#challenge [data-action="refresh"]'):
                visible = [item for item in await frame.locator(selector).all() if await item.is_visible()]
                if len(visible) == 1:
                    control = visible[0]
                    break
            if control is not None:
                break
        if control is None or not still_active():
            return {"refreshed": False, "message": "未找到唯一刷新控件或原任务已退出等待"}
        await control.click(timeout=2000)
        previous = None
        for _ in range(40):
            await asyncio.sleep(.2)
            if not still_active() or page.is_closed():
                break
            try:
                scene, _, _, _ = await locate(page)
                loaded = await scene.evaluate("""el => Array.from(el.querySelectorAll('img'))
                    .every(img => img.complete && img.naturalWidth > 0)""")
                current = await scene.screenshot(scale="css", timeout=1000)
                if loaded and current != before and current == previous:
                    return {"refreshed": True, "message": "已点击刷新并确认新图片加载"}
                previous = current
            except Exception:
                continue
        return {"refreshed": False, "message": "已点击刷新，但未确认新图片加载，停止重试"}
    except Exception as exc:
        return {"refreshed": False, "message": str(exc)}


async def inspect_layout(page) -> dict:
    """Read visible control structure only, excluding cookies, URLs and input values."""
    frames = []
    for frame in page.frames:
        try:
            elements = await frame.evaluate("""() => {
                const nodes = document.querySelectorAll(
                    'img,canvas,[role="slider"],[class*="captcha"],[id*="captcha"],[class*="drag"],[id*="drag"]');
                return Array.from(nodes).filter(el => {
                    const r = el.getBoundingClientRect();
                    return r.width > 0 && r.height > 0 && getComputedStyle(el).visibility !== 'hidden';
                }).slice(0, 100).map(el => {
                    const r = el.getBoundingClientRect();
                    return {tag: el.tagName, id: el.id, class: String(el.className).slice(0,240),
                        role: el.getAttribute('role'), width: r.width, height: r.height,
                        x: r.x, y: r.y, parentId: el.parentElement?.id,
                        parentClass: String(el.parentElement?.className).slice(0,240),
                        naturalWidth: el.naturalWidth, naturalHeight: el.naturalHeight};
                });
            }""")
            frames.append({"elements": elements})
        except Exception as exc:
            frames.append({"error": type(exc).__name__})
    return {"frames": frames}


async def operation_feedback(page) -> str:
    for frame in getattr(page, 'frames', []):
        try:
            if frame is not page.main_frame and not await (await frame.frame_element()).is_visible():
                continue
            for root in await frame.locator('.vc-captcha-verify, #challenge').all():
                if await root.is_visible():
                    text = await root.inner_text(timeout=1000)
                    for line in text.splitlines():
                        if any(word in line for word in ('操作过快', '验证失败', '验证成功', '网络异常')):
                            return line.strip()[:300]
        except Exception:
            continue
    return ''


async def piece_alpha_bounds(piece) -> dict | None:
    """Read the displayed piece's transparent padding; never read page answers."""
    return await piece.evaluate("""img => {
        if (img.tagName !== 'IMG' || !img.complete || !img.naturalWidth) return null;
        const width = img.naturalWidth, height = img.naturalHeight;
        if (width * height > 1000000) return null;
        try {
            const canvas = document.createElement('canvas');
            canvas.width = width; canvas.height = height;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(img, 0, 0);
            const data = ctx.getImageData(0, 0, width, height).data;
            let left=width, top=height, right=-1, bottom=-1;
            for (let y=0; y<height; y++) for (let x=0; x<width; x++) {
                if (data[(y*width+x)*4+3] > 16) {
                    left=Math.min(left,x); right=Math.max(right,x);
                    top=Math.min(top,y); bottom=Math.max(bottom,y);
                }
            }
            return right >= left ? {left, top, right:right+1, bottom:bottom+1, width, height} : null;
        } catch { return null; }
    }""")


def drag_plan(boxes: dict, prediction: dict, image_width: int, handle_travel: float) -> dict:
    box = prediction.get("box") or []
    confidence = prediction.get("confidence", 0)
    if (not prediction.get("detected") or len(box) != 4
            or not isinstance(confidence, (float, int)) or confidence < .5):
        raise ValueError("未识别到可靠的目标位置")
    source_box = prediction.get("source_box")
    if source_box is not None and len(source_box) != 4:
        raise ValueError("拼图片块识别范围无效")
    values = [*box, *(source_box or []), confidence, image_width, handle_travel,
              *(v for b in boxes.values() for v in b.values())]
    if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in values):
        raise ValueError("位移数据无效")
    image, piece, handle = boxes["image"], boxes["piece"], boxes["handle"]
    if image_width <= 0 or image["width"] <= 0 or handle_travel <= 0:
        raise ValueError("控件移动范围无效")
    initial = piece["x"] - image["x"]
    piece_travel = image["width"] - piece["width"] - initial
    scale = image["width"] / image_width
    source_offset = source_box[0] * scale - initial if source_box else 0
    if not -2 <= source_offset <= piece["width"] * .6:
        raise ValueError("识别到的起始图块与页面位置不一致")
    target = box[0] * scale - source_offset
    if target < initial + piece["width"] * .5:
        raise ValueError("仅识别到起始图块，尚未可靠识别目标位置")
    if piece_travel <= 0 or not initial <= target <= initial + piece_travel:
        raise ValueError("预测位置超出可移动范围")
    delta = (target - initial) / piece_travel * handle_travel
    start = [handle["x"] + handle["width"] / 2, handle["y"] + handle["height"] / 2]
    return {"start": start, "end": [start[0] + delta, start[1]], "delta_css_px": delta,
            "source_offset_css_px": source_offset}


async def locate(page):
    for frame in page.frames:
        for selectors in PROFILES:
            controls = []
            for selector in selectors:
                candidates = frame.locator(selector)
                visible = [item for item in await candidates.all() if await item.is_visible()]
                if len(visible) != 1:
                    break
                controls.append(visible[0])
            if len(controls) == 4:
                return controls
    raise ValueError("当前页面控件尚未适配或定位不唯一，保留人工操作")


async def operate(page, predict, still_active, evidence_dir: Path) -> dict:
    folder = evidence_dir / uuid4().hex
    folder.mkdir(parents=True, exist_ok=True)
    report = {"status": "manual", "directory": str(folder)}
    try:
        await page.screenshot(path=str(folder / "before.png"), scale="css", timeout=3000)
        scene, piece, handle, track = await locate(page)
        await handle.scroll_into_view_if_needed(timeout=2000)
        images_ready = """el => (el.tagName === 'IMG' ? [el] : Array.from(el.querySelectorAll('img')))
            .every(img => img.complete && img.naturalWidth > 0)"""
        for _ in range(30):
            if await scene.evaluate(images_ready):
                break
            if not still_active():
                raise ValueError("原任务已退出等待，取消本次操作")
            await asyncio.sleep(.1)
        else:
            raise ValueError("滑块图片尚未加载完成，保留人工操作")
        boxes = {name: await item.bounding_box() for name, item in
                 (("image", scene), ("piece", piece), ("handle", handle), ("track", track))}
        if not all(boxes.values()):
            raise ValueError("网页控件未显示")
        pixels = await scene.screenshot(scale="css", timeout=3000)
        (folder / "input.png").write_bytes(pixels)
        width = struct.unpack(">I", pixels[16:20])[0]
        prediction = await predict(base64.b64encode(pixels).decode("ascii"))
        report["prediction"] = prediction
        alpha = await piece_alpha_bounds(piece)
        if alpha:
            report["piece_alpha"] = alpha
        if (prediction.get("detected") and not prediction.get("source_box")
                and await piece.evaluate("el => el.tagName") == "IMG"):
            if not alpha:
                raise ValueError("未取得起始图块边界，保留人工操作")
            image = boxes["image"]
            part = boxes["piece"]
            ratio = width / image["width"]
            prediction = {**prediction, "source_origin": "visible_piece_alpha", "source_box": [
                (part["x"] - image["x"] + alpha["left"] / alpha["width"] * part["width"]) * ratio,
                (part["y"] - image["y"] + alpha["top"] / alpha["height"] * part["height"]) * ratio,
                (part["x"] - image["x"] + alpha["right"] / alpha["width"] * part["width"]) * ratio,
                (part["y"] - image["y"] + alpha["bottom"] / alpha["height"] * part["height"]) * ratio,
            ]}
        report["prediction"] = prediction
        track_width = await track.evaluate("el => el.offsetWidth")
        if track_width <= 0:
            raise ValueError("滑动轨道尺寸无效")
        viewport_scale = boxes["track"]["width"] / track_width
        travel = (await track.evaluate("el => el.clientWidth")
                  - await handle.evaluate("el => el.offsetWidth")) * viewport_scale
        report["controls"] = boxes
        report["viewport_scale"] = viewport_scale
        plan = drag_plan(boxes, prediction, width, travel)
        report["drag_plan"] = plan
        # Prediction may take time. Never drag a changed image or another task's page.
        if not still_active() or page.is_closed():
            raise ValueError("原任务已退出等待，取消本次操作")
        current = await scene.screenshot(scale="css", timeout=3000)
        if current != pixels:
            raise ValueError("识别期间图片已变化，保留人工操作")
        for name, item in (("image", scene), ("piece", piece), ("handle", handle), ("track", track)):
            if await item.bounding_box() != boxes[name]:
                raise ValueError("识别期间控件位置已变化，取消本次操作")
        seed = secrets.randbits(64)
        trajectory = generate_trajectory(plan['delta_css_px'], start=tuple(plan['start']),
                                         seed=seed)
        schedule = schedule_from_trajectory(trajectory)
        plan['end'] = [schedule[-1]['x'], schedule[-1]['y']]
        report['motion_algorithm'] = trajectory['算法版本']
        report['trajectory_plan'] = trajectory
        report["motion_seed"] = seed
        report["motion_schedule"] = schedule
        await page.mouse.move(*plan["start"])
        await page.mouse.down()
        started = asyncio.get_running_loop().time()
        previous_position = tuple(plan['start'])
        commands = 0
        try:
            for point in schedule:
                if not still_active():
                    raise ValueError("原任务已退出等待，停止本次拖动")
                remaining = started + point["time"] - asyncio.get_running_loop().time()
                if remaining > 0:
                    await asyncio.sleep(remaining)
                if not still_active():
                    raise ValueError("原任务已退出等待，停止本次拖动")
                position = (point['x'], point['y'])
                if position != previous_position:
                    await page.mouse.move(*position)
                    previous_position = position
                    commands += 1
        finally:
            await page.mouse.up()
        report["drag_duration_seconds"] = asyncio.get_running_loop().time() - started
        report['mouse_move_commands'] = commands
        report.update(status="performed", message="已在原页面执行拖动，是否通过由原任务继续检查")
        await page.screenshot(path=str(folder / "after.png"), scale="css", timeout=3000)
    except Exception as exc:
        report["message"] = str(exc)
    finally:
        (folder / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    return report
