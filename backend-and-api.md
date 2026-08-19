# Backend and API Practices

Applies to any server-side application or service: REST, GraphQL, gRPC, or RPC; monolith
or microservices; any language. Framework-specific advice is marked as such.

**Read this before:** designing or changing an endpoint, adding a service or module,
writing business logic, introducing background work, or touching anything that crosses a
process boundary.

---

## 1. Core principles

1. **The API contract is the product.** Internals can be rewritten; a contract you have
   published cannot. Design it before you implement it, and change it only additively.
2. **Never trust the caller.** Not the browser, not the mobile app, not the other
   microservice. Validate and authorize at every entry point. See `security.md`.
3. **The network fails, and it fails partially.** Every remote call can hang, time out,
   return garbage, or succeed after you gave up. Design for that, not for the happy path.
4. **Make operations safe to repeat.** Retries are a fact of distributed systems.
   Idempotence is what makes them harmless.
5. **If it isn't logged, traced, or measured, it didn't happen**, and you will not be able
   to debug it at 3am.

---

## 2. API design

### 2.1 Resources and URLs

- **Model nouns, not verbs.** `POST /orders/{id}/refunds` over `POST /refundOrder`. When an
  action genuinely isn't a resource, make the action itself a resource
  (`POST /orders/{id}/cancellations`) rather than inventing an RPC verb in a REST API.
- **Plural, lowercase, hyphenated collection names**: `/payment-methods`, not
  `/PaymentMethod` or `/payment_methods`. Pick one convention and never mix.
- **Nest at most one level.** `/users/{id}/orders` is fine; `/users/{id}/orders/{id}/items/{id}`
  is not. Address the deep resource directly at `/order-items/{id}`.
- **Never expose sequential database ids in public URLs.** They leak volume and enable
  enumeration. Use UUIDv7/ULID (sortable, index-friendly) or a public opaque id.

### 2.2 HTTP semantics

Use methods and status codes for what they mean. Clients, proxies, and CDNs act on them.

| Method | Semantics | Safe | Idempotent |
|---|---|---|---|
| `GET` | Read. Must never mutate. | ✅ | ✅ |
| `POST` | Create, or non-idempotent action | ❌ | ❌ |
| `PUT` | Full replace at a known id | ❌ | ✅ |
| `PATCH` | Partial update | ❌ | ❌ (make it so if you can) |
| `DELETE` | Remove | ❌ | ✅ (repeat → 204/404, never an error) |

| Status | Use it when |
|---|---|
| `200` | Success with a body |
| `201` | Created; include a `Location` header |
| `202` | Accepted for async processing; return a status URL |
| `204` | Success, no body |
| `400` | Malformed request (unparseable, wrong types) |
| `401` | Not authenticated, or credentials invalid/expired |
| `403` | Authenticated but not permitted |
| `404` | Not found. **Also use for "exists but you may not see it"** |
| `409` | Conflict: duplicate, or version/state conflict |
| `410` | Gone permanently |
| `422` | Well-formed but semantically invalid (business rule violation) |
| `429` | Rate limited; must include `Retry-After` |
| `500` | Unhandled server fault. Never leak internals. |
| `503` | Dependency down / shedding load; include `Retry-After` |

Never return `200` with `{"error": …}` in the body. It defeats client error handling,
monitoring, alerting, and retry logic.

### 2.3 Collections

- **Always paginate.** No unbounded list endpoint, ever, not even for "small" tables,
  which grow. Enforce a default (e.g. 20) and a hard maximum (e.g. 100) page size server-side.
- **Prefer cursor (keyset) pagination** over offset for anything large or frequently
  written. Offset pagination gets slower the deeper you go and silently skips or duplicates
  rows when the underlying data changes between pages. See `database-and-migrations.md` §4.3.
- **Filtering, sorting, and field selection go in query parameters**, and every sortable
  or filterable field must be **allow-listed**. Never interpolate a client-supplied column
  name into a query.
- **Return a consistent envelope** for collections so clients can write one parser:

  ```json
  { "data": [ … ], "page": { "next_cursor": "eyJpZCI6…", "has_more": true } }
  ```

### 2.4 Versioning and compatibility

- **Version from day one.** `/v1/` in the path is the simplest thing that works and is
  visible in logs, dashboards, and CDN rules.
- **Additive changes only within a version.** Safe: new optional field, new endpoint, new
  optional parameter, new enum value *if clients were told to tolerate unknowns*. Breaking:
  removing or renaming a field, changing a type, tightening validation, making an optional
  field required, changing a default.
- **Clients must ignore unknown fields.** State this in your API documentation and follow it
  in your own client code. It is what makes additive evolution possible.
- **Deprecate on a schedule, not on a whim.** Announce, add `Deprecation`/`Sunset` headers,
  measure remaining usage per client, then remove. Never remove something still in use.

### 2.5 GraphQL specifics

- **Depth-limit and cost-limit every query.** Without it, one nested query is a denial of
  service. Reject beyond a configured complexity budget.
- **Batch every resolver that hits a datastore** (DataLoader pattern). Otherwise nested
  fields produce N+1 queries by construction.
- **Authorize per field, not just per query.** A permitted parent does not imply permitted
  children.
- **Disable introspection and persist queries in production** for public-facing APIs.

---

## 3. Validation

- **Validate at the boundary, in one place, before any business logic runs.** Use a schema
  (JSON Schema, Zod, Pydantic, bean validation, struct tags) rather than scattered manual
  `if` checks.
- **Parse, don't validate.** Convert the raw request into a typed domain object at the edge
  so the rest of the code cannot receive an invalid shape. Passing untyped maps inward means
  re-validating in every function, forever.
- **Reject unknown fields** in request bodies rather than silently dropping them. A typo'd
  field name that silently does nothing is a bug that reaches production.
- **Validate ranges, lengths, and formats, not just types.** Every string needs a maximum
  length; every number needs bounds; every list needs a maximum size. Unbounded input is a
  memory-exhaustion vector.
- **Return all validation errors at once**, keyed by field path, so clients can render a
  complete form state in one round trip.

---

## 4. Error handling

### 4.1 The error contract

Return one machine-readable shape for every error in the service:

```json
{
  "error": {
    "code": "insufficient_funds",
    "message": "Balance is below the transfer amount.",
    "details": [
      { "field": "amount", "code": "max_exceeded", "message": "Must be ≤ 250.00" }
    ],
    "request_id": "01J8X2Q…"
  }
}
```

- **`code` is a stable, documented string** clients can branch on. Never make clients parse
  `message`. It is for humans and may be localized or reworded.
- **`request_id` on every response**, success and failure. This is what turns a support
  ticket into a log query.

### 4.2 Rules

- **Never leak internals**: no stack traces, SQL, file paths, dependency names, or internal
  hostnames in a response. Log them; return a code and a request id. See `security.md` §7.
- **Fail fast and loudly on programmer error** (misconfiguration, invalid state, missing
  required env var). Crash at startup rather than serving broken traffic.
- **Handle expected failures explicitly** (validation, conflict, not-found, dependency
  timeout). These are control flow, not exceptions to swallow.
- **Never catch-and-ignore.** An empty catch block is a silent data-loss bug. If a failure
  is genuinely tolerable, log it at the appropriate level with the reason it's tolerable.
- **Preserve the cause when re-throwing.** Wrap with context (`"charging customer %s: %w"`),
  never discard the original.
- **A partial write that fails must not leave inconsistent state.** Use a transaction, or an
  explicit compensating action. See §6.

---

## 5. Architecture and code organization

### 5.1 Layering

Keep three concerns separated, whatever you name them:

```
Transport   HTTP/gRPC/queue handler. Parses input, calls a use case, formats output.
            Knows about status codes. Knows nothing about business rules.
Domain      Business rules and entities. Pure, testable, no framework imports,
            no SQL, no HTTP.
Infra       Database, cache, queues, third-party clients. Implements interfaces
            the domain declares.
```

**Dependencies point inward.** Domain code must not import the web framework or the ORM. The
test: *can I unit-test my business rules with no database and no HTTP?* If not, the layering
has leaked.

- **Never put business logic in a controller/handler.** Handlers translate; they don't decide.
- **Never let ORM entities reach the transport layer.** Map to explicit response DTOs.
  Otherwise a schema change silently becomes a breaking API change, and lazy-loaded
  relations become accidental N+1 queries during serialization.
- **Organize by feature, not by technical layer.** `orders/{handler,service,repository}`
  beats `controllers/`, `services/`, `repositories/` once you pass a handful of features:
  a change to ordering touches one directory.

### 5.2 Dependencies and configuration

- **Inject dependencies; don't reach for globals or singletons.** Explicit constructor
  parameters make substitution in tests trivial and make coupling visible.
- **All configuration comes from the environment, validated at startup.** Parse the whole
  config into a typed object at boot and fail immediately on anything missing or malformed.
  Never read raw env vars deep in business logic, and never ship a default that is only safe
  in development (a default secret, `DEBUG=true`, permissive CORS).
- **Never commit secrets.** See `security.md` §5.

### 5.3 Services

Only split a service out when you have a specific reason: independent scaling, independent
deployment cadence, team ownership, or a hard isolation boundary. "Microservices" as a
default converts local function calls into network calls with partial failure, distributed
transactions, and versioned contracts: a large, permanent cost.

When you do split:
- **Each service owns its data.** No other service reads its database directly. Ever. A
  shared database makes independent deployment impossible.
- **Communicate via well-defined contracts**, versioned like public APIs.
- **Prefer async events for cross-service side effects**; keep synchronous chains shallow.
  Every synchronous hop multiplies latency and failure probability.

---

## 6. Data, transactions, and concurrency

- **Keep transactions short and scoped to a single logical operation.** Never do I/O (HTTP
  calls, emails, queue publishing) inside a transaction. It holds locks for the duration of
  a remote timeout.
- **Never rely on read-then-write without protection.** Check-then-act across a transaction
  boundary is a race. Use a unique constraint, an atomic update
  (`UPDATE … WHERE version = ?`), `SELECT … FOR UPDATE`, or a conditional write.
- **Use optimistic concurrency for user-editable resources.** A `version` column plus
  `If-Match`/`ETag` turns silent last-write-wins overwrites into a `409` the user can act on.
- **Acquire locks in a consistent global order** to avoid deadlocks, and keep them brief.
- **Enforce invariants in the database, not only in code.** Application-level checks race;
  unique and foreign-key constraints do not. See `database-and-migrations.md` §2.
- **Making a mutation idempotent** is the single highest-value robustness change available
  to most APIs. For creates, accept a client-supplied `Idempotency-Key`, store it with the
  result, and return the stored result on replay.

  ```
  POST /payments
  Idempotency-Key: 9f2a…      → charge once; retries return the same 201 body
  ```

- **The dual-write problem is real**: writing to your database and publishing an event are
  not atomic. If the event must not be lost, use the transactional outbox pattern: write the
  event to a table in the same transaction, and relay it separately.

---

## 7. Calling other services

- **Always set an explicit timeout.** Most HTTP clients default to infinite. One slow
  dependency with no timeout exhausts your connection pool and takes down the whole service.
  Set connect and read timeouts on every client.
- **Give each request a total deadline and propagate it.** A caller with 2s left should not
  start a 5s downstream call.
- **Retry only idempotent operations**, with exponential backoff **plus jitter**, and a small
  bounded attempt count. Synchronized retries without jitter create thundering herds that
  keep a recovering dependency down.
- **Never retry `4xx`.** The request is wrong; repeating it won't help. Retry `429`
  (respecting `Retry-After`), `503`, and transport errors.
- **Use a circuit breaker for critical dependencies.** After a failure threshold, fail fast
  for a cooling-off period. This protects both you and the struggling dependency.
- **Bulkhead your resources.** Separate connection pools per dependency so one failing
  integration can't consume every worker.
- **Degrade gracefully.** If the recommendations service is down, serve the page without
  recommendations. Decide per dependency, in advance, whether it is required or optional.

---

## 8. Background work

- **Anything slow, retriable, or non-essential to the response belongs in a queue**: email,
  webhooks, report generation, thumbnails, third-party sync. Never make a user wait for it,
  and never fire-and-forget it in an in-process thread that dies with the deploy.
- **Enqueue ids, not payloads.** The job re-reads current state; a serialized snapshot goes
  stale between enqueue and execution.
- **Jobs must be idempotent.** At-least-once delivery is the norm; a job will run twice.
- **Every queue needs a dead-letter queue and an alert on it.** A DLQ nobody watches is a
  silent failure store.
- **Bound retries and use backoff.** Infinite retries on a poison message will saturate the
  workers.
- **Make jobs interruptible and restart-safe.** Deploys kill workers mid-job; handle
  shutdown signals and either finish quickly or leave the job re-runnable.
- **For scheduled jobs, guard against overlap and multi-instance execution** with a lock or
  a leader election. Two app instances means two crons firing.

---

## 9. Caching

- **Know what you're solving.** Caching hides a performance problem; sometimes that is the
  right call, but check for a missing index first (`database-and-migrations.md` §3).
- **Cache invalidation is the hard part, so choose a strategy explicitly**: short TTL
  (simple, tolerates staleness), explicit invalidation on write (fresh, easy to get wrong),
  or versioned keys (safe, wastes space). Write down which you chose and why.
- **Never cache anything user-specific under a shared key.** This is a recurring, serious
  data-leak bug: one user's response served to another. Include the identity in the key, or
  don't cache.
- **Set `Cache-Control` deliberately on every response.** Authenticated responses need
  `private, no-store` unless you have specifically reasoned otherwise.
- **Guard against stampedes.** When a hot key expires, use a lock or serve-stale-while-
  revalidate so one miss doesn't become 10,000 simultaneous rebuilds.

---

## 10. Observability

### 10.1 Logging

- **Structured, machine-parseable logs (JSON), one event per line.** Free-text logs cannot
  be queried, aggregated, or alerted on.
- **Include a correlation/request id on every log line**, propagated across service
  boundaries via a header. Return it to the client too.
- **Never log secrets, credentials, tokens, full card numbers, or unnecessary PII.**
  Maintain a redaction list and apply it in the logger itself, not at each call site. See
  `security.md` §7.
- **Use levels meaningfully.** `ERROR` = a human must look at this. `WARN` = degraded but
  handled. `INFO` = notable business events. `DEBUG` = off in production. An `ERROR` log
  that fires routinely trains everyone to ignore all `ERROR` logs.
- **Log decisions and outcomes, not control flow.** "charge declined: insufficient_funds,
  customer=X, amount=Y" is useful; "entering method chargeCard" is noise.

### 10.2 Metrics and tracing

- **Instrument the four signals per endpoint**: request rate, error rate, duration, and
  saturation (queue depth, pool utilization).
- **Track percentiles, never averages.** p50/p95/p99. An average latency hides the fact that
  1% of users are timing out.
- **Distributed tracing across service boundaries** is the only practical way to debug
  latency in a multi-service system. Propagate trace context everywhere, including into
  queue messages.
- **Alert on symptoms users feel** (error rate, latency, queue age), not on causes (CPU).
  Every alert must be actionable and link to a runbook; anything else is noise that erodes
  on-call trust.

### 10.3 Health checks

Expose two distinct endpoints:
- **Liveness**: "is the process wedged?" No dependency checks. Failing this restarts you.
- **Readiness**: "can I serve traffic?" Checks critical dependencies. Failing this removes
  you from the load balancer.

Conflating them causes restart loops when a database blips.

---

## 11. Performance

- **Profile before optimizing.** The bottleneck is almost never where it feels like it is.
  In most web backends it is the database (§4 of `database-and-migrations.md`) or a
  synchronous remote call.
- **N+1 queries are the default failure mode of every ORM.** Assert on query counts in tests
  for hot paths; eager-load deliberately.
- **Stream large responses and large uploads**; never load a whole file or result set into
  memory. One 2GB export will take down the process.
- **Use connection pools, size them deliberately, and never open a connection per request.**
  Pool size should relate to database capacity, not to worker count wishful thinking.
- **Do work once**: compute-per-request that could be compute-per-deploy (config parsing,
  regex compilation, template parsing, key derivation) belongs at startup.
- **Rate-limit every public endpoint**, and more strictly on expensive and auth-related ones.
  See `security.md` §6.

---

## 12. Testing

- **Test the domain layer heavily and in isolation**: fast, no I/O. If this is hard, revisit
  §5.1.
- **Test the transport layer through the real routing stack** with the app assembled: status
  codes, headers, serialization, auth, validation errors.
- **Use real datastores in integration tests** (containers), not mocks. Mocked repositories
  pass while the real SQL is wrong.
- **Mock only what you don't own**: third-party HTTP, payment providers, mail. And verify
  those mocks against reality with contract tests or recorded fixtures you refresh.
- **Every bug fix starts with a failing test that reproduces it.** Otherwise you don't know
  you fixed it, and nothing stops it returning.
- **Test the failure paths explicitly**: timeouts, dependency 500s, malformed input,
  concurrent writes, permission denials. That is where production incidents come from.
- **Tests must be deterministic and independent.** No shared mutable fixtures, no ordering
  dependencies, no real clock, no real network. Inject time; never call `now()` directly in
  logic you need to test.

---

## 13. Anti-patterns

- Unbounded list endpoints with no pagination.
- `200 OK` with an error payload.
- HTTP client with no timeout.
- Retrying non-idempotent operations.
- Business logic in controllers; ORM entities serialized straight to the wire.
- Catching an exception and continuing with no log and no handling.
- Transactions that wrap a network call.
- Read-check-write without a constraint or lock.
- A shared database between services.
- Cache keys missing the user/tenant identity.
- Stack traces or SQL errors in API responses.
- Config read from env vars scattered through business logic, with unsafe defaults.
- Cron jobs running once per app instance.
- `SELECT *` mapped to a response DTO; see `database-and-migrations.md`.
- Sequential integer ids exposed publicly.
- Logging full request bodies containing credentials or PII.

---

## Review checklist

**Contract**
- [ ] Correct HTTP method and status code semantics
- [ ] Versioned path; all changes additive within the version
- [ ] Every collection paginated with an enforced max page size
- [ ] Sort/filter fields allow-listed
- [ ] Consistent error envelope with a stable `code` and a `request_id`
- [ ] No internal details (stack traces, SQL, hostnames) in responses

**Validation & auth**
- [ ] Schema validation at the boundary before any logic
- [ ] Unknown fields rejected; lengths, ranges, and collection sizes bounded
- [ ] Every endpoint authenticated and authorized on the object, not just the route
- [ ] Rate limits on public and expensive endpoints

**Structure**
- [ ] Domain logic testable without HTTP or a database
- [ ] No ORM entities crossing the transport boundary
- [ ] Config parsed and validated at startup; no unsafe defaults
- [ ] Dependencies injected, not global

**Data & concurrency**
- [ ] Transactions short, with no I/O inside
- [ ] Invariants enforced by database constraints
- [ ] Concurrent updates guarded (version/`FOR UPDATE`/atomic update)
- [ ] Mutations idempotent, or protected by an idempotency key

**Remote calls & jobs**
- [ ] Explicit timeouts on every client; deadlines propagated
- [ ] Retries only on idempotent ops, with backoff + jitter and a cap
- [ ] Optional dependencies degrade gracefully
- [ ] Background jobs idempotent, bounded-retry, with a monitored DLQ
- [ ] Scheduled jobs guarded against multi-instance execution

**Operability**
- [ ] Structured logs with correlation id; secrets and PII redacted
- [ ] Rate/error/duration/saturation metrics; percentiles not averages
- [ ] Separate liveness and readiness endpoints
- [ ] Alerts on user-visible symptoms, each with a runbook

**Testing**
- [ ] Domain unit tests fast and I/O-free
- [ ] Integration tests against a real datastore
- [ ] Failure paths covered: timeout, 5xx, malformed input, conflict, denial
- [ ] Regression test accompanies every bug fix
- [ ] No real clock or real network in tests
