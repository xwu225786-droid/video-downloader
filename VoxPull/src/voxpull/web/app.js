const elements = {
  systemGrid: document.querySelector("#system-grid"),
  systemSummary: document.querySelector("#system-summary"),
  systemSummaryTitle: document.querySelector("#system-summary-title"),
  systemSummaryCopy: document.querySelector("#system-summary-copy"),
  settingsDialog: document.querySelector("#settings-dialog"),
  settingsOpen: document.querySelector("#settings-open"),
  settingsClose: document.querySelector("#settings-close"),
  refreshSystem: document.querySelector("#refresh-system"),
  authStart: document.querySelector("#auth-start"),
  authComplete: document.querySelector("#auth-complete"),
  authHint: document.querySelector("#auth-hint"),
  authState: document.querySelector("#auth-state"),
  authStateLabel: document.querySelector("#auth-state-label"),
  jobForm: document.querySelector("#job-form"),
  modeSingle: document.querySelector("#mode-single"),
  modeBatch: document.querySelector("#mode-batch"),
  shareContentLabel: document.querySelector("#share-content-label"),
  inputModeHint: document.querySelector("#input-mode-hint"),
  batchInputTools: document.querySelector("#batch-input-tools"),
  importBatchLinks: document.querySelector("#import-batch-links"),
  batchLinksFile: document.querySelector("#batch-links-file"),
  batchLinkCount: document.querySelector("#batch-link-count"),
  batchPanel: document.querySelector("#batch-panel"),
  queueStatusError: document.querySelector("#queue-status-error"),
  batchList: document.querySelector("#batch-list"),
  batchPagination: document.querySelector("#batch-pagination"),
  batchPageInfo: document.querySelector("#batch-page-info"),
  batchPagePrevious: document.querySelector("#batch-page-previous"),
  batchPageNext: document.querySelector("#batch-page-next"),
  batchPageNumbers: document.querySelector("#batch-page-numbers"),
  batchRetry: document.querySelector("#batch-retry"),
  batchDownload: document.querySelector("#batch-download"),
  queueDelete: document.querySelector("#queue-delete"),
  queueDeleteDialog: document.querySelector("#queue-delete-dialog"),
  queueDeleteCount: document.querySelector("#queue-delete-count"),
  queueDeleteFiles: document.querySelector("#queue-delete-files"),
  queueDeleteCancel: document.querySelector("#queue-delete-cancel"),
  queueDeleteConfirm: document.querySelector("#queue-delete-confirm"),
  queueDeleteError: document.querySelector("#queue-delete-error"),
  queueFeedback: document.querySelector("#queue-feedback"),
  queueSelectStart: document.querySelector("#queue-select-start"),
  queueSelectCancel: document.querySelector("#queue-select-cancel"),
  queueSelectPageLabel: document.querySelector(".queue-select-page"),
  queueSelectPage: document.querySelector("#queue-select-page"),
  queueSelectionCount: document.querySelector("#queue-selection-count"),
  queueSelectionActions: document.querySelector("#queue-selection-actions"),
  queueTagFilter: document.querySelector("#queue-tag-filter"),
  queueTagPicker: document.querySelector("#queue-tag-picker"),
  queueTagFilterMenu: document.querySelector("#queue-tag-filter-menu"),
  queueTagFilterLabel: document.querySelector("#queue-tag-filter-label"),
  materialTagDeleteDialog: document.querySelector("#material-tag-delete-dialog"),
  materialTagDeleteMessage: document.querySelector("#material-tag-delete-message"),
  materialTagDeleteError: document.querySelector("#material-tag-delete-error"),
  materialTagDeleteCancel: document.querySelector("#material-tag-delete-cancel"),
  materialTagDeleteConfirm: document.querySelector("#material-tag-delete-confirm"),
  queueTagStatus: document.querySelector("#queue-tag-status"),
  queueTagReload: document.querySelector("#queue-tag-reload"),
  queueFilterEmpty: document.querySelector("#queue-filter-empty"),
  queueSearch: document.querySelector("#queue-search"),
  queueSearchSubmit: document.querySelector("#queue-search-submit"),
  queueSearchClear: document.querySelector("#queue-search-clear"),
  queueSearchStatus: document.querySelector("#queue-search-status"),
  queueAddTags: document.querySelector("#queue-add-tags"),
  materialTagTitle: document.querySelector("#material-tag-title"),
  materialTagOverwrite: document.querySelector("#material-tag-overwrite"),
  materialTagOverwriteMessage: document.querySelector("#material-tag-overwrite-message"),
  materialTagOverwriteList: document.querySelector("#material-tag-overwrite-list"),
  materialTagConfirm: document.querySelector("#material-tag-confirm"),
  materialTagDialog: document.querySelector("#material-tag-dialog"),
  materialTagForm: document.querySelector("#material-tag-form"),
  materialTagSubtitle: document.querySelector("#material-tag-subtitle"),
  materialTagOptions: document.querySelector("#material-tag-options"),
  materialTagAdd: document.querySelector("#material-tag-add"),
  materialTagCreatePanel: document.querySelector("#material-tag-create-panel"),
  materialTagCreateCancel: document.querySelector("#material-tag-create-cancel"),
  materialTagName: document.querySelector("#material-tag-name"),
  materialTagCreate: document.querySelector("#material-tag-create"),
  materialTagSave: document.querySelector("#material-tag-save"),
  materialTagClose: document.querySelector("#material-tag-close"),
  materialTagCancel: document.querySelector("#material-tag-cancel"),
  materialTagError: document.querySelector("#material-tag-error"),
  batchReadOpen: document.querySelector("#batch-read-open"),
  batchTextHint: document.querySelector("#batch-text-hint"),
  batchReader: document.querySelector("#batch-reader"),
  batchReaderTitle: document.querySelector("#batch-reader-title"),
  batchReaderMeta: document.querySelector("#batch-reader-meta"),
  batchReaderText: document.querySelector("#batch-reader-text"),
  batchReaderClose: document.querySelector("#batch-reader-close"),
  batchReaderCopy: document.querySelector("#batch-reader-copy"),
  batchReaderDownload: document.querySelector("#batch-reader-download"),
  batchReaderFeedback: document.querySelector("#batch-reader-feedback"),
  shareContent: document.querySelector("#share-content"),
  shareContentError: document.querySelector("#share-content-error"),
  sharePasteStatus: document.querySelector("#share-paste-status"),
  language: document.querySelector("#language"),
  saveVideoToggle: document.querySelector("#save-video-toggle"),
  extractTxtToggle: document.querySelector("#extract-txt-toggle"),
  storagePathCard: document.querySelector("#storage-path-card"),
  storagePathLabel: document.querySelector("#storage-path-label"),
  storageChange: document.querySelector("#storage-change"),
  storagePathFeedback: document.querySelector("#storage-path-feedback"),
  videoStoragePath: document.querySelector("#video-storage-path"),
  imageStoragePath: document.querySelector("#image-storage-path"),
  submitJob: document.querySelector("#submit-job"),
  submitJobLabel: document.querySelector("#submit-job-label"),
  resultPanel: document.querySelector("#result-panel"),
  resultTitle: document.querySelector("#result-title"),
  resultTypeBadge: document.querySelector("#result-type-badge"),
  mediaMeta: document.querySelector("#media-meta"),
  mediaPath: document.querySelector("#media-path"),
  batchFileActions: document.querySelector("#batch-file-actions"),
  transcriptActions: document.querySelector("#transcript-actions"),
  transcriptTextActions: document.querySelector("#transcript-text-actions"),
  downloadControls: document.querySelector("#transcript-actions .result-downloads"),
  imageResult: document.querySelector("#image-result"),
  imageResultNote: document.querySelector("#image-result-note"),
  imageGrid: document.querySelector("#image-grid"),
  livePhotoNote: document.querySelector("#live-photo-note"),
  imageViewer: document.querySelector("#image-viewer"),
  imageViewerCanvas: document.querySelector("#image-viewer-canvas"),
  imageViewerImage: document.querySelector("#image-viewer-image"),
  imageViewerVideo: document.querySelector("#image-viewer-video"),
  imageViewerLiveReplay: document.querySelector("#image-viewer-live-replay"),
  imageViewerError: document.querySelector("#image-viewer-error"),
  imageViewerFilename: document.querySelector("#image-viewer-filename"),
  imageViewerCounter: document.querySelector("#image-viewer-counter"),
  imageViewerClose: document.querySelector("#image-viewer-close"),
  imageViewerPrevious: document.querySelector("#image-viewer-previous"),
  imageViewerNext: document.querySelector("#image-viewer-next"),
  imageViewerZoomOut: document.querySelector("#image-viewer-zoom-out"),
  imageViewerZoomValue: document.querySelector("#image-viewer-zoom-value"),
  imageViewerZoomIn: document.querySelector("#image-viewer-zoom-in"),
  imageViewerZoomReset: document.querySelector("#image-viewer-zoom-reset"),
  imageViewerHelp: document.querySelector("#image-viewer-help"),
  videoResult: document.querySelector("#video-result"),
  videoDetails: document.querySelector("#video-details"),
  batchVideoPreview: document.querySelector("#batch-video-preview"),
  batchVideoPlayer: document.querySelector("#batch-video-player"),
  batchVideoUnavailable: document.querySelector("#batch-video-unavailable"),
  batchVideoError: document.querySelector("#batch-video-error"),
  videoCover: document.querySelector("#video-cover"),
  videoOriginalTitle: document.querySelector("#video-original-title"),
  videoDetailsPath: document.querySelector("#video-details-path"),
  copyTitle: document.querySelector("#copy-title"),
  downloadCover: document.querySelector("#download-cover"),
  downloadTitle: document.querySelector("#download-title"),
  autoSummaryToggle: document.querySelector("#auto-summary-toggle"),
  summaryService: document.querySelector("#summary-state"),
  summaryServiceLabel: document.querySelector("#summary-state-label"),
  summaryHint: document.querySelector("#summary-hint"),
  summaryConfigOpen: document.querySelector("#summary-config-open"),
  summaryView: document.querySelector("#summary-view"),
  summaryEmpty: document.querySelector("#summary-empty"),
  summaryProgress: document.querySelector("#summary-progress"),
  summaryResult: document.querySelector("#summary-result"),
  summaryError: document.querySelector("#summary-error"),
  summaryErrorText: document.querySelector("#summary-error-text"),
  summaryGenerate: document.querySelector("#summary-generate"),
  summaryCancel: document.querySelector("#summary-cancel"),
  summaryRetry: document.querySelector("#summary-retry"),
  summaryRegenerate: document.querySelector("#summary-regenerate"),
  summaryCopy: document.querySelector("#summary-copy"),
  summaryCopyLabel: document.querySelector("#summary-copy .copy-label"),
  summaryDownload: document.querySelector("#summary-download"),
  summaryMarkdown: document.querySelector("#summary-markdown"),
  summaryMeta: document.querySelector("#summary-meta"),
  summaryConfigDialog: document.querySelector("#summary-config-dialog"),
  summaryConfigForm: document.querySelector("#summary-config-form"),
  summaryConfigBase: document.querySelector("#summary-config-base"),
  summaryConfigKey: document.querySelector("#summary-config-key"),
  summaryConfigModel: document.querySelector("#summary-config-model"),
  summaryConfigModelTrigger: document.querySelector("#summary-config-model-trigger"),
  summaryConfigModelValue: document.querySelector("#summary-config-model-value"),
  summaryConfigModelList: document.querySelector("#summary-config-model-list"),
  summaryConfigModelStatus: document.querySelector("#summary-config-model-status"),
  summaryConfigModelStatusText: document.querySelector("#summary-config-model-status .summary-status-text"),
  summaryConfigKeyToggle: document.querySelector("#summary-config-key-toggle"),
  summaryPresets: [...document.querySelectorAll(".summary-preset")],
  summaryConfigError: document.querySelector("#summary-config-error"),
  summaryConfigClear: document.querySelector("#summary-config-clear"),
  summaryConfigSave: document.querySelector("#summary-config-save"),
  summaryConfigClose: document.querySelector("#summary-config-close"),
  editor: document.querySelector("#transcript-editor"),
  textView: document.querySelector("#text-view"),
  timelineView: document.querySelector("#timeline-view"),
  resultViewPanel: document.querySelector("#result-view-panel"),
  viewTabs: [...document.querySelectorAll(".view-tab")],
  copyText: document.querySelector("#copy-text"),
  copyLabel: document.querySelector("#copy-text .copy-label"),
  downloadText: document.querySelector("#download-text"),
  downloadTimeline: document.querySelector("#download-timeline"),
  downloadSrt: document.querySelector("#download-srt"),
};

let currentResult = null;
let copyFeedbackTimer = null;
const SAVE_VIDEO_KEY = "media.settings.saveVideo";
let saveVideo = readStorage(SAVE_VIDEO_KEY) === "true";
const EXTRACT_TXT_KEY = "media.settings.extractTxt";
let extractTxt = readStorage(EXTRACT_TXT_KEY) !== "false";
let taskInProgress = false;
let transcriptBaseline = "";
let transcriptDirty = false;
let viewerAssets = [];
let viewerIndex = -1;
let viewerScale = 1;
let viewerOffsetX = 0;
let viewerOffsetY = 0;
let viewerReturnFocus = null;
let viewerLoadToken = 0;
let viewerLiveIsPlaying = false;
let viewerGesture = null;
let viewerGestureDidPinch = false;
let viewerLastTap = null;
const viewerPointers = new Map();
let summaryStatus = "empty";
let summaryAbortController = null;
let summaryData = null;
const cardSummaries = new Map();
const cardTranscriptActions = new Map();
const cardTranscriptMonitors = new Set();
let autoSummary = false;
let summaryCopyTimer = null;
let summaryModelsController = null;
let currentJobId = null;
let selectedResultView = null;
let inputMode = "single";
let sharePasteTimer = null;
let sharePastePending = null;
let shareInputRevision = 0;
let currentBatch = null;
let batchPollTimer = null;
let batchRowSignature = "";
const BATCH_PAGE_SIZE = 10;
let batchPage = 1;
let batchPaginationSignature = "";
const batchRows = new Map();
const batchEdits = new Map();
const batchResults = new Map();
const batchResultLoads = new Map();
const batchReadingPositions = new Map();
let expandedBatchJobId = null;
let batchResultRequest = 0;
let batchReaderJobId = null;
const resultPanelHome = document.createComment("single result position");
elements.resultPanel.before(resultPanelHome);
const BATCH_STORAGE_KEY = "media.batch.current";
const PROCESSING_QUEUE_KEY = "media.queue.sources.v1";
const QUEUE_DELETED_KEY = "media.queue.deleted.v1";
const deletedQueueJobs = new Set();
const queueRetrying = new Set();
const queuePausing = new Set();
let queueDeleteBusy = false;
const queueSources = [];
const queueSnapshots = new Map();
const queueUnavailable = new Set();
let queueRefreshPromise = null;
let queueSubmitting = false;
let queueArchiveBusy = false;
let queueRetryBusy = false;
const selectedQueueJobs = new Set();
let queueSelectionMode = false;
const queuePublicationDates = new Map();
const queuePublicationLoads = new Map();
let summaryServiceStatus = { configured: false, base_url: "", model: "" };
let authBasePromise = null;
let authBrowserConsoleUrl = null;
let authPollTimer = null;
let authActionBusy = false;
let currentAuthStatus = "missing";
let authStatusRefresh = null;
let authStatusCheckedAt = 0;
let nativeTaskSupportPromise = null;
let materialTaskBasePromise = null;
let materialTags = { tags: [], assignments: {} };
let materialTagsReady = false;
let materialTagsBase = null;
let materialSearchBase = null;
let queueSearchQuery = "";
let queueSearchMatches = new Map();
let queueSearchPending = false;
let queueSearchError = "";
let queueSearchWarnings = "";
let queueSearchSignature = "";
let queueSearchTimer = null;
let queueSearchController = null;
let queueSearchRequest = 0;
let materialTagsLoad = null;
let materialTagFilter = "";
let materialTagFilterSignature = "";
let materialTagJobIds = [];
let materialTagChoice = null;
let materialTagBulk = false;
let materialTagConflict = null;
let materialTagBusy = false;
let materialTagCreating = false;
let materialTagDeletePending = null;
let materialTagDeleteReturnFocus = null;
let materialTagReturnFocus = null;

const SUMMARY_CONFIG_KEY = "voxpull.summaryConfig";

const VIEWER_MIN_SCALE = 1;
const VIEWER_MAX_SCALE = 5;
const VIEWER_ZOOM_STEP = 0.5;

async function api(path, options = {}) {
  const base = downloadTaskBase();
  const match = path.match(/^\/api\/(?:jobs|batches)\/([a-f0-9]{32})(?:\/|$)/);
  if (match || path === "/api/jobs/files/delete") path = (await materialTaskBase()) + path;
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    let message = body.message || (typeof body.detail === "string" ? body.detail : body.detail?.message) || body.detail || `请求失败 (${response.status})`;
    if (Array.isArray(message)) message = message.map((item) => item.msg).join("；");
    const error = new Error(message);
    error.status = response.status;
    error.detail = body.detail;
    throw error;
  }
  if (path.startsWith(base + "/") && body.result?.media) {
    const media = body.result.media;
    for (const object of [media, ...(media.assets || [])]) {
      for (const key of Object.keys(object)) {
        if (key.endsWith("_url") && typeof object[key] === "string" && object[key].startsWith("/")) object[key] = base + object[key];
      }
    }
  }
  return body;
}

function downloadTaskBase() {
  const endpoint = new URL(location.origin);
  endpoint.port = String(Number(location.port || 80) + 2);
  return endpoint.origin;
}

function nativeTaskSupport() {
  if (!nativeTaskSupportPromise) nativeTaskSupportPromise = fetch("/api/jobs/capabilities")
    .then(async (response) => response.ok && (await response.json()).extract_txt === true)
    .catch(() => false);
  return nativeTaskSupportPromise;
}

function materialTaskBase() {
  if (!materialTaskBasePromise) materialTaskBasePromise = (async () => {
    const response = await fetch("/api/jobs/capabilities");
    if (response.ok && (await response.json()).material_folders) return "";
    const base = downloadTaskBase();
    const capabilities = await api(base + "/api/jobs/capabilities");
    if (!capabilities.material_folders) throw new Error("素材保存后台正在更新，请稍后重试");
    return base;
  })().catch((error) => { materialTaskBasePromise = null; throw error; });
  return materialTaskBasePromise;
}

async function taskSubmissionBase(_shouldExtractTxt, _content) {
  return materialTaskBase();
}

async function douyinAuthApi(action, options = {}) {
  if (!authBasePromise) authBasePromise = (async () => {
    const base = (await materialTaskBase()) + "/api/auth/douyin";
    const capabilities = await api(base + "/capabilities");
    authBrowserConsoleUrl = capabilities.browser_console_url || null;
    if (capabilities.version < 3 || !capabilities.shared_session) throw new Error("抖音登陆与验证窗口正在更新，请稍后重试");
    return base;
  })().catch((error) => { authBasePromise = null; throw error; });
  return api(`${await authBasePromise}/${action}`, options);
}

function refreshAuthStatus() {
  if (authStatusRefresh) return authStatusRefresh;
  authStatusCheckedAt = Date.now();
  authStatusRefresh = douyinAuthApi("status").then((data) => updateAuthUi(data.status, data))
    .catch((error) => { elements.authHint.textContent = `状态读取失败：${error.message}`; })
    .finally(() => { authStatusRefresh = null; });
  return authStatusRefresh;
}

function openAuthConsole() {
  if (authBrowserConsoleUrl) window.open(authBrowserConsoleUrl, "voxpull-browser-console");
}

async function showVerification(jobId) {
  openAuthConsole();
  const data = await douyinAuthApi("start", { method: "POST", body: JSON.stringify({ job_id: jobId }) });
  updateAuthUi(data.status, data);
}

async function loadSystem() {
  elements.refreshSystem.disabled = true;
  try {
    const [status, auth] = await Promise.all([
      api("/api/system"), douyinAuthApi("status").catch(() => null),
    ]);
    if (auth) status.cookie = { ready: auth.status === "ready", detail: auth.status };
    const labels = {
      chromium: "Chromium",
      cookie: "抖音 Cookie",
      yt_dlp: "yt-dlp",
      ffmpeg: "ffmpeg",
      whisper_cpp: "whisper.cpp",
      model: "Medium 模型",
      vad_model: "VAD 模型",
      python: "Python",
      playwright: "Playwright",
    };
    if (status.transcription_cloud) {
      delete labels.whisper_cpp;
      delete labels.model;
      delete labels.vad_model;
    }
    updateStoragePaths(status.video_storage_path, status.image_storage_path);
    elements.systemGrid.replaceChildren();
    const statusEntries = Object.entries(labels);
    const readyCount = statusEntries.filter(([key]) => status[key].ready).length;
    const allReady = readyCount === statusEntries.length;
    elements.systemSummary.className = `system-summary ${allReady ? "is-ready" : "has-warning"}`;
    elements.systemSummaryTitle.textContent = allReady ? "环境正常" : `${readyCount}/${statusEntries.length} 项已就绪`;
    elements.systemSummaryCopy.textContent = allReady
      ? "本机环境检测通过，可以使用"
      : "仍有项目需要处理，展开下方详情查看。";
    statusEntries.forEach(([key, label]) => {
      const isReady = status[key].ready;
      const item = document.createElement("div");
      item.className = `system-item ${isReady ? "ready" : ""}`;
      item.setAttribute("role", "listitem");
      item.setAttribute("aria-label", `${label}：${isReady ? "已就绪" : "未就绪"}。${status[key].detail}`);
      const title = document.createElement("strong");
      title.textContent = label;
      title.setAttribute("translate", "no");
      const detail = document.createElement("span");
      detail.textContent = key === "cookie" ? ({ saved: "已保存登录信息，待确认作品访问", verification_required: "当前作品需要手动验证", opening: "等待在作品窗口登录", checking: "正在检查访问状态", ready: "登录与验证状态可用", window_closed: "验证窗口已关闭，可重新打开" })[status[key].detail] || status[key].detail : status[key].detail;
      detail.title = status[key].detail;
      detail.setAttribute("translate", "no");
      item.append(title, detail);
      elements.systemGrid.append(item);
    });
    updateAuthUi(auth?.status || status.cookie.detail, auth || {});
  } catch (error) {
    elements.systemGrid.textContent = error.message;
    elements.systemSummary.className = "system-summary has-error";
    elements.systemSummaryTitle.textContent = "检测失败";
    elements.systemSummaryCopy.textContent = error.message;
    elements.videoStoragePath.textContent = "读取失败，请点击上方“重新检测”";
    elements.videoStoragePath.setAttribute("aria-busy", "false");
    elements.imageStoragePath.textContent = "读取失败，请点击上方“重新检测”";
    elements.imageStoragePath.setAttribute("aria-busy", "false");
    elements.storagePathCard.classList.add("path-error");
  } finally {
    elements.refreshSystem.disabled = false;
  }
}

function updateStoragePaths(videoStoragePath, imageStoragePath) {
  elements.videoStoragePath.textContent = videoStoragePath
    ? `视频：${videoStoragePath}`
    : "视频：读取失败";
  elements.videoStoragePath.title = videoStoragePath || "";
  elements.videoStoragePath.setAttribute("aria-busy", "false");
  elements.imageStoragePath.textContent = imageStoragePath
    ? `图片：${imageStoragePath}`
    : "图片：读取失败";
  elements.imageStoragePath.title = imageStoragePath || "";
  elements.imageStoragePath.setAttribute("aria-busy", "false");
  elements.storagePathCard.classList.toggle(
    "path-error",
    !videoStoragePath || !imageStoragePath,
  );
}

function updateAuthUi(status, details = {}) {
  currentAuthStatus = status;
  const hints = {
    missing: "尚未保存登录信息。处理抖音时会使用同一个浏览器完成登录与作品访问。",
    saved: "已保存本地登录信息，尚未确认当前作品能否访问；如需验证，请在当前作品页完成。",
    opening: "请在当前作品窗口完成登录，程序会保留同一会话并自动继续等待中的任务。",
    verification_required: "请在已打开的作品页手动完成验证，通过后原任务会自动继续，无需重新提交。",
    window_closed: "验证窗口已关闭，任务仍在等待。点击重新打开，回到被拦截的作品页。",
    checking: "正在同一个浏览器会话中检查作品访问状态。",
    ready: "当前浏览器会话已通过访问检查，后续作品仍可能要求人工验证。",
    refresh_required: "需要重新登录，请在当前作品窗口完成，避免替换正在验证的会话。",
    error: "浏览器初始化失败，请查看本地日志。",
  };
  const labels = { missing: "未登录", saved: "登录信息已保存", opening: "等待登录",
    verification_required: "等待验证", window_closed: "验证窗口已关闭", checking: "检查中",
    ready: "会话可用", refresh_required: "需要登录", error: "异常" };
  const pending = ["opening", "verification_required", "window_closed", "checking", "refresh_required"].includes(status);
  elements.authState.className = `auth-state ${status === "ready" ? "is-ready" : pending ? "is-loading" : status === "saved" ? "" : "has-error"}`;
  elements.authStateLabel.textContent = labels[status] || "状态未知";
  elements.authHint.textContent = authBrowserConsoleUrl && ["opening", "verification_required", "window_closed"].includes(status)
    ? "点击“抖音登陆与验证窗口”，在当前作品页手动登录或验证；通过后任务会自动继续。"
    : hints[status] || status;
  elements.authStart.textContent = status === "window_closed"
    ? "重新打开抖音登陆与验证窗口" : "抖音登陆与验证窗口";
  elements.authStart.classList.toggle("is-ready-action", status === "ready");
  elements.authComplete.classList.toggle("hidden", !pending);
  elements.authComplete.textContent = "检查并继续";
  setAuthActionBusy(authActionBusy);
  if (pending && !authPollTimer) authPollTimer = setTimeout(() => {
    authPollTimer = null;
    void refreshAuthStatus();
  }, 1500);
  if (!pending) { clearTimeout(authPollTimer); authPollTimer = null; }
}

function setAuthActionBusy(busy) {
  authActionBusy = busy;
  elements.authStart.disabled = busy;
  elements.authComplete.disabled = busy;
}

elements.refreshSystem.addEventListener("click", loadSystem);
elements.settingsOpen.addEventListener("click", () => {
  elements.settingsDialog.showModal();
  elements.settingsOpen.setAttribute("aria-expanded", "true");
});
elements.settingsClose.addEventListener("click", () => elements.settingsDialog.close());
elements.settingsDialog.addEventListener("close", () => {
  elements.settingsOpen.setAttribute("aria-expanded", "false");
  elements.settingsOpen.focus();
});
elements.settingsDialog.addEventListener("click", (event) => {
  if (event.target !== elements.settingsDialog) return;
  const bounds = elements.settingsDialog.getBoundingClientRect();
  if (event.clientX < bounds.left || event.clientX > bounds.right
    || event.clientY < bounds.top || event.clientY > bounds.bottom) {
    elements.settingsDialog.close();
  }
});
elements.saveVideoToggle.setAttribute("aria-checked", String(saveVideo));
elements.saveVideoToggle.addEventListener("click", () => {
  saveVideo = !saveVideo;
  writeStorage(SAVE_VIDEO_KEY, String(saveVideo));
  elements.saveVideoToggle.setAttribute("aria-checked", String(saveVideo));
  elements.storagePathLabel.textContent = "本机保存位置";
  elements.storagePathCard.classList.remove("path-inactive");
});

function updateExtractTxtUi() {
  elements.extractTxtToggle.setAttribute("aria-checked", String(extractTxt));
  elements.language.disabled = !extractTxt;
  elements.autoSummaryToggle.disabled = !extractTxt;
  if (!extractTxt) autoSummary = false;
  updateAutoSummaryUi();
}
updateExtractTxtUi();
elements.extractTxtToggle.addEventListener("click", () => {
  extractTxt = !extractTxt;
  writeStorage(EXTRACT_TXT_KEY, String(extractTxt));
  updateExtractTxtUi();
});
elements.storageChange.addEventListener("click", async () => {
  elements.storageChange.disabled = true;
  elements.storageChange.setAttribute("aria-busy", "true");
  elements.storageChange.textContent = "正在选择…";
  elements.storagePathFeedback.textContent = "请在系统窗口中选择保存文件夹";
  elements.storagePathFeedback.className = "storage-path-feedback is-visible";
  try {
    const data = await api("/api/storage/location", { method: "POST" });
    updateStoragePaths(data.video_storage_path, data.image_storage_path);
    elements.storagePathFeedback.textContent = data.changed
      ? `已改为 ${data.media_root_path}`
      : "未更改保存位置";
  } catch (error) {
    elements.storagePathFeedback.textContent = error.message;
    elements.storagePathFeedback.classList.add("has-error");
  } finally {
    elements.storageChange.disabled = taskInProgress;
    elements.storageChange.setAttribute("aria-busy", "false");
    elements.storageChange.textContent = "更改位置";
  }
});
async function showAuthWindow() {
  if (authActionBusy) return;
  openAuthConsole();
  setAuthActionBusy(true);
  elements.authHint.textContent = "正在打开抖音登陆与验证窗口，保留当前作品页和登录状态…";
  try {
    const data = await douyinAuthApi("start", { method: "POST" });
    updateAuthUi(data.status, data);
    if (data.status === "ready") await loadSystem();
  } catch (error) {
    elements.authHint.textContent = error.message;
  } finally {
    setAuthActionBusy(false);
  }
}
elements.authStart.addEventListener("click", showAuthWindow);

elements.authComplete.addEventListener("click", async () => {
  elements.authComplete.disabled = true;
  try {
    const data = await douyinAuthApi("complete", { method: "POST" });
    updateAuthUi(data.status, data);
    await loadSystem();
  } catch (error) {
    elements.authHint.textContent = error.message;
  } finally {
    elements.authComplete.disabled = false;
  }
});

function setInputError(message = "") {
  elements.shareContentError.textContent = message;
  elements.shareContentError.classList.toggle("hidden", !message);
  elements.shareContent.setAttribute("aria-invalid", String(Boolean(message)));
}

function setSubmitting(isSubmitting) {
  queueSubmitting = isSubmitting;
  taskInProgress = isSubmitting || Boolean(currentBatch?.running || currentBatch?.queued);
  elements.submitJob.disabled = isSubmitting || Boolean(sharePastePending);
  elements.submitJob.classList.toggle("is-loading", isSubmitting);
  elements.submitJob.setAttribute("aria-busy", String(isSubmitting));
  elements.submitJobLabel.textContent = isSubmitting ? "正在提交…" : inputMode === "batch" ? "开始批量处理" : "开始处理";
  elements.storageChange.disabled = taskInProgress;
  elements.modeSingle.disabled = isSubmitting;
  elements.modeBatch.disabled = isSubmitting;
  elements.importBatchLinks.disabled = isSubmitting;
}

elements.shareContent.addEventListener("input", () => {
  shareInputRevision += 1;
  cancelShareLinkExtraction();
  if (elements.shareContent.value.trim()) setInputError();
  updateBatchInputCount();
});

function cancelShareLinkExtraction() {
  clearTimeout(sharePasteTimer);
  sharePasteTimer = null;
  sharePastePending = null;
  elements.sharePasteStatus.classList.add("hidden");
  elements.sharePasteStatus.classList.remove("is-extracting");
  elements.submitJob.disabled = queueSubmitting;
}

function shareLinks(content) {
  return (content.match(/https?:\/\/[^\s<>"'“”‘’]+/gi) || [])
    .map((url) => url.replace(/[。！？，,；;：:）)】\]}>"']+$/g, ""))
    .filter((url) => {
      try { return Boolean(new URL(url).hostname); } catch { return false; }
    });
}

elements.shareContent.addEventListener("paste", (event) => {
  cancelShareLinkExtraction();
  const pasted = event.clipboardData?.getData("text/plain") || "";
  const links = shareLinks(pasted);
  if (!links.length) return;
  event.preventDefault();
  const input = elements.shareContent;
  const original = inputMode === "batch"
    ? [input.value.slice(0, input.selectionStart), pasted, input.value.slice(input.selectionEnd)].filter(Boolean).join("\n")
    : pasted;
  const content = inputMode === "batch"
    ? shareLinks(original).join("\n")
    : links[0];
  if (content.length > input.maxLength) {
    setInputError("提取后的链接内容过长，请分批粘贴。");
    return;
  }
  input.value = original;
  input.setSelectionRange(original.length, original.length);
  input.dispatchEvent(new Event("input", { bubbles: true }));
  const pending = { original, content, mode: inputMode };
  sharePastePending = pending;
  elements.sharePasteStatus.textContent = "正在提取链接…";
  elements.sharePasteStatus.classList.remove("hidden");
  elements.sharePasteStatus.classList.add("is-extracting");
  elements.submitJob.disabled = true;
  sharePasteTimer = setTimeout(() => {
    if (sharePastePending !== pending) return;
    if (input.value !== pending.original || inputMode !== pending.mode) {
      cancelShareLinkExtraction();
      return;
    }
    cancelShareLinkExtraction();
    input.value = pending.content;
    input.setSelectionRange(input.value.length, input.value.length);
    input.dispatchEvent(new Event("input", { bubbles: true }));
    elements.sharePasteStatus.textContent = "链接提取完成";
    elements.sharePasteStatus.classList.remove("hidden");
  }, 450);
});

function setInputMode(mode) {
  cancelShareLinkExtraction();
  inputMode = mode;
  const batch = mode === "batch";
  elements.modeSingle.classList.toggle("is-active", !batch);
  elements.modeBatch.classList.toggle("is-active", batch);
  elements.modeSingle.setAttribute("aria-pressed", String(!batch));
  elements.modeBatch.setAttribute("aria-pressed", String(batch));
  elements.batchInputTools.classList.toggle("hidden", !batch);
  elements.shareContentLabel.textContent = batch ? "批量分享内容或链接" : "输入分享内容或链接";
  elements.inputModeHint.textContent = batch ? "每批最多 200 个链接 · 自动去重" : "支持视频、图片与 Live 图";
  elements.shareContent.maxLength = batch ? 100000 : 4096;
  elements.shareContent.placeholder = batch
    ? "每行粘贴一个链接，也可以直接粘贴多段分享文案，或导入链接 TXT 文件。"
    : "例如：粘贴抖音/小红书/Bilibili分享文案或链接...";
  elements.submitJobLabel.textContent = batch ? "开始批量处理" : "开始处理";
  setInputError();
  if (expandedBatchJobId) closeBatchResult();
  updateBatchInputCount();
}

function updateBatchInputCount() {
  if (inputMode !== "batch") return;
  const links = shareLinks(elements.shareContent.value);
  const unique = new Set(links).size;
  elements.batchLinkCount.textContent = links.length
    ? `已识别 ${unique} 个不同链接${links.length > unique ? `，将去除 ${links.length - unique} 个重复链接` : ""}`
    : "粘贴多个链接，重复链接会自动去重";
}

function rememberQueue() {
  try {
    localStorage.setItem(PROCESSING_QUEUE_KEY, JSON.stringify(queueSources));
  } catch (_error) {
    // Processing does not depend on browser storage being enabled.
  }
}

elements.modeSingle.addEventListener("click", () => setInputMode("single"));
elements.modeBatch.addEventListener("click", () => setInputMode("batch"));
elements.importBatchLinks.addEventListener("click", () => elements.batchLinksFile.click());
elements.batchLinksFile.addEventListener("change", async () => {
  cancelShareLinkExtraction();
  const file = elements.batchLinksFile.files[0];
  if (!file) return;
  try {
    if (file.size > 1000000) throw new Error("链接 TXT 文件过大，请拆分后导入。");
    const content = await file.text();
    if (content.length > 100000) throw new Error("每批最多导入 100000 个字符，请拆分文件。");
    elements.shareContent.value = content;
    setInputError();
    updateBatchInputCount();
  } catch (error) {
    setInputError(error.message);
  } finally {
    elements.batchLinksFile.value = "";
  }
});

elements.jobForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (queueSubmitting || sharePastePending) return;
  if (!elements.shareContent.value.trim()) {
    setInputError("请输入分享内容或链接后再提交。");
    elements.shareContent.focus();
    return;
  }
  setInputError();
  closeBatchResult();
  setSubmitting(true);
  elements.resultPanel.classList.add("hidden");
  try {
    const isBatch = inputMode === "batch";
    const payload = {
      content: elements.shareContent.value,
      language: elements.language.value,
      save_video: saveVideo,
      extract_txt: extractTxt,
      auto_summary: autoSummary && extractTxt,
    };
    const submittedInputRevision = shareInputRevision;
    const apiBase = await taskSubmissionBase(payload.extract_txt, payload.content);
    const data = await api(apiBase + (isBatch ? "/api/batches" : "/api/jobs"), {
      method: "POST",
      body: JSON.stringify(payload),
    });
    const source = {
      type: isBatch ? "batch" : "single",
      id: isBatch ? data.id : data.job_id,
      payload,
      api_base: apiBase,
      submitted_at: new Date().toISOString(),
    };
    queueSources.unshift(source);
    queueSnapshots.set(source.id, isBatch ? data : {
      jobs: [singleQueueItem(source, { id: data.job_id, status: "queued", progress: 0, message: "等待处理" })],
      duplicate_count: 0,
    });
    batchPage = 1;
    materialTagFilter = "";
    resetQueueSearch();
    rememberQueue();
    if (shareInputRevision === submittedInputRevision && elements.shareContent.value === payload.content) {
      elements.shareContent.value = "";
      elements.shareContent.dispatchEvent(new Event("input", { bubbles: true }));
    }
    renderProcessingQueue();
    void refreshProcessingQueue();
  } catch (error) {
    setInputError(error.message);
  } finally {
    setSubmitting(false);
  }
});

function visibleQueueJobs() {
  return (currentBatch?.jobs || []).filter((job) => {
    if (queueSearchQuery && (queueSearchPending || queueSearchError || !queueSearchMatches.has(job.id))) return false;
    if (!materialTagFilter) return true;
    const ids = materialTags.assignments[job.id] || [];
    return materialTagFilter === "untagged" ? !ids.length : ids.includes(materialTagFilter);
  });
}

function searchQueueSignature() {
  return JSON.stringify((currentBatch?.jobs || []).map((job) => [job.id, job.title, job.status, job.result_available]));
}

function resetQueueSearch() {
  clearTimeout(queueSearchTimer);
  queueSearchController?.abort();
  queueSearchRequest += 1;
  queueSearchQuery = "";
  queueSearchMatches.clear();
  queueSearchPending = false;
  queueSearchError = "";
  queueSearchWarnings = "";
  queueSearchSignature = "";
  elements.queueSearch.value = "";
}

function scheduleQueueSearch(delay = 300) {
  clearTimeout(queueSearchTimer);
  queueSearchController?.abort();
  const request = ++queueSearchRequest;
  queueSearchPending = true;
  queueSearchError = "";
  queueSearchWarnings = "";
  queueSearchSignature = searchQueueSignature();
  queueSearchTimer = setTimeout(() => { void searchQueue(request); }, delay);
}

function searchQueueEdits() {
  const edits = Object.fromEntries(batchEdits);
  if (currentJobId && currentResult && expandedBatchJobId === currentJobId) edits[currentJobId] = elements.editor.value;
  // Unchanged opened results are already available from the task record.
  for (const [id, text] of Object.entries(edits)) {
    const result = batchResults.get(id)?.result;
    if (text === (result?.media?.description || result?.transcript?.text || "")) delete edits[id];
  }
  return edits;
}

async function searchQueue(request) {
  if (!queueSearchQuery || request !== queueSearchRequest) return;
  const controller = new AbortController();
  queueSearchController = controller;
  const jobs = currentBatch?.jobs || [];
  const ids = new Set(jobs.map((job) => job.id));
  const payload = {
    query: queueSearchQuery,
    job_ids: [...ids],
    titles: Object.fromEntries(jobs.filter((job) => job.title).map((job) => [job.id, job.title])),
    edits: Object.fromEntries(Object.entries(searchQueueEdits()).filter(([id]) => ids.has(id))),
  };
  const options = { method: "POST", body: JSON.stringify(payload), signal: controller.signal };
  try {
    let data;
    if (materialSearchBase === null) {
      try {
        data = await api("/api/material-search", options);
        if (request !== queueSearchRequest) return;
        materialSearchBase = "";
      } catch (error) {
        if (![404, 405].includes(error.status)) throw error;
        const base = downloadTaskBase();
        data = await api(base + "/api/material-search", options);
        if (request !== queueSearchRequest) return;
        materialSearchBase = base;
      }
    } else data = await api(materialSearchBase + "/api/material-search", options);
    if (request !== queueSearchRequest) return;
    queueSearchMatches = new Map(data.matches.map((match) => [match.job_id, match]));
    const warnings = [];
    if (data.unavailable_ids?.length) warnings.push(`${data.unavailable_ids.length} 条素材暂时无法读取`);
    if (data.file_error_count) warnings.push(`${data.file_error_count} 个 TXT 暂时无法读取`);
    queueSearchWarnings = warnings.length ? `；${warnings.join("，")}，可点击搜索重试` : "";
  } catch (error) {
    if (request !== queueSearchRequest || error.name === "AbortError") return;
    queueSearchError = `搜索失败：${error.message}，请点击搜索重试。`;
    queueSearchMatches.clear();
  } finally {
    if (request === queueSearchRequest) {
      queueSearchPending = false;
      queueSearchController = null;
      if (currentBatch) renderBatch(currentBatch);
    }
  }
}

function changeQueueSearch(immediate = false) {
  const query = elements.queueSearch.value.trim();
  if (query === queueSearchQuery && !immediate) {
    renderQueueSearch();
    return;
  }
  batchPage = 1;
  selectedQueueJobs.clear();
  closeQueueMenus();
  closeMaterialTagFilter();
  if (!query) resetQueueSearch();
  else {
    queueSearchQuery = query;
    queueSearchMatches.clear();
    scheduleQueueSearch(immediate ? 0 : 300);
  }
  if (currentBatch) renderBatch(currentBatch);
}

function renderQueueSearch() {
  elements.queueSearchSubmit.disabled = !elements.queueSearch.value.trim();
  elements.queueSearchClear.disabled = !elements.queueSearch.value;
  elements.queueSearchStatus.classList.toggle("hidden", !queueSearchQuery);
  elements.queueSearchStatus.classList.toggle("is-error", Boolean(queueSearchError));
  elements.queueSearchStatus.textContent = queueSearchPending ? "正在搜索…"
    : queueSearchError || (queueSearchQuery ? `找到 ${visibleQueueJobs().length} 条素材${queueSearchWarnings}` : "");
  elements.batchList.setAttribute("aria-busy", String(queueSearchPending));
  elements.queueFilterEmpty.textContent = queueSearchQuery
    ? (queueSearchPending ? "正在搜索…" : queueSearchError ? "暂未获取搜索结果" : "没有找到符合关键词和标签条件的素材")
    : "没有符合此标签的素材";
}

elements.queueSearch.addEventListener("input", (event) => {
  if (!event.isComposing) changeQueueSearch();
});
elements.queueSearch.addEventListener("compositionend", () => changeQueueSearch());
elements.queueSearch.addEventListener("keydown", (event) => {
  if (event.isComposing) return;
  if (event.key === "Enter") { event.preventDefault(); changeQueueSearch(true); }
  if (event.key === "Escape") { elements.queueSearch.value = ""; changeQueueSearch(true); }
});
elements.queueSearchSubmit.addEventListener("click", () => changeQueueSearch(true));
elements.queueSearchClear.addEventListener("click", () => {
  elements.queueSearch.value = "";
  changeQueueSearch(true);
  elements.queueSearch.focus();
});

async function loadMaterialTags() {
  if (materialTagsLoad) return materialTagsLoad;
  materialTagsReady = false;
  elements.queueTagStatus.textContent = "正在读取标签…";
  elements.queueTagReload.classList.add("hidden");
  materialTagsLoad = (async () => {
    try {
      let data;
      if (materialTagsBase === null) {
        try {
          data = await api("/api/material-tags");
          materialTagsBase = "";
        } catch (error) {
          if (error.status !== 404) throw error;
          data = await api(downloadTaskBase() + "/api/material-tags");
          materialTagsBase = downloadTaskBase();
        }
      } else data = await api(materialTagsBase + "/api/material-tags");
      materialTags = data;
      materialTagsReady = true;
      elements.queueTagStatus.textContent = "";
    } catch (error) {
      elements.queueTagStatus.textContent = `标签读取失败：${error.message}`;
      elements.queueTagReload.classList.remove("hidden");
    } finally {
      materialTagsLoad = null;
      materialTagFilterSignature = "";
      if (currentBatch) renderBatch(currentBatch);
      else renderMaterialTagFilter();
    }
  })();
  return materialTagsLoad;
}

function closeMaterialTagFilter(restoreFocus = false) {
  elements.queueTagFilterMenu.classList.add("hidden");
  elements.queueTagFilter.setAttribute("aria-expanded", "false");
  if (restoreFocus) elements.queueTagFilter.focus({ preventScroll: true });
}

function chooseMaterialTagFilter(id) {
  materialTagFilter = id;
  batchPage = 1;
  selectedQueueJobs.clear();
  closeMaterialTagFilter(true);
  if (currentBatch) renderBatch(currentBatch);
}

function materialTagRemoveButton(tag) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "material-tag-remove";
  button.setAttribute("aria-label", `删除标签：${tag.name}`);
  button.title = `删除标签：${tag.name}`;
  button.innerHTML = '<svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" aria-hidden="true"><path d="m4 4 8 8M12 4l-8 8"/></svg>';
  button.disabled = materialTagBusy;
  button.addEventListener("click", (event) => {
    event.stopPropagation();
    beginMaterialTagDelete(tag.id, button);
  });
  return button;
}

function renderMaterialTagFilter() {
  const jobs = currentBatch?.jobs || [];
  const counts = new Map();
  for (const job of jobs) {
    for (const id of materialTags.assignments[job.id] || []) counts.set(id, (counts.get(id) || 0) + 1);
  }
  const tags = materialTags.tags.filter((tag) => (counts.get(tag.id) || 0) > 0)
    .sort((a, b) => counts.get(b.id) - counts.get(a.id) || a.name.localeCompare(b.name, "zh-CN"));
  if (materialTagFilter && !tags.some((tag) => tag.id === materialTagFilter)) {
    materialTagFilter = "";
    batchPage = 1;
    selectedQueueJobs.clear();
  }
  const options = [{ id: "", name: `全部素材 (${jobs.length})` },
    ...tags.map((tag) => ({ ...tag, name: `${tag.name} (${counts.get(tag.id)})` }))];
  elements.queueTagFilterLabel.textContent = options.find((option) => option.id === materialTagFilter)?.name || options[0].name;
  elements.queueTagFilter.disabled = !materialTagsReady || materialTagBusy;
  const signature = JSON.stringify([options, materialTagFilter, materialTagBusy]);
  if (signature === materialTagFilterSignature) return;
  materialTagFilterSignature = signature;
  elements.queueTagFilterMenu.replaceChildren(...options.map((option) => {
    const row = document.createElement("div");
    row.className = "queue-tag-filter-row";
    const select = document.createElement("button");
    select.type = "button";
    select.className = "queue-tag-filter-option";
    select.dataset.filter = option.id;
    select.textContent = option.name;
    select.title = option.name;
    select.disabled = materialTagBusy;
    select.setAttribute("aria-pressed", String(option.id === materialTagFilter));
    select.addEventListener("click", () => chooseMaterialTagFilter(option.id));
    row.append(select);
    return row;
  }));
}

elements.queueTagFilter.addEventListener("click", () => {
  const open = elements.queueTagFilter.getAttribute("aria-expanded") === "true";
  elements.queueTagFilterMenu.classList.toggle("hidden", open);
  elements.queueTagFilter.setAttribute("aria-expanded", String(!open));
});
elements.queueTagPicker.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    event.preventDefault();
    event.stopPropagation();
    closeMaterialTagFilter(true);
  } else if (event.key === "ArrowDown" && event.target === elements.queueTagFilter) {
    event.preventDefault();
    elements.queueTagFilterMenu.classList.remove("hidden");
    elements.queueTagFilter.setAttribute("aria-expanded", "true");
    elements.queueTagFilterMenu.querySelector(".queue-tag-filter-option")?.focus();
  }
});
document.addEventListener("click", (event) => {
  if (!elements.queueTagPicker.contains(event.target)) closeMaterialTagFilter();
});

function restoreMaterialTagDeleteFocus() {
  if (materialTagDeleteReturnFocus?.isConnected && !materialTagDeleteReturnFocus.disabled) materialTagDeleteReturnFocus.focus({ preventScroll: true });
  else if (elements.materialTagDialog.open) (materialTagCreating ? elements.materialTagName : elements.materialTagAdd).focus({ preventScroll: true });
  else elements.queueTagFilter.focus({ preventScroll: true });
}

function beginMaterialTagDelete(id, button) {
  if (!materialTagsReady || materialTagBusy || elements.materialTagDeleteDialog.open) return;
  materialTagDeletePending = { id };
  materialTagDeleteReturnFocus = elements.materialTagDialog.open ? button : elements.queueTagFilter;
  closeMaterialTagFilter();
  elements.materialTagDeleteError.textContent = "";
  elements.materialTagError.textContent = "";
  elements.queueTagStatus.textContent = "";
  void deleteMaterialTag(false);
}

async function deleteMaterialTag(confirm) {
  if (!materialTagDeletePending || materialTagBusy) return;
  const pending = materialTagDeletePending;
  const payload = { confirm };
  if (confirm) payload.expected_job_ids = pending.expected_job_ids;
  setMaterialTagBusy(true);
  elements.materialTagDeleteError.textContent = "";
  try {
    const result = await api(`${materialTagsBase}/api/material-tags/${encodeURIComponent(pending.id)}/delete`, {
      method: "POST", body: JSON.stringify(payload),
    });
    materialTags = { tags: result.tags, assignments: result.assignments };
    if (materialTagChoice === pending.id) materialTagChoice = materialTagBulk ? undefined : null;
    resetMaterialTagConflict();
    renderMaterialTagOptions();
    materialTagFilterSignature = "";
    if (currentBatch) renderBatch(currentBatch);
    else renderMaterialTagFilter();
    if (elements.materialTagDeleteDialog.open) elements.materialTagDeleteDialog.close();
    else materialTagDeletePending = null;
  } catch (error) {
    if (error.status === 409 && error.detail?.expected_job_ids) {
      const detail = error.detail;
      pending.expected_job_ids = detail.expected_job_ids;
      elements.materialTagDeleteMessage.textContent = `${detail.code === "tag_delete_changed" ? "标签关联的素材已变化。" : ""}标签“${detail.tag.name}”下有 ${detail.count} 条素材。删除后会移除此标签及其标记关系，素材文件和文案会保留。是否确认删除？`;
      if (!elements.materialTagDeleteDialog.open) elements.materialTagDeleteDialog.showModal();
      elements.materialTagDeleteCancel.focus();
    } else if (elements.materialTagDeleteDialog.open) elements.materialTagDeleteError.textContent = `删除失败：${error.message}`;
    else if (elements.materialTagDialog.open) elements.materialTagError.textContent = `标签删除失败：${error.message}`;
    else elements.queueTagStatus.textContent = `标签删除失败：${error.message}`;
  } finally {
    setMaterialTagBusy(false);
    if (elements.materialTagDeleteDialog.open) elements.materialTagDeleteCancel.focus({ preventScroll: true });
    else restoreMaterialTagDeleteFocus();
  }
}

elements.materialTagDeleteConfirm.addEventListener("click", () => deleteMaterialTag(true));
elements.materialTagDeleteCancel.addEventListener("click", () => elements.materialTagDeleteDialog.close());
elements.materialTagDeleteDialog.addEventListener("cancel", (event) => {
  if (materialTagBusy) event.preventDefault();
});
elements.materialTagDeleteDialog.addEventListener("close", () => {
  materialTagDeletePending = null;
  restoreMaterialTagDeleteFocus();
});

function renderMaterialTagRow(job, row) {
  const ids = materialTags.assignments[job.id] || [];
  const tags = materialTags.tags.filter((tag) => ids.includes(tag.id));
  row.tagButton.classList.toggle("hidden", !canSelectQueueRecord(job));
  if (["failed", "paused"].includes(job.status) && tags.length) row.progress.classList.remove("hidden");
  row.tagButton.disabled = !materialTagsReady;
  row.tagButton.classList.toggle("has-tags", tags.length > 0);
  row.tagButton.setAttribute("aria-label", `管理标签：${job.title || "此素材"}`);
  row.tagButton.title = tags.length ? `编辑标签：${tags.map((tag) => tag.name).join("、")}` : "添加标签";
  const signature = JSON.stringify(tags);
  if (row.tagList.dataset.signature === signature) return;
  row.tagList.dataset.signature = signature;
  row.tagList.replaceChildren(...tags.map((tag) => {
    const chip = document.createElement("span");
    chip.className = "material-tag-chip";
    chip.textContent = tag.name;
    chip.title = tag.name;
    return chip;
  }));
}

function resetMaterialTagConflict() {
  materialTagConflict = null;
  elements.materialTagOverwrite.classList.add("hidden");
  elements.materialTagConfirm.classList.add("hidden");
  elements.materialTagSave.classList.remove("hidden");
}

function renderMaterialTagOptions() {
  elements.materialTagOptions.replaceChildren();
  const options = [...materialTags.tags, { id: null, name: "不设置标签" }];
  for (const tag of options) {
    const label = document.createElement("label");
    label.className = "material-tag-option";
    const input = document.createElement("input");
    input.type = "radio";
    input.name = "material-tag-choice";
    input.value = tag.id || "";
    input.checked = materialTagChoice === tag.id;
    input.disabled = materialTagBusy;
    input.addEventListener("change", () => {
      materialTagChoice = tag.id;
      resetMaterialTagConflict();
      setMaterialTagBusy(false);
    });
    const name = document.createElement("span");
    name.textContent = tag.name;
    name.title = tag.name;
    label.append(input, name);
    const row = document.createElement("div");
    row.className = "material-tag-row";
    row.append(label);
    if (tag.id) {
      label.classList.add("has-delete");
      row.append(materialTagRemoveButton(tag));
    }
    elements.materialTagOptions.append(row);
  }
}

function openMaterialTagEditor(jobs, bulk) {
  if (!materialTagsReady || materialTagBusy || !jobs.length) return;
  materialTagJobIds = jobs.map((job) => job.id);
  materialTagBulk = bulk;
  const ids = materialTags.assignments[jobs[0].id] || [];
  materialTagChoice = bulk ? undefined : ids.length === 1 ? ids[0] : null;
  materialTagReturnFocus = bulk ? elements.queueAddTags : batchRows.get(jobs[0].id)?.tagButton;
  elements.materialTagTitle.textContent = bulk ? "批量添加标签" : "素材标签";
  elements.materialTagSubtitle.textContent = bulk
    ? `已选 ${jobs.length} 条素材 · 每个作品只能有一个标签`
    : `${jobs[0].title || "此素材"} · 每个作品只能有一个标签`;
  closeMaterialTagCreate(false);
  elements.materialTagError.textContent = "";
  resetMaterialTagConflict();
  renderMaterialTagOptions();
  setMaterialTagBusy(false);
  elements.materialTagDialog.showModal();
}

function openMaterialTags(jobId) {
  const job = currentBatch?.jobs.find((item) => item.id === jobId);
  if (job && canSelectQueueRecord(job)) openMaterialTagEditor([job], false);
}

elements.queueAddTags.addEventListener("click", () => {
  const jobs = currentBatch?.jobs.filter((job) => selectedQueueJobs.has(job.id) && canSelectQueueRecord(job)) || [];
  if (jobs.length > 1) openMaterialTagEditor(jobs, true);
});

function setMaterialTagBusy(busy) {
  materialTagBusy = busy;
  elements.materialTagSave.disabled = busy || materialTagCreating || materialTagChoice === undefined;
  elements.materialTagConfirm.disabled = busy || materialTagCreating;
  elements.materialTagAdd.disabled = busy;
  elements.materialTagCreateCancel.disabled = busy;
  elements.materialTagDeleteCancel.disabled = busy;
  elements.materialTagDeleteConfirm.disabled = busy;
  document.querySelectorAll(".material-tag-remove, .queue-tag-filter-option").forEach((button) => { button.disabled = busy; });
  elements.queueTagFilter.disabled = busy || !materialTagsReady;
  elements.materialTagCancel.disabled = busy;
  elements.materialTagClose.disabled = busy;
  elements.materialTagName.disabled = busy;
  elements.materialTagCreate.disabled = busy || !elements.materialTagName.value.trim();
  elements.materialTagOptions.querySelectorAll("input").forEach((input) => { input.disabled = busy; });
  elements.materialTagForm.setAttribute("aria-busy", String(busy));
  if (currentBatch) syncQueueSelection();
}

function openMaterialTagCreate() {
  if (materialTagBusy) return;
  materialTagCreating = true;
  elements.materialTagAdd.classList.add("hidden");
  elements.materialTagAdd.setAttribute("aria-expanded", "true");
  elements.materialTagCreatePanel.classList.remove("hidden");
  elements.materialTagError.textContent = "";
  setMaterialTagBusy(false);
  elements.materialTagName.focus();
}

function closeMaterialTagCreate(restoreFocus = true) {
  materialTagCreating = false;
  elements.materialTagName.value = "";
  elements.materialTagCreatePanel.classList.add("hidden");
  elements.materialTagAdd.classList.remove("hidden");
  elements.materialTagAdd.setAttribute("aria-expanded", "false");
  if (restoreFocus) {
    elements.materialTagError.textContent = "";
    setMaterialTagBusy(false);
    elements.materialTagAdd.focus();
  }
}

async function createMaterialTag() {
  const name = elements.materialTagName.value.trim();
  if (!name || materialTagBusy || !materialTagCreating) return;
  setMaterialTagBusy(true);
  elements.materialTagError.textContent = "";
  try {
    const tag = await api(materialTagsBase + "/api/material-tags", { method: "POST", body: JSON.stringify({ name }) });
    if (!materialTags.tags.some((item) => item.id === tag.id)) materialTags.tags.push(tag);
    materialTagChoice = tag.id;
    resetMaterialTagConflict();
    closeMaterialTagCreate(false);
    renderMaterialTagOptions();
    renderMaterialTagFilter();
  } catch (error) {
    elements.materialTagError.textContent = `标签添加失败：${error.message}`;
  } finally {
    setMaterialTagBusy(false);
    if (materialTagCreating) elements.materialTagName.focus();
    else {
      const selected = elements.materialTagOptions.querySelector("input:checked");
      selected?.focus({ preventScroll: true });
      selected?.scrollIntoView({ block: "nearest" });
    }
  }
}

function showMaterialTagConflicts(detail) {
  materialTagConflict = detail;
  const target = materialTags.tags.find((tag) => tag.id === materialTagChoice)?.name || "不设置标签";
  const conflicts = detail.conflicts || [];
  const action = materialTagChoice === null ? "清除标签" : `设置为“${target}”`;
  elements.materialTagOverwriteMessage.textContent = detail.code === "tag_assignment_changed"
    ? `素材标签已发生变化，请重新确认。将对选中的 ${materialTagJobIds.length} 条素材${action}。`
    : `选中的 ${materialTagJobIds.length} 条素材中，有 ${conflicts.length} 条已有不同标签。确认后将统一${action}，原标签将被${materialTagChoice === null ? "移除" : "替换"}。`;
  elements.materialTagOverwriteList.replaceChildren(...conflicts.map((conflict) => {
    const job = currentBatch?.jobs.find((item) => item.id === conflict.job_id);
    const entry = document.createElement("li");
    const names = conflict.tag_names || (conflict.tag_ids || []).map((id) => materialTags.tags.find((tag) => tag.id === id)?.name || "已有标签");
    entry.textContent = `${job?.title || job?.source_url || "此素材"}：${names.join("、")} → ${target}`;
    return entry;
  }));
  elements.materialTagOverwrite.classList.remove("hidden");
  elements.materialTagConfirm.classList.remove("hidden");
  elements.materialTagSave.classList.add("hidden");
  elements.materialTagOverwrite.scrollIntoView({ block: "nearest" });
}

async function saveMaterialTags(overwrite = false) {
  if (!materialTagJobIds.length || materialTagBusy || materialTagCreating || materialTagChoice === undefined) return;
  if (overwrite && !materialTagConflict) return;
  const payload = { job_ids: [...materialTagJobIds], tag_id: materialTagChoice, overwrite };
  if (overwrite) payload.expected_assignments = materialTagConflict.expected_assignments;
  setMaterialTagBusy(true);
  elements.materialTagSave.textContent = "正在保存…";
  elements.materialTagConfirm.textContent = "正在保存…";
  elements.materialTagError.textContent = "";
  try {
    const result = await api(`${materialTagsBase}/api/material-tags/bulk`, { method: "POST", body: JSON.stringify(payload) });
    Object.assign(materialTags.assignments, result.assignments);
    if (materialTagBulk) selectedQueueJobs.clear();
    elements.materialTagDialog.close();
    if (currentBatch) renderBatch(currentBatch);
  } catch (error) {
    if (error.status === 409 && error.detail?.expected_assignments) showMaterialTagConflicts(error.detail);
    else elements.materialTagError.textContent = `标签保存失败：${error.message}`;
  } finally {
    setMaterialTagBusy(false);
    elements.materialTagSave.textContent = "保存标签";
    elements.materialTagConfirm.textContent = "确认覆盖";
  }
}

elements.materialTagForm.addEventListener("submit", (event) => {
  event.preventDefault();
  // Enter must never bypass the explicit overwrite confirmation button.
  if (!materialTagConflict) void saveMaterialTags(false);
});
elements.materialTagConfirm.addEventListener("click", () => saveMaterialTags(true));
elements.materialTagAdd.addEventListener("click", openMaterialTagCreate);
elements.materialTagCreateCancel.addEventListener("click", () => { if (!materialTagBusy) closeMaterialTagCreate(); });
elements.materialTagCreate.addEventListener("click", createMaterialTag);
elements.materialTagName.addEventListener("input", () => {
  elements.materialTagCreate.disabled = materialTagBusy || !elements.materialTagName.value.trim();
});
elements.materialTagName.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.isComposing) {
    event.preventDefault();
    void createMaterialTag();
  }
});
for (const button of [elements.materialTagClose, elements.materialTagCancel]) {
  button.addEventListener("click", () => { if (!materialTagBusy) elements.materialTagDialog.close(); });
}
elements.materialTagDialog.addEventListener("cancel", (event) => {
  if (materialTagBusy) event.preventDefault();
});
elements.materialTagDialog.addEventListener("close", () => {
  materialTagJobIds = [];
  materialTagChoice = null;
  closeMaterialTagCreate(false);
  if (materialTagReturnFocus?.isConnected && !materialTagReturnFocus.disabled) materialTagReturnFocus.focus({ preventScroll: true });
  else elements.queueTagFilter.focus({ preventScroll: true });
});
elements.queueTagReload.addEventListener("click", loadMaterialTags);

// Suppress only clicks from this pointer gesture, never an old text selection.
const queueDragClicks = new WeakSet();
let queuePointerGesture = null;
document.addEventListener("pointerdown", (event) => {
  queuePointerGesture = event.isPrimary && event.button === 0
    ? { id: event.pointerId, x: event.clientX, y: event.clientY, moved: false }
    : null;
}, true);
function trackQueuePointer(event) {
  if (queuePointerGesture?.id !== event.pointerId) return;
  if (Math.hypot(event.clientX - queuePointerGesture.x, event.clientY - queuePointerGesture.y) > 4) {
    queuePointerGesture.moved = true;
  }
}
document.addEventListener("pointermove", trackQueuePointer, true);
document.addEventListener("pointerup", trackQueuePointer, true);
document.addEventListener("pointercancel", () => { queuePointerGesture = null; }, true);
document.addEventListener("click", (event) => {
  if (event.detail > 0 && queuePointerGesture?.moved) queueDragClicks.add(event);
  queuePointerGesture = null;
}, true);

function queuePointHitsText(element, event) {
  const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT);
  const range = document.createRange();
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    if (!node.textContent.trim()) continue;
    range.selectNodeContents(node);
    for (const rect of range.getClientRects()) {
      if (event.clientX >= rect.left && event.clientX < rect.right
        && event.clientY >= rect.top && event.clientY < rect.bottom) return true;
    }
  }
  return false;
}

function renderBatch(batch) {
  if (currentBatch?.id !== batch.id) batchPage = 1;
  currentBatch = batch;
  if (queueSearchQuery && queueSearchSignature !== searchQueueSignature()) {
    batchPage = 1;
    selectedQueueJobs.clear();
    scheduleQueueSearch();
  }
  renderMaterialTagFilter();
  renderQueueSearch();
  const filteredJobs = visibleQueueJobs();
  batchPage = Math.min(batchPage, Math.max(1, Math.ceil(filteredJobs.length / BATCH_PAGE_SIZE)));
  elements.batchPanel.classList.remove("hidden");
  const done = batch.completed + batch.failed + (batch.paused || 0) === batch.total;
  elements.batchRetry.classList.toggle("hidden", !done || !(batch.failed + (batch.paused || 0)));
  elements.batchRetry.disabled = !done || queueRetryBusy || queueRetrying.size > 0 || queueDeleteBusy;
  const pageStart = (batchPage - 1) * BATCH_PAGE_SIZE;
  const pageJobs = filteredJobs.slice(pageStart, pageStart + BATCH_PAGE_SIZE);
  elements.queueFilterEmpty.classList.toggle("hidden", filteredJobs.length > 0 || !batch.total);
  const signature = `${batch.id}:${batchPage}:${pageJobs.map((job) => job.id).join(":")}`;
  if (signature !== batchRowSignature) {
    closeBatchResult();
    batchRowSignature = signature;
    batchRows.clear();
    elements.batchList.replaceChildren();
    pageJobs.forEach((job, offset) => {
      const index = pageStart + offset;
      const row = document.createElement("li");
      row.className = "batch-item";
      row.dataset.jobId = job.id;
      const menu = document.createElement("details");
      menu.className = "batch-item-menu";
      const menuToggle = document.createElement("summary");
      menuToggle.title = "更多操作";
      menuToggle.innerHTML = '<svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor" aria-hidden="true"><circle cx="5" cy="12" r="1.7"/><circle cx="12" cy="12" r="1.7"/><circle cx="19" cy="12" r="1.7"/></svg>';
      menuToggle.addEventListener("click", () => closeQueueMenus(menu));
      const menuPanel = document.createElement("div");
      menuPanel.className = "batch-item-menu-panel";
      const menuDelete = document.createElement("button");
      menuDelete.type = "button";
      menuDelete.className = "batch-item-menu-delete";
      menuDelete.textContent = "删除素材";
      menuDelete.addEventListener("click", () => openQueueDelete([job.id], menuToggle));
      menuPanel.append(menuDelete);
      menu.append(menuToggle, menuPanel);
      menu.addEventListener("keydown", (event) => {
        if (event.key !== "Escape" || !menu.open) return;
        event.preventDefault();
        event.stopPropagation();
        menu.open = false;
        menuToggle.focus();
      });
      row.append(menu);
      const select = document.createElement("input");
      select.type = "checkbox";
      select.className = "batch-item-select";
      select.addEventListener("change", () => {
        if (!queueSelectionMode) return;
        if (select.checked) selectedQueueJobs.add(job.id);
        else selectedQueueJobs.delete(job.id);
        syncQueueSelection();
      });
      const content = document.createElement("div");
      content.className = "batch-item-copy";
      const cover = document.createElement("img");
      cover.className = "batch-item-cover hidden";
      cover.alt = "视频封面";
      cover.loading = "lazy";
      cover.setAttribute("role", "button");
      cover.setAttribute("aria-controls", "result-panel");
      cover.setAttribute("aria-expanded", "false");
      cover.tabIndex = -1;
      cover.addEventListener("click", (event) => {
        event.stopPropagation();
        if (batchRows.get(job.id)?.view.disabled === false) {
          void showBatchResult(job.id);
        }
      });
      cover.addEventListener("keydown", (event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          cover.click();
        }
      });
      cover.addEventListener("error", () => {
        cover.dataset.failedUrl = cover.getAttribute("src");
        cover.classList.add("hidden");
      });
      const main = document.createElement("div");
      main.className = "batch-item-main";
      const title = document.createElement("strong");
      const published = document.createElement("time");
      published.className = "batch-published hidden";
      const source = document.createElement("a");
      source.href = job.source_url;
      source.target = "_blank";
      source.rel = "noopener noreferrer";
      source.textContent = job.source_url;
      const searchHit = document.createElement("p");
      searchHit.className = "batch-search-hit hidden";
      const messageLine = document.createElement("p");
      messageLine.className = "batch-item-message";
      const message = document.createElement("span");
      const savedBadge = document.createElement("span");
      savedBadge.className = "batch-video-saved hidden";
      savedBadge.textContent = "视频已保留";
      const status = document.createElement("span");
      status.className = "batch-item-status";
      const subtitleBadge = document.createElement("span");
      subtitleBadge.className = "card-completion-badge card-subtitle-completed hidden";
      subtitleBadge.textContent = "提取字幕";
      subtitleBadge.title = "字幕已提取";
      const summaryBadge = document.createElement("span");
      summaryBadge.className = "card-completion-badge card-summary-completed hidden";
      summaryBadge.textContent = "AI总结";
      summaryBadge.title = "AI总结已生成";
      const featureBadges = document.createElement("div");
      featureBadges.className = "card-feature-badges";
      featureBadges.setAttribute("role", "group");
      featureBadges.setAttribute("aria-label", "字幕与总结状态");
      featureBadges.append(subtitleBadge, summaryBadge);
      row.append(featureBadges);
      const view = document.createElement("button");
      view.className = "button button-ghost batch-result-toggle";
      view.type = "button";
      view.textContent = "查看结果";
      view.setAttribute("aria-expanded", "false");
      view.setAttribute("aria-controls", "result-panel");
      view.addEventListener("click", () => showBatchResult(job.id));
      const actions = document.createElement("div");
      actions.className = "batch-item-actions";
      const retry = document.createElement("button");
      retry.className = "button button-ghost batch-item-retry hidden";
      retry.type = "button";
      retry.textContent = "重试";
      retry.addEventListener("click", () => retryQueueItem(job.id));
      const pause = document.createElement("button");
      pause.className = "button button-ghost batch-item-pause hidden";
      pause.type = "button";
      pause.textContent = "暂停";
      pause.title = "中断此任务，保留已有素材；之后可重试重新开始";
      pause.addEventListener("click", () => pauseQueueItem(job.id));
      messageLine.append(savedBadge, message);
      content.append(title, published, source, messageLine, searchHit);
      const verify = document.createElement("button");
      verify.type = "button";
      verify.className = "button button-ghost batch-item-verify hidden";
      verify.textContent = "继续验证";
      verify.addEventListener("click", async () => {
        verify.disabled = true;
        try { await showVerification(job.id); }
        catch (error) { elements.queueFeedback.textContent = error.message; }
        finally { verify.disabled = false; }
      });
      actions.append(verify, pause, retry, view);
      const progress = document.createElement("div");
      progress.className = "batch-item-progress";
      const progressTop = document.createElement("div");
      progressTop.className = "batch-item-progress-top";
      const progressLabel = document.createElement("div");
      progressLabel.className = "batch-item-progress-label";
      status.setAttribute("role", "status");
      progressLabel.append(status);
      const progressValue = document.createElement("span");
      progressValue.className = "batch-item-progress-value";
      progressValue.setAttribute("aria-hidden", "true");
      const tagList = document.createElement("div");
      tagList.className = "material-tag-list";
      const tagButton = document.createElement("button");
      tagButton.type = "button";
      tagButton.className = "material-tag-button";
      tagButton.setAttribute("aria-haspopup", "dialog");
      tagButton.setAttribute("aria-controls", "material-tag-dialog");
      tagButton.innerHTML = '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 13l-7 7a2 2 0 0 1-2.8 0L3 12.8V3h9.8l7.2 7.2a2 2 0 0 1 0 2.8Z"/><circle cx="7.5" cy="7.5" r="1.2"/></svg>';
      tagButton.addEventListener("click", () => openMaterialTags(job.id));
      const progressRight = document.createElement("div");
      progressRight.className = "batch-item-progress-right";
      progressRight.append(progressValue, tagList, tagButton);
      progressTop.append(progressLabel, progressRight);
      const progressTrack = document.createElement("div");
      progressTrack.className = "batch-item-progress-track";
      progressTrack.setAttribute("role", "progressbar");
      progressTrack.setAttribute("aria-valuemin", "0");
      progressTrack.setAttribute("aria-valuemax", "100");
      const progressBar = document.createElement("div");
      progressBar.className = "batch-item-progress-bar";
      progressTrack.append(progressBar);
      progress.append(progressTop, progressTrack);
      main.append(select, cover, content);
      row.append(main, actions, progress);
      const blankAreas = new Set([row, main, content, messageLine, actions, progress, progressTop, progressLabel, progressTrack, progressBar]);
      const textAreas = new Set([title, published, message, savedBadge, status, progressValue, searchHit]);
      const isBlankPoint = (event) => {
        if (batchRows.get(job.id)?.view.disabled !== false) return false;
        if (!blankAreas.has(event.target)
          && !(textAreas.has(event.target) && !queuePointHitsText(event.target, event))) return false;
        return elements.resultPanel.parentElement !== row
          || event.clientY < elements.resultPanel.getBoundingClientRect().top;
      };
      row.addEventListener("pointerdown", (event) => {
        // Empty header areas are controls; don't let a tiny mouse movement select nearby text.
        if (event.pointerType === "mouse" && event.button === 0 && isBlankPoint(event)) event.preventDefault();
      });
      row.addEventListener("pointermove", (event) => {
        if (event.pointerType !== "mouse" || !textAreas.has(event.target)
          || batchRows.get(job.id)?.view.disabled !== false) return;
        event.target.style.cursor = queuePointHitsText(event.target, event) ? "text" : "pointer";
      });
      row.addEventListener("pointerleave", () => {
        for (const area of textAreas) area.style.removeProperty("cursor");
      });
      row.addEventListener("click", (event) => {
        if (!isBlankPoint(event) || queueDragClicks.has(event)) return;
        void showBatchResult(job.id);
      });
      elements.batchList.append(row);
      const feedback = document.createElement("p");
      feedback.className = "batch-result-feedback hidden";
      feedback.setAttribute("role", "status");
      row.append(feedback);
      batchRows.set(job.id, { row, title, searchHit, published, message, status, subtitleBadge, summaryBadge, view, retry, pause, feedback, savedBadge, cover, select, index, actions, progress, progressLabel, progressTrack, progressBar, progressValue, tagList, tagButton, menu, menuToggle, menuDelete, verify });
    });
  }
  const labels = { queued: "等待中", running: "处理中", completed: "已完成", failed: "失败", paused: "已暂停" };
  pageJobs.forEach((job) => {
    const row = batchRows.get(job.id);
    row.title.textContent = job.title || "等待解析标题";
    const match = queueSearchQuery ? queueSearchMatches.get(job.id) : null;
    row.searchHit.classList.toggle("hidden", !match);
    row.searchHit.textContent = match ? `命中${match.fields.map((field) => ({ title: "标题", text: "文案", txt: "TXT" })[field] || field).join(" / ")}：${match.snippet}` : "";
    row.row.dataset.status = job.status;
    row.message.textContent = job.error?.code === "cookie_refresh_required"
      ? "此任务需要检查登录或完成平台验证，请在抖音登陆与验证窗口完成后单项重试。"
      : job.error?.message || job.message;
    if (row.message.textContent === "正在使用抖音登陆与验证窗口读取作品") {
      row.message.textContent = "正在使用抖音窗口读取作品";
    }
    const authWaiting = job.status === "running" && Boolean(job.auth_status);
    const failedAuth = job.status === "failed" && ["platform_verification_required", "cookie_refresh_required"].includes(job.error?.code);
    const needsVerification = failedAuth || (authWaiting && ["opening", "verification_required", "window_closed", "refresh_required", "waiting_browser"].includes(job.auth_status));
    const authLabels = { opening: "等待登录", verification_required: "等待验证", window_closed: "等待验证",
      refresh_required: "等待登录", waiting_browser: "等待浏览器",
      guest_reading: "读取公开资源", guest_downloading: "下载中" };
    row.status.textContent = authWaiting ? authLabels[job.auth_status] || "处理中" : labels[job.status] || "等待中";
    updateCardCompletionBadges(job.id, job);
    row.verify.classList.toggle("hidden", !needsVerification);
    row.verify.textContent = failedAuth ? "打开验证页" : job.auth_status === "waiting_browser" ? "查看验证窗口" : "继续验证";
    const failed = ["failed", "paused"].includes(job.status);
    const pausing = queuePausing.has(job.id);
    const canPause = ["queued", "running"].includes(job.status);
    const canView = Boolean(job.result_available);
    row.row.classList.toggle("is-result-actionable", canView);
    const statusTarget = failed ? row.actions : row.progressLabel;
    if (row.status.parentElement !== statusTarget) statusTarget.prepend(row.status);
    row.progress.classList.toggle("hidden", failed);
    row.actions.classList.toggle("hidden", !failed && !canView && !needsVerification && !canPause);
    row.row.classList.toggle("has-actions", failed || canView || needsVerification || canPause);
    row.pause.classList.toggle("hidden", !canPause && !pausing);
    row.pause.disabled = pausing;
    row.pause.textContent = pausing ? "正在暂停…" : "暂停";
    const value = job.status === "queued" ? 0 : Math.max(0, Math.min(100, Number(job.progress) || 0));
    const terminal = ["completed", "failed", "paused"].includes(job.status);
    row.progressTrack.classList.toggle("hidden", terminal);
    row.progressValue.classList.toggle("hidden", terminal);
    row.progressValue.textContent = `${value}%`;
    row.progressBar.style.transform = `scaleX(${value / 100})`;
    row.progressTrack.setAttribute("aria-label", `${job.title || "此任务"}的处理进度`);
    row.progressTrack.setAttribute("aria-valuenow", String(value));
    row.progressTrack.setAttribute("aria-valuetext", `${labels[job.status]}，进度 ${value}%`);
    row.view.classList.toggle("hidden", !canView);
    row.view.disabled = !canView;
    row.cover.tabIndex = canView ? 0 : -1;
    row.cover.setAttribute("aria-disabled", String(!canView));
    row.cover.setAttribute("aria-label", `展开结果：${job.title || "此视频"}`);
    row.cover.classList.toggle("is-actionable", canView);
    row.retry.classList.toggle("hidden", !failed);
    row.retry.disabled = pausing || queueRetrying.has(job.id) || queueDeleteBusy || queueRetryBusy;
    row.retry.textContent = queueRetrying.has(job.id) ? "正在重试…" : "重试";
    renderMaterialTagRow(job, row);
    updateBatchSavedBadge(job, row);
  });
  if (batch.jobs.some((job) => job.status === "running" && job.auth_status)
    && Date.now() - authStatusCheckedAt > 1500) void refreshAuthStatus();
  renderBatchPagination();
  syncQueueSelection();
  taskInProgress = queueSubmitting || !done;
  elements.storageChange.disabled = taskInProgress;
}

function canSelectQueueItem(job) {
  return job.status === "completed" && job.result_available;
}

function canSelectQueueRecord(job) {
  return ["completed", "failed", "paused"].includes(job.status) && !queuePausing.has(job.id);
}

function setQueueSelectionMode(selecting) {
  if (!currentBatch || queueArchiveBusy || queueDeleteBusy || queueRetryBusy || queueRetrying.size || materialTagBusy) return;
  queueSelectionMode = selecting;
  if (!selecting) selectedQueueJobs.clear();
  closeQueueMenus();
  closeMaterialTagFilter();
  syncQueueSelection();
  if (!selecting) elements.queueSelectStart.focus({ preventScroll: true });
  else (elements.queueSelectPage.disabled ? elements.queueSelectCancel : elements.queueSelectPage).focus({ preventScroll: true });
}
elements.queueSelectStart.addEventListener("click", () => setQueueSelectionMode(true));
elements.queueSelectCancel.addEventListener("click", () => setQueueSelectionMode(false));

function syncQueueSelection() {
  if (!currentBatch) return;
  if (!queueSelectionMode) selectedQueueJobs.clear();
  const busy = queueArchiveBusy || queueDeleteBusy || queueRetryBusy || queueRetrying.size > 0 || materialTagBusy;
  elements.batchPanel.classList.toggle("is-selecting", queueSelectionMode);
  elements.queueSelectStart.classList.toggle("hidden", queueSelectionMode);
  elements.queueSelectStart.setAttribute("aria-pressed", String(queueSelectionMode));
  elements.queueSelectStart.disabled = busy || !currentBatch.total;
  elements.queueSelectPageLabel.classList.toggle("hidden", !queueSelectionMode);
  elements.queueSelectionCount.classList.toggle("hidden", !queueSelectionMode);
  elements.queueSelectCancel.classList.toggle("hidden", !queueSelectionMode);
  elements.queueSelectCancel.disabled = busy;
  const eligible = new Set(visibleQueueJobs().filter(canSelectQueueRecord).map((job) => job.id));
  for (const id of selectedQueueJobs) if (!eligible.has(id)) selectedQueueJobs.delete(id);
  const start = (batchPage - 1) * BATCH_PAGE_SIZE;
  const pageJobs = visibleQueueJobs().slice(start, start + BATCH_PAGE_SIZE);
  const pageEligible = pageJobs.filter(canSelectQueueRecord);
  const pageCount = pageEligible.filter((job) => selectedQueueJobs.has(job.id)).length;
  for (const job of pageJobs) {
    const row = batchRows.get(job.id);
    if (!row) continue;
    row.select.checked = selectedQueueJobs.has(job.id);
    row.select.disabled = !queueSelectionMode || !canSelectQueueRecord(job) || queueArchiveBusy || queueDeleteBusy || queueRetrying.has(job.id);
    row.select.tabIndex = queueSelectionMode ? 0 : -1;
    row.select.setAttribute("aria-hidden", String(!queueSelectionMode));
    row.select.setAttribute("aria-label", `选择任务：${job.title || job.source_url}`);
    row.select.title = canSelectQueueRecord(job) ? "选择此任务打包、添加标签或删除" : "处理结束后可选择";
    row.menuToggle.setAttribute("aria-label", `更多操作：${job.title || job.source_url}`);
    row.menuDelete.disabled = !canSelectQueueRecord(job) || queueArchiveBusy || queueDeleteBusy || queueRetrying.size > 0 || queueRetryBusy;
    row.menuDelete.title = canSelectQueueRecord(job) ? "删除此素材" : "处理结束后可删除";
  }
  elements.queueSelectPage.checked = pageEligible.length > 0 && pageCount === pageEligible.length;
  elements.queueSelectPage.indeterminate = pageCount > 0 && pageCount < pageEligible.length;
  elements.queueSelectPage.disabled = !queueSelectionMode || !pageEligible.length || queueArchiveBusy || queueDeleteBusy || queueRetrying.size > 0;
  const selected = selectedQueueJobs.size;
  elements.queueSelectionCount.textContent = `已选 ${selected} 条`;
  elements.queueSelectionActions.classList.toggle("hidden", !selected);
  elements.queueDelete.classList.toggle("hidden", !selected);
  elements.batchDownload.classList.toggle("hidden", !selected);
  const packable = currentBatch.jobs.some((job) => selectedQueueJobs.has(job.id) && canSelectQueueItem(job));
  elements.batchDownload.classList.remove("button-primary");
  elements.batchDownload.classList.add("button-ghost");
  elements.batchDownload.disabled = !packable || queueArchiveBusy || queueDeleteBusy;
  elements.queueDelete.disabled = !selected || queueArchiveBusy || queueDeleteBusy || queueRetrying.size > 0 || queueRetryBusy;
  elements.queueAddTags.classList.toggle("hidden", selected < 2);
  elements.queueAddTags.disabled = selected < 2 || !materialTagsReady || materialTagBusy || queueArchiveBusy || queueDeleteBusy || queueRetrying.size > 0 || queueRetryBusy;
}

elements.queueSelectPage.addEventListener("change", () => {
  if (!currentBatch || !queueSelectionMode) return;
  const start = (batchPage - 1) * BATCH_PAGE_SIZE;
  for (const job of visibleQueueJobs().slice(start, start + BATCH_PAGE_SIZE)) {
    if (!canSelectQueueRecord(job)) continue;
    if (elements.queueSelectPage.checked) selectedQueueJobs.add(job.id);
    else selectedQueueJobs.delete(job.id);
  }
  syncQueueSelection();
});

function rememberCardSummary(job) {
  if (!job.summary?.markdown) return;
  cardSummaries.set(job.id, {
    markdown: job.summary.markdown, model: job.summary.model,
    sourceText: job.summary.source_text, generatedAt: job.summary.generated_at,
  });
}

function updateCardCompletionBadges(jobId, snapshot) {
  const row = batchRows.get(jobId);
  if (!row) return;
  const detail = batchResults.get(jobId);
  if (!detail?.result && !snapshot?.result_available) {
    row.subtitleBadge.classList.add("hidden");
    row.summaryBadge.classList.add("hidden");
    return;
  }
  const subtitle = detail?.result ? Boolean(detail.result.transcript) : snapshot?.subtitle_completed;
  const summary = Boolean(detail?.summary || cardSummaries.has(jobId) || snapshot?.summary_completed);
  const subtitleState = detail?.subtitle_state || snapshot?.subtitle_state || (subtitle ? "completed" : "not_requested");
  const summaryState = currentJobId === jobId && summaryStatus === "busy" ? "generating"
    : detail?.summary_state || snapshot?.summary_state || (summary ? "completed" : "not_requested");
  row.subtitleBadge.textContent = subtitleState === "generating" ? "字幕生成中" : subtitleState === "failed" ? "字幕失败" : "提取字幕";
  row.summaryBadge.textContent = summaryState === "generating" ? "AI总结生成中" : summaryState === "waiting" ? "AI总结等待字幕"
    : summaryState === "failed" ? "AI总结失败" : "AI总结";
  row.subtitleBadge.classList.toggle("hidden", !subtitle && !["generating", "failed"].includes(subtitleState));
  row.summaryBadge.classList.toggle("hidden", !summary && !["waiting", "generating", "failed"].includes(summaryState));
  row.subtitleBadge.classList.toggle("is-processing", subtitleState === "generating");
  row.summaryBadge.classList.toggle("is-processing", ["waiting", "generating"].includes(summaryState));
  row.subtitleBadge.title = subtitleState === "generating" ? "正在识别字幕" : "字幕已提取";
  row.summaryBadge.title = summaryState === "waiting" ? "字幕完成后自动生成总结" : summaryState === "generating" ? "正在生成总结" : "AI总结已生成";
}

function syncExpandedCard(job) {
  if (currentJobId !== job.id || expandedBatchJobId !== job.id || !job.result) return;
  const view = selectedResultView;
  const newTranscript = job.result.transcript && !currentResult?.transcript;
  const newSummary = job.summary && job.summary.markdown !== summaryData?.markdown;
  if ((newTranscript || newSummary) && !summaryAbortController) {
    renderResult(job.result, job.id, { inline: true });
    if (batchEdits.has(job.id) && !newTranscript) elements.editor.value = batchEdits.get(job.id);
    selectView(view);
    fitBatchEditor();
  } else {
    const previewChanged = currentResult?.media?.video_url !== job.result.media.video_url;
    currentResult = job.result;
    if (previewChanged) renderBatchVideoPreview(job.result.media, job.id, true);
    renderMediaPath(job.result.media, job.id);
    if (job.summary_state === "generating" && !summaryAbortController) setSummaryState("busy");
    else if (summaryStatus === "busy" && !summaryAbortController) {
      if (job.summary_state === "failed") {
        elements.summaryErrorText.textContent = "总结生成失败，可重新尝试。视频和字幕已保留。";
        setSummaryState("error");
      } else setSummaryState(summaryData ? "done" : "empty");
    }
  }
}

async function loadBatchResult(jobId, { refresh = false } = {}) {
  if (batchResults.has(jobId) && !refresh) return batchResults.get(jobId);
  if (!batchResultLoads.has(jobId)) {
    const request = api(`/api/jobs/${jobId}`).then((job) => {
      if (job.result) batchResults.set(jobId, job);
      rememberCardSummary(job);
      updateCardCompletionBadges(jobId);
      syncExpandedCard(job);
      return job;
    }).finally(() => {
      if (batchResultLoads.get(jobId) === request) batchResultLoads.delete(jobId);
    });
    batchResultLoads.set(jobId, request);
  }
  return batchResultLoads.get(jobId);
}

function updateBatchSavedBadge(job, row) {
  const eligible = Boolean(job.result_available);
  const show = (result) => {
    if (batchRows.get(job.id) !== row || !row.row.isConnected) return;
    const media = result?.media;
    updateCardCompletionBadges(job.id, job);
    row.savedBadge.classList.toggle("hidden", !eligible || media?.kind !== "video" || media.saved !== true);
    const firstImage = media?.assets?.filter((asset) => asset.kind === "image")
      .sort((a, b) => a.index - b.index)[0];
    const coverUrl = eligible ? (media?.kind === "images" ? firstImage?.preview_url : media?.cover_url) : null;
    row.cover.alt = media?.kind === "images" ? "图文封面" : "视频封面";
    row.cover.classList.toggle("hidden", !coverUrl || row.cover.dataset.failedUrl === coverUrl);
    if (coverUrl && row.cover.getAttribute("src") !== coverUrl) row.cover.src = coverUrl;
    updateQueuePublication(job, media, row);
  };
  show(batchResults.get(job.id)?.result);
  if (eligible && (!batchResults.has(job.id) || job.status === "running" || batchResults.get(job.id).status !== job.status)) {
    loadBatchResult(job.id, { refresh: true }).then((detail) => show(detail.result)).catch(() => {
      // Unknown retention state must never be shown as saved.
      show(null);
    });
  }
}

function updateQueuePublication(job, media, row) {
  if (batchRows.get(job.id) !== row || !media) return;
  const native = Number(media.published_at);
  if (Number.isFinite(native) && native > 0) queuePublicationDates.set(job.id, native);
  const stamp = queuePublicationDates.get(job.id);
  row.published.classList.toggle("hidden", !stamp);
  if (stamp) {
    const date = new Date(stamp * 1000);
    const parts = Object.fromEntries(new Intl.DateTimeFormat("zh-CN", {
      timeZone: "Asia/Shanghai", year: "numeric", month: "2-digit", day: "2-digit",
      hour: "2-digit", minute: "2-digit", hourCycle: "h23",
    }).formatToParts(date).map((part) => [part.type, part.value]));
    row.published.dateTime = date.toISOString();
    row.published.textContent = `发布时间：${parts.year}-${parts.month}-${parts.day} ${parts.hour}:${parts.minute}`;
    return;
  }
  let douyin = false;
  try {
    const host = new URL(job.source_url).hostname;
    douyin = host === "douyin.com" || host.endsWith(".douyin.com")
      || host === "iesdouyin.com" || host.endsWith(".iesdouyin.com");
  } catch { /* No platform lookup without a known source. */ }
  if (!douyin || queuePublicationDates.has(job.id) || queuePublicationLoads.has(job.id)) return;
  const endpoint = new URL(media.publication_url || `/api/jobs/${encodeURIComponent(job.id)}/publication`, location.href);
  if (!media.publication_url) endpoint.port = String(Number(location.port || 80) + 1);
  const request = fetch(endpoint).then(async (response) => {
    if (!response.ok) return null;
    const body = await response.json();
    const value = Number(body.published_at);
    return Number.isFinite(value) && value > 0 ? value : null;
  }).catch(() => null).then((value) => {
    queuePublicationDates.set(job.id, value);
    updateQueuePublication(job, media, row);
  }).finally(() => queuePublicationLoads.delete(job.id));
  queuePublicationLoads.set(job.id, request);
}

function renderBatchPagination() {
  const total = visibleQueueJobs().length;
  const pages = Math.max(1, Math.ceil(total / BATCH_PAGE_SIZE));
  const start = total ? (batchPage - 1) * BATCH_PAGE_SIZE + 1 : 0;
  const end = Math.min(batchPage * BATCH_PAGE_SIZE, total);
  elements.batchPagination.classList.toggle("hidden", pages <= 1);
  elements.batchPageInfo.textContent = `第 ${batchPage} / ${pages} 页 · 第 ${start}–${end} 条，共 ${total} 条`;
  elements.batchPagePrevious.disabled = batchPage === 1;
  elements.batchPageNext.disabled = batchPage === pages;
  const signature = `${batchPage}:${pages}`;
  if (signature === batchPaginationSignature) return;
  batchPaginationSignature = signature;
  elements.batchPageNumbers.replaceChildren();
  const visiblePages = pages <= 7
    ? Array.from({ length: pages }, (_, index) => index + 1)
    : [...new Set([1, batchPage - 1, batchPage, batchPage + 1, pages])]
      .filter((page) => page >= 1 && page <= pages).sort((a, b) => a - b);
  let previous = 0;
  visiblePages.forEach((page) => {
    if (previous && page - previous > 1) {
      const gap = document.createElement("span");
      gap.textContent = "…";
      gap.setAttribute("aria-hidden", "true");
      elements.batchPageNumbers.append(gap);
    }
    const button = document.createElement("button");
    button.type = "button";
    button.className = "batch-page-number";
    button.textContent = String(page);
    button.setAttribute("aria-label", `第 ${page} 页`);
    button.setAttribute("aria-controls", "batch-list");
    if (page === batchPage) button.setAttribute("aria-current", "page");
    button.addEventListener("click", () => changeBatchPage(page));
    elements.batchPageNumbers.append(button);
    previous = page;
  });
}

function changeBatchPage(page) {
  if (!currentBatch) return;
  const pages = Math.max(1, Math.ceil(visibleQueueJobs().length / BATCH_PAGE_SIZE));
  const next = Math.max(1, Math.min(pages, page));
  if (next === batchPage) return;
  batchPage = next;
  renderBatch(currentBatch);
  elements.batchPanel.scrollIntoView({ block: "start", behavior: "instant" });
  document.querySelector("#batch-title").focus({ preventScroll: true });
}

elements.batchPagePrevious.addEventListener("click", () => changeBatchPage(batchPage - 1));
elements.batchPageNext.addEventListener("click", () => changeBatchPage(batchPage + 1));

async function showBatchResult(jobId) {
  if (expandedBatchJobId === jobId) {
    closeBatchResult();
    return;
  }
  const row = batchRows.get(jobId);
  if (!row) return;
  const anchorTop = row.row.getBoundingClientRect().top;
  closeBatchResult();
  // Closing an earlier card must not move the newly selected card off screen.
  window.scrollBy({ top: row.row.getBoundingClientRect().top - anchorTop, behavior: "instant" });
  expandedBatchJobId = jobId;
  const request = ++batchResultRequest;
  row.view.textContent = "收起结果";
  row.view.setAttribute("aria-expanded", "true");
  row.cover.setAttribute("aria-expanded", "true");
  row.row.classList.add("is-expanded");
  row.feedback.textContent = "正在读取结果…";
  row.feedback.classList.remove("hidden");
  row.row.setAttribute("aria-busy", "true");
  try {
    const job = await loadBatchResult(jobId);
    if (request !== batchResultRequest || expandedBatchJobId !== jobId) return;
    if (!job.result) throw new Error("结果暂未就绪，请稍后再试");
    batchResults.set(jobId, job);
    row.row.append(elements.resultPanel);
    renderResult(job.result, job.id, { inline: true });
    if (batchEdits.has(jobId)) {
      elements.editor.value = batchEdits.get(jobId);
      transcriptDirty = elements.editor.value !== transcriptBaseline;
    }
    row.feedback.classList.add("hidden");
    fitBatchEditor();
    elements.editor.scrollTop = batchReadingPositions.get(jobId)?.inline || 0;
    if (row.row.getBoundingClientRect().top < 0) {
      row.row.scrollIntoView({ block: "start", behavior: "instant" });
    }
  } catch (error) {
    if (request !== batchResultRequest) return;
    row.feedback.textContent = `结果读取失败：${error.message}。收起后可重新打开。`;
  } finally {
    if (request === batchResultRequest) row.row.removeAttribute("aria-busy");
  }
}

function closeBatchResult() {
  ++batchResultRequest;
  resetBatchVideoPreview();
  closeBatchReader();
  if (expandedBatchJobId) {
    if (currentJobId === expandedBatchJobId && !elements.resultPanel.classList.contains("hidden")) {
      batchEdits.set(currentJobId, elements.editor.value);
      const position = batchReadingPositions.get(currentJobId) || {};
      batchReadingPositions.set(currentJobId, { ...position, inline: elements.editor.scrollTop });
    }
    const row = batchRows.get(expandedBatchJobId);
    if (row) {
      row.view.textContent = "查看结果";
      row.view.setAttribute("aria-expanded", "false");
      row.cover.setAttribute("aria-expanded", "false");
      row.row.classList.remove("is-expanded");
      row.row.removeAttribute("aria-busy");
      row.feedback.classList.add("hidden");
    }
    expandedBatchJobId = null;
  }
  elements.resultPanel.classList.add("hidden");
  resultPanelHome.after(elements.resultPanel);
}

function resetBatchVideoPreview() {
  const player = elements.batchVideoPlayer;
  player.pause();
  if (player.hasAttribute("src")) {
    player.removeAttribute("src");
    player.load();
  }
  player.removeAttribute("poster");
  elements.batchVideoError.classList.add("hidden");
}

function renderBatchVideoPreview(media, jobId, inline) {
  const visible = inline && media.kind === "video";
  const available = (media.saved === true || Boolean(media.video_url)) && Boolean(jobId);
  const source = visible && available ? new URL(media.video_url || `/api/jobs/${encodeURIComponent(jobId)}/video`, location.href) : null;
  if (source && !media.video_url) source.port = String(Number(location.port || 80) + 1);
  const reuse = source && elements.batchVideoPlayer.getAttribute("src") === source.href;
  if (!reuse) resetBatchVideoPreview();
  elements.batchVideoPreview.classList.toggle("hidden", !visible);
  if (!visible) return;
  elements.batchVideoPlayer.classList.toggle("hidden", !available);
  elements.batchVideoUnavailable.classList.toggle("hidden", available);
  if (!available) return;
  if (media.cover_url) elements.batchVideoPlayer.poster = media.cover_url;
  // Older running sessions use a read-only loopback bridge, preserving their
  // in-memory results. New app instances return their native playback URL.
  if (!reuse) elements.batchVideoPlayer.src = source.href;
}

elements.batchVideoPlayer.addEventListener("error", () => {
  if (elements.batchVideoPlayer.error && elements.batchVideoPlayer.hasAttribute("src")) {
    elements.batchVideoError.classList.remove("hidden");
  }
});
elements.batchVideoPlayer.addEventListener("loadedmetadata", () => {
  elements.batchVideoError.classList.add("hidden");
});

function fitBatchEditor() {
  if (!expandedBatchJobId || !currentResult) return;
  const editor = elements.editor;
  const scrollTop = editor.scrollTop;
  editor.style.height = "0px";
  const limit = window.innerWidth <= 600 ? Math.min(400, window.innerHeight * 0.5) : 400;
  editor.style.height = `${Math.max(100, Math.min(limit, editor.scrollHeight + 2))}px`;
  editor.scrollTop = scrollTop;
  elements.batchTextHint.textContent = `共 ${editor.value.length.toLocaleString()} 字符 · 复制和 TXT 下载包含完整文案${editor.scrollHeight > editor.clientHeight + 2 ? " · 向下滚动阅读全文" : ""}`;
}

elements.batchReadOpen.addEventListener("click", () => {
  if (!expandedBatchJobId || !currentResult) return;
  batchReaderJobId = expandedBatchJobId;
  elements.batchReaderTitle.textContent = currentResult.media.title;
  elements.batchReaderMeta.textContent = `第 ${batchRows.get(batchReaderJobId).index + 1} 条 · ${elements.editor.value.length.toLocaleString()} 字符 · 关闭后返回原卡片`;
  elements.batchReaderText.value = elements.editor.value;
  elements.batchReaderText.setSelectionRange(elements.editor.selectionStart, elements.editor.selectionEnd);
  elements.batchReaderFeedback.textContent = "";
  elements.batchReader.showModal();
  elements.batchReaderText.scrollTop = batchReadingPositions.get(batchReaderJobId)?.reader || 0;
});
function closeBatchReader() {
  if (!elements.batchReader.open) return;
  if (batchReaderJobId) {
    syncExpandedTranscript();
    const position = batchReadingPositions.get(batchReaderJobId) || {};
    batchReadingPositions.set(batchReaderJobId, { ...position, reader: elements.batchReaderText.scrollTop });
  }
  elements.batchReader.close();
  batchReaderJobId = null;
}
function syncExpandedTranscript() {
  if (!batchReaderJobId || currentJobId !== batchReaderJobId) return;
  if (elements.editor.value !== elements.batchReaderText.value) {
    elements.editor.value = elements.batchReaderText.value;
    elements.editor.dispatchEvent(new Event("input", { bubbles: true }));
  }
  const row = batchRows.get(batchReaderJobId);
  if (row) elements.batchReaderMeta.textContent = `第 ${row.index + 1} 条 · ${elements.editor.value.length.toLocaleString()} 字符 · 关闭后返回原卡片`;
}
elements.batchReaderText.addEventListener("input", syncExpandedTranscript);
elements.batchReaderClose.addEventListener("click", closeBatchReader);
elements.batchReader.addEventListener("cancel", (event) => {
  event.preventDefault();
  closeBatchReader();
});
elements.batchReaderCopy.addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(elements.editor.value);
    elements.batchReaderFeedback.textContent = "完整文案已复制";
  } catch {
    elements.batchReaderFeedback.textContent = "复制失败，请在正文中选择文字复制";
  }
});
elements.batchReaderDownload.addEventListener("click", () => elements.downloadText.click());
window.addEventListener("resize", fitBatchEditor);

function singleQueueItem(source, job) {
  if (job.result) batchResults.set(job.id, job);
  rememberCardSummary(job);
  syncExpandedCard(job);
  const content = source.payload?.content || "";
  const url = content.match(/https?:\/\/[^\s<>]+/i)?.[0]
    ?.replace(/[。！？，,；;：:）)】\]}>"']+$/g, "") || content;
  return {
    id: job.id, source_url: url, status: job.status, progress: job.progress,
    message: job.message, title: job.result?.media?.title || null,
    result_available: Boolean(job.result), auth_status: job.auth_status || null, error: job.error || null,
    subtitle_completed: Boolean(job.result?.transcript), summary_completed: Boolean(job.summary),
    subtitle_state: job.subtitle_state, summary_state: job.summary_state,
  };
}

function sourceFinished(snapshot) {
  return Boolean(snapshot) && snapshot.jobs.every((job) => ["completed", "failed", "paused"].includes(job.status));
}

function renderProcessingQueue() {
  const seen = new Set();
  const jobs = queueSources.flatMap((source) => queueSnapshots.get(source.id)?.jobs || [])
    .filter((job) => {
      if (seen.has(job.id) || deletedQueueJobs.has(job.id)) return false;
      seen.add(job.id);
      return true;
    });
  const count = (status) => jobs.filter((job) => job.status === status).length;
  renderBatch({
    id: "processing-queue", jobs, total: jobs.length,
    completed: count("completed"), failed: count("failed"),
    paused: count("paused"),
    queued: count("queued"), running: count("running"),
    progress: jobs.length ? Math.round(jobs.reduce((sum, job) => sum
      + (["completed", "failed", "paused"].includes(job.status) ? 100 : job.progress), 0) / jobs.length) : 0,
    duplicate_count: queueSources.reduce((sum, source) => sum
      + (queueSnapshots.get(source.id)?.duplicate_count || 0), 0),
  });
}

function refreshProcessingQueue() {
  if (queueRefreshPromise) return queueRefreshPromise;
  clearTimeout(batchPollTimer);
  queueRefreshPromise = (async () => {
    const errors = [];
    await Promise.all(queueSources.filter((source) => !queueUnavailable.has(source.id)
      && !sourceFinished(queueSnapshots.get(source.id))).map(async (source) => {
      try {
        const data = await api(source.type === "batch" ? `/api/batches/${source.id}` : `/api/jobs/${source.id}`);
        queueSnapshots.set(source.id, source.type === "batch" ? data
          : { jobs: [singleQueueItem(source, data)], duplicate_count: 0 });
      } catch (error) {
        errors.push(error.message);
        if (error.status === 404) {
          queueUnavailable.add(source.id);
          const previous = queueSnapshots.get(source.id);
          if (previous) queueSnapshots.set(source.id, {
            ...previous,
            jobs: previous.jobs.map((job) => ["completed", "failed", "paused"].includes(job.status) ? job : {
              ...job, status: "failed", message: "后台任务记录已清除，请重新提交链接",
              error: { code: "record_unavailable", message: "后台任务记录已清除，请重新提交链接" },
            }),
          });
        }
      }
    }));
    renderProcessingQueue();
    if (errors.length) {
      elements.queueStatusError.textContent = "部分任务状态暂不可用";
      elements.queueStatusError.title = errors.join("；");
    } else {
      elements.queueStatusError.textContent = "";
      elements.queueStatusError.removeAttribute("title");
    }
    if (queueSources.some((source) => !queueUnavailable.has(source.id)
      && !sourceFinished(queueSnapshots.get(source.id)))) {
      batchPollTimer = setTimeout(refreshProcessingQueue, 1500);
    }
  })().finally(() => { queueRefreshPromise = null; });
  return queueRefreshPromise;
}

async function pauseQueueItem(jobId) {
  const job = currentBatch?.jobs.find((item) => item.id === jobId);
  if (!job || !["queued", "running"].includes(job.status) || queuePausing.has(jobId)) return;
  queuePausing.add(jobId);
  renderProcessingQueue();
  try {
    const paused = await api(`/api/jobs/${jobId}/pause`, { method: "POST" });
    if (queueRefreshPromise) await queueRefreshPromise;
    for (const [sourceId, snapshot] of queueSnapshots) {
      queueSnapshots.set(sourceId, { ...snapshot, jobs: snapshot.jobs.map((item) => item.id === jobId
        ? { ...item, status: paused.status, progress: paused.progress, message: paused.message,
          auth_status: paused.auth_status, error: paused.error } : item) });
    }
    elements.queueFeedback.textContent = "此任务已暂停，已有素材保留。点击重试可重新开始。";
  } catch (error) {
    elements.queueFeedback.textContent = `暂停失败：${error.message}`;
  } finally {
    queuePausing.delete(jobId);
    renderProcessingQueue();
    void refreshProcessingQueue();
  }
}

async function retryQueueItem(jobId, refresh = true) {
  const job = currentBatch?.jobs.find((item) => item.id === jobId);
  if (!job || !["failed", "paused"].includes(job.status) || queuePausing.has(jobId) || queueRetrying.has(jobId) || queueDeleteBusy) return false;
  const source = queueSources.find((item) => queueSnapshots.get(item.id)?.jobs.some((job) => job.id === jobId));
  if (!source) return false;
  queueRetrying.add(jobId);
  renderBatch(currentBatch);
  const payload = { content: job.source_url, language: source.payload?.language || "zh",
    save_video: source.payload?.save_video ?? true, extract_txt: source.payload?.extract_txt ?? true };
  try {
    let data;
    let retryApiBase = await materialTaskBase();
    try {
      data = await api(`/api/jobs/${jobId}/retry`, { method: "POST" });
    } catch (error) {
      if (![404, 405].includes(error.status)) throw error;
      // Older running sessions have no per-job retry endpoint. Verify that
      // this exact job failed, then submit just its original link/options.
      const original = await api(`/api/jobs/${jobId}`);
      if (!["failed", "paused"].includes(original.status)) throw new Error("此任务当前不可重试");
      retryApiBase = await taskSubmissionBase(payload.extract_txt, payload.content);
      data = await api(retryApiBase + "/api/jobs", { method: "POST", body: JSON.stringify(payload) });
    }
    const retried = { type: "single", id: data.job_id, payload, api_base: retryApiBase,
      retry_of: jobId, submitted_at: new Date().toISOString() };
    queueSources.unshift(retried);
    queueSnapshots.set(retried.id, { jobs: [singleQueueItem(retried, {
      id: data.job_id, status: "queued", progress: 0, message: "等待处理",
    })], duplicate_count: 0 });
    deletedQueueJobs.add(jobId);
    selectedQueueJobs.delete(jobId);
    rememberQueue();
    try { localStorage.setItem(QUEUE_DELETED_KEY, JSON.stringify([...deletedQueueJobs])); } catch { /* retry_of also restores this replacement */ }
    batchPage = 1;
    elements.queueFeedback.textContent = "已单独提交重试，其他任务保持不变。";
    return true;
  } catch (error) {
    elements.queueFeedback.textContent = `重试失败：${error.message}`;
    return false;
  } finally {
    queueRetrying.delete(jobId);
    renderProcessingQueue();
    if (refresh) void refreshProcessingQueue();
  }
}

elements.batchRetry.addEventListener("click", async () => {
  if (!currentBatch || queueRetryBusy || queueRetrying.size || queueDeleteBusy) return;
  const failed = currentBatch.jobs.filter((job) => ["failed", "paused"].includes(job.status)).map((job) => job.id);
  queueRetryBusy = true;
  renderBatch(currentBatch);
  try {
    for (const jobId of failed) await retryQueueItem(jobId, false);
  } finally {
    queueRetryBusy = false;
    renderProcessingQueue();
    void refreshProcessingQueue();
  }
});

function closeQueueMenus(except = null) {
  for (const row of batchRows.values()) if (row.menu !== except) row.menu.open = false;
}

document.addEventListener("click", (event) => {
  for (const row of batchRows.values()) {
    if (!row.menu.contains(event.target)) row.menu.open = false;
  }
});

let pendingQueueDelete = [];
let queueDeleteReturnFocus = null;
function openQueueDelete(jobIds, returnFocus = elements.queueDelete) {
  if (!currentBatch || queueDeleteBusy || queueArchiveBusy || queueRetryBusy || queueRetrying.size) return;
  const wanted = new Set(jobIds);
  const jobs = currentBatch.jobs.filter((job) => wanted.has(job.id) && canSelectQueueRecord(job));
  pendingQueueDelete = jobs.map((job) => job.id);
  if (!pendingQueueDelete.length) return;
  queueDeleteReturnFocus = returnFocus;
  closeQueueMenus();
  elements.queueDeleteCount.textContent = jobs.length === 1
    ? `确认删除这条素材记录：“${jobs[0].title || jobs[0].source_url}”？`
    : `确认删除选中的 ${jobs.length} 条任务记录？`;
  elements.queueDeleteFiles.checked = false;
  elements.queueDeleteError.textContent = "";
  elements.queueDeleteDialog.showModal();
  elements.queueDeleteCancel.focus();
}
elements.queueDelete.addEventListener("click", () => openQueueDelete([...selectedQueueJobs]));
elements.queueDeleteDialog.addEventListener("close", () => {
  if (queueDeleteReturnFocus?.isConnected && !queueDeleteReturnFocus.disabled) queueDeleteReturnFocus.focus({ preventScroll: true });
  else document.querySelector("#batch-title").focus({ preventScroll: true });
});
elements.queueDeleteCancel.addEventListener("click", () => elements.queueDeleteDialog.close());
elements.queueDeleteDialog.addEventListener("cancel", (event) => {
  if (queueDeleteBusy) event.preventDefault();
});
elements.queueDeleteConfirm.addEventListener("click", async () => {
  if (queueDeleteBusy || !pendingQueueDelete.length) return;
  queueDeleteBusy = true;
  elements.queueDeleteConfirm.disabled = true;
  elements.queueDeleteCancel.disabled = true;
  elements.queueDeleteFiles.disabled = true;
  elements.queueDeleteConfirm.textContent = "正在删除…";
  syncQueueSelection();
  try {
    let result = null;
    if (elements.queueDeleteFiles.checked) {
      const ids = new Set(pendingQueueDelete);
      const payload = { job_ids: pendingQueueDelete,
        protect_job_ids: currentBatch.jobs.filter((job) => !ids.has(job.id)).map((job) => job.id) };
      const options = { method: "POST", body: JSON.stringify(payload) };
      const hasWorkerJobs = queueSources.some((source) => source.api_base === downloadTaskBase());
      const filesBase = hasWorkerJobs && !await nativeTaskSupport() ? downloadTaskBase() : "";
      try {
        result = await api(filesBase + "/api/jobs/files/delete", options);
      } catch (error) {
        if (![404, 405].includes(error.status)) throw error;
        const endpoint = new URL("/api/jobs/files/delete", location.href);
        endpoint.port = String(Number(location.port || 80) + 1);
        result = await api(endpoint.href, options);
      }
    }
    const removed = new Set([...deletedQueueJobs, ...pendingQueueDelete]);
    // Persist before hiding rows so a browser refresh cannot restore them.
    localStorage.setItem(QUEUE_DELETED_KEY, JSON.stringify([...removed]));
    if (pendingQueueDelete.includes(expandedBatchJobId)) closeBatchResult();
    for (const id of pendingQueueDelete) {
      deletedQueueJobs.add(id);
      selectedQueueJobs.delete(id);
      batchResults.delete(id);
      batchEdits.delete(id);
    }
    elements.queueFeedback.textContent = `已删除 ${pendingQueueDelete.length} 条记录。`
      + (result ? `已删除 ${result.deleted_files} 个源文件。${result.shared_files ? `另有 ${result.shared_files} 个文件仍被其他任务使用，已保留。` : ""}` : "本地源文件已保留。");
    elements.queueDeleteDialog.close();
    renderProcessingQueue();
  } catch (error) {
    elements.queueDeleteError.textContent = `删除未完成：${error.message}`;
  } finally {
    queueDeleteBusy = false;
    elements.queueDeleteConfirm.disabled = false;
    elements.queueDeleteCancel.disabled = false;
    elements.queueDeleteFiles.disabled = false;
    elements.queueDeleteConfirm.textContent = "删除";
    renderProcessingQueue();
  }
});

function displayLanguageName(language) {
  const names = {
    zh: "中文",
    en: "英语",
    ja: "日语",
    ko: "韩语",
    yue: "粤语",
    fr: "法语",
    de: "德语",
    es: "西班牙语",
  };
  return names[language] || language;
}

function renderResult(result, jobId, { inline = false } = {}) {
  const keepView = inline && currentJobId === jobId && !elements.resultPanel.classList.contains("hidden");
  const previousView = selectedResultView;
  if (!inline) {
    closeBatchResult();
    elements.editor.style.height = "";
  }
  currentResult = result;
  currentJobId = jobId || null;
  resetSummary();
  const media = result.media;
  const isImages = media.kind === "images";
  elements.resultPanel.classList.remove("hidden");
  const hasTranscript = Boolean(result.transcript?.text?.trim());
  const hasText = hasTranscript || Boolean(isImages && media.description?.trim());
  elements.resultPanel.dataset.hasTranscript = String(hasTranscript);
  elements.batchVideoUnavailable.textContent = hasTranscript
    ? "此任务未保留视频，无法本地预览。逐字稿仍可正常查看。"
    : "此任务未保留视频，无法本地预览。";
  elements.resultPanel.dataset.mediaKind = media.kind;
  elements.resultPanel.classList.toggle("is-batch-result", inline);
  elements.downloadText.textContent = "TXT";
  elements.downloadControls.classList.toggle("hidden", inline);
  if (inline) {
    elements.transcriptTextActions.prepend(elements.copyText, elements.downloadControls);
  } else {
    elements.transcriptActions.append(elements.copyText, elements.downloadControls);
  }
  clearTimeout(copyFeedbackTimer);
  elements.copyText.classList.remove("copy-success");
  elements.copyLabel.textContent = "复制文案";
  elements.copyText.setAttribute("aria-label", "复制文案");
  elements.batchReadOpen.classList.toggle("hidden", !inline || !hasText);
  elements.batchTextHint.classList.toggle("hidden", !inline || !hasText);
  elements.resultViewPanel.setAttribute("aria-labelledby", "view-tab-text");
  elements.resultViewPanel.setAttribute("role", "tabpanel");
  document.querySelector("#view-tab-text").textContent = inline ? (isImages ? "图文文案" : "字幕") : "纯文本";
  elements.transcriptActions.classList.toggle("hidden", inline || !hasText);
  elements.imageResult.classList.toggle("hidden", !isImages);
  elements.videoResult.classList.remove("hidden");
  elements.editor.setAttribute("aria-label", isImages ? "图文文案，可编辑" : "视频逐字稿，可编辑");
  elements.videoDetails.classList.toggle("hidden", isImages || inline);
  renderBatchVideoPreview(media, jobId, inline);
  elements.resultTypeBadge.textContent = isImages ? "图片作品" : "视频作品";
  elements.resultTypeBadge.className = `result-type-badge ${isImages ? "images" : "video"}`;
  elements.resultTitle.textContent = batchResults.get(jobId)?.status === "running" ? "视频已就绪"
    : isImages || hasTranscript ? "识别完成" : "视频处理完成";
  renderMediaPath(media, jobId);

  if (isImages) {
    renderImageResult(media);
    elements.editor.value = media.description || "";
    transcriptBaseline = elements.editor.value;
  } else {
    renderVideoResult(result);
  }
  transcriptDirty = false;

  const cachedSummary = cardSummaries.get(jobId);
  if (cachedSummary) {
    summaryData = cachedSummary;
    renderSummary();
    setSummaryState("done");
  }
  if (batchResults.get(jobId)?.summary_state === "generating" && !summaryAbortController) setSummaryState("busy");
  else if (batchResults.get(jobId)?.summary_state === "failed") {
    elements.summaryErrorText.textContent = "总结生成失败，可重新尝试。视频和字幕已保留。";
    setSummaryState("error");
  }
  updateResultContentActions(jobId);
  selectView(keepView ? previousView : inline && !hasText ? null : "text");

  const behavior = window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth";
  if (!inline) {
    elements.resultPanel.scrollIntoView({ behavior, block: "start" });
    elements.resultTitle.focus({ preventScroll: true });
  }
  if (inline && !isImages && media.saved && batchResults.get(jobId)?.status !== "running") void monitorCardTranscript(jobId);
}

function renderMediaPath(media, jobId) {
  const isImages = media.kind === "images";
  elements.batchFileActions.replaceChildren();
  elements.batchFileActions.classList.add("hidden");
  elements.mediaPath.replaceChildren();
  elements.mediaPath.className = `result-file ${media.saved ? "saved" : "deleted"} ${media.kind}`;
  const pathSummary = document.createElement("div");
  pathSummary.className = "result-file-main";
  const pathStatus = document.createElement("span");
  pathStatus.className = `result-file-status ${media.saved ? "saved" : "deleted"}`;
  pathStatus.textContent = isImages ? "已归档" : (media.saved ? "已保留" : "已清理");
  const pathCopy = document.createElement("div");
  pathCopy.className = "result-file-copy";
  const pathTitle = document.createElement("strong");
  pathTitle.textContent = isImages
    ? "图片已保存到独立文件夹"
    : (media.saved ? "视频文件已保留" : "临时视频已自动清理");
  const pathHint = document.createElement("span");
  pathHint.textContent = isImages
    ? `${media.asset_count} 张原图按作品顺序编号，Live 动态文件使用同一编号`
    : (media.saved
      ? "后续可以直接使用本机 MP4"
      : "识别完成后已删除，不占用本机空间");
  pathCopy.append(pathTitle, pathHint);
  pathSummary.append(pathStatus, pathCopy);
  const inline = elements.resultPanel.classList.contains("is-batch-result");
  const pathLocation = document.createElement(media.saved && !inline ? "div" : "details");
  if (!media.saved && !inline) pathLocation.open = true;
  pathLocation.className = `result-file-location ${media.saved ? "visible-path" : ""}`;
  const pathLabel = document.createElement(media.saved && !inline ? "span" : "summary");
  pathLabel.textContent = media.saved
    ? (isImages && !inline ? "文件夹位置" : "保存位置")
    : "查看原临时路径";
  const pathValue = document.createElement("code");
  pathValue.textContent = media.absolute_path;
  pathValue.title = media.absolute_path;
  pathValue.setAttribute("translate", "no");
  if (jobId && (media.saved || media.title_path || media.cover_path || media.description_path)) {
    const pathHeading = document.createElement("div");
    pathHeading.className = "result-file-location-heading";
    const openLocation = document.createElement("button");
    openLocation.className = "result-open-location";
    openLocation.type = "button";
    openLocation.textContent = "打开文件夹";
    openLocation.setAttribute("aria-label", "在父目录中定位作品文件夹");
    const openFeedback = document.createElement("p");
    openFeedback.className = "result-open-location-feedback";
    openFeedback.setAttribute("role", "status");
    openFeedback.setAttribute("aria-live", "polite");
    openLocation.addEventListener("click", async () => {
      openLocation.disabled = true;
      openLocation.setAttribute("aria-busy", "true");
      openLocation.textContent = "正在打开…";
      openFeedback.textContent = "";
      openFeedback.classList.remove("has-error");
      try {
        await api(`/api/jobs/${encodeURIComponent(jobId)}/open-location`, { method: "POST" });
        openLocation.textContent = "已打开";
        openFeedback.textContent = "已在父目录中定位作品文件夹";
      } catch (error) {
        openLocation.textContent = "打开失败";
        openFeedback.textContent = error.message;
        openFeedback.classList.add("has-error");
      } finally {
        openLocation.disabled = false;
        openLocation.setAttribute("aria-busy", "false");
        window.setTimeout(() => {
          if (openLocation.isConnected) openLocation.textContent = "打开文件夹";
        }, 1400);
      }
    });
    if (inline) {
      pathLocation.append(pathLabel, pathValue);
      for (const [label, value] of [["封面", media.cover_path], ["标题", media.title_path]]) {
        if (!value) continue;
        const detailPath = document.createElement("code");
        detailPath.textContent = `${label}：${value}`;
        detailPath.setAttribute("translate", "no");
        pathLocation.append(detailPath);
      }
      pathSummary.append(openLocation, openFeedback);
    } else {
      pathHeading.append(pathLabel, openLocation);
      pathLocation.append(pathHeading, pathValue, openFeedback);
    }
  } else {
    pathLocation.append(pathLabel, pathValue);
  }
  if (inline) {
    const openLocation = pathSummary.querySelector(".result-open-location");
    const openFeedback = pathSummary.querySelector(".result-open-location-feedback");
    if (openLocation) {
      openFeedback.classList.add("visually-hidden");
      elements.batchFileActions.append(openLocation, openFeedback);
      elements.batchFileActions.classList.remove("hidden");
    }
    updateResultContentActions(jobId);
    return;
  }
  elements.mediaPath.append(pathSummary, pathLocation);
}

function updateResultContentActions(jobId) {
  if (!currentResult || currentJobId !== jobId) return;
  const media = currentResult.media;
  const images = media.kind === "images";
  const hasText = Boolean(images ? media.description?.trim() : currentResult.transcript?.text?.trim());
  const detail = batchResults.get(jobId);
  const action = cardTranscriptActions.get(jobId) || {};
  const running = detail?.status === "running";
  const subtitleBusy = Boolean(action.busy) || (running && detail?.subtitle_state === "generating");
  const canExtract = !images && media.saved && (!detail || detail.status === "completed") && !subtitleBusy;
  document.querySelector("#transcript-empty").classList.toggle("hidden", hasText);
  elements.textView.querySelector(".transcript-editor-frame").classList.toggle("hidden", !hasText);
  document.querySelector("#transcript-bottom-actions").classList.toggle("hidden", !hasText);
  elements.batchTextHint.classList.toggle("hidden", !hasText || !elements.resultPanel.classList.contains("is-batch-result"));
  const extract = document.querySelector("#transcript-generate");
  extract.classList.toggle("hidden", images);
  extract.textContent = subtitleBusy ? "提取中…" : "提取字幕";
  const regenerate = document.querySelector("#transcript-regenerate");
  regenerate.classList.toggle("hidden", images);
  for (const button of [extract, regenerate]) {
    button.disabled = !canExtract;
    button.setAttribute("aria-busy", String(subtitleBusy));
  }
  document.querySelector("#transcript-empty-note").textContent = images ? "这条图文没有正文。"
    : subtitleBusy ? "字幕正在生成，请稍候。" : !media.saved ? "未保留本地视频，无法提取字幕。" : "还没有这条作品的字幕。";
  const feedback = document.querySelector("#transcript-action-feedback");
  feedback.classList.toggle("has-error", Boolean(action.error));
  if (action.busy) {
    const elapsed = action.elapsed_seconds || Math.floor((Date.now() - (action.startedAt || Date.now())) / 1000);
    const duration = elapsed >= 60 ? `${Math.floor(elapsed / 60)}分${elapsed % 60}秒` : `${elapsed}秒`;
    const progress = Number.isFinite(action.progress) ? ` ${action.progress}%` : "";
    feedback.textContent = `${action.message || "正在准备提取字幕"}${progress} · 已用 ${duration}。本地识别可能需要数分钟。`;
  } else feedback.textContent = subtitleBusy ? "视频已下载，可先播放；字幕正在生成。" : action.message || "";
  const summaryBusy = summaryStatus === "busy" || ["waiting", "generating"].includes(detail?.summary_state);
  elements.summaryGenerate.disabled = !hasText || summaryBusy || (detail && detail.status !== "completed");
  elements.summaryEmpty.querySelector("p").textContent = !hasText
    ? images ? "这条图文没有可供总结的正文。" : "请先在字幕页提取字幕，再生成AI总结。"
    : detail?.summary_state === "waiting" ? "字幕完成后将自动生成总结。" : "基于当前卡片文案生成。";
}

document.querySelector("#transcript-generate").addEventListener("click", () => extractCardTranscript(currentJobId));
document.querySelector("#transcript-regenerate").addEventListener("click", () => extractCardTranscript(currentJobId));

async function confirmCardRegeneration(kind) {
  const dialog = document.querySelector("#card-regenerate-dialog");
  if (dialog.open) return false;
  const subtitle = kind === "transcript";
  const initial = kind === "summary_initial";
  const automatic = kind === "automatic";
  document.querySelector("#card-regenerate-title").textContent = automatic ? "开启自动生成AI总结？" : subtitle ? "重新提取字幕？" : initial ? "生成AI总结？" : "重新生成AI总结？";
  document.querySelector("#card-regenerate-message").textContent = subtitle
    ? "这条作品已提取字幕，是否重新生成？生成成功后显示新字幕，原有字幕文件会保留。"
    : automatic ? "开启后，新任务会在字幕完成后自动生成总结，是否开启？"
    : initial ? "是否使用当前文案生成AI总结？" : "这条作品已有AI总结，是否使用当前文案重新生成？";
  dialog.querySelector('[value="regenerate"]').textContent = automatic ? "确认开启" : initial ? "开始生成" : "重新生成";
  dialog.returnValue = "cancel";
  const answer = new Promise((resolve) => dialog.addEventListener("close", () => resolve(dialog.returnValue === "regenerate"), { once: true }));
  dialog.showModal();
  return answer;
}

function applyCardTranscriptResult(jobId, detail) {
  if (deletedQueueJobs.has(jobId)) return;
  const previous = batchResults.get(jobId)?.result;
  const unchanged = previous?.transcript && previous.transcript.text === detail.result?.transcript?.text
    && previous.media.description_path === detail.result?.media?.description_path;
  batchResults.set(jobId, detail);
  rememberCardSummary(detail);
  updateCardCompletionBadges(jobId);
  cardTranscriptActions.set(jobId, { message: "字幕提取完成，已保存到作品文件夹。" });
  if (unchanged && (currentJobId !== jobId || currentResult?.transcript)) return;
  batchEdits.delete(jobId);
  if (currentJobId === jobId && expandedBatchJobId === jobId) {
    renderResult(detail.result, jobId, { inline: true });
    fitBatchEditor();
  }
}

async function monitorCardTranscript(jobId) {
  if (cardTranscriptMonitors.has(jobId)) return;
  cardTranscriptMonitors.add(jobId);
  let failures = 0;
  try {
    while (!deletedQueueJobs.has(jobId)) {
      let status;
      try {
        status = await api(`/api/jobs/${encodeURIComponent(jobId)}/transcript/status`);
        failures = 0;
      } catch {
        if (++failures >= 3 && cardTranscriptActions.get(jobId)?.busy) {
          const state = cardTranscriptActions.get(jobId);
          state.message = "暂时无法读取进度，正在重新连接";
          if (currentJobId === jobId && expandedBatchJobId === jobId) renderMediaPath(currentResult.media, jobId);
        } else if (failures >= 3) return;
        await new Promise((resolve) => window.setTimeout(resolve, 1500));
        continue;
      }
      if (status.state === "completed") {
        if (cardTranscriptActions.get(jobId)?.requestPending) {
          await new Promise((resolve) => window.setTimeout(resolve, 1500));
          continue;
        }
        if (cardTranscriptActions.get(jobId)?.busy || !batchResults.get(jobId)?.result?.transcript) {
          applyCardTranscriptResult(jobId, await api(`/api/jobs/${encodeURIComponent(jobId)}`));
        }
        return;
      }
      if (status.state === "failed") {
        if (cardTranscriptActions.get(jobId)?.requestPending) {
          await new Promise((resolve) => window.setTimeout(resolve, 1500));
          continue;
        }
        cardTranscriptActions.set(jobId, { error: true, message: `字幕提取失败：${status.message}` });
      } else if (status.state === "running") {
        cardTranscriptActions.set(jobId, { ...cardTranscriptActions.get(jobId), ...status, busy: true });
      } else if (status.state !== "idle" || !cardTranscriptActions.get(jobId)?.busy) return;
      if (currentJobId === jobId && expandedBatchJobId === jobId) renderMediaPath(currentResult.media, jobId);
      if (status.state === "failed") return;
      await new Promise((resolve) => window.setTimeout(resolve, 1500));
    }
  } catch {
    // The extraction request reports its own error; reopening the card retries monitoring.
  } finally {
    cardTranscriptMonitors.delete(jobId);
  }
}

async function extractCardTranscript(jobId) {
  if (currentJobId !== jobId || cardTranscriptActions.get(jobId)?.busy) return;
  const regenerate = Boolean(currentResult?.transcript);
  if (regenerate && !await confirmCardRegeneration("transcript")) return;
  if (currentJobId !== jobId || cardTranscriptActions.get(jobId)?.busy) return;
  selectView("text");
  cardTranscriptActions.set(jobId, { busy: true, requestPending: true, startedAt: Date.now() });
  renderMediaPath(currentResult.media, jobId);
  void monitorCardTranscript(jobId);
  try {
    const detail = await api(`/api/jobs/${encodeURIComponent(jobId)}/transcript${regenerate ? "?regenerate=true" : ""}`, { method: "POST" });
    applyCardTranscriptResult(jobId, detail);
  } catch (error) {
    cardTranscriptActions.set(jobId, { error: true, message: `字幕提取失败：${error.message}` });
  } finally {
    const state = cardTranscriptActions.get(jobId);
    if (state) {
      state.busy = false;
      state.requestPending = false;
    }
    if (currentJobId === jobId && expandedBatchJobId === jobId && !deletedQueueJobs.has(jobId)) {
      renderMediaPath(currentResult.media, jobId);
    }
  }
}

document.addEventListener("click", (event) => {
  const location = elements.batchFileActions.querySelector("details[open]");
  if (location && !location.contains(event.target)) location.open = false;
});

document.addEventListener("click", (event) => {
  if (!expandedBatchJobId || !(event.target instanceof Element)) return;
  const row = batchRows.get(expandedBatchJobId)?.row;
  const target = event.target;
  if (!row || row.contains(target) || elements.queueTagPicker.contains(target) || document.querySelector("dialog[open]")) return;
  if (target.closest("a, button, input, textarea, select, label, summary, details, video, audio, img, dialog, [role='button'], [role='link'], [contenteditable]:not([contenteditable='false'])")) return;
  if (!target.matches("html, body, main, section, article, aside, header, footer, nav, form, div, ul, ol, li")) return;
  if ([...target.childNodes].some((node) => node.nodeType === Node.TEXT_NODE && node.textContent.trim())) return;
  if (queueDragClicks.has(event)) return;
  closeBatchResult();
});
elements.batchFileActions.addEventListener("keydown", (event) => {
  if (event.key !== "Escape") return;
  const location = elements.batchFileActions.querySelector("details[open]");
  if (!location) return;
  event.preventDefault();
  location.open = false;
  location.querySelector("summary").focus();
});

function renderImageResult(media) {
  const liveAssetsByIndex = new Map(
    media.assets
      .filter((asset) => asset.kind === "live_motion" && asset.playback_url)
      .map((asset) => [asset.index, asset]),
  );
  const imageAssets = media.assets
    .filter((asset) => asset.kind === "image")
    .sort((a, b) => a.index - b.index)
    .map((asset) => ({
      ...asset,
      playback_url: liveAssetsByIndex.get(asset.index)?.playback_url || null,
    }));
  const liveIndexes = new Set(liveAssetsByIndex.keys());
  const liveCopy = media.live_photo_count
    ? ` · ${media.live_photo_count} 张 Live 图`
    : "";
  elements.mediaMeta.classList.remove("video-meta");
  if (elements.resultPanel.classList.contains("is-batch-result")) {
    const facts = document.createElement("span");
    facts.className = "result-media-facts";
    const filename = document.createElement("code");
    filename.className = "result-media-filename";
    filename.textContent = media.filename;
    filename.title = media.filename;
    const count = document.createElement("span");
    count.className = "result-media-fact";
    count.textContent = `${media.asset_count} 张图片${liveCopy}`;
    facts.append(filename, count);
    elements.mediaMeta.classList.add("video-meta");
    elements.mediaMeta.replaceChildren(facts);
  } else {
    elements.mediaMeta.textContent = `${media.title} · ${media.asset_count} 张图片${liveCopy}`;
  }
  elements.imageResultNote.textContent = `${media.asset_count} 张图片 · 文件夹 ${media.filename}`;
  elements.livePhotoNote.classList.toggle("hidden", media.live_photo_count === 0);
  elements.imageGrid.replaceChildren();

  imageAssets.forEach((asset, position) => {
    const figure = document.createElement("figure");
    figure.className = "contact-frame";
    const imageShell = document.createElement("button");
    imageShell.className = "contact-image-shell image-preview-trigger";
    imageShell.type = "button";
    imageShell.setAttribute(
      "aria-label",
      asset.playback_url
        ? `打开并播放第 ${asset.index} 张 Live 图`
        : `放大查看第 ${asset.index} 张图片`,
    );
    const image = document.createElement("img");
    image.src = asset.preview_url;
    image.alt = `第 ${asset.index} 张图片`;
    image.loading = position < 4 ? "eager" : "lazy";
    image.decoding = "async";
    image.addEventListener("error", () => {
      imageShell.classList.add("preview-unavailable");
      imageShell.disabled = true;
      imageShell.setAttribute("aria-label", `第 ${asset.index} 张图片预览不可用`);
      image.remove();
      const fallback = document.createElement("span");
      fallback.textContent = "预览不可用";
      imageShell.append(fallback);
    }, { once: true });
    imageShell.addEventListener("click", () => {
      openImageViewer(imageAssets, position, imageShell);
    });
    imageShell.append(image);
    if (liveIndexes.has(asset.index)) {
      const liveBadge = document.createElement("span");
      liveBadge.className = "contact-live-badge";
      liveBadge.textContent = "LIVE";
      imageShell.append(liveBadge);
    }
    const caption = document.createElement("figcaption");
    const frameNumber = document.createElement("span");
    frameNumber.textContent = `FRAME ${String(asset.index).padStart(3, "0")}`;
    const filename = document.createElement("code");
    filename.textContent = asset.filename;
    filename.title = asset.filename;
    caption.append(frameNumber, filename);
    figure.append(imageShell, caption);
    elements.imageGrid.append(figure);
  });
}

function clamp(value, minimum, maximum) {
  return Math.min(maximum, Math.max(minimum, value));
}

function imageViewerIsOpen() {
  return elements.imageViewer.open;
}

function openImageViewer(assets, index, trigger) {
  const asset = assets[index];
  if (!asset?.preview_url) return;
  viewerAssets = assets;
  viewerIndex = index;
  viewerReturnFocus = trigger;
  document.body.classList.add("image-viewer-open");
  if (!imageViewerIsOpen()) elements.imageViewer.showModal();
  renderViewerImage();
  elements.imageViewer.focus({ preventScroll: true });
}

function closeImageViewer() {
  if (imageViewerIsOpen()) elements.imageViewer.close();
}

function setViewerLivePlaybackState(isPlaying) {
  viewerLiveIsPlaying = isPlaying;
  elements.imageViewerVideo.classList.toggle("hidden", !isPlaying);
  elements.imageViewerLiveReplay.classList.toggle("is-playing", isPlaying);
  elements.imageViewerCanvas.classList.toggle("is-live-playing", isPlaying);
  applyViewerTransform();
}

function stopViewerLivePlayback(clearSource = false) {
  elements.imageViewerVideo.pause();
  setViewerLivePlaybackState(false);
  if (!clearSource) return;
  elements.imageViewerVideo.removeAttribute("src");
  elements.imageViewerVideo.removeAttribute("poster");
  delete elements.imageViewerVideo.dataset.playbackUrl;
  elements.imageViewerVideo.load();
}

function playViewerLive() {
  const asset = viewerAssets[viewerIndex];
  if (!asset?.playback_url) return;
  const loadToken = viewerLoadToken;
  resetViewerZoom();
  try {
    elements.imageViewerVideo.currentTime = 0;
  } catch (_error) {
    // Some browsers defer seeking until the MP4 metadata is available.
  }
  setViewerLivePlaybackState(true);
  elements.imageViewerLiveReplay.setAttribute("aria-label", "从头重新播放 Live 图");
  const playRequest = elements.imageViewerVideo.play();
  if (playRequest === undefined) return;
  playRequest.catch(() => {
    if (loadToken !== viewerLoadToken) return;
    setViewerLivePlaybackState(false);
    elements.imageViewerLiveReplay.setAttribute("aria-label", "播放 Live 图");
  });
}

function renderViewerImage() {
  const asset = viewerAssets[viewerIndex];
  if (!asset) return;
  const loadToken = ++viewerLoadToken;
  stopViewerLivePlayback(true);
  resetViewerZoom();
  elements.imageViewerCanvas.setAttribute("aria-busy", "true");
  elements.imageViewerImage.classList.remove("hidden");
  elements.imageViewerError.classList.add("hidden");
  elements.imageViewerLiveReplay.classList.toggle("hidden", !asset.playback_url);
  elements.imageViewerLiveReplay.setAttribute("aria-label", "播放 Live 图");
  elements.imageViewerHelp.textContent = asset.playback_url
    ? "打开后自动带声音播放一次 · 悬停或点击左上角 LIVE 可重播"
    : "滚轮或双指缩放 · 放大后拖动查看";
  elements.imageViewerFilename.textContent = asset.filename;
  elements.imageViewerFilename.title = asset.filename;
  elements.imageViewerCounter.textContent = `${viewerIndex + 1} / ${viewerAssets.length}`;
  elements.imageViewerImage.alt = `第 ${asset.index} 张图片，共 ${viewerAssets.length} 张`;
  elements.imageViewerPrevious.disabled = viewerAssets.length < 2;
  elements.imageViewerNext.disabled = viewerAssets.length < 2;
  elements.imageViewerPrevious.setAttribute(
    "aria-label",
    `上一张图片，当前第 ${viewerIndex + 1} 张`,
  );
  elements.imageViewerNext.setAttribute(
    "aria-label",
    `下一张图片，当前第 ${viewerIndex + 1} 张`,
  );

  elements.imageViewerImage.onload = () => {
    if (loadToken !== viewerLoadToken) return;
    elements.imageViewerCanvas.setAttribute("aria-busy", "false");
    fitViewerImage();
    clampViewerOffsets();
    applyViewerTransform();
  };
  elements.imageViewerImage.onerror = () => {
    if (loadToken !== viewerLoadToken) return;
    elements.imageViewerCanvas.setAttribute("aria-busy", "false");
    elements.imageViewerImage.classList.add("hidden");
    elements.imageViewerError.classList.remove("hidden");
  };
  elements.imageViewerImage.src = asset.preview_url;

  if (asset.playback_url) {
    elements.imageViewerVideo.loop = false;
    elements.imageViewerVideo.muted = false;
    elements.imageViewerVideo.defaultMuted = false;
    elements.imageViewerVideo.volume = 1;
    elements.imageViewerVideo.poster = asset.preview_url;
    elements.imageViewerVideo.src = asset.playback_url;
    elements.imageViewerVideo.dataset.playbackUrl = asset.playback_url;
    elements.imageViewerVideo.onended = () => {
      if (loadToken !== viewerLoadToken) return;
      setViewerLivePlaybackState(false);
      elements.imageViewerLiveReplay.setAttribute("aria-label", "重新播放 Live 图");
    };
    elements.imageViewerVideo.onerror = () => {
      if (loadToken !== viewerLoadToken) return;
      setViewerLivePlaybackState(false);
      elements.imageViewerLiveReplay.setAttribute("aria-label", "Live 图播放失败，点击重试");
    };
    playViewerLive();
  }

  [viewerIndex - 1, viewerIndex + 1]
    .filter((position) => position >= 0 && position < viewerAssets.length)
    .forEach((position) => {
      const preload = new Image();
      preload.src = viewerAssets[position].preview_url;
    });
}

function navigateViewer(direction) {
  if (viewerAssets.length < 2) return;
  viewerIndex = (viewerIndex + direction + viewerAssets.length) % viewerAssets.length;
  renderViewerImage();
}

function applyViewerTransform() {
  elements.imageViewerImage.style.transform =
    `translate3d(${viewerOffsetX}px, ${viewerOffsetY}px, 0) scale(${viewerScale})`;
  elements.imageViewerZoomValue.value = `${Math.round(viewerScale * 100)}%`;
  elements.imageViewerZoomValue.textContent = `${Math.round(viewerScale * 100)}%`;
  elements.imageViewerZoomOut.disabled = viewerLiveIsPlaying || viewerScale <= VIEWER_MIN_SCALE;
  elements.imageViewerZoomIn.disabled = viewerLiveIsPlaying || viewerScale >= VIEWER_MAX_SCALE;
  elements.imageViewerZoomReset.disabled = viewerLiveIsPlaying || viewerScale <= VIEWER_MIN_SCALE;
  elements.imageViewerCanvas.classList.toggle(
    "is-zoomed",
    !viewerLiveIsPlaying && viewerScale > VIEWER_MIN_SCALE,
  );
}

function fitViewerImage() {
  const naturalWidth = elements.imageViewerImage.naturalWidth;
  const naturalHeight = elements.imageViewerImage.naturalHeight;
  if (!naturalWidth || !naturalHeight) return;
  const canvasStyles = getComputedStyle(elements.imageViewerCanvas);
  const horizontalRoom = Number.parseFloat(
    canvasStyles.getPropertyValue("--viewer-horizontal-room"),
  ) || 0;
  const verticalRoom = Number.parseFloat(
    canvasStyles.getPropertyValue("--viewer-vertical-room"),
  ) || 0;
  const availableWidth = Math.max(1, elements.imageViewerCanvas.clientWidth - horizontalRoom);
  const availableHeight = Math.max(1, elements.imageViewerCanvas.clientHeight - verticalRoom);
  const fitScale = Math.min(availableWidth / naturalWidth, availableHeight / naturalHeight);
  elements.imageViewerImage.style.width = `${Math.round(naturalWidth * fitScale)}px`;
  elements.imageViewerImage.style.height = `${Math.round(naturalHeight * fitScale)}px`;
}

function clampViewerOffsets() {
  if (viewerScale <= VIEWER_MIN_SCALE) {
    viewerOffsetX = 0;
    viewerOffsetY = 0;
    return;
  }
  const canvasRect = elements.imageViewerCanvas.getBoundingClientRect();
  const maxX = Math.max(0, (elements.imageViewerImage.clientWidth * viewerScale - canvasRect.width) / 2);
  const maxY = Math.max(0, (elements.imageViewerImage.clientHeight * viewerScale - canvasRect.height) / 2);
  viewerOffsetX = clamp(viewerOffsetX, -maxX, maxX);
  viewerOffsetY = clamp(viewerOffsetY, -maxY, maxY);
}

function setViewerZoom(nextScale, focalClientX = null, focalClientY = null) {
  if (viewerLiveIsPlaying) return;
  const previousScale = viewerScale;
  const clampedScale = clamp(nextScale, VIEWER_MIN_SCALE, VIEWER_MAX_SCALE);
  if (clampedScale === previousScale) return;

  if (clampedScale === VIEWER_MIN_SCALE) {
    viewerOffsetX = 0;
    viewerOffsetY = 0;
  } else if (focalClientX !== null && focalClientY !== null) {
    const canvasRect = elements.imageViewerCanvas.getBoundingClientRect();
    const focalX = focalClientX - (canvasRect.left + canvasRect.width / 2);
    const focalY = focalClientY - (canvasRect.top + canvasRect.height / 2);
    const scaleRatio = clampedScale / previousScale;
    viewerOffsetX = focalX - (focalX - viewerOffsetX) * scaleRatio;
    viewerOffsetY = focalY - (focalY - viewerOffsetY) * scaleRatio;
  }
  viewerScale = clampedScale;
  clampViewerOffsets();
  applyViewerTransform();
}

function resetViewerZoom() {
  viewerScale = VIEWER_MIN_SCALE;
  viewerOffsetX = 0;
  viewerOffsetY = 0;
  viewerPointers.clear();
  viewerGesture = null;
  viewerGestureDidPinch = false;
  applyViewerTransform();
}

function viewerPointDistance(first, second) {
  return Math.hypot(second.x - first.x, second.y - first.y);
}

function viewerPointMidpoint(first, second) {
  return { x: (first.x + second.x) / 2, y: (first.y + second.y) / 2 };
}

function viewerImageContainsPoint(clientX, clientY) {
  if (elements.imageViewerImage.classList.contains("hidden")) return false;
  const imageRect = elements.imageViewerImage.getBoundingClientRect();
  return clientX >= imageRect.left
    && clientX <= imageRect.right
    && clientY >= imageRect.top
    && clientY <= imageRect.bottom;
}

function beginViewerPinch() {
  const [first, second] = [...viewerPointers.values()];
  if (!first || !second) return;
  const midpoint = viewerPointMidpoint(first, second);
  const canvasRect = elements.imageViewerCanvas.getBoundingClientRect();
  viewerGesture = {
    type: "pinch",
    distance: Math.max(1, viewerPointDistance(first, second)),
    scale: viewerScale,
    offsetX: viewerOffsetX,
    offsetY: viewerOffsetY,
    focalX: midpoint.x - (canvasRect.left + canvasRect.width / 2),
    focalY: midpoint.y - (canvasRect.top + canvasRect.height / 2),
  };
  viewerGestureDidPinch = true;
}

function handleViewerPointerDown(event) {
  if (event.target.closest("button")) return;
  if (viewerPointers.size === 0) viewerGestureDidPinch = false;
  const point = {
    x: event.clientX,
    y: event.clientY,
    startX: event.clientX,
    startY: event.clientY,
    startedAt: performance.now(),
    pointerType: event.pointerType,
    startedOnImage: viewerImageContainsPoint(event.clientX, event.clientY),
  };
  viewerPointers.set(event.pointerId, point);
  elements.imageViewerCanvas.setPointerCapture(event.pointerId);
  if (viewerPointers.size === 1) {
    viewerGesture = {
      type: "drag",
      startX: event.clientX,
      startY: event.clientY,
      offsetX: viewerOffsetX,
      offsetY: viewerOffsetY,
    };
  } else if (viewerPointers.size === 2) {
    beginViewerPinch();
  }
  event.preventDefault();
}

function handleViewerPointerMove(event) {
  const point = viewerPointers.get(event.pointerId);
  if (!point) return;
  point.x = event.clientX;
  point.y = event.clientY;

  if (viewerPointers.size >= 2) {
    if (viewerGesture?.type !== "pinch") beginViewerPinch();
    const [first, second] = [...viewerPointers.values()];
    const midpoint = viewerPointMidpoint(first, second);
    const canvasRect = elements.imageViewerCanvas.getBoundingClientRect();
    const currentFocalX = midpoint.x - (canvasRect.left + canvasRect.width / 2);
    const currentFocalY = midpoint.y - (canvasRect.top + canvasRect.height / 2);
    const nextScale = clamp(
      viewerGesture.scale * viewerPointDistance(first, second) / viewerGesture.distance,
      VIEWER_MIN_SCALE,
      VIEWER_MAX_SCALE,
    );
    const scaleRatio = nextScale / viewerGesture.scale;
    viewerScale = nextScale;
    viewerOffsetX = currentFocalX - (viewerGesture.focalX - viewerGesture.offsetX) * scaleRatio;
    viewerOffsetY = currentFocalY - (viewerGesture.focalY - viewerGesture.offsetY) * scaleRatio;
    clampViewerOffsets();
    applyViewerTransform();
  } else if (viewerGesture?.type === "drag" && viewerScale > VIEWER_MIN_SCALE) {
    viewerOffsetX = viewerGesture.offsetX + event.clientX - viewerGesture.startX;
    viewerOffsetY = viewerGesture.offsetY + event.clientY - viewerGesture.startY;
    clampViewerOffsets();
    applyViewerTransform();
  }
  event.preventDefault();
}

function handleViewerPointerEnd(event) {
  const point = viewerPointers.get(event.pointerId);
  if (!point) return;
  viewerPointers.delete(event.pointerId);
  if (elements.imageViewerCanvas.hasPointerCapture(event.pointerId)) {
    elements.imageViewerCanvas.releasePointerCapture(event.pointerId);
  }

  if (viewerPointers.size === 1) {
    const remaining = [...viewerPointers.values()][0];
    viewerGesture = {
      type: "drag",
      startX: remaining.x,
      startY: remaining.y,
      offsetX: viewerOffsetX,
      offsetY: viewerOffsetY,
    };
  } else if (viewerPointers.size === 0) {
    const travel = Math.hypot(event.clientX - point.startX, event.clientY - point.startY);
    const isTap = point.pointerType === "touch"
      && !viewerGestureDidPinch
      && travel < 12
      && performance.now() - point.startedAt < 300;
    if (isTap && !point.startedOnImage && viewerScale === VIEWER_MIN_SCALE) {
      viewerLastTap = null;
      viewerGesture = null;
      event.preventDefault();
      closeImageViewer();
      return;
    }
    if (isTap && viewerLastTap
      && performance.now() - viewerLastTap.time < 320
      && Math.hypot(event.clientX - viewerLastTap.x, event.clientY - viewerLastTap.y) < 28) {
      setViewerZoom(
        viewerScale > VIEWER_MIN_SCALE ? VIEWER_MIN_SCALE : 2.5,
        event.clientX,
        event.clientY,
      );
      viewerLastTap = null;
    } else {
      viewerLastTap = isTap
        ? { time: performance.now(), x: event.clientX, y: event.clientY }
        : null;
    }
    viewerGesture = null;
  }
  event.preventDefault();
}

elements.imageViewerClose.addEventListener("click", closeImageViewer);
elements.imageViewerPrevious.addEventListener("click", () => navigateViewer(-1));
elements.imageViewerNext.addEventListener("click", () => navigateViewer(1));
elements.imageViewerLiveReplay.addEventListener("click", playViewerLive);
elements.imageViewerLiveReplay.addEventListener("mouseenter", playViewerLive);
elements.imageViewerZoomOut.addEventListener("click", () => {
  setViewerZoom(viewerScale - VIEWER_ZOOM_STEP);
});
elements.imageViewerZoomIn.addEventListener("click", () => {
  setViewerZoom(viewerScale + VIEWER_ZOOM_STEP);
});
elements.imageViewerZoomReset.addEventListener("click", resetViewerZoom);

elements.imageViewerCanvas.addEventListener("wheel", (event) => {
  event.preventDefault();
  const zoomFactor = Math.exp(-event.deltaY * 0.002);
  setViewerZoom(viewerScale * zoomFactor, event.clientX, event.clientY);
}, { passive: false });
elements.imageViewerCanvas.addEventListener("dblclick", (event) => {
  if (event.target !== elements.imageViewerImage) return;
  event.preventDefault();
  setViewerZoom(
    viewerScale > VIEWER_MIN_SCALE ? VIEWER_MIN_SCALE : 2.5,
    event.clientX,
    event.clientY,
  );
});
elements.imageViewerCanvas.addEventListener("click", (event) => {
  if (event.pointerType === "touch" || event.target.closest("button")) return;
  if (viewerScale === VIEWER_MIN_SCALE
    && !viewerImageContainsPoint(event.clientX, event.clientY)) {
    closeImageViewer();
  }
});
elements.imageViewerCanvas.addEventListener("pointerdown", handleViewerPointerDown);
elements.imageViewerCanvas.addEventListener("pointermove", handleViewerPointerMove);
elements.imageViewerCanvas.addEventListener("pointerup", handleViewerPointerEnd);
elements.imageViewerCanvas.addEventListener("pointercancel", handleViewerPointerEnd);

elements.imageViewer.addEventListener("cancel", (event) => {
  event.preventDefault();
  closeImageViewer();
});
elements.imageViewer.addEventListener("close", () => {
  ++viewerLoadToken;
  document.body.classList.remove("image-viewer-open");
  stopViewerLivePlayback(true);
  resetViewerZoom();
  viewerAssets = [];
  viewerIndex = -1;
  const returnFocus = viewerReturnFocus;
  viewerReturnFocus = null;
  if (returnFocus?.isConnected && !returnFocus.disabled) {
    returnFocus.focus({ preventScroll: true });
  }
});
elements.imageViewer.addEventListener("keydown", (event) => {
  const keyActions = {
    Escape: closeImageViewer,
    ArrowLeft: () => navigateViewer(-1),
    ArrowRight: () => navigateViewer(1),
    "+": () => setViewerZoom(viewerScale + VIEWER_ZOOM_STEP),
    "=": () => setViewerZoom(viewerScale + VIEWER_ZOOM_STEP),
    "-": () => setViewerZoom(viewerScale - VIEWER_ZOOM_STEP),
    "0": resetViewerZoom,
  };
  const action = keyActions[event.key];
  if (!action || event.altKey || event.ctrlKey || event.metaKey) return;
  event.preventDefault();
  action();
  if (["ArrowLeft", "ArrowRight"].includes(event.key) && imageViewerIsOpen()) {
    elements.imageViewer.focus({ preventScroll: true });
  }
});
window.addEventListener("resize", () => {
  if (!imageViewerIsOpen()) return;
  fitViewerImage();
  clampViewerOffsets();
  applyViewerTransform();
});

function renderVideoResult(result) {
  const media = result.media;
  const transcript = result.transcript || { text: "", detected_language: "", segments: [] };
  elements.editor.value = transcript.text;
  transcriptBaseline = elements.editor.value;
  const durationSeconds = media.duration ? Math.round(media.duration) : null;
  const detectedLanguage = displayLanguageName(transcript.detected_language);
  elements.videoOriginalTitle.textContent = media.title;
  elements.copyTitle.textContent = "复制标题";
  elements.videoCover.classList.toggle("hidden", !media.cover_url);
  if (media.cover_url) elements.videoCover.src = media.cover_url;
  else elements.videoCover.removeAttribute("src");
  elements.downloadCover.classList.toggle("hidden", !media.cover_url);
  elements.downloadTitle.classList.toggle("hidden", !media.title_url);
  if (media.cover_url) elements.downloadCover.href = media.cover_url;
  else elements.downloadCover.removeAttribute("href");
  if (media.title_url) elements.downloadTitle.href = media.title_url;
  else elements.downloadTitle.removeAttribute("href");
  elements.videoDetailsPath.textContent = [
    media.cover_path ? `封面：${media.cover_path}` : "",
    media.title_path ? `标题：${media.title_path}` : "",
  ].filter(Boolean).join("\n");
  elements.videoDetails.querySelector(".video-details-note").classList.toggle("hidden", !media.cover_url);

  const mediaFacts = document.createElement("span");
  mediaFacts.className = "result-media-facts";
  const filename = document.createElement("code");
  filename.className = "result-media-filename";
  filename.textContent = media.filename;
  filename.title = media.filename;
  filename.setAttribute("translate", "no");
  mediaFacts.append(filename);

  if (durationSeconds !== null) {
    const durationFact = document.createElement("span");
    durationFact.className = "result-media-fact";
    const durationLabel = document.createElement("span");
    durationLabel.className = "result-media-fact-label";
    durationLabel.textContent = "视频时长";
    const durationValue = document.createElement("span");
    durationValue.className = "result-media-fact-value";
    durationValue.textContent = `${durationSeconds} 秒`;
    durationFact.append(durationLabel, durationValue);
    mediaFacts.append(durationFact);
  }

  const languageFact = document.createElement("span");
  languageFact.className = "result-media-fact";
  const languageLabel = document.createElement("span");
  languageLabel.className = "result-media-fact-label";
  languageLabel.textContent = "识别语言";
  const languageValue = document.createElement("span");
  languageValue.className = "result-media-fact-value";
  languageValue.textContent = detectedLanguage;
  languageFact.append(languageLabel, languageValue);
  if (result.transcript) mediaFacts.append(languageFact);

  elements.mediaMeta.classList.add("video-meta");
  elements.mediaMeta.replaceChildren(mediaFacts);
  elements.timelineView.replaceChildren();
  elements.downloadTimeline.disabled = !transcript.segments.length;
  elements.downloadSrt.disabled = !transcript.segments.length;
  if (transcript.segments.length === 0) {
    const emptyTimeline = document.createElement("div");
    emptyTimeline.className = "timeline-empty";
    emptyTimeline.textContent = "没有可用的时间轴片段，请使用纯文本视图。";
    elements.timelineView.append(emptyTimeline);
  }
  transcript.segments.forEach((segment) => {
    const row = document.createElement("div");
    row.className = "timeline-row";
    const time = document.createElement("span");
    time.className = "timeline-time";
    time.textContent = `${formatTime(segment.start_ms)} → ${formatTime(segment.end_ms)}`;
    time.setAttribute("translate", "no");
    const text = document.createElement("span");
    text.textContent = segment.text;
    row.append(time, text);
    elements.timelineView.append(row);
  });
}

elements.editor.addEventListener("input", () => {
  transcriptDirty = Boolean(currentResult)
    && elements.editor.value !== transcriptBaseline;
  fitBatchEditor();
});

window.addEventListener("beforeunload", (event) => {
  if (!taskInProgress && !transcriptDirty) return;
  event.preventDefault();
  event.returnValue = "";
});

elements.viewTabs.forEach((button) => {
  button.addEventListener("click", () => {
    const emptySubtitle = currentResult?.media.kind === "video" && !currentResult.transcript?.text?.trim();
    selectView(emptySubtitle && button.dataset.view === "text" && selectedResultView === "text" ? null : button.dataset.view);
  });
  button.addEventListener("keydown", (event) => {
    const navigationKeys = ["ArrowRight", "ArrowDown", "ArrowLeft", "ArrowUp", "Home", "End"];
    if (!navigationKeys.includes(event.key)) return;
    const tabs = elements.viewTabs.filter((tab) => tab.getClientRects().length);
    const index = tabs.indexOf(button);
    let nextIndex = index;
    if (["ArrowRight", "ArrowDown"].includes(event.key)) nextIndex = (index + 1) % tabs.length;
    if (["ArrowLeft", "ArrowUp"].includes(event.key)) nextIndex = (index - 1 + tabs.length) % tabs.length;
    if (event.key === "Home") nextIndex = 0;
    if (event.key === "End") nextIndex = tabs.length - 1;
    event.preventDefault();
    const nextTab = tabs[nextIndex];
    selectView(nextTab.dataset.view);
    nextTab.focus();
  });
});

function selectView(view) {
  selectedResultView = view;
  elements.resultViewPanel.classList.toggle("hidden", view === null);
  elements.viewTabs.forEach((button) => {
    const selected = button.dataset.view === view;
    button.classList.toggle("active", selected);
    button.setAttribute("aria-selected", String(selected));
    button.tabIndex = selected || (view === null && button.dataset.view === "text") ? 0 : -1;
    if (selected) elements.resultViewPanel.setAttribute("aria-labelledby", button.id);
  });
  elements.textView.classList.toggle("hidden", !["text", "combined"].includes(view));
  elements.timelineView.classList.toggle("hidden", !["timeline", "combined"].includes(view));
  elements.summaryView.classList.toggle("hidden", view !== "summary");
}

function formatTime(milliseconds, srt = false) {
  const value = Math.max(0, Number(milliseconds) || 0);
  const hours = Math.floor(value / 3600000);
  const minutes = Math.floor((value % 3600000) / 60000);
  const seconds = Math.floor((value % 60000) / 1000);
  const millis = value % 1000;
  const separator = srt ? "," : ".";
  return `${String(hours).padStart(2, "0")}:${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}${separator}${String(millis).padStart(3, "0")}`;
}

function timelineText(transcript = currentResult?.transcript) {
  return (transcript?.segments || [])
    .map((segment) => `[${formatTime(segment.start_ms)} --> ${formatTime(segment.end_ms)}] ${segment.text}`)
    .join("\n");
}

function srtText(transcript = currentResult?.transcript) {
  return (transcript?.segments || [])
    .map((segment, index) => `${index + 1}\n${formatTime(segment.start_ms, true)} --> ${formatTime(segment.end_ms, true)}\n${segment.text}`)
    .join("\n\n") + "\n";
}

function createStoredZip(entries) {
  if (entries.length > 65535) throw new Error("文件过多，请分批导出");
  const encode = new TextEncoder();
  const table = Uint32Array.from({ length: 256 }, (_, index) => {
    let value = index;
    for (let bit = 0; bit < 8; bit++) value = value & 1 ? 0xedb88320 ^ (value >>> 1) : value >>> 1;
    return value >>> 0;
  });
  const records = [];
  const central = [];
  let offset = 0;
  const now = new Date();
  const date = ((now.getFullYear() - 1980) << 9) | ((now.getMonth() + 1) << 5) | now.getDate();
  const time = (now.getHours() << 11) | (now.getMinutes() << 5) | (now.getSeconds() >> 1);
  for (const entry of entries) {
    const name = encode.encode(entry.name);
    const data = typeof entry.data === "string" ? encode.encode(entry.data) : entry.data;
    if (offset + data.length + name.length + 30 > 0xffffffff) throw new Error("打包内容过大，请分批导出");
    let crc = 0xffffffff;
    for (const byte of data) crc = (crc >>> 8) ^ table[(crc ^ byte) & 255];
    crc = (crc ^ 0xffffffff) >>> 0;
    const header = new Uint8Array(30 + name.length);
    const view = new DataView(header.buffer);
    view.setUint32(0, 0x04034b50, true);
    view.setUint16(4, 20, true);
    view.setUint16(6, 0x0800, true);
    view.setUint16(10, time, true);
    view.setUint16(12, date, true);
    view.setUint32(14, crc, true);
    view.setUint32(18, data.length, true);
    view.setUint32(22, data.length, true);
    view.setUint16(26, name.length, true);
    header.set(name, 30);
    records.push(header, data);
    const directory = new Uint8Array(46 + name.length);
    const item = new DataView(directory.buffer);
    item.setUint32(0, 0x02014b50, true);
    item.setUint16(4, 20, true);
    item.setUint16(6, 20, true);
    item.setUint16(8, 0x0800, true);
    item.setUint16(12, time, true);
    item.setUint16(14, date, true);
    item.setUint32(16, crc, true);
    item.setUint32(20, data.length, true);
    item.setUint32(24, data.length, true);
    item.setUint16(28, name.length, true);
    item.setUint32(42, offset, true);
    directory.set(name, 46);
    central.push(directory);
    offset += header.length + data.length;
  }
  const centralSize = central.reduce((sum, record) => sum + record.length, 0);
  if (offset + centralSize + 22 > 0xffffffff) throw new Error("打包内容过大，请分批导出");
  const end = new Uint8Array(22);
  const view = new DataView(end.buffer);
  view.setUint32(0, 0x06054b50, true);
  view.setUint16(8, entries.length, true);
  view.setUint16(10, entries.length, true);
  view.setUint32(12, centralSize, true);
  view.setUint32(16, offset, true);
  return new Blob([...records, ...central, end], { type: "application/zip" });
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function titleFolderName(title, used) {
  let base = String(title || "未命名作品").normalize("NFC")
    .replace(/[\\/:*?"<>|\u0000-\u001f\u007f]/g, "_").replace(/[. ]+$/g, "").trim();
  if (!base || /^\.+$/.test(base)) base = "未命名作品";
  if (/^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?$/i.test(base)) base = `_${base}`;
  const encoder = new TextEncoder();
  let clipped = "";
  for (const character of base) {
    if (encoder.encode(clipped + character).length > 220) break;
    clipped += character;
  }
  base = clipped.replace(/[. ]+$/g, "") || "未命名作品";
  let folder = base;
  let suffix = 2;
  while (used.has(folder.toLocaleLowerCase())) folder = `${base}_${suffix++}`;
  used.add(folder.toLocaleLowerCase());
  return folder;
}

elements.batchDownload.addEventListener("click", async () => {
  if (!currentBatch || queueArchiveBusy || !selectedQueueJobs.size) return;
  const chosen = currentBatch.jobs.filter((job) => selectedQueueJobs.has(job.id) && canSelectQueueItem(job));
  if (!chosen.length) return;
  queueArchiveBusy = true;
  syncQueueSelection();
  elements.batchDownload.textContent = "正在打包…";
  const snapshot = { ...currentBatch, jobs: chosen, total: chosen.length, completed: chosen.length,
    failed: 0, running: 0, queued: 0, progress: 100, duplicate_count: 0 };
  const missing = [];
  try {
    const entries = [];
    const folders = new Set();
    for (const item of snapshot.jobs) {
      if (item.status !== "completed" || !item.result_available) continue;
      const job = await loadBatchResult(item.id);
      if (!job.result) {
        missing.push({ job_id: item.id, file: "任务结果", reason: "结果不可用" });
        continue;
      }
      const result = job.result;
      const folder = titleFolderName(result.media.title, folders);
      const add = (name, data) => entries.push({ name: `${folder}/${name}`, data });
      add("标题.txt", result.media.title);
      add("元数据.json", JSON.stringify(job, null, 2));
      if (result.media.description) add(result.transcript ? "作品文案.txt" : "文案.txt", result.media.description);
      if (result.transcript) {
        add("文案.txt", result.transcript.text);
        if (result.transcript.segments?.length) {
          add("时间轴.txt", timelineText(result.transcript));
          add("字幕.srt", srtText(result.transcript));
        }
      }
      if (result.media.cover_url) {
        try {
          const response = await fetch(result.media.cover_url);
          if (!response.ok) throw new Error(`封面读取失败 (${response.status})`);
          const extension = result.media.cover_path?.match(/\.(jpg|jpeg|png|webp|avif|gif)$/i)?.[1]?.toLowerCase() || "jpg";
          add(`封面.${extension}`, new Uint8Array(await response.arrayBuffer()));
        } catch (error) {
          missing.push({ job_id: item.id, file: "封面.jpg", reason: error.message });
        }
      }
    }
    entries.push({ name: "处理队列清单.json", data: JSON.stringify({ ...snapshot, missing_files: missing }, null, 2) });
    entries.push({ name: "说明.txt", data: "仅包含本次选中任务的原始逐字稿、时间轴、字幕、标题、封面与元数据，文件夹按作品发布标题命名，同名添加后缀。\n视频原文件不包含在压缩包中。文案为原始提取结果。\n" });
    downloadBlob(createStoredZip(entries), `处理队列_${new Date().toISOString().slice(0, 10)}.zip`);
  } catch (error) {
    elements.queueFeedback.textContent = `打包失败：${error.message}`;
  } finally {
    queueArchiveBusy = false;
    elements.batchDownload.textContent = "打包文案与封面";
    syncQueueSelection();
  }
});

function download(content, suffix, mime = "text/plain;charset=utf-8") {
  const url = URL.createObjectURL(new Blob([content], { type: mime }));
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = suffix;
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

elements.copyTitle.addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(currentResult?.media?.title || "");
    elements.copyTitle.textContent = "标题已复制";
  } catch {
    elements.copyTitle.textContent = "复制失败，请选择标题复制";
  }
});

elements.copyText.addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(elements.editor.value);
    clearTimeout(copyFeedbackTimer);
    elements.copyText.classList.add("copy-success");
    elements.copyText.setAttribute("aria-label", "文案已复制");
    elements.copyLabel.textContent = "已复制";
    transcriptBaseline = elements.editor.value;
    transcriptDirty = false;
    copyFeedbackTimer = setTimeout(() => {
      elements.copyText.classList.remove("copy-success");
      elements.copyText.setAttribute("aria-label", "复制文案");
      elements.copyLabel.textContent = "复制文案";
    }, 1500);
  } catch (error) {
    elements.copyLabel.textContent = "复制失败";
    elements.copyText.setAttribute("aria-label", "复制失败，请手动选择文案复制");
    setTimeout(() => {
      elements.copyText.setAttribute("aria-label", "复制文案");
      elements.copyLabel.textContent = "复制文案";
    }, 1500);
  }
});
elements.downloadText.addEventListener("click", () => {
  download(elements.editor.value, "文案.txt");
  transcriptBaseline = elements.editor.value;
  transcriptDirty = false;
});
elements.downloadTimeline.addEventListener("click", () => download(timelineText(), "时间轴.txt"));
elements.downloadSrt.addEventListener("click", () => download(srtText(), "字幕.srt", "application/x-subrip;charset=utf-8"));

function readStorage(key) {
  try {
    return window.localStorage.getItem(key);
  } catch (_error) {
    return null;
  }
}

function writeStorage(key, value) {
  try {
    window.localStorage.setItem(key, value);
  } catch (_error) {
    // localStorage 不可用(如隐私模式)时静默降级为会话内状态。
  }
}

function removeStorage(key) {
  try {
    window.localStorage.removeItem(key);
  } catch (_error) {
    // 同上,忽略存储异常。
  }
}

function updateSummaryServiceUi() {
  const { configured, base_url: baseUrl, model } = summaryServiceStatus;
  elements.summaryService.className = `auth-state ${configured ? "" : "has-error"}`;
  elements.summaryServiceLabel.textContent = configured ? "已配置" : "未配置";
  elements.summaryHint.textContent = configured
    ? `使用 ${model} 生成总结时，文案将发送至该服务。`
    : "配置 OpenAI 兼容接口后，可在结果页生成视频内容总结。";
  elements.summaryConfigOpen.textContent = configured ? "修改 LLM 配置" : "配置 LLM 接口";
  elements.summaryConfigOpen.classList.toggle("is-ready-action", configured);
}

async function refreshSummaryServiceStatus() {
  try {
    const status = await api("/api/summary/config");
    summaryServiceStatus = {
      configured: Boolean(status.configured),
      base_url: status.base_url || "",
      model: status.model || "",
    };
  } catch (_error) {
    summaryServiceStatus = { configured: false, base_url: "", model: "" };
  }
  updateSummaryServiceUi();
}

async function migrateLegacySummaryConfig() {
  let legacy = null;
  try {
    legacy = JSON.parse(readStorage(SUMMARY_CONFIG_KEY));
  } catch (_error) {
    legacy = null;
  }
  if (!legacy?.base_url || !legacy?.api_key || !legacy?.model) return;
  try {
    await api("/api/summary/config", {
      method: "PUT",
      body: JSON.stringify({
        base_url: legacy.base_url,
        api_key: legacy.api_key,
        model: legacy.model,
      }),
    });
    removeStorage(SUMMARY_CONFIG_KEY);
  } catch (_error) {
    // 迁移失败时保留本地配置，下次启动再试。
  }
}

function setSummaryConfigError(message = "") {
  elements.summaryConfigError.textContent = message;
  elements.summaryConfigError.classList.toggle("hidden", !message);
}

function closeSummaryModelList(restoreFocus = false) {
  elements.summaryConfigModelList.classList.add("hidden");
  elements.summaryConfigModelTrigger.setAttribute("aria-expanded", "false");
  if (restoreFocus) elements.summaryConfigModelTrigger.focus();
}

function renderSummaryModelControl() {
  const selectedValue = elements.summaryConfigModel.value;
  const selectedOption = elements.summaryConfigModel.selectedOptions[0];
  elements.summaryConfigModelValue.textContent = selectedOption?.textContent || "请先获取模型";
  elements.summaryConfigModelTrigger.disabled = elements.summaryConfigModel.disabled;
  elements.summaryConfigModelList.replaceChildren();

  [...elements.summaryConfigModel.options].forEach((model) => {
    if (!model.value) return;
    const option = document.createElement("button");
    option.type = "button";
    option.className = "summary-model-option";
    option.setAttribute("role", "option");
    option.dataset.value = model.value;
    option.setAttribute("aria-selected", String(model.value === selectedValue));
    const check = document.createElement("span");
    check.className = "summary-model-option-check";
    check.setAttribute("aria-hidden", "true");
    check.textContent = "✓";
    const name = document.createElement("span");
    name.className = "summary-model-option-name";
    name.textContent = model.textContent;
    option.append(check, name);
    option.addEventListener("click", () => {
      elements.summaryConfigModel.value = model.value;
      renderSummaryModelControl();
      closeSummaryModelList(true);
    });
    elements.summaryConfigModelList.append(option);
  });

  if (elements.summaryConfigModel.disabled) closeSummaryModelList();
}

function openSummaryModelList(focusPosition = "selected") {
  if (elements.summaryConfigModelTrigger.disabled) return;
  const options = [...elements.summaryConfigModelList.querySelectorAll(".summary-model-option")];
  if (!options.length) return;
  elements.summaryConfigModelList.classList.remove("hidden");
  elements.summaryConfigModelTrigger.setAttribute("aria-expanded", "true");
  const target = focusPosition === "last"
    ? options.at(-1)
    : options.find((option) => option.getAttribute("aria-selected") === "true") || options[0];
  target.focus();
}

function setSummaryModelOptions(models, selectedModel = "") {
  const uniqueModels = [...new Set(models.filter((model) => typeof model === "string" && model.trim()))]
    .sort((left, right) => left.localeCompare(right, undefined, { numeric: true }));
  elements.summaryConfigModel.replaceChildren();
  if (selectedModel && !uniqueModels.includes(selectedModel)) uniqueModels.unshift(selectedModel);
  if (!uniqueModels.length) {
    const option = document.createElement("option");
    option.value = "";
    option.textContent = "暂无可用模型";
    elements.summaryConfigModel.append(option);
    elements.summaryConfigModel.disabled = true;
    renderSummaryModelControl();
    return;
  }
  uniqueModels.forEach((model) => {
    const option = document.createElement("option");
    option.value = model;
    option.textContent = model;
    elements.summaryConfigModel.append(option);
  });
  elements.summaryConfigModel.value = selectedModel && uniqueModels.includes(selectedModel)
    ? selectedModel
    : uniqueModels[0];
  elements.summaryConfigModel.disabled = false;
  renderSummaryModelControl();
}

function setModelStatus(text, state = "idle") {
  elements.summaryConfigModelStatusText.textContent = text;
  elements.summaryConfigModelStatus.dataset.state = state;
  elements.summaryConfigModelStatus.classList.toggle("has-error", state === "error");
}

async function loadSummaryModels(selectedModel = "") {
  const baseUrl = elements.summaryConfigBase.value.trim().replace(/\/+$/, "");
  const apiKey = elements.summaryConfigKey.value.trim();
  summaryModelsController?.abort();
  summaryModelsController = null;
  const canUseSavedKey = !apiKey && summaryServiceStatus.configured;
  if (!/^https?:\/\/.+/.test(baseUrl) || (!apiKey && !canUseSavedKey)) {
    setSummaryModelOptions(selectedModel ? [selectedModel] : [], selectedModel);
    setModelStatus("填写接口地址和 API Key 后，将自动获取可用模型。", "idle");
    return;
  }

  const controller = new AbortController();
  summaryModelsController = controller;
  elements.summaryConfigModel.disabled = true;
  elements.summaryConfigModel.setAttribute("aria-busy", "true");
  elements.summaryConfigModelTrigger.setAttribute("aria-busy", "true");
  renderSummaryModelControl();
  setModelStatus("正在获取可用模型…", "busy");
  try {
    const body = await api("/api/summary/models", {
      method: "POST",
      body: JSON.stringify({ base_url: baseUrl, api_key: apiKey }),
      signal: controller.signal,
    });
    const models = Array.isArray(body.models) ? body.models : [];
    if (!models.length) {
      throw new Error("接口未返回模型列表");
    }
    setSummaryModelOptions(models, selectedModel);
    setModelStatus(`已获取 ${elements.summaryConfigModel.options.length} 个模型。`, "ok");
  } catch (error) {
    if (error.name === "AbortError") return;
    setSummaryModelOptions(selectedModel ? [selectedModel] : [], selectedModel);
    setModelStatus(
      selectedModel
        ? `模型列表获取失败，已保留当前模型。${error.message}`
        : `模型列表获取失败：${error.message}`,
      "error",
    );
  } finally {
    if (summaryModelsController === controller) summaryModelsController = null;
    elements.summaryConfigModel.removeAttribute("aria-busy");
    elements.summaryConfigModelTrigger.removeAttribute("aria-busy");
    renderSummaryModelControl();
  }
}

function openSummaryConfigDialog() {
  const { configured, base_url: baseUrl, model } = summaryServiceStatus;
  elements.summaryConfigBase.value = baseUrl || "";
  elements.summaryConfigKey.value = "";
  elements.summaryConfigKey.placeholder = configured ? "已保存，留空则保留原 Key" : "sk-...";
  elements.summaryConfigKey.type = "password";
  elements.summaryConfigKeyToggle.textContent = "显示";
  elements.summaryConfigKeyToggle.setAttribute("aria-pressed", "false");
  elements.summaryConfigKeyToggle.setAttribute("aria-label", "显示 API Key");
  setSummaryModelOptions(model ? [model] : [], model || "");
  setSummaryConfigError();
  elements.summaryConfigDialog.showModal();
  elements.summaryConfigBase.focus();
  loadSummaryModels(model || "");
}

elements.summaryConfigOpen.addEventListener("click", openSummaryConfigDialog);
elements.summaryPresets.forEach((button) => {
  button.addEventListener("click", () => {
    elements.summaryConfigBase.value = button.dataset.baseUrl;
    setSummaryConfigError();
    if (elements.summaryConfigKey.value.trim()) {
      loadSummaryModels(elements.summaryConfigModel.value);
    } else {
      elements.summaryConfigKey.focus();
      loadSummaryModels();
    }
  });
});
elements.summaryConfigKeyToggle.addEventListener("click", () => {
  const show = elements.summaryConfigKey.type === "password";
  elements.summaryConfigKey.type = show ? "text" : "password";
  elements.summaryConfigKeyToggle.textContent = show ? "隐藏" : "显示";
  elements.summaryConfigKeyToggle.setAttribute("aria-pressed", String(show));
  elements.summaryConfigKeyToggle.setAttribute("aria-label", show ? "隐藏 API Key" : "显示 API Key");
  elements.summaryConfigKey.focus();
});
elements.summaryConfigBase.addEventListener("blur", () => loadSummaryModels());
elements.summaryConfigKey.addEventListener("blur", () => loadSummaryModels(elements.summaryConfigModel.value));
elements.summaryConfigClose.addEventListener("click", () => {
  summaryModelsController?.abort();
  closeSummaryModelList();
  elements.summaryConfigDialog.close();
});
elements.summaryConfigModelTrigger.addEventListener("click", () => {
  if (elements.summaryConfigModelTrigger.getAttribute("aria-expanded") === "true") {
    closeSummaryModelList();
  } else {
    openSummaryModelList();
  }
});
elements.summaryConfigModelTrigger.addEventListener("keydown", (event) => {
  if (!["ArrowDown", "ArrowUp"].includes(event.key)) return;
  event.preventDefault();
  openSummaryModelList(event.key === "ArrowUp" ? "last" : "selected");
});
elements.summaryConfigModelList.addEventListener("keydown", (event) => {
  const options = [...elements.summaryConfigModelList.querySelectorAll(".summary-model-option")];
  const currentIndex = options.indexOf(document.activeElement);
  let nextIndex = currentIndex;
  if (event.key === "ArrowDown") nextIndex = Math.min(options.length - 1, currentIndex + 1);
  else if (event.key === "ArrowUp") nextIndex = Math.max(0, currentIndex - 1);
  else if (event.key === "Home") nextIndex = 0;
  else if (event.key === "End") nextIndex = options.length - 1;
  else if (event.key === "Escape") {
    event.preventDefault();
    closeSummaryModelList(true);
    return;
  } else if (event.key === "Tab") {
    closeSummaryModelList();
    return;
  } else return;
  event.preventDefault();
  options[nextIndex]?.focus();
});
document.addEventListener("click", (event) => {
  if (!elements.summaryConfigModelTrigger.contains(event.target)
    && !elements.summaryConfigModelList.contains(event.target)) {
    closeSummaryModelList();
  }
});
elements.summaryConfigForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const baseUrl = elements.summaryConfigBase.value.trim().replace(/\/+$/, "");
  const apiKey = elements.summaryConfigKey.value.trim();
  const model = elements.summaryConfigModel.value.trim();
  if (!/^https?:\/\/.+/.test(baseUrl)) {
    setSummaryConfigError("请输入以 http:// 或 https:// 开头的接口地址。");
    elements.summaryConfigBase.focus();
    return;
  }
  if (!apiKey && !summaryServiceStatus.configured) {
    setSummaryConfigError("请输入 API Key。");
    elements.summaryConfigKey.focus();
    return;
  }
  if (!model) {
    setSummaryConfigError("请选择模型。");
    elements.summaryConfigModelTrigger.focus();
    return;
  }
  const saveButton = elements.summaryConfigSave;
  saveButton.disabled = true;
  try {
    await api("/api/summary/config", {
      method: "PUT",
      body: JSON.stringify({ base_url: baseUrl, api_key: apiKey, model }),
    });
    await refreshSummaryServiceStatus();
    setSummaryConfigError();
    elements.summaryConfigDialog.close();
  } catch (error) {
    setSummaryConfigError(error.message || "保存失败，请稍后重试。");
  } finally {
    saveButton.disabled = false;
  }
});
elements.summaryConfigClear.addEventListener("click", async () => {
  elements.summaryConfigClear.disabled = true;
  try {
    await api("/api/summary/config", { method: "DELETE" });
    await refreshSummaryServiceStatus();
    elements.summaryConfigDialog.close();
  } catch (error) {
    setSummaryConfigError(error.message || "清除失败，请稍后重试。");
  } finally {
    elements.summaryConfigClear.disabled = false;
  }
});

function updateAutoSummaryUi() {
  elements.autoSummaryToggle.setAttribute("aria-checked", String(autoSummary));
}

elements.autoSummaryToggle.addEventListener("click", async () => {
  if (!autoSummary) {
    if (!summaryServiceStatus.configured) { openSummaryConfigDialog(); return; }
    if (!await confirmCardRegeneration("automatic") || !extractTxt) return;
  }
  autoSummary = !autoSummary;
  updateAutoSummaryUi();
});

function setSummaryState(state) {
  summaryStatus = state;
  updateCardCompletionBadges(currentJobId);
  elements.summaryEmpty.classList.toggle("hidden", state !== "empty");
  elements.summaryProgress.classList.toggle("hidden", state !== "busy");
  elements.summaryResult.classList.toggle("hidden", state !== "done");
  elements.summaryError.classList.toggle("hidden", state !== "error");
  elements.summaryCancel.classList.toggle("hidden", state === "busy" && !summaryAbortController);
  updateResultContentActions(currentJobId);
}

function resetSummary() {
  summaryAbortController?.abort();
  summaryAbortController = null;
  summaryData = null;
  setSummaryState("empty");
}

function appendInlineMarkdown(parent, source) {
  const tokenPattern = /(`[^`]+`|\*\*[^*]+\*\*|__[^_]+__|\*[^*]+\*|_[^_]+_|\[[^\]]+\]\([^)]+\))/g;
  let offset = 0;
  for (const match of source.matchAll(tokenPattern)) {
    parent.append(document.createTextNode(source.slice(offset, match.index)));
    const token = match[0];
    let element;
    if (token.startsWith("`")) {
      element = document.createElement("code");
      element.textContent = token.slice(1, -1);
    } else if (token.startsWith("**") || token.startsWith("__")) {
      element = document.createElement("strong");
      element.textContent = token.slice(2, -2);
    } else if (token.startsWith("[") && token.includes("](")) {
      const separator = token.indexOf("](");
      const href = token.slice(separator + 2, -1).trim();
      if (/^https?:\/\//i.test(href)) {
        element = document.createElement("a");
        element.href = href;
        element.target = "_blank";
        element.rel = "noopener noreferrer";
        element.textContent = token.slice(1, separator);
      }
    } else {
      element = document.createElement("em");
      element.textContent = token.slice(1, -1);
    }
    parent.append(element || document.createTextNode(token));
    offset = (match.index || 0) + token.length;
  }
  parent.append(document.createTextNode(source.slice(offset)));
}

function renderMarkdown(markdown, container) {
  container.replaceChildren();
  const fragment = document.createDocumentFragment();
  const lines = String(markdown || "").replace(/\r\n?/g, "\n").split("\n");
  let list = null;
  let paragraph = null;
  let code = null;

  const closeBlocks = () => {
    list = null;
    paragraph = null;
  };
  const appendTextBlock = (tagName, text, className = "") => {
    const node = document.createElement(tagName);
    if (className) node.className = className;
    appendInlineMarkdown(node, text);
    fragment.append(node);
    return node;
  };

  for (const line of lines) {
    const fence = line.match(/^\s*```(?:\w+)?\s*$/);
    if (fence) {
      closeBlocks();
      if (code) {
        code = null;
      } else {
        const pre = document.createElement("pre");
        code = document.createElement("code");
        pre.append(code);
        fragment.append(pre);
      }
      continue;
    }
    if (code) {
      code.textContent += `${code.textContent ? "\n" : ""}${line}`;
      continue;
    }
    if (!line.trim()) {
      closeBlocks();
      continue;
    }
    const heading = line.match(/^(#{1,6})\s+(.+)$/);
    if (heading) {
      closeBlocks();
      appendTextBlock(`h${heading[1].length}`, heading[2]);
      continue;
    }
    if (/^\s*(?:---+|___+|\*\*\*+)\s*$/.test(line)) {
      closeBlocks();
      fragment.append(document.createElement("hr"));
      continue;
    }
    const quote = line.match(/^>\s?(.*)$/);
    if (quote) {
      closeBlocks();
      appendTextBlock("blockquote", quote[1]);
      continue;
    }
    const unordered = line.match(/^\s*[-+*]\s+(.+)$/);
    const ordered = line.match(/^\s*\d+[.)]\s+(.+)$/);
    if (unordered || ordered) {
      paragraph = null;
      const tagName = ordered ? "OL" : "UL";
      if (!list || list.tagName !== tagName) {
        list = document.createElement(tagName.toLowerCase());
        fragment.append(list);
      }
      const item = document.createElement("li");
      appendInlineMarkdown(item, (unordered || ordered)[1]);
      list.append(item);
      continue;
    }
    list = null;
    if (!paragraph) paragraph = appendTextBlock("p", line);
    else {
      paragraph.append(document.createTextNode(" "));
      appendInlineMarkdown(paragraph, line);
    }
  }
  container.append(fragment);
}

function renderSummary() {
  renderMarkdown(summaryData.markdown, elements.summaryMarkdown);
  const now = summaryData.generatedAt ? new Date(summaryData.generatedAt) : new Date();
  const timeText = `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`;
  elements.summaryMeta.textContent =
    `生成于 ${timeText} · ${summaryData.model || "未知模型"}`;
}

async function startSummaryGeneration() {
  if (!currentResult?.media || !currentJobId) return;
  if (!summaryServiceStatus.configured) {
    openSummaryConfigDialog();
    return;
  }
  if (!elements.editor.value.trim()) {
    elements.summaryErrorText.textContent = "没有可用的转写文案，无法生成总结。";
    setSummaryState("error");
    return;
  }
  if (summaryStatus === "busy" || batchResults.get(currentJobId)?.status === "running") return;
  const requestedJobId = currentJobId;
  if (!await confirmCardRegeneration(cardSummaries.has(currentJobId) ? "summary" : "summary_initial")) return;
  if (currentJobId !== requestedJobId || summaryStatus === "busy") return;
  selectView("summary");
  summaryAbortController?.abort();
  const controller = new AbortController();
  const jobId = currentJobId;
  const sourceText = elements.editor.value;
  summaryAbortController = controller;
  setSummaryState("busy");
  try {
    const payload = await api(`/api/jobs/${jobId}/summary`, {
      method: "POST",
      body: JSON.stringify({ style: "brief", transcript_text: sourceText }),
      signal: controller.signal,
    });
    if (summaryAbortController !== controller || currentJobId !== jobId) return;
    summaryData = {
      markdown: payload.markdown || "",
      model: payload.model || "",
      sourceText,
      generatedAt: payload.generated_at || new Date().toISOString(),
    };
    cardSummaries.set(jobId, summaryData);
    const detail = batchResults.get(jobId);
    if (detail) {
      detail.summary = { markdown: summaryData.markdown, model: summaryData.model,
        source_text: sourceText, style: payload.style || "brief", generated_at: summaryData.generatedAt };
      detail.summary_state = "completed";
    }
    updateCardCompletionBadges(jobId);
    renderSummary();
    setSummaryState("done");
  } catch (error) {
    if (error.name === "AbortError") return;
    elements.summaryErrorText.textContent = error.message || "生成失败，请稍后重试。";
    setSummaryState("error");
  } finally {
    if (summaryAbortController === controller) summaryAbortController = null;
  }
}

elements.summaryGenerate.addEventListener("click", startSummaryGeneration);
elements.summaryRegenerate.addEventListener("click", startSummaryGeneration);
elements.summaryRetry.addEventListener("click", startSummaryGeneration);
elements.summaryCancel.addEventListener("click", () => {
  summaryAbortController?.abort();
  summaryAbortController = null;
  setSummaryState(summaryData ? "done" : "empty");
});

elements.summaryCopy.addEventListener("click", async () => {
  if (!summaryData) return;
  try {
    await navigator.clipboard.writeText(summaryData.markdown);
    clearTimeout(summaryCopyTimer);
    elements.summaryCopy.classList.add("copy-success");
    elements.summaryCopy.setAttribute("aria-label", "总结已复制");
    elements.summaryCopyLabel.textContent = "已复制";
    summaryCopyTimer = setTimeout(() => {
      elements.summaryCopy.classList.remove("copy-success");
      elements.summaryCopy.setAttribute("aria-label", "复制总结");
      elements.summaryCopyLabel.textContent = "复制总结";
    }, 1500);
  } catch (_error) {
    elements.summaryCopyLabel.textContent = "复制失败";
    setTimeout(() => {
      elements.summaryCopyLabel.textContent = "复制总结";
    }, 1500);
  }
});

elements.summaryDownload.addEventListener("click", () => {
  if (!summaryData) return;
  download(summaryData.markdown, "AI总结.md", "text/markdown;charset=utf-8");
});

autoSummary = false;
updateAutoSummaryUi();
updateSummaryServiceUi();

(async () => {
  await migrateLegacySummaryConfig();
  await refreshSummaryServiceStatus();
})();

window.addEventListener("feishu-jobs", (event) => {
  const sources = event.detail?.sources;
  if (!Array.isArray(sources)) return;
  const fresh = sources.filter((source) => source.type === "single"
    && /^[a-f0-9]{32}$/.test(source.id) && !deletedQueueJobs.has(source.id)
    && !queueSources.some((existing) => existing.id === source.id));
  if (fresh.length) {
    queueSources.unshift(...fresh);
    batchPage = 1;
    rememberQueue();
    void refreshProcessingQueue();
  }
});

loadSystem();
void loadMaterialTags();

try {
  const deleted = JSON.parse(readStorage(QUEUE_DELETED_KEY) || "[]");
  if (Array.isArray(deleted)) for (const id of deleted) {
    if (typeof id === "string" && /^[a-f0-9]{32}$/.test(id)) deletedQueueJobs.add(id);
  }
} catch (_error) { /* Invalid local deletion history must not prevent loading. */ }

try {
  const saved = JSON.parse(readStorage(PROCESSING_QUEUE_KEY) || "[]");
  if (Array.isArray(saved)) {
    for (const source of saved) {
      if (["single", "batch"].includes(source.type) && /^[a-f0-9]{32}$/.test(source.id)
        && !queueSources.some((item) => item.id === source.id)) {
        queueSources.push(source);
        if (/^[a-f0-9]{32}$/.test(source.retry_of || "")) deletedQueueJobs.add(source.retry_of);
      }
    }
  }
} catch (_error) { /* Recover the previous batch below if history cannot be read. */ }
const legacyBatch = readStorage(BATCH_STORAGE_KEY);
if (legacyBatch && /^[a-f0-9]{32}$/.test(legacyBatch)
  && !queueSources.some((source) => source.id === legacyBatch)) {
  queueSources.push({ type: "batch", id: legacyBatch });
}
if (queueSources.length) {
  rememberQueue();
  setInputMode(queueSources[0].type === "batch" ? "batch" : "single");
  void refreshProcessingQueue();
}
