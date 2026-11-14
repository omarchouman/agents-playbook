#!/usr/bin/env python3
"""Deterministic first pass of a remove-slop audit.

Checks only what can be settled by reading files, so that the expensive passes
never spend a turn on a question a grep answers. Everything here is evidence:
each finding carries the path and the text that produced it.

What this cannot see is as important as what it can. It does not run the app,
so it says nothing about query counts, render timing or layout at phone width.
Those need the commands in ../references/measurement.md.

Run:  python3 slop-scan.py [path]
      python3 slop-scan.py --json [path]
      python3 slop-scan.py --strict [path]     exit 1 if any blocker is found
      python3 slop-scan.py --self-test         prove every check can fire, and
                                               that a clean project trips none
"""
import io
import json
import os
import re
import subprocess
import sys
import tempfile

BLOCKER, HIGH, MEDIUM, LOW = "blocker", "high", "medium", "low"
RANK = {BLOCKER: 0, HIGH: 1, MEDIUM: 2, LOW: 3}

SKIP_DIRS = {
    ".git", "node_modules", "vendor", "venv", ".venv", "__pycache__",
    ".next/cache", "coverage", ".pytest_cache", ".mypy_cache",
    # Fixtures and specs carry placeholder copy and sample keys on purpose.
    # Scanning them reports the test suite rather than the app.
    "test", "tests", "__tests__", "spec", "specs", "fixtures", "e2e",
    "cypress", "playwright", ".storybook",
}

# A file that defines these patterns is not an app that violates them. Without this,
# any scanner, lint config or rule list in the project reports itself.
SELF = os.path.abspath(__file__)
BUILD_DIRS = ["dist", "build", ".next/static", "out", "public/build", "_site"]
PUBLIC_DIRS = ["public", "static", "www", "dist", "build", "_site"]

# A title a generator wrote and nobody changed. Matched case-insensitively.
DEFAULT_TITLES = [
    "create react app", "create next app", "vite + react", "vite app",
    "react app", "next.js", "nuxt app", "svelte app", "vue app",
    "document", "untitled", "my app", "home page", "index",
    "laravel", "django", "rails", "astro",
]
DEFAULT_ICONS = ["vite.svg", "next.svg", "favicon.ico?v=react", "logo192.png", "nuxt.svg"]
PLACEHOLDERS = [
    "lorem ipsum", "your company", "company name here", "example@example.com",
    "john doe", "jane doe", "replace this text", "add your description",
    "tailwind starter", "your product name",
]
SECRET_PATTERNS = [
    (r"\b(?:sk|rk)_(?:live|test)_[A-Za-z0-9]{10,}", "Stripe secret key"),
    (r"\bAIza[A-Za-z0-9_\-]{30,}", "Google API key"),
    (r"\bghp_[A-Za-z0-9]{30,}", "GitHub token"),
    (r"\bxox[baprs]-[A-Za-z0-9\-]{10,}", "Slack token"),
    (r"SERVICE_ROLE_KEY\s*[:=]\s*[\"'][A-Za-z0-9._\-]{20,}", "service role key"),
    (r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----", "private key"),
]
SOURCE_EXT = (".js", ".jsx", ".ts", ".tsx", ".vue", ".svelte", ".php", ".py", ".rb", ".go")
MARKUP_EXT = (".html", ".htm", ".vue", ".svelte", ".astro", ".ejs", ".erb", ".twig", ".blade.php")

LARGE_JS_BYTES = 350 * 1024
LARGE_IMAGE_BYTES = 200 * 1024


class Finding(object):
    def __init__(self, check, severity, title, evidence, cost):
        self.check = check
        self.severity = severity
        self.title = title
        self.evidence = evidence
        self.cost = cost

    def as_dict(self):
        return {"check": self.check, "severity": self.severity, "title": self.title,
                "evidence": self.evidence, "cost": self.cost}


class Project(object):
    """Everything the checks need, read once."""

    def __init__(self, root):
        self.root = os.path.abspath(root)
        self.files = []
        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".git")]
            for fn in filenames:
                full = os.path.join(dirpath, fn)
                if os.path.abspath(full) == SELF:
                    continue
                self.files.append(os.path.relpath(full, self.root))
        self.markup = [f for f in self.files if f.endswith(MARKUP_EXT)]
        self.source = [f for f in self.files if f.endswith(SOURCE_EXT)]
        self._cache = {}

    def read(self, rel):
        if rel not in self._cache:
            try:
                with io.open(os.path.join(self.root, rel), encoding="utf-8", errors="replace") as fh:
                    self._cache[rel] = fh.read()
            except (IOError, OSError):
                self._cache[rel] = ""
        return self._cache[rel]

    def size(self, rel):
        try:
            return os.path.getsize(os.path.join(self.root, rel))
        except OSError:
            return 0

    def exists_any(self, names):
        """True if any of these filenames sits at the root or in a public directory."""
        for n in names:
            if os.path.exists(os.path.join(self.root, n)):
                return n
            for d in PUBLIC_DIRS:
                if os.path.exists(os.path.join(self.root, d, n)):
                    return os.path.join(d, n)
        return None

    def path_matches(self, pattern):
        rx = re.compile(pattern, re.I)
        return [f for f in self.files if rx.search(f)]

    def build_files(self):
        out = []
        for d in BUILD_DIRS:
            prefix = d + os.sep
            out.extend(f for f in self.files if f.startswith(prefix))
        return out

    def is_web(self):
        """Only web apps get the crawler and share-preview checks."""
        return bool(self.markup) or os.path.exists(os.path.join(self.root, "package.json"))

    def entry_markup(self):
        """The document most likely to carry the head, preferring a root index."""
        html = [f for f in self.markup if f.endswith((".html", ".htm"))]
        if not html:
            return None
        html.sort(key=lambda f: (f.count(os.sep), len(f)))
        for f in html:
            if "index" in os.path.basename(f).lower():
                return f
        return html[0]


def _head_text(p):
    f = p.entry_markup()
    return (f, p.read(f)) if f else (None, "")


def check_head_tags(p):
    """Title, description, share image, canonical and viewport, from the entry document."""
    found = []
    path, html = _head_text(p)
    if not path:
        return found
    low = html.lower()

    if "name=\"viewport\"" not in low and "name='viewport'" not in low:
        found.append(Finding(
            "missing-viewport", HIGH, "No viewport meta tag",
            "%s has no viewport meta" % path,
            "Mobile browsers render the desktop layout scaled down"))

    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
    if not m:
        found.append(Finding(
            "default-title", MEDIUM, "No page title",
            "%s has no title element" % path,
            "The tab and every search result show the URL"))
    else:
        title = re.sub(r"\s+", " ", m.group(1)).strip()
        if title.lower() in DEFAULT_TITLES or not title:
            found.append(Finding(
                "default-title", MEDIUM, "Page title is the generator default",
                "%s title is %r" % (path, title),
                "The first thing a visitor sees says nobody looked at this page"))

    if not re.search(r"name=[\"']description[\"']", html, re.I):
        found.append(Finding(
            "missing-description", MEDIUM, "No meta description",
            "%s has no description meta" % path,
            "Search results show a scraped fragment instead of a summary"))

    if not re.search(r"property=[\"']og:image[\"']", html, re.I):
        found.append(Finding(
            "missing-og-image", MEDIUM, "No share preview image",
            "%s has no og:image" % path,
            "Shared links render as a grey box on every platform"))

    if not re.search(r"rel=[\"']canonical[\"']", html, re.I):
        found.append(Finding(
            "missing-canonical", LOW, "No canonical URL",
            "%s has no canonical link" % path,
            "Duplicate URLs split search ranking between them"))

    icon = re.search(r"rel=[\"'][^\"']*icon[^\"']*[\"'][^>]*href=[\"']([^\"']+)", html, re.I)
    if icon and any(d in icon.group(1) for d in DEFAULT_ICONS):
        found.append(Finding(
            "default-favicon", LOW, "Favicon is the framework default",
            "%s points at %s" % (path, icon.group(1)),
            "A generic icon in the tab, in bookmarks and in history"))
    return found


def check_crawler_files(p):
    found = []
    if not p.is_web():
        return found
    if not p.exists_any(["robots.txt"]):
        found.append(Finding(
            "missing-robots", LOW, "No robots.txt",
            "No robots.txt at the root or in a public directory",
            "Crawlers get no guidance about what to index"))
    has_sitemap = p.exists_any(["sitemap.xml", "sitemap_index.xml"]) or p.path_matches(r"sitemap")
    if not has_sitemap:
        found.append(Finding(
            "missing-sitemap", LOW, "No sitemap",
            "No sitemap file or sitemap route found",
            "Crawlers discover only the pages they stumble into"))
    return found


def check_routes(p):
    """A 404 page and the legal routes, found by the file conventions of the common frameworks."""
    found = []
    if not p.is_web():
        return found
    if not p.path_matches(r"(^|/)(404|not[-_]?found|_?error)\.(html|js|jsx|ts|tsx|vue|svelte|php|py)$"):
        found.append(Finding(
            "missing-404", HIGH, "No custom 404 page",
            "No 404, not-found or error route file found",
            "The framework error page is where visitors leave"))
    if not p.path_matches(r"(privacy|terms|tos|legal)"):
        found.append(Finding(
            "missing-legal", MEDIUM, "No privacy policy or terms route",
            "No file or route matching privacy, terms or legal",
            "Blocks payment processors and app store review"))
    return found


def check_fonts(p):
    found = []
    for f in p.markup + p.source + [x for x in p.files if x.endswith(".css")]:
        text = p.read(f)
        if "fonts.googleapis.com" in text or "fonts.gstatic.com" in text:
            found.append(Finding(
                "hotlinked-fonts", MEDIUM, "Fonts loaded from a third-party origin",
                "%s references the Google Fonts CDN" % f,
                "An extra connection before text can render, and their uptime becomes yours"))
            break
    return found


def check_images(p):
    found = []
    big = []
    for f in p.files:
        if f.lower().endswith((".jpg", ".jpeg", ".png")) and p.size(f) > LARGE_IMAGE_BYTES:
            big.append((f, p.size(f)))
    if big:
        big.sort(key=lambda x: -x[1])
        sample = ", ".join("%s (%dKB)" % (f, s // 1024) for f, s in big[:3])
        found.append(Finding(
            "raster-images", MEDIUM,
            "%d image(s) over %dKB are not WebP or AVIF" % (len(big), LARGE_IMAGE_BYTES // 1024),
            sample,
            "Several times the bytes for the same picture, paid on every first visit"))
    return found


def check_bundle_size(p):
    found = []
    js = [(f, p.size(f)) for f in p.build_files() if f.endswith(".js")]
    heavy = [x for x in js if x[1] > LARGE_JS_BYTES]
    if heavy:
        heavy.sort(key=lambda x: -x[1])
        sample = ", ".join("%s (%dKB)" % (f, s // 1024) for f, s in heavy[:3])
        found.append(Finding(
            "large-bundle", HIGH,
            "%d JavaScript file(s) over %dKB in the build output" % (len(heavy), LARGE_JS_BYTES // 1024),
            sample,
            "Parse and execute time on a mid-range phone, before anything renders"))
    return found


def check_bundle_secrets(p):
    """Grep the build output, where a key inlined at build time stops looking like a secret."""
    found = []
    for f in p.build_files():
        if not f.endswith((".js", ".mjs", ".css", ".json", ".html", ".map")):
            continue
        text = p.read(f)
        for pattern, label in SECRET_PATTERNS:
            m = re.search(pattern, text)
            if m:
                found.append(Finding(
                    "bundle-credentials", BLOCKER, "Credential in the client bundle",
                    "%s contains what looks like a %s" % (f, label),
                    "Published to every visitor who loads the page"))
                return found
    return found


def check_env_committed(p):
    found = []
    try:
        out = subprocess.check_output(
            ["git", "-C", p.root, "ls-files"], stderr=subprocess.DEVNULL).decode("utf-8", "replace")
    except (subprocess.CalledProcessError, OSError):
        return found
    tracked = [l for l in out.splitlines()
               if re.search(r"(^|/)\.env($|\.(local|production|prod|staging))", l)]
    if tracked:
        found.append(Finding(
            "env-committed", BLOCKER, "Environment file is tracked by git",
            "git ls-files reports %s" % ", ".join(tracked[:3]),
            "Secrets are in every clone and in the history even after deletion"))
    return found


def check_console_noise(p):
    found = []
    hits = []
    for f in p.source:
        if f.startswith(tuple(d + os.sep for d in BUILD_DIRS)):
            continue
        for i, line in enumerate(p.read(f).splitlines(), 1):
            if re.search(r"\bconsole\.(log|debug)\s*\(", line):
                hits.append("%s:%d" % (f, i))
    if len(hits) > 5:
        found.append(Finding(
            "console-logs", LOW, "%d console.log calls left in source" % len(hits),
            ", ".join(hits[:3]) + (", ..." if len(hits) > 3 else ""),
            "Leaks internals and buries the errors that matter"))
    return found


def check_placeholders(p):
    """Placeholder copy in anything that renders.

    Markdown is excluded. Documentation that discusses placeholder text is
    indistinguishable from documentation that contains it, and flagging a README
    for naming the thing it warns about is the check being wrong, not the file.
    Content-driven static sites pay for this: lorem ipsum in a post is left to the
    client-behaviour probe, which can see what the page actually renders.
    """
    found = []
    for f in p.markup + p.source + [x for x in p.files if x.endswith(".json")]:
        if f.startswith(tuple(d + os.sep for d in BUILD_DIRS)):
            continue
        low = p.read(f).lower()
        for ph in PLACEHOLDERS:
            if ph in low:
                found.append(Finding(
                    "placeholder-copy", MEDIUM, "Placeholder text still in the app",
                    "%s contains %r" % (f, ph),
                    "Visible evidence that nobody read the page"))
                return found
    return found


def check_error_tracking(p):
    found = []
    pkg = os.path.join(p.root, "package.json")
    if not os.path.exists(pkg):
        return found
    blob = " ".join(p.read(f) for f in p.files
                    if os.path.basename(f) in ("package.json", "composer.json", "requirements.txt"))
    if not re.search(r"sentry|bugsnag|rollbar|honeybadger|datadog|airbrake|appsignal", blob, re.I):
        found.append(Finding(
            "no-error-tracking", MEDIUM, "No error tracking dependency",
            "No reporter found in the dependency manifests",
            "Production errors are known only when a user mentions one"))
    return found


CHECKS = [
    check_head_tags, check_crawler_files, check_routes, check_fonts,
    check_images, check_bundle_size, check_bundle_secrets, check_env_committed,
    check_console_noise, check_placeholders, check_error_tracking,
]

ALL_CHECK_IDS = {
    "missing-viewport", "default-title", "missing-description", "missing-og-image",
    "missing-canonical", "default-favicon", "missing-robots", "missing-sitemap",
    "missing-404", "missing-legal", "hotlinked-fonts", "raster-images",
    "large-bundle", "bundle-credentials", "env-committed", "console-logs",
    "placeholder-copy", "no-error-tracking",
}


def scan(root):
    p = Project(root)
    found = []
    for fn in CHECKS:
        found.extend(fn(p))
    found.sort(key=lambda f: (RANK[f.severity], f.check))
    return found


def report(found, root):
    if not found:
        print("No mechanical findings in %s" % root)
    else:
        current = None
        for f in found:
            if f.severity != current:
                current = f.severity
                print("\n%s" % current.upper())
            print("  %-22s %s" % (f.check, f.title))
            print("  %-22s   evidence: %s" % ("", f.evidence))
            print("  %-22s   cost:     %s" % ("", f.cost))
        print("\n%d finding(s)." % len(found))
    print("\nThis pass reads files only. Query counts, render timing and layout at phone")
    print("width need the commands in ../references/measurement.md.")


def _write(root, rel, body):
    full = os.path.join(root, rel)
    d = os.path.dirname(full)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    with io.open(full, "w", encoding="utf-8") as fh:
        fh.write(body)


def _dirty_project(root):
    """Every check's violation, planted. A check that cannot fire here is dead code."""
    _write(root, "index.html",
           "<html><head><title>Vite + React</title>"
           "<link rel=\"icon\" href=\"/vite.svg\">"
           "<link href=\"https://fonts.googleapis.com/css2?family=Inter\" rel=\"stylesheet\">"
           "</head><body><h1>Lorem ipsum dolor sit amet</h1></body></html>")
    _write(root, "package.json", json.dumps({"name": "demo", "dependencies": {"react": "18.3.1"}}))
    _write(root, "src/app.js", "\n".join("console.log(%d);" % i for i in range(8)))
    _write(root, "dist/assets/index.js", "var k='sk_live_%s';\n" % ("a" * 24) + "x" * LARGE_JS_BYTES)
    _write(root, "public/hero.png", "p" * (LARGE_IMAGE_BYTES + 1))
    _write(root, ".env", "SECRET=1\n")
    subprocess.call(["git", "-C", root, "init", "-q"])
    subprocess.call(["git", "-C", root, "add", "-A", "-f"], stderr=subprocess.DEVNULL)


def _clean_project(root):
    """The same app with every defect fixed. Any finding here is a false positive."""
    _write(root, "index.html",
           "<html><head><title>Fleet Manager</title>"
           "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
           "<meta name=\"description\" content=\"Manage a rental fleet.\">"
           "<meta property=\"og:image\" content=\"/og.png\">"
           "<link rel=\"canonical\" href=\"https://example.com/\">"
           "<link rel=\"icon\" href=\"/brand-mark.svg\">"
           "</head><body><h1>Fleet Manager</h1></body></html>")
    _write(root, "package.json", json.dumps(
        {"name": "fleet", "dependencies": {"react": "18.3.1", "@sentry/react": "8.0.0"}}))
    _write(root, "src/app.js", "export const boot = () => true;\n")
    _write(root, "src/routes/404.jsx", "export default function NotFound() { return null; }\n")
    _write(root, "src/routes/privacy.jsx", "export default function Privacy() { return null; }\n")
    _write(root, "public/robots.txt", "User-agent: *\n")
    _write(root, "public/sitemap.xml", "<urlset></urlset>")
    _write(root, "dist/assets/index.js", "export const a = 1;\n")
    _write(root, "public/hero.webp", "w" * (LARGE_IMAGE_BYTES + 1))


def self_test():
    ok = True

    dirty = tempfile.mkdtemp(prefix="slop-dirty-")
    _dirty_project(dirty)
    fired = {f.check for f in scan(dirty)}
    missing = sorted(ALL_CHECK_IDS - fired)
    if missing:
        ok = False
        print("FAIL  checks that never fired on a project built to violate them:")
        for m in missing:
            print("        %s" % m)
    else:
        print("ok    all %d checks fire on a violating project" % len(ALL_CHECK_IDS))

    clean = tempfile.mkdtemp(prefix="slop-clean-")
    _clean_project(clean)
    noise = sorted(f.check for f in scan(clean))
    if noise:
        ok = False
        print("FAIL  false positives on a clean project:")
        for n in noise:
            print("        %s" % n)
    else:
        print("ok    no findings on a clean project")

    unknown = sorted(fired - ALL_CHECK_IDS)
    if unknown:
        ok = False
        print("FAIL  checks emitted but not declared in ALL_CHECK_IDS: %s" % ", ".join(unknown))

    print("\nself-test %s" % ("passed" if ok else "FAILED"))
    return 0 if ok else 1


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    flags = {a for a in argv[1:] if a.startswith("--")}
    if "--self-test" in flags:
        return self_test()
    root = args[0] if args else "."
    if not os.path.isdir(root):
        print("Not a directory: %s" % root)
        return 2
    found = scan(root)
    if "--json" in flags:
        print(json.dumps([f.as_dict() for f in found], indent=2))
    else:
        report(found, os.path.abspath(root))
    if "--strict" in flags and any(f.severity == BLOCKER for f in found):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
