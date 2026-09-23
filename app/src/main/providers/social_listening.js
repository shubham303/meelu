export class SocialListeningClient {
  constructor({ meelu }) {
    this.domain = "social-listening";
    this.meelu = meelu;
  }

  async availablePlatforms() {
    const res = await this.meelu.request("/providers/social-listening/platforms");
    return res?.platforms ?? [];
  }

  async searchPlatform({ platform, keywords, since = null, limit = 30, siteId = null }) {
    const res = await this.meelu.request("/providers/social-listening/search", {
      method: "POST",
      body: { platform, keywords, since, limit },
      siteId,
    });
    return res?.posts ?? [];
  }
}
