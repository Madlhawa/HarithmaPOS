#!/bin/bash
# Manual deploy of the latest commit on GitHub main. Run as root:
#   sudo bash /opt/harithma-pos/deployment/update.sh
#
# Normally GitHub Actions deploys after the tests pass; use this only when Actions
# is unavailable. It runs the same root-owned script as the pipeline: database
# backup, migrate, restart, health check, and automatic return to the old version
# if the site does not come back. (Bypasses the tests: run them first.)
set -euo pipefail
APP_DIR=/opt/harithma-pos
SHA=$(su -s /bin/bash - harithma -c "cd $APP_DIR && git fetch --quiet origin && git rev-parse origin/main")
exec /usr/local/bin/harithma-ci-deploy deploy "$SHA"
