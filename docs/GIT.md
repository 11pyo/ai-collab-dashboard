# Git workflow & repo setup

A practical reference for working with this repo (for you, and for any AI
assistant helping you).

## Identity (committer)

This is a **public** repo. To avoid leaking a work email in the commit history,
it commits under a GitHub no-reply identity, set **locally** for this repo only:

```bash
git config user.name  "11pyo"
git config user.email "11pyo@users.noreply.github.com"
```

Your machine's global git identity is untouched — this override applies to this
folder only. Verify with: `git config user.email`.

## Remote

```bash
# first time (already done if you cloned it):
git remote add origin https://github.com/11pyo/ai-collab-dashboard.git
git branch -M main
git push -u origin main
```

Subsequent pushes are just `git push`.

## Everyday flow

```bash
git status                 # what changed
git add -A                 # stage everything (respects .gitignore)
git commit -m "message"    # commit
git push                   # publish
```

Pull others' changes (or your edits from another machine): `git pull`.

## Commit message style

Short imperative subject, optional body explaining *why*:

```
Add round-trip sync from the board to tasks.md

The Export button emitted a JSON diff but there was no way to apply it.
This wires "Apply" to rewrite the matching task statuses in tasks.md.
```

## What is intentionally NOT committed (`.gitignore`)

| Pattern | Why |
|---------|-----|
| `inquiry-log.js.lock` | runtime lock file from `log-inquiry.py` |
| `__pycache__/`, `*.pyc` | Python build artifacts |
| `.omc/`, `.claude/`, `.mcp.json` | local AI-tooling state — may contain machine paths/secrets |
| `NOTES.local.md`, `*.local.md` | your **private** vision/idea notes — never public |
| `.vscode/`, `.idea/`, `.DS_Store` | editor/OS noise |

**Golden rule:** this repo is public and ships **fictional sample data only**.
Before committing, make sure no real names, customers, internal codes, document
numbers, hostnames, or credentials slipped in. A quick check:

```bash
git diff --cached            # review staged changes before committing
```

## Branching (optional)

For anything non-trivial, branch first, then open a PR:

```bash
git checkout -b feature/round-trip-sync
# ...edit, commit...
git push -u origin feature/round-trip-sync
gh pr create --fill          # needs the GitHub CLI, authenticated
```

## Handy `gh` commands

```bash
gh repo view --web           # open this repo in the browser
gh auth status               # check you're logged in
gh repo create <name> --public --source . --remote origin --push   # create + push a new repo
```
