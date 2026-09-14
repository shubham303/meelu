import {
  AmbiguousProviderError,
  NoProviderConnectedError,
  NotSupportedError,
  ProviderNotConnectedError,
} from "./errors.js";

export class ProviderFacade {
  constructor({ domain, label, adapters, store, meelu }) {
    this.domain = domain;
    this.label = label;
    this.adapters = new Map(adapters.map((a) => [a.id, a]));
    this.store = store;
    this.meelu = meelu;
  }

  connectedAdapters() {
    const out = [];
    for (const adapter of this.adapters.values()) {
      const values = this.store.connected(adapter.id);
      if (values != null) out.push(adapter.withCredentials(values));
    }
    return out;
  }

  status() {
    const connected = this.connectedAdapters().map((a) => a.id);
    return {
      domain: this.domain,
      connected,
      default: this.store.defaultFor(this.domain),
      adapters: [...this.adapters.values()].map((a) => ({
        id: a.id,
        name: a.name,
        capabilities: [...a.capabilities],
        connected: connected.includes(a.id),
      })),
    };
  }

  resolve(explicitId = null) {
    const connected = this.connectedAdapters();
    if (explicitId) {
      const found = connected.find((a) => a.id === explicitId);
      if (!found) throw new ProviderNotConnectedError(explicitId);
      return found;
    }
    if (connected.length === 0) throw new NoProviderConnectedError(this.domain, this.label);
    if (connected.length === 1) return connected[0];
    const preferred = this.store.defaultFor(this.domain);
    const chosen = connected.find((a) => a.id === preferred);
    if (chosen) return chosen;
    throw new AmbiguousProviderError(
      this.domain,
      this.label,
      connected.map((a) => a.id),
    );
  }

  require(capability, explicitId = null) {
    const adapter = this.resolve(explicitId);
    if (!adapter.capabilities.has(capability)) {
      throw new NotSupportedError(adapter.id, capability);
    }
    return adapter;
  }
}

export class ProviderAdapter {
  constructor(credentials = null) {
    this.credentials = credentials;
  }

  withCredentials(values) {
    const copy = Object.create(Object.getPrototypeOf(this));
    Object.assign(copy, this, { credentials: values });
    return copy;
  }

  static get capabilities() {
    return new Set();
  }

  get capabilities() {
    return this.constructor.capabilities;
  }

  get id() {
    return this.constructor.id;
  }

  get name() {
    return this.constructor.name_;
  }

  unsupported(capability) {
    return new NotSupportedError(this.id, capability);
  }
}
