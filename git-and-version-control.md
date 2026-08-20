# Git and Version Control Practices

Applies to any project using Git, in any language, with any branching model. The
collaboration rules assume a pull-request workflow on a hosted forge (GitHub, GitLab,
Bitbucket); the commit and history rules apply regardless.

**Read this before:** making a commit, opening a pull request, rewriting history, adding
anything binary or generated to the repository, or resolving a conflict.

---

## 1. Core principles

1. **History is a communication medium, not a backup log.** Its readers are the person
   bisecting a regression at 2am, the reviewer deciding whether a change is safe, and you
   in eighteen months. Optimize for them, not for your own convenience while working.
2. **The commit is the unit of revert, review, and bisect.** Everything about commit
   hygiene follows from this. A commit that mixes two changes cannot be reverted cleanly,
   reviewed independently, or isolated by `git bisect`.
3. **Local history is yours; published history is shared state.** You may rewrite the
   first freely. Rewriting the second breaks everyone who has pulled it.
4. **The repository is permanent.** Anything committed is recoverable from clones, forks,
   reflogs, and CI caches long after you delete it. Treat every commit as public and
   irreversible, because for secrets it effectively is.

---

## 2. Commits

### 2.1 What goes in one commit

- **One logical change per commit.** Not one file, not one day's work. If the subject line
  needs the word "and", it is probably two commits.
- **Every commit should build and pass its tests.** This is what makes `git bisect` usable
  and `git revert` safe. A commit that is knowingly broken, to be fixed by the next one,
  poisons every tool that assumes commits are independent points in time.
- **Never mix a refactor with a behaviour change.** This is the single highest-value commit
  rule. A diff that both moves code and changes it is one where the reviewer cannot see the
  change, because it is buried in a hundred lines of movement. Do the refactor in one
  commit, the behaviour change in the next, and say so in the subjects.
- **Separate mechanical changes from meaningful ones.** Reformatting, renaming, import
  reordering, dependency bumps, and generated-file updates each get their own commit. A
  formatter running over a file you also edited turns a three-line change into an
  unreviewable diff.
- **Commit early and often locally; clean up before you publish.** Work-in-progress commits
  are a working technique, not something anyone else needs to see. Squash them into
  coherent units before review (§4.2).

### 2.2 Messages

```
Add rate limiting to the password reset endpoint

Reset requests were unbounded, so an attacker could enumerate accounts
by timing and exhaust the mail provider's quota. Limits are per-account
and per-IP, sharing the login endpoint's existing bucket configuration.

Chose a fixed window over a token bucket because the reset flow is
low-volume and the simpler mechanism is easier to reason about under
concurrent requests.

Fixes #482
```

- **Subject line: imperative mood, capitalized, no trailing period, roughly 50 characters.**
  "Add rate limiting", not "Added rate limiting" or "Adds rate limiting". The convention is
  not arbitrary: Git's own generated messages ("Merge branch", "Revert") are imperative, so
  matching them keeps the log consistent.
- **Blank line between subject and body**, always. Without it, tooling cannot tell them
  apart and the whole message becomes the subject.
- **Wrap the body at about 72 characters.** Git does not wrap for you, and terminal output
  indents the body by four spaces.
- **The body explains why, not what.** The diff already shows what changed. What it cannot
  show is the reasoning: the alternative you rejected, the constraint that forced this
  shape, the bug that motivated it, the benchmark that justified the complexity. A commit
  whose body restates the diff in prose has wasted the only place that context can live.
- **Write the body whenever the change is not self-evident.** A one-line subject is fine for
  a typo fix and inadequate for anything with a reason behind it.
- **Reference issues, and describe the symptom.** "Fixes #482" is a pointer that requires
  network access and an intact issue tracker to resolve. One sentence of symptom in the
  message survives the tracker being migrated or shut down.
- **Never write `fix`, `wip`, `update`, `changes`, `asdf`, or `address review comments`** in
  published history. These say precisely nothing to the person reading `git log` later.

**Conventional Commits** (`feat:`, `fix:`, `chore:`, with `!` for breaking changes) is a
reasonable convention when you want automated changelogs and semantic-version inference.
Adopt it only if you actually consume the machine-readable part; otherwise it adds ceremony
without benefit. If you do adopt it, enforce it with a hook, because a partially followed
convention is worse than none: automation silently misses the commits that skipped it.

---

## 3. Branching

- **Keep branches short-lived.** A branch open for three weeks is three weeks of divergence,
  and the cost of integrating it grows faster than linearly. Aim for days, not weeks.
- **Choose a model by release cadence, then stick to it.**
  - **Trunk-based** (short branches, merge to `main` continuously, release from `main`)
    suits continuous deployment and is the right default for most web applications.
  - **Release branches** suit versioned software supporting multiple live versions.
  - **Git Flow** (`develop`, `release/*`, `hotfix/*`) suits scheduled releases with a
    formal QA phase. It is heavy machinery, and adopting it for a continuously deployed web
    app buys ceremony you will not use.
- **Use long-lived feature branches as a last resort.** If a feature is too big to merge
  incrementally, merge it incrementally behind a feature flag instead. Dark-launching
  unfinished code that is switched off is nearly always less risky than a branch that has
  drifted for a month.
- **Name branches predictably**: `feat/reset-rate-limit`, `fix/duplicate-invoice-email`,
  `chore/bump-node-22`. Include the ticket id if your tooling links on it. Never work
  directly on `main`.
- **Integrate the base branch into your branch often**, not once at the end. Ten small
  conflicts resolved as they appear are much easier than one enormous conflict resolved
  under pressure.
- **Delete branches after merging.** A branch list that accumulates hundreds of merged
  branches makes the handful of live ones invisible.

---

## 4. History hygiene

### 4.1 The rule that matters

**Never rewrite history that others may have pulled.** Rebasing, amending, squashing, or
force-pushing a shared branch rewrites commits that exist in other people's clones, and
their next pull produces duplicated commits, phantom conflicts, or silently lost work.

The line is publication, not the branch's name: rewriting your own feature branch that
nobody else has checked out is fine and encouraged. Rewriting `main`, a release branch, or
a branch someone else is building on is not.

If you must rewrite a shared branch (a committed secret, a huge accidental binary), treat
it as an incident: tell everyone first, agree a time, and give explicit re-sync
instructions. This is the same reasoning that makes migrations immutable once they have
run anywhere (`database-and-migrations.md` §6.1).

### 4.2 Cleaning up before review

Interactive rebase is how work-in-progress becomes reviewable history:

```bash
git rebase -i main            # reorder, squash, split, reword
git commit --fixup <sha>      # mark a commit as fixing an earlier one
git rebase -i --autosquash main   # apply the fixups automatically
```

- **Rewrite your branch before opening the PR**, not after review starts. Rewriting under a
  reviewer invalidates the comments they have already left.
- **After review begins, add commits rather than amending.** Reviewers need to see what
  changed since they last looked. Squash at merge time instead.

### 4.3 Merge, rebase, or squash

| Strategy | History | Use when |
|---|---|---|
| **Merge commit** | Preserves every commit and the branch topology | The branch's individual commits are meaningful and worth keeping |
| **Squash merge** | One commit per branch; individual commits discarded | Branches are small and their intermediate commits are noise. Simple, and the common default |
| **Rebase merge** | Linear, all commits preserved, no merge commit | You want linear history and your commits are already clean |

Any of the three is defensible. **Pick one per repository and configure the forge to
enforce it**, because a history that mixes all three is hard to read and hard to script
against. What matters far more than the choice is that commits are atomic in the first
place.

Note the trade-off in squash merging: it guarantees a tidy `main` and destroys the
intermediate steps, so a carefully constructed sequence of refactor-then-change commits
collapses into one. If your team invests in commit hygiene, squashing throws that away.

### 4.4 Force-pushing

- **Always `--force-with-lease`, never `--force`.** The lease variant refuses to push if the
  remote has commits you have not seen, which is exactly the case where a plain force-push
  silently destroys a colleague's work.
- **Prefer `--force-with-lease --force-if-includes`** where available, which additionally
  verifies you have actually inspected the remote state rather than merely fetched it.
- **Protect `main` and release branches against force-pushes at the forge**, so the rule is
  enforced rather than remembered.

### 4.5 Conflicts

- **Understand both sides before resolving.** A conflict is two intentions meeting. Taking
  "yours" or "theirs" wholesale, without reading them, is how a colleague's fix vanishes
  while the merge appears clean.
- **Run the tests after resolving.** A syntactically valid resolution can be semantically
  wrong, and no tool will tell you.
- **Never commit conflict markers.** Add a lint or hook that rejects `<<<<<<<` outright: it
  happens to everyone eventually, and it is trivially detectable.
- **`git rerere` is worth enabling** on long-running work, since it remembers how you
  resolved a conflict and replays it when the same one recurs during repeated rebases.

---

## 5. Pull requests and review

- **Keep pull requests small.** Review quality collapses past a few hundred changed lines:
  beyond that, reviewers approve rather than review, and defect detection approaches zero.
  If a change cannot be made small, split it into a stack of dependent PRs that each stand
  alone.
- **Write the description for someone with no context**: what changed, why, how to verify,
  and what could break. Link the issue and include screenshots for anything visual.
- **Say what you want from the review.** "Please check the locking in `transfer()`" gets a
  better review than silence, which gets you a comment about variable naming.
- **Open a draft PR early** for anything large. Directional feedback before the work is
  finished is worth more than approval after.
- **Review the change, not the person**, and mark clearly which comments block merging and
  which are optional. A review that mixes a security flaw with a preference about naming, at
  equal weight, communicates neither.
- **Reviewing is a normal, high-value use of your time.** A PR sitting for two days blocks a
  colleague and rots against a moving base branch.
- **Merge your own PR after approval** (unless your process says otherwise), and merge only
  green. Merging a red build to fix it afterwards breaks the branch for everyone.

---

## 6. What belongs in the repository

- **Add `.gitignore` in the first commit**, before anything can be added by accident.
  Ignore build output, dependency directories, editor and OS files, logs, coverage reports,
  and local environment files. Use a language-appropriate template as a starting point.
- **`.gitignore` does not untrack what is already tracked.** Adding a pattern for a
  committed file changes nothing; you also need `git rm --cached`.
- **Commit lockfiles for applications** (`package-lock.json`, `poetry.lock`, `Cargo.lock`,
  `go.sum`). They are what make a build reproducible. Libraries usually do not commit them.
  See `security.md` §9.
- **Commit an example environment file** (`.env.example`) with every required key present
  and every value a placeholder. Never commit the real one.
- **Never commit secrets.** Not keys, tokens, certificates, connection strings, or
  credentials, not even briefly, not even in a branch you plan to delete. **A secret that
  reaches a remote is compromised and must be rotated**, because removing it from history
  does not remove it from clones, forks, PR views, or CI caches. See `security.md` §5.
- **Run secret scanning as a pre-commit hook and in CI.** Catching a key before it is pushed
  costs seconds; catching it afterwards costs a rotation.
- **Keep large binaries out.** Git stores every version of every binary forever, and a
  200MB asset committed once makes every clone slow permanently. Use Git LFS or external
  storage, and decide before the first commit, since fixing it later requires rewriting
  history.
- **Do not commit generated files** that the build produces, with the deliberate exceptions:
  lockfiles, generated code that consumers need without your toolchain, and vendored
  dependencies where you have chosen vendoring on purpose. Anything committed and generated
  needs a CI check that it is up to date, otherwise it will silently drift.

---

## 7. Recovering and investigating

- **`git reflog` is the undo button** and almost nothing is truly lost for a couple of
  weeks. A "destroyed" branch after a bad reset or rebase is nearly always recoverable:
  find the old head in the reflog and reset back to it. Check here before panicking.
- **Prefer `git revert` to `git reset` for anything published.** Revert creates a new commit
  that undoes the change, preserving history and working safely for everyone else. Reset
  rewrites, which on a shared branch is the problem in §4.1.
- **`git bisect` finds a regression in log2(n) steps** and is dramatically faster than
  reasoning about it. It works only if commits are atomic and individually buildable, which
  is the payoff for §2.1. Script the test and use `git bisect run` for full automation.
- **`git log -S "someString"`** finds the commit that introduced or removed a string, which
  is usually what you want when hunting for when a behaviour appeared. `git log -p <file>`
  and `git blame` cover the rest; use `git blame -w -C` to see through reformatting and code
  movement.
- **Use `git stash` sparingly.** Stashes are unlabelled, easy to forget, and invisible in
  normal workflows. A throwaway branch is usually better.
- **Cherry-pick deliberately.** It duplicates a commit rather than moving it, so the same
  change now exists twice with different hashes, which will surface as a conflict when the
  branches eventually merge. Legitimate for backporting a fix to a release branch; a smell
  when used as a substitute for merging.

---

## 8. Tags and releases

- **Tag releases with annotated tags** (`git tag -a v2.3.0 -m "..."`), not lightweight ones.
  Annotated tags carry a tagger, date, and message, and are proper objects that can be
  signed.
- **Follow semantic versioning** for anything others depend on, and mean it: a breaking
  change in a minor release breaks builds downstream and destroys trust in the version
  number.
- **Tags are immutable once published.** Moving a tag means two people who fetched "the same
  version" have different code, which is a genuinely hard class of bug to diagnose. Cut a
  new version instead.
- **Sign tags and release commits** where provenance matters.
- **Generate the changelog from history** if your messages support it, but keep a
  human-curated summary of what users care about. A raw commit dump is not release notes.

---

## 9. Automation and protection

Rules that are enforced hold; rules that are merely documented decay.

- **Protect `main`**: require pull requests, require passing status checks, require at least
  one approval, forbid force-pushes and deletion. This is a five-minute configuration that
  prevents entire categories of accident.
- **Use local hooks for fast feedback and server-side checks for enforcement.** Client hooks
  are not version-controlled by default, are trivially bypassed with `--no-verify`, and are
  never installed on a new clone unless something does it for them. Treat them as a
  convenience, never as a guarantee.
- **Keep pre-commit hooks fast.** Anything over a couple of seconds gets bypassed, and a
  bypassed hook enforces nothing. Lint and format the staged files only; leave the full
  suite to CI.
- **Run in CI what actually matters**: build, tests, linting, formatting check, dependency
  audit, secret scan. Make them required checks so a red build cannot merge.
- **Use `CODEOWNERS`** to route reviews for sensitive paths (auth, payments, migrations,
  infrastructure) to the people who understand them.
- **Consider signed commits** (GPG, SSH, or gitsign) where supply-chain provenance matters,
  and require them on protected branches if you adopt them.
- **Pin third-party CI actions by commit SHA**, not by tag: tags are mutable, and a
  compromised action runs with your pipeline's credentials. See `security.md` §9.

---

## 10. Anti-patterns

- Commit messages reading `fix`, `wip`, `update`, `changes`, or `address review comments`.
- A commit that mixes a refactor with a behaviour change.
- A commit that mixes a reformat with anything at all.
- Commits that do not build, left "to be fixed in the next one".
- `git push --force` to a shared branch.
- Rewriting history that others have pulled.
- Committing secrets, then "removing" them in a later commit without rotating.
- Committing `.env`, build output, `node_modules`, or IDE configuration.
- Adding a `.gitignore` entry for an already-tracked file and expecting it to untrack.
- Large binaries committed directly instead of LFS.
- Long-lived feature branches instead of feature flags.
- Pull requests thousands of lines long.
- Merging a red build intending to fix it on `main`.
- Resolving a conflict by taking one side wholesale without reading the other.
- Committed conflict markers.
- Moving a published tag.
- Relying on client-side hooks as an enforcement mechanism.
- Working directly on `main`.

---

## Review checklist

**Commits**
- [ ] One logical change per commit; no "and" in the subject
- [ ] Refactors and reformatting separated from behaviour changes
- [ ] Every commit builds and passes tests independently
- [ ] Subject imperative, capitalized, no trailing period, ~50 chars
- [ ] Blank line before a body wrapped at ~72
- [ ] Body explains why, not what, wherever the change is not self-evident
- [ ] Issue referenced, with the symptom described in the message itself

**Branch and history**
- [ ] Branch is short-lived and named to convention; not committed to `main` directly
- [ ] Base branch integrated regularly, not only at the end
- [ ] No rewriting of history anyone else may have pulled
- [ ] Force-pushes use `--force-with-lease`
- [ ] Branch cleaned up before review, not during
- [ ] Repository's merge strategy applied consistently
- [ ] Conflicts resolved by reading both sides; tests run afterwards; no markers committed

**Pull request**
- [ ] Small enough to review properly, or split into a stack
- [ ] Description covers what, why, how to verify, and the risk
- [ ] Blocking and non-blocking review comments distinguished
- [ ] Green before merge; branch deleted after

**Repository contents**
- [ ] `.gitignore` present and covering build output, deps, editor files, env files
- [ ] Lockfile committed (applications); `.env.example` committed, real `.env` not
- [ ] No secrets in the diff or anywhere in history; any leak rotated, not just removed
- [ ] Secret scanning runs pre-commit and in CI
- [ ] No large binaries outside LFS
- [ ] Generated files either absent or CI-verified as current

**Protection**
- [ ] `main` protected: PR required, checks required, force-push and deletion forbidden
- [ ] Required checks cover build, tests, lint, format, audit, secret scan
- [ ] Hooks fast and treated as convenience, with enforcement server-side
- [ ] `CODEOWNERS` routes sensitive paths
- [ ] Releases tagged with annotated tags; published tags never moved
- [ ] Third-party CI actions pinned by SHA
