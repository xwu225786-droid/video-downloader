import asyncio
import json
import time

import pytest

from voxpull.infrastructure.host_bridge import HostBridgeError, host_request
from voxpull.infrastructure.host_bridge_server import checked_path, process_request


async def test_private_bridge_roundtrip_and_path_validation(tmp_path, monkeypatch):
    directory=tmp_path/'bridge'
    directory.mkdir()
    (directory/'health.json').write_text('{}')
    monkeypatch.setenv('VOXPULL_HOST_BRIDGE_DIR',str(directory))
    root=tmp_path/'media'
    root.mkdir()
    folder=root/'作品'
    folder.mkdir()
    observed=[]
    monkeypatch.setattr('voxpull.infrastructure.host_bridge_server.NativePathOpener._reveal_sync', lambda self,path: observed.append(path))
    request=asyncio.create_task(asyncio.to_thread(host_request,'reveal',{'path':str(folder)},timeout=2))
    async with asyncio.timeout(2):
        while not list(directory.glob('*.request.json')):
            await asyncio.sleep(.01)
    process_request(next(directory.glob('*.request.json')),[root],tmp_path/'state.json')
    assert await request=={'opened':True}
    assert observed==[folder]
    assert not list(directory.glob('*.request.json')) and not list(directory.glob('*.response.json'))
    with pytest.raises(ValueError,match='未挂载'):
        checked_path(str(tmp_path/'outside'),[root])
    (root/'escape').symlink_to(tmp_path,target_is_directory=True)
    with pytest.raises(ValueError,match='未挂载'):
        checked_path(str(root/'escape/outside'),[root])


def test_expired_requests_never_open_host_files(tmp_path,monkeypatch):
    request=tmp_path/('a'*32+'.request.json')
    request.write_text(json.dumps({'action':'reveal','payload':{'path':'/tmp'},'expires_at':time.time()-1}))
    called=[]
    monkeypatch.setattr('voxpull.infrastructure.host_bridge_server.dispatch',lambda *args:called.append(args))
    process_request(request,[tmp_path],tmp_path/'state.json')
    response=json.loads((tmp_path/('a'*32+'.response.json')).read_text())
    assert not response['ok'] and not called


def test_offline_bridge_fails_without_pending_requests(tmp_path,monkeypatch):
    monkeypatch.setenv('VOXPULL_HOST_BRIDGE_DIR',str(tmp_path))
    with pytest.raises(HostBridgeError,match='未运行'):
        host_request('reveal',{'path':'/tmp'},timeout=.01)
    assert not list(tmp_path.iterdir())
