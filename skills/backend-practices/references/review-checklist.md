# Review checklist: Backend and API Practices

The condensed form of the `backend-practices` skill. Use it as a review pass over a diff, or as a
pull-request template. Each item maps to a numbered section of that skill's SKILL.md,
so read the section when an item needs its reasoning.

## Review checklist

**Contract**
- [ ] Correct HTTP method and status code semantics
- [ ] Versioned path; all changes additive within the version
- [ ] Every collection paginated with an enforced max page size
- [ ] Sort/filter fields allow-listed
- [ ] Consistent error envelope with a stable `code` and a `request_id`
- [ ] Errors carry a next step and an explicit `retryable` flag
- [ ] Field types and cardinality stable across responses; deprecations visible in the body
- [ ] No internal details (stack traces, SQL, hostnames) in responses

**Legibility to its callers**
- [ ] Operations named verb plus noun; paths still address nouns
- [ ] Descriptions say when the operation applies and when to use a different one
- [ ] Units in field names; closed sets enumerated, not free text
- [ ] A worked request and response example per operation, generated or asserted
- [ ] Dry run available on destructive and bulk operations
- [ ] Field selection supported and allow-listed
- [ ] Realistic task prompts exercise the published schema in CI

**Validation & auth**
- [ ] Schema validation at the boundary before any logic
- [ ] Unknown fields rejected; lengths, ranges, and collection sizes bounded
- [ ] Every endpoint authenticated and authorized on the object, not just the route
- [ ] Rate limits on public and expensive endpoints

**Structure**
- [ ] Domain logic testable without HTTP or a database
- [ ] No ORM entities crossing the transport boundary
- [ ] Config parsed and validated at startup; no unsafe defaults
- [ ] Environment read only in the config layer
- [ ] Dependencies injected, not global
- [ ] Strict type checking on; guard clauses over nested conditionals

**Data & concurrency**
- [ ] Transactions short, with no I/O inside
- [ ] Jobs and events dispatched after commit, never inside the transaction
- [ ] Invariants enforced by database constraints
- [ ] Concurrent updates guarded (version/`FOR UPDATE`/atomic update)
- [ ] Mutations idempotent, or protected by an idempotency key

**Remote calls & jobs**
- [ ] Explicit timeouts on every client; deadlines propagated
- [ ] One configured, injected client per dependency
- [ ] Retries only on idempotent ops, with backoff + jitter and a cap
- [ ] Optional dependencies degrade gracefully
- [ ] Background jobs idempotent, bounded-retry, with a monitored DLQ
- [ ] Jobs carry their context explicitly; no ambient request state read in a worker
- [ ] Deduplication skips emit a metric
- [ ] Consumers can be paused without a deploy
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
- [ ] No real clock or real network in tests; no `sleep()`
