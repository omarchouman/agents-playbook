# Measurement

Read this before writing any performance finding. Every claim in a report traces back to one
of these commands or to a number you observed yourself.

The commands are illustrative. Pick whichever equivalent your stack provides and quote what
it actually printed, including the number.

## Budgets

Numbers to compare against, so a finding is a measurement rather than an impression. They are
starting points for a content site or a dashboard on a mid-range phone over slow mobile data,
not universal law. Adjust them for the app and say so in the report.

| What | Budget | Why this number |
|---|---|---|
| JavaScript on first load, compressed | under 200KB | Above roughly this, parse and execute time dominates on a mid-range phone regardless of network |
| Total page weight, first load | under 1MB | A second and a half of transfer on slow mobile data |
| Largest Contentful Paint | under 2.5s | The point past which users report a page as slow rather than loading |
| Cumulative Layout Shift | under 0.1 | Above this, content moves under the user's finger |
| Interaction to Next Paint | under 200ms | The threshold where a tap stops feeling connected to the result |
| Server response, median | under 200ms | Leaves the rest of the budget for render |
| Queries per request | under 10, and never proportional to rows | Anything proportional is an N+1 and will fail in production, not in development |

## Page and payload

```bash
# Lighthouse, scriptable, gives LCP, CLS, INP and the byte breakdown in one run.
npx lighthouse https://example.com --output=json --output-path=./lh.json \
  --only-categories=performance,seo,best-practices,accessibility

# Mobile emulation with CPU and network throttling, which is the number that changes minds.
npx lighthouse https://example.com --preset=desktop=false --throttling-method=simulate

# What the first page actually downloads, by type.
npx lighthouse https://example.com --output=json | \
  python3 -c "import json,sys; d=json.load(sys.stdin); \
print(d['audits']['resource-summary']['details']['items'])"
```

Build output, when there is no deployed URL to point at:

```bash
du -sh dist/ build/ .next/ 2>/dev/null
find dist build .next -name '*.js' -size +100k 2>/dev/null | xargs ls -lhS 2>/dev/null | head
```

Bundle composition, to find what is large rather than that something is:

```bash
npx vite-bundle-visualizer          # Vite
ANALYZE=true npm run build          # Next.js with the bundle analyzer configured
npx webpack-bundle-analyzer stats.json
npx source-map-explorer 'dist/**/*.js'
```

## Credentials in the bundle

Grep the build output, not the source. A key injected at build time is inlined into the
output and stops looking like a secret.

```bash
grep -roEh "(sk|pk|rk)_(live|test)_[A-Za-z0-9]{8,}|AIza[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{20,}" dist/ build/ .next/static/ 2>/dev/null | sort -u
grep -rl "SERVICE_ROLE\|service_role\|SECRET" dist/ build/ .next/static/ 2>/dev/null
```

A hit is a finding whatever the key is labelled. A key with a `publishable` or `anon` prefix
is designed to ship, so the finding there is not the key: it is whether the server enforces
access rules behind it.

## Queries

Count the queries for one request. The number is the finding; the code reading is the
hypothesis.

```sql
-- PostgreSQL: slowest statements by total time, once pg_stat_statements is on.
SELECT calls, round(mean_exec_time::numeric, 1) AS avg_ms,
       round(total_exec_time::numeric) AS total_ms, left(query, 90) AS query
FROM pg_stat_statements ORDER BY total_exec_time DESC LIMIT 15;

-- Does this query use an index, and how many rows does it really touch.
EXPLAIN (ANALYZE, BUFFERS) SELECT ...;

-- MySQL equivalent.
SET profiling = 1; /* run the request */ SHOW PROFILES;
```

Framework-level counting, which is usually faster than reaching for the database:

```bash
# Rails
tail -f log/development.log | grep -c "SELECT"
# Laravel: DB::listen in a service provider, or Telescope
# Django: django-debug-toolbar, or CaptureQueriesContext in a test
# Prisma: log: ['query'] in the client constructor
```

An N+1 is confirmed when the query count rises with the number of rows rendered. Load the
page with one row and with fifty and compare the counts. That comparison is the evidence to
quote, not the ORM call.

## Missing indexes

```sql
-- PostgreSQL: sequential scans on tables big enough to care about.
SELECT relname, seq_scan, seq_tup_read, idx_scan
FROM pg_stat_user_tables
WHERE seq_scan > 0 AND n_live_tup > 10000
ORDER BY seq_tup_read DESC LIMIT 15;
```

## Transfer and caching

```bash
# Is compression on, and which headers come back.
curl -sI -H "Accept-Encoding: br,gzip" https://example.com | \
  grep -iE "content-encoding|cache-control|vary|content-type"

# Full timing breakdown for one request.
curl -s -o /dev/null -w "dns %{time_namelookup}  connect %{time_connect}  tls %{time_appconnect}  ttfb %{time_starttransfer}  total %{time_total}  size %{size_download}\n" https://example.com
```

No `content-encoding` on an HTML, CSS, JS or JSON response is a finding. No `cache-control`
on a content-addressed asset is a finding.

## Images and fonts

```bash
# Images that are large enough to matter, biggest first.
find public static assets -type f \( -name '*.jpg' -o -name '*.jpeg' -o -name '*.png' \) \
  -size +100k 2>/dev/null | xargs ls -lhS 2>/dev/null | head -20

# Intrinsic size versus the size it renders at. A 3000px image in a 400px slot is the finding.
sips -g pixelWidth -g pixelHeight image.jpg          # macOS
identify -format "%w x %h\n" image.jpg               # ImageMagick

# Fonts fetched from someone else's origin.
grep -rn "fonts.googleapis.com\|fonts.gstatic.com\|use.typekit" --include='*.html' \
  --include='*.css' --include='*.tsx' --include='*.jsx' --include='*.vue' . | head
```

## Dependencies

```bash
npx depcheck                      # declared and never imported
npm ls --all --depth=0            # what is actually declared
npx npm-check-updates             # how far behind, which is a security finding as much as a size one
pip list --not-required           # Python equivalent
composer show --unused            # PHP equivalent
```

## Metadata and routes

```bash
# What a crawler and a share preview actually get.
curl -s https://example.com | grep -iE '<title>|og:image|og:title|description|canonical'
curl -s -o /dev/null -w "%{http_code}\n" https://example.com/robots.txt
curl -s -o /dev/null -w "%{http_code}\n" https://example.com/sitemap.xml
curl -s -o /dev/null -w "%{http_code}\n" https://example.com/this-page-does-not-exist

# Dead links, including the footer, which is where they survive longest.
npx linkinator https://example.com --recurse --skip "^(?!https://example.com)"
```

A 404 that returns the framework default, or that returns 200 with an empty page, are both
findings. The second is worse: a crawler indexes it.

## Mobile

```bash
# Horizontal overflow at phone width, which is most of "looks bad on mobile".
npx playwright screenshot --viewport-size=375,812 https://example.com shot.png
```

In a browser, throttle to slow mobile data and a 4x CPU slowdown before judging anything.
A finding that only reproduces on the development machine is not a finding; a finding that
only appears under throttling is the one users are living with.
