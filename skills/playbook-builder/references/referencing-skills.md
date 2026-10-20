# Referencing general practice skills

Read this at step 4 of the `playbook-builder` skill, when writing the area table or deciding
whether to cite a general practice skill at a gate.


A playbook sits alongside whatever general standards the team already has available, including
the `frontend-practices`, `backend-practices`, `database-practices`, `security-practices` and
`git-practices` skills in this plugin. Deciding what to say about them is its own judgment, and
the obvious answer is wrong.

**Do not restate a skill's trigger conditions.** Every skill carries a description saying when
it applies, and that description is the mechanism that loads it. Writing "for anything touching
auth, use `security-practices`" duplicates text that already exists, costs context in every
session, and breaks silently when a skill is renamed. If the description works, the skill
arrives without the playbook's help; if it does not, fix the description rather than papering
over it from here.

**Reference a skill only where you are changing what would otherwise happen.** Four cases earn
their place:

- **Making it mandatory.** A description invites the agent to judge relevance. A gate can
  remove the judgment: "Gate 4 does not close until the relevant practice skill has been read
  and the change verified against it." Use this for whatever the team treats as
  non-negotiable, not for everything.
- **Binding it to a moment.** Descriptions trigger on subject matter. A gate triggers on
  position in the pipeline, which is information a description cannot express: before writing
  code, before the review gate closes, after a contract changes.
- **Resolving a conflict.** Where the team's convention contradicts the general skill, say
  which wins and why. This is the most valuable sentence in the whole playbook, because it is
  the one thing that exists nowhere else, and without it an agent will follow the general rule
  and be confidently wrong.
- **Narrowing to a section.** "Apply `security-practices` §3 to every endpoint that takes an
  id" is actionable in a way that pointing at an entire skill is not.

The natural home is a table at the implementation gate, mapping each area of the codebase to
what governs it, so one lookup answers "what should I have read before touching this":

```markdown
| Area | Team conventions | General practice |
|---|---|---|
| `api/` | [`docs/api-conventions.md`](docs/api-conventions.md) | `backend-practices` |
| `web/` | none yet | `frontend-practices` |
| `db/migrations/` | [`docs/db.md`](docs/db.md) | `database-practices` (§6 before any migration) |
| anything with auth or user input | [`docs/authz.md`](docs/authz.md) | `security-practices` |
```

**Make references additive, never load-bearing.** A playbook that cites skills is committed to
a shared repository, where a teammate may not have them installed. Do not solve that by hedging
at each site: "if `security-practices` is available, use it" tells an agent nothing about what
to do when it is not, so the rule quietly evaporates for exactly the reader who needed it most.

Write the rule so it stands on its own and let the pointer add depth:

```markdown
✗ If `security-practices` is available, follow it for authorization.

✓ **Every endpoint checks ownership of the object, not just the route.** Returning another
  tenant's row to an authenticated caller is the most common serious bug in this codebase.
  `security-practices` §3 has the full treatment.
```

The second works whether or not the skill is installed, because the sentence carrying the rule
does not depend on it. The first is a conditional wrapped around the only content.

Then **declare the dependency once, at the top**, rather than at every reference:

```markdown
## Expected tooling

General practice comes from the `agents-playbook` plugin: `/plugin install agents-playbook`.
If a referenced skill is not in your available skills, say so once and carry on. Every rule
below stands without it; what you lose is the reasoning behind the pointer, not the rule.
```

That tells an agent what to do in the absent case, which "if available" does not, and it keeps
the hedge in one place instead of multiplying it across the file.
