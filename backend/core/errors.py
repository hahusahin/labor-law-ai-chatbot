class RetryableError(Exception):
    """Transient failure — safe to retry (e.g. 429 rate limit, 503 unavailable)."""


class NonRetryableError(Exception):
    """Permanent failure — do not retry (e.g. 400 bad request, 401 invalid key)."""
