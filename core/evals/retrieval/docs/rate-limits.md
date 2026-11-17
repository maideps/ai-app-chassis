# Rate limits

The API allows 600 requests per minute per token and 10,000 requests per hour per account. Bulk endpoints count each item in the batch as one request.

When a limit is reached the API answers HTTP 429 Too Many Requests with a `Retry-After` header that says how many seconds to wait. Clients should back off exponentially and retry; repeated violations within an hour lower the limit for that token for the rest of the hour.

Enterprise plans can request higher limits from support. Limits are reported in the `X-RateLimit-Remaining` and `X-RateLimit-Reset` response headers.
