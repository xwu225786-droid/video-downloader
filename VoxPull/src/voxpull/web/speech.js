(() => {
  const get = (id) => document.getElementById(`speech-${id}`);
  const form = get('form');
  if (!form) return;
  const feedback = (message, error = false) => {
    get('feedback').textContent = message;
    get('feedback').style.color = error ? 'var(--danger, #b42318)' : '';
  };
  const mode = () => {
    const cloud = get('provider').value !== 'local';
    get('cloud-fields').classList.toggle('hidden', !cloud);
    get('mode-hint').textContent = cloud
      ? '保存后，新开始的字幕识别将使用此云端接口，不再需要本地 Whisper 模型。'
      : '保存后使用本地 Whisper，音频不会上传到语音识别服务。';
  };
  const render = (config) => {
    get('provider').value = config.provider;
    get('base').value = config.base_url || 'https://api.siliconflow.cn/v1';
    get('model').value = config.model || 'FunAudioLLM/SenseVoiceSmall';
    get('key').value = '';
    get('key').placeholder = config.has_api_key ? '已保存；相同接口留空可保留原 Key' : '填写语音识别服务的 Key';
    get('state').textContent = !config.cloud ? '本地 Whisper' : config.provider === 'siliconflow' ? '硅基流动' : '云端接口';
    mode();
  };
  get('provider').addEventListener('change', () => {
    if (get('provider').value === 'siliconflow') {
      get('base').value = 'https://api.siliconflow.cn/v1';
      get('model').value = 'FunAudioLLM/SenseVoiceSmall';
    }
    mode();
    feedback('尚未保存，请点击“保存语音模型”使更改生效。');
  });
  const busy = (value) => {
    get('save').disabled = value;
    get('clear').disabled = value;
  };
  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    busy(true);
    feedback('正在保存…');
    try {
      const config = await api('/api/transcription/config', { method: 'PUT', body: JSON.stringify({
        provider: get('provider').value, base_url: get('base').value.trim(),
        model: get('model').value.trim(), api_key: get('key').value.trim(),
      }) });
      render(config);
      feedback('识别设置已保存。');
      void loadSystem();
    } catch (error) { feedback(error.message, true); }
    finally { busy(false); }
  });
  get('clear').addEventListener('click', async () => {
    if (!window.confirm('清除云端识别配置并切换回本地 Whisper？')) return;
    busy(true);
    try {
      await api('/api/transcription/config', { method: 'DELETE' });
      render(await api('/api/transcription/config'));
      feedback('已清除接口配置，恢复本地识别。');
      void loadSystem();
    } catch (error) { feedback(error.message, true); }
    finally { busy(false); }
  });
  api('/api/transcription/config').then(render).catch((error) => {
    feedback(`读取识别配置失败：${error.message}`, true);
    get('save').disabled = true;
  });
})();
