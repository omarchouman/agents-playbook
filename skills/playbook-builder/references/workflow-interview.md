# Workflow architecture interview

Read this at step 2 of the `playbook-builder` skill, after detection and before drafting.

These questions decide the **shape of the gate pipeline**, not the content of individual
rules. They are architectural: each answer adds, removes or reorders a gate, so getting them
wrong means the whole pipeline is wrong. The standards interview in SKILL.md §2 asks what good
code looks like; this one asks how work moves.

Ask in the order below. Each group has a **default** to propose rather than an open question,
because a user confronted with "how do you want your workflow?" says "I don't know", while the
same user shown a concrete default says "yes, except..." and gives you the real answer in one
exchange. Propose, then correct.

## Contents

1. [Repository topology](#1-repository-topology)
2. [Tracking and traceability](#2-tracking-and-traceability)
3. [Execution model](#3-execution-model)
4. [Isolation](#4-isolation)
5. [Design and planning gates](#5-design-and-planning-gates)
6. [Triage](#6-triage)
7. [Review](#7-review)
8. [Commit, push and PR authority](#8-commit-push-and-pr-authority)
9. [Closing the loop](#9-closing-the-loop)
10. [Module order and layering](#10-module-order-and-layering)
11. [Where conventions live](#11-where-conventions-live)

---

## 1. Repository topology

Ask this first. It decides where the playbook can physically live, how many pull requests one
task produces, and whether those pull requests have to merge in a particular order. Every later
answer sits on top of it.

Detection (`references/detection.md`) should already have told you the shape. **State your
conclusion and ask for correction** rather than asking an open question, since a directory of
separate repositories and a monorepo look identical from the outside.

### The five shapes, and what each one changes

**Single project.** One repository, one deployable. One `CLAUDE.md` at the root, one pull
request per task, nothing to coordinate. Skip the rest of this section.

**Tooled monorepo** (pnpm workspaces, Turborepo, Nx, Gradle multi-project, Cargo workspace,
`go.work`). One repository, shared lockfile, coordinated builds. One task is one commit and one
pull request even when it spans packages, which is the main reason teams choose this. The
pipeline lives once at the root; per-package conventions go in a `CLAUDE.md` inside that
package, picked up when work happens there.

**Untooled monorepo.** One repository, independent projects in sibling directories, no workspace
manifest tying them together. Behaves like the tooled case for version control (one history, one
pull request) but each project has its own build and its own commands, so the quick-start table
needs a row per project and the implementation gate needs an explicit order.

**Separate repositories side by side.** Several repositories cloned into one parent folder.
This looks like a monorepo in the file tree and behaves nothing like one, and it is the case
worth the most care. See below.

**Superproject with submodules.** One repository pinning others at specific commits. A change
spanning both needs the inner pull request merged first, then a commit in the outer repository
moving the pointer. Teams routinely forget the second half, so the pipeline should make the
pointer bump an explicit gate step rather than an afterthought.

### When repositories are separate but joined under one folder

Three questions, and the first has consequences people do not expect:

**Is the parent folder itself a repository?** Usually not: it is just a directory someone made
to hold two clones. If so, a `CLAUDE.md` written there is invisible to everyone else. It is not
committed anywhere, so a teammate cloning only the backend never sees it, CI never sees it, and
it silently disappears when someone reorganizes their machine. Raise this before writing
anything, and pick one:

- **A `CLAUDE.md` in each repository**, each carrying the pipeline, with the cross-repo rules
  stated in both. Duplication is the cost; being visible to everyone who clones either side is
  the benefit. Usually the right answer.
- **Make the parent a real repository** that holds the shared playbook and the clones are
  ignored or submodules. Clean, but it is a new repository for the team to adopt.
- **A shared package or documentation repository** that both reference. Avoids duplication at
  the cost of indirection, and only works if people actually follow the pointer.

**Does a single task routinely span both repositories?** If it does, the pipeline has to say so
explicitly, because the default agent behaviour is to finish one side and report success:

- **One issue or two?** One issue with both pull requests attached usually beats two issues that
  drift apart. Decide and write it down.
- **Which side goes first?** The producer of a contract before its consumer, always. The
  implementation gate should name the order rather than leaving it to judgment.
- **Merge order, and what is broken between the two merges.** This is the real hazard. A client
  pull request merged before its server counterpart ships a frontend calling an endpoint that
  does not exist yet, and nothing in either repository's CI can detect it, because each one
  passes in isolation. The gate must state the order and say that the task is not done until
  both have merged.
- **Does the definition of done span both?** It has to, or "done" means half-shipped.

**How do the two sides stay in contract?** The sync mechanism decides how much the pipeline can
rely on tooling instead of care:

- **Generated client or shared types** from an OpenAPI, GraphQL or protobuf schema. The
  strongest option, because drift becomes a build failure rather than a runtime surprise. If
  this exists, regenerating and committing the client is a step in the implementation gate, and
  "did you regenerate" is a checkable exit condition.
- **A shared package of types or contracts** consumed by both. Works, but version bumps become
  part of the merge ordering problem.
- **Nothing: the two sides agree by convention.** Then the playbook is the only thing holding
  the contract together, and the review gate should explicitly check both sides of any contract
  change.

**Prefer backwards-compatible changes across the boundary**, which removes the merge-ordering
problem rather than managing it. Add the new field or endpoint, deploy it, migrate the client,
then remove the old one in a later change. This is the same expand-and-contract reasoning the
`database-practices` skill applies to migrations, for exactly the same reason: two things that
cannot be deployed atomically must tolerate running in either combination.

## 2. Tracking and traceability

**Which tracker, and is it reachable from here?** Linear, Jira, ClickUp, Shortcut, GitHub
Issues, Notion, Asana, or nothing. Then the question that decides whether a tracking gate is
even possible: **is there an MCP server or CLI connected for it?** Check what is actually
available in the session rather than assuming:

- Linear, Jira, Notion, Asana and others commonly expose an MCP server.
- GitHub Issues needs no MCP: `gh issue` covers it.
- If nothing is connected, the gate becomes "ask the user for the issue ID and record it",
  which still buys traceability. Say so rather than silently dropping the gate.

If a tracker is connected, get the specifics the gate needs to run without guessing: the team
or project key, the issue prefix (`HEY-123`), and whether there are multiple projects work gets
routed between. **Never hardcode workflow status names.** Teams rename them, and a gate that
hardcodes "In Review" breaks silently against a workflow using "Code Review". The gate should
resolve statuses from the live workflow and ask when no status obviously fits.

**Does every task get an issue, or only substantive ones?** The stricter answer is usually
right, because an issue is the only durable record of why a change happened once the branch is
deleted. If they want it for everything, the tracking gate runs *before* triage and the trivial
cases get a short issue rather than no issue.

**Who assigns, and who closes?** Assignment is usually "ask once per session and reuse". Closing
is the one to pin down: an agent that marks work Done when a PR opens produces a tracker that
lies. The common correct answer is that the agent moves it to In Review and a human closes it
after merge.

**Does the issue ID travel into the branch name, commit trailer, or PR title?** Putting it in
the branch name is the cheapest form of traceability and it is what makes the tracking gate
feed the branching gate.

## 3. Execution model

**Native, subagent, or mixed?** This is the question people most often have no opinion on until
shown the trade-off, so present it:

- **Native** (everything in the main session): full context, simplest to follow, and the user
  sees every step. Costs context window on exploration that gets discarded.
- **Subagent delegation** for bounded, read-heavy work (codebase exploration, a review pass,
  research): keeps large tool output out of the main context and returns only the conclusion.
  Costs a cold start, so the subagent re-derives context the main session already had.
- **Parallel subagents** for genuinely independent tasks only. Shared state or sequential
  dependencies make this worse than serial, not better.

A good default for most teams: native by default, delegate exploration and review, and never
parallelize work that touches the same files. Ask whether they have a preference against
subagents entirely, since some teams dislike not seeing the intermediate steps.

**Which skills or tools are mandatory at which gate?** If the team has house skills (a TDD
skill, a review toolkit, a brainstorming skill), name them in the gate that owns them. A gate
that says "review the code" is weaker than one that says "run `<skill>` against the working
diff".

## 4. Isolation

**One working tree, or a worktree per task?** Git worktrees give each task its own checked-out
directory sharing one repository, so work in progress does not collide.

- **Single tree** is right for sequential work by one person. Simpler, and nothing to clean up.
- **Worktree per task** earns its keep when tasks run in parallel, when a long-running task
  must be parked while something urgent jumps the queue, or when an agent should not be able to
  disturb the user's own working tree. Claude Code can create and manage these.

Ask directly: *do you want each task isolated in its own worktree, or all work in the main
checkout?* If they pick worktrees, the pipeline needs a creation step in the branching gate and
a cleanup step in the closing gate, otherwise worktrees accumulate.

**Does the agent ever work on the base branch directly?** For most teams the answer is no, and
the branching gate should say so explicitly, because "branch first" is the kind of step an agent
skips when the change feels small.

## 5. Design and planning gates

**Is there a design phase before implementation, and is plan approval required?** Three common
shapes:

- **Plan-gated**: agent produces a step-by-step plan and waits for approval before any
  implementation code. Right for most substantive work.
- **Design then plan**: an open-ended exploration of intent and constraints first, then a plan.
  Right when the requirement is ambiguous rather than just unimplemented.
- **Straight to implementation**: right only for short-flow work (see triage).

If they use a brainstorming or planning skill, ask **where it should stop**. Skills that produce
design documents often write artifacts the team does not want; the CARLA example stops its
brainstorming skill at "design approved" and explicitly forbids the document-writing steps that
follow. Pin this down, or the agent will produce files nobody asked for.

## 6. Triage

**What distinguishes work that needs the full pipeline from work that does not?** Make the
criteria concrete and about blast radius, not size. Typical full-flow triggers:

- touches business logic or a service boundary
- touches the schema, a migration, or seed data
- changes a public contract: endpoint path, payload shape, permission name
- touches auth, permissions, or tenant scoping
- spans more than one module

Typical short-flow: typo, comment, copy string, local-only config, dependency bump, single-file
cosmetic change. **State which gates short-flow still runs**, since the honest answer is usually
"all of them except design and planning", and leaving it vague means short-flow quietly becomes
no-flow. Add the tiebreaker explicitly: when it is a judgment call, run the full flow.

## 7. Review

**Is there a review pass before anything is pushed, and what runs it?** A review of the
uncommitted working diff catches problems while they are still cheap to fix and while no history
has been written. Ask what tool or skill owns it.

**Is the PR auto-reviewed after it opens, or only by humans?** If both, note that the two passes
read different things: the pre-push pass reads the working diff, and once committed that diff is
empty, so the PR pass has to be scoped explicitly to the branch (`gh pr diff`, or
`git diff <base>...HEAD`) or it reviews nothing. This is a real failure mode worth writing into
the gate.

**What happens to findings?** The useful rule is that every finding is either fixed or
explicitly dismissed with a reason, never silently carried past the gate.

## 8. Commit, push and PR authority

The single most consequential group. Ask all of it:

**Does the agent commit on its own?** Push? Open a PR? Merge? Treat each as separate authority,
because teams genuinely differ and the failure modes are opposite: an agent too timid stops with
work stranded in a dirty tree, and one too bold pushes to a protected branch.

If the answer is "ask first", three details decide whether the rule actually holds:

- **Is permission per-step or a bundle?** "Commit it" is usually not permission to push. Say
  which, or the agent will infer the generous reading.
- **Does permission carry forward to the next task?** Usually not. Without this, one go-ahead
  silently becomes standing authority.
- **What does not count as permission?** Finishing the work, a clean review, a green CI run, and
  an instruction to "work autonomously" are the four things agents reliably misread as consent.
  Name them.

**Which skills override this?** This matters more than it looks. Skills that commit as part of
their own flow (test-driven development's "commit after each green", plan execution, branch
finishing) will commit unless the playbook explicitly says that when a skill says commit, it
means ask. If the team uses any such skill, the gate must name it and override it.

## 9. Closing the loop

**What state does the task end in?** The task is not over when the PR opens; it is over when the
tracker reflects reality. Decide: the status it moves to, whether the PR gets attached as a link,
whether a comment summarizing what shipped is wanted, and what happens to acceptance criteria
that did not make it. The last one has a correct answer: a follow-up issue, never a quiet drop.

**And when work parks mid-pipeline** waiting on a human, what state does it sit in, and does the
agent say so in its report? Work stalled in a state nobody can see is how things get forgotten.

## 10. Module order and layering

**If the repo has multiple modules, is there a required implementation order?** Schema before
API before UI is the common one, and it is worth stating because an agent working outside it
produces code that cannot run until the rest lands. Ask for the dependency direction and
whether anything enforces it.

**Is there a startup order for local development?** Same reasoning: it belongs in the quick-start
table so nobody debugs a failure that is really a missing dependency.

## 11. Where conventions live

**Are there existing convention documents per area?** If the team already has them, the playbook
should point at them rather than restate them, with a table mapping module to document and an
instruction to read the relevant one *before* writing code and verify against it after. If they
do not exist, that absence is itself worth surfacing: it is what the practice skills in this
plugin cover generically, and what a per-module guide would cover specifically.

**Is there architecture an agent must not violate without knowing it?** Tenant scoping, auth
pipelines, caching layers, event ordering. These are the mechanisms where a change that looks
locally correct is globally wrong, and they belong in the playbook as mechanism descriptions,
not as rules. The test: could an agent make a change that passes review and tests, and still be
wrong because it did not know this existed? If yes, write it down.
