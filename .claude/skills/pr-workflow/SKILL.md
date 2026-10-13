---
name: pr-workflow
description: Ship committed work through pull requests. Opens a PR to main, cherry-picks its commits into a PR to test, then merges a simple change straight to main or sends a risky one through test first. Use when the user says "pr-workflow", "raise a PR", "ship this", "deploy this", "send it to test", "update the PR" or "merge to main". Never push to main or test directly.
argument-hint: [simple|risky|update|merge] [optional: main PR number]
---

`main` and `test` are never pushed to directly. Every change reaches them through a pull request. Coolify deploys each branch when it changes, so merging to `main` deploys production and merging to `test` deploys the test environment.

## Modes

Read the mode from `$ARGUMENTS`:

- **simple**: low-risk change. Raise both PRs, then merge the main PR and the test PR. Nothing is tested on the test environment first.
- **risky**: change that might break something. Raise both PRs, merge only the test PR, and stop. The user tests the test environment.
- **update**: the main PR already exists and its branch got new commits (a fix found during testing). Push them, carry only the new commits into test, and merge the test PR again.
- **merge**: the user says testing passed. Merge the main PR.

If no mode is given, ask "simple or risky?". Do not guess: the answer decides whether production changes without testing.

## Step 1: Read the repo

```bash
git fetch origin --prune
git status --short
git branch --show-current
git ls-remote --exit-code --heads origin test
```

- If `origin/test` does not exist, the repo has no test environment. Run the main PR steps only. For **risky**, tell the user there is nothing to test on and ask whether to merge to main.
- If there are uncommitted changes, stop and ask whether to commit them first. Never stash, never `git checkout` or `git restore` over them.

## Step 2: Put the work on a feature branch

- **On a feature branch:** use it.
- **On `main` or `test` with local commits ahead of the remote:** move them to a new branch without touching the working tree:
  ```bash
  git switch -c <type>/<short-slug>
  git branch -f main origin/main
  ```
  Name the branch from the commits (for example `feat/pricing-page`, `fix/offline-screen`).
- **No commits ahead of `origin/main`:** there is nothing to ship. Say so and stop.

If `origin/main` has moved and the PR would conflict, run `git rebase origin/main` on the feature branch, then `git push --force-with-lease`. Force-push only feature branches, never `main` or `test`.

## Step 3: The main PR

```bash
git push -u origin HEAD
gh pr view --json number,url,state 2>/dev/null
```

If no open PR exists for the branch, create one:

```bash
gh pr create --base main --head <branch> --title "<title>" --body "<body>"
```

- **Title:** the change in plain words, in the style of the repo's commit subjects.
- **Body:** what changed and why, the commits it carries, `Risk: simple` or `Risk: risky`, and a line `Test PR: (pending)`.
- **Ending:** follow the repo's attribution rule for PR descriptions.

In **update** mode the push alone updates the PR.

## Step 4: The test PR (only when `origin/test` exists)

The test PR carries the same commits as the main PR, cherry-picked onto `test`. Build it in a separate worktree so the user's working tree is not touched:

```bash
WT=<scratchpad>/test-pr-<branch-slug>
TEST_BRANCH=test-pr/<feature-branch with / replaced by ->
```

Never name it `test/...`: git cannot hold a `test/...` branch next to the `test` branch.

1. **Pick the base.**
   - If an open PR to `test` exists from `$TEST_BRANCH`, add to it: `git worktree add "$WT" "$TEST_BRANCH"` and `git -C "$WT" pull --ff-only`.
   - Otherwise start fresh from `origin/test` (if an earlier test PR for this branch was merged, use the name `$TEST_BRANCH-2`, `-3` and so on): `git worktree add -b "$TEST_BRANCH" "$WT" origin/test`.
2. **Catch test up with main.** If `origin/main` is not already in the base, run `git -C "$WT" merge --no-edit origin/main`. This brings in changes that went straight to main. If the merge conflicts, stop and show the conflict to the user.
3. **Pick the commits not yet on test.** List the PR's commits oldest first: `git rev-list --reverse --no-merges origin/main..<feature-branch>`. Skip any commit whose full SHA already appears in a `cherry picked from commit <sha>` line on the base: `git -C "$WT" log --format=%B HEAD | grep -q "cherry picked from commit $sha"`.
4. **Cherry-pick them.** Run `git -C "$WT" cherry-pick -x <sha>` for each. The `-x` line is what step 3 uses next time. On a conflict, stop and show it to the user. Never resolve by blindly taking one side.
5. **Push and open the PR.**
   ```bash
   git -C "$WT" push -u origin "$TEST_BRANCH"
   gh pr create --base test --head "$TEST_BRANCH" --title "[test] <main PR title>" --body "Cherry-picked from #<main PR>. Merging deploys the test environment."
   ```
   Edit the main PR body so its `Test PR:` line links the test PR (`gh pr edit <n> --body ...`).
6. **Clean up.** Run `git worktree remove "$WT"`.

## Step 5: Merge

Merge with `gh pr merge <n> --rebase --delete-branch`. This keeps history linear and matches the repo. Never use `--admin`, and never merge a PR whose checks fail.

- **simple:** merge the main PR (production deploys), then merge the test PR so test matches main.
- **risky:** merge only the test PR. Tell the user which test environment to check (see the project's deployment notes) and stop. Leave the main PR open.
- **update:** after Step 3 and Step 4, merge the new test PR and stop again for testing.
- **merge:** the user said testing passed. Merge the main PR. If a test PR for this branch is still open, close it with `gh pr close`, because main now has the change and the next test PR catches test up.

## Step 6: Finish

- If the user's current branch was deleted by the merge and the working tree is clean, run `git switch main && git merge --ff-only origin/main`.
- Report the PR links, what was merged, and which environment is deploying.

## Rules

- Never `git push` to `main` or `test`, with or without force. A local `pre-push` hook blocks it. Do not bypass it with `--no-verify`.
- Never merge to `main` in **risky** mode until the user says testing passed.
- Commit messages follow the repo's style and attribution rules.
