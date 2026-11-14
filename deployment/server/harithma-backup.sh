#!/bin/bash
# Nightly database backup, kept for 14 days. Run by root from /etc/cron.d/harithma-backup.
# Installed as /usr/local/bin/harithma-backup (root-owned copy; see deploy.sh).
set -euo pipefail
DIR=/root/backups/nightly
mkdir -p "$DIR" && chmod 700 "$DIR"
FILE="$DIR/harithma_pos_$(date +%Y%m%d_%H%M%S).dump"
cd /tmp
sudo -u postgres pg_dump -Fc harithma_pos > "$FILE.part"
chmod 600 "$FILE.part"
pg_restore --list "$FILE.part" > /dev/null
mv "$FILE.part" "$FILE"
find "$DIR" -name 'harithma_pos_*.dump' -mtime +14 -delete
echo "Backup ok: $FILE ($(du -h "$FILE" | cut -f1))"
