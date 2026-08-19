# Database and Migrations Practices

Applies to relational databases primarily (PostgreSQL, MySQL, SQL Server, SQLite), with a
section on non-relational stores. Examples use PostgreSQL syntax; translate as needed.

**Read this before:** designing a table, adding a column or index, writing a non-trivial
query, or shipping any migration.

---

## 1. Core principles

1. **The schema outlives the application.** Code gets rewritten; data gets migrated. A bad
   schema is the most expensive mistake in this document to reverse.
2. **The database is the last line of defense for data integrity.** Application checks
   race, get bypassed by scripts, and get forgotten in the second service. Constraints
   don't.
3. **Migrations run against production while it is serving traffic.** Every migration must
   be safe to apply to a live, large table with old code still running.
4. **You cannot un-lose data.** Destructive operations get a deliberate, separate,
   reversible-by-backup process.

---

## 2. Schema design

### 2.1 Types

- **Choose the most restrictive type that fits.** The type system is free validation.
- **Never store money in a float.** Use `NUMERIC(19,4)` / `DECIMAL`, or integer minor units
  (cents) with the currency stored alongside. Binary floating point cannot represent 0.10.
- **Store timestamps as `TIMESTAMPTZ` (UTC).** Never a naive local timestamp, never a
  string, never a Unix integer in a column you'll want to range-query in SQL. Store the
  user's timezone separately when you need to render or schedule in local time.
- **Prefer native types over strings**: `BOOLEAN`, `UUID`, `INET`, `JSONB`, `DATE`,
  `INTERVAL`, arrays, enums. `VARCHAR` holding `"true"` is a bug generator.
- **Always bound `VARCHAR`** — but bound it generously and for a real reason. (In
  PostgreSQL, `TEXT` with a `CHECK` length is equivalent and easier to change.)
- **Choose your primary key deliberately:**
  - `BIGINT` identity — smallest, fastest, but sequential and enumerable. Never expose it
    publicly (see `backend-and-api.md` §2.1).
  - `UUIDv7` / `ULID` — time-sortable, safe to expose, index-friendly. **Preferred default
    for new systems.**
  - `UUIDv4` — random. Safe to expose, but random insertion order causes B-tree page splits
    and index bloat on large tables. Avoid as a clustered/primary key at scale.
  - **Never use a natural key** (email, username, SKU) as a primary key. Business meaning
    changes; primary keys shouldn't.
- **Enums**: a lookup table with a foreign key is the most flexible (values can carry
  metadata and change without a migration). A native enum is faster but adding/removing
  values needs DDL. A `VARCHAR` with a `CHECK` constraint is a reasonable middle ground.
  Choose one; never let an unconstrained string hold a fixed set of values.

### 2.2 Constraints

Every one of these is a bug that becomes impossible:

- **`NOT NULL` by default.** Make nullability the exception you can justify. `NULL` means
  "unknown/not applicable" — never use it for "empty", "zero", or "false".
- **`FOREIGN KEY` on every reference**, with an explicit `ON DELETE` action:
  - `RESTRICT` (default choice) — refuse to orphan.
  - `CASCADE` — only when the child genuinely has no life without the parent, and you have
    thought about how many rows one delete could touch.
  - `SET NULL` — only where the column is nullable and that means something.
- **`UNIQUE` on anything that must be unique.** Application-level "check then insert" is a
  race condition, always. Let the constraint fail and handle the error.
- **`CHECK` constraints for domain rules**: `amount > 0`, `ends_at > starts_at`,
  `status IN (…)`, `discount BETWEEN 0 AND 100`.
- **`DEFAULT` for values that should never be absent**: `created_at DEFAULT now()`,
  `status DEFAULT 'pending'`.

```sql
CREATE TABLE subscriptions (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  account_id    UUID NOT NULL REFERENCES accounts(id) ON DELETE RESTRICT,
  plan          TEXT NOT NULL REFERENCES plans(code),
  status        TEXT NOT NULL DEFAULT 'trialing'
                  CHECK (status IN ('trialing','active','past_due','canceled')),
  amount_cents  BIGINT NOT NULL CHECK (amount_cents >= 0),
  currency      CHAR(3) NOT NULL,
  starts_at     TIMESTAMPTZ NOT NULL,
  ends_at       TIMESTAMPTZ,
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
  CHECK (ends_at IS NULL OR ends_at > starts_at)
);
-- Only one active subscription per account.
CREATE UNIQUE INDEX ON subscriptions (account_id) WHERE status = 'active';
```

### 2.3 Normalization and denormalization

- **Normalize first (3NF).** Duplicated data drifts out of sync; that is a correctness
  problem, not a performance trade-off.
- **Denormalize only with measurements and a maintenance plan.** A cached `comment_count`
  must be updated by a trigger or a transaction that also writes the comment — never by
  hopeful application code in one of the three places that inserts comments.
- **Use `JSONB` for genuinely schemaless data** — third-party payloads, user-defined fields,
  event bodies. Do **not** use it to avoid writing a migration: you lose type checking,
  constraints, and query planning, and you will end up validating in five places.
  If you query or filter on a field regularly, promote it to a column.

### 2.4 Conventions

Pick one convention per repo and never mix:

- `snake_case` for tables and columns; plural table names (`orders`, `order_items`).
- Foreign keys named `<singular_table>_id` (`account_id`).
- Booleans read as assertions: `is_active`, `has_verified_email`.
- Timestamps end in `_at`; dates in `_on`; durations carry units (`timeout_seconds`).
- Every table gets `created_at` and `updated_at`.
- Never name a column with a reserved word (`order`, `user`, `group`, `type`).

### 2.5 Deletion

- **Prefer soft delete for anything user-visible or referenced elsewhere**
  (`deleted_at TIMESTAMPTZ`), but understand the cost: every query must filter it, and
  unique constraints must become partial (`… WHERE deleted_at IS NULL`). Missing that filter
  in one query is the classic soft-delete leak.
- **Hard-delete transient, high-volume, or legally-must-be-erased data.** Retention and
  erasure obligations (GDPR "right to erasure") override convenience — see `security.md` §8.
- **Consider an archive table** rather than either, when history matters but volume doesn't
  belong in the hot table.

---

## 3. Indexing

An index is a permanent write cost and storage cost paid to make some reads fast. Both
sides matter.

### 3.1 What to index

- **Every foreign key column.** Most databases (including PostgreSQL) do **not** index them
  automatically, and an unindexed FK makes parent deletes and joins table-scan.
- **Columns in `WHERE`, `JOIN`, `ORDER BY`, and `GROUP BY`** on queries that matter.
- **Composite indexes follow the leftmost-prefix rule**: an index on `(a, b, c)` serves
  `WHERE a`, `WHERE a AND b`, and `WHERE a AND b AND c` — but not `WHERE b`. Order columns
  by: equality predicates first, then range predicates, then sort columns.
- **Partial indexes for skewed queries** — far smaller and cheaper:
  ```sql
  CREATE INDEX ON jobs (created_at) WHERE status = 'pending';
  ```
- **Covering indexes** (`INCLUDE`) let the database answer from the index alone, avoiding
  the heap fetch. Useful for hot, narrow read paths.

### 3.2 What not to index

- **Low-cardinality columns alone** (a boolean, a 3-value status) — usually useless as a
  standalone index; useful as the *leading* column of a composite or as a partial index
  predicate.
- **Duplicate and redundant indexes.** `(a)` is redundant when `(a, b)` exists. Audit
  periodically and drop unused indexes — they cost every write.
- **Everything, reflexively.** Ten indexes on a write-hot table will dominate its write
  latency.

### 3.3 Things that silently disable an index

```sql
WHERE lower(email) = $1          -- ✗ unless you index lower(email)
WHERE created_at::date = $1      -- ✗ use a range: created_at >= $1 AND < $1 + 1 day
WHERE status != 'done'           -- ✗ negation is rarely selective
WHERE name LIKE '%foo'           -- ✗ leading wildcard; use a trigram/full-text index
WHERE user_id = $1::text         -- ✗ type mismatch forces a cast on the column
```

**Verify with `EXPLAIN (ANALYZE, BUFFERS)`** — never assume an index is being used. A
sequential scan on a large table in a hot query is the finding you're looking for.

---

## 4. Query practices

### 4.1 Correctness and safety

- **Always use parameterized queries.** Never build SQL by string concatenation with user
  input — this is SQL injection, the highest-impact and most preventable vulnerability in
  this document. See `security.md` §4.2. When a table or column name must be dynamic,
  allow-list it against a fixed set; parameters cannot bind identifiers.
- **Never `SELECT *` in application code.** It breaks when columns are added, transfers data
  you don't need, prevents covering-index-only scans, and hides the fact that you're pulling
  a 2MB blob column on every request.
- **Every query that can return many rows needs a `LIMIT`.**
- **`UPDATE` and `DELETE` must have a `WHERE` clause.** Review these specifically — run the
  equivalent `SELECT` first and confirm the row count.

### 4.2 Performance

- **N+1 queries are the most common backend performance bug.** One query for a list plus one
  per row. Fix by eager-loading (join or a second batched `WHERE id = ANY($1)`), not by
  caching. Assert query counts in tests on hot paths.
- **Filter and aggregate in the database, not in application memory.** Pulling 100k rows to
  count them in code is orders of magnitude slower and will eventually OOM.
- **Batch writes.** One `INSERT` with 1,000 rows beats 1,000 `INSERT`s by a wide margin.
  Batch, but bound the batch size — a single 100k-row statement creates its own problems.
- **Prefer `EXISTS` to `COUNT(*) > 0`** — it can stop at the first match.
- **Beware `COUNT(*)` on large tables** for pagination totals; it scans. Use an approximate
  count, a cached count, or cursor pagination that doesn't need a total.
- **Stream or chunk large result sets** with a server-side cursor. Never materialize a full
  table export in memory.

### 4.3 Pagination

**Offset pagination** is fine for small, static data and admin screens:
```sql
SELECT … ORDER BY created_at DESC LIMIT 20 OFFSET 4000;   -- scans 4020 rows
```
It degrades linearly with depth and **skips or duplicates rows** when data changes between
page requests.

**Keyset (cursor) pagination** is constant-time and stable:
```sql
SELECT … FROM orders
WHERE (created_at, id) < ($1, $2)     -- last row of the previous page
ORDER BY created_at DESC, id DESC
LIMIT 20;
```
Include a unique tiebreaker (`id`) in both the sort and the cursor, or rows with identical
timestamps will be skipped. Index on `(created_at DESC, id DESC)`.

**Use keyset for anything user-facing, infinite-scrolling, large, or frequently written.**

---

## 5. Transactions

- **Wrap a single logical business operation**, no more and no less.
- **Keep them short. Never perform I/O inside** — no HTTP calls, no email, no queue
  publishes. A remote timeout inside a transaction holds locks for its full duration.
- **Know your isolation level and its anomalies.** Most databases default to `READ
  COMMITTED`, which permits non-repeatable reads and phantoms. If your logic depends on
  reading a value and acting on it, `READ COMMITTED` will not protect you — use an explicit
  lock, an atomic conditional update, or `SERIALIZABLE` (and be ready to retry on
  serialization failure).
- **Prevent lost updates explicitly.** Read-modify-write across a round trip is a race:
  ```sql
  -- ✗ racy
  SELECT balance FROM accounts WHERE id = $1;   -- app computes balance - 10
  UPDATE accounts SET balance = $2 WHERE id = $1;

  -- ✓ atomic
  UPDATE accounts SET balance = balance - 10
  WHERE id = $1 AND balance >= 10;              -- check rows affected
  ```
- **Avoid deadlocks by acquiring locks in a consistent order** across all code paths (e.g.
  always the lower account id first).
- **Retry serialization/deadlock failures** with backoff — they are expected, not
  exceptional. Only retry when the transaction is safe to replay.
- **Never hold a transaction open across a user interaction.** Use optimistic concurrency
  (a `version` column) instead — see `backend-and-api.md` §6.

---

## 6. Migrations

### 6.1 Non-negotiables

- **Every schema change is a versioned migration file in version control.** No manual
  production DDL, ever. If you ran something by hand to fix an incident, write the migration
  immediately afterward so environments don't diverge.
- **Migrations are append-only and immutable once merged.** Never edit a migration that has
  run anywhere. Fix forward with a new one.
- **One logical change per migration**, with a descriptive name and timestamped ordering.
- **Test every migration against a production-shaped copy** — the same data volume, the same
  indexes. A migration that takes 50ms on 100 rows can take 40 minutes and lock a table on
  100 million.
- **Separate schema migrations from data backfills.** Backfills are long-running, batched,
  resumable, and often better run as a job than as a migration that blocks deploys.
- **Know your rollback.** Either a tested `down` migration, or an explicit, documented
  "forward-only, restore from backup if this goes wrong". Untested `down` migrations are
  false comfort.

### 6.2 Zero-downtime: the expand/contract pattern

During a deploy, old and new application code run **simultaneously**. Every migration must
be compatible with both. This is the single most important operational rule here.

The pattern, in three deploys:

| Phase | Migration | Code |
|---|---|---|
| **Expand** | Add the new structure, nullable/defaulted, alongside the old | Write to both, read from old |
| **Migrate** | Backfill in batches | Read from new, keep writing both |
| **Contract** | Drop the old structure, add `NOT NULL`/constraints | Read and write new only |

**Renaming a column** is not one migration — it is: add `new_name` → dual-write → backfill →
switch reads → stop writing `old_name` → drop `old_name`. Any shortcut breaks in-flight
requests during the deploy window.

### 6.3 Safe vs. dangerous operations

**Generally safe on a live table:**
- Adding a nullable column (with no volatile default)
- Adding a new table
- Adding an index **concurrently** (`CREATE INDEX CONCURRENTLY`, outside a transaction)
- Adding a constraint as `NOT VALID`, then `VALIDATE CONSTRAINT` separately
- Widening a type (`INT` → `BIGINT` is *not* free in most engines — check yours)

**Dangerous — will lock, rewrite, or break running code:**
- Dropping or renaming a column or table (breaks old code instantly; `SELECT *` and ORMs
  will fail)
- Adding a `NOT NULL` column with a default (rewrites the table on older engines)
- Adding a foreign key or `CHECK` without `NOT VALID` (full validation scan under lock)
- `CREATE INDEX` without `CONCURRENTLY` (blocks writes for the duration)
- Changing a column type (usually a full rewrite plus an `ACCESS EXCLUSIVE` lock)
- Any unbatched `UPDATE`/`DELETE` on a large table (long transaction, lock escalation,
  replication lag, bloat)

```sql
-- Adding a NOT NULL column safely:
ALTER TABLE users ADD COLUMN locale TEXT;                          -- 1. nullable, instant
UPDATE users SET locale = 'en' WHERE locale IS NULL                -- 2. batched backfill
  AND id IN (SELECT id FROM users WHERE locale IS NULL LIMIT 5000);
ALTER TABLE users ADD CONSTRAINT users_locale_nn                   -- 3. no full scan
  CHECK (locale IS NOT NULL) NOT VALID;
ALTER TABLE users VALIDATE CONSTRAINT users_locale_nn;             -- 4. no write lock
```

- **Always set a short `lock_timeout` (and `statement_timeout`) before DDL.** A migration
  that waits for a lock queues every subsequent query behind it and takes the site down.
  Failing fast and retrying is far safer:
  ```sql
  SET lock_timeout = '3s';
  SET statement_timeout = '30s';
  ```

### 6.4 Backfills

- **Batch them** (1k–10k rows), commit each batch, and sleep briefly between batches to let
  replication catch up.
- **Make them resumable and idempotent** — they will be interrupted.
- **Drive them off an indexed column** with a stable order, and log progress.
- **Run them out-of-band** for large tables, not inside the deploy's migration step.

### 6.5 Destructive changes

Dropping a column or table deserves its own ritual:

1. Confirm nothing reads it — grep the codebase, and check query logs / `pg_stat_statements`
   over a full business cycle.
2. Ship a release that stops writing it.
3. Wait long enough to roll back that release without needing the data (at least a full
   deploy cycle, often a week).
4. Take a verified backup.
5. Drop it in its own migration, separate from anything else.

**Never combine a destructive change with anything else in one migration.**

---

## 7. Operations

- **Backups are only real if you have restored one.** Schedule a periodic restore drill and
  measure how long it takes — that number is your actual RTO. Verify point-in-time recovery
  works and that the retention window meets your RPO.
- **Least-privilege database users.** The application user should not be able to `DROP` a
  table. Migrations run under a separate, more privileged user. Read replicas get a
  read-only user.
- **Connection pooling is mandatory**, sized against the database's connection limit — not
  against how many app instances you happen to run. Each connection has a real memory cost.
- **Monitor**: slow query log, replication lag, connection saturation, cache hit ratio, dead
  tuples/bloat, longest-running transaction, deadlock count, and disk headroom.
- **Reads on a replica are eventually consistent.** A write followed immediately by a read
  from a replica can miss it — route read-after-write to the primary.
- **Never point a test suite, script, or local environment at production.** Enforce it with
  separate credentials, and make the production DSN visibly distinct.
- **Seed and anonymize.** Development data comes from a generator or a scrubbed dump — never
  a raw production copy containing real personal data. See `security.md` §8.

---

## 8. Non-relational stores

Most of the above still applies; these are the differences that catch people out.

- **Document stores need a schema too** — it just lives in your application and is enforced
  by validation. Version your documents (`schema_version`) so you can migrate them lazily on
  read.
- **Design the model around your access patterns**, not around your entities. In key-value
  and wide-column stores, the query you need determines the key you choose, and adding a new
  access pattern later usually means a new index or a data rewrite.
- **Understand the consistency model you actually have.** "Eventually consistent" means a
  read can return stale data; design the UI and business logic for it, or use the store's
  strong-consistency option where correctness requires it.
- **Cross-document transactions are limited or absent.** Model together what must change
  together.
- **Set TTLs and eviction policies on caches deliberately**, and never treat a cache as a
  system of record — it can vanish entirely at any moment.
- **Redis specifics**: `KEYS` is O(n) and blocks the server — use `SCAN`. Set `maxmemory` and
  an eviction policy explicitly. Persistence is off or partial by default.

---

## 9. Anti-patterns

- Money in `FLOAT`/`DOUBLE`.
- Naive/local timestamps, or timestamps stored as strings.
- Nullable columns everywhere "just in case".
- Missing foreign keys, or missing indexes on foreign keys.
- Uniqueness enforced only in application code.
- `SELECT *` in application code.
- String-concatenated SQL.
- Offset pagination on a large, actively-written table.
- `COUNT(*)` on a large table for every page of results.
- An unbatched `UPDATE`/`DELETE` over millions of rows.
- Editing a migration that has already run somewhere.
- Renaming or dropping a column in a single deploy.
- `CREATE INDEX` without `CONCURRENTLY` on a live table.
- DDL with no `lock_timeout`.
- Backups that have never been restored.
- The application user having `DROP` privileges.
- A shared database written by multiple services (see `backend-and-api.md` §5.3).
- `JSONB` used to avoid designing a schema.

---

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

**Operations**
- [ ] Backup restore verified within the last drill window
- [ ] Application DB user is least-privilege
- [ ] Connection pool sized against database limits
- [ ] Slow queries, replication lag, and connection saturation monitored
- [ ] No non-production environment pointed at production data
