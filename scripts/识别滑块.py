"""Use the same local Slider model as 验证码/分离版/控制应用, without opening a browser."""
import json
import sys

def select_prediction(predictions, model) -> dict:
    result = {"detected": False, "box": [], "confidence": 0}
    if not predictions:
        return result
    boxes, masks = predictions[0]
    boxes = boxes.tolist()
    if len(boxes) == 1:
        # The supplied Slider.identify() also accepts a single detection. It may
        # identify the target while missing the white outline of the moving piece.
        target = boxes[0]
        return {"detected": True, "box": target[:4], "confidence": target[4]}
    if len(boxes) >= 2:
        segments = model.masks_to_segments(masks)
        target, _ = model.pick_out_mask(boxes, segments)
        source = min(boxes, key=lambda box: box[0])
        result = {"detected": True, "box": target[:4], "confidence": target[4],
                  "source_box": source[:4]}
    return result


if __name__ == "__main__":
    from captcha_recognizer.slider import Slider
    pixels = sys.stdin.buffer.read(3 * 1024 * 1024 + 1)
    if len(pixels) > 3 * 1024 * 1024:
        raise ValueError("图片过大")
    model = Slider()
    image = model.image_to_array(pixels)
    predictions = model.predict(image, conf=.5, iou=.8)
    result = select_prediction(predictions, model)
    print(json.dumps(result))
