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
  analyzeSite: (payload) => ipcRenderer.invoke("site:analyze", payload),
  stopAnalysis: (jobId) => ipcRenderer.invoke("site:analyzeStop", { jobId }),
  onAnalysisEvent: (callback) => {
    const listener = (_event, message) => callback(message);
    ipcRenderer.on("analysis:event", listener);
    return () => ipcRenderer.removeListener("analysis:event", listener);
  },
  renderSite: (payload) => ipcRenderer.invoke("site:render", payload),
  stopRender: (jobId) => ipcRenderer.invoke("site:renderStop", { jobId }),
  onRenderEvent: (callback) => {
    const listener = (_event, message) => callback(message);
    ipcRenderer.on("render:event", listener);
    return () => ipcRenderer.removeListener("render:event", listener);
  },
  checkIssues: (payload) => ipcRenderer.invoke("site:issueCheck", payload),
  stopIssueCheck: (siteId) => ipcRenderer.invoke("site:issueCheckStop", { siteId }),
  onIssueCheckEvent: (callback) => {
    const listener = (_event, message) => callback(message);
    ipcRenderer.on("issue-check:event", listener);
    return () => ipcRenderer.removeListener("issue-check:event", listener);
  },
  abort: (turnId) => ipcRenderer.invoke("agent:abort", turnId),
  sessionUsage: () => ipcRenderer.invoke("usage:session"),
  respondPermission: (requestId, decision) =>
    ipcRenderer.invoke("agent:permission", { requestId, decision }),
  getLlmConfig: () => ipcRenderer.invoke("llm:get"),
  setLlmConfig: (cfg) => ipcRenderer.invoke("llm:set", cfg),
  getConnectors: () => ipcRenderer.invoke("connectors:list"),
  providersCatalog: () => ipcRenderer.invoke("providers:catalog"),
  providersStatus: () => ipcRenderer.invoke("providers:status"),
  setProviderDefault: (domain, providerId) =>
    ipcRenderer.invoke("providers:setDefault", { domain, providerId }),
  providerCall: (tool, input) => ipcRenderer.invoke("providers:call", { tool, input }),
  setConnector: (provider, values, secretKeys) =>
    ipcRenderer.invoke("connectors:set", provider, values, secretKeys),
  removeConnector: (provider) => ipcRenderer.invoke("connectors:remove", provider),
  connectGsc: () => ipcRenderer.invoke("connectors:connectGsc"),
  connectGa4: () => ipcRenderer.invoke("connectors:connectGa4"),
  getMailboxAccounts: () => ipcRenderer.invoke("mailbox:accounts"),
  connectMailbox: (values, secretKeys) =>
    ipcRenderer.invoke("mailbox:connect", { values, secretKeys }),
  forgetMailbox: (accountId) => ipcRenderer.invoke("mailbox:forget", { accountId }),
  mailboxList: (params) => ipcRenderer.invoke("mailbox:list", params),
  mailboxRead: (params) => ipcRenderer.invoke("mailbox:read", params),
  mailboxSyncProspects: (params) => ipcRenderer.invoke("mailbox:syncProspects", params),
  mailboxSend: (params) => ipcRenderer.invoke("mailbox:send", params),
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
