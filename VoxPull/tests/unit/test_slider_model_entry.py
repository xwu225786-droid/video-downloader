import importlib.util
from pathlib import Path
from unittest.mock import Mock


def entry():
    path = Path(__file__).resolve().parents[3] / 'scripts/识别滑块.py'
    spec = importlib.util.spec_from_file_location('slider_model_entry', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_single_target_is_not_discarded_when_source_outline_is_missing():
    boxes = Mock()
    boxes.tolist.return_value = [[151, 63, 214, 128, .937, 0]]
    model = Mock()
    result = entry().select_prediction([(boxes, None)], model)
    assert result == {'detected': True, 'box': [151, 63, 214, 128], 'confidence': .937}
    model.pick_out_mask.assert_not_called()


def test_multiple_shapes_keep_existing_model_matching_and_source_position():
    boxes = Mock()
    boxes.tolist.return_value = [[8, 60, 61, 125, .9, 0], [150, 60, 213, 125, .94, 0]]
    model = Mock()
    model.pick_out_mask.return_value = (boxes.tolist.return_value[1], None)
    result = entry().select_prediction([(boxes, object())], model)
    assert result['box'] == [150, 60, 213, 125]
    assert result['source_box'] == [8, 60, 61, 125]


def test_empty_model_result_stays_undetected():
    assert entry().select_prediction([], Mock())['detected'] is False
