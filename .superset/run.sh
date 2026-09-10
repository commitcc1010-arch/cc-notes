#!/usr/bin/env bash
# Dev server for the notes site. Launched by the Superset Run button.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
. ./.superset/lib.sh

# Allocate on demand too, so Run works even if setup never ran (root checkout,
# or a workspace created before this config landed).
port="$(allocate_port)"
write_ports_json "$port"

if port_in_use "$port"; then
  echo "Port $port is already serving this workspace — stop the existing Run pane first." >&2
  exit 1
fi

echo "Serving $WORKSPACE_PATH on http://localhost:$port"

if command -v python3 >/dev/null 2>&1; then
  exec python3 -m http.server "$port" --bind 127.0.0.1 --directory "$WORKSPACE_PATH"
elif command -v npx >/dev/null 2>&1; then
  exec npx --yes serve --listen "127.0.0.1:$port" "$WORKSPACE_PATH"
else
  echo "Need python3 or npx to serve static files." >&2
  exit 1
fi
