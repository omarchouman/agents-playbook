# Security Practices

Applies to any application handling user data, credentials, money, or third-party
integrations, in any language or framework. This is defensive guidance: how to build
software that resists attack, not how to attack.

**Read this before:** touching authentication or authorization, handling any user-supplied
input, storing or transmitting sensitive data, adding a dependency, or writing anything
that renders, executes, deserializes, or forwards data you didn't create.

---

## 1. Core principles

1. **All input is hostile until validated**: request bodies, headers, query strings, file
   uploads, webhook payloads, responses from third-party APIs, and messages from your own
   other services.
2. **Defense in depth.** Assume any single control will fail. The client validates *and* the
   server validates *and* the database constrains.
3. **Fail closed.** When authorization is uncertain, deny. When a security check errors,
   deny. A control that fails open is not a control.
4. **Least privilege, everywhere**: user roles, service accounts, database users, API
   tokens, container capabilities, CI credentials.
5. **Never invent cryptography or authentication.** Use the vetted, maintained library for
   your platform. Every hand-rolled token scheme has the same bugs.
6. **Security is a property of the design.** Bolting it on at the end produces the
   vulnerabilities in this document.

---

## 2. Authentication and session management

### 2.1 Passwords

- **Hash with a memory-hard algorithm: Argon2id (preferred), scrypt, or bcrypt.** Never
  MD5, SHA-1, SHA-256, or any fast hash. Those are designed for speed, which is precisely
  what an offline cracker wants.
- **Never implement your own password hashing, salting, or comparison.** The library handles
  salting and the encoded parameters. Use its constant-time verify function.
- **Enforce length, not composition.** Minimum 12 characters; do not require symbols or
  force rotation on a schedule; both drive predictable, weaker passwords. (NIST SP 800-63B.)
- **Check against a breached-password list** (e.g. Have I Been Pwned's k-anonymity range API,
  which never sends the full hash).
- **Set a maximum length** (e.g. 128) so a 10MB password can't become a CPU exhaustion
  attack, but never truncate silently.
- **Rehash on login when your parameters change**, transparently.

### 2.2 Login flows

- **Never reveal whether an account exists.** Login, registration, password reset, and
  "resend verification" must all return the same generic message and take similar time.
  Enumeration feeds credential stuffing.
- **Rate-limit by both account and source IP**, with progressive delay and temporary
  lockout. Alert on distributed attempts across many accounts.
- **Password reset tokens**: cryptographically random (≥128 bits), stored **hashed**,
  single-use, short-lived (15–60 min), invalidated on use and on password change.
- **Rotate the session identifier on every privilege change**: login, elevation,
  re-authentication. Failing to do so is session fixation.
- **Invalidate all other sessions on password change**, and offer the user a visible
  session list with revoke.
- **Require the current password** to change email, password, or MFA settings.
- **Support MFA (TOTP or WebAuthn) for any account with real value.** Prefer WebAuthn/
  passkeys, phishing-resistant by design. SMS is the weakest option (SIM swap); offer it
  only as a fallback. Issue single-use recovery codes and store them hashed.

### 2.3 Sessions and tokens

- **Prefer server-side sessions with an opaque cookie identifier** for browser applications.
  Simple, revocable, and no token parsing to get wrong.
- **Cookie flags are mandatory:**
  ```
  Set-Cookie: sid=…; HttpOnly; Secure; SameSite=Lax; Path=/; Max-Age=…
  ```
  `HttpOnly` (JavaScript cannot read it, blunting XSS token theft), `Secure` (HTTPS only),
  `SameSite=Lax` or `Strict` (CSRF defense). Use `__Host-` prefixed names where applicable.
- **If you use JWTs, know what you're taking on.** They are not revocable without extra
  state, which defeats their main selling point. Rules if you do:
  - **Pin the algorithm server-side.** Never trust the `alg` header; explicitly reject
    `none` and reject an asymmetric-to-symmetric algorithm switch.
  - Verify signature, `exp`, `nbf`, `iss`, and `aud`, every time.
  - Keep access tokens short-lived (5–15 min) with a rotating, revocable refresh token;
    detect refresh-token reuse and revoke the whole family.
  - Never put secrets or PII in the payload; it is base64, not encrypted.
- **Never store tokens in `localStorage`.** Any XSS reads it instantly. Use an `HttpOnly`
  cookie.
- **Enforce absolute and idle session lifetimes**, tuned to sensitivity.
- **Logout must invalidate server-side**, not merely delete the client's cookie.

### 2.4 API credentials

- **Generate API keys with a CSPRNG (≥256 bits) and store only a hash.** You cannot show
  them again, and that's correct.
- **Prefix keys for identification and secret-scanning** (`sk_live_…`), and include a
  checksum so scanners can detect leaks with low false positives.
- **Scope keys** to specific permissions and, where possible, source IPs. Support rotation
  with an overlap window, and expiry.
- **For machine-to-machine auth, prefer short-lived credentials** (OIDC federation,
  workload identity) over long-lived static keys.

---

## 3. Authorization

This is where the most damaging bugs live. Authentication answers "who are you";
authorization answers "may you do this to *this specific object*". The second question is
the one people forget.

- **Authorize on the object, not just the route.** The canonical vulnerability (IDOR /
  broken object-level authorization):

  ```python
  # ✗ Authenticated, but any user can read any invoice by changing the id.
  @require_login
  def get_invoice(id):
      return db.invoices.find(id)

  # ✓ Ownership is part of the query.
  @require_login
  def get_invoice(id, user):
      inv = db.invoices.find_one(id=id, account_id=user.account_id)
      if not inv: raise NotFound()   # 404, not 403; don't confirm existence
      return inv
  ```

- **Enforce authorization server-side, always.** Hidden buttons and client-side route guards
  are UX. The endpoint is the boundary.
- **Deny by default.** New endpoints should be inaccessible until a policy grants access;
  the opposite ordering guarantees that a forgotten annotation becomes a public endpoint.
- **Centralize policy** in one place (a policy layer, middleware, or row-level security) so
  it can be reviewed and tested. Authorization scattered across handlers cannot be audited.
- **Check authorization on every request**, including subsequent steps of a multi-step flow
  and every nested field in a GraphQL query.
- **Never accept identity or role from client input.** Not from a request body, not from a
  header, not from a hidden form field. Derive it from the authenticated session server-side.
  Ignore client-supplied `user_id`, `role`, `is_admin`, `account_id`.
- **Guard mass assignment.** Binding a whole request body to a model lets an attacker set
  `role`, `credit_balance`, or `email_verified`. Allow-list bindable fields explicitly.
- **Persist the output of validation, never the raw request.** The distinction is exact:
  the raw body is whatever the attacker sent, while the validated result contains only the
  fields you declared rules for. Passing the raw body to a create or update is mass
  assignment even when validation ran first, because validation checked the fields it knew
  about and passed the rest through untouched. Make the validated object the only thing in
  scope after the boundary, so reaching for the raw body requires deliberately going back
  for it. See `backend-and-api.md` §3 on parsing rather than validating.

  ```
  create(request.body)         ← ✗ validated, but every extra key rides along
  create(request.validated())  ← ✓ only declared fields exist
  ```
- **In multi-tenant systems, scope every query by tenant** at a layer that cannot be
  forgotten: a repository base class, a query scope, or database row-level security. A
  single unscoped query is a cross-tenant data breach.
- **Re-authenticate for sensitive actions**: changing credentials, disabling MFA, deleting an
  account, moving money, exporting data.
- **Prevent privilege escalation in role changes**: a user must not be able to grant
  themselves, or anyone, a role above their own.

---

## 4. Input handling and injection

The universal fix: **keep code and data separate**. Every injection class below is the same
bug: attacker data being interpreted as instructions.

### 4.1 Validation

- **Validate at the boundary with a schema**, before any logic. Allow-list what is
  acceptable; never blocklist what is dangerous (blocklists are always incomplete).
- **Bound everything**: string lengths, numeric ranges, array sizes, object depth, request
  body size, and upload size. Unbounded input is a denial-of-service vector.
- **Validate on the server even when the client already did.** The client can be bypassed
  entirely with a single `curl`.
- **Canonicalize before validating** (Unicode normalization, path resolution, URL decoding)
  so that an encoded payload can't slip past a check on the raw form. Decode exactly once;
  double-decoding reintroduces the problem.
- **Constrain the keys of an object or array, not only its values.** A rule set that
  validates the fields it knows about will happily accept twenty it does not, which is how
  an unexpected key reaches a mass-assignment sink (§3) or a downstream service that treats
  it as meaningful. Reject any key outside the allowed set, and apply that at every level of
  a nested structure rather than only the top.
- **Know what your framework silently rewrites before validation runs.** Common defaults
  include trimming whitespace from every string and converting empty strings to null. These
  are usually helpful and occasionally wrong: a "required" rule behaves differently once
  `""` has become `null`, a password with a deliberate trailing space is altered before it
  is hashed, and a field meaning "explicitly blank" cannot be distinguished from absent.
  Find out what the default middleware does, and exempt the fields where it is wrong.
- **Treat validation cost itself as an attack surface.** Rules applied across a wildcard
  over a large nested array can go quadratic, so an attacker who can post a
  ten-thousand-element array may consume seconds of CPU per request without ever submitting
  anything invalid. Bound the array size before the per-element rules run, not after.

### 4.2 SQL injection

- **Parameterized queries or a query builder. Always. No exceptions.**
  ```python
  cur.execute("SELECT * FROM users WHERE email = %s", (email,))   # ✓
  cur.execute(f"SELECT * FROM users WHERE email = '{email}'")     # ✗
  ```
- **Identifiers cannot be parameterized.** If a table, column, or sort direction is dynamic,
  map the client's value through a fixed allow-list. Never interpolate it.
- **Escaping is not a defense.** It fails on encoding edge cases and is one refactor away
  from being forgotten.
- The same rule holds for NoSQL (never pass a raw object where a scalar is expected; it can
  contain operators like `$ne`/`$gt`), LDAP, XPath, and ORM raw-SQL escape hatches.

### 4.3 Cross-site scripting (XSS)

- **Use a templating engine or framework that escapes by default**, and never disable it.
  `dangerouslySetInnerHTML`, `v-html`, `innerHTML`, `document.write`, and `|safe` are the
  places to look during review.
- **Escape for the correct context.** HTML body, HTML attribute, JavaScript, CSS, and URL
  contexts all need different encoding. Never inject untrusted data into a `<script>` block
  or an event handler attribute at all.
- **If you must render user-supplied HTML, sanitize with a maintained library**
  (DOMPurify, Bleach, sanitize-html) with a strict allow-list of tags and attributes. Never
  write your own sanitizer, and never use a regex.
- **Your language's tag-stripping helper is not a sanitizer.** Functions in the
  `strip_tags` family remove things that look like elements. They do not parse HTML, so they
  do not understand malformed markup that browsers recover from, they leave event-handler
  and `style` attributes on any tag you chose to keep, and they do not touch `javascript:`
  URLs. They are a formatting convenience for producing plain text, not a security control.
  If the output is rendered as HTML, it needs a real parsing sanitizer.
- **Validate URL schemes before rendering a link or `src`.** `javascript:` and `data:` URLs
  in an `href` are script execution. Allow-list `https:`, `http:`, `mailto:`.
- **Deploy a Content Security Policy.** A strict, nonce-based CSP is the strongest
  mitigation available:
  ```
  Content-Security-Policy: default-src 'self'; script-src 'nonce-{random}' 'strict-dynamic';
    object-src 'none'; base-uri 'none'; frame-ancestors 'none'
  ```
  Avoid `unsafe-inline` and `unsafe-eval`; with them the policy provides little protection.
  Roll out with `Content-Security-Policy-Report-Only` first.
- **Never pass user input to `eval`, `Function`, `setTimeout(string)`,** or a template
  compiler at runtime.

### 4.4 Command, path, and template injection

- **Never build a shell command from user input.** Use the array/`execve` form that bypasses
  the shell entirely (`subprocess.run(["convert", path])`, never `shell=True` with
  interpolation). If a shell is unavoidable, allow-list the input strictly.
- **Path traversal**: resolve the path, then verify it is still inside the intended
  directory. Never trust a filename from a client. Generate your own and store the original
  name as metadata only.
  ```python
  full = (base / user_supplied).resolve()
  if not full.is_relative_to(base.resolve()): raise Forbidden()
  ```
- **Never render a user-supplied string as a template.** Server-side template injection is
  usually remote code execution.
- **Never deserialize untrusted data with a format that can construct arbitrary objects**:
  Python `pickle`, Java native serialization, PHP `unserialize`, Ruby `Marshal`, unsafe YAML
  loaders. Use JSON with a schema. Guard against decompression bombs and deeply nested
  payloads.

### 4.5 SSRF (server-side request forgery)

Any feature that fetches a user-supplied URL (webhooks, image imports, link previews, PDF
rendering, integrations) can be turned against your internal network and cloud metadata
service.

- **Allow-list destination hosts** where possible.
- **Otherwise**: resolve the hostname, reject private/loopback/link-local ranges
  (`127.0.0.0/8`, `10/8`, `172.16/12`, `192.168/16`, `169.254/16`, `::1`, `fc00::/7`),
  disable redirects or re-validate after each one, and **re-check at connection time** to
  defeat DNS rebinding.
- **Block the cloud metadata endpoint** (`169.254.169.254`) explicitly, and require IMDSv2.
- **Send outbound fetches through an egress proxy** with its own allow-list where the
  feature warrants it.
- **Never forward internal credentials** on a user-directed request.

### 4.6 File uploads

- **Determine type by content sniffing, not by extension or `Content-Type`**; both are
  attacker-controlled.
- **Store outside the web root, with a generated name**, and serve through a handler that
  sets `Content-Disposition: attachment` and `X-Content-Type-Options: nosniff`. Serving
  user files from your primary origin risks stored XSS; use a separate domain.
- **Enforce a size limit at the proxy and the application**, and scan archives for zip bombs.
- **Never execute, include, or `import` an uploaded file.**
- **Strip EXIF metadata** from images; it commonly carries GPS coordinates.

---

## 5. Secrets management

- **Never commit a secret.** Not in code, config, tests, fixtures, comments, notebooks,
  Docker images, CI YAML, or a `.env` that isn't gitignored. Not "temporarily".
- **A committed secret is compromised, so rotate it.** Removing the commit does not help: it
  persists in reflogs, forks, clones, CI caches, and anything that mirrored it.
- **Use a secret manager** (Vault, AWS/GCP Secrets Manager, sealed secrets) or, at minimum,
  runtime environment variables injected by the platform.
- **Run automated secret scanning** in pre-commit hooks and CI (gitleaks, trufflehog);
  detection at commit time is far cheaper than rotation.
- **Rotate on a schedule and on personnel change.** Design for rotation from the start:
  support two valid keys during an overlap window.
- **Different secrets per environment**, always. A development key that works in production
  is a production incident waiting for a laptop to be stolen.
- **Never log a secret**, including in exception traces, request dumps, and debug output.
  Redact in the logging layer, not at each call site.
- **Client-side code has no secrets.** Anything in a browser bundle or a mobile app binary is
  public, including `NEXT_PUBLIC_*`-style variables and anything obfuscated.

---

## 6. Transport, headers, and browser controls

- **HTTPS everywhere, with HTTP redirected.** TLS 1.2 minimum, 1.3 preferred. No mixed
  content.
- **HSTS**: `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload`.
- **Never disable certificate verification.** `verify=False`, `rejectUnauthorized: false`,
  and `-k` are how a debugging workaround becomes a permanent MITM vulnerability.
- **Set the standard security headers:**
  ```
  Strict-Transport-Security: max-age=31536000; includeSubDomains
  Content-Security-Policy: …            (see §4.3)
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=()
  ```
  `frame-ancestors 'none'` in CSP supersedes `X-Frame-Options` for clickjacking defense.
- **CORS: never reflect the `Origin` header, and never use `*` with credentials.**
  Allow-list exact origins. `Access-Control-Allow-Origin: *` plus
  `Allow-Credentials: true` is invalid and, where honored, catastrophic.
- **CSRF protection for cookie-authenticated state changes**: `SameSite` cookies plus
  synchronizer tokens or the double-submit pattern. Token-header auth (no cookies) is not
  CSRF-vulnerable, but check that your API doesn't *also* accept the cookie.
- **Validate redirect targets against an allow-list.** An open redirect
  (`/login?next=https://evil.example`) is a phishing primitive and an OAuth token-theft
  vector.
- **`rel="noopener noreferrer"` on `target="_blank"` links** to untrusted destinations.
- **Rate-limit and throttle** at the edge and in the application. Stricter budgets on login,
  registration, password reset, search, export, and anything that sends email or SMS. Return
  `429` with `Retry-After`.

---

## 7. Logging, errors, and monitoring

- **Never leak internals in a response**: no stack traces, SQL, framework versions, internal
  hostnames, or file paths. Return a generic message plus a correlation id; log the detail.
  Disable debug mode and verbose error pages in production; verify this, don't assume it.
- **Never log** passwords, tokens, session ids, API keys, full card numbers, CVVs, national
  ids, health data, or full request bodies from authentication endpoints. Redact centrally.
- **Do log security-relevant events**, with actor, action, target, source IP, user agent,
  timestamp, and outcome: login success/failure, MFA changes, password and email changes,
  permission and role changes, API key creation, admin actions, data exports, and
  authorization denials.
- **Make audit logs tamper-evident and append-only**, with retention that matches your
  compliance obligations. Ship them off-host, since an attacker's first move is the local log.
- **Alert on attack signal**: authentication failure spikes, authorization-denial spikes
  (often enumeration in progress), unusual data-export volume, new admin grants, and traffic
  from unexpected regions.
- **Beware log injection.** Strip CR/LF from user-controlled values before logging, or use a
  structured logger that encodes them; otherwise attackers forge log entries.

---

## 8. Data protection and privacy

- **Collect the minimum.** Data you never collected cannot be breached, subpoenaed, or
  mishandled. Challenge every new field that identifies a person.
- **Encrypt in transit (TLS) and at rest** (disk/volume encryption plus column-level
  encryption for the most sensitive fields).
- **Use authenticated encryption**, AES-GCM or XChaCha20-Poly1305, via a high-level
  library (libsodium, `cryptography`'s Fernet, your cloud KMS). Never ECB. Never reuse a
  nonce. Never design your own construction.
- **Manage keys in a KMS/HSM**, separate from the encrypted data, with rotation support and
  a documented re-encryption path.
- **Tokenize or avoid regulated data.** Do not store raw card numbers; use a payment
  provider's token and stay out of PCI scope. Treat health and biometric data as requiring
  specialist handling.
- **Set and enforce retention.** Automatically delete what you no longer need; a retention
  policy nobody implemented is a liability.
- **Support deletion and export** where the law requires it (GDPR, CCPA), and make sure it
  reaches backups, logs, analytics, caches, and third-party processors.
- **Never use production personal data in development, testing, demos, or LLM prompts.**
  Anonymize or generate. See `database-and-migrations.md` §7.
- **Use constant-time comparison for secrets** (tokens, HMACs, signatures):
  `hmac.compare_digest`, `crypto.timingSafeEqual`. `==` leaks length and content via timing.
- **Generate all security-relevant randomness with a CSPRNG**: `secrets`, `crypto.randomBytes`,
  `SecureRandom`. Never `Math.random()`, `rand()`, or a seeded PRNG for tokens, ids,
  passwords, or nonces.

---

## 9. Dependencies and supply chain

- **Commit the lockfile and install from it** with the frozen/CI flag. Reproducible builds
  are the baseline for knowing what you shipped.
- **Pin exact versions for applications**; use ranges only for published libraries.
- **Run vulnerability scanning in CI** (`npm audit`, `pip-audit`, `govulncheck`, Dependabot,
  Snyk, Trivy) and fail the build on high/critical findings in reachable code.
- **Vet a dependency before adding it**: maintenance activity, download volume, maintainer
  count, transitive weight, and whether the platform already does it. Every dependency runs
  with your application's full privileges.
- **Watch for typosquats and install scripts.** Verify the exact package name. Disable
  post-install scripts where your toolchain allows.
- **Patch promptly, on a defined SLA.** Most breaches exploit a known vulnerability with an
  available patch. Automate the routine upgrades so the urgent ones aren't buried.
- **Pin container base images by digest, use minimal bases** (distroless/alpine), scan
  images, run as a non-root user, and mount the filesystem read-only where possible.
- **Lock down CI/CD**: least-privilege tokens, OIDC federation instead of long-lived cloud
  keys, no secrets exposed to pull requests from forks, and pinned third-party actions by
  commit SHA. Your CI system can deploy to production, so treat it as production.

---

## 10. Secure development lifecycle

- **Threat-model any feature touching auth, money, PII, or file handling.** Four questions
  are enough for most cases: What can an attacker reach? What do they gain? What stops them?
  How would we know it happened?
- **Design first, review the design.** Authorization models and token flows are enormously
  more expensive to change after launch.
- **Automate what you can**: SAST/linters with security rules, dependency scanning, secret
  scanning, and IaC scanning in CI.
- **Encode your invariants as architecture tests.** A rule that only exists in a document
  degrades; a rule enforced by a failing build does not. Most ecosystems have a way to
  assert structural facts in the test suite, and the ones worth asserting are the boring
  ones people get wrong: no environment reads outside the config layer, no debug or dump
  helpers in committed code, domain code importing nothing from the framework, controllers
  never touching the raw request body, every endpoint carrying an authorization annotation.
- **Guard destructive tooling against production**, including your own maintenance scripts,
  and remember that automation and coding agents execute commands without the hesitation a
  human would have. See `database-and-migrations.md` §7.
- **Write regression tests for security fixes**: the same test that reproduces the
  vulnerability keeps it fixed.
- **Test authorization explicitly**: for each protected endpoint, assert that an anonymous
  user, a different user, and a lower-privileged user are all denied. This is the single
  highest-value security test suite you can write.
- **Have a documented incident response plan** before you need it: who is called, how you
  contain, how you rotate credentials, how you preserve evidence, and your legal disclosure
  deadlines (GDPR is 72 hours). Rehearse it.
- **Provide a way to report vulnerabilities**: `SECURITY.md` and a `/.well-known/security.txt`
  with a monitored contact. Researchers who can't reach you disclose publicly.

---

## 11. Anti-patterns

- Passwords hashed with SHA-256/MD5, or "encrypted" so they can be recovered.
- Authorization by route only, with no object-level ownership check (IDOR).
- Trusting `user_id`, `role`, `is_admin`, or `account_id` from client input.
- Binding a whole request body to a model without an allow-list (mass assignment).
- Persisting the raw request body instead of the validated result.
- Using a `strip_tags`-style helper as XSS protection.
- String-concatenated SQL, or shell commands built by interpolation.
- Auth tokens in `localStorage`; cookies without `HttpOnly`/`Secure`/`SameSite`.
- JWT verification that trusts the `alg` header, or skips `exp`/`aud`/`iss`.
- `verify=False` / `rejectUnauthorized: false` / `curl -k` in committed code.
- CORS reflecting the `Origin` header, or `*` with credentials.
- Secrets in the repository, in the client bundle, or in logs.
- `Math.random()` for tokens, ids, or password resets.
- `==` comparison on tokens, signatures, or HMACs.
- Stack traces and debug pages enabled in production.
- Fetching a user-supplied URL with no SSRF controls.
- Deserializing untrusted `pickle`/`Marshal`/native-serialization data.
- Trusting a file's extension or `Content-Type` on upload; serving uploads from the app origin.
- Different error messages or response times for "no such user" vs "wrong password".
- No rate limiting on login, reset, or expensive endpoints.
- Production data copied into a development database.
- Security controls implemented only on the client.

---

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
