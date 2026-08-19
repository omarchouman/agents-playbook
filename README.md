# Agents Playbook

Language-agnostic engineering best practices, written to be read by coding agents
(Claude Code, Codex, Cursor, and friends) as much as by humans.

Most "best practices" documents are written to be agreed with. These are written to be
**followed**: every rule is imperative, scoped to a trigger ("when you are doing X..."),
and paired with the reason it exists, so an agent can tell when the rule applies and when
it legitimately does not.

## The playbooks

| File | Covers |
|---|---|
| [`frontend-and-ui.md`](frontend-and-ui.md) | Component design, state, forms, accessibility, performance, styling, client-side data |
| [`backend-and-api.md`](backend-and-api.md) | API contracts, layering, errors, concurrency, background work, observability, testing |
| [`database-and-migrations.md`](database-and-migrations.md) | Schema design, indexing, query performance, transactions, zero-downtime migrations |
| [`security.md`](security.md) | AuthN/AuthZ, input handling, secrets, transport, dependencies, logging, incident basics |

They overlap deliberately at the seams. Validation appears in both backend and security,
and migrations appear in both database and backend, because that is where bugs live.

## How to use these

### With Claude Code

Reference them from your project's `CLAUDE.md`:

```markdown
## Engineering standards

Before writing code, read the playbook relevant to the layer you are touching:

- UI/component work → @agents-playbook/frontend-and-ui.md
- API/service work → @agents-playbook/backend-and-api.md
- Schema/query/migration work → @agents-playbook/database-and-migrations.md
- Anything touching auth, user input, secrets, or PII → @agents-playbook/security.md
```

Or vendor them in directly:

```bash
git submodule add https://github.com/omarchouman/agents-playbook.git docs/playbook
```

### With Codex / AGENTS.md

Point at them from `AGENTS.md` at the repo root, or paste the relevant sections inline;
Codex reads `AGENTS.md` from the working directory upward.

### As a review checklist

Each playbook ends with a **Review checklist**, a condensed, scannable version of the
whole document. Use it in PR templates, or hand it to a review agent:

> Review this diff against the "Review checklist" section of `backend-and-api.md`.
> Report only violations, with file and line.

## Conventions used in these documents

- **Rules are imperative.** "Return 409 on conflict", not "you might consider 409".
- **Every rule states its cost.** A rule you can't justify is a rule you can't override
  responsibly. Where a rule has a legitimate exception, it says so explicitly.
- **Examples are illustrative, not prescriptive.** Snippets appear in whatever language
  makes the point clearest. Translate the idea, not the syntax.
- **"Prefer X" means X unless you can name the reason.** "Never X" means never: the
  cases where it seems necessary are usually a design problem one level up.

## Contributing

These are opinionated by design. If a rule is wrong, or right only in some contexts, open
an issue with the counter-case. A rule that survives a real counter-example is worth more
than one that was never tested.

## License

MIT
