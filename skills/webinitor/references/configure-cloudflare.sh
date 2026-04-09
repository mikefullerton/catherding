#!/bin/bash
# configure-cloudflare.sh — manage Cloudflare API token
# Usage:
#   configure-cloudflare.sh get           — show masked token + account_id
#   configure-cloudflare.sh set <token>   — save token, auto-fetch account_id, test
#   configure-cloudflare.sh test          — verify token works
# Output: JSON

CONFIG_DIR="$HOME/.webinitor"
CONFIG_FILE="$CONFIG_DIR/config.json"
ACTION="$1"

ensure_config() {
  if [ ! -d "$CONFIG_DIR" ]; then
    mkdir -p "$CONFIG_DIR"
    chmod 700 "$CONFIG_DIR"
  fi
  if [ ! -f "$CONFIG_FILE" ]; then
    cat > "$CONFIG_FILE" <<'DEFAULTS'
{
  "godaddy": {
    "api_key": "",
    "api_secret": "",
    "environment": "production"
  },
  "cloudflare": {
    "api_token": "",
    "account_id": ""
  },
  "preferences": {
    "install_method": "brew"
  }
}
DEFAULTS
    chmod 600 "$CONFIG_FILE"
  fi
  # Ensure cloudflare section exists in existing config
  if ! jq -e '.cloudflare' "$CONFIG_FILE" >/dev/null 2>&1; then
    jq '.cloudflare = {"api_token":"","account_id":""}' \
      "$CONFIG_FILE" > "${CONFIG_FILE}.tmp" && mv "${CONFIG_FILE}.tmp" "$CONFIG_FILE"
    chmod 600 "$CONFIG_FILE"
  fi
}

case "$ACTION" in
  get)
    if [ ! -f "$CONFIG_FILE" ]; then
      jq -n '{"configured":false}'
      exit 0
    fi
    TOKEN=$(jq -r '.cloudflare.api_token // empty' "$CONFIG_FILE")
    ACCOUNT_ID=$(jq -r '.cloudflare.account_id // empty' "$CONFIG_FILE")
    if [ -n "$TOKEN" ] && [ "$TOKEN" != "" ]; then
      MASKED="${TOKEN:0:4}...${TOKEN: -4}"
      jq -n --arg token "$MASKED" --arg aid "$ACCOUNT_ID" \
        '{"configured":true,"api_token":$token,"account_id":$aid}'
    else
      jq -n '{"configured":false}'
    fi
    ;;

  set)
    TOKEN="$2"
    ensure_config
    # Test the token first
    RESPONSE=$(curl -s -H "Authorization: Bearer ${TOKEN}" \
      "https://api.cloudflare.com/client/v4/zones?per_page=1" 2>/dev/null)
    SUCCESS=$(echo "$RESPONSE" | jq -r '.success' 2>/dev/null)
    if [ "$SUCCESS" != "true" ]; then
      ERROR=$(echo "$RESPONSE" | jq -r '.errors[0].message // "unknown error"' 2>/dev/null)
      jq -n --arg err "$ERROR" '{"status":"failed","error":$err}'
      exit 0
    fi
    # Fetch account_id
    ACCT_RESPONSE=$(curl -s -H "Authorization: Bearer ${TOKEN}" \
      "https://api.cloudflare.com/client/v4/accounts?per_page=1" 2>/dev/null)
    ACCOUNT_ID=$(echo "$ACCT_RESPONSE" | jq -r '.result[0].id // empty' 2>/dev/null)
    ACCOUNT_NAME=$(echo "$ACCT_RESPONSE" | jq -r '.result[0].name // empty' 2>/dev/null)
    # Save token and account_id
    jq --arg token "$TOKEN" --arg aid "$ACCOUNT_ID" \
      '.cloudflare.api_token = $token | .cloudflare.account_id = $aid' \
      "$CONFIG_FILE" > "${CONFIG_FILE}.tmp" && mv "${CONFIG_FILE}.tmp" "$CONFIG_FILE"
    chmod 600 "$CONFIG_FILE"
    ZONE_COUNT=$(echo "$RESPONSE" | jq -r '.result_info.total_count // 0' 2>/dev/null)
    jq -n --arg aid "$ACCOUNT_ID" --arg name "$ACCOUNT_NAME" --argjson zones "$ZONE_COUNT" \
      '{"status":"saved","account_id":$aid,"account_name":$name,"zones":$zones}'
    ;;

  test)
    if [ ! -f "$CONFIG_FILE" ]; then
      jq -n '{"status":"failed","error":"no config file"}'
      exit 0
    fi
    TOKEN=$(jq -r '.cloudflare.api_token // empty' "$CONFIG_FILE")
    if [ -z "$TOKEN" ]; then
      jq -n '{"status":"failed","error":"no api token configured"}'
      exit 0
    fi
    RESPONSE=$(curl -s -H "Authorization: Bearer ${TOKEN}" \
      "https://api.cloudflare.com/client/v4/zones?per_page=1" 2>/dev/null)
    SUCCESS=$(echo "$RESPONSE" | jq -r '.success' 2>/dev/null)
    if [ "$SUCCESS" = "true" ]; then
      ZONE_COUNT=$(echo "$RESPONSE" | jq -r '.result_info.total_count // 0' 2>/dev/null)
      jq -n --argjson zones "$ZONE_COUNT" '{"status":"ok","zones":$zones}'
    else
      ERROR=$(echo "$RESPONSE" | jq -r '.errors[0].message // "unknown error"' 2>/dev/null)
      jq -n --arg err "$ERROR" '{"status":"failed","error":$err}'
    fi
    ;;

  *)
    jq -n '{"error":"usage: configure-cloudflare.sh [get|set|test]"}'
    exit 1
    ;;
esac
