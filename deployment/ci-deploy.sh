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
HISTORY=$STATE_DIR/history.jsonl   # one JSON line per deploy or rollback, read by the developer page

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
    LAST_BACKUP=$file
    say "Database backed up to $file ($(du -h "$file" | cut -f1))."
    ls -1t "$BACKUP_DIR"/predeploy_*.dump | tail -n +$((KEEP_BACKUPS + 1)) | xargs -r rm -f
}

valid_commit() { [[ "$1" =~ ^[0-9a-f]{7,40}$ ]]; }
number() { [[ "${1:-}" =~ ^[0-9]{1,12}(\.[0-9]{1,3})?$ ]]; }

# deploy <sha> [passed failed skipped seconds run_id]   (the test figures come from GitHub Actions)
read -r ACTION TARGET T_PASSED T_FAILED T_SKIPPED T_SECONDS RUN_ID EXTRA <<< "${SSH_ORIGINAL_COMMAND:-${*:-}}" || true
[[ -z "${EXTRA:-}" ]] || { echo "Too many arguments."; exit 2; }
for v in T_PASSED T_FAILED T_SKIPPED T_SECONDS RUN_ID; do
    [[ -z "${!v:-}" ]] || number "${!v}" || { echo "Bad value for $v."; exit 2; }
done
if [[ -n "${SSH_ORIGINAL_COMMAND:-}" ]]; then TRIGGER=github; else TRIGGER=server; fi
STARTED=$(date +%s)
LAST_BACKUP=""

record() {   # $1 = action, $2 = result, $3 = from, $4 = to, $5 = note
    local subject
    subject=$(as_app "git log -1 --format=%s $4 2>/dev/null" | head -c 160 | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read().strip()))')
    printf '{"time":"%s","action":"%s","result":"%s","trigger":"%s","from":"%s","to":"%s","subject":%s,"seconds":%s,"backup":"%s","tests_passed":%s,"tests_failed":%s,"tests_skipped":%s,"tests_seconds":%s,"run_id":%s,"note":"%s"}\n' \
        "$(date -u +%FT%TZ)" "$1" "$2" "$TRIGGER" "${3:0:12}" "${4:0:12}" "$subject" "$(( $(date +%s) - STARTED ))" \
        "$(basename "${LAST_BACKUP:-}")" "${T_PASSED:-null}" "${T_FAILED:-null}" "${T_SKIPPED:-null}" "${T_SECONDS:-null}" "${RUN_ID:-null}" "$5" >> "$HISTORY"
    chmod 644 "$HISTORY"
}

case "${ACTION:-}" in
deploy)
    valid_commit "${TARGET:-}" || { echo "Usage: deploy <commit sha>"; exit 2; }
    BEFORE=$(current)
    say "Deploying $TARGET (currently $BEFORE)."
    as_app "git fetch --quiet origin && git cat-file -e '$TARGET^{commit}'" \
        || { say "Commit $TARGET is not on GitHub. Nothing was changed."; record deploy refused "$BEFORE" "$BEFORE" "unknown commit ${TARGET:0:12}"; exit 1; }
    backup "${TARGET:0:7}"
    if checkout "$TARGET" && migrate && restart_and_check; then
        echo "$BEFORE" > "$STATE_DIR/previous"
        echo "$TARGET" > "$STATE_DIR/current"
        record deploy success "$BEFORE" "$TARGET" ""
        say "Deploy finished."
    else
        say "Deploy failed: going back to $BEFORE."
        checkout "$BEFORE" || true
        restart_and_check || say "The old version did not come back either. Check: journalctl -u $SERVICE"
        say "Database changes from the failed deploy were NOT undone; the backup above has the data from before it."
        record deploy failed "$BEFORE" "$TARGET" "went back to ${BEFORE:0:7}"
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
    if ! { checkout "$TARGET" && restart_and_check; }; then
        record rollback failed "$BEFORE" "$TARGET" "check the service"
        exit 1
    fi
    echo "$BEFORE" > "$STATE_DIR/previous"
    echo "$TARGET" > "$STATE_DIR/current"
    record rollback success "$BEFORE" "$TARGET" ""
    say "Rollback finished. Database migrations are not reversed; run 'flask db downgrade' by hand if a newer one must be undone."
    ;;
*)
    echo "Usage: deploy <commit> | rollback [commit]"
    exit 2
    ;;
esac
