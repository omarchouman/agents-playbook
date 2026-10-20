---
name: playbook-builder
description: >-
  Build a custom engineering playbook that captures how a specific team wants work done in their
  codebase, and how a task gets from an issue to finished, then write it out as a skill, a
  CLAUDE.md section or a reference doc. Use this when the user wants to codify conventions,
  standards, a definition of done, review expectations, guardrails or a task workflow for agents
  to follow, including phrasings like "write up our engineering standards", "codify how we work",
  "make a playbook", "turn our conventions into a skill", "document how Claude should work in
  this repo", or "onboard an agent to our codebase". Also use it when an agent keeps making the
  same wrong call in a repo and the user wants that captured once instead of repeated in every
  prompt. It detects what the repository already states (stack, test and lint commands, commit
  and branch conventions, CI, existing agent instructions) and interviews only for what no
  amount of reading can reveal.
---

# Playbook Builder

A playbook is the standing answer to "how do we work here", written so an agent can act on it.
This skill produces one by reading the repository first and asking the user only what the
repository cannot tell you.

**Why most playbooks fail, and what to do differently.** Teams write a long document of
preferences, and agents ignore it. Three causes, each with a fix that shapes this whole process:

1. **It restates what tooling already enforces.** If the formatter sets quote style, writing
   "use single quotes" adds nothing and buys a maintenance liability. Fix: never write a rule a
   tool can enforce. Automate it instead and say so (§3).
2. **Rules have no trigger.** "Prefer composition" cannot be applied, because nothing says when.
   Fix: every rule names the situation that invokes it (§4).
3. **Rules have no reason.** An agent given an unexplained rule cannot tell a case the rule was
   built for from a case where it does harm, so it either over-applies or abandons it. Fix: every
   non-obvious rule carries its cost or consequence (§4).

The target is 20 to 40 real rules, not 200. A playbook competes for attention with the task
itself, and length is the enemy of being followed.

## When this is the wrong tool

Say so rather than building something nobody needs:

- **Fewer than about ten rules.** Put them directly in `CLAUDE.md`. A playbook is overhead until
  there is enough to organize. This is not in tension with the placement guidance in §5: that
  section describes how to split a playbook once it is large enough to need splitting, and a
  small repo arriving at §5 with a dozen rules should put all of them in `CLAUDE.md` and stop.
- **The user wants one specific thing fixed now.** Fix it. A playbook is for recurring decisions.
- **Generic best practices with nothing team-specific.** Point them at the `frontend-practices`,
  `backend-practices`, `database-practices`, `security-practices` and `git-practices` skills,
  which already cover the general case. This skill is for what makes *their* repo different.

## The process

Detect, confirm, interview, draft, place, then test it on real work. Do not skip detection: the
interview is short and credible only because detection did the boring half first, and asking a
user for their test command when `package.json` states it reads as not having looked.

## 1. Detect

Run these before asking anything. For ecosystem-specific detail (Node, Python, Go, Rust, Ruby,
PHP, Java, .NET), read `references/detection.md`.

```bash
# What already instructs agents here, which you are extending rather than replacing
ls -a | grep -iE 'claude|agents|cursor|copilot|windsurf|\.rules'
find . -maxdepth 3 -name 'CLAUDE.md' -o -maxdepth 3 -name 'AGENTS.md' | grep -v node_modules

# Stack, scripts, and the real verification commands
ls package.json pyproject.toml go.mod Cargo.toml Gemfile composer.json pom.xml 2>/dev/null

# Enforcement already in place: anything here must NOT become a written rule
ls -a | grep -iE 'eslint|prettier|biome|ruff|rubocop|pint|editorconfig|pre-commit|lefthook|husky'
ls .github/workflows .gitlab-ci.yml Jenkinsfile 2>/dev/null

# Conventions as practised, not as claimed
git log --format='%s' -200
git log --format='%an' -200 | sort | uniq -c | sort -rn | head
git branch -r --format='%(refname:short)' | head -30
ls .github/pull_request_template.md .github/CODEOWNERS docs/ 2>/dev/null

# Test and source layout, so the playbook can say where new code goes
find . -type d \( -name test -o -name tests -o -name spec -o -name __tests__ \) \
  -not -path '*/node_modules/*' | head
```

Read the commit log for what is *practised*. If 80% of subjects carry a `fix:` prefix, that is
the convention whatever anyone says. If the log is a wall of "update", that is a finding worth
raising, not a convention to encode.

**When detection comes up empty.** Documentation repos, config and infrastructure repos, design
systems, content sites and fresh projects have no manifest, no test runner and no linter, so most
of the commands above return nothing. That is itself the most useful finding: a repo with no
mechanical enforcement has every convention living in someone's head, which is the strongest
possible case for writing them down and for §3's advice to convert them into checks. Fall back to
three sources that always exist:

- **The commit log**, which shows subject style, body discipline, granularity and whether work
  goes through branches. In a repo with no tooling this is the only written record of how the
  team operates.
- **Churn**, which shows what the work actually consists of. A repo where every commit touches
  the same four documents has a different shape from one spread across fifty files.
- **The artifacts themselves.** Read two or three of the files the repo exists to produce and
  infer the house style directly: how rules are phrased, how sections are structured, what the
  author clearly refuses to do. A convention visible in every file is a real convention.

**Check whether the repo follows the standards it already ships or cites.** If it contains or
links a style guide, a contributing document, a set of practice rules or a published policy,
verify a sample of those claims against reality: does `main` have the protection its own guide
demands, does CI run what its own README promises, do the files follow the conventions they
document? Divergence here is high-value, because a repo that visibly ignores its own rules
teaches every reader, human or agent, that the rules are decorative. Either the practice or the
rule needs to change, and the user is the one who decides which.

Then **report what you found and ask for correction**, in a few lines. "Your last 200 commits are
85% Conventional Commits, tests live beside sources as `*.test.ts`, Biome and a pre-commit hook
already enforce formatting, and CI runs typecheck plus unit plus e2e. Correct anything wrong
here." Confirming beats interrogating, and it surfaces the gap between the intended convention
and the practised one, which is often the most useful thing the exercise produces.

## 2. Interview

Ask only what reading cannot answer. Go in small batches of two or three, not a wall of
questions, and offer the fast path: the starred items alone produce a usable playbook, and the
rest can be filled in later from real runs.

**Definition of done.** ★ What has to be true before a task counts as finished? Tests passing,
new tests written, types checked, docs or changelog updated, a migration tried against a copy, a
screenshot, a manual check somewhere? This is the highest-value answer in the interview, because
nearly every disagreement about agent work is a disagreement about what finished meant.

**Stop conditions and autonomy.** ★ Ask these together, in one exchange, because they are two
ends of the same question and answering one half-answers the other. How far does an agent's
authority run: edit the working tree, commit, push a branch, open a pull request, merge? And
where does it stop and ask instead of deciding: adding a dependency, changing a schema, altering
a public API or response shape, touching auth or permissions, anything involving money or
personal data, a change spanning more than some number of files? Then the hard limits, which are
worth stating separately in the output: what it may never do without a human, such as pushing to
a protected branch, running a migration against live data, editing production config, or
rotating a credential. Being explicit prevents both timid agents that stop short of useful work
and bold ones that push to `main`.

Watch for answers that contradict a rule the playbook is about to state. A team that wants an
agent pushing directly to `main` has chosen a workflow that branch-protection advice forbids;
that is a legitimate choice for a small repo, but it has to be recorded as a deliberate
deviation with its reason (§4), or the playbook will contradict itself and lose credibility.

**The shape of a task.** Where does work arrive from, and in what format? Branch from what, named
how? Is there a required sequence from issue to merge, and who or what reviews? Agents are good
at following a stated pipeline and bad at inferring one.

**Scope discipline.** When an agent notices an unrelated problem mid-task, what should it do:
fix it, mention it, open an issue, or leave it alone? Is drive-by refactoring welcome or
unwelcome? Teams differ sharply here and the wrong guess is irritating in both directions.

**The dangerous parts.** Which areas of this codebase are riskiest to change, and why? What
mistake do new contributors reliably make? Is there anything that looks wrong but is deliberate?
That last question is worth real weight: it is the only reliable way to stop an agent
confidently "fixing" an intentional oddity, and the answer is never in the code.

**Verification.** The exact commands to build, test, lint and typecheck, roughly how long each
takes, and anything that cannot be checked locally at all. Duration matters: an agent that knows
the suite takes twelve minutes will scope what it runs, and one that does not will either skip
testing or stall.

**Taste that recurs.** Any library or pattern deliberately banned, and what to use instead? Any
module the team considers exemplary and worth imitating? A pointer to one good example teaches
more than a paragraph of description.

**Corrections you have already had to make.** ★ Ask directly: what have you had to tell an agent,
or a new colleague, more than once? What did the last review of agent-written work change? This
is the single most productive question in the interview and the one most often skipped, because
those corrections are the conventions that matter most and the ones least likely to be written
anywhere. They exist only in chat logs and reviewers' memory, and they vanish when the session
ends, which is exactly the problem a playbook solves. If you are running this skill inside a
session where the user has already corrected you, mine that: those corrections are evidence, and
they belong in the playbook whether or not the user thinks to mention them.

## 3. What earns a place

Admit a rule only if all three hold. This filter is what keeps the result worth reading:

1. **It recurs.** It will come up again. A one-off is a code comment, not a rule.
2. **Getting it wrong has a real cost.** Broken production, a security hole, data loss, a painful
   revert, a repeated argument. Aesthetic preferences with no consequence are not rules.
3. **No tool enforces it.** If a linter, formatter, type checker, test, CI gate or database
   constraint can enforce it, that is strictly better than a written rule, because it cannot be
   forgotten or ignored. When you find such a rule, **say so and offer to add the check instead**.
   A playbook should shrink as enforcement grows.

   `scripts/validate-playbook.py` in this skill is a working scaffold for exactly that. Copy it
   into the repository, usually as `scripts/validate-playbook.py`, and replace its example
   `CHECKS` with the project's own. It composes checks from factories for forbidden text,
   required text, file existence, link resolution, commit subjects and bodies, and a shell
   escape hatch that delegates to tooling the project already owns rather than reimplementing
   it. Prefer that escape hatch where a real linter exists: wrapping `pnpm lint` keeps the
   check honest, while reimplementing its rules guarantees drift.

   **Then prove the checks can fail.** Run `python3 scripts/validate-playbook.py --self-test`,
   which writes a synthetic violation for each check and confirms it fires. A check that cannot
   fail is worse than no check, because it reports success forever and nobody looks at it again.
   Do this every time you add or edit one; it catches inverted conditions and patterns that
   never match, and it takes a second. Anything reported as unverified needs a sample violation
   declared before you trust it.

   Expect the first real run to fail on things that are fine. That is the scaffold's defaults
   meeting the project's actual choices, and each failure is a question worth asking: is this
   a rule the project wants, or a default to delete? Resolve every one before wiring it to CI,
   because a validator that is known to cry wolf gets disabled within a week.

Also exclude: anything already obvious from the code, anything covered by the five general
practice skills unless this team deliberately differs from them, and anything nobody actually
follows. An aspirational rule that is routinely violated teaches an agent that the playbook is
decorative.

## 4. Write it

Two halves, because they answer different questions. **Standards** say what good work looks like
here. **Workflow** says how a task travels from arrival to done. Most teams have some of the
first written down somewhere and almost none of the second, which is the half agents most need.

Write every rule in this form:

> **Imperative claim.** The trigger or situation, then the reason or cost.

```markdown
- **Never query the warehouse from a request handler.** Warehouse queries take seconds to
  minutes, and one blocking call occupies a worker for the duration. Read from the replica, or
  move it to a job and return a job id.
```

That carries a trigger (a request handler), an instruction, and a consequence that lets a reader
judge when an exception is legitimate. Compare "avoid slow queries", which carries none.

Conventions that make the output usable:

- **Order by how often it applies**, not by topic neatness. The rule that fires every task goes
  first.
- **State the real command**, not a description of it. `pnpm test -- --filter=api` beats "run the
  relevant tests".
- **Name files and directories explicitly.** "Handlers live in `src/api/routes/`, one file per
  resource" is actionable; "keep the structure consistent" is not.
- **Record the reason for anything surprising**, especially deliberate oddities. This is the
  content with the longest useful life, because the code cannot express it.
- **Mark hard limits as hard.** Separate "stop and ask" items visually from preferences. An agent
  needs to distinguish a guardrail from a nicety.
- **Match the repo's own vocabulary.** If the team says "tenant", never silently switch to
  "organization".

Use `references/template.md` for the skeleton and a worked example.

## 5. Place it

| Target | Loading | Best for |
|---|---|---|
| `CLAUDE.md` | Every session, always | A small set of universal rules: stop conditions, verification commands, definition of done |
| `.claude/skills/<name>/SKILL.md` | Only when triggered | Depth on one area (migrations, this API, the billing module) without taxing every session |
| `docs/playbook.md` | Only when read | Reference and human onboarding, plus a target for the two above to point at |

**Recommend the split, not one file.** Put the handful of rules that apply to every task in
`CLAUDE.md`, because a stop condition that loads conditionally is a stop condition that fails.
Put domain depth in skills, where it costs nothing until relevant. The common failure is cramming
everything into `CLAUDE.md`, which taxes every session and buries the critical rules in bulk.

When writing a skill, the frontmatter `description` is the entire triggering mechanism, so it
must state both what the skill covers and the situations that should invoke it. A skill with a
vague description never fires and its content may as well not exist.

## 6. Test it on real work

A playbook is a hypothesis until a task runs through it. Finish by taking one real task, ideally
one that previously went wrong, and running it under the new playbook. Then look for:

- **Silence**: a decision the agent had to make that the playbook did not cover. Add it.
- **Friction**: a rule that made the work worse or was overridden for good reason. Fix or delete
  it. A rule reasonable people violate is wrong or badly explained.
- **Dead weight**: rules that never came up. Leave them if they are real guardrails; cut them if
  they were speculative.

Say this to the user explicitly, because it is what turns the document into something load
bearing instead of a one-time artifact.

**Keep it true.** A stale playbook is worse than none, since agents follow wrong rules with
confidence. Set a trigger for revisiting it: whenever a rule is overridden twice, whenever the
stack changes, and whenever a postmortem names a missing rule. Prefer deleting a rule to leaving
one nobody believes.

## Anti-patterns

- A playbook restating what the linter, formatter, type checker or CI already enforces.
- Rules with no trigger ("write clean code", "prefer composition").
- Rules with no reason, which an agent cannot apply judgment to.
- Aspirational rules the team does not actually follow.
- Everything in `CLAUDE.md`, so critical guardrails sit buried in context every session.
- A skill whose description is too vague to trigger, making its content unreachable.
- Interviewing the user for facts the repository plainly states.
- A playbook long enough that reading it costs more than the mistakes it prevents.
- Writing it once and never revisiting it after a rule proves wrong.
