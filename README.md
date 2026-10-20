# Agents Playbook

Engineering standards packaged as Claude Code skills, so they load when the work calls for them
instead of sitting in every session's context.

Most "best practices" documents are written to be agreed with. These are written to be
**followed**: every rule is imperative, scoped to a trigger ("when you are doing X..."), and
paired with the reason it exists, so an agent can tell when a rule applies and when it
legitimately does not.

## Install

```
/plugin marketplace add omarchouman/agents-playbook
/plugin install agents-playbook
```

Nothing else to configure. Each skill declares when it applies and loads itself.

## What's in it

| Skill | Triggers on | Covers |
|---|---|---|
| `frontend-practices` | Components, pages, forms, styling, client state | Component boundaries, state placement, effect cleanup, the four async states, forms, accessibility, performance, layout shift, design tokens |
| `backend-practices` | Endpoints, services, handlers, jobs, queues | API contracts and HTTP semantics, boundary validation, error contracts, layering, transactions, idempotency, resilient calls, background work, caching, observability |
| `database-practices` | Migrations, schema, queries, indexes | Types and constraints, indexing, query performance, keyset pagination, lost-update prevention, zero-downtime migrations, backfills, destructive changes |
| `security-practices` | Auth, permissions, user input, uploads, secrets, PII | AuthN and sessions, object-level authorization, the injection classes, SSRF, uploads, secrets, headers, audit logging, data protection, supply chain |
| `git-practices` | Commits, messages, branches, pull requests, rebases | Atomic commits, message form, branching models, history rewriting, merge strategy, force-push safety, PR size and review, repo hygiene, recovery, protection |
| `playbook-builder` | "Codify how we work", "write our standards" | Builds a playbook for **your** repo: detects conventions, interviews for what it cannot detect, writes rules agents follow |

The first five are general practice. `playbook-builder` is the one that makes this yours.

## Two things this gives you

**Standards that trigger themselves.** Writing a migration pulls in the migration rules,
including the safe-versus-dangerous operation list that prevents table-locking outages. Touching
auth pulls in object-level authorization. You don't have to remember to ask.

**A way to capture your own conventions.** `playbook-builder` interviews you and writes a
playbook for your codebase. It reads the repo first, so it asks about what no amount of reading
reveals: what "done" means here, when an agent should stop and ask instead of deciding, which
parts of the codebase are dangerous, and what looks wrong but is deliberate.

Try it with:

> Use playbook-builder to write an engineering playbook for this repo.

## Reviewing with these

Every practice skill ships a condensed checklist at
`skills/<name>/references/review-checklist.md`, loaded on demand rather than with the rules.
Useful as a PR template, or handed to a review agent:

> Review this diff against the review checklist in the `backend-practices` skill. Report only
> violations, with file and line.

## Using them without Claude Code

Each skill is plain Markdown with a short YAML header. Nothing needs the plugin system.

For **Codex, Cursor, or any agent that reads a project file**, point at the skills you want from
`AGENTS.md` or equivalent:

```markdown
- UI work → agents-playbook/skills/frontend-practices/SKILL.md
- API work → agents-playbook/skills/backend-practices/SKILL.md
- Schema, query or migration work → agents-playbook/skills/database-practices/SKILL.md
- Auth, user input, secrets or PII → agents-playbook/skills/security-practices/SKILL.md
- Before any commit or pull request → agents-playbook/skills/git-practices/SKILL.md
```

Or vendor the whole thing:

```bash
git submodule add https://github.com/omarchouman/agents-playbook.git docs/playbook
```

Prefer this over a `CLAUDE.md` import of all five: imports load every session whether relevant or
not, which is the cost the skill format exists to avoid.

## Layout

```
.claude-plugin/
  plugin.json           plugin manifest and skill registry
  marketplace.json      lets the repo be added as a marketplace directly
skills/
  <name>/
    SKILL.md            the rules; frontmatter description controls triggering
    references/         loaded on demand, not with the rules
```

## Conventions used in these documents

- **Rules are imperative.** "Return 409 on conflict", not "you might consider 409".
- **Every rule states its cost.** A rule you can't justify is a rule you can't override
  responsibly. Where a rule has a legitimate exception, it says so.
- **Examples are illustrative, not prescriptive.** Snippets appear in whatever language makes the
  point clearest. Translate the idea, not the syntax.
- **"Prefer X" means X unless you can name the reason.** "Never X" means never: the cases where
  it seems necessary are usually a design problem one level up.
- **No rule that a tool could enforce instead.** A linter that cannot be ignored beats a
  document that can.

## Contributing

These are opinionated by design. If a rule is wrong, or right only in some contexts, open an
issue with the counter-case. A rule that survives a real counter-example is worth more than one
that was never tested.

## License

MIT. See [LICENSE](LICENSE).
