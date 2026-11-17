# Webhooks

Webhooks send an HTTP POST to your server when something changes: a project is created, a comment is added, or an export finishes. Register an endpoint URL and choose the events from Settings, Integrations, Webhooks.

Each delivery is signed. The `X-Signature` header holds an HMAC-SHA256 of the raw body computed with your webhook secret; reject deliveries whose signature does not match.

Failed deliveries (any status other than 2xx, or no answer within ten seconds) are retried five times with increasing delays over about an hour. After that the delivery is dropped and listed as failed on the webhook page, where it can be resent by hand.
