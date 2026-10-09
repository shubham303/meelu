import { MeeluApi } from "./meelu.js";
import { SocialListeningClient } from "./social_listening.js";

export function createProviders({ cookieHeader = "" } = {}) {
  const meelu = new MeeluApi({ cookieHeader });
  const listening = new SocialListeningClient({ meelu });
  return { listening };
}
