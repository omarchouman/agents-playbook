# Ecosystem detection

Read this at step 1 of the `playbook-builder` skill. Find the section matching the repository's
stack and run those commands. The goal is to arrive at the interview already knowing the stack,
the real verification commands, and what is enforced by tooling, so the user is asked to correct
findings rather than supply them.

Two rules throughout:

- **Prefer declared scripts to invented commands.** If `package.json` defines `test`, the
  playbook should say `pnpm test`, not `vitest run`. The script is the team's interface and it
  will keep working when the underlying tool is swapped.
- **Record what is enforced, so it can be excluded.** Every check already run by a linter,
  formatter, type checker, hook or CI job is a rule that must not be written down (§3).

## Contents

- [Topology: what shape is this folder?](#topology-what-shape-is-this-folder)
- [Node and TypeScript](#node-and-typescript)
- [Python](#python)
- [Go](#go)
- [Rust](#rust)
- [Ruby](#ruby)
- [PHP and Laravel](#php-and-laravel)
- [Java and Kotlin](#java-and-kotlin)
- [.NET](#net)
- [Stack-independent](#stack-independent)

## Topology: what shape is this folder?

Run this before anything else. It decides where the playbook can live, how many pull requests
a task produces, and whether merge order matters, so every later answer depends on it.

```bash
# How many repositories are in play? More than one means this is not a monorepo,
# whatever the directory layout suggests.
find . -maxdepth 3 -name .git -not -path '*/node_modules/*' | sed 's|/.git$||'

# Is the parent folder itself a repository? If not, nothing placed here is shareable.
git rev-parse --show-toplevel 2>/dev/null || echo "PARENT IS NOT A GIT REPO"

# Workspace tooling: one repo with coordinated packages
ls pnpm-workspace.yaml turbo.json nx.json lerna.json rush.json go.work 2>/dev/null
grep -l '\[workspace\]' Cargo.toml 2>/dev/null
grep -rl 'include(' settings.gradle settings.gradle.kts 2>/dev/null
python3 -c "import json;d=json.load(open('package.json'));print('workspaces:',d.get('workspaces'))" 2>/dev/null

# Submodules or subtrees
cat .gitmodules 2>/dev/null || echo "no submodules"

# Independent projects side by side: a manifest in each immediate subdirectory
for d in */; do
  m=$(ls "$d"package.json "$d"pyproject.toml "$d"go.mod "$d"Cargo.toml "$d"pom.xml \
         "$d"build.gradle "$d"composer.json 2>/dev/null | head -1)
  [ -n "$m" ] && echo "$d -> $(basename "$m")"
done

# Existing instruction files, which reveal whether anyone has already picked a layout
find . -maxdepth 3 -name 'CLAUDE.md' -not -path '*/node_modules/*'
```

Read the result as one of five shapes, and say which you concluded so the user can correct it:

| Signal | Shape |
|---|---|
| One `.git`, one manifest | **Single project** |
| One `.git`, workspace manifest present | **Tooled monorepo** |
| One `.git`, manifests in sibling directories, no workspace file | **Untooled monorepo** |
| Several `.git` directories under a parent | **Separate repos side by side** |
| One `.git` plus `.gitmodules` | **Superproject with submodules** |

The fourth is the one that catches people, because the directory listing looks identical to a
monorepo while almost every workflow consequence differs. If `git rev-parse` reported that the
parent is not a repository, anything written there is invisible to teammates, to CI, and to
anyone who clones a single repo, which is a finding to raise before writing a line.

## Node and TypeScript

```bash
cat package.json | python3 -c 'import json,sys;d=json.load(sys.stdin);print(json.dumps(d.get("scripts",{}),indent=2))'
ls pnpm-lock.yaml yarn.lock package-lock.json bun.lockb 2>/dev/null   # which runner
ls pnpm-workspace.yaml turbo.json nx.json lerna.json 2>/dev/null      # monorepo?
ls tsconfig.json && grep -E '"(strict|noUncheckedIndexedAccess|noImplicitAny)"' tsconfig.json
ls .eslintrc* eslint.config.* biome.json .prettierrc* 2>/dev/null     # enforced style
ls vitest.config.* jest.config.* playwright.config.* cypress.config.* 2>/dev/null
```

The lockfile determines the runner, which must appear in every command the playbook states.
`strict` being off in `tsconfig.json` is worth raising: it changes what rules are even needed.

## Python

```bash
ls pyproject.toml setup.cfg requirements*.txt Pipfile 2>/dev/null
grep -A30 '\[tool' pyproject.toml 2>/dev/null | head -60     # ruff, mypy, pytest config
ls .ruff.toml ruff.toml mypy.ini .flake8 .pre-commit-config.yaml 2>/dev/null
ls poetry.lock uv.lock Pipfile.lock 2>/dev/null              # which manager
grep -rn 'strict\|disallow_untyped' pyproject.toml mypy.ini 2>/dev/null | head
```

Whether `mypy`/`pyright` runs in strict mode, and whether it runs in CI at all, changes which
type-related rules are worth writing.

## Go

```bash
head -5 go.mod                                               # module path, Go version
ls Makefile Taskfile.yml 2>/dev/null && grep -E '^[a-z-]+:' Makefile 2>/dev/null | head
ls .golangci.yml .golangci.yaml 2>/dev/null
find . -name '*_test.go' -not -path './vendor/*' | head -5
```

Go projects usually drive everything through a `Makefile`; read its targets rather than assuming
`go test ./...`.

## Rust

```bash
grep -A5 '^\[workspace\]' Cargo.toml 2>/dev/null
ls clippy.toml rustfmt.toml rust-toolchain* 2>/dev/null
grep -rn 'deny\|warn' Cargo.toml .cargo/config.toml 2>/dev/null | head
```

## Ruby

```bash
ls Gemfile Rakefile config/application.rb 2>/dev/null        # Rails?
ls .rubocop.yml .rspec 2>/dev/null
grep -E 'rspec|minitest' Gemfile 2>/dev/null
ls db/migrate | tail -5 2>/dev/null                          # migration cadence
```

## PHP and Laravel

```bash
cat composer.json | python3 -c 'import json,sys;d=json.load(sys.stdin);print(json.dumps(d.get("scripts",{}),indent=2))'
ls pint.json phpstan.neon psalm.xml .php-cs-fixer.php phpunit.xml 2>/dev/null
ls app/ database/migrations/ tests/ 2>/dev/null
grep -rn 'level' phpstan.neon 2>/dev/null                    # static analysis strictness
```

## Java and Kotlin

```bash
ls pom.xml build.gradle build.gradle.kts settings.gradle* 2>/dev/null
ls checkstyle.xml spotbugs*.xml .editorconfig detekt.yml 2>/dev/null
ls ./gradlew ./mvnw 2>/dev/null                              # prefer the wrapper in commands
```

## .NET

```bash
ls *.sln */*.csproj 2>/dev/null
ls .editorconfig Directory.Build.props 2>/dev/null
grep -rn 'TreatWarningsAsErrors\|Nullable' Directory.Build.props *.csproj 2>/dev/null | head
```

## Stack-independent

Run these regardless. They produce most of what the interview would otherwise have to ask for.

```bash
# Existing agent instructions: extend these, never silently replace them
find . -maxdepth 3 \( -name 'CLAUDE.md' -o -name 'AGENTS.md' -o -name '.cursorrules' \) \
  -not -path '*/node_modules/*'

# Conventions as practised
git log --format='%s' -200                                   # commit message reality
git log --format='%s' -200 | grep -cE '^(feat|fix|chore|docs|refactor|test|perf)(\(.+\))?!?:'
git branch -r --format='%(refname:short)' | sed 's|origin/||' | head -30
git log --merges --format='%s' -40                           # merge or squash or rebase

# Review and ownership process
ls .github/pull_request_template.md .github/ISSUE_TEMPLATE .github/CODEOWNERS 2>/dev/null

# What CI actually gates on, which is the de facto definition of done
for f in .github/workflows/*.y*ml; do echo "--- $f"; grep -E '^\s*(name|run):' "$f" | head -20; done

# Hooks: enforced locally, so excluded from written rules
ls .husky .lefthook.yml lefthook.yml .pre-commit-config.yaml 2>/dev/null
git config core.hooksPath

# Where things live
git ls-files | sed 's|/[^/]*$||' | sort | uniq -c | sort -rn | head -20

# Churn: the files changed most often are where rules pay off most
git log --format=%H -500 --name-only | grep -v '^$' | grep -v '^[0-9a-f]\{40\}$' \
  | sort | uniq -c | sort -rn | head -15
```

The churn list is worth attention. The twenty files a team touches constantly are where a
convention earns its keep, and a playbook aimed at rarely-touched code is wasted effort.

The Conventional Commits count tells you whether to treat it as the convention. A high ratio
means yes. A ratio near half usually means someone intended it and it was never enforced, which
is a finding to raise with an offer to add a commit-message hook rather than a rule to write.
