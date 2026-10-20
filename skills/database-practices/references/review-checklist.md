# Review checklist: Database and Migrations Practices

The condensed form of the `database-practices` skill. Use it as a review pass over a diff, or as a
pull-request template. Each item maps to a numbered section of that skill's SKILL.md,
so read the section when an item needs its reasoning.

## Review checklist

**Schema**
- [ ] Types are the most restrictive that fit; money is decimal/integer; timestamps are UTC `TIMESTAMPTZ`
- [ ] `NOT NULL` unless nullability is meaningful and justified
- [ ] Foreign keys present with an explicit `ON DELETE` action
- [ ] Unique constraints enforce every real-world uniqueness rule
- [ ] `CHECK` constraints encode domain rules
- [ ] Primary key is a surrogate, not a natural key; not exposed if sequential
- [ ] `created_at` / `updated_at` present; naming conventions followed

**Indexes**
- [ ] Every foreign key indexed
- [ ] Indexes exist for hot `WHERE` / `JOIN` / `ORDER BY` paths, composite order correct
- [ ] No redundant or unused indexes added
- [ ] Query plan verified with `EXPLAIN ANALYZE`; no unexpected sequential scans
- [ ] No index-defeating predicates (function on column, leading wildcard, type mismatch)

**Queries**
- [ ] Parameterized; no string-built SQL; dynamic identifiers allow-listed
- [ ] No `SELECT *`; result sets bounded by `LIMIT`
- [ ] No N+1; batched or eager-loaded
- [ ] Keyset pagination for large or user-facing lists, with a unique tiebreaker
- [ ] Batch loops that mutate their own filter column iterate by key, not offset
- [ ] Queries expecting one row fail loudly on two
- [ ] Restricted column lists still include the keys relations need
- [ ] Aggregation done in the database

**Transactions**
- [ ] Scoped to one logical operation; no I/O inside
- [ ] Read-modify-write replaced by an atomic update or explicit lock
- [ ] Isolation level adequate for the invariant; serialization failures retried
- [ ] Consistent lock ordering

**Migrations**
- [ ] Versioned, immutable, one logical change, reviewed
- [ ] Compatible with the previous release running concurrently (expand/contract)
- [ ] Tested against production-scale data
- [ ] `CREATE INDEX CONCURRENTLY`; constraints added `NOT VALID` then validated
- [ ] `lock_timeout` and `statement_timeout` set
- [ ] Backfills batched, resumable, run out-of-band
- [ ] Destructive changes isolated, preceded by a verified backup and a wait period
- [ ] Rollback plan stated and tested
- [ ] Squashing, if used, applied only to migrations that ran everywhere

**Operations**
- [ ] Backup restore verified within the last drill window
- [ ] Application DB user is least-privilege
- [ ] Connection pool sized against database limits
- [ ] Slow queries, replication lag, and connection saturation monitored
- [ ] No non-production environment pointed at production data
- [ ] Destructive commands refuse to run in production without an explicit override
