# Learn the system by following one link

## Why build this?

The small feature set lets you understand an entire cloud application: browser requests, API routing, Python handlers, persistent storage, concurrent updates, observability, and infrastructure as code. For your AWS Student Builder Group application, demonstrate what you learned and the decisions you can explain, rather than claiming production scale or AWS deployment before it happens.

## Creating a link

1. JavaScript handles the form submission and sends JSON to `POST /api/links`.
2. API Gateway turns the request into an HTTP API v2 event. In local development, the standard-library server performs this translation.
3. `Application.route()` checks content type, size, JSON shape, and destination URL.
4. Two shared fixed-window limits allow at most 20 successful creation attempts per minute and 500 per UTC day. Failed storage/collision attempts can also consume quota. Limits are global, not per person. This is simple and easy to test; one person can exhaust everyone’s quota.
5. `secrets.token_urlsafe(6)` produces eight URL-safe characters from six random bytes (48 bits). It is a random identifier, not an encryption key or access-control mechanism.
6. A conditional insert succeeds only when the partition key is unused. On a collision, the app tries a new code up to five times. It never overwrites a previous destination.
7. The API returns 201 with the short link and metadata. The browser saves only the code locally.

## Following a link

1. The browser requests `GET /r/abcdefgh`.
2. The app validates the code format.
3. DynamoDB `UpdateItem` checks that the item exists and has not expired, atomically adds one visit, and returns the updated record.
4. The app returns `302` with `Location: <original URL>` and `Cache-Control: no-store`.
5. The browser requests the destination website directly. Lambda never fetches the destination.

Why 302 rather than a permanent 301? Browsers and intermediaries can cache permanent redirects and bypass the backend on later visits. A temporary redirect with `no-store` keeps normal repeat requests flowing through the counter.

## Why atomic increments matter

Imagine two visitors arrive when the count is 5. Reading 5 in two workers and writing 6 in both loses a visit. DynamoDB's atomic `ADD` updates the shared value safely, ending at 7. SQLite uses a write transaction locally to reproduce that behavior.

This is not exactly-once analytics: retries, bots, previews, failed browser navigations, and network failures can affect counts. A request may commit its increment before its response is lost. Automatic SDK retries are disabled for these non-idempotent updates to avoid adding extra attempts silently. An explicit user/browser retry can still add another visit.

HEAD requests and statistics reads do not increment counts. Opening the destination directly does not increment them either.

## Data model

One DynamoDB table, one string partition key named `pk`; no indexes or scans are needed.

```json
{
  "pk": "abcdefgh",
  "url": "https://docs.aws.amazon.com/lambda/latest/dg/welcome.html",
  "visits": 0,
  "created_at": 1700000000,
  "expires_at": 1702592000
}
```

Rate-limit rows use keys such as `rate#60#28333333`, with `count` and `expires_at`. The colon/hash-containing namespace cannot collide with the eight-character short-code format. Using separate window keys means the next window works even when old rows have not been deleted yet.

DynamoDB TTL eventually deletes expired records; it does not guarantee immediate removal. The handler checks expiration itself, so expired links stop working immediately even before TTL cleanup. Local link records remain on disk but are rejected after expiry; local rate-limit records are pruned during creation.

Statistics use strongly consistent `GetItem` reads so the count reflects a completed increment rather than an older eventually consistent value.

## Files to read in order

1. `backend/static/app.js`: trace form → fetch → display.
2. `local_server.py`: see how HTTP becomes an event dictionary.
3. `backend/app.py`: follow POST, redirect, and statistics branches.
4. `backend/storage.py`: compare SQLite transactions with DynamoDB expressions.
5. `tests/test_app.py`: see expected behavior and edge cases.
6. `template.yaml`: connect each AWS resource to its role in the diagram.

## Important trade-offs

- **One function:** simplest deployment and same-origin frontend. Separate create/redirect/stats functions could have more specific permissions and scaling, but would add infrastructure for this first version.
- **DynamoDB on-demand:** fits sporadic learning traffic without managing provisioned capacity; each read/write still has a price. “Free plan supported” does not mean every usage unit is free forever.
- **SQLite locally:** fast, persistent, no Docker or AWS dependency. Moto tests verify the DynamoDB API expressions, but real cloud integration must be tested later after approval.
- **Same-origin frontend:** no CORS needed. CORS is not authentication or an abuse-prevention mechanism.
- **Public statistics:** anyone with the code can see its URL and count. Recent links are browser-local; there is no global list endpoint.
- **API throttling:** reduces request pressure but is a best-effort target, not a financial cap. Creation limits are enforced in storage, but rejected requests and lookups still consume resources in AWS.
- **CloudWatch:** use standard Lambda Invocations, Errors, Duration, Throttles; API Gateway Count/4xx/5xx/Latency; and DynamoDB throttle/capacity metrics. The template creates logs but no paid custom metrics, dashboard, or alarm resources.

## Exercises before deploying

1. Explain why reading statistics must not update the count.
2. Change the test clock to simulate expiration without waiting 30 days.
3. Run the collision test and explain why a conditional insert is essential even with random codes.
4. Predict the result of 50 concurrent visits, then run the concurrency test.
5. Explain the distinction between a link code, browser localStorage, and an AWS credential.
6. Trace each IAM action in the template to the Python method that needs it.

## A concise demo for your application

“I built and deployed a Python serverless URL shortener with a plain JavaScript frontend. I used conditional writes to handle code collisions and atomic increments for concurrent visits. I described the AWS infrastructure in SAM, scoped the Lambda role to its table and logs, and tested locally with SQLite and mocked DynamoDB. During deployment, I used CloudWatch to diagnose startup timeouts and verified the working create/redirect/statistics flow in Ohio.”

Use wording that accurately reflects your own understanding and the assistance you received. Read the startup logs and repeat the live demo yourself so you can explain the diagnosis. Git is initialized locally; no GitHub repository has been created or published.
