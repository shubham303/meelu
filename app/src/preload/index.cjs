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
  stopSearchSync: (syncId) => ipcRenderer.invoke("site:searchSyncStop", { syncId }),
  indexCheck: (payload) => ipcRenderer.invoke("site:indexCheck", payload),
  contentChecks: () => ipcRenderer.invoke("content:checks"),
  checkContent: (payload) => ipcRenderer.invoke("content:check", payload),
  inspectPageUrl: (payload) => ipcRenderer.invoke("site:inspectUrl", payload),
  gscProperties: (domain) => ipcRenderer.invoke("site:gscProperties", { domain }),
  trafficSync: (payload) => ipcRenderer.invoke("site:trafficSync", payload),
  stopTrafficSync: (syncId) => ipcRenderer.invoke("site:trafficSyncStop", { syncId }),
  gaProperties: () => ipcRenderer.invoke("site:gaProperties"),
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
  respondPermission: (requestId, decision) =>
    ipcRenderer.invoke("agent:permission", { requestId, decision }),
  getLlmConfig: () => ipcRenderer.invoke("llm:get"),
  setLlmConfig: (cfg) => ipcRenderer.invoke("llm:set", cfg),
  getConnectors: () => ipcRenderer.invoke("connectors:list"),
  setConnector: (provider, values, secretKeys) =>
    ipcRenderer.invoke("connectors:set", provider, values, secretKeys),
  removeConnector: (provider) => ipcRenderer.invoke("connectors:remove", provider),
  connectGsc: () => ipcRenderer.invoke("connectors:connectGsc"),
  connectGa4: () => ipcRenderer.invoke("connectors:connectGa4"),
  socialSignalsSearch: (payload) => ipcRenderer.invoke("social-signals:search", payload),
  socialSignalsStop: (jobId) => ipcRenderer.invoke("social-signals:stop", { jobId }),
  socialSignalsPlatforms: () => ipcRenderer.invoke("social-signals:platforms"),
  onSocialSignalsEvent: (callback) => {
    const listener = (_event, message) => callback(message);
    ipcRenderer.on("social-signals:event", listener);
    return () => ipcRenderer.removeListener("social-signals:event", listener);
  },
  leadsRun: (payload) => ipcRenderer.invoke("leads:run", payload),
  leadsStop: (jobId) => ipcRenderer.invoke("leads:stop", { jobId }),
  prospectSources: () => ipcRenderer.invoke("leads:sources"),
  onLeadsEvent: (callback) => {
    const listener = (_event, message) => callback(message);
    ipcRenderer.on("leads:event", listener);
    return () => ipcRenderer.removeListener("leads:event", listener);
  },
  analyticsSaveSource: (params) => ipcRenderer.invoke("analytics:saveSource", params),
  analyticsCheckSession: (params) => ipcRenderer.invoke("analytics:checkSession", params),
  analyticsResolvePaths: (params) => ipcRenderer.invoke("analytics:resolvePaths", params),
  analyticsDeleteSource: (params) => ipcRenderer.invoke("analytics:deleteSource", params),
  analyticsReadSource: (params) => ipcRenderer.invoke("analytics:readSource", params),
  analyticsRevealSource: (params) => ipcRenderer.invoke("analytics:revealSource", params),
  analyticsExportSource: (params) => ipcRenderer.invoke("analytics:exportSource", params),
  analyticsExportText: (params) => ipcRenderer.invoke("analytics:exportText", params),
};

contextBridge.exposeInMainWorld("meeluAgent", bridge);
contextBridge.exposeInMainWorld("meelu", bridge);

if (process.argv.includes("--meelu-dev-annotator")) {
  contextBridge.exposeInMainWorld("meeluAnnotator", {
    capture: (payload) => ipcRenderer.invoke("annotator:capture", payload),
  });
}
