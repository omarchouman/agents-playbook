#!/usr/bin/env python3
"""Mechanical checks for a project's playbook rules.

Copy this into the target repository (conventionally `scripts/validate-playbook.py`),
then edit the CHECKS list at the bottom. Nothing above that list normally needs changing.

The point of this file is to let a playbook shrink. Every rule expressed here is a rule
that no longer has to be remembered, and a check cannot be skimmed past the way a written
convention can. When you are tempted to add a line to a playbook, look here first.

    python3 scripts/validate-playbook.py              run every check
    python3 scripts/validate-playbook.py --self-test  prove the checks can actually fail
    python3 scripts/validate-playbook.py --list       show what is being enforced

Paths resolve from the repository root, found via git, so the script works from any
working directory. That matters: a validator that resolves paths relative to its own
location silently validates the wrong tree when it is copied or vendored.
"""

import argparse
import fnmatch
import glob
import io
import os
import re
import subprocess
import sys
import tempfile


# ---------------------------------------------------------------------------
# Framework. Edit CHECKS at the bottom, not this part.
# ---------------------------------------------------------------------------

def repo_root():
    """The repository root, so checks are independent of the working directory."""
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "--show-toplevel"], stderr=subprocess.DEVNULL
        )
        return out.decode().strip()
    except Exception:
        return os.getcwd()


class Check:
    """One enforceable rule.

    `run` returns a list of human-readable failures, empty when the rule holds.
    `violation` describes something that *should* trip this check, so `--self-test` can
    prove the check fires. It is either a (relative_path, contents) pair written into a
    scratch tree, or a callable receiving the scratch directory to set up whatever the
    violation needs (a git repo with a bad commit, for instance). A check with no
    `violation` is reported as unverified rather than silently trusted, because a check
    that cannot fail provides false comfort.
    """

    def __init__(self, name, run, violation=None, why=None):
        self.name = name
        self.run = run
        self.violation = violation
        self.why = why


def _text_files(root, patterns, exclude):
    for pattern in patterns:
        for path in glob.glob(os.path.join(root, pattern), recursive=True):
            rel = os.path.relpath(path, root)
            if not os.path.isfile(path):
                continue
            if any(fnmatch.fnmatch(rel, ex) or rel.startswith(ex.rstrip("*"))
                   for ex in exclude):
                continue
            yield rel, path


DEFAULT_EXCLUDE = [".git/*", "node_modules/*", "vendor/*", "dist/*", "build/*",
                   ".venv/*", "venv/*", "target/*", "__pycache__/*", "*.lock"]


# ---------------------------------------------------------------------------
# Check factories. Compose these in CHECKS.
# ---------------------------------------------------------------------------

def forbidden_text(name, needles, patterns=("**/*.md",), exclude=(), why=None,
                   regex=False, ignore_case=False, violation=None):
    """Fail when any needle appears in the matched files.

    For banned characters (em-dashes, smart quotes), banned APIs, leftover debug calls,
    or a deprecated helper you are migrating away from.
    """
    skip = list(DEFAULT_EXCLUDE) + list(exclude)
    flags = re.I if ignore_case else 0

    def run(root):
        out = []
        for rel, path in _text_files(root, patterns, skip):
            try:
                lines = io.open(path, encoding="utf-8", errors="replace").readlines()
            except OSError:
                continue
            for i, line in enumerate(lines, 1):
                for needle, label in needles.items():
                    hit = (re.search(needle, line, flags) if regex
                           else (needle.lower() in line.lower() if ignore_case
                                 else needle in line))
                    if hit:
                        out.append("%s:%d contains %s" % (rel, i, label))
        return out

    if violation is None and not regex:
        # Literal needles are their own sample. A regex is not: its source text is
        # usually not a string it matches, so the caller must supply a real sample.
        first = sorted(patterns)[0].replace("**/", "").replace("*", "sample")
        violation = (first, "a line with %s in it\n" % list(needles)[0])
    return Check(name, run, violation=violation, why=why)


def required_text(name, needle, patterns, exclude=(), why=None):
    """Fail when a matched file is missing something it must contain.

    For license headers, a required frontmatter key, a mandatory import.
    """
    skip = list(DEFAULT_EXCLUDE) + list(exclude)

    def run(root):
        out = []
        for rel, path in _text_files(root, patterns, skip):
            try:
                body = io.open(path, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            if needle not in body:
                out.append("%s is missing %r" % (rel, needle))
        return out

    first = sorted(patterns)[0].replace("**/", "").replace("*", "sample")
    return Check(name, run, violation=(first, "content without the required marker\n"),
                 why=why)


def files_exist(name, paths, why=None):
    """Fail when a path the playbook depends on is absent."""
    def run(root):
        return ["%s does not exist" % p
                for p in paths if not os.path.exists(os.path.join(root, p))]
    # An empty scratch tree is precisely this check's violation.
    return Check(name, run, violation=lambda d: None, why=why)


def links_resolve(name, patterns=("**/*.md",), exclude=(), why=None):
    """Fail on relative Markdown links pointing at nothing.

    Broken internal links are how documentation quietly rots: each one is a dead end
    for whoever followed it mid-task.
    """
    skip = list(DEFAULT_EXCLUDE) + list(exclude)

    def run(root):
        out = []
        for rel, path in _text_files(root, patterns, skip):
            base = os.path.dirname(path)
            body = io.open(path, encoding="utf-8", errors="replace").read()
            for m in re.finditer(r"\[[^\]]*\]\(([^)#:]+)\)", body):
                target = m.group(1).strip()
                if target.startswith(("http", "mailto", "#", "/")):
                    continue
                if not os.path.exists(os.path.normpath(os.path.join(base, target))):
                    out.append("%s links %s which does not exist" % (rel, target))
        return out

    return Check(name, run,
                 violation=("broken-link-sample.md", "[x](./definitely-not-here.md)\n"),
                 why=why)


def _scratch_repo(bad_subject="wip", bad_body=""):
    """Build a throwaway git repo whose single commit violates the convention."""
    def setup(d):
        env = dict(os.environ,
                   GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@e",
                   GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@e")
        io.open(os.path.join(d, "f.txt"), "w").write("x\n")
        for cmd in (["init", "-q"], ["add", "."],
                    ["commit", "-q", "-m", bad_subject, "-m", bad_body]):
            subprocess.run(["git", "-C", d] + cmd, env=env,
                           capture_output=True, check=False)
    return setup


def commit_subjects(name, pattern=None, forbid=None, max_length=None, count=200,
                    why=None):
    """Fail on commit subjects that break the project's convention.

    Checks only the recent window, since rewriting old history to satisfy a new
    convention costs more than it is worth. See the git-practices skill on why
    published history is shared state.
    """
    def run(root):
        try:
            log = subprocess.check_output(
                ["git", "-C", root, "log", "--no-merges",
                 "--format=%h\t%s", "-%d" % count],
                stderr=subprocess.DEVNULL).decode("utf-8", "replace")
        except Exception:
            return []
        out = []
        for line in log.splitlines():
            if "\t" not in line:
                continue
            sha, subject = line.split("\t", 1)
            if pattern and not re.match(pattern, subject):
                out.append("%s %r does not match %s" % (sha, subject, pattern))
            if max_length and len(subject) > max_length:
                out.append("%s subject is %d chars (max %d)"
                           % (sha, len(subject), max_length))
            for bad, label in (forbid or {}).items():
                if re.search(bad, subject, re.I):
                    out.append("%s %r contains %s" % (sha, subject, label))
        return out
    return Check(name, run, violation=_scratch_repo(bad_subject="wip"), why=why)


def commit_bodies_clean(name, forbid, count=400, why=None):
    """Fail when commit message bodies contain something banned.

    Attribution trailers are the usual case. Catching one before it is pushed is cheap;
    removing it afterwards means rewriting published history.
    """
    def run(root):
        try:
            log = subprocess.check_output(
                ["git", "-C", root, "log", "--format=%B", "-%d" % count],
                stderr=subprocess.DEVNULL).decode("utf-8", "replace")
        except Exception:
            return []
        return ["history contains %s" % label
                for bad, label in forbid.items() if re.search(bad, log, re.I)]
    return Check(name, run,
                 violation=_scratch_repo(bad_subject="Add thing",
                                         bad_body="Co-Authored-By: Claude <x@y>"),
                 why=why)


def shell(name, command, why=None):
    """Fail when a command the project already owns exits non-zero.

    Prefer wrapping the project's own script (`pnpm lint`, `make test`) over
    reimplementing its logic here, so this file does not drift from the real tooling.
    Not self-testable, since the harness cannot synthesize a failure for it.
    """
    def run(root):
        try:
            proc = subprocess.run(command, shell=True, cwd=root,
                                  capture_output=True, text=True)
        except Exception as exc:
            return ["could not run %r: %s" % (command, exc)]
        if proc.returncode != 0:
            tail = (proc.stdout + proc.stderr).strip().splitlines()[-6:]
            return ["`%s` exited %d" % (command, proc.returncode)] + \
                   ["  " + t for t in tail]
        return []
    return Check(name, run, why=why)


def custom(name, run, violation=None, why=None):
    """Escape hatch for a project-specific rule the factories above do not cover."""
    return Check(name, run, violation=violation, why=why)


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_all(checks, root):
    failed = 0
    for c in checks:
        try:
            problems = c.run(root)
        except Exception as exc:
            problems = ["check raised %s: %s" % (type(exc).__name__, exc)]
        if problems:
            failed += 1
            print("FAIL  %s" % c.name)
            if c.why:
                print("        why: %s" % c.why)
            for p in problems[:12]:
                print("        %s" % p)
            if len(problems) > 12:
                print("        ... and %d more" % (len(problems) - 12))
        else:
            print("ok    %s" % c.name)
    print()
    if failed:
        print("%d of %d checks failed" % (failed, len(checks)))
        return 1
    print("all %d checks passed" % len(checks))
    return 0


def self_test(checks):
    """Confirm each check fires on a synthetic violation.

    A check that cannot fail is worse than no check, because it reports success forever
    and nobody looks again. Run this whenever you add or edit a check.
    """
    passed = unverified = broken = 0
    for c in checks:
        if not c.violation:
            print("skip  %s (no sample violation declared)" % c.name)
            unverified += 1
            continue
        with tempfile.TemporaryDirectory() as tmp:
            if callable(c.violation):
                c.violation(tmp)
            else:
                rel, contents = c.violation
                target = os.path.join(tmp, rel)
                os.makedirs(os.path.dirname(target) or tmp, exist_ok=True)
                io.open(target, "w", encoding="utf-8").write(contents)
            try:
                fired = bool(c.run(tmp))
            except Exception as exc:
                print("ERROR %s raised on its own sample: %s" % (c.name, exc))
                broken += 1
                continue
        if fired:
            print("ok    %s fires on a violation" % c.name)
            passed += 1
        else:
            print("BROKEN %s did NOT fire on its own sample violation" % c.name)
            broken += 1
    print()
    print("%d verified, %d unverified, %d broken" % (passed, unverified, broken))
    if unverified:
        print("Unverified checks are not necessarily wrong, but nothing proves they work.")
    return 1 if broken else 0


# ---------------------------------------------------------------------------
# CHECKS: this is the part you edit.
#
# Replace the examples below with your project's mechanical rules. Keep each `why`
# short and real, because it is what someone reads when the check blocks them and they
# are deciding whether the check or their change is wrong.
# ---------------------------------------------------------------------------

CHECKS = [
    # Typography and banned strings.
    forbidden_text(
        "no em-dashes in prose",
        {"—": "an em-dash", "–": "an en-dash"},
        patterns=("**/*.md",),
        why="house style uses commas, colons or separate sentences instead",
    ),

    # Leftover debugging, the most common accidental commit.
    forbidden_text(
        "no leftover debug statements",
        {r"\bconsole\.log\(": "console.log", r"\bdebugger\b": "a debugger statement",
         r"\bbreakpoint\(\)": "breakpoint()", r"\bbinding\.pry\b": "binding.pry"},
        patterns=("src/**/*.*", "app/**/*.*", "lib/**/*.*"),
        regex=True,
        violation=("src/sample.js", "function f() {\n  console.log('x');\n}\n"),
        why="debug output in production logs is noise at best and a data leak at worst",
    ),

    # Documentation that rots silently.
    links_resolve("relative Markdown links resolve"),

    # Files the playbook depends on existing.
    files_exist(
        "required project files present",
        ["README.md"],
        why="referenced from onboarding; a missing one sends a newcomer nowhere",
    ),

    # Commit conventions. Tune or delete to match the project.
    commit_subjects(
        "commit subjects follow the convention",
        forbid={r"^(wip|fix|update|changes|asdf)$": "a placeholder subject"},
        max_length=72,
        why="the log is read when bisecting; a placeholder subject tells the reader nothing",
    ),
    commit_bodies_clean(
        "no agent attribution in commit messages",
        {r"Co-Authored-By:\s*(Claude|GPT|Copilot)": "an agent attribution trailer",
         r"Generated with \[?Claude Code": "a generated-with trailer"},
        why="removing one after it is pushed means rewriting published history",
    ),

    # Delegate to tooling the project already owns rather than reimplementing it.
    # shell("lint", "pnpm lint", why="style is enforced, not reviewed"),
    # shell("types", "pnpm typecheck", why="a type error reaching main blocks everyone"),
]


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--self-test", action="store_true",
                    help="confirm each check fires on a synthetic violation")
    ap.add_argument("--list", action="store_true",
                    help="list the enforced rules and exit")
    args = ap.parse_args()

    if args.list:
        for c in CHECKS:
            print("%-44s %s" % (c.name, c.why or ""))
        return 0
    if args.self_test:
        return self_test(CHECKS)
    return run_all(CHECKS, repo_root())


if __name__ == "__main__":
    sys.exit(main())
