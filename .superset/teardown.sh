#!/usr/bin/env bash
# Runs when a Superset workspace is deleted. Undoes what setup/run started.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
. ./.superset/lib.sh

echo "==> Stopping the dev server"
port="$(release_port)"
if [ -z "$port" ]; then
  echo "    no port was reserved"
else
  pids="$(lsof -nP -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
  if [ -n "$pids" ]; then
    # shellcheck disable=SC2086
    kill $pids 2>/dev/null || true
    sleep 1
    pids="$(lsof -nP -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null || true)"
    # shellcheck disable=SC2086
    [ -n "$pids" ] && kill -9 $pids 2>/dev/null || true
    echo "    stopped process on port $port"
  else
    echo "    nothing listening on port $port"
  fi
  echo "    released port $port"
fi

rm -f "$PORT_FILE" "$WORKSPACE_PATH/.superset/ports.json"

echo "==> Teardown complete"
