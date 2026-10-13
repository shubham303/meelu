const { contextBridge, ipcRenderer } = require("electron");

const bridge = {
  runTurn: (payload) => ipcRenderer.invoke("agent:turn", payload),
  onEvent: (callback) => {
    const listener = (_event, message) => callback(message);
    ipcRenderer.on("agent:event", listener);
    return () => ipcRenderer.removeListener("agent:event", listener);
  },
  crawlSite: (payload) => ipcRenderer.invoke("site:crawl", payload),
  stopCrawl: (jobId) => ipcRenderer.invoke("site:crawlStop", { jobId }),
  searchSync: (payload) => ipcRenderer.invoke("site:searchSync", payload),
  stopSearchSync: (payload) => ipcRenderer.invoke("site:searchSyncStop", payload),
  indexCheck: (payload) => ipcRenderer.invoke("site:indexCheck", payload),
  contentChecks: () => ipcRenderer.invoke("content:checks"),
  checkContent: (payload) => ipcRenderer.invoke("content:check", payload),
  inspectPageUrl: (payload) => ipcRenderer.invoke("site:inspectUrl", payload),
  gscProperties: (domain) => ipcRenderer.invoke("site:gscProperties", { domain }),
  trafficSync: (payload) => ipcRenderer.invoke("site:trafficSync", payload),
  stopTrafficSync: (payload) => ipcRenderer.invoke("site:trafficSyncStop", payload),
  gaProperties: () => ipcRenderer.invoke("site:gaProperties"),
  describeSite: (siteId) => ipcRenderer.invoke("site:describe", { siteId }),
  onSiteSummaryEvent: (callback) => {
    const listener = (_event, message) => callback(message);
    ipcRenderer.on("site-summary:event", listener);
    return () => ipcRenderer.removeListener("site-summary:event", listener);
  },
  crawlToken: (domain) => ipcRenderer.invoke("site:crawlToken", { domain }),
  onCrawlEvent: (callback) => {
    const listener = (_event, message) => callback(message);
    ipcRenderer.on("crawl:event", listener);
    return () => ipcRenderer.removeListener("crawl:event", listener);
  },
  renderSite: (payload) => ipcRenderer.invoke("site:render", payload),
  stopRender: (jobId) => ipcRenderer.invoke("site:renderStop", { jobId }),
  onRenderEvent: (callback) => {
    const listener = (_event, message) => callback(message);
    ipcRenderer.on("render:event", listener);
    return () => ipcRenderer.removeListener("render:event", listener);
  },
  abort: (turnId) => ipcRenderer.invoke("agent:abort", turnId),
  sessionUsage: () => ipcRenderer.invoke("usage:session"),
  appUpdate: () => ipcRenderer.invoke("app:update"),
  downloadUpdate: () => ipcRenderer.invoke("app:downloadUpdate"),
  onAppUpdate: (callback) => {
    const listener = (_event, update) => callback(update);
    ipcRenderer.on("app:update-event", listener);
    return () => ipcRenderer.removeListener("app:update-event", listener);
  },
  respondPermission: (requestId, decision) =>
    ipcRenderer.invoke("agent:permission", { requestId, decision }),
  getLlmConfig: () => ipcRenderer.invoke("llm:get"),
  setLlmConfig: (cfg) => ipcRenderer.invoke("llm:set", cfg),
  getConnectors: () => ipcRenderer.invoke("connectors:list"),
  removeConnector: (provider) => ipcRenderer.invoke("connectors:remove", provider),
  connectGsc: () => ipcRenderer.invoke("connectors:connectGsc"),
  connectGa4: () => ipcRenderer.invoke("connectors:connectGa4"),
  socialSignalsSearch: (payload) => ipcRenderer.invoke("social-signals:search", payload),
  socialSignalsStop: (jobId) => ipcRenderer.invoke("social-signals:stop", { jobId }),
  socialSignalsActive: (siteId) => ipcRenderer.invoke("social-signals:active", { siteId }),
  socialSignalsPlatforms: () => ipcRenderer.invoke("social-signals:platforms"),
  onSocialSignalsEvent: (callback) => {
    const listener = (_event, message) => callback(message);
    ipcRenderer.on("social-signals:event", listener);
    return () => ipcRenderer.removeListener("social-signals:event", listener);
  },
  saveTextFile: (params) => ipcRenderer.invoke("files:saveText", params),
};

contextBridge.exposeInMainWorld("meeluAgent", bridge);
contextBridge.exposeInMainWorld("meelu", bridge);

if (process.argv.includes("--meelu-dev-annotator")) {
  contextBridge.exposeInMainWorld("meeluAnnotator", {
    capture: (payload) => ipcRenderer.invoke("annotator:capture", payload),
  });
}
