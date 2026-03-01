#!/usr/bin/env bash

# Detect which files changed based on git state.
# Priority: staged > unstaged > branch changes
#
# Output format:
#   Scope: <description>
#   Diff: <git diff command base>
#   <file list, one per line>

set -euo pipefail

resolve_branch_base() {
  local candidate
  local upstream
  local origin_head

  # Prefer local default branches when they exist.
  for candidate in main master; do
    if git show-ref --verify --quiet "refs/heads/$candidate"; then
      git merge-base HEAD "$candidate"
      return 0
    fi
  done

  # Use configured upstream branch for the current branch, if available.
  if upstream=$(git rev-parse --abbrev-ref --symbolic-full-name '@{upstream}' 2>/dev/null); then
    git merge-base HEAD "$upstream"
    return 0
  fi

  # Use the remote default branch when origin/HEAD is available.
  if origin_head=$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null); then
    git merge-base HEAD "$origin_head"
    return 0
  fi

  # Last remote fallback for conventional branch names.
  for candidate in origin/main origin/master; do
    if git show-ref --verify --quiet "refs/remotes/$candidate"; then
      git merge-base HEAD "$candidate"
      return 0
    fi
  done

  # Final fallback: compare only against the previous commit.
  if git rev-parse --verify --quiet HEAD^ >/dev/null; then
    echo "HEAD^"
    return 0
  fi

  return 1
}

staged=$(git diff --cached --name-only)
if [[ -n "$staged" ]]; then
  echo "Scope: staged changes"
  echo "Diff: git diff --cached --"
  echo "$staged"
  exit 0
fi

unstaged=$(git diff --name-only)
untracked=$(git ls-files --others --exclude-standard)
if [[ -n "$unstaged" || -n "$untracked" ]]; then
  echo "Scope: unstaged changes"
  echo "Diff: git diff --"
  {
    echo "$unstaged"
    echo "$untracked"
  } | grep -v '^$' | sort -u
  exit 0
fi

# Fall back to branch changes since merge-base
base=$(resolve_branch_base || true)
if [[ -z "$base" ]]; then
  echo "Scope: unable to determine branch base"
  exit 1
fi
branch_changes=$(git diff --name-only "$base"...HEAD)
if [[ -n "$branch_changes" ]]; then
  echo "Scope: branch changes (since $base)"
  echo "Diff: git diff '${base}'...HEAD --"
  echo "$branch_changes"
  exit 0
fi

echo "Scope: no changes detected"
exit 1
