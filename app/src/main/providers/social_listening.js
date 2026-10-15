export class SocialListeningClient {
  constructor({ meelu }) {
    this.domain = "social-listening";
    this.meelu = meelu;
  }

  async availablePlatforms() {
    const res = await this.meelu.request("/providers/social-listening/platforms");
    return res?.platforms ?? [];
  }
}
