# Review checklist: Git and Version Control Practices

The condensed form of the `git-practices` skill. Use it as a review pass over a diff, or as a
pull-request template. Each item maps to a numbered section of that skill's SKILL.md,
so read the section when an item needs its reasoning.

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
