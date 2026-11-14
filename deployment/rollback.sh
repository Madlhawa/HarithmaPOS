#!/bin/bash
# Manual rollback. Run as root:
#   sudo bash /opt/harithma-pos/deployment/rollback.sh            # the version before the last deploy
#   sudo bash /opt/harithma-pos/deployment/rollback.sh <commit>   # a commit you name
# Same as Actions → "Roll back". Database migrations are not reversed.
set -euo pipefail
exec /usr/local/bin/harithma-ci-deploy rollback ${1:-}
