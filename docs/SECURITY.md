# Security and privacy boundaries

## Implemented

- HTTP/HTTPS only; no embedded usernames/passwords, control characters, backslashes, or nonstandard ports.
- Public IP literals only; private, loopback, link-local, and other nonglobal addresses are rejected.
- ASCII public-shaped hostnames; local/internal suffixes and ambiguous numeric IP formats are rejected. International names must be represented as punycode with a supported ASCII suffix.
- Maximum destination length of 2,048 UTF-8 bytes and request body of 4,096 bytes.
- Cryptographically random codes with conditional insertion and collision retries.
- Global atomic creation limits: 20/minute and 500/UTC day. Fixed windows can permit bursts across a boundary.
- Thirty-day expiration enforced in code, independently of eventual database TTL cleanup.
- Optional `AllowedHosts` SAM parameter restricts destinations to exact comma-separated hostnames; subdomains are not automatically allowed.
- No request-body/URL/IP logging. Unexpected errors expose only a generic message; logs record the exception class without its message.
- Restrictive same-origin CSP, no inline scripts or third-party dependencies, `nosniff`, no-referrer policy, frame embedding blocked, no redirect caching.
- User-supplied content is rendered with `textContent`, not injected as HTML.
- No AWS credentials in frontend, application code, or configuration. Lambda will use its execution role. Local runtime does not import the AWS SDK.
- Lambda role permits only GetItem/PutItem/UpdateItem on its table and log-stream creation/writes in its log group. No Scan, DeleteItem, table administration, or wildcard service permissions.

## Limitations to understand

This is an intentionally unauthenticated learning demo. Public websites can be malicious, and URL syntax validation cannot determine whether a destination is trustworthy. There is no malware/phishing scanning, user identity, ownership system, or abuse-report workflow.

The server does not resolve DNS or fetch destinations. It therefore cannot verify that a hostname resolves to a public address or prevent a destination from later redirecting elsewhere. Syntax checks do not prevent DNS rebinding or every browser URL interpretation. A controlled demonstration should use the optional exact-host allowlist. An unrestricted public launch needs a separate abuse review.

Short URLs and their statistics are public to anyone who knows or discovers the code. Never submit password-reset links, signed download links, authentication tokens, or other secret-bearing URLs. Original destinations are stored in the database and returned by the statistics endpoint. Browser history and localStorage retain codes.

Every GET redirect is a countable request, including bots, previews, retries, and repeat visitors. Counts do not measure unique users or successful destination page loads. HEAD does not increment. A storage/network error can occur after an update commits; exactly-once delivery is not guaranteed.

API Gateway throttling is not a hard cost ceiling, and distributed abuse can still consume request capacity and credits. Someone can deliberately exhaust the shared creation quota. The Free plan and service restrictions are separate from application controls.

The local development server binds only to 127.0.0.1; it is not hardened for exposure to the internet. Production HTTP parsing and TLS will be handled by API Gateway. DynamoDB access in a real AWS deployment has not been exercised in this phase.
