import pytest

from voxpull.infrastructure.material_reorganization import _rewrite_paths


@pytest.mark.parametrize(('value', 'mapping', 'expected'), [
    (r'C:\素材\旧\视频.mp4', {r'C:\素材\旧': r'C:\素材\新'}, r'C:\素材\新\视频.mp4'),
    ('C:/素材/OLD/video.mp4', {r'c:\素材\old': r'C:\素材\new'}, r'C:\素材\new\video.mp4'),
    (r'\\server\share\old\nested\a.txt', {r'\\server\share\old': r'\\server\share\new'}, r'\\server\share\new\nested\a.txt'),
    ('/tmp/old/nested/a.txt', {'/tmp/old': '/tmp/new'}, '/tmp/new/nested/a.txt'),
    (r'C:\素材\old-backup\a.txt', {r'C:\素材\old': r'C:\素材\new'}, r'C:\素材\old-backup\a.txt'),
    ('relative/a.txt', {'relative': '/new'}, 'relative/a.txt'),
])
def test_rewrite_paths_supports_windows_and_posix_components(value, mapping, expected):
    assert _rewrite_paths({'paths': [value]}, mapping) == {'paths': [expected]}
