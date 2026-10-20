# Playbook template

Read this at step 4 of the `playbook-builder` skill, when you are ready to write.

The output is a `CLAUDE.md` built around a **gate pipeline**: an ordered sequence where each
gate closes before the next opens. This shape matters more than any individual rule in it,
because it converts a list of preferences into a procedure. "Write tests" is advice an agent
weighs; "Gate 4 does not open until Gate 3 is approved" is a thing an agent does.

Delete every section you have nothing real to put in. An empty heading invites filler, and
filler is what makes a playbook unread.

## What makes a gate a gate

Four properties. A step missing any of them is a suggestion wearing a gate's name:

1. **An entry condition.** What must already be true. Usually "the previous gate closed".
2. **A definite action**, naming the real tool, skill or command rather than describing it.
3. **An exit condition that can be checked.** "Plan approved", "review findings all resolved",
   "issue moved and PR linked". Not "done properly".
4. **A stated behaviour when it cannot close.** The tracker is unreachable, the user has not
   given a go-ahead, the review found something unfixable. The common failure is a gate that
   silently gets skipped when its precondition fails, so say what happens instead.

Number gates from 0 so a tracking gate can sit ahead of triage without renumbering everything.

## Skeleton

```markdown
# CLAUDE - <Project>

## Project overview

<Two or three sentences: what this is, who uses it, what it sits on top of. Enough that an
agent reading only this file knows what domain it is in.>

<The topology, in one line, because it decides how many pull requests a task produces: a single
project, a monorepo of N packages, or N separate repositories under this folder. If separate,
name them and say which is the contract producer.>

<If there are distinct user roles or tenancy concepts, list them here. They shape every
authorization decision that follows.>

---

## Task playbook

Every substantive task runs these gates **in order**. A gate closes before the next opens.
This is the prescribed flow, not a menu.

<One sentence naming the hardest constraints up front, so they are not buried: no code before
an approved plan, no commit until explicitly asked, or whatever the real ones are.>

### Gate 0 - <Tracking>

<Every task gets an issue, or the stated exception. Search before creating, so the same work
does not get two issues. How to route it. Who to assign. What status it moves to. Which ID
travels into the branch name.>

<What to do when the tracker is unreachable: say so and ask. Never skip silently.>

### Gate 1 - Triage

Run the **full flow** if any of these is true:

- <blast-radius criterion>
- <blast-radius criterion>

**Short flow** (skip Gates <n>-<m>, start at Gate <k>) for changes with no blast radius:
<typo, comment, copy string, local config, dependency bump>. These still run Gates <k>-<last>.

When it is a judgment call, run the full flow.

### Gate 2 - <Design>

<Which skill or approach. Crucially: where it stops, and what artifacts it must not produce.>

### Gate 3 - <Plan>

<Plan produced and approved before any implementation code. Name the approval mechanism.>

### Gate 4 - Implement

<Isolation: branch from what, named how, worktree or not.>
<Module order if there is one.>

Read the relevant guide **before** writing code, and verify against it after:

| Area | Guide |
|---|---|
| <module> | [`<path>`](<path>) |

### Gate 5 - Review before pushing

<What runs it, against the working diff. Every finding fixed or explicitly dismissed.>

### Gate 6 - Commit and PR <- authority boundary

<Whether this gate opens on its own. If not: what the agent does instead, which words
constitute permission, whether permission is per-step, whether it carries to the next task,
and what does not count as permission.>

<Which skills commit as part of their own flow and are overridden here.>

### Gate 7 - <Post-PR review>

<Only if Gate 6 happened. Note the scoping trap: the working diff is empty once committed, so
scope to the branch explicitly.>

### Gate 8 - Close the loop

<What state the task ends in. Where work parks if it stalls. Who is allowed to mark it Done.
What happens to acceptance criteria that did not ship.>

<If a task routinely spans more than one repository, add this to the implement and PR gates:>

```markdown
### Spanning repositories

A task touching both <producer> and <consumer> is one unit of work in two repositories.

- **Order**: <producer> first, always. The consumer cannot be reviewed against a contract
  that does not exist yet.
- **Regenerate the client** after a contract change, and commit it: `<command>`. Drift here
  is invisible to both CI runs, because each repository passes in isolation.
- **Two pull requests, one issue.** Attach both. The issue does not move until both merge.
- **Merge order is <producer> then <consumer>**, and the consumer is broken in between.
  Prefer an additive change that makes the order irrelevant: add the new shape, ship it,
  migrate the consumer, remove the old shape in a later task.
- **Done means both merged.** A green build on one side is half a task.
```

---

## Conventions by area

<One table answering "what should I have read before touching this". Team conventions and
general practice are different columns, because they answer different questions and one of
them is optional.>

| Area | Team conventions | General practice |
|---|---|---|
| `<dir>/` | [`<doc>`](<doc>) | `<skill>` |

<Only name a general skill where you are changing what would otherwise happen: making it
mandatory at a gate, narrowing it to a section, or recording where your convention overrides
it. Do not restate the trigger conditions the skill's own description already carries.>

<Where a local convention contradicts the general practice, say so explicitly and say which
wins. That sentence is the one piece of information that exists nowhere else.>

---

## Tech stack

<Per module: the stack in one line, pointing at its guide.>

---

## Quick start

Startup order: **<a> -> <b> -> <c>**.

| Module | Start | Test / lint | Port |
|---|---|---|---|
| <module> | `<cmd>` | `<cmd>` | <port> |

<Gotchas that make the difference between the above working and not: what must run first,
what has no test suite and what gates it instead, where the API docs are.>

---

## Local environment

<Prerequisites with versions. Which config files are committed. Which environment variables
are needed even locally, and what breaks without them.>

---

## Git conventions

<Commit format with the real types and scopes. Branch naming including how the issue ID is
carried. Which branch PRs into which. What CI runs and on what. Attribution rules. A pointer
back to the authority gate.>

---

## Architecture

<The mechanisms an agent could violate without noticing: tenancy, auth, request pipelines,
event ordering. Describe how they work, not just that they exist. Tables and small diagrams
beat paragraphs here.>

<The test for inclusion: could a change pass review and tests and still be wrong because the
author did not know this existed?>

---

## Gotchas

<Per area. The tacit knowledge: things that look wrong and are deliberate, mistakes new
contributors reliably make, and rules whose violation is silent rather than loud.>

**<Area>**:
- <Specific, checkable, with the consequence stated.>
```

## Worked fragments

Quality bar to aim for. Each names a trigger, gives an instruction, and states a consequence
that lets a reader judge when an exception is legitimate.

### A gate with a real authority boundary

```markdown
### Gate 6 - Commit and PR - requires explicit go-ahead

**This gate does not open on its own.** When the work is implemented and Gate 5 is clean,
stop: report what is ready, leave the changes uncommitted, and wait.

Never run `git commit`, `git push`, or `gh pr create` unless asked for that step in this
session, in the user's own words.

- **Permission is per-step.** "Commit it" is not permission to push.
- **Permission does not carry forward.** The next task starts back at asking.
- A clean review, a green CI run, finishing the work, and being told to "work autonomously"
  are **not** permission.
- **This overrides any skill that commits in its own flow.** When a skill says commit, it
  means ask.
```

Note what makes it work: it names the exact commands, enumerates the four things agents
misread as consent, and resolves the conflict with other skills rather than leaving the agent
to arbitrate.

### A gotcha worth writing down

```markdown
- **Admin routes bypass tenant scoping entirely.** Tenant routes are auto-filtered by the
  request pipeline, so a missing `tenant_id` on a tenant query is harmless. On an admin
  route the filter does not run, and the same omission silently returns every tenant's rows.
  Repositories called from admin paths must take an explicit tenant id.
```

Silent and wrong beats loud and wrong for playbook inclusion: a crash teaches itself, and
this does not.

### Scoping a second review pass

```markdown
Gate 5 already consumed the working diff, so the tree is clean by now. Scope this pass to the
branch explicitly with `gh pr diff` or `git diff origin/<base>...HEAD`, or the review reads
nothing and reports success.
```

## What to leave out

The example above contains no quote style, no import ordering, no naming conventions. A
formatter and linter own those, and §3 of the skill says a rule a tool can check should become
the tool. Everything present is something no tool can check and something that has already
cost the team.
