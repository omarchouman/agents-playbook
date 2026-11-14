# Slop catalogue

Every item this skill looks for, with the check that proves it and the cost of leaving it.
The SKILL.md body carries the reasoning for the items that need it; this is the complete
list, for sweeping an app without missing a category.

**Scope column.** `any` applies everywhere. `public` applies only to something people find,
share or crawl, so it is not a finding in an internal tool. Applying the public list to an
admin panel is the fastest way to waste the one pass of attention an audit gets.

## Shipping blockers

Confirmed items here outrank everything else in the report.

| Tell | Check | Cost | Scope |
|---|---|---|---|
| Credentials in the client bundle | Grep built output, not source | Published to every visitor | any |
| Public database key with no row rules | Query a table as an anonymous client | Whole table readable | any |
| No rate limit on generation, email or payment | Call the endpoint in a loop | Unbounded cost, triggered by anyone | any |
| Stack traces shown to users | Force an error in production mode | Leaks internals, user gets no next step | any |
| Debug mode on in production | Check the env var the framework reads | Verbose errors, slow paths, exposed config | any |
| Source maps served publicly | Request the `.map` URL | Original source readable | any |
| Wildcard CORS with credentials | `curl -I` with an `Origin` header | Every origin becomes trusted | any |
| `.env` committed | Search the history, not the tree | Secrets in every clone | any |
| Endpoint with no authorization check | Call it without a session | Object-level access, see `security-practices` §3 | any |

## Speed you can measure

| Tell | Check | Cost | Scope |
|---|---|---|---|
| N+1 query | Compare query count at 1 row and 50 | Linear slowdown, fails in production not dev | any |
| Missing index | `EXPLAIN` the slow query | Sequential scan that worsens as data grows | any |
| List endpoint with no pagination | Call it against a large table | Server and client fail together, see `database-practices` §4.3 | any |
| `SELECT *` for two columns | Read the query, check the row width | Wasted bytes, index cannot cover the query | any |
| Offset pagination deep in a table | Time page 1 against page 500 | Each page slower than the last | any |
| No connection pooling or unbounded pool | Check the client config | Setup cost per request, or database exhaustion under spike | any |
| Duplicate requests per page load | Network tab, count identical calls | Doubled cost nobody attributes to one component | any |
| Sequential independent awaits | Read the handler | Sum of latencies instead of the maximum | any |
| No timeout on an outbound call | Check the client config | A slow third party becomes your outage, see `backend-practices` §7 | any |
| Slow work inside the request | Time the endpoint, find the blocking call | User waits for work that could be queued, see `backend-practices` §8 | any |
| No compression | `curl -I` for `content-encoding` | Several times the bytes on every text response | any |
| No cache headers on static assets | `curl -I` for `cache-control` | Re-downloaded every visit | any |
| No tracing or slow-request visibility | Look for an exporter or APM | The only evidence is a user saying it felt slow | any |
| No SSR or static generation where it fits | Check the render mode against the page's purpose | Blank page until JavaScript runs, and nothing to crawl | public |

## Speed the user feels

| Tell | Check | Cost | Scope |
|---|---|---|---|
| Fetch with no loading state | Throttle the network, watch the region | Blank looks broken, user reloads or leaves | any |
| Content without reserved space | Lighthouse CLS | Page jumps, the user misses the click | any |
| Model response not streamed | Watch a generation call | Ten silent seconds instead of one, then text | any |
| Search or autocomplete not debounced | Type and count requests | Wasted requests, results flicker out of order | any |
| Optimistic update with no rollback | Force the request to fail | User shown a success that did not happen | any |
| No optimistic update on a near-certain action | Click and watch for a round trip | Every interaction feels laggy | any |
| Images below the fold not lazy | Check the `loading` attribute | They compete with content the user is looking at | any |
| Missing empty state | Load as a new user | The first screen is blank, and that is where they decide | any |
| Error with no next step | Force one, read the message | User cannot act, see `backend-practices` §4.1 | any |

## Payload and delivery

| Tell | Check | Cost | Scope |
|---|---|---|---|
| JavaScript over budget | Build and measure against the budget table | Parse and execute time on a mid-range phone | any |
| No code splitting | One large chunk for every route | Landing page pays for the dashboard | any |
| Blocking third-party scripts | Lighthouse render-blocking audit | Paint waits on a host you do not control | any |
| Fonts from a third-party origin | Grep for the font CDN | Extra connection before text renders, see `frontend-practices` §7.1 | any |
| JPEG or PNG where WebP or AVIF fits | List images over 100KB | Several times the bytes for the same picture | any |
| Image far larger than its slot | Compare intrinsic size to rendered size | The browser pays for pixels nobody sees | any |
| No CDN for static files | Check the asset host | Every visitor fetches from one region | public |
| Unused dependencies | `npx depcheck` | Larger installs, wider vulnerability surface, see `security-practices` §9 | any |

## Template tells

| Tell | Check | Cost | Scope |
|---|---|---|---|
| Default page title | `curl` the page, read `<title>` | "Create Next App" in the tab is the first thing seen | public |
| Default favicon | Compare to the framework's shipped icon | Generic icon in the tab and in bookmarks | public |
| Untouched starter theme | Compare palette and hero to the generator default | Reads as unfinished, not as a design choice | public |
| Placeholder copy | Grep for lorem ipsum, "Your Company" | Visible evidence nobody read the page | public |
| Dead footer or nav links | Crawl the site | Suggests nothing on the page was checked | public |
| `console.log` in production | Open the console on the main flows | Leaks internals, buries real errors | any |

## Trust and completeness

| Tell | Check | Cost | Scope |
|---|---|---|---|
| No custom 404 | Request a missing path | Framework error page is where visitors leave | public |
| 404 returning 200 | Check the status code, not the page | Crawlers index pages that do not exist | public |
| No meta description | `curl` and grep | Search results show a scraped fragment | public |
| No share preview image | Grep for `og:image` | Shared links render as a grey box | public |
| No canonical URL | Grep for `canonical` | Duplicate URLs split ranking | public |
| No `robots.txt` or sitemap | Request both paths | Crawlers find only what they stumble into | public |
| No privacy policy | Check the routes, then whether the app has forms, accounts, payment or analytics | Processing personal data with none of the notice the law requires | any |
| No terms of service | Check the routes, weighted by whether there are accounts, payment or user content | No basis to suspend abuse, no liability limit, no governing law | any |
| No cookie policy | Only where a cookie-setting tracker is present | Non-essential cookies set with nothing explaining them | any |
| Tracking runs before consent | Load with a clean profile, watch requests and cookies before any click | Collection with no lawful basis, and a banner that documents it | any |
| No contact route | Check the routes | No way to report the bug you just shipped | public |
| Deep link only works after client navigation | Open the URL directly in a new tab | Broken for everyone arriving from outside | public |

Privacy, terms and cookies are listed separately on purpose. Reported as one line they read
as paperwork and get deferred together, and the privacy one is usually the obligation rather
than the nicety. Cookieless analytics such as Plausible or Fathom set no cookie, so they
trigger neither of the last two rows, which makes swapping to one a cheaper fix than building
a consent gate.

## Mobile and devices

| Tell | Check | Cost | Scope |
|---|---|---|---|
| No viewport meta tag | Grep the document head | Desktop layout scaled down, unreadable | any |
| Horizontal scroll at 375px | Screenshot at phone width | The clearest sign nobody opened it on a phone | any |
| Tap targets too small | Measure the control | Controls sized for a cursor, used by a thumb | any |
| Never tested throttled | Run Lighthouse with CPU and network throttling | Every judgment made on the fastest machine it will run on | any |
| Fixed element covering content | Scroll at phone width | Content unreachable behind a sticky bar | any |

## Accessibility and forms

Full rules are in `frontend-practices` §6. These are the ones that show up in generated code
often enough to be worth a sweep.

| Tell | Check | Cost | Scope |
|---|---|---|---|
| `div` used as a button | Grep for click handlers on non-interactive elements | Not reachable by keyboard or screen reader | any |
| No visible focus state | Tab through the page | Keyboard users cannot see where they are | any |
| Images with no alt text | Lighthouse accessibility audit | Unusable with a screen reader | any |
| Contrast below threshold | Lighthouse accessibility audit | Unreadable for low-vision users and in sunlight | any |
| Form submit not disabled while in flight | Double-click submit | Duplicate records, duplicate charges | any |
| No inline validation feedback | Submit an invalid form | User guesses what was wrong | any |

## Operations

| Tell | Check | Cost | Scope |
|---|---|---|---|
| No error tracking | Look for a reporter in the entry point | Errors are only known when a user mentions one | any |
| No uptime check | Ask what alerts on an outage | Downtime is discovered by customers | public |
| No backups, or untested ones | Ask when a restore was last run | A backup nobody restored is not a backup | any |
