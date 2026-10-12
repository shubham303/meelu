export class ServiceError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
    this.name = "ServiceError";
  }
}

export function readableError(error: unknown): string {
  if (error instanceof ServiceError) return error.message;

  const cause = (error as { cause?: unknown })?.cause;
  const causeMessage =
    cause instanceof Error
      ? cause.message
      : typeof cause === "string"
        ? cause
        : undefined;
  if (causeMessage) {
    const detail = (cause as { detail?: string })?.detail;
    return detail ? `${causeMessage} (${detail})` : causeMessage;
  }

  const message = error instanceof Error ? error.message : String(error);
  return message.startsWith("Failed query:")
    ? "The database rejected this write. The full statement is in the server log."
    : message;
}
