(() => {
  const get = (id) => document.getElementById(`speech-${id}`);
  const dialog = get('dialog');
  if (!dialog) return;
  let saved = { provider: 'local', base_url: '', model: '', has_api_key: false };
  let manual = false;
  let modelsController = null;
  let revision = 0;
  const feedback = (message = '', error = false) => {
    get('feedback').textContent = message;
    get('feedback').classList.toggle('hidden', !message);
    get('feedback').style.color = error ? 'var(--color-status-error)' : 'var(--color-status-success)';
  };
  const model = () => manual ? get('model-custom').value.trim() : get('model').value.trim();
  const payload = () => ({ provider: get('provider').value, base_url: get('base').value.trim(), model: model(), api_key: get('key').value.trim() });
  const status = (message, state = 'idle') => {
    get('model-status').querySelector('.summary-status-text').textContent = message;
    get('model-status').dataset.state = state;
  };
  const closeList = () => {
    get('model-list').classList.add('hidden');
    get('model-trigger').setAttribute('aria-expanded', 'false');
  };
  const setModels = (models, selected = '') => {
    const names = [...new Set([selected, ...models].filter(Boolean))];
    get('model').replaceChildren();
    get('model-list').replaceChildren();
    for (const name of names) {
      const option = new Option(name, name);
      get('model').append(option);
      const button = document.createElement('button');
      button.type = 'button'; button.className = 'summary-model-option';
      button.setAttribute('role', 'option'); button.setAttribute('aria-selected', String(name === selected));
      const check = document.createElement('span'); check.className = 'summary-model-option-check'; check.textContent = '✓';
      const label = document.createElement('span'); label.className = 'summary-model-option-name'; label.textContent = name;
      button.append(check, label);
      button.addEventListener('click', () => {
        get('model').value = name; get('model-value').textContent = name;
        get('model-list').querySelectorAll('button').forEach((item) => item.setAttribute('aria-selected', String(item === button)));
        revision += 1; feedback(); closeList(); get('model-trigger').focus();
      });
      get('model-list').append(button);
    }
    get('model').value = selected || names[0] || '';
    get('model').disabled = !names.length;
    get('model-trigger').disabled = !names.length;
    get('model-value').textContent = get('model').value || '请先获取模型';
  };
  const mode = () => {
    const cloud = get('provider').value !== 'local';
    get('cloud-fields').classList.toggle('hidden', !cloud);
    get('test-hint').classList.toggle('hidden', !cloud);
    get('mode-hint').textContent = cloud
      ? '部分语音模型不返回时间轴；仍可使用纯文本和后续 AI 总结。'
      : '使用本地 Whisper，不上传音频；测试连接仅检查本地识别依赖。';
  };
  const renderStatus = (config) => {
    saved = config;
    get('state').textContent = !config.cloud ? '本地 Whisper' : '已配置';
    get('hint').textContent = !config.cloud ? '使用本地 Whisper，音频不上传到语音识别服务。' : `使用 ${config.model} 识别语音，音频将发送至该服务。`;
    populate();
  };
  const normalizeBase = (value) => value.trim().replace(/\/+$/, '').replace(/\/audio\/transcriptions$/, '');
  const loadModels = async () => {
    modelsController?.abort();
    if (get('provider').value === 'local') return;
    const current = payload();
    const canReuse = saved.has_api_key && normalizeBase(current.base_url) === normalizeBase(saved.base_url);
    if (!/^https?:\/\//.test(current.base_url) || (!current.api_key && !canReuse)) {
      status('填写接口地址和 API Key 后，将自动获取可用模型。'); return;
    }
    const controller = new AbortController(); modelsController = controller;
    const selected = model(); status('正在获取可用模型…', 'busy');
    try {
      const result = await api('/api/transcription/models', { method: 'POST', signal: controller.signal,
        body: JSON.stringify({ ...current, model: current.model || 'asr' }) });
      if (!Array.isArray(result.models) || !result.models.length) throw new Error('接口未返回语音模型');
      if (!manual) setModels(result.models, selected);
      status(`已获取 ${result.models.length} 个模型，可选择或手动输入。`, 'ok');
    } catch (error) {
      if (error.name !== 'AbortError') status(`获取模型失败，已保留当前模型；也可手动输入。${error.message}`, 'error');
    }
  };
  const populate = () => {
    revision += 1; manual = false;
    get('provider').value = saved.provider;
    get('base').value = saved.base_url || 'https://api.siliconflow.cn/v1';
    get('key').value = ''; get('key').type = 'password'; get('key-toggle').textContent = '显示';
    get('key-toggle').setAttribute('aria-pressed', 'false');
    get('key').placeholder = saved.has_api_key ? '已保存，留空则保留原 Key' : 'sk-...';
    get('model-custom').classList.add('hidden'); get('model-trigger').classList.remove('hidden');
    get('model-manual').textContent = '手动输入';
    setModels([], saved.model || 'FunAudioLLM/SenseVoiceSmall');
    feedback(); closeList(); mode();
  };
  document.getElementById('settings-open').addEventListener('click', () => { if (get('settings').open) void loadModels(); });
  get('settings').addEventListener('toggle', () => { if (get('settings').open) void loadModels(); });
  get('provider').addEventListener('change', () => {
    if (get('provider').value === 'siliconflow') {
      get('base').value = 'https://api.siliconflow.cn/v1';
      setModels(['FunAudioLLM/SenseVoiceSmall', 'TeleAI/TeleSpeechASR'], 'FunAudioLLM/SenseVoiceSmall');
      get('model-custom').value = 'FunAudioLLM/SenseVoiceSmall';
    }
    revision += 1; feedback(); mode(); void loadModels();
  });
  dialog.querySelectorAll('.summary-preset[data-provider]').forEach((button) => {
    button.addEventListener('click', () => {
      get('provider').value = button.dataset.provider; get('base').value = button.dataset.baseUrl;
      setModels([], button.dataset.model); get('model-custom').value = button.dataset.model;
      revision += 1; feedback(); mode(); void loadModels();
    });
  });
  get('key-toggle').addEventListener('click', () => {
    const visible = get('key').type === 'password'; get('key').type = visible ? 'text' : 'password';
    get('key-toggle').textContent = visible ? '隐藏' : '显示';
    get('key-toggle').setAttribute('aria-pressed', String(visible));
  });
  get('model-manual').addEventListener('click', () => {
    const value = model(); manual = !manual; closeList();
    get('model-custom').classList.toggle('hidden', !manual); get('model-trigger').classList.toggle('hidden', manual);
    get('model-manual').textContent = manual ? '从列表选择' : '手动输入';
    if (manual) { get('model-custom').value = value; get('model-custom').focus(); }
    else setModels([...get('model').options].map((o) => o.value), value);
    revision += 1; feedback();
  });
  get('model-trigger').addEventListener('click', () => {
    const open = get('model-list').classList.contains('hidden');
    get('model-list').classList.toggle('hidden', !open); get('model-trigger').setAttribute('aria-expanded', String(open));
    if (open) get('model-list').querySelector('button')?.focus();
  });
  get('model-list').addEventListener('keydown', (event) => {
    const options = [...get('model-list').querySelectorAll('button')];
    const index = options.indexOf(document.activeElement);
    if (event.key === 'Escape') { closeList(); get('model-trigger').focus(); }
    else if (event.key === 'ArrowDown') options[Math.min(options.length - 1, index + 1)]?.focus();
    else if (event.key === 'ArrowUp') options[Math.max(0, index - 1)]?.focus();
    else if (event.key === 'Tab') closeList(); else return;
    if (event.key !== 'Tab') event.preventDefault();
  });
  document.addEventListener('click', (event) => {
    if (!get('model-trigger').contains(event.target) && !get('model-list').contains(event.target)) closeList();
  });
  for (const id of ['base', 'key', 'model-custom']) {
    get(id).addEventListener('input', () => { revision += 1; feedback(); });
  }
  get('base').addEventListener('blur', loadModels); get('key').addEventListener('blur', loadModels);
  document.getElementById('settings-dialog').addEventListener('close', () => { revision += 1; modelsController?.abort(); get('key').value = ''; closeList(); });
  const busy = (value) => { for (const id of ['save', 'clear', 'test']) get(id).disabled = value; };
  get('test').addEventListener('click', async () => {
    busy(true); feedback('正在测试连接…'); const version = revision;
    try {
      const result = await api('/api/transcription/test', { method: 'POST', body: JSON.stringify(payload()) });
      if (version !== revision || !document.getElementById('settings-dialog').open) return;
      feedback(`${result.message}${result.elapsed_ms != null ? `（${result.elapsed_ms} ms）` : ''}${result.text ? `：${result.text}` : ''}`);
    } catch (error) { if (version === revision && document.getElementById('settings-dialog').open) feedback(`测试失败：${error.message}`, true); }
    finally { busy(false); }
  });
  get('form').addEventListener('submit', async (event) => {
    event.preventDefault(); busy(true);
    try {
      const config = await api('/api/transcription/config', { method: 'PUT', body: JSON.stringify(payload()) });
      renderStatus(config); feedback("语音模型配置已保存。"); void loadSystem();
    } catch (error) { feedback(error.message, true); }
    finally { busy(false); }
  });
  get('clear').addEventListener('click', async () => {
    if (!window.confirm('清除语音接口配置并恢复本地 Whisper？')) return;
    busy(true);
    try { await api('/api/transcription/config', { method: 'DELETE' });
      renderStatus(await api('/api/transcription/config')); feedback('已清除语音配置，恢复本地 Whisper。'); void loadSystem();
    } catch (error) { feedback(error.message, true); } finally { busy(false); }
  });
  api('/api/transcription/config').then(renderStatus).catch((error) => {
    get('hint').textContent = `读取配置失败：${error.message}`; get('save').disabled = true;
  });
})();
