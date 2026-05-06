#!/usr/bin/env bash
# Enqueue render jobs for every model on the running portal.
# Usage: bash infra/scripts/render-all.sh "<bearer-jwt>"
#
# The token must come from a fresh login at $PORTAL_URL/api/auth/login
# (admin credentials). Worker (arq) processes jobs serially so wall
# time is roughly N_models * per-render-seconds.

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: $0 <bearer-jwt>" >&2
  exit 1
fi

PORTAL_URL="${PORTAL_URL:-http://192.168.2.190:8090}"
TOKEN="$1"
PAGE_LIMIT=200

echo "→ Listing models from $PORTAL_URL/api/models"
ids=$(curl -fsS -H "Authorization: Bearer $TOKEN" \
        "$PORTAL_URL/api/models?limit=$PAGE_LIMIT" \
      | python3 -c 'import sys,json
for m in json.load(sys.stdin)["items"]:
    print(m["id"])')

count=$(printf "%s\n" "$ids" | grep -c .)
echo "→ Found $count models. Enqueuing render jobs."

i=0
while IFS= read -r id; do
  [[ -z "$id" ]] && continue
  i=$((i+1))
  curl -fsS -X POST -H "Authorization: Bearer $TOKEN" \
       -H "Content-Type: application/json" -d '{}' \
       "$PORTAL_URL/api/admin/models/$id/render" >/dev/null
  echo "  [$i/$count] queued $id"
done <<< "$ids"

echo "Done. arq worker will process jobs asynchronously."
