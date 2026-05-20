#!/usr/bin/env bash
# Story 8.1 (Epic 7 retro §1) — LOCAL infra/.env secret-provisioning check.
#
# Scans infra/env.example for ^[A-Z_]+=$ patterns (empty-on-purpose secret
# slots that the operator must populate locally) and asserts each one is
# present and non-empty in infra/.env. Catches the LOCAL-dev variant of
# the Story 7.1 production incident class (forgot to provision
# TOTP_FERNET_KEY before container restart).
#
# Skips gracefully if infra/.env is absent — common on fresh checkouts
# before the operator copies env.example → .env.
#
# Exit codes: 0 on green or skipped; 1 on missing secret.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
ENV_EXAMPLE="$ROOT/infra/env.example"
ENV_FILE="$ROOT/infra/.env"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "[skip] local-env-secrets (no infra/.env)"
  exit 0
fi

missing=()
while IFS= read -r line; do
  # Strip optional whitespace around an empty-secret declaration: ^NAME=$
  # (no value after the equals sign).
  if [[ "$line" =~ ^([A-Z][A-Z_0-9]*)=$ ]]; then
    name="${BASH_REMATCH[1]}"
    if ! grep -qE "^${name}=.+" "$ENV_FILE"; then
      missing+=("$name")
    fi
  fi
done < "$ENV_EXAMPLE"

if (( ${#missing[@]} > 0 )); then
  echo "FAIL: infra/.env is missing values for the following operator-supplied secrets" >&2
  for s in "${missing[@]}"; do
    echo "  - $s" >&2
  done
  exit 1
fi

echo "[ok] local-env-secrets — all operator-supplied slots populated"
exit 0
