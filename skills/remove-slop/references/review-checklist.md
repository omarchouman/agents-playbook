# Review checklist: Remove Slop

The condensed form of the `remove-slop` skill. Two passes: one over the audit itself before
reporting, one over the app before shipping. Each item maps to a numbered section of that
skill's SKILL.md, so read the section when an item needs its reasoning.

## Pass 1: the audit, before you report it

An audit nobody can act on is worse than none, because it consumes the attention a usable
one would have had.

- [ ] Every finding carries a file and line, or a quoted command output
- [ ] Every finding states what the user loses, not which rule it breaks
- [ ] Findings inferred from reading code are marked as unverified, not reported as defects
- [ ] Duplicates merged by cause, so one fix is one finding
- [ ] List ranked globally, not per pass
- [ ] Blockers separated from polish
- [ ] Twelve or fewer items, or a stated reason for more
- [ ] Nothing in the list is a proposal to rebuild
- [ ] Public-product items dropped if this is an internal tool
- [ ] Count of dropped unevidenced findings reported

## Pass 2: the app, before it ships

**Blockers**
- [ ] No credentials in the built client bundle
- [ ] Public database keys backed by row-level rules
- [ ] Rate limits on generation, email and payment endpoints
- [ ] No stack traces or framework error pages reaching users
- [ ] Debug mode off, source maps not served
- [ ] CORS not a wildcard with credentials
- [ ] No `.env` anywhere in git history

**Speed**
- [ ] Query count per request does not grow with rows
- [ ] Indexes on columns used in WHERE, JOIN and ORDER BY
- [ ] Every list endpoint paginated
- [ ] Timeouts on every outbound call
- [ ] Slow work queued, not done in the request
- [ ] Compression on, cache headers on static assets
- [ ] Slow requests visible in production

**Perceived speed**
- [ ] Loading state for every fetch, with space reserved
- [ ] Model responses stream
- [ ] Search and autocomplete debounced
- [ ] Optimistic updates roll back on failure
- [ ] Empty states exist and say what to do next
- [ ] Errors give a next step

**Payload**
- [ ] First-load JavaScript measured against a budget
- [ ] Routes code split
- [ ] Third-party scripts deferred
- [ ] Fonts self-hosted
- [ ] Images WebP or AVIF, sized to their slot, below-fold lazy
- [ ] No unused dependencies

**Finish**
- [ ] Title, favicon and meta description are the project's own
- [ ] Share preview image set
- [ ] Custom 404 that returns 404
- [ ] `robots.txt` and sitemap present for anything public
- [ ] Privacy policy, terms and a contact route if anything is collected
- [ ] No placeholder copy, no dead links, no console noise

**Mobile**
- [ ] Viewport meta tag present
- [ ] No horizontal scroll at 375px
- [ ] Tap targets large enough to hit
- [ ] Checked once with CPU and network throttling
