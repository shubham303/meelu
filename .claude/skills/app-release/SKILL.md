---
name: app-release
description: Release a new version of the Meelu desktop app. Bumps the version in app/package.json, ships the bump through the pr-workflow skill, then watches the App build workflow until the installers and version.json are live on downloads.meelu.tech. Use when the user says "app-release", "release the app", "ship a new app build", "bump the app version", "publish the app" or "build the app".
argument-hint: [patch|minor|major|<x.y.z>] [simple|risky]
---

The desktop app is built by `.github/workflows/app-build.yml`. It runs on every push to `main` or `test` that touches `app/**`, but it only builds when `app/package.json`'s version is higher than the `version.json` already published in the `meelu-downloads` R2 bucket (`version.json` for prod, `test/version.json` for test). Installed apps compare that same version to decide whether to offer an update. So a release is a version bump that reaches `main` (prod build) and `test` (test build, published under `downloads.meelu.tech/test/`).

Merging app code alone releases nothing. Only the bump does.

## Arguments

- Version: `patch` (default), `minor`, `major`, or an exact `x.y.z` that must be higher than the current one.
- Risk: passed to pr-workflow. If not given, ask "simple or risky?". A **simple** release builds prod and test right away. A **risky** release merges only to test, so only the test build ships until the user says testing passed.

## Step 1: Read the state

```bash
git fetch origin --prune
git status --short
git branch --show-current
node -p 'require("./app/package.json").version'
curl -fsS https://downloads.meelu.tech/version.json
curl -fsS https://downloads.meelu.tech/test/version.json
published=$(curl -fsS https://downloads.meelu.tech/version.json | jq -r .version)
bump=$(git log -1 --format=%h -S"\"version\": \"$published\"" origin/main -- app/package.json)
git log --oneline "$bump"..origin/main -- app/
```

- If there are uncommitted changes, stop and ask whether they belong in this release. Never stash, never `git checkout` or `git restore` over them.
- If `app/package.json` on `origin/main` is already higher than the published prod version, a release is pending or a build failed. Check `gh run list --workflow "App build" --limit 5` and report before bumping again.
- List the app commits since the published version so the user sees what this release carries. If there are none, say so and ask before releasing.

## Step 2: Bump the version

Work on a branch named `release/app-<new-version>`, created from `origin/main` (if already on a feature branch with app work, bump on that branch instead so code and version ship together).

```bash
cd app && npm version <patch|minor|major|x.y.z> --no-git-tag-version
```

This updates `app/package.json` and `app/package-lock.json` together. Commit both with the subject `Release the app <new-version>` and the attribution lines the session requires. Do not create a git tag.

## Step 3: Ship it

Invoke the `pr-workflow` skill with the chosen risk. Use the PR title `Release the app <new-version>` and list the app commits from Step 1 in the body.

## Step 4: Watch the build

Each merge to `main` or `test` starts its own `App build` run (prod and test flavours run in separate concurrency groups).

```bash
gh run list --workflow "App build" --limit 4 --json databaseId,headBranch,status,conclusion,createdAt
gh run watch <id> --exit-status
```

- Watch with `run_in_background`, since a run takes several minutes (mac arm64 and x64, then Windows, then publish).
- If the `check` job logs `build=false`, the version was not higher than the published one. Report it; do not force a rebuild with `workflow_dispatch`, because a rebuild at the same version never reaches installed apps.
- If a job fails, show the failing step's log (`gh run view <id> --log-failed`) and stop. Do not retry blindly.

## Step 5: Confirm it is live

```bash
curl -fsS https://downloads.meelu.tech/version.json
curl -fsS https://downloads.meelu.tech/test/version.json
curl -fsSI https://downloads.meelu.tech/Meelu-mac-arm64.dmg | head -1
```

Report: the new version, the PRs, which flavours were published, the installer links, and that installed apps will offer the update on their next check. For a **risky** release, say that only test was published and that `pr-workflow merge` releases prod.

## Rules

- Never push to `main` or `test`. Everything goes through pr-workflow.
- Never lower or reuse a version number.
- Use `gh workflow run "App build"` only when the user asks for a manual rebuild, and tell them it does not trigger an update in installed apps.
