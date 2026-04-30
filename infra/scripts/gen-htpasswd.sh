#!/usr/bin/env bash
# Generate the household htpasswd file for nginx-180.
# Usage: ./gen-htpasswd.sh <username> <password>

set -euo pipefail
user="${1:?username required}"
pw="${2:?password required}"
htpasswd -nbB "$user" "$pw" > infra/nginx-180/htpasswd-3d-portal
echo "Wrote infra/nginx-180/htpasswd-3d-portal — copy to /etc/nginx/htpasswd-3d-portal on .180"
