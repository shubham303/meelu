export class ProviderError extends Error {
  constructor(code, message, extra = {}) {
    super(message);
    this.code = code;
    Object.assign(this, extra);
  }

  toJSON() {
    return { code: this.code, message: this.message };
  }
}

export function errorPayload(err) {
  if (err instanceof ProviderError) return err.toJSON();
  return {
    code: err?.code ?? "error",
    message: err instanceof Error ? err.message : String(err),
  };
}
