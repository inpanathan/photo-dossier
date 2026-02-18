#!/usr/bin/env bash
# Sync requirements controller JSONs from requirements markdown files.
# Syncs both common_requirements and documentation_requirements by default.
# Preserves existing implement/enable flags; adds new reqs with "N"/"N".
#
# Usage:
#   ./scripts/sync_requirements.sh                    # sync all
#   ./scripts/sync_requirements.sh --dry-run           # preview only
#   ./scripts/sync_requirements.sh --file common       # sync only common
#   ./scripts/sync_requirements.sh --file documentation # sync only documentation

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$SCRIPT_DIR/sync_requirements_controller.py" "$@"
