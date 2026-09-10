#!/usr/bin/env bash
# Shared helpers for the Superset lifecycle scripts (setup / run / teardown).
# Sourced, not executed.

# Repo root of the current worktree (all scripts cd here before sourcing).
WORKSPACE_PATH="${SUPERSET_WORKSPACE_PATH:-$PWD}"
WORKSPACE_NAME="${SUPERSET_WORKSPACE_NAME:-$(basename "$WORKSPACE_PATH")}"

# Where the allocated port is recorded inside this worktree.
PORT_FILE="$WORKSPACE_PATH/.superset/.port"

# Cross-workspace port reservations: one file per port, named after the port,
# containing the path of the workspace that owns it. Shared with every other
# workspace on this machine, which is what keeps parallel dev servers apart.
ALLOC_DIR="${SUPERSET_PORT_ALLOC_DIR:-$HOME/.superset/port-allocations}"

PORT_BASE="${SUPERSET_PORT_BASE:-4200}"
PORT_SPAN="${SUPERSET_PORT_SPAN:-100}"

port_in_use() {
  lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1
}

# Echo a port reserved for this workspace, reusing an existing reservation.
allocate_port() {
  local port owner
  mkdir -p "$ALLOC_DIR"

  if [ -f "$PORT_FILE" ]; then
    port="$(cat "$PORT_FILE")"
    if [ -n "$port" ]; then
      printf '%s\n' "$WORKSPACE_PATH" > "$ALLOC_DIR/$port"
      printf '%s\n' "$port"
      return 0
    fi
  fi

  for (( port = PORT_BASE; port < PORT_BASE + PORT_SPAN; port++ )); do
    if [ -e "$ALLOC_DIR/$port" ]; then
      owner="$(cat "$ALLOC_DIR/$port" 2>/dev/null || true)"
      if [ "$owner" = "$WORKSPACE_PATH" ]; then
        printf '%s\n' "$port" > "$PORT_FILE"
        printf '%s\n' "$port"
        return 0
      fi
      # Keep the reservation while its workspace still exists; otherwise it is
      # stale (workspace deleted without teardown) and can be reclaimed.
      if [ -n "$owner" ] && [ -d "$owner" ]; then
        continue
      fi
      rm -f "$ALLOC_DIR/$port"
    fi

    # Skip ports something else on the machine is already listening on.
    port_in_use "$port" && continue

    # noclobber makes the create atomic, so two workspaces starting at the same
    # moment cannot claim the same port.
    if ( set -o noclobber; printf '%s\n' "$WORKSPACE_PATH" > "$ALLOC_DIR/$port" ) 2>/dev/null; then
      printf '%s\n' "$port" > "$PORT_FILE"
      printf '%s\n' "$port"
      return 0
    fi
  done

  echo "no free port in ${PORT_BASE}-$((PORT_BASE + PORT_SPAN - 1))" >&2
  return 1
}

release_port() {
  local port owner
  [ -f "$PORT_FILE" ] || return 0
  port="$(cat "$PORT_FILE" 2>/dev/null || true)"
  [ -n "$port" ] || return 0

  owner="$(cat "$ALLOC_DIR/$port" 2>/dev/null || true)"
  if [ "$owner" = "$WORKSPACE_PATH" ]; then
    rm -f "$ALLOC_DIR/$port"
  fi
  printf '%s\n' "$port"
}

# Label the workspace's port in the Superset ports sidebar.
write_ports_json() {
  local port="$1"
  cat > "$WORKSPACE_PATH/.superset/ports.json" <<JSON
{
  "ports": [
    { "port": $port, "label": "CC Notes — $WORKSPACE_NAME" }
  ]
}
JSON
}
