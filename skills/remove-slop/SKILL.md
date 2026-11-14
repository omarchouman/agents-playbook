---
name: remove-slop
description: >-
  Audits an application that already exists for the defects that make it feel unfinished or
  machine-generated: slow pages, missing loading and error states, N+1 queries, oversized
  JavaScript, a default template nobody changed, no 404 page, no meta description, no sitemap,
  no privacy policy, terms or cookie consent, no rate limit on generation endpoints, keys shipped in the client bundle, and a mobile layout
  nobody opened. Use this whenever the user asks to clean up, polish, audit, harden, speed up or
  ship an app, says it feels slow, janky, cheap, unfinished or AI-generated, asks what is wrong
  with it, or asks whether it is ready to launch, and use it when they invoke it directly as
  /agents-playbook:remove-slop. Read references/measurement.md before claiming any performance
  finding, references/probes.md when delegating passes to subagents,
  references/slop-catalogue.md for the complete item list with the check for each, and
  references/review-checklist.md for the pre-ship pass.
---

# Remove Slop

An audit of an application that already exists. The other skills in this plugin are
generative: they apply while code is being written. This one is diagnostic. It starts
from a running app and asks what is wrong with it, in what order that matters, and with
what evidence.

That difference decides what belongs here. This skill owns the procedure, the evidence
rule and the ranking. It does not own the fixes. When a finding has a rule behind it, the
rule lives in a practice skill and this file points at it rather than restating it, so a
rule that changes changes in one place.

**Read this before:** auditing, polishing or hardening an existing app, preparing a launch,
answering "why does this feel slow", or deciding whether something is ready to show anyone.

**Not for:** writing new code. Use the practice skills for that. An audit that turns into a
rewrite has stopped being an audit.

---

## 1. How to run this audit

- **Measure before you claim.** Every finding carries either a command output, a file and
  line, or a number you observed. Without that rule an audit degrades into a list of things
  that are usually true of web apps, which is unfalsifiable and therefore unfixable. The
  commands are in [references/measurement.md](references/measurement.md); read it before
  writing any performance finding.
- **Run in this order: scan, probe, rank, fix.** Each stage narrows the next. Scanning first
  is what stops four subagents independently rediscovering the framework and the build
  directory, and ranking before fixing is what stops a session spent on a 4KB image while a
  3MB bundle ships.
- **A finding without a cost is not a finding.** State what the user loses: a wait in
  seconds, a broken flow, a page that cannot be shared, data exposed. "Not best practice" is
  not a cost, and anything you can only justify that way belongs in §11 rather than in the
  report.
- **Prefer the tool over the opinion.** Where a linter, a bundler analyzer, a query planner
  or a Lighthouse run can answer the question, run it and quote it. Your reading of the code
  is a hypothesis; the tool output is the finding.
- **Stop when the ranked list stops being worth fixing.** An audit that returns sixty items
  returns nothing, because nobody triages sixty items. Twelve ranked findings with evidence
  beat a complete inventory.

## 2. Triage

Work out what the app is before judging it, and let the cheap deterministic pass go first.

- **Run [scripts/slop-scan.py](scripts/slop-scan.py) first, and read its output before anything else.** It is
  deterministic, it finishes in seconds, and it answers the questions every later pass would
  otherwise repeat: what the stack is, where the build output lands, which routes exist. It
  also settles the mechanical items outright, so no agent spends a turn deciding whether a
  meta description is present.
- **Decide fan-out against a threshold, not a feeling.** Delegate the four passes in §10 to
  subagents when the codebase is large enough that one pass means reading dozens of files and
  only the conclusion matters. Below that, run the same passes inline in the same order. Four
  cold agents on a twelve-file project cost more than they return.
- **Verify the subagent tool exists rather than assuming it.** These skills run in Claude
  Code, in other agents, and from a plain file. A procedure that assumes a tool it never
  checked for fails at the point where it was supposed to help. The inline path is not a
  degraded mode: it is the same passes in sequence.
- **Ask what the app is for before calling anything a defect.** An internal admin tool with
  four users does not need a sitemap, an OG image or a sub-second cold start, and flagging
  them wastes the one pass of attention you get. A public marketing page needs all three.
  The catalogue in [references/slop-catalogue.md](references/slop-catalogue.md) marks which
  items depend on this.

## 3. Shipping blockers

These are not polish. Each one is a live defect, and they come first in the report whatever
else is found.

- **Look for credentials in anything the browser downloads.** Grep the built bundle, not the
  source, because a key read from an environment variable at build time is inlined into the
  output and no longer looks like a secret in the repo. A key in the bundle is published to
  everyone who loads the page. See `security-practices` §5.
- **Check that a hosted database key is backed by row-level rules.** A public anon key is
  designed to be shipped, which means the access rules are the only thing standing between a
  visitor and the whole table. The key being public is expected; the table being readable is
  the bug. See `security-practices` §3.
- **Flag any endpoint that triggers generation, email or payment and has no rate limit.** The
  cost is unbounded and it is someone else's to trigger: one script turns an AI endpoint into
  a bill. Return 429 with a retry hint, per `backend-practices` §2.2.
- **Check whether errors reach the user as stack traces.** A stack trace tells an attacker
  the framework, the file layout and often the query, and it tells the user nothing they can
  act on. See `security-practices` §7, and give the user a next step instead, per
  `backend-practices` §4.1.
- **Confirm debug mode is off and source maps are not served in production.** Both are
  defaults in development and both survive a deploy unnoticed, because nothing visibly breaks
  when they ship.
- **Check CORS is not set to a wildcard with credentials.** It is the configuration people
  reach for when a request fails and the error mentions CORS, and it turns every other origin
  into a trusted one. See `security-practices` §6.
- **Confirm no `.env` file is committed.** Check the history, not just the working tree: a
  secret removed in a later commit is still in the clone. See `git-practices` §6.

## 4. Speed you can measure

Server-side work, where the numbers are unambiguous.

- **Find the N+1 before optimising anything else.** It is the single most common cause of a
  page that was fast with ten rows and unusable with a thousand, and the fix is usually one
  line. Enable query logging and count the queries for one request, per
  `database-practices` §4.2.
- **Check the slow queries against the planner, not against intuition.** A sequential scan on
  a table that has grown is invisible in the code and obvious in `EXPLAIN`. Indexes and the
  things that silently disable them are in `database-practices` §3.
- **Flag any list endpoint without pagination.** It works until the table grows, then it
  takes the server and the client down together, and it fails in production rather than in
  development because that is where the rows are. See `database-practices` §4.3 for keyset
  pagination and `backend-practices` §2.3 for the contract.
- **Flag a query that selects every column to use two.** The cost is paid in bytes over the
  wire and in indexes that would otherwise have covered the query. See
  `database-practices` §4.2.
- **Check that connections are pooled and the pool is sized.** Without a pool, each request
  pays connection setup; with an unbounded one, a traffic spike exhausts the database instead
  of queueing. See `database-practices` §7.
- **Look for duplicate requests for the same data in one page load.** Two components each
  fetching the current user is the usual shape, and it doubles a cost nobody attributes to
  either component. See `frontend-practices` §4.
- **Look for sequential awaits that have no dependency between them.** Three independent
  calls run in series take their sum instead of their maximum, and the fix is a single
  concurrent call.
- **Check every outbound call has a timeout.** Without one, a slow third party becomes your
  outage, because your workers block on a response that never arrives. See
  `backend-practices` §7.
- **Move anything slow out of the request.** Email, image processing, report generation and
  model calls all belong on a queue, per `backend-practices` §8. A user waiting on work that
  did not need to be synchronous is the easiest win in this whole list.
- **Check compression and caching are on.** Brotli or gzip on text responses, and cache
  headers on anything content-addressed. Both are configuration rather than code, both are
  frequently absent, and together they often halve transfer. Caching rules are in
  `backend-practices` §9.
- **Check there is a way to see slow requests in production.** Without tracing, the only
  available evidence about the real system is a user saying it felt slow. See
  `backend-practices` §10.2.

## 5. Speed the user feels

Perceived performance is a separate axis from measured performance, and an app can be fast
and still feel broken.

- **Flag content that appears without a reserved space.** The page that jumps while loading
  costs the user the click they were about to make. See `frontend-practices` §7.3.
- **Flag a fetch with no loading state.** A blank region is indistinguishable from a broken
  one, so the user reloads or leaves. Skeletons and the four async states are in
  `frontend-practices` §4.
- **Check model responses stream.** Waiting ten seconds for a complete answer and waiting ten
  seconds for an answer that started after one feel entirely different, and only one of them
  gets abandoned. See `backend-practices` §2.6.
- **Check search and autocomplete are debounced.** Firing on every keystroke spends requests
  the user never needed and arrives out of order, so the results flicker between answers. See
  `frontend-practices` §4.
- **Use optimistic updates where the action nearly always succeeds, and only there.** A like
  button that waits for a round trip feels broken. An optimistic update with no rollback path
  shows the user a success that did not happen, which is worse than the wait.
- **Check images below the fold are lazy.** They compete for bandwidth with content the user
  is actually looking at.
- **Check the empty state exists and says what to do next.** The first screen a new user sees
  is usually the empty one, and a blank table is where they decide the product does not work.

## 6. Payload and delivery

- **Measure the JavaScript the first page actually downloads, then compare it to a budget.**
  Without a number this is all taste. The budgets and the commands are in
  [references/measurement.md](references/measurement.md).
- **Split by route.** A single bundle makes the landing page pay for the dashboard, and the
  landing page is the one visitors actually load.
- **Defer third-party scripts.** Analytics, chat widgets and cookie banners are rarely
  needed before paint, and each one blocks it while fetching from a host you do not control.
- **Self-host fonts.** A font from a third-party CDN is a connection to another origin before
  text can render, plus a dependency on their uptime for your typography. See
  `frontend-practices` §7.1.
- **Serve WebP or AVIF, and size the image to its container.** A 3000px JPEG rendered at
  400px wide is the most common single payload defect in a vibecoded app, and the browser
  pays for every one of those pixels.
- **Set cache headers on static files and serve them from a CDN.** Content-addressed assets
  can be cached indefinitely; without the header the browser re-fetches them on every visit.
- **Remove unused dependencies.** They inflate installs, widen the vulnerability surface and
  mislead the next reader about what the app uses. See `security-practices` §9.

## 7. The template tells

The signals that a project was generated and never finished. Individually trivial, and the
reason the whole thing reads as unfinished when several appear together.

- **Check the page title, the favicon and the meta description are the project's own.** A tab
  still reading "Create Next App" or showing a default logo is the first thing a visitor
  sees, and it says nobody looked at this page.
- **Flag the untouched starter theme.** The indigo-to-purple hero gradient, the default
  component library palette and the stock hero layout are recognisable because they are
  shipped unchanged so often. This is a real finding and it is also the one most easily
  overstated: report the specific unchanged defaults, not a verdict on the design.
- **Grep for placeholder text.** Lorem ipsum, "Your Company", "example@example.com" and
  stock testimonials survive to production regularly, because they look like content.
- **Check footer and navigation links resolve.** A dead link in a footer is not an oversight
  the visitor forgives: it is evidence that nothing on the page was checked.
- **Check the console is clean on the main flows.** Leftover logs leak internals and bury the
  errors that matter under noise nobody reads any more.

## 8. Trust and completeness

What a visitor, a crawler or a reviewer needs before the app counts as a real product.

- **Check a custom 404 exists and offers a way back.** The default framework error page is
  where a visitor leaves, and broken links are normal rather than exceptional.
- **Check the meta description, canonical URL and share preview image.** Without an OG image
  a shared link renders as a grey box, which on every social platform is the difference
  between a click and a scroll past.
- **Check `robots.txt` and a sitemap exist for anything public.** Without them a crawler
  discovers only what it stumbles into.
- **Check the privacy policy exists, and treat its absence as a defect rather than a
  nicety.** Any app with a form, an account, server logs or analytics is processing personal
  data, which in the EU, the UK, California and a growing list of others carries a legal
  obligation to say what is collected, why, how long it is kept and how to have it deleted.
  A generated app almost never has one, because nothing in the build fails without it. The
  cost is regulatory exposure and a blocked payment processor, and the fix is cheap only
  before launch.
- **Check the terms of service exist wherever there are accounts, payment or user content.**
  Without them there is no stated basis for suspending an abusive account, no limitation of
  liability and no governing law, so the first dispute is argued from nothing. Stripe, the
  app stores and most B2B procurement reviews all ask for them by name.
- **Check the cookie policy and the consent mechanism when anything non-essential is set.**
  This one is missed most often, because the tracker usually arrives as a single analytics
  snippet that nobody thinks of as data collection. If the app loads Google Analytics, a
  Meta pixel, a session recorder or any advertising tag, consent is required before the tag
  runs, not after, and a banner that merely announces cookies while setting them is the
  common non-compliant pattern rather than a fix.
- **Check whether tracking fires before consent is given.** Load the page with a clean
  profile and look at the network requests and the cookies set before any interaction. A
  consent banner that does not gate the tag is worse than no banner, because it documents
  that the collection was known about. Cookieless analytics such as Plausible or Fathom
  avoid the whole question, which is often the better fix.
- **Check a contact route exists.** Data-protection law assumes a way to reach someone, and
  independently of that, an app with no contact page cannot be told about the bug you just
  shipped.
- **Check the app behaves on a shared link.** A deep link that only works after a client-side
  navigation is broken for everyone arriving from outside.

## 9. Mobile and real devices

- **Check the viewport meta tag is present.** Without it a mobile browser renders the desktop
  layout scaled down, which is the single-line cause of most "looks bad on mobile".
- **Test at 375px and confirm nothing scrolls horizontally.** A fixed width or an unwrapped
  table is the usual cause, and it is the most reliable signal that nobody opened the app on
  a phone.
- **Check tap targets are large enough to hit.** Controls sized for a cursor are a different
  product on a touchscreen.
- **Test on a throttled network and a throttled CPU.** Everything is fast on the machine that
  built it. The one measurement that changes people's minds is the app on a mid-range phone
  over slow mobile data, and the commands for it are in
  [references/measurement.md](references/measurement.md).

## 10. Running the passes

Four passes, whether delegated or run inline. They are split so that two passes rarely read
the same file, which is what makes delegation worth its overhead.

1. **Payload and delivery**: build output, bundler config, fonts, images, third-party scripts.
2. **Data access**: queries, ORM calls, endpoints, indexes, pagination.
3. **Client behaviour**: loading, error and empty states, duplicate requests, debounce.
4. **Exposure**: credentials in the bundle, CORS, missing rate limits, debug flags.

- **Probes report, they never fix.** Findings come back to the main session and the edits
  happen there. Parallel agents editing the same files produce a diff nobody can review and
  conflicts nobody expected.
- **Every probe returns the same schema, or its findings are dropped.** Claim, evidence,
  cost, suggested fix. A probe that cannot measure something will estimate it unless the
  schema forces it to produce the evidence, and an audit full of confident estimates is worse
  than no audit, because it gets believed.
- **Give each probe the matching practice skill if it is available.** The data-access probe
  reviews against `database-practices`, the client probe against `frontend-practices`. A
  probe left to its own judgment reports what it personally dislikes.
- **Merge before ranking.** One root cause surfaces in several passes: an oversized bundle
  arrives from payload and again from mobile. Deduplicate by cause, not by wording.

The prompts and the schema are in [references/probes.md](references/probes.md).

## 11. Anti-patterns

- **Reporting what you did not measure.** The commonest failure of this skill. If the bundle
  was never built, there is no bundle finding.
- **Returning everything you found.** A ranked twelve gets fixed. A complete sixty gets
  skipped, and the three items that mattered are now indistinguishable from the rest.
- **Rewriting instead of fixing.** The audit identifies defects in an app someone has
  decided to keep. A proposal to rebuild it is a refusal to do the work.
- **Treating taste as a defect.** A purple gradient is evidence when it is the generator's
  untouched default and nothing else in the app was themed. It is not evidence when somebody
  chose purple.
- **Fixing the measurable because it is measurable.** Shaving 40ms off a query while the
  first paint waits on a render-blocking font is a real improvement that no user will notice.
- **Applying the public-product checklist to an internal tool.** Sitemaps and share images
  are findings only where someone would share or crawl the thing.

## Review pass

Before reporting, check the audit itself against
[references/review-checklist.md](references/review-checklist.md): every finding carries
evidence, every finding states a cost, the list is ranked, blockers are separated from
polish, and nothing in it is a rewrite.

The complete item list, with the check and the user-visible cost for each, is in
[references/slop-catalogue.md](references/slop-catalogue.md).
