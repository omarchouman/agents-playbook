# Working in this repository

This repo is a Claude Code plugin whose content is prose: six skills that tell agents how to
build software. There is no application code, no test suite and no build. The work is writing
and editing rules, so the conventions below are about rules and commits, not about code.

General engineering practice is not repeated here. It lives in this repo's own skills, and
`skills/playbook-builder/SKILL.md` is the method that produced this file.

## Stop and ask

- **Rewriting published history.** The remote has been recreated once already to strip commit
  trailers. Any rebase, amend or force-push of `main` needs a decision from Omar first, because
  the history is public and others may have cloned it.
- **Deleting or renaming a skill.** The plugin is installable, so a skill name is a public
  identifier. Renaming one breaks anybody whose `CLAUDE.md` references it.
- **Changing what a rule claims, as opposed to how it reads.** Rewording is ordinary editing.
  Reversing a recommendation, or adding a rule that contradicts an existing one, is a content
  decision to raise rather than make.

## Autonomy

Commit and push without asking. One logical change per commit, pushed as it is finished rather
than batched, and report afterwards. This is a solo trunk-based repo, so direct commits to
`main` are correct here.

## Definition of done

A change is finished when both are true:

- [ ] `python3 scripts/validate.py` passes
- [ ] Committed and pushed to `origin main`

Local commits are not done. CI runs the same script on push, so a green local run should mean a
green remote one.

## Never write a rule a tool can check

`scripts/validate.py` enforces typography, cross-reference integrity, skill frontmatter,
manifest and filesystem agreement, link resolution and the absence of agent attribution. Those
things are therefore **not** conventions to remember, and they are deliberately absent from the
rules below.

When you notice a new mechanical convention, add a check to that script instead of a line to
this file. The playbook should shrink as enforcement grows.

## Writing rules

The house style, which is the reason these skills get followed rather than skimmed:

- **Every rule is an imperative claim, then its trigger, then its cost.** Without a trigger an
  agent cannot tell when the rule applies; without a cost it cannot tell a case the rule was
  built for from one where the rule does harm, so it either over-applies or abandons it.
- **Prose, not bullets of keywords.** A rule is a sentence that could be said aloud to a
  colleague. Fragments read as filler and get skipped.
- **Concrete over abstract.** Name the real command, the real status code, the real column type.
  "Return 409 on conflict" beats "handle conflicts appropriately".
- **"Prefer X" means X unless you can name the reason. "Never X" means never.** Use the second
  sparingly, and only where the apparent exceptions are really a design problem one level up.
- **Examples are illustrative, not prescriptive.** Pick whichever language makes the point
  clearest and say so, since these skills are language-agnostic.
- **No em-dashes.** Enforced by the validator, mentioned here only because it shapes how you
  draft: reach for a colon, a semicolon, a comma or a second sentence.

## Adding or changing a rule

- **A rule must survive a counter-example.** Before adding one, try to think of a real situation
  where following it would be wrong. If you find one, either scope the rule to exclude that case
  or state the exception in the rule itself. Rules that collapse on first contact are what make
  readers distrust the whole document.
- **Keep a rule where its trigger lives, even when that means repeating a cross-reference.**
  Validation appears in both `backend-practices` and `security-practices` because someone
  writing an endpoint and someone auditing for injection both need it at the moment they are
  working. Overlap at the seams is deliberate.
- **Cross-reference by skill name and section**, as `` `security-practices` §4.2 ``. The
  validator checks these resolve, so a section renumbering that breaks one fails the build.
- **When a rule changes, update that skill's `references/review-checklist.md` to match.** The
  checklist is the condensed form of the rules, so a rule without its checklist item is a half
  finished change. Same for `README.md` and `.claude-plugin/plugin.json` when a skill is added.
- **A skill's frontmatter `description` is the entire triggering mechanism.** It has to say both
  what the skill covers and the situations that should invoke it. A skill nobody triggers may as
  well not exist, so treat the description as the most load-bearing text in the file.

## Commits

- **Subject is imperative, capitalized, no trailing period, about 50 characters.** The log is
  consistent on this across its whole history; match it.
- **Write a body explaining why, for anything beyond a typo.** The diff shows what changed. The
  body is the only place the reasoning, the rejected alternative or the motivating bug can live.
  Nearly every commit here has one.
- **Never add agent attribution trailers.** Enforced by the validator. The remote was deleted
  and recreated once to remove them.
- **No Conventional Commits.** Zero of the commits here use `feat:`/`fix:` prefixes. There is no
  changelog automation consuming them, so the prefix would be ceremony. Do not introduce it
  without deciding to adopt it everywhere.

## Deliberate deviations

Things that look like the repo ignoring its own skills, and are not.

- **`main` has no branch protection, and there are no required reviews.** `git-practices` §9
  calls for both. They are written for repos with more than one committer, where protection
  stops one person's mistake reaching everyone. Here protection would only block the solo
  push-freely workflow above while protecting nobody. Revisit the moment a second committer
  appears, which is also when the rule starts paying for itself.
- **Skills exceed the 500-line guidance in places.** `backend-practices` is around 550. The
  guidance exists so a skill does not crowd out the task, and splitting a coherent set of rules
  into two files to satisfy a line count would cost more in navigation than it saves in context.
  The review checklists are already extracted, which is the split that pays.

## Verifying

| What | Command | Takes |
|---|---|---|
| Everything | `python3 scripts/validate.py` | under a second |

There is nothing to build and nothing to test beyond that. If a change needs verification the
script cannot give, that is a sign the script needs another check.
