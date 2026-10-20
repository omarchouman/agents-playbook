#!/usr/bin/env python3
"""Structural checks for this repository.

Every check here replaces a written rule. If you are tempted to add a convention to
CLAUDE.md, first ask whether it belongs in this file instead: a check cannot be
forgotten, and a written rule can.

Run: python3 scripts/validate.py
"""
import glob
import io
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

failures = []
checks_run = 0


def check(name):
    """Register a check and return a reporter for its failures."""
    global checks_run
    checks_run += 1
    found = []

    def fail(msg):
        found.append(msg)

    def done():
        if found:
            failures.append((name, found))
            print("FAIL  %s" % name)
            for f in found[:12]:
                print("        %s" % f)
            if len(found) > 12:
                print("        ... and %d more" % (len(found) - 12))
        else:
            print("ok    %s" % name)

    return fail, done


def _strip_code(text):
    """Remove fenced code blocks and inline code.

    Markdown inside a fence is a sample, not a link: a template showing
    `[label](path)` is documenting syntax, not pointing anywhere. Scanning it
    produces failures that can only be silenced by making the documentation worse.
    """
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    text = re.sub(r"~~~.*?~~~", "", text, flags=re.S)
    return re.sub(r"`[^`\n]*`", "", text)


def markdown_files():
    return sorted(
        p for p in glob.glob("**/*.md", recursive=True)
        if not p.startswith(".git/")
    )


# 1. Typography. The repo deliberately contains no em-dashes or lookalikes.
fail, done = check("no em-dashes or dash lookalikes in Markdown")
BANNED = {"—": "em-dash", "―": "horizontal bar",
          "‒": "figure dash", "−": "minus sign"}
for p in markdown_files():
    for i, line in enumerate(io.open(p, encoding="utf-8"), 1):
        for ch, label in BANNED.items():
            if ch in line:
                fail("%s:%d contains %s" % (p, i, label))
done()

# 2. Cross-references between skills must resolve to a real section.
fail, done = check("cross-references resolve to an existing section")
sections = {}
for p in glob.glob("skills/*/SKILL.md"):
    name = p.split(os.sep)[1]
    body = io.open(p, encoding="utf-8").read()
    sections[name] = {
        m.group(1) for m in re.finditer(r"^#{2,3} (\d+(?:\.\d+)?)\.? ", body, re.M)
    }
for p in markdown_files():
    text = io.open(p, encoding="utf-8").read()
    for m in re.finditer(r"`([a-z-]+-practices)` §(\d+(?:\.\d+)?)", text):
        skill, sec = m.group(1), m.group(2)
        if skill not in sections:
            fail("%s references unknown skill `%s`" % (p, skill))
        elif sec not in sections[skill]:
            fail("%s references `%s` §%s which does not exist" % (p, skill, sec))
done()

# 3. Every skill needs frontmatter whose name matches its directory, because the
#    directory is how the plugin loader finds it and the name is how it is invoked.
fail, done = check("skill frontmatter present, valid and matching its directory")
skill_dirs = sorted(os.path.dirname(p) for p in glob.glob("skills/*/SKILL.md"))
for d in skill_dirs:
    text = io.open(os.path.join(d, "SKILL.md"), encoding="utf-8").read()
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        fail("%s/SKILL.md has no YAML frontmatter" % d)
        continue
    fm = m.group(1)
    nm = re.search(r"^name:\s*(\S+)\s*$", fm, re.M)
    expected = os.path.basename(d)
    if not nm:
        fail("%s/SKILL.md frontmatter has no name" % d)
    elif nm.group(1) != expected:
        fail("%s/SKILL.md name is '%s', expected '%s'" % (d, nm.group(1), expected))
    if not re.search(r"^description:", fm, re.M):
        fail("%s/SKILL.md frontmatter has no description" % d)
done()

# 4. The manifest and the filesystem must agree, in both directions. A skill on disk
#    but absent from the manifest never loads; one in the manifest but absent from disk
#    breaks installation.
fail, done = check("plugin manifest and skills/ agree in both directions")
try:
    manifest = json.load(open(".claude-plugin/plugin.json"))
    json.load(open(".claude-plugin/marketplace.json"))
except Exception as exc:
    fail("manifest does not parse: %s" % exc)
    manifest = {"skills": []}
listed = {s.lstrip("./").rstrip("/") for s in manifest.get("skills", [])}
on_disk = {d.replace(os.sep, "/") for d in skill_dirs}
for missing in sorted(listed - on_disk):
    fail("manifest lists %s which does not exist" % missing)
for unlisted in sorted(on_disk - listed):
    fail("%s exists but is not in plugin.json skills" % unlisted)
done()

# 5. Reference files are only reachable if a SKILL.md points at them, and a pointer to
#    a missing file is a dead end mid-task.
fail, done = check("reference files are linked, and every link resolves")
for d in skill_dirs:
    text = io.open(os.path.join(d, "SKILL.md"), encoding="utf-8").read()
    linked = set(re.findall(r"references/([A-Za-z0-9._-]+\.md)", text))
    present = {os.path.basename(p) for p in glob.glob(os.path.join(d, "references", "*.md"))}
    for dangling in sorted(linked - present):
        fail("%s/SKILL.md links references/%s which is missing" % (d, dangling))
    for orphan in sorted(present - linked):
        fail("%s/references/%s is never linked from SKILL.md" % (d, orphan))
done()

# 6. Relative Markdown links must point at files that exist.
fail, done = check("relative Markdown links resolve")
for p in markdown_files():
    base = os.path.dirname(p)
    text = _strip_code(io.open(p, encoding="utf-8").read())
    for m in re.finditer(r"\[[^\]]*\]\(([^)#:]+)\)", text):
        target = m.group(1).strip()
        if target.startswith(("http", "mailto", "#", "/")):
            continue
        if not os.path.exists(os.path.normpath(os.path.join(base, target))):
            fail("%s links %s which does not exist" % (p, target))
done()

# 7. A section reference inside a file must point at a heading in that same file.
#    Renumbering sections is routine and silently strands these.
fail, done = check("internal section references resolve within their own file")
for p_ in markdown_files():
    text = io.open(p_, encoding="utf-8").read()
    own = {m.group(1) for m in re.finditer(r"^#{2,3} (\d+(?:\.\d+)?)\.? ", text, re.M)}
    if not own:
        continue
    for m in re.finditer(r"(?<!`)\u00a7(\d+(?:\.\d+)?)", text):
        # Skip refs qualified by a skill name; check 2 already covers those.
        start = max(0, m.start() - 40)
        if re.search(r"`[a-z-]+-practices` $", text[start:m.start()]):
            continue
        if m.group(1) not in own:
            fail("%s references \u00a7%s with no such section in that file"
                 % (p_, m.group(1)))
done()

# 8. No agent attribution anywhere in history. Rewriting history to remove one is
#    expensive, so catching it before it spreads is the whole point.
fail, done = check("no agent attribution in commit messages")
try:
    log = subprocess.check_output(
        ["git", "log", "--format=%B"], stderr=subprocess.DEVNULL
    ).decode("utf-8", "replace")
    for pattern in (r"Co-Authored-By:\s*Claude", r"Generated with \[?Claude Code"):
        if re.search(pattern, log, re.I):
            fail("history contains %s" % pattern)
except Exception:
    print("      (skipped history check: not a git repository)")
done()

print()
if failures:
    print("%d of %d checks failed" % (len(failures), checks_run))
    sys.exit(1)
print("all %d checks passed" % checks_run)
