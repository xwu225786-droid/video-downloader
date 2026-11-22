(() => {
  const find = (name) => document.querySelector(`#feishu-${name}`);
  const endpoint = "/api/integrations/feishu";
  let busy = false;
  let loaded = false;
  let refreshing = false;

  async function request(path = "", options = {}) {
    const response = await fetch(endpoint + path, {
      ...options, headers: { "Content-Type": "application/json", ...options.headers },
    });
    const data = await response.json();
    if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "配置保存失败，请检查输入");
    return data;
  }

  function render(data, populate = false) {
    const config = data.config;
    find("state").textContent = ({ disabled: "未启用", connecting: "连接中", connected: "已连接", error: "连接异常" })[data.status] || "状态未知";
    find("hint").textContent = data.message;
    if (populate) {
      find("app-id").value = config.app_id;
      find("app-secret").value = "";
      find("app-secret").placeholder = config.secret_saved ? "已保存，留空保持不变" : "填写应用凭证";
      find("users").value = config.allowed_users.join("\n");
      find("chats").value = config.allowed_chats.join("\n");
      find("enabled").checked = config.enabled;
      find("mention").checked = config.group_require_mention;
      find("transcript").checked = config.extract_txt;
      find("language").value = config.language;
    }
    const list = find("deliveries");
    list.replaceChildren();
    for (const record of (data.recent || []).slice(0, 5)) {
      const row = document.createElement("div");
      const label = document.createElement("span");
      label.textContent = `${new Date(record.created_at * 1000).toLocaleString()} · ${({ pending: "等待处理或回传", done: "已处理", delivery_failed: "回传失败", ignored: "未触发处理" })[record.state] || record.state}`;
      const ids = document.createElement("small");
      ids.textContent = `用户ID：${record.sender_id || "未知"}\n会话ID：${record.chat_id || "未知"}`;
      label.append(document.createElement("br"), ids);
      row.append(label);
      if (record.state === "delivery_failed") {
        row.title = record.error;
        const retry = document.createElement("button");
        retry.type = "button";
        retry.className = "button button-ghost";
        retry.textContent = "重试回传";
        retry.addEventListener("click", () => action(async () => {
          await request(`/retry/${encodeURIComponent(record.id)}`, { method: "POST" });
          find("feedback").textContent = "已加入回传重试，不会重复下载已存在的任务。";
          await refresh();
        }));
        row.append(retry);
      }
      list.append(row);
    }
  }

  async function refresh() {
    if (refreshing) return;
    refreshing = true;
    try {
      const data = await request();
      const initial = !loaded;
      render(data, initial);
      loaded = true;
      if (initial || data.config.enabled || data.recent?.some((item) => item.job_ids.length)) {
        const jobs = await request("/jobs");
        window.dispatchEvent(new CustomEvent("feishu-jobs", { detail: jobs }));
      }
    } catch (error) {
      find("hint").textContent = `飞书状态读取失败：${error.message}`;
    } finally { refreshing = false; }
  }

  async function action(callback) {
    if (busy) return;
    busy = true;
    find("form").querySelectorAll("button").forEach((button) => { button.disabled = true; });
    find("feedback").textContent = "";
    try { await callback(); }
    catch (error) { find("feedback").textContent = error.message; }
    finally {
      busy = false;
      find("form").querySelectorAll("button").forEach((button) => { button.disabled = false; });
    }
  }

  const ids = (name) => find(name).value.split(/[\s,，;；]+/).filter(Boolean);
  find("form").addEventListener("submit", (event) => {
    event.preventDefault();
    void action(async () => {
      const data = await request("/config", { method: "PUT", body: JSON.stringify({
        enabled: find("enabled").checked, app_id: find("app-id").value.trim(),
        app_secret: find("app-secret").value || null,
        allowed_users: ids("users"), allowed_chats: ids("chats"),
        group_require_mention: find("mention").checked, extract_txt: find("transcript").checked,
        language: find("language").value,
      }) });
      render(data, true);
      find("feedback").textContent = data.config.enabled ? "已保存，正在建立飞书连接。" : "已保存，飞书接入保持关闭。";
    });
  });
  find("test").addEventListener("click", () => action(async () => {
    const data = await request("/test", { method: "POST" });
    find("feedback").textContent = `凭证验证通过：${data.bot_name}。消息权限和收发仍需在飞书中验证。`;
  }));
  find("clear").addEventListener("click", () => action(async () => {
    if (!window.confirm("清除飞书配置并停止接收新消息？已有任务和素材会保留。")) return;
    render(await request("/config", { method: "DELETE" }), true);
    find("feedback").textContent = "已清除配置并关闭飞书接入。";
  }));
  void refresh();
  window.setInterval(() => { if (!document.hidden && !busy) void refresh(); }, 10000);
  document.addEventListener("visibilitychange", () => { if (!document.hidden) void refresh(); });
})();
