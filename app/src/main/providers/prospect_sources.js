export class ProspectSourcesClient {
  constructor({ meelu }) {
    this.domain = "prospect-sources";
    this.meelu = meelu;
  }

  async availableSources() {
    const res = await this.meelu.request("/providers/prospect-sources/sources");
    return res?.sources ?? [];
  }

  async searchSource({ source, queries, limit = 20, siteId = null }) {
    const res = await this.meelu.request("/providers/prospect-sources/search", {
      method: "POST",
      body: { source, queries, limit },
      siteId,
    });
    return res?.prospects ?? [];
  }
}
