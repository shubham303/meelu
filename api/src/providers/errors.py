from typing import Any


class ProviderError(Exception):
    code = "error"
    http_status = 400

    def __init__(self, message: str, **extra: Any):
        super().__init__(message)
        self.extra = extra

    def payload(self) -> dict[str, Any]:
        return {"code": self.code, "message": str(self), **self.extra}


class NoProviderError(ProviderError):
    code = "no_provider"

    def __init__(self, domain: str, label: str, capability: str):
        super().__init__(
            f"No {label} provider is configured on the server for {capability}.",
            domain=domain,
            capability=capability,
        )


class NotSupportedError(ProviderError):
    code = "not_supported"

    def __init__(self, provider_id: str, capability: str):
        super().__init__(
            f"{provider_id} does not support {capability}.",
            provider_id=provider_id,
            capability=capability,
        )


class ConflictError(ProviderError):
    code = "conflict"


class ProviderRequestError(ProviderError):
    code = "request_failed"
    http_status = 502

    def __init__(self, provider_id: str, status: int | None, message: str, body: Any = None):
        super().__init__(message, provider_id=provider_id, status=status)
        self.provider_id = provider_id
        self.status = status
        self.body = body


class SpendCeilingError(ProviderError):
    code = "spend_ceiling"
    http_status = 402

    def __init__(self, spent_micros: int, ceiling_micros: int):
        super().__init__(
            f"This job has spent {spent_micros / 1_000_000:.2f} USD of its "
            f"{ceiling_micros / 1_000_000:.2f} USD vendor ceiling; start a new job to spend more.",
            spent_micros=spent_micros,
            ceiling_micros=ceiling_micros,
        )
