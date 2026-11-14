# Probes

How to run the four audit passes, delegated or inline, and the contract their findings have
to satisfy to be worth merging.

## When to delegate

Delegate when one pass means reading dozens of files and only the conclusion is needed back.
Run inline when the project is small enough that a cold agent would spend most of its turn
rediscovering what the main session already knows.

Check that a subagent tool exists before planning around it. Where there is none, run the
same four passes in the same order in the main session. The order matters more than the
parallelism: the scan feeds the probes, and the probes feed the ranking.

Never run more than these four. An audit that spawns an agent per checklist item costs more
than it returns and produces findings nobody can reconcile.

## The finding schema

Every probe returns a list of findings in this shape and nothing else. A finding missing
`evidence` is dropped during the merge rather than reported with a caveat, because a
plausible unverified claim is the one thing an audit cannot afford to emit.

```json
{
  "claim": "Product list issues one query per row",
  "evidence": "app/Http/Controllers/ProductController.php:42, query log shows 51 SELECTs for 50 rows",
  "cost": "Page takes 2.3s with 50 products and degrades linearly",
  "fix": "Eager load the category relation",
  "severity": "blocker | high | medium | low",
  "confidence": "measured | read-the-code"
}
```

`confidence` is not decoration. `measured` means a command was run and its output is quoted
in `evidence`. `read-the-code` means the probe inferred it from source and it is a
hypothesis, which the main session either confirms or drops. Probes that cannot tell the
difference will report both as fact.

## The four probes

Each prompt is written to be sent as-is. Fill the bracketed parts from the scan output, so
no probe spends its first turn working out the stack.

### 1. Payload and delivery

```text
Audit this [STACK] app for payload and delivery defects. Read only, make no edits.

Build output is at [PATH]. Run the bundle and image commands in
skills/remove-slop/references/measurement.md and quote what they printed.

Report on: total and per-route JavaScript against the budget in that file, code splitting,
render-blocking third-party scripts, fonts loaded from another origin, images that are not
WebP or AVIF or are far larger than the slot they render in, missing compression, missing
cache headers on static assets, and declared dependencies that are never imported.

If `frontend-practices` is available, review against it.

Return findings in the schema in skills/remove-slop/references/probes.md. Every finding
needs a file and line or a quoted command output. Report at most 10, ranked by what the user
loses.
```

### 2. Data access

```text
Audit this [STACK] app's data access. Read only, make no edits.

Report on: N+1 queries, confirmed by comparing query counts at two different row counts;
list endpoints with no pagination; queries selecting every column to use a few; missing
indexes on columns used in WHERE, JOIN and ORDER BY; connection pooling; and slow work done
inside the request that belongs on a queue.

If `database-practices` and `backend-practices` are available, review against them.

Return findings in the schema in skills/remove-slop/references/probes.md. State the query
count or the plan output you observed. Mark anything you inferred without running a query as
read-the-code. Report at most 10, ranked by what the user loses.
```

### 3. Client behaviour

```text
Audit this [STACK] app's client behaviour. Read only, make no edits.

Report on: fetches with no loading state, content that arrives without reserved space, error
states that show no next step, missing empty states, the same data fetched more than once per
page load, search or autocomplete with no debounce, optimistic updates with no rollback,
images below the fold that are not lazy, forms that can be submitted twice, and model
responses that do not stream.

If `frontend-practices` is available, review against it.

Return findings in the schema in skills/remove-slop/references/probes.md. Name the component
and line for each. Report at most 10, ranked by what the user loses.
```

### 4. Exposure

```text
Audit this [STACK] app for exposure. Read only, make no edits. Report, do not fix.

Run the credential grep in skills/remove-slop/references/measurement.md against the build
output, not the source.

Report on: credentials reachable from the browser; a hosted-database public key with no
row-level rules behind it; endpoints that trigger generation, email or payment with no rate
limit; stack traces or framework error pages shown to users; debug mode on; source maps
served in production; wildcard CORS with credentials; and any .env file in the git history.

If `security-practices` is available, review against it.

Return findings in the schema in skills/remove-slop/references/probes.md. Quote the file and
line or the command output. Anything confirmed here is a blocker, so do not report it unless
you verified it.
```

## Merging

- **Deduplicate by cause, not by wording.** One oversized bundle arrives from the payload
  probe as a budget breach and from the client probe as a slow first paint. Two findings
  with one fix is one finding.
- **Drop anything without evidence, and say how many you dropped.** The count is useful: four
  dropped findings means the probes could not run their commands, which is itself worth
  reporting.
- **Re-rank globally.** Each probe ranks within its own area and cannot see the others, so
  the severities arrive incomparable. A medium from the exposure probe usually outranks a
  high from payload.
- **Promote every confirmed exposure finding to the top.** Those are defects rather than
  degradations, and they are the ones that cannot wait for a tidy-up pass.
- **Carry `read-the-code` findings separately.** List them as worth checking rather than as
  defects. Promoting an unverified hypothesis into the report is how an audit loses the
  reader's trust for every other finding in it.
