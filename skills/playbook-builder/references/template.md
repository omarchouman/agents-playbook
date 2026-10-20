# Playbook template and worked example

Read this at step 4 of the `playbook-builder` skill, when you are ready to write.

## Skeleton

Delete every section you have nothing real to put in. An empty heading invites someone to
fill it with filler, and filler is what makes playbooks unreadable.

```markdown
# <Project> engineering playbook

How work gets done in this repository. Rules here exist because getting them wrong has cost
us something. General language and framework practice lives in the agents-playbook skills;
this document covers only what is specific to us.

## Stop and ask

Hard limits. Do not decide these alone.

- **<Action>.** <Why it needs a human.>

## Definition of done

A task is finished when all of these are true:

- [ ] <Condition, with the command that proves it.>

## Verifying your work

| What | Command | Takes |
|---|---|---|
| Typecheck | `<cmd>` | <time> |
| Unit tests | `<cmd>` | <time> |
| Lint | `<cmd>` | <time> |

<Anything that cannot be verified locally, and what to do instead.>

## How a task travels

1. <Where work arrives from.>
2. <Branch from what, named how.>
3. <Write the test first, or not, and where tests live.>
4. <Commit convention.>
5. <Open a PR against what, with what in the description, reviewed by whom.>
6. <What happens at merge.>

## Scope

- **<Fix it / note it / open an issue / leave it>** when you notice an unrelated problem.
- <Whether drive-by refactoring is welcome.>

## Standards

### <Area, e.g. API handlers>

- **<Imperative claim.>** <Trigger, then reason or cost.>

### <Area, e.g. Data access>

- **<Imperative claim.>** <Trigger, then reason or cost.>

## Deliberate oddities

Things that look wrong and are not. Do not "fix" these.

- **<The oddity.>** <Why it is that way.>

## Exemplars

- `<path>` is the pattern to copy for <kind of work>.
```

## Worked example

Rules at the quality bar to aim for. Each names a trigger, gives an instruction, and states a
consequence that lets a reader judge when an exception is legitimate.

```markdown
## Stop and ask

- **Adding a runtime dependency.** Our bundle budget is 180KB gzipped and we are at 171KB.
  Any addition needs a conversation about what comes out.
- **Changing a response shape on `/v2/*`.** Three mobile releases are live at any time and
  cannot be force-upgraded, so a removed field breaks clients for about six weeks.
- **Any migration touching `events`.** It holds 2.1 billion rows. A migration that is instant
  in development locks the table for hours here. Bring the plan first.

## Definition of done

- [ ] `pnpm verify` passes (typecheck, lint, unit)
- [ ] New behaviour has a test that fails without the change
- [ ] Anything user-visible has a changelog entry under `## Unreleased`
- [ ] Migrations tested against a restored production snapshot, not a seeded dev database

## Standards

### API handlers

- **Handlers parse, delegate, and format. Nothing else.** Business logic in a handler cannot be
  tested without HTTP and gets duplicated the moment a second caller appears. Logic belongs in
  `src/domain/`, which has no framework imports.
- **Every handler returns a `Result`, never throws for expected failures.** Our error middleware
  maps `Result` to the error envelope; a thrown exception bypasses it and returns a bare 500
  with no request id, which makes the support ticket unanswerable.

### Data access

- **Read through a repository in `src/data/`, never the ORM directly from domain code.** We
  swapped the ORM once already and the repositories were the only reason it took a week.
- **Any query on `events` needs `tenant_id` in the WHERE clause.** It is the partition key.
  Without it the query scans every partition, which has taken the database down twice.

## Deliberate oddities

- **`src/legacy/pricing.ts` duplicates logic in `src/domain/pricing.ts`.** The legacy copy is
  frozen because invoices issued before 2025-04 must reproduce byte-identically for audit.
  Change the new one only.
- **`useLayoutEffect` in `ScrollRestore.tsx` is intentional.** `useEffect` paints at the old
  scroll position first and the jump is visible.
```

Note what the example does not contain: no quote style, no import ordering, no naming
conventions. The formatter and linter own those. Every line present is something no tool can
check and something that has already cost the team.
