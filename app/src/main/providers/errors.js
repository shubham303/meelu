export class ProviderError extends Error {
  constructor(code, message, extra = {}) {
    super(message);
    this.code = code;
    Object.assign(this, extra);
  }

  toJSON() {
    return { code: this.code, message: this.message, ...this.extra() };
  }

  extra() {
    return {};
  }
}

export class NoProviderConnectedError extends ProviderError {
  constructor(domain, label) {
    super(
      "no_provider",
      `No ${label} provider is connected on this device. Connect one on the Connections screen first.`,
      { domain },
    );
  }

  extra() {
    return { domain: this.domain };
  }
}

export class ProviderNotConnectedError extends ProviderError {
  constructor(providerId) {
    super("not_connected", `${providerId} is not connected on this device.`, { providerId });
  }

  extra() {
    return { providerId: this.providerId };
  }
}

export class AmbiguousProviderError extends ProviderError {
  constructor(domain, label, providerIds) {
    super(
      "ambiguous_provider",
      `More than one ${label} provider is connected (${providerIds.join(", ")}). ` +
        "Pick a default on the Connections screen or name the provider for this call.",
      { domain, providerIds },
    );
  }

  extra() {
    return { domain: this.domain, providerIds: this.providerIds };
  }
}

export class NotSupportedError extends ProviderError {
  constructor(providerId, capability) {
    super("not_supported", `${providerId} does not support ${capability}.`, {
      providerId,
      capability,
    });
  }

  extra() {
    return { providerId: this.providerId, capability: this.capability };
  }
}

export class ProviderRequestError extends ProviderError {
  constructor(providerId, status, message, body = null) {
    super("request_failed", message, { providerId, status, body });
  }

  extra() {
    return { providerId: this.providerId, status: this.status };
  }
}

export function errorPayload(err) {
  if (err instanceof ProviderError) return err.toJSON();
  return { code: "error", message: err instanceof Error ? err.message : String(err) };
}
