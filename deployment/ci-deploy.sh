#!/bin/bash
# Deploys or rolls back Harithma POS. Called by GitHub Actions over SSH.
#
# Installed on the server as /usr/local/bin/harithma-ci-deploy (owned by root, not
# the copy in the repository: the repository belongs to the app user, and root must
# never run a file that user can edit). The GitHub key in /root/.ssh/authorized_keys
# is locked to this script with command="...", so it can do nothing else:
#
#   deploy <commit>      back up the database, check out <commit>, install, migrate,
#                        restart, health-check; on failure go back to the old commit
#   rollback [commit]    go back to [commit], or to the commit before the last deploy
#
# Install or update:  sudo install -o root -g root -m 755 deployment/ci-deploy.sh /usr/local/bin/harithma-ci-deploy
set -euo pipefail

APP_DIR=/opt/harithma-pos
APP_USER=harithma
SERVICE=harithma-pos
DB_NAME=harithma_pos
BACKUP_DIR=/root/backups/predeploy
KEEP_BACKUPS=20
STATE_DIR=/var/lib/harithma-deploy
LOG=/var/log/harithma-deploy.log
HEALTH_URL=http://127.0.0.1:8080/app/login

mkdir -p "$STATE_DIR" "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"
exec > >(tee -a "$LOG") 2>&1

# One deploy at a time.
exec 9>"$STATE_DIR/lock"
flock -w 600 9 || { echo "Another deploy is still running."; exit 1; }

say() { echo "[$(date -u +%FT%TZ)] $*"; }
as_app() { su -s /bin/bash - "$APP_USER" -c "cd $APP_DIR && $1"; }
current() { as_app "git rev-parse HEAD"; }

checkout() {   # $1 = commit
    as_app "git fetch --quiet origin && git reset --hard --quiet $1" || return 1
    say "Code is at $(as_app 'git log -1 --format="%h %s"')"
    as_app "venv/bin/pip install --quiet --disable-pip-version-check -r requirements.txt" || return 1
}

migrate() {
    as_app "export \$(grep -v '^#' .env | grep -v '^$' | xargs) && venv/bin/flask db upgrade"
}

restart_and_check() {
    systemctl restart "$SERVICE"
    for _ in $(seq 1 20); do
        sleep 2
        if curl -fsS -o /dev/null --max-time 5 "$HEALTH_URL"; then
            say "Health check passed."
            return 0
        fi
    done
    say "Health check FAILED: $HEALTH_URL did not answer."
    return 1
}

backup() {   # $1 = label
    local file="$BACKUP_DIR/predeploy_$(date -u +%Y%m%d_%H%M%S)_$1.dump"
    (cd /tmp && sudo -u postgres pg_dump -Fc "$DB_NAME") > "$file"
    chmod 600 "$file"
    say "Database backed up to $file ($(du -h "$file" | cut -f1))."
    ls -1t "$BACKUP_DIR"/predeploy_*.dump | tail -n +$((KEEP_BACKUPS + 1)) | xargs -r rm -f
}

valid_commit() { [[ "$1" =~ ^[0-9a-f]{7,40}$ ]]; }

read -r ACTION TARGET EXTRA <<< "${SSH_ORIGINAL_COMMAND:-${*:-}}" || true
[[ -z "${EXTRA:-}" ]] || { echo "Too many arguments."; exit 2; }

case "${ACTION:-}" in
deploy)
    valid_commit "${TARGET:-}" || { echo "Usage: deploy <commit sha>"; exit 2; }
    BEFORE=$(current)
    say "Deploying $TARGET (currently $BEFORE)."
    as_app "git fetch --quiet origin && git cat-file -e '$TARGET^{commit}'" \
        || { say "Commit $TARGET is not on GitHub. Nothing was changed."; exit 1; }
    backup "${TARGET:0:7}"
    if checkout "$TARGET" && migrate && restart_and_check; then
        echo "$BEFORE" > "$STATE_DIR/previous"
        echo "$TARGET" > "$STATE_DIR/current"
        say "Deploy finished."
    else
        say "Deploy failed: going back to $BEFORE."
        checkout "$BEFORE" || true
        restart_and_check || say "The old version did not come back either. Check: journalctl -u $SERVICE"
        say "Database changes from the failed deploy were NOT undone; the backup above has the data from before it."
        exit 1
    fi
    ;;
rollback)
    if [[ -z "${TARGET:-}" ]]; then
        TARGET=$(cat "$STATE_DIR/previous" 2>/dev/null || true)
        [[ -n "$TARGET" ]] || { echo "No previous deploy is recorded. Give a commit to roll back to."; exit 2; }
    fi
    valid_commit "$TARGET" || { echo "Usage: rollback [commit sha]"; exit 2; }
    BEFORE=$(current)
    as_app "git fetch --quiet origin && git cat-file -e '$TARGET^{commit}'" \
        || { say "Commit $TARGET is not known. Nothing was changed."; exit 1; }
    say "Rolling back from $BEFORE to $TARGET."
    backup "rollback"
    checkout "$TARGET"
    restart_and_check
    echo "$BEFORE" > "$STATE_DIR/previous"
    echo "$TARGET" > "$STATE_DIR/current"
    say "Rollback finished. Database migrations are not reversed; run 'flask db downgrade' by hand if a newer one must be undone."
    ;;
*)
    echo "Usage: deploy <commit> | rollback [commit]"
    exit 2
    ;;
esac
