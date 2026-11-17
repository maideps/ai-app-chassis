# API tokens

Every request to the API carries a personal access token in the Authorization header. Tokens are created from the Settings page, under Developer access, and are shown only once: copy the value before closing the dialog.

Tokens expire after 90 days. Thirty days before expiry the account owner receives an e-mail reminder. An expired token returns HTTP 401 with the error code `token_expired`.

To rotate a token, create a new one, update your integrations, then revoke the old token from the same page. Revocation takes effect immediately; requests in flight with the old token fail.

Scopes limit what a token can do. A read-only token can list projects and download exports but cannot create or delete anything.
