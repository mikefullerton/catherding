#!/bin/bash
# configure-godaddy.sh — manage GoDaddy API credentials
# Usage:
#   configure-godaddy.sh get             — read current config (masks secret)
#   configure-godaddy.sh set KEY SECRET  — write credentials
#   configure-godaddy.sh test            — test API connectivity
#   configure-godaddy.sh set-env ENV     — set environment (production|ote)
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
}

case "$ACTION" in
  get)
    if [ ! -f "$CONFIG_FILE" ]; then
      jq -n '{"configured":false}'
      exit 0
    fi
    KEY=$(jq -r '.godaddy.api_key // empty' "$CONFIG_FILE")
    ENV=$(jq -r '.godaddy.environment // "production"' "$CONFIG_FILE")
    if [ -n "$KEY" ] && [ "$KEY" != "" ]; then
      MASKED_KEY="${KEY:0:4}...${KEY: -4}"
      jq -n --arg key "$MASKED_KEY" --arg env "$ENV" \
        '{"configured":true,"api_key":$key,"api_secret":"****","environment":$env}'
    else
      jq -n --arg env "$ENV" '{"configured":false,"environment":$env}'
    fi
    ;;

  set)
    KEY="$2"
    SECRET="$3"
    ensure_config
    jq --arg key "$KEY" --arg secret "$SECRET" \
      '.godaddy.api_key = $key | .godaddy.api_secret = $secret' \
      "$CONFIG_FILE" > "${CONFIG_FILE}.tmp" && mv "${CONFIG_FILE}.tmp" "$CONFIG_FILE"
    chmod 600 "$CONFIG_FILE"
    jq -n '{"status":"saved"}'
    ;;

  set-env)
    ENV="$2"
    if [ "$ENV" != "production" ] && [ "$ENV" != "ote" ]; then
      jq -n --arg env "$ENV" '{"status":"error","error":"invalid environment, use production or ote"}'
      exit 1
    fi
    ensure_config
    jq --arg env "$ENV" '.godaddy.environment = $env' \
      "$CONFIG_FILE" > "${CONFIG_FILE}.tmp" && mv "${CONFIG_FILE}.tmp" "$CONFIG_FILE"
    chmod 600 "$CONFIG_FILE"
    jq -n --arg env "$ENV" '{"status":"saved","environment":$env}'
    ;;

  test)
    if [ ! -f "$CONFIG_FILE" ]; then
      jq -n '{"status":"failed","error":"no config file — run setup first"}'
      exit 0
    fi
    KEY=$(jq -r '.godaddy.api_key // empty' "$CONFIG_FILE")
    SECRET=$(jq -r '.godaddy.api_secret // empty' "$CONFIG_FILE")
    ENV=$(jq -r '.godaddy.environment // "production"' "$CONFIG_FILE")
    if [ -z "$KEY" ] || [ -z "$SECRET" ]; then
      jq -n '{"status":"failed","error":"api key or secret not configured"}'
      exit 0
    fi
    if [ "$ENV" = "ote" ]; then
      BASE_URL="https://api.ote-godaddy.com"
    else
      BASE_URL="https://api.godaddy.com"
    fi
    RESPONSE=$(curl -s -w "\n%{http_code}" \
      -H "Authorization: sso-key ${KEY}:${SECRET}" \
      "${BASE_URL}/v1/domains?limit=1" 2>/dev/null)
    HTTP_CODE=$(echo "$RESPONSE" | tail -1)
    BODY=$(echo "$RESPONSE" | sed '$d')
    if [ "$HTTP_CODE" = "200" ]; then
      DOMAIN_COUNT=$(echo "$BODY" | jq 'length' 2>/dev/null || echo 0)
      jq -n --argjson count "$DOMAIN_COUNT" --arg env "$ENV" \
        '{"status":"ok","environment":$env,"domains_found":$count}'
    else
      jq -n --arg code "$HTTP_CODE" --arg env "$ENV" --arg body "$BODY" \
        '{"status":"failed","environment":$env,"http_code":$code,"error":$body}'
    fi
    ;;

  *)
    jq -n '{"error":"usage: configure-godaddy.sh [get|set|set-env|test]"}'
    exit 1
    ;;
esac
