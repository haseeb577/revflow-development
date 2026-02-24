#!/usr/bin/env bash
set -euo pipefail

# deploy_revhome.sh
# Usage:
#   sudo ./deploy_revhome.sh --user root
#   sudo ./deploy_revhome.sh --user www-data --src /root/revhome_assessment_engine_v2 --dst /var/www/revhome_assessment_engine_v2
#
# What it does:
#  - optionally rsyncs src -> dst when running as www-data
#  - stops & disables old revhome.service (if present)
#  - creates /etc/systemd/system/revhome_api.service for the chosen user
#  - daemon-reloads, enables, starts the new unit
#  - prints service status and last logs and checks /health

# Defaults
USER_OPT="root"
SRC="/root/revhome_assessment_engine_v2"
DST="/var/www/revhome_assessment_engine_v2"
OLD_UNIT="revhome.service"
NEW_UNIT="revhome_api.service"
PORT=8100
WORKERS=1

function usage() {
  cat <<EOF
Usage: sudo $0 --user root|www-data [--src /path/to/source] [--dst /path/to/destination]
Examples:
  sudo $0 --user root
  sudo $0 --user www-data --src /root/revhome_assessment_engine_v2 --dst /var/www/revhome_assessment_engine_v2
EOF
  exit 1
}

# Arg parsing (simple)
while [ $# -gt 0 ]; do
  case "$1" in
    --user)
      USER_OPT="$2"; shift 2;;
    --src)
      SRC="$2"; shift 2;;
    --dst)
      DST="$2"; shift 2;;
    --port)
      PORT="$2"; shift 2;;
    --help|-h)
      usage;;
    *)
      echo "Unknown arg: $1"; usage;;
  esac
done

if [ "$(id -u)" -ne 0 ]; then
  echo "ERROR: This script must be run as root (sudo)." >&2
  exit 2
fi

if [[ "$USER_OPT" != "root" && "$USER_OPT" != "www-data" ]]; then
  echo "ERROR: --user must be 'root' or 'www-data'." >&2
  exit 2
fi

# Determine working directory depending on user choice
if [ "$USER_OPT" = "www-data" ]; then
  WORKDIR="$DST"
else
  WORKDIR="$SRC"
fi

echo "Deploying service as user: $USER_OPT"
echo "Source dir: $SRC"
echo "Workdir (service will use): $WORKDIR"
echo "Systemd unit to create: /etc/systemd/system/$NEW_UNIT"
echo

# 1) If user=www-data, sync files to DST and set ownership
if [ "$USER_OPT" = "www-data" ]; then
  echo "Preparing destination dir $DST for www-data..."
  mkdir -p "$DST"
  rsync -a --delete --exclude='.venv' --exclude='venv' "$SRC"/ "$DST"/
  # If you have a venv inside src and want to copy, remove --exclude above or recreate venv at DST
  chown -R www-data:www-data "$DST"
  echo "Synced $SRC -> $DST and set ownership to www-data."
  echo
fi

# 2) Stop & disable the old revhome.service if present (safe check)
if systemctl list-units --full -all | grep -Fq "$OLD_UNIT"; then
  echo "Found existing unit $OLD_UNIT. Stopping and disabling it..."
  systemctl stop "$OLD_UNIT" || true
  systemctl disable "$OLD_UNIT" || true
  echo "$OLD_UNIT stopped & disabled."
else
  echo "No existing $OLD_UNIT unit found. Skipping stop/disable."
fi
echo

# 3) Determine uvicorn path inside venv or fallback
function find_uvicorn() {
  candidates=(
    "$WORKDIR/venv/bin/uvicorn"
    "$WORKDIR/.venv/bin/uvicorn"
    "/usr/local/bin/uvicorn"
    "/usr/bin/uvicorn"
  )
  for c in "${candidates[@]}"; do
    if [ -x "$c" ]; then
      echo "$c"
      return 0
    fi
  done
  return 1
}

UVICORN_BIN="$(find_uvicorn || true)"
if [ -z "$UVICORN_BIN" ]; then
  echo "WARNING: uvicorn binary not found in common places." >&2
  echo "Make sure a venv is available at $WORKDIR/venv or .venv, or install uvicorn system-wide."
  echo "Continuing — systemd unit will reference \$PATH to find uvicorn inside the venv."
fi

# 4) Create systemd unit contents dynamically
if [ "$USER_OPT" = "root" ]; then
  UNIT_USER="root"
  UNIT_WORKINGDIR="$WORKDIR"
  # prefer explicit venv bin if found
  if [ -n "$UVICORN_BIN" ]; then
    EXECSTART="${UVICORN_BIN} revhome_api:app --host 127.0.0.1 --port ${PORT} --workers ${WORKERS}"
    ENV_PATH=""
  else
    EXECSTART="/bin/sh -c 'PATH=${WORKDIR}/venv/bin:\$PATH uvicorn revhome_api:app --host 127.0.0.1 --port ${PORT} --workers ${WORKERS}'"
    ENV_PATH="Environment=\"PATH=${WORKDIR}/venv/bin\""
  fi
else
  UNIT_USER="www-data"
  UNIT_WORKINGDIR="$WORKDIR"
  if [ -n "$UVICORN_BIN" ]; then
    EXECSTART="${UVICORN_BIN} server:app --host 127.0.0.1 --port ${PORT} --workers ${WORKERS}"
    # Note: existing running service used server:app in /opt/revhome_api; adjust if your entrypoint differs.
    ENV_PATH=""
  else
    EXECSTART="/bin/sh -c 'PATH=${WORKDIR}/venv/bin:\$PATH uvicorn server:app --host 127.0.0.1 --port ${PORT} --workers ${WORKERS}'"
    ENV_PATH="Environment=\"PATH=${WORKDIR}/venv/bin\""
  fi
fi

echo "Creating systemd unit /etc/systemd/system/$NEW_UNIT ..."
cat > /etc/systemd/system/$NEW_UNIT <<UNIT
[Unit]
Description=RevHome API FastAPI Service (deployed from $WORKDIR)
After=network.target

[Service]
Type=simple
User=${UNIT_USER}
WorkingDirectory=${UNIT_WORKINGDIR}
${ENV_PATH}
ExecStart=${EXECSTART}
Restart=on-failure
RestartSec=5
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
UNIT

chmod 644 /etc/systemd/system/$NEW_UNIT
echo "Unit file written."
echo

# 5) Reload systemd, enable & start new unit
systemctl daemon-reload
systemctl enable "$NEW_UNIT"
systemctl start "$NEW_UNIT"

echo "Started $NEW_UNIT. Waiting a moment for startup..."
sleep 2

# 6) Show status & recent logs
echo "====== systemctl status $NEW_UNIT ======"
systemctl status "$NEW_UNIT" --no-pager
echo
echo "====== journalctl -n 200 for $NEW_UNIT (tail) ======"
journalctl -u "$NEW_UNIT" -n 200 --no-pager

# 7) Quick health check
echo
echo "====== Health check ======"
if command -v curl >/dev/null 2>&1; then
  sleep 1
  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:${PORT}/health" || true)
  if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "302" ] || [ "$HTTP_CODE" = "204" ] || [ -n "$HTTP_CODE" ]; then
    echo "HTTP ${HTTP_CODE} from http://127.0.0.1:${PORT}/health"
  else
    echo "No response from health endpoint."
  fi
else
  echo "curl not installed — please run: curl -i http://127.0.0.1:${PORT}/health"
fi

echo
echo "Done. If you need to view live logs: sudo journalctl -u $NEW_UNIT -f"
