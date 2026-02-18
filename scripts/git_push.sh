#!/usr/bin/env bash
# Quick commit and push — the everyday git workflow script.
#
# Usage:
#   ./scripts/git_push.sh "fix search result colors"        # commit msg
#   ./scripts/git_push.sh "add feature" --all                # stage everything
#   ./scripts/git_push.sh "update config" --files "configs/" # specific files
#   ./scripts/git_push.sh --status                           # just show status
#
# Assumes git_setup.sh has already configured the remote + auth.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# -- Defaults ---------------------------------------------------------------
MESSAGE=""
STAGE_ALL=false
SPECIFIC_FILES=""
STATUS_ONLY=false
BRANCH="main"
RUN_TESTS=false

# -- Parse args -------------------------------------------------------------
while [[ $# -gt 0 ]]; do
    case "$1" in
        --all|-a)       STAGE_ALL=true; shift ;;
        --files|-f)     SPECIFIC_FILES="$2"; shift 2 ;;
        --status|-s)    STATUS_ONLY=true; shift ;;
        --branch|-b)    BRANCH="$2"; shift 2 ;;
        --test|-t)      RUN_TESTS=true; shift ;;
        -h|--help)
            echo "Usage: $0 \"commit message\" [options]"
            echo ""
            echo "Options:"
            echo "  --all, -a         Stage all modified/new files"
            echo "  --files, -f PATH  Stage specific files/dirs (space-separated in quotes)"
            echo "  --status, -s      Just show git status, don't commit"
            echo "  --branch, -b NAME Remote branch (default: main)"
            echo "  --test, -t        Run tests before committing"
            echo ""
            echo "Examples:"
            echo "  $0 \"fix search colors\"                    # commit staged changes"
            echo "  $0 \"add visualization\" --all              # stage + commit all"
            echo "  $0 \"update config\" -f \"configs/ src/ui/\" # stage specific paths"
            echo "  $0 --status                                # just check status"
            exit 0
            ;;
        -*)
            echo "Unknown option: $1"; exit 1 ;;
        *)
            # First positional arg is the commit message
            if [[ -z "$MESSAGE" ]]; then
                MESSAGE="$1"
            fi
            shift
            ;;
    esac
done

# -- Status only mode -------------------------------------------------------
if [[ "$STATUS_ONLY" == true ]]; then
    echo "=== Git Status ==="
    git status
    echo ""
    echo "=== Recent Commits ==="
    git log --oneline -5 2>/dev/null || echo "(no commits yet)"
    exit 0
fi

# -- Validate message -------------------------------------------------------
if [[ -z "$MESSAGE" ]]; then
    echo "Error: commit message required."
    echo "Usage: $0 \"your commit message\" [--all]"
    exit 1
fi

# -- Run tests if requested -------------------------------------------------
if [[ "$RUN_TESTS" == true ]]; then
    echo "Running tests..."
    if ! uv run pytest tests/ -q; then
        echo "Tests failed! Aborting commit."
        exit 1
    fi
    echo "Tests passed."
    echo ""
fi

# -- Stage files ------------------------------------------------------------
if [[ "$STAGE_ALL" == true ]]; then
    echo "Staging all changes..."
    git add -A
elif [[ -n "$SPECIFIC_FILES" ]]; then
    echo "Staging: $SPECIFIC_FILES"
    # shellcheck disable=SC2086
    git add $SPECIFIC_FILES
else
    # Check if there are staged changes
    if git diff --cached --quiet 2>/dev/null; then
        echo "No staged changes. Use --all to stage everything, or --files to pick specific files."
        echo ""
        git status --short
        exit 1
    fi
    echo "Using already-staged changes."
fi

# -- Show what's being committed --------------------------------------------
echo ""
echo "=== Changes to commit ==="
git diff --cached --stat
echo ""

# -- Commit -----------------------------------------------------------------
git commit -m "$MESSAGE

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"

echo ""

# -- Push -------------------------------------------------------------------
LOCAL_BRANCH=$(git branch --show-current)
echo "Pushing ${LOCAL_BRANCH} -> origin/${BRANCH}..."
git push origin "${LOCAL_BRANCH}:${BRANCH}"

echo ""
echo "Pushed successfully."
git log --oneline -1
