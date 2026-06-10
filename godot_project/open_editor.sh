#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
BIN="$ROOT/bin/Godot_v4.5.2-stable_linux.x86_64"

if [[ ! -x "$BIN" ]]; then
  echo "Godot binary not found at: $BIN" >&2
  exit 1
fi

exec "$BIN" --editor --path "$ROOT"
