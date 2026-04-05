#!/bin/bash
# status-all.sh — unified status check for all webinitor services
# Usage: status-all.sh
# Output: JSON with CLI install status and auth status for all services

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

CF_CLI=$(bash "$SCRIPT_DIR/check-cli.sh" wrangler --version)
RW_CLI=$(bash "$SCRIPT_DIR/check-cli.sh" railway version)

CF_AUTH=$(bash "$SCRIPT_DIR/check-auth.sh" cloudflare)
CF_API=$(bash "$SCRIPT_DIR/check-auth.sh" cloudflare_api)
RW_AUTH=$(bash "$SCRIPT_DIR/check-auth.sh" railway)
GD_AUTH=$(bash "$SCRIPT_DIR/check-auth.sh" godaddy)

jq -n \
  --argjson cf_cli "$CF_CLI" \
  --argjson rw_cli "$RW_CLI" \
  --argjson cf_auth "$CF_AUTH" \
  --argjson cf_api "$CF_API" \
  --argjson rw_auth "$RW_AUTH" \
  --argjson gd_auth "$GD_AUTH" \
  '{
    "cloudflare": {"cli": $cf_cli, "auth": $cf_auth, "api": $cf_api},
    "railway": {"cli": $rw_cli, "auth": $rw_auth},
    "godaddy": {"auth": $gd_auth}
  }'
