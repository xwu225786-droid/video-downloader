import importlib.util
from pathlib import Path

import pytest

from voxpull.infrastructure.mouse_trajectory import VERSION, generate_trajectory
from voxpull.infrastructure.slider_operation import motion_schedule


@pytest.mark.parametrize('distance,start,seed', [(160, (500, 400), 2026), (-80, (300, 200), 42)])
def test_adapter_follows_supplied_xy_timestamps_and_random_endpoint(distance, start, seed):
    trajectory = generate_trajectory(distance, start=start, seed=seed)
    schedule = motion_schedule(seed, distance, start)
    assert trajectory['算法版本'] == VERSION == '分阶段连续运动-v3-首峰增强'
    assert len(schedule) == len(trajectory['鼠标位置轨迹'])
    for actual, expected in zip(schedule, trajectory['鼠标位置轨迹']):
        assert actual['time'] == expected['时间（毫秒）'] / 1000
        assert (actual['x'], actual['y']) == (expected['鼠标横坐标（像素）'], expected['鼠标纵坐标（像素）'])
    assert schedule[0]['x'] == start[0] and schedule[0]['y'] == start[1]
    assert schedule[-1]['x'] == pytest.approx(start[0] + distance)
    assert schedule[-1]['y'] != pytest.approx(start[1])
    assert 1.19582 <= schedule[-1]['time'] <= 1.937051
    assert any(point['progress'] == 0 and point['time'] > 0 for point in schedule)
    assert any(point['progress'] == 1 and point['time'] < schedule[-1]['time'] for point in schedule)


def test_bundled_algorithm_matches_user_file_without_modifying_parameters():
    source = Path(__file__).parent / 'fixtures' / 'mouse_trajectory_reference.py'
    if not source.is_file():
        pytest.skip('User reference file is only available on the original Mac')
    spec = importlib.util.spec_from_file_location('user_mouse_trajectory', source)
    reference = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reference)
    for seed in [1, 2026, 1234567]:
        assert generate_trajectory(180, start=(500, 400), seed=seed) == reference.generate_trajectory(
            180, start=(500, 400), seed=seed)
