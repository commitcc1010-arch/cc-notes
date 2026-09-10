#!/usr/bin/env bash
# Runs once when a Superset workspace is created.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
. ./.superset/lib.sh

# Untracked files that git will not bring into a new worktree, but that the dev
# server needs. Add patterns here as the project grows.
COPY_PATTERNS=(".env" ".env.*" ".envrc" ".tool-versions")

echo "==> Copying untracked files from the root checkout"
root="${SUPERSET_ROOT_PATH:-}"
if [ -z "$root" ]; then
  echo "    SUPERSET_ROOT_PATH not set — skipping"
elif [ "$root" = "$WORKSPACE_PATH" ]; then
  echo "    already in the root checkout — skipping"
else
  shopt -s nullglob
  copied=0
  for pattern in "${COPY_PATTERNS[@]}"; do
    for src in "$root"/$pattern; do
      [ -f "$src" ] || continue
      dest="./$(basename "$src")"
      if [ -e "$dest" ]; then
        echo "    $dest already exists — keeping it"
      else
        cp -p "$src" "$dest"
        echo "    copied $(basename "$src")"
        copied=$((copied + 1))
      fi
    done
  done
  shopt -u nullglob
  [ "$copied" -eq 0 ] && echo "    nothing to copy"
fi

echo "==> Installing dependencies"
if [ -f package.json ]; then
  if { [ -f bun.lock ] || [ -f bun.lockb ]; } && command -v bun >/dev/null 2>&1; then
    bun install
  elif [ -f pnpm-lock.yaml ] && command -v pnpm >/dev/null 2>&1; then
    pnpm install --frozen-lockfile
  elif [ -f yarn.lock ] && command -v yarn >/dev/null 2>&1; then
    yarn install --frozen-lockfile
  else
    npm install
  fi
else
  echo "    no package.json — static HTML site, nothing to install"
fi

echo "==> Reserving a dev-server port"
port="$(allocate_port)"
write_ports_json "$port"
echo "    port $port (recorded in .superset/.port)"

echo "==> Setup complete. Press Run to serve http://localhost:$port"
