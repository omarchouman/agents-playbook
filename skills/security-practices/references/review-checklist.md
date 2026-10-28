# Review checklist: Security Practices

The condensed form of the `security-practices` skill. Use it as a review pass over a diff, or as a
pull-request template. Each item maps to a numbered section of that skill's SKILL.md,
so read the section when an item needs its reasoning.

## Review checklist

**Authentication**
- [ ] Argon2id/scrypt/bcrypt hashing via a maintained library
- [ ] No user enumeration in login, registration, or reset responses or timings
- [ ] Rate limiting and lockout on auth endpoints
- [ ] Reset tokens random, hashed at rest, single-use, short-lived
- [ ] Session id rotated on login and privilege change; logout invalidates server-side
- [ ] Cookies `HttpOnly`, `Secure`, `SameSite`; no tokens in `localStorage`
- [ ] JWTs (if used) verify pinned alg, `exp`, `iss`, `aud`; refresh tokens rotate and revoke
- [ ] MFA available; recovery codes hashed

**Authorization**
- [ ] Every endpoint checks object-level ownership/permission, not just the route
- [ ] Deny by default; policy centralized and testable
- [ ] Identity and role derived server-side only
- [ ] Mass assignment prevented by an explicit field allow-list
- [ ] Writes take the validated result, never the raw request body
- [ ] Multi-tenant queries scoped at a layer that can't be bypassed
- [ ] Non-human callers hold their own identity, not a shared or borrowed one
- [ ] Authority ceilings enforced server-side, with a human decision above the limit
- [ ] Destructive and bulk operations reviewable via dry run before they run
- [ ] Tests assert denial for anonymous, other-user, and lower-privilege callers

**Input**
- [ ] Schema validation at the boundary; allow-lists, not blocklists
- [ ] All lengths, ranges, sizes, and depths bounded, before per-element rules run
- [ ] Unexpected keys rejected at every level of nested input
- [ ] Framework input normalization (trimming, empty-to-null) understood and overridden where wrong
- [ ] All SQL parameterized; dynamic identifiers allow-listed
- [ ] Output escaped per context; no raw HTML injection; parsing sanitizer used for rich text
- [ ] CSP deployed without `unsafe-inline`/`unsafe-eval`
- [ ] No shell interpolation; path traversal prevented by resolve-and-verify
- [ ] No untrusted deserialization; no user input reaching `eval` or a template compiler
- [ ] SSRF controls on any user-supplied URL fetch; metadata endpoint blocked
- [ ] Text reaching a model is provenance-labelled, and no action of consequence depends on
      how a model read it
- [ ] Output derived from untrusted input stays untrusted when stored or displayed
- [ ] Uploads type-sniffed, size-limited, renamed, stored off-origin, never executed

**Secrets & transport**
- [ ] No secrets in the repo, client bundle, or logs; scanning in CI
- [ ] Secrets sourced from a manager/env at runtime; per-environment; rotatable
- [ ] HTTPS enforced with HSTS; certificate verification never disabled
- [ ] Security headers set; CORS origins allow-listed
- [ ] CSRF protection on cookie-authenticated state changes
- [ ] Redirect targets validated

**Data**
- [ ] Minimum data collected; retention defined and enforced
- [ ] Encrypted at rest and in transit; authenticated encryption; keys in a KMS
- [ ] CSPRNG for all security randomness; constant-time comparison for secrets
- [ ] No production personal data outside production

**Operations**
- [ ] No internal details in error responses; debug mode off in production
- [ ] Security events audited; logs shipped off-host and PII-redacted
- [ ] Alerting on auth-failure and authz-denial spikes
- [ ] Dependencies pinned, lockfile committed, scanning in CI, patch SLA defined
- [ ] CI/CD least-privilege, OIDC over static keys, third-party actions SHA-pinned
- [ ] `SECURITY.md` present; incident response plan documented
- [ ] Architecture tests enforce the structural invariants
- [ ] Destructive tooling refuses to run against production
